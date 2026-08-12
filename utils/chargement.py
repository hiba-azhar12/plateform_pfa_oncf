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


def charger_comparaison_inter_annees(cle_modele):
    return charger_csv(cle_modele, "comparaison_inter_annees")


def charger_encodage_liaison(cle_modele):
    return charger_csv(cle_modele, "encodage_liaison")


def liste_liaisons(cle_modele):
    encodage = charger_encodage_liaison(cle_modele)
    if encodage.empty or "LiaisonId" not in encodage.columns:
        historique = charger_historique(cle_modele)
        if historique.empty or "LiaisonId" not in historique.columns:
            return []
        return sorted(historique["LiaisonId"].astype(str).unique().tolist())
    return sorted(encodage["LiaisonId"].astype(str).unique().tolist())


def liste_categories(cle_modele):
    info = MODELES[cle_modele]
    if not info["multi_categorie"]:
        return []
    historique = charger_historique(cle_modele)
    colonne = info["colonne_categorie"]
    if historique.empty or colonne not in historique.columns:
        return []
    return sorted(historique[colonne].astype(str).unique().tolist())


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


@st.cache_data(show_spinner=False)
def charger_predictions_nouvelles(cle_modele):
    from config.chemins import PREDICTIONS_NOUVELLES

    chemin = os.path.join(PREDICTIONS_NOUVELLES, f"{cle_modele}.parquet")
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
    if not journal:
        return None
    return journal[-1]