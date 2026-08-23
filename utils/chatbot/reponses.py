import os
from datetime import datetime

import pandas as pd
import plotly.express as px

from config.chemins import RAPPORTS
from config.modeles import HORIZONS_DEDIES, MODELES, horizon_est_dedie, horizons_disponibles
from utils.chargement import (
    charger_anomalies,
    charger_anomalies_horizon,
    charger_calendrier_quotidien_dynamique,
    charger_calendrier_quotidien_horizon,
    charger_comparaison_inter_annees_dynamique,
    charger_comparaison_inter_annees_horizon,
    charger_importance_features,
    charger_importance_features_horizon,
    charger_importance_shap,
    charger_importance_shap_horizon,
    charger_metriques,
    charger_metriques_horizon,
    charger_predictions,
    charger_predictions_nouvelles,
    charger_predictions_nouvelles_multi_horizon,
    charger_predictions_test_horizon,
    charger_saisonnalite,
    charger_saisonnalite_horizon,
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


def _horizon_normalise(horizon):
    """Ramene un horizon absent ou egal a 1 (J+1, comportement par defaut du
    modele standard) a None, pour ne pas alourdir inutilement les textes de
    reponse et pour reutiliser les chargements non-horizon existants."""
    if horizon is None or horizon == 1:
        return None
    return horizon


def _suffixe_horizon(horizon):
    horizon_normalise = _horizon_normalise(horizon)
    if horizon_normalise is None:
        return ""
    return f" — horizon J+{horizon_normalise}"


def _message_horizon_indisponible(cle_modele, horizon):
    info = MODELES[cle_modele]
    if horizon in HORIZONS_DEDIES:
        return _reponse(
            f"Les horizons J+7, J+15 et J+30 s'appuient sur des modèles dédiés, disponibles uniquement pour "
            f"les modèles Billets vendus et Billets contrôlés. Aucune donnée détaillée n'existe à J+{horizon} "
            f"pour {info['libelle']} ; seules les prédictions récursives (J+1 à J+6) sont calculées pour ce modèle."
        )
    return _reponse(
        f"Seules les prédictions sont calculées pour l'horizon J+{horizon} (méthode récursive). "
        f"Les métriques, anomalies, l'explicabilité et les comparaisons détaillées ne sont disponibles qu'à "
        f"J+1 par défaut, ou à J+7 / J+15 / J+30 pour les modèles Billets vendus et Billets contrôlés."
    )


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


def reponse_performance(cle_modele, horizon=None):
    info = MODELES[cle_modele]
    horizon_normalise = _horizon_normalise(horizon)

    if horizon_normalise is not None:
        if not horizon_est_dedie(cle_modele, horizon_normalise):
            return _message_horizon_indisponible(cle_modele, horizon_normalise)
        metriques = charger_metriques_horizon(cle_modele, horizon_normalise)
    else:
        metriques = charger_metriques(cle_modele)

    if not metriques:
        return _reponse(f"Aucune métrique disponible pour {info['libelle']}{_suffixe_horizon(horizon_normalise)}.")
    retenues = {
        LIBELLES_METRIQUES[cle]: round(valeur, 3) if isinstance(valeur, float) else valeur
        for cle, valeur in metriques.items() if cle in LIBELLES_METRIQUES
    }
    return _reponse(f"Performance du modèle **{info['libelle']}**{_suffixe_horizon(horizon_normalise)} :", metriques=retenues)


def reponse_anomalies(cle_modele, liaison=None, borne_debut=None, borne_fin=None, horizon=None):
    info = MODELES[cle_modele]
    horizon_normalise = _horizon_normalise(horizon)

    if horizon_normalise is not None:
        if not horizon_est_dedie(cle_modele, horizon_normalise):
            return _message_horizon_indisponible(cle_modele, horizon_normalise)
        anomalies = charger_anomalies_horizon(cle_modele, horizon_normalise)
    else:
        anomalies = charger_anomalies(cle_modele)

    if anomalies.empty:
        return _reponse(f"Aucune donnée d'anomalie disponible pour {info['libelle']}{_suffixe_horizon(horizon_normalise)}.")

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
    texte = (
        f"**{nombre}** anomalie(s) détectée(s) pour {info['libelle']}{suffixe_liaison}{suffixe_periode}"
        f"{_suffixe_horizon(horizon_normalise)}."
    )

    tableau = None
    if nombre:
        colonnes = [c for c in ["Date", "LiaisonId", info["cible"], "Prediction", "ErreurAbsolue"] if c in detectees.columns]
        tableau = detectees.sort_values("ErreurAbsolue", ascending=False)[colonnes].head(10)
        tableau = ajouter_colonne_nom_liaison(tableau)

    return _reponse(texte, tableau=tableau)


def reponse_predictions(cle_modele, liaison=None, borne_debut=None, borne_fin=None, horizon=None):
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
        if horizon_normalise == 1:
            source = charger_predictions(cle_modele)
        elif horizon_est_dedie(cle_modele, horizon_normalise):
            source = charger_predictions_test_horizon(cle_modele, horizon_normalise)

    if source.empty:
        return _reponse(f"Aucune prédiction disponible pour {info['libelle']}{_suffixe_horizon(horizon_normalise)}.")

    source = source.copy()
    source["Date"] = pd.to_datetime(source["Date"])
    if liaison and "LiaisonId" in source.columns:
        source = source[source["LiaisonId"].astype(str) == str(liaison)]
    if borne_debut is not None:
        source = source[(source["Date"].dt.date >= borne_debut) & (source["Date"].dt.date <= borne_fin)]

    if source.empty:
        return _reponse("Aucune prédiction disponible pour cette sélection.")

    derniere = source.sort_values("Date").iloc[-1]
    suffixe_liaison = f" sur la liaison {libelle_liaison(liaison)}" if liaison else ""
    texte = (
        f"Dernière prédiction pour **{info['libelle']}**{suffixe_liaison}{_suffixe_horizon(horizon_normalise)} : "
        f"**{derniere['Prediction']:.3f}** au {derniere['Date'].strftime('%d/%m/%Y')}."
    )

    colonnes = [c for c in ["Date", "LiaisonId", "Prediction", "Reel"] if c in source.columns]
    tableau = source.sort_values("Date", ascending=False)[colonnes].head(10)
    tableau = ajouter_colonne_nom_liaison(tableau)
    return _reponse(texte, tableau=tableau)


def reponse_explicabilite(cle_modele, horizon=None):
    info = MODELES[cle_modele]
    horizon_normalise = _horizon_normalise(horizon)

    if horizon_normalise is not None:
        if not horizon_est_dedie(cle_modele, horizon_normalise):
            return _message_horizon_indisponible(cle_modele, horizon_normalise)
        importance_features = charger_importance_features_horizon(cle_modele, horizon_normalise)
        importance_shap = charger_importance_shap_horizon(cle_modele, horizon_normalise)
    else:
        importance_features = charger_importance_features(cle_modele)
        importance_shap = charger_importance_shap(cle_modele)

    if importance_features.empty and importance_shap.empty:
        return _reponse(f"Aucune donnée d'explicabilité disponible pour {info['libelle']}{_suffixe_horizon(horizon_normalise)}.")

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
    _mise_en_forme(figure, titre=f"Variables les plus importantes — {info['libelle']}{_suffixe_horizon(horizon_normalise)}", hauteur=380)

    texte = f"Les variables les plus influentes pour **{info['libelle']}**{_suffixe_horizon(horizon_normalise)} sont présentées ci-dessous."
    return _reponse(texte, tableau=agregee, figure=figure)


def reponse_comparaison(cle_modele, liaison=None, horizon=None):
    info = MODELES[cle_modele]
    horizon_normalise = _horizon_normalise(horizon)

    if horizon_normalise is not None:
        if not horizon_est_dedie(cle_modele, horizon_normalise):
            return _message_horizon_indisponible(cle_modele, horizon_normalise)
        comparaison = charger_comparaison_inter_annees_horizon(cle_modele, horizon_normalise)
    else:
        comparaison = charger_comparaison_inter_annees_dynamique(cle_modele)

    if comparaison.empty:
        return _reponse(f"Aucune donnée de comparaison inter-années disponible pour {info['libelle']}{_suffixe_horizon(horizon_normalise)}.")

    colonne_valeur = info["cible"] if info["cible"] in comparaison.columns else comparaison.columns[-1]
    comparaison = comparaison.copy()
    comparaison["Annee"] = comparaison["Annee"].astype(int).astype(str)
    comparaison["MoisLabel"] = comparaison["Mois"].astype(int).apply(lambda mois: MOIS_ABREGES[mois - 1])

    figure = px.bar(
        comparaison, x="MoisLabel", y=colonne_valeur, color="Annee", barmode="group",
        category_orders={"MoisLabel": MOIS_ABREGES},
    )
    _mise_en_forme(figure, titre=f"Comparaison inter-années — {info['libelle']}{_suffixe_horizon(horizon_normalise)}", hauteur=380)

    texte = f"Comparaison inter-années pour **{info['libelle']}**{_suffixe_horizon(horizon_normalise)}."

    figure_saison = None
    if liaison:
        saisonnalite = (
            charger_saisonnalite_horizon(cle_modele, horizon_normalise)
            if horizon_normalise is not None else charger_saisonnalite(cle_modele)
        )
        if not saisonnalite.empty:
            colonne_serie = saisonnalite[saisonnalite["LiaisonId"].astype(str) == str(liaison)] if "LiaisonId" in saisonnalite.columns else saisonnalite
            if not colonne_serie.empty and {"Date", "Tendance", "Saisonnalite"}.issubset(colonne_serie.columns):
                figure_saison = px.line(colonne_serie, x="Date", y=["Tendance", "Saisonnalite"])
                _mise_en_forme(figure_saison, titre=f"Tendance et saisonnalité — liaison {libelle_liaison(liaison)}{_suffixe_horizon(horizon_normalise)}", hauteur=320)
                texte += f" Décomposition saisonnière ajoutée pour la liaison {libelle_liaison(liaison)}."

    return _reponse(texte, figure=figure, figure_secondaire=figure_saison)


def reponse_saisonnalite(cle_modele, liaison, horizon=None):
    info = MODELES[cle_modele]
    if not liaison:
        return _reponse("Précisez une liaison pour afficher sa décomposition saisonnière.")

    horizon_normalise = _horizon_normalise(horizon)
    if horizon_normalise is not None:
        if not horizon_est_dedie(cle_modele, horizon_normalise):
            return _message_horizon_indisponible(cle_modele, horizon_normalise)
        saisonnalite = charger_saisonnalite_horizon(cle_modele, horizon_normalise)
    else:
        saisonnalite = charger_saisonnalite(cle_modele)

    if saisonnalite.empty:
        return _reponse(f"Aucune donnée de saisonnalité disponible pour {info['libelle']}{_suffixe_horizon(horizon_normalise)}.")

    colonne_serie = saisonnalite[saisonnalite["LiaisonId"].astype(str) == str(liaison)] if "LiaisonId" in saisonnalite.columns else saisonnalite
    if colonne_serie.empty or not {"Date", "Tendance", "Saisonnalite"}.issubset(colonne_serie.columns):
        return _reponse(f"Aucune décomposition saisonnière disponible pour la liaison {liaison}{_suffixe_horizon(horizon_normalise)}.")

    figure = px.line(colonne_serie, x="Date", y=["Tendance", "Saisonnalite"])
    _mise_en_forme(figure, titre=f"Tendance et saisonnalité — {info['libelle']} — liaison {libelle_liaison(liaison)}{_suffixe_horizon(horizon_normalise)}", hauteur=380)
    return _reponse(
        f"Décomposition saisonnière pour **{info['libelle']}**, liaison {libelle_liaison(liaison)}{_suffixe_horizon(horizon_normalise)}.",
        figure=figure,
    )


def reponse_calendrier(cle_modele, horizon=None):
    info = MODELES[cle_modele]
    horizon_normalise = _horizon_normalise(horizon)

    if horizon_normalise is not None:
        if not horizon_est_dedie(cle_modele, horizon_normalise):
            return _message_horizon_indisponible(cle_modele, horizon_normalise)
        calendrier = charger_calendrier_quotidien_horizon(cle_modele, horizon_normalise)
    else:
        calendrier = charger_calendrier_quotidien_dynamique(cle_modele)

    if calendrier.empty:
        return _reponse(f"Aucun calendrier d'écarts disponible pour {info['libelle']}{_suffixe_horizon(horizon_normalise)}.")

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
    _mise_en_forme(figure, titre=f"Calendrier quotidien des écarts — {info['libelle']}{_suffixe_horizon(horizon_normalise)}", hauteur=340)

    return _reponse(
        f"Calendrier quotidien des écarts (prédiction − réel) pour **{info['libelle']}**{_suffixe_horizon(horizon_normalise)}.",
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
        "Je peux répondre sur la performance, les anomalies, les prédictions, l'explicabilité, "
        "les comparaisons et tendances, l'état du pipeline et les rapports, pour les 7 modèles de la plateforme. "
        "Je peux aussi préciser un horizon de prédiction : J+1 à J+6 (calcul récursif, tous les modèles) ou "
        "J+7, J+15, J+30 (modèles dédiés, uniquement pour les billets vendus et les billets contrôlés) — "
        "par exemple « performance du modèle billets vendus à J+15 » ou « prédiction des billets contrôlés dans 7 jours ». "
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