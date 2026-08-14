import difflib

REMPLACEMENTS_ACCENTS = {
    "é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a",
    "ô": "o", "î": "i", "ï": "i", "ç": "c", "ù": "u", "û": "u",
}


def normaliser_texte(texte):
    texte = texte.lower().strip()
    for source, cible in REMPLACEMENTS_ACCENTS.items():
        texte = texte.replace(source, cible)
    return texte


def construire_vocabulaire(mots_cles_modele, mots_cles_intention):
    vocabulaire = set()
    for expressions in mots_cles_modele.values():
        for expression in expressions:
            vocabulaire.update(expression.split())
    for expressions in mots_cles_intention.values():
        for expression in expressions:
            vocabulaire.update(expression.split())
    return vocabulaire


def corriger_mots(texte_normalise, vocabulaire, seuil=0.82):
    mots_corriges = []
    for mot in texte_normalise.split():
        if len(mot) < 4 or mot in vocabulaire:
            mots_corriges.append(mot)
            continue
        correspondance = difflib.get_close_matches(mot, vocabulaire, n=1, cutoff=seuil)
        mots_corriges.append(correspondance[0] if correspondance else mot)
    return " ".join(mots_corriges)