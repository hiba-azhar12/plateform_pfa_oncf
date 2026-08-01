import os

import streamlit as st

from config.chemins import RAPPORTS
from utils.rapport import generer_rapport_hebdomadaire
from utils.style import entete

entete("Rapports", "Rapport hebdomadaire assemblé à partir des métriques et anomalies de chaque modèle")

st.markdown(
    "Le contenu du rapport est un assemblage de gabarit, pas une génération par intelligence "
    "artificielle. Un script identique (scripts/generer_rapport.py) peut être planifié chaque "
    "lundi via une tâche cron pour produire ce même document sans passer par l'application."
)

if st.button("Générer le rapport de la semaine"):
    chemin = generer_rapport_hebdomadaire()
    st.session_state["dernier_rapport"] = chemin

if "dernier_rapport" in st.session_state and os.path.isfile(st.session_state["dernier_rapport"]):
    with open(st.session_state["dernier_rapport"], "rb") as fichier:
        st.download_button(
            "Télécharger le rapport",
            data=fichier.read(),
            file_name=os.path.basename(st.session_state["dernier_rapport"]),
            mime="application/pdf",
        )

st.markdown("**Rapports déjà générés**")
if os.path.isdir(RAPPORTS):
    fichiers = sorted(
        [f for f in os.listdir(RAPPORTS) if f.endswith(".pdf")],
        reverse=True,
    )
    if fichiers:
        for nom_fichier in fichiers:
            chemin = os.path.join(RAPPORTS, nom_fichier)
            with open(chemin, "rb") as fichier:
                st.download_button(nom_fichier, data=fichier.read(), file_name=nom_fichier, mime="application/pdf", key=nom_fichier)
    else:
        st.info("Aucun rapport généré pour l'instant.")
