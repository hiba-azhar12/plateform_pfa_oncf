def phrase_anomalie(date, liaison_id, valeur_reelle, prediction, libelle_cible):
    ecart = valeur_reelle - prediction
    if prediction == 0:
        pourcentage = 0
    else:
        pourcentage = round(abs(ecart) / prediction * 100, 1)

    direction = "en dessous de" if ecart < 0 else "au dessus de"
    return (
        f"Le {date}, la liaison {liaison_id} enregistre un {libelle_cible.lower()} "
        f"de {valeur_reelle:.0f}, soit {pourcentage}% {direction} la prévision ({prediction:.0f})."
    )


def severite_anomalie(erreur_absolue, seuil):
    if seuil <= 0:
        return "faible"
    if erreur_absolue > 2 * seuil:
        return "critique"
    if erreur_absolue > seuil:
        return "moderee"
    return "faible"
