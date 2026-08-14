import re
from datetime import datetime, timedelta

from config.chatbot import MOTS_CLES_INTENTION, MOTS_CLES_MODELE

MOTS_CLES_PERIODE = {
    "aujourd_hui": ["aujourd'hui", "aujourdhui", "ce jour"],
    "hier": ["hier"],
    "cette_semaine": ["cette semaine", "semaine derniere", "7 derniers jours"],
    "deux_semaines": ["deux dernieres semaines", "15 derniers jours", "quinze derniers jours"],
    "ce_mois": ["ce mois", "mois dernier", "30 derniers jours"],
}

MOTS_CLES_COMPARAISON = ["annee derniere", "vs annee derniere", "inter-annee", "inter annee", "comparer", "comparaison"]


def detecter_intention(texte_normalise):
    for intention, mots in MOTS_CLES_INTENTION.items():
        for mot in mots:
            if mot in texte_normalise:
                return intention
    return None


def detecter_modele(texte_normalise):
    for cle_modele, mots in MOTS_CLES_MODELE.items():
        for mot in mots:
            if mot in texte_normalise:
                return cle_modele
    return None


def detecter_liaison(texte_normalise, liaisons_connues):
    for liaison in liaisons_connues:
        motif = r"\b" + re.escape(str(liaison).lower()) + r"\b"
        if re.search(motif, texte_normalise):
            return liaison
    correspondance = re.search(r"liaison\s+([a-z0-9_-]+)", texte_normalise)
    if correspondance:
        return correspondance.group(1)
    return None


def detecter_periode(texte_normalise):
    date_precise = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", texte_normalise)
    if date_precise:
        jour, mois, annee = date_precise.groups()
        try:
            return {"type": "date", "date": datetime(int(annee), int(mois), int(jour)).date()}
        except ValueError:
            pass
    for cle_periode, mots in MOTS_CLES_PERIODE.items():
        for mot in mots:
            if mot in texte_normalise:
                return {"type": cle_periode}
    return None


def detecter_comparaison(texte_normalise):
    return any(mot in texte_normalise for mot in MOTS_CLES_COMPARAISON)


def periode_vers_bornes(periode):
    if periode is None:
        return None, None
    aujourd_hui = datetime.now().date()
    if periode["type"] == "date":
        return periode["date"], periode["date"]
    if periode["type"] == "aujourd_hui":
        return aujourd_hui, aujourd_hui
    if periode["type"] == "hier":
        veille = aujourd_hui - timedelta(days=1)
        return veille, veille
    if periode["type"] == "cette_semaine":
        return aujourd_hui - timedelta(days=7), aujourd_hui
    if periode["type"] == "deux_semaines":
        return aujourd_hui - timedelta(days=14), aujourd_hui
    if periode["type"] == "ce_mois":
        return aujourd_hui - timedelta(days=30), aujourd_hui
    return None, None


def extraire_slots(texte_normalise, liaisons_connues):
    return {
        "intention": detecter_intention(texte_normalise),
        "cle_modele": detecter_modele(texte_normalise),
        "liaison": detecter_liaison(texte_normalise, liaisons_connues),
        "periode": detecter_periode(texte_normalise),
        "comparaison": detecter_comparaison(texte_normalise),
    }