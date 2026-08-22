import streamlit as st

from utils.composants import afficher_dashboard_modele
from utils.style import entete

entete("Dashboard Ventes", "Suivi réel contre prédiction pour les billets, le taux de vente PDA et la répartition par confort")

onglet_billets, onglet_taux, onglet_confort = st.tabs([
    "Billets vendus", "Taux de ventes PDA", "Répartition par confort",
])

with onglet_billets:
    afficher_dashboard_modele("modele1_ventes")

with onglet_taux:
    afficher_dashboard_modele("modele2_taux_vente_guichet")

with onglet_confort:
    afficher_dashboard_modele("modele4_part_confort")