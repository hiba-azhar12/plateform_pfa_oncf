import streamlit as st

from config.modeles import MODELES
from utils.composants import afficher_calendrier_quotidien, afficher_comparaison_inter_annees
from utils.style import entete

entete("Comparaison inter-années", "Évolution annuelle et calendrier quotidien des écarts, par modèle")

cles_modeles = list(MODELES.keys())
libelles = [MODELES[cle]["libelle_court"] for cle in cles_modeles]

onglets = st.tabs(libelles)

for onglet, cle_modele in zip(onglets, cles_modeles):
    with onglet:
        st.markdown("**Comparaison inter-années**")
        afficher_comparaison_inter_annees(cle_modele)
        st.markdown("**Calendrier quotidien des écarts**")
        afficher_calendrier_quotidien(cle_modele)
