import streamlit as st

from utils.composants import afficher_anomalies_modele
from utils.style import entete

entete("Anomalies Ventes", "Écarts significatifs entre réel et prédiction sur les trois modèles de ventes")

onglet_billets, onglet_taux, onglet_confort = st.tabs([
    "Billets vendus", "Taux de ventes guichet", "Répartition par confort",
])

with onglet_billets:
    afficher_anomalies_modele("modele1_ventes")

with onglet_taux:
    afficher_anomalies_modele("modele2_taux_vente_guichet")

with onglet_confort:
    afficher_anomalies_modele("modele4_part_confort")
