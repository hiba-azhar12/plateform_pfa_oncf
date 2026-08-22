import gc
import json
import os
import re
import shutil
import sys
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import psutil

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
from config.modeles import HORIZONS_RECURSIFS, HORIZONS_DEDIES, MODELES, MODELES_HORIZON_DEDIE
from utils.agregation import agreger_lot_quotidien
from utils.inference import predire_horizon_dedie, predire_horizons_recursifs
from utils.temps import horodatage_maroc

MOTIF_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")

ID_DECLENCHEMENT = None


def _afficher_ram(etiquette):
    print(f"[RAM] {etiquette} : {round(psutil.Process().memory_info().rss / 1e9, 2)} Go", flush=True)


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


def _derniere_date_traitee():
    dates_ventes = set(_dates_disponibles(DEPOT_TRAITE_VENTES, "ventes_"))
    dates_controles = set(_dates_disponibles(DEPOT_TRAITE_CONTROLES, "controles_"))
    dates_circulation = set(_dates_disponibles(DEPOT_TRAITE_CIRCULATION, "circulation_"))

    dates_completes = dates_ventes & dates_controles & dates_circulation
    if not dates_completes:
        return None
    return sorted(dates_completes)[-1]


def _valider_colonnes(df, colonnes_attendues, nom_fichier):
    manquantes = [colonne for colonne in colonnes_attendues if colonne not in df.columns]
    if manquantes:
        raise ValueError(f"Colonnes manquantes dans {nom_fichier} : {manquantes}")


def _chemin_source(dossier_quotidien, dossier_traite, nom_fichier):
    chemin_quotidien = os.path.join(dossier_quotidien, nom_fichier)
    if os.path.isfile(chemin_quotidien):
        return chemin_quotidien
    return os.path.join(dossier_traite, nom_fichier)


def _charger_lot(date_texte):
    chemin_ventes = _chemin_source(DEPOT_QUOTIDIEN_VENTES, DEPOT_TRAITE_VENTES, f"ventes_{date_texte}.csv")
    chemin_controles = _chemin_source(DEPOT_QUOTIDIEN_CONTROLES, DEPOT_TRAITE_CONTROLES, f"controles_{date_texte}.csv")
    chemin_circulation = _chemin_source(DEPOT_QUOTIDIEN_CIRCULATION, DEPOT_TRAITE_CIRCULATION, f"circulation_{date_texte}.csv")

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


def _derniere_date_historique():
    dates_max = []
    for cle_modele in MODELES:
        chemin = _chemin_historique(cle_modele)
        if not os.path.isfile(chemin):
            continue
        historique = pd.read_parquet(chemin, columns=["Date"])
        if not historique.empty:
            dates_max.append(pd.to_datetime(historique["Date"]).max())
    if not dates_max:
        return None
    return min(dates_max).date()


def _verifier_continuite(date_texte):
    derniere_date = _derniere_date_historique()
    if derniere_date is None:
        return None
    date_objet = datetime.strptime(date_texte, "%Y-%m-%d").date()
    date_attendue = derniere_date + timedelta(days=1)
    if date_objet != date_attendue:
        return (
            f"Date traitee ({date_texte}) differente de la date attendue "
            f"({date_attendue.isoformat()}) d'apres l'historique existant (dernier jour connu : "
            f"{derniere_date.isoformat()}). Verifiez les fichiers deposes avant de continuer."
        )
    return None


def _aligner_types(nouvelles_lignes, historique):
    nouvelles_lignes = nouvelles_lignes.copy()
    for colonne in nouvelles_lignes.columns:
        if colonne not in historique.columns:
            continue
        dtype_historique = historique[colonne].dtype
        if nouvelles_lignes[colonne].dtype == dtype_historique:
            continue
        if isinstance(dtype_historique, pd.CategoricalDtype):
            continue
        try:
            nouvelles_lignes[colonne] = nouvelles_lignes[colonne].astype(dtype_historique)
        except (ValueError, TypeError):
            pass
    return nouvelles_lignes


def _mettre_a_jour_historique(cle_modele, nouvelles_lignes):
    chemin = _chemin_historique(cle_modele)
    os.makedirs(HISTORIQUE, exist_ok=True)

    if os.path.isfile(chemin):
        historique = pd.read_parquet(chemin)
        nouvelles_lignes = _aligner_types(nouvelles_lignes, historique)
        combine = pd.concat([historique, nouvelles_lignes], ignore_index=True, sort=False)
        del historique
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


def _cles_dedoublonnage(cle_modele, table):
    info = MODELES[cle_modele]
    cles = ["Date", "LiaisonId"]
    if info["granularite"] == "horaire":
        cles.append("Heure")
    if info["famille"] == "composition" and info["colonne_categorie"] in table.columns:
        cles.append(info["colonne_categorie"])
    if "Horizon" in table.columns:
        cles.append("Horizon")
    return cles


def _ecrire_predictions_nouvelles(cle_modele, table):
    table = table.copy()
    if "Horizon" not in table.columns:
        table["Horizon"] = 1
    table["Horizon"] = pd.to_numeric(table["Horizon"], errors="coerce").fillna(1).astype(int)

    cles = _cles_dedoublonnage(cle_modele, table)
    table = table.drop_duplicates(subset=cles, keep="last").sort_values(cles)
    os.makedirs(PREDICTIONS_NOUVELLES, exist_ok=True)
    table.to_parquet(_chemin_predictions_nouvelles(cle_modele), index=False)
    return table


def _ajouter_nouvelle_prediction(cle_modele, existantes, nouvelles_predictions):
    info = MODELES[cle_modele]
    nouvelles_predictions = nouvelles_predictions.copy()
    nouvelles_predictions["Reel"] = pd.NA
    nouvelles_predictions["ErreurAbsolue"] = pd.NA

    colonnes_gardees = ["Date", "LiaisonId", "Prediction", "DateCalculPrediction", "DateAncrage", "Horizon", "Reel", "ErreurAbsolue"]
    if info["granularite"] == "horaire":
        colonnes_gardees.insert(2, "Heure")
    if info["famille"] == "composition" and info["colonne_categorie"] in nouvelles_predictions.columns:
        colonnes_gardees.insert(2, info["colonne_categorie"])

    nouvelles_predictions = nouvelles_predictions[colonnes_gardees]

    if existantes is None or existantes.empty:
        combine = nouvelles_predictions
    else:
        combine = pd.concat([existantes, nouvelles_predictions], ignore_index=True, sort=False)

    return _ecrire_predictions_nouvelles(cle_modele, combine)


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
    if ID_DECLENCHEMENT:
        entree = {**entree, "id_declenchement": ID_DECLENCHEMENT}
    os.makedirs(os.path.dirname(LOG_EXECUTION), exist_ok=True)
    journal = []
    if os.path.isfile(LOG_EXECUTION):
        with open(LOG_EXECUTION, "r") as fichier:
            journal = json.load(fichier)
    journal.append(entree)
    with open(LOG_EXECUTION, "w") as fichier:
        json.dump(journal, fichier, indent=2, default=str)


def _predire_toutes_les_horizons(cle_modele, historique):
    predictions = []
    colonnes_manquantes_modele = {}
    liaisons_inconnues_modele = {}

    resultats_recursifs = predire_horizons_recursifs(cle_modele, HORIZONS_RECURSIFS, historique)
    for horizon, (resultat, colonnes_manquantes, liaisons_inconnues) in resultats_recursifs.items():
        if colonnes_manquantes:
            colonnes_manquantes_modele[horizon] = colonnes_manquantes
        if liaisons_inconnues:
            liaisons_inconnues_modele[horizon] = liaisons_inconnues
        predictions.append(resultat)
    del resultats_recursifs
    gc.collect()

    if cle_modele in MODELES_HORIZON_DEDIE:
        for horizon in HORIZONS_DEDIES:
            resultat, colonnes_manquantes, liaisons_inconnues = predire_horizon_dedie(cle_modele, horizon, historique)
            if colonnes_manquantes:
                colonnes_manquantes_modele[horizon] = colonnes_manquantes
            if liaisons_inconnues:
                liaisons_inconnues_modele[horizon] = liaisons_inconnues
            predictions.append(resultat)
            gc.collect()

    toutes_predictions = pd.concat(predictions, ignore_index=True, sort=False)
    del predictions
    return toutes_predictions, colonnes_manquantes_modele, liaisons_inconnues_modele


def traiter_date(date_texte, retraitement=False):
    _afficher_ram("debut traiter_date")
    alerte_continuite = None if retraitement else _verifier_continuite(date_texte)
    ventepda, controlepda, circulation, chemins = _charger_lot(date_texte)
    lots_agreges = agreger_lot_quotidien(ventepda, controlepda, circulation)
    del ventepda, controlepda, circulation
    _afficher_ram("apres agregation lot quotidien")

    for cle_modele in list(lots_agreges.keys()):
        lots_agreges[cle_modele] = _valeur_reelle_observee(cle_modele, lots_agreges[cle_modele])
        _mettre_a_jour_historique(cle_modele, lots_agreges[cle_modele])
    _afficher_ram("apres mise a jour historique")

    date_courante = pd.Timestamp(date_texte)
    date_suivante = date_courante + timedelta(days=1)

    colonnes_manquantes_totales = {}
    liaisons_inconnues_totales = {}
    erreurs_modeles = {}

    for cle_modele in MODELES:
        existantes = None
        try:
            existantes = _reconcilier(cle_modele, date_texte, lots_agreges[cle_modele])
            existantes = _ecrire_predictions_nouvelles(cle_modele, existantes)
        except Exception as exception:
            erreurs_modeles[cle_modele] = f"reconciliation : {exception}"
            continue

        try:
            historique = pd.read_parquet(_chemin_historique(cle_modele))

            toutes_predictions, colonnes_manquantes_modele, liaisons_inconnues_modele = _predire_toutes_les_horizons(
                cle_modele, historique
            )
            if colonnes_manquantes_modele:
                colonnes_manquantes_totales[cle_modele] = colonnes_manquantes_modele
            if liaisons_inconnues_modele:
                liaisons_inconnues_totales[cle_modele] = liaisons_inconnues_modele

            _ajouter_nouvelle_prediction(cle_modele, existantes, toutes_predictions)
            del historique, toutes_predictions
            gc.collect()
            _afficher_ram(f"{cle_modele} - fin boucle")
        except Exception as exception:
            erreurs_modeles[cle_modele] = f"prediction : {exception}"
        finally:
            del existantes
            gc.collect()

    _archiver_fichiers(chemins)
    _afficher_ram("fin traiter_date")

    return {
        "date_traitee": date_texte,
        "date_predite": date_suivante.strftime("%Y-%m-%d"),
        "horizons_recursifs": HORIZONS_RECURSIFS,
        "horizons_dedies": HORIZONS_DEDIES,
        "colonnes_manquantes": colonnes_manquantes_totales,
        "liaisons_inconnues": liaisons_inconnues_totales,
        "erreurs_modeles": erreurs_modeles,
        "alerte_continuite": alerte_continuite,
    }


def executer():
    _ecrire_log({"horodatage": horodatage_maroc(), "statut": "en_cours"})

    try:
        try:
            from scripts.telecharger_depot import telecharger_nouveaux_fichiers
            telecharger_nouveaux_fichiers()
        except Exception:
            pass

        date_a_traiter = _prochaine_date_a_traiter()
        retraitement = False

        if date_a_traiter is None:
            date_a_traiter = _derniere_date_traitee()
            retraitement = True

        if date_a_traiter is None:
            _ecrire_log({
                "horodatage": horodatage_maroc(),
                "statut": "aucune_donnee",
                "fichiers_traites": 0,
            })
            return

        resultat = traiter_date(date_a_traiter, retraitement=retraitement)
        _ecrire_log({
            "horodatage": horodatage_maroc(),
            "statut": "succes" if not resultat["erreurs_modeles"] else "succes_partiel",
            "fichiers_traites": 3,
            "retraitement": retraitement,
            "date_traitee": resultat["date_traitee"],
            "date_predite": resultat["date_predite"],
            "colonnes_manquantes": resultat["colonnes_manquantes"],
            "liaisons_inconnues": resultat["liaisons_inconnues"],
            "erreurs_modeles": resultat["erreurs_modeles"],
            "alerte_continuite": resultat["alerte_continuite"],
        })

    except Exception as exception:
        _ecrire_log({
            "horodatage": horodatage_maroc(),
            "statut": "erreur",
            "erreur": str(exception),
            "trace": traceback.format_exc(),
        })


if __name__ == "__main__":
    import argparse

    analyseur = argparse.ArgumentParser()
    analyseur.add_argument("--id-declenchement", default=None)
    arguments = analyseur.parse_args()

    ID_DECLENCHEMENT = arguments.id_declenchement

    executer()