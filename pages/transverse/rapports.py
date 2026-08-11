import os
from datetime import datetime

import pandas as pd
import streamlit as st

from config.chemins import RAPPORTS
from config.modeles import MODELES
from utils.chargement import charger_anomalies, charger_metriques
from utils.rapport import generer_rapport_hebdomadaire
from utils.style import entete

entete("Rapports", "Rapport hebdomadaire assemblé à partir des métriques et anomalies de chaque modèle")


def _kpis_semaine():
    nb_anomalies = 0
    wmapes = []
    for cle_modele in MODELES:
        anomalies = charger_anomalies(cle_modele)
        if not anomalies.empty and "EstAnomalie" in anomalies.columns:
            nb_anomalies += int(anomalies["EstAnomalie"].sum())
        metriques = charger_metriques(cle_modele)
        if metriques.get("WMAPE") is not None:
            wmapes.append(metriques["WMAPE"])
    wmape_moyen = round(sum(wmapes) / len(wmapes), 1) if wmapes else None
    return nb_anomalies, wmape_moyen


def _fichiers_rapports():
    if not os.path.isdir(RAPPORTS):
        return []
    lignes = []
    for nom in os.listdir(RAPPORTS):
        if not nom.endswith(".pdf"):
            continue
        chemin = os.path.join(RAPPORTS, nom)
        stats = os.stat(chemin)
        lignes.append({
            "Fichier": nom,
            "Date de génération": datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M"),
            "Taille": f"{stats.st_size / 1024:.0f} Ko",
            "_chemin": chemin,
        })
    lignes.sort(key=lambda ligne: ligne["_chemin"], reverse=True)
    return lignes


nb_anomalies, wmape_moyen = _kpis_semaine()
fichiers = _fichiers_rapports()

colonne_un, colonne_deux, colonne_trois = st.columns(3)
with colonne_un:
    st.metric("Anomalies (7 derniers jours)", nb_anomalies)
with colonne_deux:
    st.metric("WMAPE moyen des modèles", f"{wmape_moyen}%" if wmape_moyen is not None else "—")
with colonne_trois:
    st.metric("Rapports déjà générés", len(fichiers))

st.markdown("<div style='height: 6px'></div>", unsafe_allow_html=True)

with st.container(border=True):
    colonne_texte, colonne_bouton = st.columns([3, 1])
    with colonne_texte:
        st.markdown("**Rapport de la semaine**")
        st.caption("Compile les métriques et les anomalies récentes des 7 modèles en un PDF.")
    with colonne_bouton:
        if st.button("Générer le rapport", use_container_width=True):
            chemin = generer_rapport_hebdomadaire()
            st.session_state["dernier_rapport"] = chemin
            st.rerun()

    if "dernier_rapport" in st.session_state and os.path.isfile(st.session_state["dernier_rapport"]):
        with open(st.session_state["dernier_rapport"], "rb") as fichier:
            st.download_button(
                "Télécharger le dernier rapport généré",
                data=fichier.read(),
                file_name=os.path.basename(st.session_state["dernier_rapport"]),
                mime="application/pdf",
                use_container_width=True,
            )

st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
st.markdown("**Historique des rapports**")

if not fichiers:
    st.info("Aucun rapport généré pour l'instant.")
else:
    tableau = pd.DataFrame([{k: v for k, v in ligne.items() if k != "_chemin"} for ligne in fichiers])
    st.dataframe(tableau, use_container_width=True, hide_index=True)

    with st.expander("Télécharger un rapport précédent"):
        for ligne in fichiers:
            with open(ligne["_chemin"], "rb") as fichier:
                st.download_button(
                    ligne["Fichier"],
                    data=fichier.read(),
                    file_name=ligne["Fichier"],
                    mime="application/pdf",
                    key=ligne["Fichier"],
                )