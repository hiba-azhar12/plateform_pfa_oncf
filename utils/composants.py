import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.modeles import MODELES
from utils.chargement import (
    charger_anomalies,
    charger_calendrier_quotidien,
    charger_comparaison_inter_annees,
    charger_importance_features,
    charger_importance_shap,
    charger_metriques,
    charger_predictions,
    charger_saisonnalite,
    charger_seuil_anomalie,
    modele_dispose_de_donnees,
)
from utils.style import PALETTE
from utils.texte import phrase_anomalie, severite_anomalie

LIBELLES_METRIQUES = {
    "RMSE": "RMSE",
    "MAE": "MAE",
    "MedAE": "MedAE",
    "WMAPE": "WMAPE (%)",
    "LogLossComposition": "Perte log (composition)",
    "NbLignesTest": "Lignes de test",
}


def _message_donnees_absentes(cle_modele):
    st.info(
        f"Aucune donnée exportée trouvée pour {MODELES[cle_modele]['libelle']}. "
        f"Déposez le contenu du dossier exporté depuis Kaggle dans "
        f"{MODELES[cle_modele]['dossier']}."
    )


def afficher_cartes_metriques(cle_modele, mettre_en_avant=False):
    metriques = charger_metriques(cle_modele)
    if not metriques:
        return

    champs = [cle for cle in metriques if cle in LIBELLES_METRIQUES]
    colonnes = st.columns(len(champs)) if champs else []
    for colonne, cle in zip(colonnes, champs):
        with colonne:
            if mettre_en_avant and cle in ("RMSE", "MAE"):
                st.markdown('<div class="carte-fraude">', unsafe_allow_html=True)
                st.metric(LIBELLES_METRIQUES[cle], round(metriques[cle], 3) if isinstance(metriques[cle], float) else metriques[cle])
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                valeur = metriques[cle]
                if isinstance(valeur, float):
                    valeur = round(valeur, 3)
                st.metric(LIBELLES_METRIQUES[cle], valeur)


def afficher_dashboard_modele(cle_modele, mettre_en_avant_fraude=False):
    info = MODELES[cle_modele]

    if not modele_dispose_de_donnees(cle_modele):
        _message_donnees_absentes(cle_modele)
        return

    predictions = charger_predictions(cle_modele)
    if predictions.empty:
        _message_donnees_absentes(cle_modele)
        return

    afficher_cartes_metriques(cle_modele, mettre_en_avant=mettre_en_avant_fraude)

    predictions = predictions.copy()
    predictions["Date"] = pd.to_datetime(predictions["Date"])

    colonne_categorie = info["colonne_categorie"]

    liaisons = sorted(predictions["LiaisonId"].astype(str).unique().tolist())
    colonne_gauche, colonne_droite = st.columns([2, 1])
    with colonne_gauche:
        liaison_choisie = st.selectbox("Liaison", liaisons, key=f"liaison_{cle_modele}")
    with colonne_droite:
        if colonne_categorie:
            categories = sorted(predictions[colonne_categorie].astype(str).unique().tolist())
            categorie_choisie = st.selectbox(colonne_categorie, categories, key=f"categorie_{cle_modele}")
        else:
            categorie_choisie = None

    filtre = predictions["LiaisonId"].astype(str) == liaison_choisie
    if colonne_categorie:
        filtre &= predictions[colonne_categorie].astype(str) == categorie_choisie

    sous_ensemble = predictions[filtre].copy()

    if sous_ensemble.empty:
        st.warning("Aucune donnée disponible pour cette combinaison.")
        return

    if "Heure" in sous_ensemble.columns:
        sous_ensemble["Axe"] = sous_ensemble["Date"] + pd.to_timedelta(sous_ensemble["Heure"].astype(int), unit="h")
    else:
        sous_ensemble["Axe"] = sous_ensemble["Date"]

    sous_ensemble = sous_ensemble.sort_values("Axe")

    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=sous_ensemble["Axe"], y=sous_ensemble[info["cible"]],
        mode="lines", name="Réel", line=dict(color=PALETTE["navy"]),
    ))
    figure.add_trace(go.Scatter(
        x=sous_ensemble["Axe"], y=sous_ensemble["Prediction"],
        mode="lines", name="Prédiction", line=dict(color=PALETTE["red"], dash="dash"),
    ))
    figure.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        plot_bgcolor=PALETTE["surface"],
        paper_bgcolor=PALETTE["surface"],
    )
    st.plotly_chart(figure, use_container_width=True)

    saisonnalite = charger_saisonnalite(cle_modele)
    if not saisonnalite.empty:
        with st.expander("Décomposition saisonnière"):
            colonne_serie = saisonnalite[saisonnalite["LiaisonId"].astype(str) == liaison_choisie] if "LiaisonId" in saisonnalite.columns else saisonnalite
            if not colonne_serie.empty:
                figure_saison = px.line(
                    colonne_serie, x="Date", y=["Tendance", "Saisonnalite"],
                    color_discrete_sequence=[PALETTE["navy"], PALETTE["steel"]],
                )
                figure_saison.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(figure_saison, use_container_width=True)


def afficher_anomalies_modele(cle_modele):
    info = MODELES[cle_modele]

    if not modele_dispose_de_donnees(cle_modele):
        _message_donnees_absentes(cle_modele)
        return

    anomalies = charger_anomalies(cle_modele)
    seuil_info = charger_seuil_anomalie(cle_modele)

    if anomalies.empty:
        _message_donnees_absentes(cle_modele)
        return

    seuil = seuil_info.get("SeuilAnomalie", 0)

    colonne_gauche, colonne_droite, colonne_trois = st.columns(3)
    with colonne_gauche:
        st.metric("Seuil d'anomalie", round(seuil, 3))
    with colonne_droite:
        st.metric("Nombre d'anomalies", int(anomalies["EstAnomalie"].sum()))
    with colonne_trois:
        taux = anomalies["EstAnomalie"].mean() * 100 if len(anomalies) else 0
        st.metric("Taux d'anomalies", f"{taux:.1f}%")

    anomalies_detectees = anomalies[anomalies["EstAnomalie"]].sort_values("ErreurAbsolue", ascending=False)

    if anomalies_detectees.empty:
        st.success("Aucune anomalie détectée sur la période disponible.")
        return

    anomalies_detectees = anomalies_detectees.copy()
    anomalies_detectees["Severite"] = anomalies_detectees["ErreurAbsolue"].apply(
        lambda erreur: severite_anomalie(erreur, seuil)
    )

    colonnes_affichees = [c for c in ["Date", "LiaisonId", info["colonne_categorie"], info["cible"], "Prediction", "ErreurAbsolue", "Severite"] if c and c in anomalies_detectees.columns]

    st.dataframe(
        anomalies_detectees[colonnes_affichees].head(200),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Détail des anomalies critiques"):
        critiques = anomalies_detectees[anomalies_detectees["Severite"] == "critique"].head(10)
        for _, ligne in critiques.iterrows():
            texte = phrase_anomalie(
                ligne["Date"], ligne["LiaisonId"], ligne[info["cible"]], ligne["Prediction"], info["cible"]
            )
            st.write(texte)


def afficher_explicabilite_modele(cle_modele):
    info = MODELES[cle_modele]

    if not modele_dispose_de_donnees(cle_modele):
        _message_donnees_absentes(cle_modele)
        return

    importance_features = charger_importance_features(cle_modele)
    importance_shap = charger_importance_shap(cle_modele)

    if importance_features.empty and importance_shap.empty:
        _message_donnees_absentes(cle_modele)
        return

    colonne_gauche, colonne_droite = st.columns(2)

    with colonne_gauche:
        st.markdown("**Importance des variables**")
        if not importance_features.empty:
            agregee = importance_features.groupby("Feature")["Importance"].mean().sort_values(ascending=False).head(15).reset_index()
            figure = px.bar(agregee, x="Importance", y="Feature", orientation="h", color_discrete_sequence=[PALETTE["navy"]])
            figure.update_layout(height=460, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(figure, use_container_width=True)

    with colonne_droite:
        st.markdown("**Importance SHAP**")
        if not importance_shap.empty:
            colonne_valeur = "ImportanceSHAP" if "ImportanceSHAP" in importance_shap.columns else importance_shap.columns[-1]
            agregee = importance_shap.groupby("Feature")[colonne_valeur].mean().sort_values(ascending=False).head(15).reset_index()
            figure = px.bar(agregee, x=colonne_valeur, y="Feature", orientation="h", color_discrete_sequence=[PALETTE["red"]])
            figure.update_layout(height=460, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(figure, use_container_width=True)

    predictions = charger_predictions(cle_modele)
    if not predictions.empty and "ErreurAbsolue" in predictions.columns:
        st.markdown("**Analyse des erreurs**")
        predictions = predictions.copy()
        predictions["Date"] = pd.to_datetime(predictions["Date"])
        predictions["JourSemaine"] = predictions["Date"].dt.dayofweek

        colonne_gauche, colonne_droite = st.columns(2)
        with colonne_gauche:
            erreur_jour = predictions.groupby("JourSemaine")["ErreurAbsolue"].mean().reset_index()
            figure = px.bar(erreur_jour, x="JourSemaine", y="ErreurAbsolue", color_discrete_sequence=[PALETTE["steel"]])
            figure.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(figure, use_container_width=True)
        with colonne_droite:
            erreur_liaison = (
                predictions.groupby("LiaisonId")["ErreurAbsolue"].mean()
                .sort_values(ascending=False).head(15).reset_index()
            )
            erreur_liaison["LiaisonId"] = erreur_liaison["LiaisonId"].astype(str)
            figure = px.bar(erreur_liaison, x="ErreurAbsolue", y="LiaisonId", orientation="h", color_discrete_sequence=[PALETTE["amber"]])
            figure.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(figure, use_container_width=True)


def afficher_comparaison_inter_annees(cle_modele):
    info = MODELES[cle_modele]
    comparaison = charger_comparaison_inter_annees(cle_modele)
    if comparaison.empty:
        _message_donnees_absentes(cle_modele)
        return

    st.markdown(f"**{info['libelle']}**")
    colonne_valeur = info["cible"]
    if colonne_valeur not in comparaison.columns:
        colonne_valeur = comparaison.columns[-1]

    figure = px.bar(
        comparaison, x="Mois", y=colonne_valeur, color="Annee", barmode="group",
        color_discrete_sequence=[PALETTE["navy"], PALETTE["steel"], PALETTE["red"], PALETTE["amber"]],
    )
    figure.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(figure, use_container_width=True)


def afficher_calendrier_quotidien(cle_modele):
    calendrier = charger_calendrier_quotidien(cle_modele)
    if calendrier.empty:
        _message_donnees_absentes(cle_modele)
        return

    calendrier = calendrier.copy()
    calendrier["Date"] = pd.to_datetime(calendrier["Date"])
    figure = px.density_heatmap(
        calendrier, x=calendrier["Date"].dt.isocalendar().week, y=calendrier["Date"].dt.dayofweek,
        z="Ecart", color_continuous_scale=["#1E7145", "#F4F6F9", PALETTE["red"]],
    )
    figure.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(figure, use_container_width=True)
