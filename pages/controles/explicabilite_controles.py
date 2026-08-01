import streamlit as st

from utils.composants import afficher_explicabilite_modele
from utils.style import entete

entete("Explicabilité Contrôles", "Importance des variables et analyse des erreurs par modèle")

onglet_controles, onglet_taux, onglet_fraude, onglet_type = st.tabs([
    "Billets contrôlés", "Taux de contrôle", "Taux de fraude", "Répartition par type de titre",
])

with onglet_controles:
    afficher_explicabilite_modele("modele3_controles")

with onglet_taux:
    afficher_explicabilite_modele("modele5_taux_controle")

with onglet_fraude:
    afficher_explicabilite_modele("modele6_taux_fraude")

with onglet_type:
    afficher_explicabilite_modele("modele7_part_type")
