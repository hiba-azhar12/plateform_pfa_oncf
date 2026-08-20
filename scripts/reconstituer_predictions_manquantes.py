import gc
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from config.chemins import HISTORIQUE, PREDICTIONS_NOUVELLES
from config.modeles import MODELES
from utils.inference import predire_nouvelle_date

DATE_DEBUT = "2025-11-01"
DATE_FIN = "2025-11-05"


def _cles_grain(cle_modele):
    info = MODELES[cle_modele]
    cles = ["LiaisonId"]
    if info["granularite"] == "horaire":
        cles.append("Heure")
    if info["colonne_categorie"]:
        cles.append(info["colonne_categorie"])
    return cles


def _chemin_historique(cle_modele):
    return os.path.join(HISTORIQUE, f"{cle_modele}.parquet")


def _chemin_predictions_nouvelles(cle_modele):
    return os.path.join(PREDICTIONS_NOUVELLES, f"{cle_modele}.parquet")


def _charger_predictions_nouvelles(cle_modele):
    chemin = _chemin_predictions_nouvelles(cle_modele)
    if os.path.isfile(chemin):
        return pd.read_parquet(chemin)
    return pd.DataFrame()


def _normaliser_cles(table, cles):
    table = table.copy()
    if "LiaisonId" in table.columns:
        table["LiaisonId"] = table["LiaisonId"].astype(str)
    if "Heure" in cles and "Heure" in table.columns:
        table["Heure"] = table["Heure"].astype(int)
    for cle in cles:
        if cle not in ("LiaisonId", "Heure") and cle in table.columns:
            table[cle] = table[cle].astype(str)
    return table


def _reel_pour_date(historique, cle_modele, date_cible):
    info = MODELES[cle_modele]
    cles = _cles_grain(cle_modele)
    sous = historique[historique["Date"] == pd.Timestamp(date_cible)]
    colonnes = ["Date"] + cles + [info["cible"]]
    if sous.empty:
        return pd.DataFrame(columns=colonnes)
    return _normaliser_cles(sous[colonnes].copy(), cles)


def _reconstituer_date_absente(cle_modele, date_cible, historique):
    info = MODELES[cle_modele]
    cles = _cles_grain(cle_modele)

    historique_avant = historique[historique["Date"] < pd.Timestamp(date_cible)]
    if historique_avant.empty:
        print(f"{cle_modele} {date_cible} : historique vide avant cette date, ignore")
        return None

    resultat, colonnes_manquantes, liaisons_inconnues = predire_nouvelle_date(
        cle_modele, pd.Timestamp(date_cible), historique_avant
    )
    if colonnes_manquantes:
        print(f"{cle_modele} {date_cible} : colonnes manquantes {colonnes_manquantes}")
    if liaisons_inconnues:
        print(f"{cle_modele} {date_cible} : {len(liaisons_inconnues)} liaison(s) inconnue(s)")

    resultat = _normaliser_cles(resultat, cles)
    resultat = resultat.drop(columns=[info["cible"]], errors="ignore")
    reel = _reel_pour_date(historique, cle_modele, date_cible)

    fusion = resultat.merge(reel, on=["Date"] + cles, how="left")
    fusion["Reel"] = fusion[info["cible"]]
    fusion["ErreurAbsolue"] = (fusion["Reel"] - fusion["Prediction"]).abs()
    fusion["DateCalculPrediction"] = pd.Timestamp(date_cible) - pd.Timedelta(days=1)

    colonnes_gardees = ["Date"] + cles + ["Prediction", "DateCalculPrediction", "Reel", "ErreurAbsolue"]
    return fusion[colonnes_gardees]


def _completer_date_presente(cle_modele, date_cible, historique, existantes):
    info = MODELES[cle_modele]
    cles = _cles_grain(cle_modele)

    masque = (existantes["Date"] == pd.Timestamp(date_cible)) & (existantes["Reel"].isna())
    if not masque.any():
        return existantes, 0

    reel = _reel_pour_date(historique, cle_modele, date_cible)

    sous = _normaliser_cles(existantes.loc[masque, ["Date"] + cles].copy(), cles)
    fusion = sous.merge(reel, on=["Date"] + cles, how="left")

    existantes.loc[masque, "Reel"] = fusion[info["cible"]].values
    existantes.loc[masque, "ErreurAbsolue"] = (
        existantes.loc[masque, "Reel"].astype(float) - existantes.loc[masque, "Prediction"].astype(float)
    ).abs()

    return existantes, int(fusion[info["cible"]].notna().sum())


def reconstituer_modele(cle_modele, date_debut, date_fin):
    print(f"=== {cle_modele} ===")
    chemin_historique = _chemin_historique(cle_modele)
    if not os.path.isfile(chemin_historique):
        print(f"{cle_modele} : pas d'historique, ignore")
        return

    cles = _cles_grain(cle_modele)

    historique = pd.read_parquet(chemin_historique)
    historique["Date"] = pd.to_datetime(historique["Date"])
    historique = _normaliser_cles(historique, cles)

    existantes = _charger_predictions_nouvelles(cle_modele)
    if not existantes.empty:
        existantes["Date"] = pd.to_datetime(existantes["Date"])
        existantes = _normaliser_cles(existantes, cles)

    dates_existantes = set(existantes["Date"].dt.date.unique()) if not existantes.empty else set()
    lignes_reconstituees = []

    for date_cible in pd.date_range(date_debut, date_fin):
        date_cible = date_cible.date()
        if date_cible in dates_existantes:
            existantes, nb_completees = _completer_date_presente(cle_modele, date_cible, historique, existantes)
            if nb_completees:
                print(f"{cle_modele} {date_cible} : {nb_completees} valeur(s) reelle(s) completee(s)")
        else:
            nouvelles_lignes = _reconstituer_date_absente(cle_modele, date_cible, historique)
            if nouvelles_lignes is not None:
                lignes_reconstituees.append(nouvelles_lignes)
                print(f"{cle_modele} {date_cible} : {len(nouvelles_lignes)} ligne(s) reconstituee(s)")
        gc.collect()

    if lignes_reconstituees:
        if existantes.empty:
            existantes = pd.concat(lignes_reconstituees, ignore_index=True, sort=False)
        else:
            existantes = pd.concat([existantes] + lignes_reconstituees, ignore_index=True, sort=False)

    cles_completes = ["Date"] + cles
    existantes = existantes.drop_duplicates(subset=cles_completes, keep="last").sort_values(cles_completes).reset_index(drop=True)

    os.makedirs(PREDICTIONS_NOUVELLES, exist_ok=True)
    existantes.to_parquet(_chemin_predictions_nouvelles(cle_modele), index=False)
    print(f"{cle_modele} : {len(existantes)} lignes au total apres reconstitution")


if __name__ == "__main__":
    modeles_cibles = sys.argv[1:] if len(sys.argv) > 1 else list(MODELES.keys())
    for cle_modele in modeles_cibles:
        if cle_modele not in MODELES:
            print(f"{cle_modele} : modele inconnu, ignore")
            continue
        reconstituer_modele(cle_modele, DATE_DEBUT, DATE_FIN)