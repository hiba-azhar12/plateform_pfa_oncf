import streamlit as st

from utils.composants import afficher_anomalies_modele
from utils.style import entete

entete("Anomalies Contrôles", "Écarts significatifs entre réel et prédiction sur les quatre modèles de contrôle")

onglet_controles, onglet_taux, onglet_fraude, onglet_type = st.tabs([
    "Billets contrôlés", "Taux de contrôle", "Taux de fraude", "Répartition par type de titre",
])

with onglet_controles:
    afficher_anomalies_modele("modele3_controles")

with onglet_taux:
    afficher_anomalies_modele("modele5_taux_controle")

with onglet_fraude:
    afficher_anomalies_modele("modele6_taux_fraude")

with onglet_type:
    afficher_anomalies_modele("modele7_part_type")
