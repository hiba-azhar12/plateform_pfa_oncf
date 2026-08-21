import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from config.chemins import HISTORIQUE
from config.modeles import MODELES


def _chemin_historique(cle_modele):
    return os.path.join(HISTORIQUE, f"{cle_modele}.parquet")


def reparer_modele(cle_modele):
    info = MODELES[cle_modele]
    if info["famille"] != "composition":
        print(f"{cle_modele} : pas un modele de composition, ignore")
        return

    chemin = _chemin_historique(cle_modele)
    if not os.path.isfile(chemin):
        print(f"{cle_modele} : pas d'historique, ignore")
        return

    historique = pd.read_parquet(chemin)
    historique["Date"] = pd.to_datetime(historique["Date"])

    colonne_brute = "NbBillets" if "NbBillets" in historique.columns else "NbControles"
    manquants = historique[info["cible"]].isna()

    if not manquants.any():
        print(f"{cle_modele} : aucune valeur manquante")
        return

    total_jour = historique.groupby(["Date", "LiaisonId"])[colonne_brute].transform("sum")
    ratio = historique[colonne_brute] / total_jour.replace(0, float("nan"))
    ratio = ratio.astype("float64").astype(historique[info["cible"]].dtype)

    historique.loc[manquants, info["cible"]] = ratio.loc[manquants]

    historique.to_parquet(chemin, index=False)
    print(f"{cle_modele} : {manquants.sum()} valeur(s) de {info['cible']} recalculee(s)")


if __name__ == "__main__":
    modeles_cibles = sys.argv[1:] if len(sys.argv) > 1 else list(MODELES.keys())
    for cle_modele in modeles_cibles:
        if cle_modele not in MODELES:
            print(f"{cle_modele} : modele inconnu, ignore")
            continue
        reparer_modele(cle_modele)