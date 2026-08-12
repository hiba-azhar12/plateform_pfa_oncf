import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.modeles import MODELES
from utils.chargement import charger_predictions_nouvelles, dernier_log_execution, liaisons_ordonnees_nouvelles_predictions
from utils.composants import OPTION_TOUTES_DATES, OPTION_TOUTES_HEURES, OPTION_TOUTES_LIAISONS, _fonction_agregation, _mise_en_forme
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
        donnees["LiaisonId"] = donnees["LiaisonId"].astype(str)
        fonction_agg = _fonction_agregation(info["famille"])
        granularite_horaire = info["granularite"] == "horaire" and "Heure" in donnees.columns

        date_min = donnees["Date"].min().date()
        date_max = donnees["Date"].max().date()

        poids = [2] + ([1] if info["colonne_categorie"] else []) + [2] + ([1] if granularite_horaire else [])

        with st.container(border=True, key=f"panneau_selection_nouvelle_{cle_modele}"):
            st.markdown("**Sélection**")
            colonnes_filtre = st.columns(poids)
            indice = 0

            with colonnes_filtre[indice]:
                liaisons = liaisons_ordonnees_nouvelles_predictions(cle_modele)
                options_liaison = [OPTION_TOUTES_LIAISONS] + liaisons
                liaison_choisie = st.selectbox("Liaison", options_liaison, key=f"nouvelle_liaison_{cle_modele}")
            indice += 1

            if info["colonne_categorie"] and info["colonne_categorie"] in donnees.columns:
                with colonnes_filtre[indice]:
                    categories = sorted(donnees[info["colonne_categorie"]].astype(str).unique().tolist())
                    categorie_choisie = st.selectbox(info["colonne_categorie"], categories, key=f"nouvelle_categorie_{cle_modele}")
                indice += 1
            else:
                categorie_choisie = None

            with colonnes_filtre[indice]:
                sous_champ, sous_case = st.columns([1.6, 1.1])
                with sous_case:
                    st.markdown("<div style='height: 1.9rem'></div>", unsafe_allow_html=True)
                    toutes_dates = st.checkbox(OPTION_TOUTES_DATES, value=True, key=f"nouvelle_toutes_dates_{cle_modele}")
                with sous_champ:
                    date_selectionnee = st.date_input(
                        "Date précise", value=date_max, min_value=date_min, max_value=date_max,
                        key=f"nouvelle_date_{cle_modele}", disabled=toutes_dates,
                    )
            indice += 1

            if granularite_horaire:
                with colonnes_filtre[indice]:
                    heures = sorted(donnees["Heure"].astype(int).unique().tolist())
                    options_heure = [OPTION_TOUTES_HEURES] + heures
                    heure_choisie = st.selectbox("Heure", options_heure, key=f"nouvelle_heure_{cle_modele}")
            else:
                heure_choisie = None

        liaison_est_all = liaison_choisie == OPTION_TOUTES_LIAISONS
        heure_est_all = granularite_horaire and heure_choisie == OPTION_TOUTES_HEURES
        date_est_all = toutes_dates

        filtre = pd.Series(True, index=donnees.index)
        if categorie_choisie is not None:
            filtre &= donnees[info["colonne_categorie"]].astype(str) == categorie_choisie
        if not liaison_est_all:
            filtre &= donnees["LiaisonId"] == liaison_choisie
        if granularite_horaire and not heure_est_all:
            filtre &= donnees["Heure"].astype(int) == heure_choisie
        if not date_est_all:
            filtre &= donnees["Date"].dt.date == date_selectionnee

        sous_ensemble = donnees[filtre].copy()

        if sous_ensemble.empty:
            st.warning("Aucune donnée pour cette combinaison.")
            continue

        titre_graphe = info["libelle"]
        titre_graphe += " — Toutes les liaisons (agrégé)" if liaison_est_all else f" — Liaison {liaison_choisie}"
        titre_graphe += " — Toutes les dates" if date_est_all else f" — {date_selectionnee.strftime('%d/%m/%Y')}"
        if granularite_horaire:
            titre_graphe += " — Toutes les heures" if heure_est_all else f" — {heure_choisie}h"

        if date_est_all:
            agrege = sous_ensemble.groupby("Date", as_index=False).agg({"Reel": fonction_agg, "Prediction": fonction_agg})
            agrege = agrege.sort_values("Date")
            derniere_reelle = agrege.dropna(subset=["Reel"])

            colonne_gauche, colonne_droite, colonne_trois = st.columns(3)
            with colonne_gauche:
                st.metric("Prochaine prédiction", f"{agrege.iloc[-1]['Prediction']:.1f}")
            with colonne_droite:
                if not derniere_reelle.empty:
                    st.metric("Dernier réel connu", f"{derniere_reelle.iloc[-1]['Reel']:.1f}")
                else:
                    st.metric("Dernier réel connu", "en attente")
            with colonne_trois:
                if not derniere_reelle.empty:
                    erreur = abs(derniere_reelle.iloc[-1]["Reel"] - derniere_reelle.iloc[-1]["Prediction"])
                    st.metric("Dernière erreur absolue", f"{erreur:.1f}")
                else:
                    st.metric("Dernière erreur absolue", "en attente")

            figure = go.Figure()
            reel = agrege.dropna(subset=["Reel"])
            figure.add_trace(go.Scatter(
                x=reel["Date"], y=reel["Reel"],
                mode="lines+markers", name="Réel", line=dict(color=PALETTE["navy"], width=2.5), marker=dict(size=5),
            ))
            figure.add_trace(go.Scatter(
                x=agrege["Date"], y=agrege["Prediction"],
                mode="lines+markers", name="Prédiction", line=dict(color=PALETTE["orange"], width=2.5), marker=dict(size=5),
            ))
            _mise_en_forme(figure, titre=titre_graphe, hauteur=400)
            figure.update_xaxes(title_text="Date")
            figure.update_yaxes(title_text=info["libelle_court"])
            st.plotly_chart(figure, use_container_width=True)

        elif liaison_est_all:
            agrege = sous_ensemble.groupby("LiaisonId", as_index=False).agg({"Reel": fonction_agg, "Prediction": fonction_agg})
            agrege["Ecart"] = agrege["Prediction"] - agrege["Reel"]
            agrege = agrege.sort_values("Prediction", ascending=False)

            colonne_un, colonne_deux, colonne_trois = st.columns(3)
            with colonne_un:
                st.metric("Liaisons concernées", len(agrege))
            with colonne_deux:
                st.metric("Total prédiction", f"{agrege['Prediction'].sum():.1f}")
            with colonne_trois:
                reel_connu = agrege.dropna(subset=["Reel"])
                valeur = f"{reel_connu['Reel'].sum():.1f}" if not reel_connu.empty else "en attente"
                st.metric("Total réel connu", valeur)

            nb_affichees = 25
            top = agrege.head(nb_affichees)
            figure = go.Figure()
            figure.add_trace(go.Bar(x=top["LiaisonId"], y=top["Reel"], name="Réel", marker_color=PALETTE["navy"]))
            figure.add_trace(go.Bar(x=top["LiaisonId"], y=top["Prediction"], name="Prédiction", marker_color=PALETTE["orange"]))
            figure.update_layout(barmode="group")
            _mise_en_forme(figure, titre=f"{titre_graphe} — Top {nb_affichees} liaisons", hauteur=420)
            figure.update_xaxes(title_text="Liaison", type="category")
            figure.update_yaxes(title_text=info["libelle_court"])
            st.plotly_chart(figure, use_container_width=True)

            with st.expander(f"Table complète des liaisons ({len(agrege)})", expanded=True):
                st.dataframe(agrege, use_container_width=True, hide_index=True)

        else:
            if heure_est_all:
                serie_horaire = sous_ensemble.sort_values("Heure")
                total_reel = serie_horaire["Reel"].sum()
                total_prediction = serie_horaire["Prediction"].sum()

                st.caption(titre_graphe)
                colonne_un, colonne_deux, colonne_trois = st.columns(3)
                with colonne_un:
                    st.metric("Total prédiction", f"{total_prediction:.1f}")
                with colonne_deux:
                    reel_connu = serie_horaire.dropna(subset=["Reel"])
                    valeur = f"{total_reel:.1f}" if not reel_connu.empty else "en attente"
                    st.metric("Total réel", valeur)
                with colonne_trois:
                    reel_connu = serie_horaire.dropna(subset=["Reel"])
                    valeur = f"{(total_prediction - total_reel):+.1f}" if not reel_connu.empty else "—"
                    st.metric("Écart total", valeur)

                figure = go.Figure()
                figure.add_trace(go.Bar(x=serie_horaire["Heure"], y=serie_horaire["Reel"], name="Réel", marker_color=PALETTE["navy"]))
                figure.add_trace(go.Bar(x=serie_horaire["Heure"], y=serie_horaire["Prediction"], name="Prédiction", marker_color=PALETTE["orange"]))
                figure.update_layout(barmode="group")
                _mise_en_forme(figure, titre=titre_graphe, hauteur=380)
                figure.update_xaxes(title_text="Heure", type="category")
                figure.update_yaxes(title_text=info["libelle_court"])
                st.plotly_chart(figure, use_container_width=True)
            else:
                ligne = sous_ensemble.iloc[0]
                valeur_reelle = ligne["Reel"]
                valeur_prediction = ligne["Prediction"]
                ecart = abs(valeur_reelle - valeur_prediction) if pd.notna(valeur_reelle) else None

                st.caption(titre_graphe)
                colonne_un, colonne_deux, colonne_trois = st.columns(3)
                with colonne_un:
                    st.metric("Prédiction", f"{valeur_prediction:.1f}")
                with colonne_deux:
                    st.metric("Réel", f"{valeur_reelle:.1f}" if pd.notna(valeur_reelle) else "en attente")
                with colonne_trois:
                    st.metric("Erreur absolue", f"{ecart:.1f}" if ecart is not None else "—")

        with st.expander("Table détaillée", expanded=True):
            colonnes = [c for c in ["Date", "Heure", "LiaisonId", info["colonne_categorie"], "Prediction", "DateCalculPrediction", "Reel", "ErreurAbsolue"] if c and c in sous_ensemble.columns]
            st.dataframe(sous_ensemble[colonnes].sort_values("Date", ascending=False), use_container_width=True, hide_index=True)