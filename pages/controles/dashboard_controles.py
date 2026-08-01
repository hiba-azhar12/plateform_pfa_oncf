import streamlit as st

from utils.composants import afficher_dashboard_modele
from utils.style import entete

entete("Dashboard Contrôles", "Suivi réel contre prédiction pour les contrôles, le taux de contrôle, la fraude et la répartition par titre")

onglet_controles, onglet_taux, onglet_fraude, onglet_type = st.tabs([
    "Billets contrôlés", "Taux de contrôle", "Taux de fraude", "Répartition par type de titre",
])

with onglet_controles:
    afficher_dashboard_modele("modele3_controles")

with onglet_taux:
    afficher_dashboard_modele("modele5_taux_controle")

with onglet_fraude:
    afficher_dashboard_modele("modele6_taux_fraude", mettre_en_avant_fraude=True)

with onglet_type:
    afficher_dashboard_modele("modele7_part_type")
