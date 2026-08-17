import numpy as np
import pandas as pd
import holidays

from config.calendrier_maroc import RAMADAN_PERIODES, VACANCES_SCOLAIRES_PERIODES

_FERIES_MAROC = holidays.Morocco()

MESSAGES_FRAUDE_CRITIQUE = [
    "Le trajet de ce billet est invalide sur la gare que vous avez choisie",
    "Ce billet a été déjà contrôlé dans ce train",
    "Vous avez déja controlé cette carte dans ce train.",
    "La date de ce billet est invalide",
    "Confort du Billet est inférieur au confort courant",
    "Attention ! Montée avant gare de départ.",
    "Attention ! Gare de destination dépassée.",
    "Cette carte dans un confort différent",
    "Carte invalide : Cette date de validité a déjà expiré !",
    "Ce billet a déjà été annulé.",
]


def _dans_une_periode(date, periodes):
    for debut, fin in periodes:
        if pd.Timestamp(debut) <= date <= pd.Timestamp(fin):
            return True
    return False


def calculer_features_calendaires(dates, avec_heure=False, heures=None):
    dates = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    table = pd.DataFrame({"Date": dates})

    table["JourSemaine"] = table["Date"].dt.dayofweek
    table["Mois"] = table["Date"].dt.month
    table["Annee"] = table["Date"].dt.year
    table["EstWeekend"] = table["JourSemaine"] >= 5
    table["EstFerie"] = table["Date"].apply(lambda d: d.date() in _FERIES_MAROC)
    table["EstRamadan"] = table["Date"].apply(lambda d: _dans_une_periode(d, RAMADAN_PERIODES))
    table["EstVacances"] = table["Date"].apply(lambda d: _dans_une_periode(d, VACANCES_SCOLAIRES_PERIODES))

    table["jour_semaine_sin"] = np.sin(2 * np.pi * table["JourSemaine"] / 7)
    table["jour_semaine_cos"] = np.cos(2 * np.pi * table["JourSemaine"] / 7)
    table["mois_sin"] = np.sin(2 * np.pi * table["Mois"] / 12)
    table["mois_cos"] = np.cos(2 * np.pi * table["Mois"] / 12)

    if avec_heure and heures is not None:
        heures = pd.Series(heures).astype(int).reset_index(drop=True)
        table["Heure"] = heures
        table["heure_sin"] = np.sin(2 * np.pi * table["Heure"] / 24)
        table["heure_cos"] = np.cos(2 * np.pi * table["Heure"] / 24)

    return table


def marquer_fraude(controlepda):
    controlepda = controlepda.copy()
    messages = controlepda["MessageControle"].fillna("")
    controlepda["Fraude"] = messages.apply(
        lambda message: int(any(critique in message for critique in MESSAGES_FRAUDE_CRITIQUE))
    )
    return controlepda


def pivot_ventes(ventepda):
    ventepda = ventepda.copy()
    ventepda["Date"] = pd.to_datetime(ventepda["Date"])
    ventepda["LiaisonId"] = ventepda["LiaisonId"].map(str)
    ventepda["Heure"] = ventepda["Heure"].astype(str)
    ventepda["NiveauConfort"] = ventepda["NiveauConfort"].map(str)
    agrege = (
        ventepda.groupby(["Date", "Heure", "LiaisonId", "NiveauConfort"], observed=True)
        .agg(NbBillets=("NumBillet", "count"))
        .reset_index()
    )
    return agrege


def pivot_controles(controlepda):
    controlepda = marquer_fraude(controlepda)
    controlepda["Date"] = pd.to_datetime(controlepda["Date"])
    controlepda["LiaisonId"] = controlepda["LiaisonId"].map(str)
    controlepda["Heure"] = controlepda["Heure"].astype(str)
    agrege = (
        controlepda.groupby(["Date", "Heure", "LiaisonId", "TypeTitre"], observed=True)
        .agg(NbControles=("ControleId", "count"), NbFraudes=("Fraude", "sum"))
        .reset_index()
    )
    return agrege


def pivot_circulation(circulation):
    circulation = circulation.copy()
    circulation["Date"] = pd.to_datetime(circulation["DateCirculation"])
    circulation["LiaisonId"] = circulation["LiaisonId"].map(str)
    circulation["Heure"] = circulation["Heure"].astype(str)
    agrege = (
        circulation.groupby(["Date", "Heure", "LiaisonId"], observed=True)
        .agg(NbCirculations=("NombreBilletCircule", "sum"))
        .reset_index()
    )
    return agrege


def construire_modele1(pivot_vente):
    table = pivot_vente.groupby(["Date", "Heure", "LiaisonId"], observed=True)["NbBillets"].sum().reset_index()
    table["Heure"] = table["Heure"].astype("int64")
    return table


def construire_modele3(pivot_controle):
    table = pivot_controle.groupby(["Date", "Heure", "LiaisonId"], observed=True)["NbControles"].sum().reset_index()
    table["Heure"] = table["Heure"].astype("int64")
    return table


def construire_modele2(pivot_vente, pivot_circ):
    vente_jour = pivot_vente.groupby(["Date", "LiaisonId"], observed=True)["NbBillets"].sum().reset_index()
    circulation_jour = pivot_circ.groupby(["Date", "LiaisonId"], observed=True)["NbCirculations"].sum().reset_index()
    fusion = vente_jour.merge(circulation_jour, on=["Date", "LiaisonId"], how="left")
    fusion = fusion[fusion["NbCirculations"].notna()].reset_index(drop=True)
    fusion["TauxVenteGuichet"] = fusion["NbBillets"] / fusion["NbCirculations"]
    return fusion


def construire_modele4(pivot_vente):
    return (
        pivot_vente.groupby(["Date", "LiaisonId", "NiveauConfort"], observed=True)["NbBillets"]
        .sum().reset_index()
    )


def construire_modele5(pivot_controle, pivot_circ):
    controle_jour = pivot_controle.groupby(["Date", "LiaisonId"], observed=True)["NbControles"].sum().reset_index()
    circulation_jour = pivot_circ.groupby(["Date", "LiaisonId"], observed=True)["NbCirculations"].sum().reset_index()
    fusion = controle_jour.merge(circulation_jour, on=["Date", "LiaisonId"], how="left")
    fusion = fusion[fusion["NbCirculations"].notna()].reset_index(drop=True)
    fusion["TauxControle"] = (fusion["NbControles"] / fusion["NbCirculations"]).clip(upper=1.0)
    return fusion


def construire_modele6(pivot_controle):
    agrege = (
        pivot_controle.groupby(["Date", "LiaisonId"], observed=True)
        .agg(NbControles=("NbControles", "sum"), NbFraudes=("NbFraudes", "sum"))
        .reset_index()
    )
    agrege["TauxFraude"] = agrege["NbFraudes"] / agrege["NbControles"].replace(0, np.nan)
    return agrege


def construire_modele7(pivot_controle):
    return (
        pivot_controle.groupby(["Date", "LiaisonId", "TypeTitre"], observed=True)["NbControles"]
        .sum().reset_index()
    )


def calculer_liaison_frequence(historique, colonnes_groupe):
    return historique.groupby(colonnes_groupe, observed=True)[colonnes_groupe[0]].transform("count")


def ajouter_lags_rolling_calendaires(historique, colonne_cible, colonnes_groupe, lags, fenetres, nom_suffixe=None):
    suffixe = nom_suffixe or colonne_cible
    colonnes_cles = colonnes_groupe + ["Date"]

    dates_completes = pd.date_range(historique["Date"].min(), historique["Date"].max(), freq="D")
    groupes_uniques = historique[colonnes_groupe].drop_duplicates()
    squelette = groupes_uniques.merge(pd.DataFrame({"Date": dates_completes}), how="cross")

    dense = squelette.merge(historique[colonnes_cles + [colonne_cible]], on=colonnes_cles, how="left")
    dense[colonne_cible] = dense[colonne_cible].fillna(0).astype("float32")
    dense = dense.sort_values(colonnes_cles).reset_index(drop=True)

    groupe = dense.groupby(colonnes_groupe, observed=True)[colonne_cible]
    colonne_decalee = f"{suffixe}_j_moins_1"
    dense[colonne_decalee] = groupe.shift(1)
    for lag in lags:
        dense[f"lag_{lag}_{suffixe}"] = groupe.shift(lag)

    for fenetre in fenetres:
        roulant = dense.groupby(colonnes_groupe, observed=True)[colonne_decalee]
        dense[f"rolling_mean_{fenetre}_{suffixe}"] = roulant.rolling(fenetre).mean().reset_index(level=list(range(len(colonnes_groupe))), drop=True)
        dense[f"rolling_std_{fenetre}_{suffixe}"] = roulant.rolling(fenetre).std().reset_index(level=list(range(len(colonnes_groupe))), drop=True)

    colonnes_resultat = [f"lag_{lag}_{suffixe}" for lag in lags] + [colonne_decalee]
    for fenetre in fenetres:
        colonnes_resultat += [f"rolling_mean_{fenetre}_{suffixe}", f"rolling_std_{fenetre}_{suffixe}"]

    dense_resultat = dense[colonnes_cles + colonnes_resultat].copy()
    del dense
    historique = historique.merge(dense_resultat, on=colonnes_cles, how="left")
    del dense_resultat
    return historique


def calculer_encodage_expanding(historique, colonne_cible, colonnes_groupe):
    groupe = historique.groupby(colonnes_groupe, observed=True)[colonne_cible]
    return groupe.transform(lambda serie: serie.shift(1).expanding().mean())


def calculer_interaction_jour(historique, colonne_cible, colonnes_groupe):
    groupe = historique.groupby(colonnes_groupe, observed=True)[colonne_cible]
    return groupe.transform(lambda serie: serie.shift(1).expanding().mean())