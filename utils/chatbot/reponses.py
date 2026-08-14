import os
from datetime import datetime

import pandas as pd
import plotly.express as px

from config.chemins import RAPPORTS
from config.modeles import MODELES
from utils.chargement import (
    charger_anomalies,
    charger_calendrier_quotidien,
    charger_comparaison_inter_annees,
    charger_importance_features,
    charger_importance_shap,
    charger_metriques,
    charger_predictions,
    charger_predictions_nouvelles,
    charger_saisonnalite,
    dernier_log_execution,
)
from utils.rapport import generer_rapport_hebdomadaire
from utils.style import PALETTE

LIBELLES_METRIQUES = {
    "RMSE": "RMSE", "MAE": "MAE", "MedAE": "MedAE",
    "WMAPE": "WMAPE (%)", "LogLossComposition": "Perte log",
}
MOIS_ABREGES = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin", "Juil", "Aout", "Sep", "Oct", "Nov", "Dec"]


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
    return _reponse(f"Performance du modèle **{info['libelle']}** :", metriques=retenues)


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

    suffixe_liaison = f" sur la liaison {liaison}" if liaison else ""
    suffixe_periode = f" entre le {borne_debut.strftime('%d/%m/%Y')} et le {borne_fin.strftime('%d/%m/%Y')}" if borne_debut else ""
    texte = f"**{nombre}** anomalie(s) détectée(s) pour {info['libelle']}{suffixe_liaison}{suffixe_periode}."

    tableau = None
    if nombre:
        colonnes = [c for c in ["Date", "LiaisonId", info["cible"], "Prediction", "ErreurAbsolue"] if c in detectees.columns]
        tableau = detectees.sort_values("ErreurAbsolue", ascending=False)[colonnes].head(10)

    return _reponse(texte, tableau=tableau)


def reponse_predictions(cle_modele, liaison=None, borne_debut=None, borne_fin=None):
    info = MODELES[cle_modele]
    nouvelles = charger_predictions_nouvelles(cle_modele)
    source = nouvelles if not nouvelles.empty else charger_predictions(cle_modele)
    if source.empty:
        return _reponse(f"Aucune prédiction disponible pour {info['libelle']}.")

    source = source.copy()
    source["Date"] = pd.to_datetime(source["Date"])
    if liaison and "LiaisonId" in source.columns:
        source = source[source["LiaisonId"].astype(str) == str(liaison)]
    if borne_debut is not None:
        source = source[(source["Date"].dt.date >= borne_debut) & (source["Date"].dt.date <= borne_fin)]

    if source.empty:
        return _reponse("Aucune prédiction disponible pour cette sélection.")

    derniere = source.sort_values("Date").iloc[-1]
    suffixe = f" sur la liaison {liaison}" if liaison else ""
    texte = f"Dernière prédiction pour **{info['libelle']}**{suffixe} : **{derniere['Prediction']:.3f}** au {derniere['Date'].strftime('%d/%m/%Y')}."

    colonnes = [c for c in ["Date", "LiaisonId", "Prediction", "Reel"] if c in source.columns]
    tableau = source.sort_values("Date", ascending=False)[colonnes].head(10)
    return _reponse(texte, tableau=tableau)


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
    comparaison = charger_comparaison_inter_annees(cle_modele)
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
                _mise_en_forme(figure_saison, titre=f"Tendance et saisonnalité — liaison {liaison}", hauteur=320)
                texte += f" Décomposition saisonnière ajoutée pour la liaison {liaison}."

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
    _mise_en_forme(figure, titre=f"Tendance et saisonnalité — {info['libelle']} — liaison {liaison}", hauteur=380)
    return _reponse(f"Décomposition saisonnière pour **{info['libelle']}**, liaison {liaison}.", figure=figure)


def reponse_calendrier(cle_modele):
    info = MODELES[cle_modele]
    calendrier = charger_calendrier_quotidien(cle_modele)
    if calendrier.empty:
        return _reponse(f"Aucun calendrier d'écarts disponible pour {info['libelle']}.")

    calendrier = calendrier.copy()
    calendrier["Date"] = pd.to_datetime(calendrier["Date"])
    calendrier["Semaine"] = calendrier["Date"].dt.strftime("Sem. %V")
    calendrier["JourSemaine"] = calendrier["Date"].dt.dayofweek

    figure = px.density_heatmap(
        calendrier, x="Semaine", y="JourSemaine", z="Ecart",
        color_continuous_midpoint=0,
        color_continuous_scale=[PALETTE["steel"], PALETTE["surface"], PALETTE["red"]],
    )
    figure.update_yaxes(tickmode="array", tickvals=list(range(7)), autorange="reversed", title_text="")
    figure.update_xaxes(title_text="")
    _mise_en_forme(figure, titre=f"Calendrier quotidien des écarts — {info['libelle']}", hauteur=340)

    return _reponse(f"Calendrier quotidien des écarts (prédiction − réel) pour **{info['libelle']}**.", figure=figure)


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
        "Je peux répondre sur la performance, les anomalies, les prédictions, l'explicabilité, "
        "les comparaisons et tendances, l'état du pipeline et les rapports, pour les 7 modèles de la plateforme. "
        "Utilisez le parcours guidé ci-dessous ou consultez le guide du chatbot pour le détail des questions possibles."
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