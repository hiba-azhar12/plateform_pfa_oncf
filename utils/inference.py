import json
import os

import numpy as np
import pandas as pd
import psutil

from config.modeles import LAGS, FENETRES_ROLLING, MODELES, chemin_fichier, chemin_modele
from utils.feature_engineering import (
    ajouter_lags_rolling_calendaires,
    calculer_encodage_expanding,
    calculer_features_calendaires,
    calculer_interaction_jour,
    calculer_liaison_frequence,
)

CIBLES_TRAITEMENT = {
    "modele1_ventes": {"completes": [("ventes", "NbBillets")], "exogenes": []},
    "modele3_controles": {"completes": [("controles", "NbControles")], "exogenes": []},
    "modele2_taux_vente_guichet": {"completes": [("ventes", "NbBillets")], "exogenes": [("circulations", "NbCirculations")]},
    "modele5_taux_controle": {"completes": [("controles", "NbControles")], "exogenes": [("circulations", "NbCirculations")]},
    "modele6_taux_fraude": {"completes": [("fraudes", "NbFraudes")], "exogenes": [("controles", "NbControles")]},
    "modele4_part_confort": {"completes": [("ventes", "NbBillets")], "exogenes": []},
    "modele7_part_type": {"completes": [("controles", "NbControles")], "exogenes": []},
}

FENETRE_LAGS_JOURS = 420


def _afficher_ram(etiquette):
    print(f"[RAM] {etiquette} : {round(psutil.Process().memory_info().rss / 1e9, 2)} Go", flush=True)


def _lire_json(chemin):
    if not os.path.isfile(chemin):
        return None
    with open(chemin, "r") as fichier:
        return json.load(fichier)


def _lire_csv(chemin):
    if not os.path.isfile(chemin):
        return pd.DataFrame()
    return pd.read_csv(chemin)


def charger_colonnes_features(cle_modele):
    return _lire_json(chemin_fichier(cle_modele, "colonnes_features")) or []


def charger_encodage(cle_modele):
    encodage = _lire_csv(chemin_fichier(cle_modele, "encodage_liaison"))
    if not encodage.empty and "LiaisonId" in encodage.columns:
        encodage["LiaisonId"] = (
            encodage["LiaisonId"].astype(str).str.replace(r"\.0$", "", regex=True)
        )
    return encodage


def colonnes_groupe_liaison(cle_modele):
    info = MODELES[cle_modele]
    base = ["LiaisonId", "Heure"] if info["granularite"] == "horaire" else ["LiaisonId"]
    if info["famille"] == "composition":
        base = base + [info["colonne_categorie"]]
    return base


def colonnes_groupe_jour(cle_modele):
    info = MODELES[cle_modele]
    base = ["LiaisonId", "JourSemaine"]
    if info["famille"] == "composition":
        base = base + [info["colonne_categorie"]]
    return base


def generer_lignes_a_predire(cle_modele, date_cible, historique):
    colonnes_cles = colonnes_groupe_liaison(cle_modele)
    combinaisons = historique[colonnes_cles].drop_duplicates().reset_index(drop=True)
    combinaisons["Date"] = pd.Timestamp(date_cible)
    return combinaisons


def preparer_liaison_id(table, cle_modele, encodage):
    info = MODELES[cle_modele]
    table = table.copy()
    table["LiaisonId_reel"] = table["LiaisonId"].astype(str)

    if info["format_modele"] == "catboost":
        table["LiaisonId"] = table["LiaisonId"].map(str)
        return table, []

    if encodage.empty or "LiaisonId" not in encodage.columns:
        codes_factorises, _ = pd.factorize(table["LiaisonId"].astype(str))
        codes = pd.Series(codes_factorises, index=table.index).astype("Int32")
    else:
        mapping = dict(zip(encodage["LiaisonId"].astype(str), encodage["Code"]))
        codes = table["LiaisonId"].astype(str).map(mapping).astype("Int32")

    masque_connu = codes.notna()
    liaisons_inconnues = sorted(table.loc[~masque_connu, "LiaisonId"].astype(str).unique().tolist())

    table = table.loc[masque_connu].copy()
    codes = codes.loc[masque_connu]

    if info["multi_categorie"]:
        table["LiaisonId_code"] = codes.astype("int32")
    else:
        table["LiaisonId"] = codes.astype("int32")
    return table, liaisons_inconnues


def construire_features(cle_modele, date_cible, historique):
    info = MODELES[cle_modele]
    traitement = CIBLES_TRAITEMENT[cle_modele]
    groupe_liaison = colonnes_groupe_liaison(cle_modele)
    groupe_jour = colonnes_groupe_jour(cle_modele)

    _afficher_ram(f"{cle_modele} - debut construire_features")

    lignes_base = generer_lignes_a_predire(cle_modele, date_cible, historique)

    frequences = calculer_liaison_frequence(historique, ["LiaisonId"])
    table_frequence = historique[["LiaisonId"]].copy()
    table_frequence["liaison_frequence"] = frequences
    table_frequence = table_frequence.drop_duplicates("LiaisonId")
    lignes_base = lignes_base.merge(table_frequence, on="LiaisonId", how="left")

    toutes_cibles = traitement["completes"] + traitement["exogenes"]
    for _, colonne_valeur in toutes_cibles:
        if colonne_valeur not in lignes_base.columns:
            lignes_base[colonne_valeur] = np.nan

    historique_etendu = pd.concat([historique, lignes_base], ignore_index=True, sort=False)
    historique_etendu = historique_etendu.sort_values(groupe_liaison + ["Date"]).reset_index(drop=True)
    historique_etendu["JourSemaine"] = pd.to_datetime(historique_etendu["Date"]).dt.dayofweek
    _afficher_ram(f"{cle_modele} - apres concat historique complet")

    for nom_suffixe, colonne_valeur in traitement["completes"]:
        historique_etendu[f"liaison_cible_encodage_{nom_suffixe}"] = calculer_encodage_expanding(
            historique_etendu, colonne_valeur, groupe_liaison
        )
        historique_etendu[f"interaction_jour_liaison_{nom_suffixe}"] = calculer_interaction_jour(
            historique_etendu, colonne_valeur, groupe_jour
        )
    _afficher_ram(f"{cle_modele} - apres encodage et interaction (historique complet)")

    date_limite = pd.Timestamp(date_cible) - pd.Timedelta(days=FENETRE_LAGS_JOURS)
    fenetre_recente = historique_etendu[historique_etendu["Date"] >= date_limite].reset_index(drop=True)
    del historique_etendu
    _afficher_ram(f"{cle_modele} - apres restriction fenetre {FENETRE_LAGS_JOURS}j")

    for nom_suffixe, colonne_valeur in toutes_cibles:
        fenetre_recente = ajouter_lags_rolling_calendaires(
            fenetre_recente, colonne_valeur, groupe_liaison, LAGS, FENETRES_ROLLING, nom_suffixe=nom_suffixe
        )
        _afficher_ram(f"{cle_modele} - apres lags_rolling_calendaires {nom_suffixe}")

    masque_nouvelles_lignes = fenetre_recente["Date"] == pd.Timestamp(date_cible)
    table = fenetre_recente[masque_nouvelles_lignes].copy()
    del fenetre_recente

    if "Heure" in table.columns:
        table["Heure"] = table["Heure"].astype(int)

    for nom_suffixe, colonne_valeur in traitement["exogenes"]:
        valeur_proxy = table[f"lag_1_{nom_suffixe}"]
        table[colonne_valeur] = valeur_proxy
        table[f"log_offset_{nom_suffixe}"] = np.log1p(valeur_proxy.clip(lower=0))

    denominateur = info.get("cible_denominateur")
    if denominateur is not None:
        suffixe_denominateur = next(
            (suffixe for suffixe, colonne in traitement["completes"] if colonne == denominateur),
            None,
        )
        if suffixe_denominateur is not None:
            valeur_proxy = table[f"lag_1_{suffixe_denominateur}"]
            table[denominateur] = valeur_proxy
            table[f"log_offset_{suffixe_denominateur}"] = np.log1p(valeur_proxy.clip(lower=0))

    avec_heure = "Heure" in table.columns
    calendaires = calculer_features_calendaires(
        table["Date"], avec_heure=avec_heure, heures=table["Heure"] if avec_heure else None
    )
    colonnes_calendaires_a_ajouter = [c for c in calendaires.columns if c not in ("Date", "Heure")]
    table = table.reset_index(drop=True)
    table[colonnes_calendaires_a_ajouter] = calendaires[colonnes_calendaires_a_ajouter].reset_index(drop=True)

    encodage = charger_encodage(cle_modele)
    table, liaisons_inconnues = preparer_liaison_id(table, cle_modele, encodage)

    colonnes_attendues = charger_colonnes_features(cle_modele)
    colonnes_manquantes = [colonne for colonne in colonnes_attendues if colonne not in table.columns]
    for colonne in colonnes_manquantes:
        table[colonne] = np.nan

    _afficher_ram(f"{cle_modele} - fin construire_features")
    return table, colonnes_attendues, colonnes_manquantes, liaisons_inconnues


def charger_modele_simple(cle_modele):
    info = MODELES[cle_modele]
    chemin = chemin_modele(cle_modele)
    if info["format_modele"] == "catboost":
        from catboost import CatBoostRegressor
        modele = CatBoostRegressor()
        modele.load_model(chemin)
        return modele
    import lightgbm as lgb
    return lgb.Booster(model_file=chemin)


def charger_modeles_categorie(cle_modele):
    info = MODELES[cle_modele]
    mapping = _lire_json(os.path.join(info["dossier"], info["mapping_modeles"])) or {}
    import lightgbm as lgb

    modeles = {}
    for categorie, nom_fichier in mapping.items():
        chemin = os.path.join(info["dossier"], info["dossier_modeles"], nom_fichier)
        modeles[categorie] = lgb.Booster(model_file=chemin)
    return modeles


def predire(cle_modele, table_features, colonnes_attendues):
    info = MODELES[cle_modele]

    if info["multi_categorie"]:
        modeles = charger_modeles_categorie(cle_modele)
        parties = []
        for categorie, modele in modeles.items():
            sous = table_features[table_features[info["colonne_categorie"]].astype(str) == str(categorie)]
            if sous.empty:
                continue
            predictions_brutes = np.clip(modele.predict(sous[colonnes_attendues]), 0, None)
            parties.append(sous.assign(PredictionBrute=predictions_brutes))

        if not parties:
            table_features["Prediction"] = np.nan
            resultat = table_features
        else:
            complet = pd.concat(parties).reset_index(drop=True)
            sommes = complet.groupby(["Date", "LiaisonId"])["PredictionBrute"].transform("sum")
            complet["Prediction"] = np.where(sommes > 0, complet["PredictionBrute"] / sommes, 0.0)
            resultat = complet.drop(columns=["PredictionBrute"])
    else:
        modele = charger_modele_simple(cle_modele)
        predictions = np.clip(modele.predict(table_features[colonnes_attendues]), 0, None)

        if info["famille"] == "taux":
            predictions = np.clip(predictions, 0, 1)

        resultat = table_features.copy()
        resultat["Prediction"] = predictions

    if "LiaisonId_reel" in resultat.columns:
        resultat["LiaisonId"] = resultat["LiaisonId_reel"]
        resultat = resultat.drop(columns=["LiaisonId_reel"])
    if "LiaisonId_code" in resultat.columns:
        resultat = resultat.drop(columns=["LiaisonId_code"])

    return resultat


def predire_nouvelle_date(cle_modele, date_cible, historique):
    table, colonnes_attendues, colonnes_manquantes, liaisons_inconnues = construire_features(cle_modele, date_cible, historique)
    resultat = predire(cle_modele, table, colonnes_attendues)
    resultat["DateCalculPrediction"] = pd.Timestamp.now().normalize()
    return resultat, colonnes_manquantes, liaisons_inconnues