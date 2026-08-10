import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.modeles import MODELES
from utils.chargement import charger_predictions_nouvelles, dernier_log_execution
from utils.style import PALETTE, bandeau_statut, entete

entete("Nouvelles Prédictions", "Prédictions calculées chaque nuit à partir des dépôts quotidiens de données PDA")

dernier = dernier_log_execution()

if dernier is None:
    bandeau_statut("avertissement", "Aucune exécution du pipeline n'a encore eu lieu.")
else:
    statut = dernier.get("statut")
    horodatage = dernier.get("horodatage", "")
    if statut == "succes":
        bandeau_statut(
            "succes",
            f"Dernière mise à jour : {horodatage} — "
            f"{dernier.get('fichiers_traites', 0)} fichier(s) traité(s), prédictions à jour.",
        )
    elif statut == "aucune_donnee":
        bandeau_statut(
            "avertissement",
            f"Aucune donnée reçue lors de l'exécution du {horodatage}. "
            f"Dernière mise à jour disponible affichée ci-dessous.",
        )
    else:
        bandeau_statut(
            "erreur",
            f"Erreur lors du traitement du {horodatage} : {dernier.get('erreur', 'détail indisponible')}",
        )

libelles = [MODELES[cle]["libelle_court"] for cle in MODELES]
onglets = st.tabs(libelles)

for onglet, cle_modele in zip(onglets, MODELES.keys()):
    with onglet:
        info = MODELES[cle_modele]
        donnees = charger_predictions_nouvelles(cle_modele)

        if donnees.empty:
            st.info("Aucune prédiction générée pour ce modèle pour le moment.")
            continue

        donnees = donnees.copy()
        donnees["Date"] = pd.to_datetime(donnees["Date"])

        liaisons = sorted(donnees["LiaisonId"].astype(str).unique().tolist())
        liaison_choisie = st.selectbox("Liaison", liaisons, key=f"nouvelle_liaison_{cle_modele}")

        filtre = donnees["LiaisonId"].astype(str) == liaison_choisie
        if info["colonne_categorie"] and info["colonne_categorie"] in donnees.columns:
            categories = sorted(donnees[info["colonne_categorie"]].astype(str).unique().tolist())
            categorie_choisie = st.selectbox(info["colonne_categorie"], categories, key=f"nouvelle_categorie_{cle_modele}")
            filtre &= donnees[info["colonne_categorie"]].astype(str) == categorie_choisie

        if info["granularite"] == "horaire" and "Heure" in donnees.columns:
            heures = sorted(donnees.loc[filtre, "Heure"].astype(int).unique().tolist())
            heure_choisie = st.selectbox("Heure", heures, key=f"nouvelle_heure_{cle_modele}")
            filtre &= donnees["Heure"].astype(int) == heure_choisie

        sous_ensemble = donnees[filtre].sort_values("Date")

        if sous_ensemble.empty:
            st.warning("Aucune donnée pour cette combinaison.")
            continue

        derniere_ligne = sous_ensemble.iloc[-1]
        colonne_gauche, colonne_droite, colonne_trois = st.columns(3)
        with colonne_gauche:
            st.metric("Prochaine prédiction", f"{derniere_ligne['Prediction']:.1f}")
        with colonne_droite:
            reconciliees = sous_ensemble.dropna(subset=["Reel"])
            if not reconciliees.empty:
                st.metric("Dernier réel connu", f"{reconciliees.iloc[-1]['Reel']:.1f}")
            else:
                st.metric("Dernier réel connu", "en attente")
        with colonne_trois:
            if not reconciliees.empty:
                st.metric("Dernière erreur absolue", f"{reconciliees.iloc[-1]['ErreurAbsolue']:.1f}")
            else:
                st.metric("Dernière erreur absolue", "en attente")

        figure = go.Figure()
        if "Reel" in sous_ensemble.columns:
            reel = sous_ensemble.dropna(subset=["Reel"])
            figure.add_trace(go.Scatter(
                x=reel["Date"], y=reel["Reel"],
                mode="lines+markers", name="Réel", line=dict(color=PALETTE["navy"], width=2.5), marker=dict(size=5),
            ))
        figure.add_trace(go.Scatter(
            x=sous_ensemble["Date"], y=sous_ensemble["Prediction"],
            mode="lines+markers", name="Prédiction", line=dict(color=PALETTE["red"], width=2.5), marker=dict(size=5),
        ))
        figure.update_layout(
            template="plotly_white",
            font=dict(family="Segoe UI, Helvetica Neue, Arial, sans-serif", color=PALETTE["text"], size=13),
            height=400, margin=dict(l=10, r=10, t=24, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor=PALETTE["surface"], paper_bgcolor=PALETTE["surface"],
            hovermode="x unified",
        )
        figure.update_xaxes(showgrid=False, showline=True, linecolor=PALETTE["border"], title_text="Date")
        figure.update_yaxes(showgrid=True, gridcolor=PALETTE["border"], title_text=info["libelle_court"])
        st.plotly_chart(figure, use_container_width=True)

        with st.expander("Table détaillée"):
            colonnes = [c for c in ["Date", "Heure", "LiaisonId", info["colonne_categorie"], "Prediction", "DateCalculPrediction", "Reel", "ErreurAbsolue"] if c and c in sous_ensemble.columns]
            st.dataframe(sous_ensemble[colonnes].sort_values("Date", ascending=False), use_container_width=True, hide_index=True)