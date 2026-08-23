import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config.chemins import RAPPORTS
from config.modeles import MODELES, horizons_disponibles
from utils.chargement import (
    charger_anomalies,
    charger_calendrier_quotidien_dynamique,
    charger_comparaison_inter_annees_dynamique,
    charger_importance_features,
    charger_importance_shap,
    charger_metriques,
    charger_predictions_completes,
    charger_predictions_nouvelles_multi_horizon,
    charger_saisonnalite,
    dernier_log_execution,
)
from utils.liaisons import ajouter_colonne_nom_liaison, libelle_liaison
from utils.rapport import generer_rapport_hebdomadaire
from utils.style import PALETTE

LIBELLES_METRIQUES = {
    "RMSE": "RMSE", "MAE": "MAE", "MedAE": "MedAE",
    "WMAPE": "WMAPE (%)", "LogLossComposition": "Perte log",
}
MOIS_ABREGES = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin", "Juil", "Aout", "Sep", "Oct", "Nov", "Dec"]


def _fonction_agregation(famille):
    return "sum" if famille == "comptages" else "mean"


def _reponse(texte, metriques=None, tableau=None, figure=None, figure_secondaire=None, fichier_telechargement=None):
    return {
        "texte": texte,
        "metriques": metriques,
        "tableau": tableau,
        "figure": figure,
        "figure_secondaire": figure_secondaire,
        "fichier_telechargement": fichier_telechargement,
        "categorie": None,
    }


def _mise_en_forme(figure, titre=None, hauteur=360):
    figure.update_layout(
        template="plotly_white",
        title=dict(text=titre, x=0.01, xanchor="left") if titre else None,
        height=hauteur,
        margin=dict(l=10, r=10, t=48 if titre else 20, b=10),
        plot_bgcolor=PALETTE["surface"],
        paper_bgcolor=PALETTE["surface"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return figure


def reponse_performance(cle_modele):
    info = MODELES[cle_modele]
    metriques = charger_metriques(cle_modele)

    if not metriques:
        return _reponse(f"Aucune métrique disponible pour {info['libelle']}.")
    retenues = {
        LIBELLES_METRIQUES[cle]: round(valeur, 3) if isinstance(valeur, float) else valeur
        for cle, valeur in metriques.items() if cle in LIBELLES_METRIQUES
    }
    return _reponse(f"Performance du modèle **{info['libelle']}** (J+1) :", metriques=retenues)


def reponse_anomalies(cle_modele, liaison=None, borne_debut=None, borne_fin=None):
    info = MODELES[cle_modele]
    anomalies = charger_anomalies(cle_modele)

    if anomalies.empty:
        return _reponse(f"Aucune donnée d'anomalie disponible pour {info['libelle']}.")

    anomalies = anomalies.copy()
    if liaison and "LiaisonId" in anomalies.columns:
        anomalies = anomalies[anomalies["LiaisonId"].astype(str) == str(liaison)]
    if borne_debut is not None and "Date" in anomalies.columns:
        anomalies["Date"] = pd.to_datetime(anomalies["Date"])
        anomalies = anomalies[(anomalies["Date"].dt.date >= borne_debut) & (anomalies["Date"].dt.date <= borne_fin)]

    detectees = anomalies[anomalies["EstAnomalie"]] if "EstAnomalie" in anomalies.columns else anomalies.iloc[0:0]
    nombre = len(detectees)

    suffixe_liaison = f" sur la liaison {libelle_liaison(liaison)}" if liaison else ""
    suffixe_periode = f" entre le {borne_debut.strftime('%d/%m/%Y')} et le {borne_fin.strftime('%d/%m/%Y')}" if borne_debut else ""
    texte = f"**{nombre}** anomalie(s) détectée(s) pour {info['libelle']}{suffixe_liaison}{suffixe_periode}."

    tableau = None
    if nombre:
        colonnes = [c for c in ["Date", "LiaisonId", info["cible"], "Prediction", "ErreurAbsolue"] if c in detectees.columns]
        tableau = detectees.sort_values("ErreurAbsolue", ascending=False)[colonnes].head(10)
        tableau = ajouter_colonne_nom_liaison(tableau)

    return _reponse(texte, tableau=tableau)


def reponse_predictions(cle_modele, liaison=None, horizon=None, heure=None):
    info = MODELES[cle_modele]
    horizon_normalise = horizon or 1
    horizons_valides = horizons_disponibles(cle_modele)

    if horizon_normalise not in horizons_valides:
        libelles = ", ".join(f"J+{h}" for h in horizons_valides)
        return _reponse(
            f"L'horizon J+{horizon_normalise} n'est pas disponible pour {info['libelle']}. "
            f"Horizons disponibles pour ce modèle : {libelles}."
        )

    multi = charger_predictions_nouvelles_multi_horizon(cle_modele)
    source = multi[multi["Horizon"] == horizon_normalise].copy() if not multi.empty else pd.DataFrame()

    if source.empty:
        return _reponse(f"Aucune prédiction générée pour {info['libelle']} à J+{horizon_normalise} pour le moment.")

    source["Date"] = pd.to_datetime(source["Date"])
    date_prediction = source["Date"].max()
    source = source[source["Date"] == date_prediction]

    granularite_horaire = info["granularite"] == "horaire" and "Heure" in source.columns
    if liaison and "LiaisonId" in source.columns:
        source = source[source["LiaisonId"].astype(str) == str(liaison)]
    if granularite_horaire and heure is not None:
        source = source[source["Heure"].astype(int) == heure]

    if source.empty:
        return _reponse("Aucune prédiction disponible pour cette sélection.")

    fonction_agg = _fonction_agregation(info["famille"])
    valeur = source["Prediction"].agg(fonction_agg)

    suffixe_liaison = f" — liaison {libelle_liaison(liaison)}" if liaison else " (toutes liaisons)"
    suffixe_heure = f", {heure}h" if granularite_horaire and heure is not None else ""
    texte = (
        f"Prédiction pour **{info['libelle']}**{suffixe_liaison}{suffixe_heure}, "
        f"horizon **J+{horizon_normalise}** (le {date_prediction.strftime('%d/%m/%Y')}) : **{valeur:.3f}**."
    )

    figure = None
    if not liaison and "LiaisonId" in source.columns and source["LiaisonId"].nunique() > 1:
        agrege_liaison = source.groupby("LiaisonId", as_index=False)["Prediction"].agg(fonction_agg)
        agrege_liaison = agrege_liaison.sort_values("Prediction", ascending=False).head(15)
        agrege_liaison = ajouter_colonne_nom_liaison(agrege_liaison)
        colonne_x = "Liaison" if "Liaison" in agrege_liaison.columns else "LiaisonId"
        figure = px.bar(agrege_liaison, x=colonne_x, y="Prediction", color_discrete_sequence=[PALETTE["orange"]])
        figure.update_xaxes(title_text="Liaison")
        figure.update_yaxes(title_text=info["libelle_court"])
        _mise_en_forme(figure, titre=f"Prédiction par liaison — {info['libelle']} — J+{horizon_normalise}", hauteur=380)

    colonnes = [c for c in ["Date", "LiaisonId", "Heure", "Prediction"] if c in source.columns]
    tableau = source.sort_values("Prediction", ascending=False)[colonnes].head(15)
    tableau = ajouter_colonne_nom_liaison(tableau)
    return _reponse(texte, tableau=tableau, figure=figure)


def reponse_historique(cle_modele, liaison=None, borne_debut=None, borne_fin=None, heure=None):
    info = MODELES[cle_modele]
    predictions = charger_predictions_completes(cle_modele)
    if predictions.empty:
        return _reponse(f"Aucune donnée historique disponible pour {info['libelle']}.")

    predictions = predictions.copy()
    predictions["Date"] = pd.to_datetime(predictions["Date"])
    predictions["LiaisonId"] = predictions["LiaisonId"].astype(str)
    cible = info["cible"]
    fonction_agg = _fonction_agregation(info["famille"])
    granularite_horaire = info["granularite"] == "horaire" and "Heure" in predictions.columns

    if liaison and "LiaisonId" in predictions.columns:
        predictions = predictions[predictions["LiaisonId"] == str(liaison)]
    if granularite_horaire and heure is not None:
        predictions = predictions[predictions["Heure"].astype(int) == heure]
    if borne_debut is not None:
        predictions = predictions[(predictions["Date"].dt.date >= borne_debut) & (predictions["Date"].dt.date <= borne_fin)]

    if predictions.empty:
        return _reponse("Aucune donnée disponible pour cette sélection.")

    agrege = predictions.groupby("Date", as_index=False).agg({cible: fonction_agg, "Prediction": fonction_agg}).sort_values("Date")
    derniere_reelle = agrege.dropna(subset=[cible])

    suffixe_liaison = f" — liaison {libelle_liaison(liaison)}" if liaison else " (toutes liaisons)"
    suffixe_heure = f", {heure}h" if granularite_horaire and heure is not None else ""
    suffixe_periode = (
        f" entre le {borne_debut.strftime('%d/%m/%Y')} et le {borne_fin.strftime('%d/%m/%Y')}"
        if borne_debut is not None else " (historique complet)"
    )
    texte = f"Historique réel vs prédiction pour **{info['libelle']}**{suffixe_liaison}{suffixe_heure}{suffixe_periode}."

    metriques = None
    if not derniere_reelle.empty:
        metriques = {
            "Dernier réel": f"{derniere_reelle.iloc[-1][cible]:.1f}",
            "Dernière prédiction": f"{agrege.iloc[-1]['Prediction']:.1f}",
        }

    figure = go.Figure()
    figure.add_trace(go.Scatter(x=agrege["Date"], y=agrege[cible], mode="lines", name="Réel", line=dict(color=PALETTE["navy"], width=2.5)))
    figure.add_trace(go.Scatter(x=agrege["Date"], y=agrege["Prediction"], mode="lines", name="Prédiction", line=dict(color=PALETTE["orange"], width=2.5)))
    _mise_en_forme(figure, titre=f"Réel vs Prédiction — {info['libelle']}{suffixe_liaison}{suffixe_heure}", hauteur=380)

    return _reponse(texte, metriques=metriques, figure=figure)


def reponse_explicabilite(cle_modele):
    info = MODELES[cle_modele]
    importance_features = charger_importance_features(cle_modele)
    importance_shap = charger_importance_shap(cle_modele)

    if importance_features.empty and importance_shap.empty:
        return _reponse(f"Aucune donnée d'explicabilité disponible pour {info['libelle']}.")

    source = importance_shap if not importance_shap.empty else importance_features
    if "ImportanceSHAP" in source.columns:
        colonne_valeur = "ImportanceSHAP"
    elif "Importance" in source.columns:
        colonne_valeur = "Importance"
    else:
        colonne_valeur = source.columns[-1]

    agregee = source.groupby("Feature")[colonne_valeur].mean().sort_values(ascending=False).head(10).reset_index()
    figure = px.bar(
        agregee, x=colonne_valeur, y="Feature", orientation="h",
        color_discrete_sequence=[PALETTE["orange"]],
    )
    figure.update_yaxes(categoryorder="total ascending", title_text="")
    _mise_en_forme(figure, titre=f"Variables les plus importantes — {info['libelle']}", hauteur=380)

    texte = f"Les variables les plus influentes pour **{info['libelle']}** sont présentées ci-dessous."
    return _reponse(texte, tableau=agregee, figure=figure)


def reponse_comparaison(cle_modele, liaison=None):
    info = MODELES[cle_modele]
    comparaison = charger_comparaison_inter_annees_dynamique(cle_modele)

    if comparaison.empty:
        return _reponse(f"Aucune donnée de comparaison inter-années disponible pour {info['libelle']}.")

    colonne_valeur = info["cible"] if info["cible"] in comparaison.columns else comparaison.columns[-1]
    comparaison = comparaison.copy()
    comparaison["Annee"] = comparaison["Annee"].astype(int).astype(str)
    comparaison["MoisLabel"] = comparaison["Mois"].astype(int).apply(lambda mois: MOIS_ABREGES[mois - 1])

    figure = px.bar(
        comparaison, x="MoisLabel", y=colonne_valeur, color="Annee", barmode="group",
        category_orders={"MoisLabel": MOIS_ABREGES},
    )
    _mise_en_forme(figure, titre=f"Comparaison inter-années — {info['libelle']}", hauteur=380)

    texte = f"Comparaison inter-années pour **{info['libelle']}**."

    figure_saison = None
    if liaison:
        saisonnalite = charger_saisonnalite(cle_modele)
        if not saisonnalite.empty:
            colonne_serie = saisonnalite[saisonnalite["LiaisonId"].astype(str) == str(liaison)] if "LiaisonId" in saisonnalite.columns else saisonnalite
            if not colonne_serie.empty and {"Date", "Tendance", "Saisonnalite"}.issubset(colonne_serie.columns):
                figure_saison = px.line(colonne_serie, x="Date", y=["Tendance", "Saisonnalite"])
                _mise_en_forme(figure_saison, titre=f"Tendance et saisonnalité — liaison {libelle_liaison(liaison)}", hauteur=320)
                texte += f" Décomposition saisonnière ajoutée pour la liaison {libelle_liaison(liaison)}."

    return _reponse(texte, figure=figure, figure_secondaire=figure_saison)


def reponse_saisonnalite(cle_modele, liaison):
    info = MODELES[cle_modele]
    if not liaison:
        return _reponse("Précisez une liaison pour afficher sa décomposition saisonnière.")

    saisonnalite = charger_saisonnalite(cle_modele)
    if saisonnalite.empty:
        return _reponse(f"Aucune donnée de saisonnalité disponible pour {info['libelle']}.")

    colonne_serie = saisonnalite[saisonnalite["LiaisonId"].astype(str) == str(liaison)] if "LiaisonId" in saisonnalite.columns else saisonnalite
    if colonne_serie.empty or not {"Date", "Tendance", "Saisonnalite"}.issubset(colonne_serie.columns):
        return _reponse(f"Aucune décomposition saisonnière disponible pour la liaison {liaison}.")

    figure = px.line(colonne_serie, x="Date", y=["Tendance", "Saisonnalite"])
    _mise_en_forme(figure, titre=f"Tendance et saisonnalité — {info['libelle']} — liaison {libelle_liaison(liaison)}", hauteur=380)
    return _reponse(
        f"Décomposition saisonnière pour **{info['libelle']}**, liaison {libelle_liaison(liaison)}.",
        figure=figure,
    )


def reponse_calendrier(cle_modele):
    info = MODELES[cle_modele]
    calendrier = charger_calendrier_quotidien_dynamique(cle_modele)

    if calendrier.empty:
        return _reponse(f"Aucun calendrier d'écarts disponible pour {info['libelle']}.")

    calendrier = calendrier.copy()
    calendrier["Date"] = pd.to_datetime(calendrier["Date"])
    calendrier["Semaine"] = calendrier["Date"].dt.strftime("Sem. %V")
    calendrier["JourSemaine"] = calendrier["Date"].dt.dayofweek

    if "Ecart" not in calendrier.columns and {"Prediction", info["cible"]}.issubset(calendrier.columns):
        calendrier["Ecart"] = calendrier["Prediction"] - calendrier[info["cible"]]

    figure = px.density_heatmap(
        calendrier, x="Semaine", y="JourSemaine", z="Ecart",
        color_continuous_midpoint=0,
        color_continuous_scale=[PALETTE["steel"], PALETTE["surface"], PALETTE["red"]],
    )
    figure.update_yaxes(tickmode="array", tickvals=list(range(7)), autorange="reversed", title_text="")
    figure.update_xaxes(title_text="")
    _mise_en_forme(figure, titre=f"Calendrier quotidien des écarts — {info['libelle']}", hauteur=340)

    return _reponse(
        f"Calendrier quotidien des écarts (prédiction − réel) pour **{info['libelle']}**.",
        figure=figure,
    )


def reponse_pipeline():
    log = dernier_log_execution()
    if not log:
        return _reponse("Aucune exécution du pipeline n'a encore été enregistrée.")

    statut = log.get("statut", "inconnu")
    texte = (
        f"Dernière exécution du pipeline le **{log.get('horodatage', '—')}** — statut **{statut}**. "
        f"{log.get('fichiers_traites', 0)} fichier(s) traité(s), date traitée : {log.get('date_traitee', '—')}, "
        f"date prédite : {log.get('date_predite', '—')}."
    )

    liaisons_inconnues = log.get("liaisons_inconnues") or {}
    if liaisons_inconnues:
        total = sum(len(valeurs) for valeurs in liaisons_inconnues.values())
        texte += f" **{total}** liaison(s) inconnue(s) détectée(s) lors de ce traitement."

    colonnes_manquantes = log.get("colonnes_manquantes") or {}
    if colonnes_manquantes:
        texte += f" Colonnes manquantes signalées sur {len(colonnes_manquantes)} fichier(s)."

    return _reponse(texte)


def reponse_liste_rapports():
    if not os.path.isdir(RAPPORTS):
        return _reponse("Aucun rapport n'a encore été généré.")

    fichiers = sorted([nom for nom in os.listdir(RAPPORTS) if nom.endswith(".pdf")], reverse=True)
    if not fichiers:
        return _reponse("Aucun rapport n'a encore été généré.")

    lignes = []
    for nom in fichiers:
        chemin = os.path.join(RAPPORTS, nom)
        stats = os.stat(chemin)
        lignes.append({"Fichier": nom, "Généré le": datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M")})

    tableau = pd.DataFrame(lignes)
    return _reponse(f"**{len(fichiers)}** rapport(s) disponible(s).", tableau=tableau)


def reponse_generer_rapport():
    chemin = generer_rapport_hebdomadaire()
    return _reponse(
        f"Nouveau rapport hebdomadaire généré : **{os.path.basename(chemin)}**.",
        fichier_telechargement=chemin,
    )


def reponse_aide():
    texte = (
        "Je peux répondre sur la performance, les anomalies, l'explicabilité et les comparaisons/tendances "
        "(toujours à J+1), sur l'historique réel vs prédiction, sur l'état du pipeline et sur les rapports, "
        "pour les 7 modèles de la plateforme. Seules les prédictions supportent un horizon : J+1 à J+6 "
        "(calcul récursif, tous les modèles) ou J+7, J+15, J+30 (modèles dédiés, uniquement pour les billets "
        "vendus et les billets contrôlés) — par exemple « prédiction des billets vendus dans 7 jours ». "
        "Pour les modèles à granularité horaire, je peux aussi filtrer sur une heure précise, en prédiction "
        "comme en historique. Utilisez le parcours guidé ci-dessous ou consultez le guide du chatbot pour le "
        "détail des questions possibles."
    )
    return _reponse(texte)


def reponse_repli(suggestion=None):
    texte = (
        "Je n'ai pas identifié votre demande avec certitude. Précisez le sujet (performance, anomalies, "
        "prédictions, explicabilité, comparaison, pipeline, rapports) et éventuellement un modèle ou une liaison."
    )
    if suggestion:
        texte += f" Vouliez-vous dire : *{suggestion}* ?"
    return _reponse(texte)