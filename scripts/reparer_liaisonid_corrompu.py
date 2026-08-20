import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from config.chemins import HISTORIQUE, PREDICTIONS_NOUVELLES
from config.modeles import MODELES
from utils.inference import charger_encodage


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


def reparer_modele(cle_modele):
    info = MODELES[cle_modele]
    chemin_predictions = _chemin_predictions_nouvelles(cle_modele)
    chemin_historique = _chemin_historique(cle_modele)

    if not os.path.isfile(chemin_predictions) or not os.path.isfile(chemin_historique):
        print(f"{cle_modele} : fichiers absents, ignore")
        return

    predictions = pd.read_parquet(chemin_predictions)
    predictions["Date"] = pd.to_datetime(predictions["Date"])
    predictions["LiaisonId"] = predictions["LiaisonId"].astype(str)

    historique = pd.read_parquet(chemin_historique)
    historique["Date"] = pd.to_datetime(historique["Date"])
    historique["LiaisonId"] = historique["LiaisonId"].astype(str)

    liaisons_reelles = set(historique["LiaisonId"].unique())
    masque_fantome = ~predictions["LiaisonId"].isin(liaisons_reelles)

    if masque_fantome.any():
        encodage = charger_encodage(cle_modele)
        if encodage.empty:
            print(f"{cle_modele} : {masque_fantome.sum()} ligne(s) fantome(s) mais pas de table d'encodage, ignore")
        else:
            mapping = dict(zip(encodage["Code"].astype(str), encodage["LiaisonId"].astype(str)))
            reparables = masque_fantome & predictions["LiaisonId"].isin(mapping.keys())
            predictions.loc[reparables, "LiaisonId"] = predictions.loc[reparables, "LiaisonId"].map(mapping)
            print(f"{cle_modele} : {reparables.sum()} ligne(s) fantome(s) reparee(s)")

            non_reparables = masque_fantome & ~predictions["LiaisonId"].isin(mapping.values())
            if non_reparables.any():
                predictions = predictions[~non_reparables].copy()
                print(f"{cle_modele} : {non_reparables.sum()} ligne(s) fantome(s) non reparable(s) supprimee(s)")
    else:
        print(f"{cle_modele} : aucune ligne fantome")

    cles = ["LiaisonId"]
    if info["granularite"] == "horaire":
        cles.append("Heure")
        predictions["Heure"] = predictions["Heure"].astype(int)
    if info["colonne_categorie"]:
        cles.append(info["colonne_categorie"])
        predictions[info["colonne_categorie"]] = predictions[info["colonne_categorie"]].astype(str)

    predictions["ReelConnu"] = predictions["Reel"].notna().astype(int)
    predictions = predictions.sort_values(["Date"] + cles + ["ReelConnu"])
    predictions = predictions.drop_duplicates(subset=["Date"] + cles, keep="last")
    predictions = predictions.drop(columns=["ReelConnu"])

    colonnes_jointure = ["Date"] + cles + [info["cible"]]
    reel_historique = historique[colonnes_jointure].copy()
    if "Heure" in cles:
        reel_historique["Heure"] = reel_historique["Heure"].astype(int)
    if info["colonne_categorie"]:
        reel_historique[info["colonne_categorie"]] = reel_historique[info["colonne_categorie"]].astype(str)

    masque_a_completer = predictions["Reel"].isna()
    if masque_a_completer.any():
        sous = predictions.loc[masque_a_completer, ["Date"] + cles]
        fusion = sous.merge(reel_historique, on=["Date"] + cles, how="left")
        nouvelles_valeurs = fusion[info["cible"]].values
        predictions.loc[masque_a_completer, "Reel"] = nouvelles_valeurs
        nb_completees = pd.notna(nouvelles_valeurs).sum()
        if nb_completees:
            print(f"{cle_modele} : {nb_completees} valeur(s) reelle(s) recuperee(s) apres reparation")

    predictions["ErreurAbsolue"] = (
        predictions["Reel"].astype(float) - predictions["Prediction"].astype(float)
    ).abs()

    predictions = predictions.sort_values(["Date"] + cles).reset_index(drop=True)
    predictions.to_parquet(chemin_predictions, index=False)
    print(f"{cle_modele} : {len(predictions)} lignes au total apres reparation")


if __name__ == "__main__":
    modeles_cibles = sys.argv[1:] if len(sys.argv) > 1 else list(MODELES.keys())
    for cle_modele in modeles_cibles:
        if cle_modele not in MODELES:
            print(f"{cle_modele} : modele inconnu, ignore")
            continue
        reparer_modele(cle_modele)