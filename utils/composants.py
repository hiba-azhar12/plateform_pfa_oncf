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
    liaisons_ordonnees_par_frequence,
    modele_dispose_de_donnees,
)
from utils.style import PALETTE
from utils.texte import phrase_anomalie, severite_anomalie

OPTION_TOUTES_LIAISONS = "Toutes les liaisons (agrégé)"
OPTION_TOUTES_HEURES = "Toutes les heures"
OPTION_TOUTES_DATES = "Toutes les dates"

LIBELLES_METRIQUES = {
    "RMSE": "RMSE",
    "MAE": "MAE",
    "MedAE": "MedAE",
    "WMAPE": "WMAPE (%)",
    "LogLossComposition": "Perte log (composition)",
    "NbLignesTest": "Lignes de test",
}

JOURS_SEMAINE = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
MOIS_ABREGES = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
SEQUENCE_ANNEES = [PALETTE["navy"], PALETTE["orange"], PALETTE["steel"], PALETTE["amber"], PALETTE["green"]]


def _mise_en_forme(figure, titre=None, hauteur=380, hovermode="x unified", afficher_legende=True):
    figure.update_layout(
        template="plotly_white",
        font=dict(family="Segoe UI, Helvetica Neue, Arial, sans-serif", color=PALETTE["text"], size=13),
        title=dict(text=titre, x=0.01, xanchor="left", font=dict(size=16, color=PALETTE["navy"])) if titre else None,
        height=hauteur,
        margin=dict(l=10, r=10, t=54 if titre else 24, b=10),
        plot_bgcolor=PALETTE["surface"],
        paper_bgcolor=PALETTE["surface"],
        hovermode=hovermode,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None) if afficher_legende else dict(visible=False),
    )
    figure.update_xaxes(showgrid=False, showline=True, linecolor=PALETTE["border"], zeroline=False)
    figure.update_yaxes(showgrid=True, gridcolor=PALETTE["border"], zeroline=False)
    return figure


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


def _fonction_agregation(famille):
    return "sum" if famille == "comptages" else "mean"


def _titre_selection(info, liaison_choisie, date_choisie, granularite_horaire, heure_choisie):
    titre = info["libelle"]
    titre += " — Toutes les liaisons (agrégé)" if liaison_choisie == OPTION_TOUTES_LIAISONS else f" — Liaison {liaison_choisie}"
    titre += f" — {date_choisie.strftime('%d/%m/%Y')}" if date_choisie is not None else " — Toutes les dates"
    if granularite_horaire:
        titre += " — Toutes les heures" if heure_choisie == OPTION_TOUTES_HEURES else f" — {heure_choisie}h"
    return titre


def afficher_dashboard_modele(cle_modele, mettre_en_avant_fraude=False):
    info = MODELES[cle_modele]

    if not modele_dispose_de_donnees(cle_modele):
        _message_donnees_absentes(cle_modele)
        return

    predictions = charger_predictions(cle_modele)
    if predictions.empty:
        _message_donnees_absentes(cle_modele)
        return

    st.markdown("**Qualité du modèle (jeu de test)**")
    afficher_cartes_metriques(cle_modele, mettre_en_avant=mettre_en_avant_fraude)
    st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)

    predictions = predictions.copy()
    predictions["Date"] = pd.to_datetime(predictions["Date"])
    predictions["LiaisonId"] = predictions["LiaisonId"].astype(str)
    colonne_categorie = info["colonne_categorie"]
    cible = info["cible"]
    fonction_agg = _fonction_agregation(info["famille"])

    granularite_horaire = info["granularite"] == "horaire" and "Heure" in predictions.columns

    date_min = predictions["Date"].min().date()
    date_max = predictions["Date"].max().date()

    with st.container(border=True, key=f"panneau_selection_{cle_modele}"):
        st.markdown("**Sélection**")
        poids = [2] + ([1] if colonne_categorie else []) + [2] + ([1] if granularite_horaire else [])
        colonnes_filtre = st.columns(poids)
        indice = 0

        with colonnes_filtre[indice]:
            liaisons = liaisons_ordonnees_par_frequence(cle_modele)
            options_liaison = [OPTION_TOUTES_LIAISONS] + liaisons
            liaison_choisie = st.selectbox("Liaison", options_liaison, key=f"liaison_{cle_modele}")
        indice += 1

        if colonne_categorie:
            with colonnes_filtre[indice]:
                categories = sorted(predictions[colonne_categorie].astype(str).unique().tolist())
                categorie_choisie = st.selectbox(colonne_categorie, categories, key=f"categorie_{cle_modele}")
            indice += 1
        else:
            categorie_choisie = None

        with colonnes_filtre[indice]:
            sous_champ, sous_case = st.columns([1.6, 1.1])
            with sous_case:
                st.markdown("<div style='height: 1.9rem'></div>", unsafe_allow_html=True)
                toutes_dates = st.checkbox(OPTION_TOUTES_DATES, value=True, key=f"toutes_dates_{cle_modele}")
            with sous_champ:
                date_selectionnee = st.date_input(
                    "Date précise", value=date_max, min_value=date_min, max_value=date_max,
                    key=f"date_{cle_modele}", disabled=toutes_dates,
                )
        indice += 1

        if granularite_horaire:
            with colonnes_filtre[indice]:
                heures = sorted(predictions["Heure"].astype(int).unique().tolist())
                options_heure = [OPTION_TOUTES_HEURES] + heures
                heure_choisie = st.selectbox("Heure", options_heure, key=f"heure_{cle_modele}")
        else:
            heure_choisie = None

    liaison_est_all = liaison_choisie == OPTION_TOUTES_LIAISONS
    heure_est_all = granularite_horaire and heure_choisie == OPTION_TOUTES_HEURES
    date_est_all = toutes_dates

    filtre = pd.Series(True, index=predictions.index)
    if colonne_categorie:
        filtre &= predictions[colonne_categorie].astype(str) == categorie_choisie
    if not liaison_est_all:
        filtre &= predictions["LiaisonId"] == liaison_choisie
    if granularite_horaire and not heure_est_all:
        filtre &= predictions["Heure"].astype(int) == heure_choisie
    if not date_est_all:
        filtre &= predictions["Date"].dt.date == date_selectionnee

    sous_ensemble = predictions[filtre].copy()

    if sous_ensemble.empty:
        st.warning("Aucune donnée disponible pour cette combinaison.")
        return

    date_pour_titre = None if date_est_all else date_selectionnee
    titre_graphe = _titre_selection(info, liaison_choisie, date_pour_titre, granularite_horaire, heure_choisie)

    if date_est_all:
        agrege = sous_ensemble.groupby("Date", as_index=False).agg({cible: fonction_agg, "Prediction": fonction_agg})
        agrege = agrege.sort_values("Date")
        agrege["Ecart"] = agrege["Prediction"] - agrege[cible]
        derniere_reelle = agrege.dropna(subset=[cible])

        st.markdown("**État courant**")
        colonne_un, colonne_deux, colonne_trois = st.columns(3)
        with colonne_un:
            valeur = f"{derniere_reelle.iloc[-1][cible]:.1f}" if not derniere_reelle.empty else "en attente"
            st.metric("Dernier réel", valeur)
        with colonne_deux:
            st.metric("Dernière prédiction", f"{agrege.iloc[-1]['Prediction']:.1f}")
        with colonne_trois:
            valeur = f"{derniere_reelle.iloc[-1]['Ecart']:+.1f}" if not derniere_reelle.empty else "—"
            st.metric("Écart", valeur)

        figure = go.Figure()
        figure.add_trace(go.Scatter(
            x=agrege["Date"], y=agrege[cible],
            mode="lines", name="Réel", line=dict(color=PALETTE["navy"], width=2.5),
        ))
        figure.add_trace(go.Scatter(
            x=agrege["Date"], y=agrege["Prediction"],
            mode="lines", name="Prédiction", line=dict(color=PALETTE["orange"], width=2.5),
            fill="tonexty", fillcolor="rgba(245,130,32,0.12)",
        ))
        _mise_en_forme(figure, titre=titre_graphe, hauteur=420)
        figure.update_xaxes(title_text="Date")
        figure.update_yaxes(title_text=info["libelle_court"])
        st.plotly_chart(figure, use_container_width=True)

        colonne_gauche, colonne_droite = st.columns(2)
        with colonne_gauche:
            donnees_ecart = agrege.dropna(subset=["Ecart"]).copy()
            donnees_ecart["AxeLabel"] = donnees_ecart["Date"].dt.strftime("%d %b")
            figure_ecart = px.bar(
                donnees_ecart, x="AxeLabel", y="Ecart", color_discrete_sequence=[PALETTE["steel"]],
                custom_data=["Date"],
            )
            figure_ecart.update_traces(marker_line_width=0, hovertemplate="%{customdata[0]|%d %b %Y}<br>Écart : %{y:.3f}<extra></extra>")
            _mise_en_forme(figure_ecart, titre="Écart dans le temps (prédiction − réel)", hauteur=280, hovermode="closest", afficher_legende=False)
            figure_ecart.update_xaxes(title_text="", type="category", tickangle=-45, nticks=10)
            figure_ecart.update_yaxes(title_text="")
            st.plotly_chart(figure_ecart, use_container_width=True)
        with colonne_droite:
            donnees_distribution = agrege.dropna(subset=["Ecart"])
            figure_distribution = px.histogram(donnees_distribution, x="Ecart", color_discrete_sequence=[PALETTE["amber"]])
            figure_distribution.update_traces(marker_line_width=0)
            _mise_en_forme(figure_distribution, titre="Distribution des écarts", hauteur=280, hovermode="closest", afficher_legende=False)
            figure_distribution.update_xaxes(title_text="Écart")
            figure_distribution.update_yaxes(title_text="Fréquence")
            st.plotly_chart(figure_distribution, use_container_width=True)

        if not liaison_est_all:
            saisonnalite = charger_saisonnalite(cle_modele)
            if not saisonnalite.empty:
                with st.expander("Décomposition saisonnière", expanded=True):
                    colonne_serie = saisonnalite[saisonnalite["LiaisonId"].astype(str) == liaison_choisie] if "LiaisonId" in saisonnalite.columns else saisonnalite
                    colonnes_requises = {"Date", "Tendance", "Saisonnalite"}
                    if not colonne_serie.empty and colonnes_requises.issubset(colonne_serie.columns):
                        figure_saison = px.line(
                            colonne_serie, x="Date", y=["Tendance", "Saisonnalite"],
                            color_discrete_sequence=[PALETTE["navy"], PALETTE["steel"]],
                        )
                        figure_saison.update_traces(line=dict(width=2.5))
                        _mise_en_forme(figure_saison, titre="Tendance et saisonnalité", hauteur=320)
                        figure_saison.update_xaxes(title_text="Date")
                        figure_saison.update_yaxes(title_text="")
                        st.plotly_chart(figure_saison, use_container_width=True)

    elif liaison_est_all:
        agrege = sous_ensemble.groupby("LiaisonId", as_index=False).agg({cible: fonction_agg, "Prediction": fonction_agg})
        agrege["Ecart"] = agrege["Prediction"] - agrege[cible]
        agrege = agrege.sort_values(cible, ascending=False)

        st.markdown("**État courant**")
        colonne_un, colonne_deux, colonne_trois, colonne_quatre = st.columns(4)
        with colonne_un:
            st.metric("Liaisons concernées", len(agrege))
        with colonne_deux:
            st.metric("Total réel", f"{agrege[cible].sum():.1f}")
        with colonne_trois:
            st.metric("Total prédiction", f"{agrege['Prediction'].sum():.1f}")
        with colonne_quatre:
            st.metric("Écart total", f"{(agrege['Prediction'].sum() - agrege[cible].sum()):+.1f}")

        nb_affichees = 25
        top = agrege.head(nb_affichees)
        figure = go.Figure()
        figure.add_trace(go.Bar(x=top["LiaisonId"], y=top[cible], name="Réel", marker_color=PALETTE["navy"]))
        figure.add_trace(go.Bar(x=top["LiaisonId"], y=top["Prediction"], name="Prédiction", marker_color=PALETTE["orange"]))
        figure.update_layout(barmode="group")
        _mise_en_forme(figure, titre=f"{titre_graphe} — Top {nb_affichees} liaisons", hauteur=440)
        figure.update_xaxes(title_text="Liaison", type="category")
        figure.update_yaxes(title_text=info["libelle_court"])
        st.plotly_chart(figure, use_container_width=True)

        with st.expander(f"Table complète des liaisons ({len(agrege)})", expanded=True):
            table = agrege.rename(columns={cible: "Réel"})[["LiaisonId", "Réel", "Prediction", "Ecart"]]
            st.dataframe(table, use_container_width=True, hide_index=True)

    else:
        if heure_est_all:
            serie_horaire = sous_ensemble.sort_values("Heure")
            total_reel = serie_horaire[cible].sum()
            total_prediction = serie_horaire["Prediction"].sum()

            st.markdown("**Variation par heure**")
            st.caption(titre_graphe)
            colonne_un, colonne_deux, colonne_trois = st.columns(3)
            with colonne_un:
                st.metric("Total réel", f"{total_reel:.1f}")
            with colonne_deux:
                st.metric("Total prédiction", f"{total_prediction:.1f}")
            with colonne_trois:
                st.metric("Écart total", f"{(total_prediction - total_reel):+.1f}")

            figure = go.Figure()
            figure.add_trace(go.Bar(x=serie_horaire["Heure"], y=serie_horaire[cible], name="Réel", marker_color=PALETTE["navy"]))
            figure.add_trace(go.Bar(x=serie_horaire["Heure"], y=serie_horaire["Prediction"], name="Prédiction", marker_color=PALETTE["orange"]))
            figure.update_layout(barmode="group")
            _mise_en_forme(figure, titre=titre_graphe, hauteur=380)
            figure.update_xaxes(title_text="Heure", type="category")
            figure.update_yaxes(title_text=info["libelle_court"])
            st.plotly_chart(figure, use_container_width=True)
        else:
            ligne = sous_ensemble.iloc[0]
            valeur_reelle = ligne[cible]
            valeur_prediction = ligne["Prediction"]
            ecart = valeur_prediction - valeur_reelle if pd.notna(valeur_reelle) else None

            st.markdown("**Valeur pour cette sélection**")
            st.caption(titre_graphe)
            colonne_un, colonne_deux, colonne_trois = st.columns(3)
            with colonne_un:
                st.metric("Réel", f"{valeur_reelle:.1f}" if pd.notna(valeur_reelle) else "en attente")
            with colonne_deux:
                st.metric("Prédiction", f"{valeur_prediction:.1f}")
            with colonne_trois:
                st.metric("Écart", f"{ecart:+.1f}" if ecart is not None else "—")


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

    with st.expander("Détail des anomalies critiques", expanded=True):
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
        if not importance_features.empty:
            agregee = importance_features.groupby("Feature")["Importance"].mean().sort_values(ascending=False).head(15).reset_index()
            figure = px.bar(
                agregee, x="Importance", y="Feature", orientation="h",
                color_discrete_sequence=[PALETTE["navy"]], text="Importance",
            )
            figure.update_traces(texttemplate="%{text:.3f}", textposition="outside", marker_line_width=0)
            _mise_en_forme(figure, titre="Importance des variables", hauteur=460, hovermode="closest", afficher_legende=False)
            figure.update_yaxes(categoryorder="total ascending", title_text="")
            figure.update_xaxes(title_text="Importance moyenne")
            st.plotly_chart(figure, use_container_width=True)

    with colonne_droite:
        if not importance_shap.empty:
            colonne_valeur = "ImportanceSHAP" if "ImportanceSHAP" in importance_shap.columns else importance_shap.columns[-1]
            agregee = importance_shap.groupby("Feature")[colonne_valeur].mean().sort_values(ascending=False).head(15).reset_index()
            figure = px.bar(
                agregee, x=colonne_valeur, y="Feature", orientation="h",
                color_discrete_sequence=[PALETTE["orange"]], text=colonne_valeur,
            )
            figure.update_traces(texttemplate="%{text:.3f}", textposition="outside", marker_line_width=0)
            _mise_en_forme(figure, titre="Importance SHAP", hauteur=460, hovermode="closest", afficher_legende=False)
            figure.update_yaxes(categoryorder="total ascending", title_text="")
            figure.update_xaxes(title_text="Importance SHAP moyenne")
            st.plotly_chart(figure, use_container_width=True)

    predictions = charger_predictions(cle_modele)
    if not predictions.empty and "ErreurAbsolue" in predictions.columns:
        predictions = predictions.copy()
        predictions["Date"] = pd.to_datetime(predictions["Date"])
        predictions["JourSemaine"] = predictions["Date"].dt.dayofweek

        colonne_gauche, colonne_droite = st.columns(2)
        with colonne_gauche:
            erreur_jour = predictions.groupby("JourSemaine")["ErreurAbsolue"].mean().reset_index()
            erreur_jour["Jour"] = erreur_jour["JourSemaine"].apply(lambda indice: JOURS_SEMAINE[int(indice)])
            figure = px.bar(
                erreur_jour, x="Jour", y="ErreurAbsolue", color_discrete_sequence=[PALETTE["steel"]],
                category_orders={"Jour": JOURS_SEMAINE}, text="ErreurAbsolue",
            )
            figure.update_traces(texttemplate="%{text:.2f}", textposition="outside", marker_line_width=0)
            _mise_en_forme(figure, titre="Erreur moyenne par jour de semaine", hauteur=360, hovermode="closest", afficher_legende=False)
            figure.update_xaxes(title_text="")
            figure.update_yaxes(title_text="Erreur absolue moyenne")
            st.plotly_chart(figure, use_container_width=True)
        with colonne_droite:
            erreur_liaison = (
                predictions.groupby("LiaisonId")["ErreurAbsolue"].mean()
                .sort_values(ascending=False).head(15).reset_index()
            )
            erreur_liaison["LiaisonId"] = erreur_liaison["LiaisonId"].astype(str)
            figure = px.bar(
                erreur_liaison, x="ErreurAbsolue", y="LiaisonId", orientation="h",
                color="ErreurAbsolue", color_continuous_scale=[PALETTE["amber"], PALETTE["red"]],
                text="ErreurAbsolue",
            )
            figure.update_traces(texttemplate="%{text:.2f}", textposition="outside", marker_line_width=0)
            figure.update_coloraxes(showscale=False)
            _mise_en_forme(figure, titre="Top 15 liaisons par erreur moyenne", hauteur=360, hovermode="closest", afficher_legende=False)
            figure.update_yaxes(categoryorder="total ascending", title_text="Liaison")
            figure.update_xaxes(title_text="Erreur absolue moyenne")
            st.plotly_chart(figure, use_container_width=True)


def afficher_comparaison_inter_annees(cle_modele):
    info = MODELES[cle_modele]
    comparaison = charger_comparaison_inter_annees(cle_modele)
    if comparaison.empty:
        _message_donnees_absentes(cle_modele)
        return

    colonne_valeur = info["cible"]
    if colonne_valeur not in comparaison.columns:
        colonne_valeur = comparaison.columns[-1]

    comparaison = comparaison.copy()
    comparaison["Annee"] = comparaison["Annee"].astype(int).astype(str)
    comparaison["MoisLabel"] = comparaison["Mois"].astype(int).apply(lambda mois: MOIS_ABREGES[mois - 1])

    annees_triees = sorted(comparaison["Annee"].unique())
    couleurs_annees = {annee: SEQUENCE_ANNEES[indice % len(SEQUENCE_ANNEES)] for indice, annee in enumerate(annees_triees)}

    figure = px.bar(
        comparaison, x="MoisLabel", y=colonne_valeur, color="Annee", barmode="group",
        category_orders={"MoisLabel": MOIS_ABREGES, "Annee": annees_triees},
        color_discrete_map=couleurs_annees,
    )
    figure.update_traces(marker_line_width=0)
    _mise_en_forme(figure, titre=info["libelle"], hauteur=400)
    figure.update_layout(legend_title_text="Année")
    figure.update_xaxes(title_text="")
    figure.update_yaxes(title_text=info["libelle_court"])
    st.plotly_chart(figure, use_container_width=True)


def afficher_calendrier_quotidien(cle_modele):
    calendrier = charger_calendrier_quotidien(cle_modele)
    if calendrier.empty:
        _message_donnees_absentes(cle_modele)
        return

    calendrier = calendrier.copy()
    calendrier["Date"] = pd.to_datetime(calendrier["Date"])
    calendrier["Semaine"] = calendrier["Date"].dt.strftime("Sem. %V")
    calendrier["JourSemaine"] = calendrier["Date"].dt.dayofweek

    ordre_semaines = calendrier.sort_values("Date")["Semaine"].unique().tolist()

    figure = px.density_heatmap(
        calendrier, x="Semaine", y="JourSemaine", z="Ecart",
        category_orders={"Semaine": ordre_semaines},
        color_continuous_scale=[PALETTE["steel"], PALETTE["surface"], PALETTE["red"]],
        color_continuous_midpoint=0,
    )
    _mise_en_forme(figure, titre="Calendrier quotidien des écarts (Prédiction − Réel)", hauteur=320, hovermode="closest", afficher_legende=False)
    figure.update_yaxes(
        title_text="", tickmode="array", tickvals=list(range(7)), ticktext=JOURS_SEMAINE, autorange="reversed",
    )
    figure.update_xaxes(title_text="")
    figure.update_layout(coloraxis_colorbar=dict(title="Écart"))
    st.plotly_chart(figure, use_container_width=True)