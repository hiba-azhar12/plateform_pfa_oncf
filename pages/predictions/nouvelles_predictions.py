import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.modeles import MODELES, MODELES_HORIZON_DEDIE, HORIZONS_DEDIES, horizons_disponibles
from utils.chargement import (
    charger_historique_complet,
    charger_predictions_nouvelles_multi_horizon,
    dernier_log_execution,
    liaisons_ordonnees_nouvelles_predictions,
)
from utils.composants import OPTION_TOUTES_HEURES, OPTION_TOUTES_LIAISONS, _fonction_agregation, _mise_en_forme
from utils.liaisons import formateur_selectbox_liaison, libelle_liaison, nom_liaison
from utils.style import PALETTE, bandeau_statut, entete
from utils.tendances import CADENCES, serie_journaliere, serie_tendance, valeur_comparaison

entete("Nouvelles Prédictions", "Prédiction des prochains jours (J+1 à J+15 selon le modèle), calculée chaque nuit à partir des dépôts quotidiens de données PDA")

COULEURS_HORIZON = {1: PALETTE["orange"], 7: PALETTE["steel"], 15: PALETTE["amber"]}


def _formater_valeur(valeur, famille):
    if valeur is None or pd.isna(valeur):
        return "—"
    if famille in ("taux", "composition"):
        return f"{valeur * 100:.1f} %"
    return f"{valeur:,.0f}".replace(",", " ")


def _formater_delta(valeur, famille):
    if valeur is None or pd.isna(valeur):
        return None
    if famille in ("taux", "composition"):
        return f"{valeur * 100:+.1f} pts"
    return f"{valeur:+,.0f}".replace(",", " ")


colonne_titre, colonne_bouton = st.columns([5, 1])
with colonne_bouton:
    if st.button("Actualiser", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

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
    elif statut == "succes_partiel":
        modeles_en_erreur = list(dernier.get("erreurs_modeles", {}).keys())
        detail = f" (modèle(s) en erreur : {', '.join(modeles_en_erreur)})" if modeles_en_erreur else ""
        bandeau_statut(
            "avertissement",
            f"Mise à jour partielle le {horodatage}{detail} — certaines prédictions ci-dessous peuvent être manquantes.",
        )
    elif statut == "aucune_donnee":
        bandeau_statut(
            "avertissement",
            f"Aucune donnée reçue lors de l'exécution du {horodatage}. "
            f"Dernière mise à jour disponible affichée ci-dessous.",
        )
    elif statut == "en_cours":
        bandeau_statut("avertissement", f"Traitement en cours depuis {horodatage} — les données ci-dessous datent du run précédent.")
    else:
        bandeau_statut(
            "erreur",
            f"Erreur lors du traitement du {horodatage} : {dernier.get('erreur', 'détail indisponible')}",
        )

    if dernier.get("alerte_continuite"):
        bandeau_statut("erreur", f"Anomalie de séquence détectée : {dernier['alerte_continuite']}")

libelles = [MODELES[cle]["libelle_court"] for cle in MODELES]
onglets = st.tabs(libelles)

for onglet, cle_modele in zip(onglets, MODELES.keys()):
    with onglet:
        info = MODELES[cle_modele]
        colonne_categorie = info["colonne_categorie"]
        fonction_agg = _fonction_agregation(info["famille"])
        libelle_agregat = "Total" if fonction_agg == "sum" else "Moyenne"
        modele_multihorizon = cle_modele in MODELES_HORIZON_DEDIE

        donnees_multi = charger_predictions_nouvelles_multi_horizon(cle_modele)
        if donnees_multi.empty:
            st.info("Aucune prédiction générée pour ce modèle pour le moment.")
            continue

        donnees_multi = donnees_multi.copy()
        donnees_multi["LiaisonId"] = donnees_multi["LiaisonId"].astype(str)
        donnees_multi["Reel"] = pd.to_numeric(donnees_multi["Reel"], errors="coerce")
        donnees_multi["Prediction"] = pd.to_numeric(donnees_multi["Prediction"], errors="coerce")
        granularite_horaire = info["granularite"] == "horaire" and "Heure" in donnees_multi.columns

        horizons_config = horizons_disponibles(cle_modele)
        lignes_horizon = []
        for horizon in horizons_config:
            sous_horizon = donnees_multi[donnees_multi["Horizon"] == horizon]
            if sous_horizon.empty:
                continue
            lignes_horizon.append((horizon, sous_horizon["Date"].max().date()))

        if not lignes_horizon:
            st.info("Aucune prédiction générée pour ce modèle pour le moment.")
            continue

        options_horizon = [f"{date_h.strftime('%d/%m/%Y')} (J+{h})" for h, date_h in lignes_horizon]
        choix_horizon = st.selectbox("Date de prédiction", options_horizon, key=f"nouvelle_horizon_{cle_modele}")
        indice_choisi = options_horizon.index(choix_horizon)
        horizon_selectionne, date_prediction = lignes_horizon[indice_choisi]

        donnees_h1 = donnees_multi[donnees_multi["Horizon"] == 1]
        dates_disponibles_h1 = sorted(donnees_h1["Date"].dt.date.unique())

        date_reconciliee = None
        for date_candidate in reversed(dates_disponibles_h1):
            if date_candidate >= date_prediction:
                continue
            if donnees_h1.loc[donnees_h1["Date"].dt.date == date_candidate, "Reel"].notna().any():
                date_reconciliee = date_candidate
                break

        sous_prediction = donnees_multi[
            (donnees_multi["Horizon"] == horizon_selectionne) & (donnees_multi["Date"].dt.date == date_prediction)
        ]
        horodatage_calcul = sous_prediction["DateCalculPrediction"].max()
        horodatage_texte = (
            pd.to_datetime(horodatage_calcul).strftime("%d/%m/%Y %H:%M") if pd.notna(horodatage_calcul) else "—"
        )

        st.markdown(f"### Prédiction pour le {date_prediction.strftime('%d/%m/%Y')} (J+{horizon_selectionne})")
        st.caption(f"Calculée lors du dernier traitement du pipeline, le {horodatage_texte}")

        with st.container(border=True, key=f"panneau_selection_nouvelle_{cle_modele}"):
            st.markdown("**Sélection**")
            poids = [2] + ([1] if colonne_categorie else []) + ([1] if granularite_horaire else [])
            colonnes_filtre = st.columns(poids)
            indice = 0

            with colonnes_filtre[indice]:
                liaisons = liaisons_ordonnees_nouvelles_predictions(cle_modele)
                options_liaison = [OPTION_TOUTES_LIAISONS] + liaisons
                liaison_choisie = st.selectbox(
                    "Liaison", options_liaison, key=f"nouvelle_liaison_{cle_modele}",
                    format_func=formateur_selectbox_liaison(OPTION_TOUTES_LIAISONS),
                )
            indice += 1

            if colonne_categorie and colonne_categorie in sous_prediction.columns:
                with colonnes_filtre[indice]:
                    categories = sorted(sous_prediction[colonne_categorie].astype(str).unique().tolist())
                    categorie_choisie = st.selectbox(colonne_categorie, categories, key=f"nouvelle_categorie_{cle_modele}")
                indice += 1
            else:
                categorie_choisie = None

            if granularite_horaire:
                with colonnes_filtre[indice]:
                    heures = sorted(sous_prediction["Heure"].astype(int).unique().tolist())
                    options_heure = [OPTION_TOUTES_HEURES] + heures
                    heure_choisie = st.selectbox("Heure", options_heure, key=f"nouvelle_heure_{cle_modele}")
            else:
                heure_choisie = None

        liaison_est_all = liaison_choisie == OPTION_TOUTES_LIAISONS
        heure_est_all = granularite_horaire and heure_choisie == OPTION_TOUTES_HEURES

        def _filtrer(table, categorie_choisie=categorie_choisie, colonne_categorie=colonne_categorie,
                     liaison_est_all=liaison_est_all, liaison_choisie=liaison_choisie,
                     granularite_horaire=granularite_horaire, heure_est_all=heure_est_all, heure_choisie=heure_choisie):
            filtre = pd.Series(True, index=table.index)
            if categorie_choisie is not None:
                filtre &= table[colonne_categorie].astype(str) == categorie_choisie
            if not liaison_est_all:
                filtre &= table["LiaisonId"] == liaison_choisie
            if granularite_horaire and not heure_est_all:
                filtre &= table["Heure"].astype(int) == heure_choisie
            return table[filtre]

        selection_prediction = _filtrer(sous_prediction).copy()

        titre_selection = info["libelle"]
        titre_selection += " — Toutes les liaisons (agrégé)" if liaison_est_all else f" — Liaison {libelle_liaison(liaison_choisie)}"
        if granularite_horaire:
            titre_selection += " — Toutes les heures" if heure_est_all else f" — {heure_choisie}h"
        titre_selection += f" — J+{horizon_selectionne}"

        valeur_prediction_globale = None

        if selection_prediction.empty:
            st.warning("Aucune donnée pour cette combinaison.")
        else:
            valeur_prediction_globale = selection_prediction["Prediction"].agg(fonction_agg)

            if liaison_est_all:
                agrege = selection_prediction.groupby("LiaisonId", as_index=False)["Prediction"].agg(fonction_agg)
                agrege = agrege.sort_values("Prediction", ascending=False)

                colonne_un, colonne_deux = st.columns(2)
                with colonne_un:
                    st.metric("Liaisons concernées", len(agrege))
                with colonne_deux:
                    st.metric(f"{libelle_agregat} prédiction", _formater_valeur(valeur_prediction_globale, info["famille"]))

                nb_affichees = 25
                top = agrege.head(nb_affichees).copy()
                top["LiaisonAffichee"] = top["LiaisonId"].map(nom_liaison)
                figure = go.Figure()
                figure.add_trace(go.Bar(x=top["LiaisonAffichee"], y=top["Prediction"], marker_color=PALETTE["orange"]))
                _mise_en_forme(figure, titre=f"{titre_selection} — Top {nb_affichees} liaisons (triées par prédiction)", hauteur=420, afficher_legende=False)
                figure.update_xaxes(title_text="Liaison", type="category")
                figure.update_yaxes(title_text=info["libelle_court"])
                st.plotly_chart(figure, use_container_width=True)

            elif granularite_horaire and heure_est_all:
                serie_horaire = selection_prediction.sort_values("Heure")

                st.caption(titre_selection)
                st.metric(f"{libelle_agregat} prédiction", _formater_valeur(valeur_prediction_globale, info["famille"]))

                figure = go.Figure()
                figure.add_trace(go.Bar(x=serie_horaire["Heure"], y=serie_horaire["Prediction"], marker_color=PALETTE["orange"]))
                _mise_en_forme(figure, titre=titre_selection, hauteur=360, afficher_legende=False)
                figure.update_xaxes(title_text="Heure", type="category")
                figure.update_yaxes(title_text=info["libelle_court"])
                st.plotly_chart(figure, use_container_width=True)

            else:
                st.caption(titre_selection)
                st.metric("Prédiction", _formater_valeur(valeur_prediction_globale, info["famille"]))

        st.markdown("**Comparaison avec les valeurs réelles passées**")
        st.caption(f"Référence : prédiction J+{horizon_selectionne} du {date_prediction.strftime('%d/%m/%Y')}")

        historique = charger_historique_complet(cle_modele)
        if not historique.empty:
            historique = historique.copy()
            historique["Date"] = pd.to_datetime(historique["Date"])
            historique["LiaisonId"] = historique["LiaisonId"].astype(str)

        colonne_valeur = info["cible"]
        filtres_tendance = dict(
            liaison_choisie=liaison_choisie, liaison_est_all=liaison_est_all,
            heure_choisie=heure_choisie, heure_est_all=heure_est_all,
            granularite_horaire=granularite_horaire,
            colonne_categorie=colonne_categorie, categorie_choisie=categorie_choisie,
        )

        libelles_cadence = {
            "semaine": "Même jour, semaine dernière",
            "mois": "Même jour, mois dernier",
            "annee": "Même jour, année dernière",
        }
        serie_jour = serie_journaliere(historique, colonne_valeur, fonction_agg, **filtres_tendance)

        colonnes_comparaison = st.columns(3)
        for cadence, colonne in zip(["semaine", "mois", "annee"], colonnes_comparaison):
            date_cible, valeur_historique = valeur_comparaison(serie_jour, date_prediction, cadence)
            with colonne:
                sous_titre = date_cible.strftime("%d/%m/%Y") if date_cible else "non disponible"
                if valeur_historique is None or valeur_prediction_globale is None:
                    st.metric(libelles_cadence[cadence], "en attente", help=f"Date de référence : {sous_titre}")
                else:
                    delta = valeur_prediction_globale - valeur_historique
                    st.metric(
                        libelles_cadence[cadence],
                        _formater_valeur(valeur_historique, info["famille"]),
                        delta=_formater_delta(delta, info["famille"]),
                        help=f"Réel du {sous_titre}, comparé à la prédiction du {date_prediction.strftime('%d/%m/%Y')}",
                    )

        index_cadence_defaut = 0 if horizon_selectionne <= 6 else 1
        cadence_selectionnee = st.selectbox(
            "Tendance affichée", options=["semaine", "mois", "annee"],
            format_func=lambda cle: CADENCES[cle]["libelle"], index=index_cadence_defaut,
            key=f"nouvelle_cadence_{cle_modele}",
        )

        if historique.empty or valeur_prediction_globale is None:
            st.info("Historique insuffisant pour tracer une tendance sur cette sélection.")
        else:
            serie = serie_tendance(serie_jour, date_prediction, cadence_selectionnee)
            figure = go.Figure()
            if not serie.empty:
                figure.add_trace(go.Scatter(
                    x=serie["Date"], y=serie["Valeur"], mode="lines+markers", name="Réel (historique)",
                    line=dict(color=PALETTE["navy"], width=2.5), marker=dict(size=6),
                ))
                figure.add_trace(go.Scatter(
                    x=[serie["Date"].iloc[-1], pd.Timestamp(date_prediction)],
                    y=[serie["Valeur"].iloc[-1], valeur_prediction_globale],
                    mode="lines", line=dict(color=PALETTE["orange"], width=2, dash="dot"),
                    showlegend=False, hoverinfo="skip",
                ))
            figure.add_trace(go.Scatter(
                x=[pd.Timestamp(date_prediction)], y=[valeur_prediction_globale],
                mode="markers", name=f"Prédiction J+{horizon_selectionne}", marker=dict(color=PALETTE["orange"], size=13, symbol="star"),
            ))
            _mise_en_forme(figure, titre=f"Tendance {CADENCES[cadence_selectionnee]['libelle'].lower()} — {titre_selection}", hauteur=360)
            figure.update_xaxes(title_text="Date")
            figure.update_yaxes(title_text=info["libelle_court"])
            st.plotly_chart(figure, use_container_width=True)

        st.divider()

        if date_reconciliee is None:
            st.info("Aucune journée n'a encore été réconciliée avec sa valeur réelle.")
            continue

        horizons_reconciliation = [1] + (HORIZONS_DEDIES if modele_multihorizon else [])
        selections_reconciliation = {}
        for horizon_r in horizons_reconciliation:
            sous_r = donnees_multi[
                (donnees_multi["Horizon"] == horizon_r) & (donnees_multi["Date"].dt.date == date_reconciliee)
            ]
            if sous_r.empty:
                continue
            selection_r = _filtrer(sous_r).copy()
            if not selection_r.empty:
                selections_reconciliation[horizon_r] = selection_r

        libelle_horizons_dispo = ", ".join(f"J+{h}" for h in selections_reconciliation)
        st.markdown(f"### Journée réconciliée : {date_reconciliee.strftime('%d/%m/%Y')}")
        st.caption(
            f"Prédiction(s) {libelle_horizons_dispo} contre réel pour cette même journée, sur la sélection ci-dessus. "
            "L'historique complet des journées réconciliées vit dans les dashboards Ventes / Contrôles."
        )

        if 1 not in selections_reconciliation:
            st.warning("Aucune donnée pour cette combinaison.")
            continue

        selection_reconciliee = selections_reconciliation[1]

        if liaison_est_all:
            agreges_par_horizon = {}
            for horizon_r, selection_r in selections_reconciliation.items():
                agrege_r = selection_r.groupby("LiaisonId", as_index=False).agg({"Reel": fonction_agg, "Prediction": fonction_agg})
                agreges_par_horizon[horizon_r] = agrege_r

            agrege_base = agreges_par_horizon[1].sort_values("Prediction", ascending=False)
            reel_connu = selection_reconciliee["Reel"].notna().any()

            colonne_un, colonne_deux, colonne_trois = st.columns(3)
            with colonne_un:
                st.metric("Liaisons concernées", len(agrege_base))
            with colonne_deux:
                valeur = selection_reconciliee["Reel"].agg(fonction_agg) if reel_connu else None
                st.metric(f"{libelle_agregat} réel", _formater_valeur(valeur, info["famille"]) if reel_connu else "en attente")
            with colonne_trois:
                st.metric(f"{libelle_agregat} prédiction J+1", _formater_valeur(selection_reconciliee["Prediction"].agg(fonction_agg), info["famille"]))

            top_liaisons = agrege_base.head(25)["LiaisonId"].tolist()
            top_liaisons_affichees = [nom_liaison(liaison) for liaison in top_liaisons]
            figure_r = go.Figure()
            figure_r.add_trace(go.Bar(
                x=top_liaisons_affichees,
                y=agrege_base.set_index("LiaisonId").reindex(top_liaisons)["Reel"],
                name="Réel", marker_color=PALETTE["navy"],
            ))
            for horizon_r, agrege_r in agreges_par_horizon.items():
                serie_liaisons = agrege_r.set_index("LiaisonId").reindex(top_liaisons)["Prediction"]
                figure_r.add_trace(go.Bar(
                    x=top_liaisons_affichees, y=serie_liaisons,
                    name=f"Prédiction J+{horizon_r}", marker_color=COULEURS_HORIZON.get(horizon_r, PALETTE["orange"]),
                ))
            figure_r.update_layout(barmode="group")
            _mise_en_forme(figure_r, titre=f"{titre_selection} — {date_reconciliee.strftime('%d/%m/%Y')}", hauteur=400)
            figure_r.update_xaxes(title_text="Liaison", type="category")
            figure_r.update_yaxes(title_text=info["libelle_court"])
            st.plotly_chart(figure_r, use_container_width=True)

        elif granularite_horaire and heure_est_all:
            series_par_horizon = {h: sel.sort_values("Heure") for h, sel in selections_reconciliation.items()}
            serie_base = series_par_horizon[1]
            reel_connu = serie_base["Reel"].notna().any()
            total_reel = serie_base["Reel"].agg(fonction_agg) if reel_connu else None
            total_pred = serie_base["Prediction"].agg(fonction_agg)

            colonne_un, colonne_deux, colonne_trois = st.columns(3)
            with colonne_un:
                st.metric(f"{libelle_agregat} réel", _formater_valeur(total_reel, info["famille"]) if reel_connu else "en attente")
            with colonne_deux:
                st.metric(f"{libelle_agregat} prédiction J+1", _formater_valeur(total_pred, info["famille"]))
            with colonne_trois:
                ecart = (total_pred - total_reel) if reel_connu else None
                st.metric("Écart J+1", _formater_delta(ecart, info["famille"]) or "—")

            figure_h = go.Figure()
            figure_h.add_trace(go.Bar(x=serie_base["Heure"], y=serie_base["Reel"], name="Réel", marker_color=PALETTE["navy"]))
            for horizon_r, serie_r in series_par_horizon.items():
                figure_h.add_trace(go.Bar(
                    x=serie_r["Heure"], y=serie_r["Prediction"],
                    name=f"Prédiction J+{horizon_r}", marker_color=COULEURS_HORIZON.get(horizon_r, PALETTE["orange"]),
                ))
            figure_h.update_layout(barmode="group")
            _mise_en_forme(figure_h, titre=f"{titre_selection} — {date_reconciliee.strftime('%d/%m/%Y')}", hauteur=360)
            figure_h.update_xaxes(title_text="Heure", type="category")
            figure_h.update_yaxes(title_text=info["libelle_court"])
            st.plotly_chart(figure_h, use_container_width=True)

        else:
            ligne = selection_reconciliee.iloc[0]
            valeur_reelle = ligne["Reel"]

            colonnes_metriques = st.columns(1 + len(selections_reconciliation))
            with colonnes_metriques[0]:
                st.metric("Réel", _formater_valeur(valeur_reelle, info["famille"]) if pd.notna(valeur_reelle) else "en attente")
            for position, (horizon_r, selection_r) in enumerate(selections_reconciliation.items(), start=1):
                valeur_prediction_r = selection_r.iloc[0]["Prediction"]
                ecart_r = abs(valeur_reelle - valeur_prediction_r) if pd.notna(valeur_reelle) else None
                with colonnes_metriques[position]:
                    st.metric(
                        f"Prédiction J+{horizon_r}",
                        _formater_valeur(valeur_prediction_r, info["famille"]),
                        delta=_formater_delta(ecart_r, info["famille"]) if ecart_r is not None else None,
                        delta_color="inverse",
                    )