import re

from config.modeles import MODELES
from utils.chargement import (
    charger_anomalies,
    charger_metriques,
    charger_predictions,
    charger_predictions_nouvelles,
)

MOTS_CLES_MODELE = {
    "modele1_ventes": ["billet vendu", "billets vendus", "nombre de billets"],
    "modele2_taux_vente_guichet": ["taux de vente", "guichet"],
    "modele4_part_confort": ["confort", "classe"],
    "modele3_controles": ["billet controle", "billets controles", "nombre de controles"],
    "modele5_taux_controle": ["taux de controle"],
    "modele6_taux_fraude": ["fraude"],
    "modele7_part_type": ["type de titre", "titre de transport"],
}

MOTS_CLES_ANOMALIE = ["anomalie", "ecart", "probleme"]
MOTS_CLES_METRIQUE = ["performance", "precision", "rmse", "mae", "fiabilite"]
MOTS_CLES_PREDICTION = ["prediction", "prevision", "demain", "prochain"]


def _normaliser(texte):
    texte = texte.lower()
    remplacements = {"é": "e", "è": "e", "ê": "e", "à": "a", "ô": "o", "î": "i", "ç": "c"}
    for source, cible in remplacements.items():
        texte = texte.replace(source, cible)
    return texte


def detecter_modele(texte_normalise):
    for cle_modele, mots in MOTS_CLES_MODELE.items():
        for mot in mots:
            if mot in texte_normalise:
                return cle_modele
    return None


def detecter_liaison(texte_normalise, liaisons_connues):
    for liaison in liaisons_connues:
        if str(liaison).lower() in texte_normalise:
            return liaison
    correspondance = re.search(r"liaison\s+([a-z0-9_-]+)", texte_normalise)
    if correspondance:
        return correspondance.group(1)
    return None


def repondre(message, liaisons_connues):
    texte_normalise = _normaliser(message)
    cle_modele = detecter_modele(texte_normalise)

    if cle_modele is None:
        return (
            "Je peux répondre sur les billets vendus, le taux de vente guichet, la répartition "
            "confort, les contrôles, le taux de contrôle, la fraude et la répartition par type de "
            "titre. Précisez le sujet et éventuellement une liaison."
        )

    info = MODELES[cle_modele]
    liaison = detecter_liaison(texte_normalise, liaisons_connues)

    if any(mot in texte_normalise for mot in MOTS_CLES_METRIQUE):
        metriques = charger_metriques(cle_modele)
        if not metriques:
            return f"Aucune métrique disponible pour {info['libelle']}."
        elements = ", ".join(f"{cle} : {round(valeur, 3) if isinstance(valeur, float) else valeur}" for cle, valeur in metriques.items() if cle in ("RMSE", "MAE", "WMAPE"))
        return f"Performance du modèle {info['libelle']} : {elements}."

    if any(mot in texte_normalise for mot in MOTS_CLES_ANOMALIE):
        anomalies = charger_anomalies(cle_modele)
        if anomalies.empty:
            return f"Aucune donnée d'anomalie disponible pour {info['libelle']}."
        if liaison:
            anomalies = anomalies[anomalies["LiaisonId"].astype(str) == str(liaison)]
        nombre = int(anomalies["EstAnomalie"].sum()) if "EstAnomalie" in anomalies.columns else 0
        suffixe = f" sur la liaison {liaison}" if liaison else ""
        return f"{nombre} anomalie(s) détectée(s) pour {info['libelle']}{suffixe}."

    if any(mot in texte_normalise for mot in MOTS_CLES_PREDICTION):
        nouvelles = charger_predictions_nouvelles(cle_modele)
        source = nouvelles if not nouvelles.empty else charger_predictions(cle_modele)
        if source.empty:
            return f"Aucune prédiction disponible pour {info['libelle']}."
        if liaison:
            source = source[source["LiaisonId"].astype(str) == str(liaison)]
        if source.empty:
            return f"Aucune prédiction disponible pour la liaison {liaison}."
        derniere = source.sort_values("Date").iloc[-1]
        suffixe = f" sur la liaison {liaison}" if liaison else ""
        return f"Dernière prédiction pour {info['libelle']}{suffixe} : {derniere['Prediction']:.1f} au {derniere['Date']}."

    return f"Je peux vous donner la performance, les anomalies ou la dernière prédiction pour {info['libelle']}. Précisez votre besoin."
