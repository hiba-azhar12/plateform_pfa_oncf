import json
import os
import re
import shutil
import sys
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from config.chemins import (
    COLONNES_ESSENTIELLES_CIRCULATION,
    COLONNES_ESSENTIELLES_CONTROLEPDA,
    COLONNES_ESSENTIELLES_VENTEPDA,
    DEPOT_QUOTIDIEN_CIRCULATION,
    DEPOT_QUOTIDIEN_CONTROLES,
    DEPOT_QUOTIDIEN_VENTES,
    DEPOT_TRAITE_CIRCULATION,
    DEPOT_TRAITE_CONTROLES,
    DEPOT_TRAITE_VENTES,
    HISTORIQUE,
    LOG_EXECUTION,
    PREDICTIONS_NOUVELLES,
)
from config.modeles import MODELES
from utils.agregation import agreger_lot_quotidien
from utils.inference import predire_nouvelle_date

MOTIF_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _dates_disponibles(dossier, prefixe):
    if not os.path.isdir(dossier):
        return []
    dates = []
    for nom_fichier in os.listdir(dossier):
        if nom_fichier.startswith(prefixe):
            correspondance = MOTIF_DATE.search(nom_fichier)
            if correspondance:
                dates.append(correspondance.group(1))
    return sorted(dates)


def _prochaine_date_a_traiter():
    dates_ventes = set(_dates_disponibles(DEPOT_QUOTIDIEN_VENTES, "ventes_"))
    dates_controles = set(_dates_disponibles(DEPOT_QUOTIDIEN_CONTROLES, "controles_"))
    dates_circulation = set(_dates_disponibles(DEPOT_QUOTIDIEN_CIRCULATION, "circulation_"))

    dates_completes = dates_ventes & dates_controles & dates_circulation
    if not dates_completes:
        return None
    return sorted(dates_completes)[0]


def _valider_colonnes(df, colonnes_attendues, nom_fichier):
    manquantes = [colonne for colonne in colonnes_attendues if colonne not in df.columns]
    if manquantes:
        raise ValueError(f"Colonnes manquantes dans {nom_fichier} : {manquantes}")


def _charger_lot(date_texte):
    chemin_ventes = os.path.join(DEPOT_QUOTIDIEN_VENTES, f"ventes_{date_texte}.csv")
    chemin_controles = os.path.join(DEPOT_QUOTIDIEN_CONTROLES, f"controles_{date_texte}.csv")
    chemin_circulation = os.path.join(DEPOT_QUOTIDIEN_CIRCULATION, f"circulation_{date_texte}.csv")

    ventepda = pd.read_csv(chemin_ventes)
    controlepda = pd.read_csv(chemin_controles)
    circulation = pd.read_csv(chemin_circulation)

    _valider_colonnes(ventepda, COLONNES_ESSENTIELLES_VENTEPDA, f"ventes_{date_texte}.csv")
    _valider_colonnes(controlepda, COLONNES_ESSENTIELLES_CONTROLEPDA, f"controles_{date_texte}.csv")
    _valider_colonnes(circulation, COLONNES_ESSENTIELLES_CIRCULATION, f"circulation_{date_texte}.csv")

    return ventepda, controlepda, circulation, [chemin_ventes, chemin_controles, chemin_circulation]


def _cles_grain(cle_modele):
    info = MODELES[cle_modele]
    cles = ["Date", "LiaisonId"]
    if info["granularite"] == "horaire":
        cles.append("Heure")
    if info["famille"] == "composition":
        cles.append(info["colonne_categorie"])
    return cles


def _chemin_historique(cle_modele):
    return os.path.join(HISTORIQUE, f"{cle_modele}.parquet")


def _mettre_a_jour_historique(cle_modele, nouvelles_lignes):
    chemin = _chemin_historique(cle_modele)
    os.makedirs(HISTORIQUE, exist_ok=True)

    if os.path.isfile(chemin):
        historique = pd.read_parquet(chemin)
        combine = pd.concat([historique, nouvelles_lignes], ignore_index=True, sort=False)
    else:
        combine = nouvelles_lignes

    cles = _cles_grain(cle_modele)
    combine = combine.drop_duplicates(subset=cles, keep="last").sort_values(cles)
    combine.to_parquet(chemin, index=False)
    return combine


def _chemin_predictions_nouvelles(cle_modele):
    return os.path.join(PREDICTIONS_NOUVELLES, f"{cle_modele}.parquet")


def _charger_predictions_nouvelles(cle_modele):
    chemin = _chemin_predictions_nouvelles(cle_modele)
    if os.path.isfile(chemin):
        return pd.read_parquet(chemin)
    return pd.DataFrame()


def _valeur_reelle_observee(cle_modele, valeurs_observees):
    info = MODELES[cle_modele]

    if info["famille"] != "composition":
        return valeurs_observees

    colonne_categorie = info["colonne_categorie"]
    colonne_brute = "NbBillets" if "NbBillets" in valeurs_observees.columns else "NbControles"

    total_jour = valeurs_observees.groupby(["Date", "LiaisonId"])[colonne_brute].transform("sum")
    valeurs_observees = valeurs_observees.copy()
    valeurs_observees[info["cible"]] = valeurs_observees[colonne_brute] / total_jour.replace(0, pd.NA)
    return valeurs_observees


def _reconcilier(cle_modele, date_texte, valeurs_observees):
    info = MODELES[cle_modele]
    existantes = _charger_predictions_nouvelles(cle_modele)
    if existantes.empty:
        return existantes

    valeurs_observees = _valeur_reelle_observee(cle_modele, valeurs_observees)

    existantes["Date"] = pd.to_datetime(existantes["Date"])
    cible_date = pd.Timestamp(date_texte)

    cles_jointure = ["LiaisonId"]
    if info["granularite"] == "horaire":
        cles_jointure.append("Heure")
    if info["famille"] == "composition":
        cles_jointure.append(info["colonne_categorie"])

    valeurs_observees = valeurs_observees.copy()
    valeurs_observees["Date"] = cible_date

    masque = (existantes["Date"] == cible_date) & (existantes["Reel"].isna())
    if not masque.any():
        return existantes

    fusion = existantes[masque].merge(
        valeurs_observees[["Date"] + cles_jointure + [info["cible"]]],
        on=["Date"] + cles_jointure,
        how="left",
        suffixes=("", "_observe"),
    )

    existantes.loc[masque, "Reel"] = fusion[info["cible"]].values
    existantes.loc[masque, "ErreurAbsolue"] = (
        existantes.loc[masque, "Reel"] - existantes.loc[masque, "Prediction"]
    ).abs()

    return existantes


def _ajouter_nouvelle_prediction(cle_modele, existantes, nouvelle_prediction):
    info = MODELES[cle_modele]
    nouvelle_prediction = nouvelle_prediction.copy()
    nouvelle_prediction["Reel"] = pd.NA
    nouvelle_prediction["ErreurAbsolue"] = pd.NA

    colonnes_gardees = ["Date", "LiaisonId", "Prediction", "DateCalculPrediction", "Reel", "ErreurAbsolue"]
    if info["granularite"] == "horaire":
        colonnes_gardees.insert(2, "Heure")
    if info["famille"] == "composition" and info["colonne_categorie"] in nouvelle_prediction.columns:
        colonnes_gardees.insert(2, info["colonne_categorie"])

    nouvelle_prediction = nouvelle_prediction[colonnes_gardees]

    if existantes is None or existantes.empty:
        combine = nouvelle_prediction
    else:
        combine = pd.concat([existantes, nouvelle_prediction], ignore_index=True, sort=False)

    cles = ["Date", "LiaisonId"]
    if info["granularite"] == "horaire":
        cles.append("Heure")
    if info["famille"] == "composition" and info["colonne_categorie"] in combine.columns:
        cles.append(info["colonne_categorie"])

    combine = combine.drop_duplicates(subset=cles, keep="last").sort_values(cles)

    os.makedirs(PREDICTIONS_NOUVELLES, exist_ok=True)
    combine.to_parquet(_chemin_predictions_nouvelles(cle_modele), index=False)
    return combine


def _archiver_fichiers(chemins):
    correspondance = {
        DEPOT_QUOTIDIEN_VENTES: DEPOT_TRAITE_VENTES,
        DEPOT_QUOTIDIEN_CONTROLES: DEPOT_TRAITE_CONTROLES,
        DEPOT_QUOTIDIEN_CIRCULATION: DEPOT_TRAITE_CIRCULATION,
    }
    for chemin in chemins:
        dossier_source = os.path.dirname(chemin)
        dossier_cible = correspondance.get(dossier_source)
        if dossier_cible:
            os.makedirs(dossier_cible, exist_ok=True)
            shutil.move(chemin, os.path.join(dossier_cible, os.path.basename(chemin)))


def _ecrire_log(entree):
    os.makedirs(os.path.dirname(LOG_EXECUTION), exist_ok=True)
    journal = []
    if os.path.isfile(LOG_EXECUTION):
        with open(LOG_EXECUTION, "r") as fichier:
            journal = json.load(fichier)
    journal.append(entree)
    with open(LOG_EXECUTION, "w") as fichier:
        json.dump(journal, fichier, indent=2, default=str)


def traiter_date(date_texte):
    ventepda, controlepda, circulation, chemins = _charger_lot(date_texte)
    lots_agreges = agreger_lot_quotidien(ventepda, controlepda, circulation)

    for cle_modele, lignes in lots_agreges.items():
        _mettre_a_jour_historique(cle_modele, lignes)

    date_courante = pd.Timestamp(date_texte)
    date_suivante = date_courante + timedelta(days=1)

    colonnes_manquantes_totales = {}

    for cle_modele in MODELES:
        historique = pd.read_parquet(_chemin_historique(cle_modele))

        existantes = _reconcilier(cle_modele, date_texte, lots_agreges[cle_modele])

        nouvelle_prediction, colonnes_manquantes = predire_nouvelle_date(cle_modele, date_suivante, historique)
        if colonnes_manquantes:
            colonnes_manquantes_totales[cle_modele] = colonnes_manquantes

        _ajouter_nouvelle_prediction(cle_modele, existantes, nouvelle_prediction)

    _archiver_fichiers(chemins)

    return {
        "date_traitee": date_texte,
        "date_predite": date_suivante.strftime("%Y-%m-%d"),
        "colonnes_manquantes": colonnes_manquantes_totales,
    }


def executer():
    horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        try:
            from scripts.telecharger_depot import telecharger_nouveaux_fichiers
            telecharger_nouveaux_fichiers()
        except Exception:
            pass

        date_a_traiter = _prochaine_date_a_traiter()

        if date_a_traiter is None:
            _ecrire_log({
                "horodatage": horodatage,
                "statut": "aucune_donnee",
                "fichiers_traites": 0,
            })
            return

        resultat = traiter_date(date_a_traiter)
        _ecrire_log({
            "horodatage": horodatage,
            "statut": "succes",
            "fichiers_traites": 3,
            "date_traitee": resultat["date_traitee"],
            "date_predite": resultat["date_predite"],
            "colonnes_manquantes": resultat["colonnes_manquantes"],
        })

    except Exception as exception:
        _ecrire_log({
            "horodatage": horodatage,
            "statut": "erreur",
            "erreur": str(exception),
            "trace": traceback.format_exc(),
        })


if __name__ == "__main__":
    executer()
