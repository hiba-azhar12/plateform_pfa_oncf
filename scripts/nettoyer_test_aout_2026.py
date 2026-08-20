import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from config.chemins import HISTORIQUE, LOG_EXECUTION, PREDICTIONS_NOUVELLES
from config.modeles import MODELES

DATES_A_SUPPRIMER = {"2026-08-15", "2026-08-16", "2026-08-17"}


def nettoyer_predictions_nouvelles():
    for cle_modele in MODELES:
        chemin = os.path.join(PREDICTIONS_NOUVELLES, f"{cle_modele}.parquet")
        if not os.path.isfile(chemin):
            continue
        table = pd.read_parquet(chemin)
        table["Date"] = pd.to_datetime(table["Date"])
        avant = len(table)
        table = table[~table["Date"].dt.strftime("%Y-%m-%d").isin(DATES_A_SUPPRIMER)]
        apres = len(table)
        if apres != avant:
            table.to_parquet(chemin, index=False)
            print(f"{cle_modele} (predictions_nouvelles) : {avant - apres} ligne(s) supprimee(s), {apres} restantes")
        else:
            print(f"{cle_modele} (predictions_nouvelles) : rien a supprimer")


def nettoyer_historique():
    for cle_modele in MODELES:
        chemin = os.path.join(HISTORIQUE, f"{cle_modele}.parquet")
        if not os.path.isfile(chemin):
            continue
        table = pd.read_parquet(chemin)
        table["Date"] = pd.to_datetime(table["Date"])
        avant = len(table)
        table = table[~table["Date"].dt.strftime("%Y-%m-%d").isin(DATES_A_SUPPRIMER)]
        apres = len(table)
        if apres != avant:
            table.to_parquet(chemin, index=False)
            print(f"{cle_modele} (historique) : {avant - apres} ligne(s) supprimee(s)")


def nettoyer_log_execution():
    if not os.path.isfile(LOG_EXECUTION):
        return
    with open(LOG_EXECUTION, "r") as fichier:
        journal = json.load(fichier)

    avant = len(journal)
    journal = [
        entree for entree in journal
        if entree.get("date_traitee") not in DATES_A_SUPPRIMER
        and entree.get("date_predite") not in DATES_A_SUPPRIMER
    ]
    apres = len(journal)

    with open(LOG_EXECUTION, "w") as fichier:
        json.dump(journal, fichier, indent=2, ensure_ascii=False)
    print(f"log_execution.json : {avant - apres} entree(s) supprimee(s)")


if __name__ == "__main__":
    nettoyer_predictions_nouvelles()
    nettoyer_historique()
    nettoyer_log_execution()
    print("Nettoyage termine. Redemarre l'app Streamlit (ou vide le cache) pour voir l'effet.")