import difflib

from config.chatbot import MOTS_CLES_INTENTION, MOTS_CLES_MODELE
from utils.chatbot import contexte as module_contexte
from utils.chatbot import extraction, normalisation, reponses

VOCABULAIRE = normalisation.construire_vocabulaire(MOTS_CLES_MODELE, MOTS_CLES_INTENTION)

QUESTIONS_REFERENCE = [
    "performance du modele billets vendus",
    "anomalies sur le taux de fraude",
    "derniere prediction du taux de controle",
    "variables importantes du modele fraude",
    "comparaison inter annees du taux de fraude",
    "saisonnalite sur la liaison",
    "calendrier des ecarts",
    "dernier traitement du pipeline",
    "liste des rapports generes",
    "generer un rapport",
]


def _suggestion_proche(texte_normalise):
    correspondance = difflib.get_close_matches(texte_normalise, QUESTIONS_REFERENCE, n=1, cutoff=0.35)
    return correspondance[0] if correspondance else None


def _taguer(reponse, intention):
    if isinstance(reponse, dict):
        reponse["categorie"] = intention
    return reponse


def repondre_texte_libre(message, session_state, liaisons_connues):
    texte_normalise = normalisation.normaliser_texte(message)
    texte_corrige = normalisation.corriger_mots(texte_normalise, VOCABULAIRE)
    slots = extraction.extraire_slots(texte_corrige, liaisons_connues)

    contexte_session = module_contexte.obtenir_contexte(session_state)
    cle_modele = slots["cle_modele"] or contexte_session["dernier_modele"]
    liaison = slots["liaison"] or contexte_session["derniere_liaison"]
    intention = slots["intention"]
    borne_debut, borne_fin = extraction.periode_vers_bornes(slots["periode"])

    if intention == "aide":
        return _taguer(reponses.reponse_aide(), "aide")

    if intention == "pipeline":
        return _taguer(reponses.reponse_pipeline(), "pipeline")

    if intention == "rapports":
        if any(mot in texte_corrige for mot in ["genere", "generer", "creer", "nouveau rapport"]):
            return _taguer(reponses.reponse_generer_rapport(), "rapports")
        return _taguer(reponses.reponse_liste_rapports(), "rapports")

    if cle_modele is None:
        suggestion = _suggestion_proche(texte_corrige)
        return reponses.reponse_repli(suggestion)

    module_contexte.mettre_a_jour_contexte(session_state, cle_modele=cle_modele, liaison=liaison)

    if intention == "performance":
        return _taguer(reponses.reponse_performance(cle_modele), "performance")

    if intention == "anomalies":
        return _taguer(
            reponses.reponse_anomalies(cle_modele, liaison=liaison, borne_debut=borne_debut, borne_fin=borne_fin),
            "anomalies",
        )

    if intention == "predictions":
        return _taguer(
            reponses.reponse_predictions(cle_modele, liaison=liaison, borne_debut=borne_debut, borne_fin=borne_fin),
            "predictions",
        )

    if intention == "explicabilite":
        return _taguer(reponses.reponse_explicabilite(cle_modele), "explicabilite")

    if intention == "comparaison":
        if "calendrier" in texte_corrige:
            return _taguer(reponses.reponse_calendrier(cle_modele), "comparaison")
        if "saisonnalite" in texte_corrige or "saisonnier" in texte_corrige:
            return _taguer(reponses.reponse_saisonnalite(cle_modele, liaison), "comparaison")
        return _taguer(reponses.reponse_comparaison(cle_modele, liaison=liaison), "comparaison")

    suggestion = _suggestion_proche(texte_corrige)
    return reponses.reponse_repli(suggestion)