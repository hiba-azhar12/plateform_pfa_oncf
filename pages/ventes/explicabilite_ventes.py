import streamlit as st

from utils.composants import afficher_explicabilite_modele
from utils.style import entete

entete("Explicabilité Ventes", "Importance des variables et analyse des erreurs par modèle")

onglet_billets, onglet_taux, onglet_confort = st.tabs([
    "Billets vendus", "Taux de ventes PDA", "Répartition par confort",
])

with onglet_billets:
    afficher_explicabilite_modele("modele1_ventes")

with onglet_taux:
    afficher_explicabilite_modele("modele2_taux_vente_guichet")

with onglet_confort:
    afficher_explicabilite_modele("modele4_part_confort")