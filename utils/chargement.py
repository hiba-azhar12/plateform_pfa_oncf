import json
import os

import pandas as pd
import streamlit as st

from config.modeles import MODELES, chemin_fichier


def _existe(chemin):
    return os.path.isfile(chemin)


@st.cache_data(show_spinner=False)
def charger_json(cle_modele, cle_fichier):
    chemin = chemin_fichier(cle_modele, cle_fichier)
    if not _existe(chemin):
        return None
    with open(chemin, "r") as fichier:
        return json.load(fichier)


@st.cache_data(show_spinner=False)
def charger_csv(cle_modele, cle_fichier):
    chemin = chemin_fichier(cle_modele, cle_fichier)
    if not _existe(chemin):
        return pd.DataFrame()
    return pd.read_csv(chemin)


@st.cache_data(show_spinner=False)
def charger_parquet(cle_modele, cle_fichier):
    chemin = chemin_fichier(cle_modele, cle_fichier)
    if not _existe(chemin):
        return pd.DataFrame()
    return pd.read_parquet(chemin)


def charger_metriques(cle_modele):
    return charger_json(cle_modele, "metriques") or {}


def charger_predictions(cle_modele):
    return charger_parquet(cle_modele, "predictions")


def charger_historique(cle_modele):
    return charger_parquet(cle_modele, "historique")


@st.cache_data(show_spinner=False, ttl=60)
def charger_predictions_completes(cle_modele):
    info = MODELES[cle_modele]
    test = charger_predictions(cle_modele)

    nouvelles = charger_predictions_nouvelles(cle_modele)
    if nouvelles.empty:
        return test

    nouvelles = nouvelles.copy()
    nouvelles["Date"] = pd.to_datetime(nouvelles["Date"])
    nouvelles["Reel"] = pd.to_numeric(nouvelles["Reel"], errors="coerce")
    reconciliees = nouvelles.dropna(subset=["Reel"])
    if reconciliees.empty:
        return test

    cible = info["cible"]
    colonne_categorie = info["colonne_categorie"]

    reconciliees = reconciliees.rename(columns={"Reel": cible})
    reconciliees["LiaisonId"] = reconciliees["LiaisonId"].astype(str)
    reconciliees["ErreurAbsolue"] = pd.to_numeric(reconciliees["ErreurAbsolue"], errors="coerce")
    reconciliees["JourSemaine"] = reconciliees["Date"].dt.dayofweek

    colonnes = ["Date", "LiaisonId"]
    if info["granularite"] == "horaire":
        colonnes.append("Heure")
    if colonne_categorie:
        colonnes.append(colonne_categorie)
    colonnes += [cible, "Prediction", "ErreurAbsolue", "JourSemaine"]
    reconciliees = reconciliees[[colonne for colonne in colonnes if colonne in reconciliees.columns]]

    if test.empty:
        combine = reconciliees
    else:
        test = test.copy()
        test["Date"] = pd.to_datetime(test["Date"])
        test["LiaisonId"] = test["LiaisonId"].astype(str)
        combine = pd.concat([test, reconciliees], ignore_index=True, sort=False)

    cles = ["Date", "LiaisonId"]
    if info["granularite"] == "horaire":
        cles.append("Heure")
    if colonne_categorie:
        cles.append(colonne_categorie)

    combine = combine.drop_duplicates(subset=cles, keep="last").sort_values(cles).reset_index(drop=True)
    return combine


def charger_anomalies(cle_modele):
    return charger_csv(cle_modele, "anomalies")


def charger_seuil_anomalie(cle_modele):
    return charger_json(cle_modele, "seuil_anomalie") or {}


def charger_importance_features(cle_modele):
    return charger_csv(cle_modele, "importance_features")


def charger_importance_shap(cle_modele):
    return charger_csv(cle_modele, "importance_shap")


def charger_saisonnalite(cle_modele):
    return charger_csv(cle_modele, "saisonnalite")


def charger_calendrier_quotidien(cle_modele):
    return charger_csv(cle_modele, "calendrier_quotidien")


@st.cache_data(show_spinner=False, ttl=60)
def charger_calendrier_quotidien_dynamique(cle_modele):
    """Reconstruit le calendrier quotidien des ecarts (Prediction - Reel) a partir
    des predictions completes (jeu de test + predictions nouvelles reconciliees),
    au lieu du CSV fige genere une seule fois pendant la modelisation."""
    info = MODELES[cle_modele]
    cible = info["cible"]
    predictions = charger_predictions_completes(cle_modele)
    if predictions.empty or cible not in predictions.columns or "Prediction" not in predictions.columns:
        return pd.DataFrame()

    predictions = predictions.copy()
    predictions["Date"] = pd.to_datetime(predictions["Date"])
    fonction_agg = "sum" if info["famille"] == "comptages" else "mean"

    agrege = (
        predictions.dropna(subset=[cible])
        .groupby("Date", as_index=False)
        .agg({cible: fonction_agg, "Prediction": fonction_agg})
    )
    agrege["Ecart"] = agrege["Prediction"] - agrege[cible]
    return agrege[["Date", "Ecart"]].sort_values("Date").reset_index(drop=True)


def charger_comparaison_inter_annees(cle_modele):
    return charger_csv(cle_modele, "comparaison_inter_annees")


@st.cache_data(show_spinner=False, ttl=60)
def charger_comparaison_inter_annees_dynamique(cle_modele):
    """Reconstruit la comparaison inter-annees a partir de l'historique complet
    (donnees de modelisation + depots quotidiens traites), au lieu du CSV fige
    genere une seule fois pendant la modelisation. Cache 60s : reflete les
    nouveaux depots automatiquement, sans redemarrage de l'application.

    Ne lit que les colonnes Date + cible directement depuis le parquet (et non
    charger_historique_complet, qui charge toutes les colonnes) : certains
    historiques dépassent 20 millions de lignes, et charger toutes les
    colonnes pour plusieurs modèles à la fois épuise la RAM disponible."""
    from config.chemins import HISTORIQUE

    cible = MODELES[cle_modele]["cible"]
    chemin = os.path.join(HISTORIQUE, f"{cle_modele}.parquet")
    if not _existe(chemin):
        return pd.DataFrame()

    try:
        historique = pd.read_parquet(chemin, columns=["Date", cible])
    except (ValueError, KeyError):
        historique = charger_historique_complet(cle_modele)
        if not historique.empty:
            historique = historique[["Date", cible]] if cible in historique.columns else pd.DataFrame()

    if historique.empty or cible not in historique.columns:
        return pd.DataFrame()

    historique["Date"] = pd.to_datetime(historique["Date"])
    historique["Annee"] = historique["Date"].dt.year
    historique["Mois"] = historique["Date"].dt.month

    fonction_agg = "sum" if MODELES[cle_modele]["famille"] == "comptages" else "mean"
    resultat = historique.groupby(["Annee", "Mois"], as_index=False)[cible].agg(fonction_agg)
    del historique
    return resultat.sort_values(["Annee", "Mois"]).reset_index(drop=True)


def charger_encodage_liaison(cle_modele):
    return charger_csv(cle_modele, "encodage_liaison")


def _liaisons_propres(colonne):
    """Convertit une colonne LiaisonId (ou une colonne de categorie) en liste
    de str triable, en filtrant les valeurs manquantes et en forcant
    explicitement le type via map(str) (plus robuste que .astype(str) face
    aux NaN/valeurs mixtes qui provoquaient le TypeError du chatbot)."""
    valeurs = colonne.dropna().map(str).unique().tolist()
    return sorted(valeurs, key=str)


def liste_liaisons(cle_modele):
    try:
        encodage = charger_encodage_liaison(cle_modele)
        if encodage.empty or "LiaisonId" not in encodage.columns:
            historique = charger_historique(cle_modele)
            if historique.empty or "LiaisonId" not in historique.columns:
                return []
            return _liaisons_propres(historique["LiaisonId"])
        return _liaisons_propres(encodage["LiaisonId"])
    except Exception:
        # Un modele avec des donnees corrompues ne doit pas faire planter
        # toute la page chatbot (qui boucle sur tous les modeles).
        return []


def liste_categories(cle_modele):
    try:
        info = MODELES[cle_modele]
        if not info["multi_categorie"]:
            return []
        historique = charger_historique(cle_modele)
        colonne = info["colonne_categorie"]
        if historique.empty or colonne not in historique.columns:
            return []
        return _liaisons_propres(historique[colonne])
    except Exception:
        return []


def modele_dispose_de_donnees(cle_modele):
    return _existe(chemin_fichier(cle_modele, "metriques"))


@st.cache_data(show_spinner=False)
def liaisons_ordonnees_par_frequence(cle_modele):
    predictions = charger_predictions(cle_modele)
    if predictions.empty or "LiaisonId" not in predictions.columns:
        return []
    cible = MODELES[cle_modele]["cible"]
    liaisons = predictions["LiaisonId"].astype(str)
    if cible not in predictions.columns:
        return sorted(liaisons.unique().tolist())
    frequence = predictions.assign(LiaisonId=liaisons).groupby("LiaisonId")[cible].sum()
    return frequence.sort_values(ascending=False).index.tolist()


@st.cache_data(show_spinner=False)
def liaisons_ordonnees_nouvelles_predictions(cle_modele):
    predictions = charger_predictions_nouvelles(cle_modele)
    if predictions.empty or "LiaisonId" not in predictions.columns:
        return []
    colonne_volume = "Reel" if "Reel" in predictions.columns else "Prediction"
    liaisons = predictions["LiaisonId"].astype(str)
    frequence = predictions.assign(LiaisonId=liaisons).groupby("LiaisonId")[colonne_volume].sum()
    return frequence.sort_values(ascending=False).index.tolist()


@st.cache_data(show_spinner=False, ttl=60)
def charger_predictions_nouvelles(cle_modele):
    from config.chemins import PREDICTIONS_NOUVELLES

    chemin = os.path.join(PREDICTIONS_NOUVELLES, f"{cle_modele}.parquet")
    if not _existe(chemin):
        return pd.DataFrame()
    return pd.read_parquet(chemin)


@st.cache_data(show_spinner=False, ttl=60)
def charger_historique_complet(cle_modele):
    from config.chemins import HISTORIQUE

    chemin = os.path.join(HISTORIQUE, f"{cle_modele}.parquet")
    if not _existe(chemin):
        return pd.DataFrame()
    return pd.read_parquet(chemin)


@st.cache_data(show_spinner=False, ttl=60)
def charger_log_execution():
    from config.chemins import LOG_EXECUTION

    if not _existe(LOG_EXECUTION):
        return []
    with open(LOG_EXECUTION, "r") as fichier:
        return json.load(fichier)


def dernier_log_execution():
    journal = charger_log_execution()
    entrees_pipeline = [
        entree for entree in journal
        if isinstance(entree, dict) and entree.get("type") != "reentrainement"
    ]
    if not entrees_pipeline:
        return None
    return entrees_pipeline[-1]


@st.cache_data(show_spinner=False, ttl=60)
def charger_journal_reentrainements():
    journal = charger_log_execution()
    return [entree for entree in journal if isinstance(entree, dict) and entree.get("type") == "reentrainement"]