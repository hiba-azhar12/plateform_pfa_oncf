CLE_SESSION = "contexte_chatbot"


def obtenir_contexte(session_state):
    if CLE_SESSION not in session_state:
        session_state[CLE_SESSION] = {"dernier_modele": None, "derniere_liaison": None}
    return session_state[CLE_SESSION]


def mettre_a_jour_contexte(session_state, cle_modele=None, liaison=None):
    contexte = obtenir_contexte(session_state)
    if cle_modele is not None:
        contexte["dernier_modele"] = cle_modele
    if liaison is not None:
        contexte["derniere_liaison"] = liaison


def reinitialiser_contexte(session_state):
    session_state[CLE_SESSION] = {"dernier_modele": None, "derniere_liaison": None}