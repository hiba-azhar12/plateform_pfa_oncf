import pandas as pd

CADENCES = {
    "semaine": {"libelle": "Semaine", "unite": "weeks", "n_points": 8},
    "mois": {"libelle": "Mois", "unite": "months", "n_points": 6},
    "annee": {"libelle": "Année", "unite": "years", "n_points": 6},
}


def date_decalee(date_reference, cadence, nombre_periodes):
    reference = pd.Timestamp(date_reference)
    unite = CADENCES[cadence]["unite"]
    if unite == "weeks":
        decalee = reference - pd.Timedelta(weeks=nombre_periodes)
    elif unite == "months":
        decalee = reference - pd.DateOffset(months=nombre_periodes)
    else:
        decalee = reference - pd.DateOffset(years=nombre_periodes)
    return decalee.date()


def serie_journaliere(historique, colonne_valeur, fonction_agg, liaison_choisie, liaison_est_all,
                       heure_choisie, heure_est_all, granularite_horaire,
                       colonne_categorie, categorie_choisie):
    if historique.empty or colonne_valeur not in historique.columns:
        return pd.Series(dtype="float64")

    sous = historique
    if colonne_categorie and categorie_choisie is not None and colonne_categorie in sous.columns:
        sous = sous[sous[colonne_categorie].astype(str) == categorie_choisie]
    if not liaison_est_all:
        sous = sous[sous["LiaisonId"] == liaison_choisie]
    if granularite_horaire and not heure_est_all and "Heure" in sous.columns:
        sous = sous[sous["Heure"].astype(int) == heure_choisie]

    if sous.empty:
        return pd.Series(dtype="float64")

    valeurs = pd.to_numeric(sous[colonne_valeur], errors="coerce")
    dates = sous["Date"].dt.normalize()
    return valeurs.groupby(dates).agg(fonction_agg)


def valeur_comparaison(serie_jour, date_reference, cadence):
    date_cible = date_decalee(date_reference, cadence, 1)
    if serie_jour.empty:
        return date_cible, None
    horodatage = pd.Timestamp(date_cible)
    if horodatage not in serie_jour.index:
        return date_cible, None
    return date_cible, float(serie_jour.loc[horodatage])


def serie_tendance(serie_jour, date_reference, cadence):
    if serie_jour.empty:
        return pd.DataFrame(columns=["Date", "Valeur"])

    n_points = CADENCES[cadence]["n_points"]
    date_min_disponible = serie_jour.index.min().date()

    lignes = []
    for k in range(n_points, 0, -1):
        date_cible = date_decalee(date_reference, cadence, k)
        if date_cible < date_min_disponible:
            continue
        horodatage = pd.Timestamp(date_cible)
        if horodatage in serie_jour.index:
            lignes.append({"Date": horodatage, "Valeur": float(serie_jour.loc[horodatage])})

    return pd.DataFrame(lignes)