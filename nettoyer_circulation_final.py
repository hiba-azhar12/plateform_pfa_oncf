"""
Nettoie circulation_final_2023_2025.parquet :
- retire les lignes ou LiaisonId est un vrai NaN (valeur invalide dans le
  fichier Excel source, jamais un identifiant valide), pour empecher la
  fausse "liaison nan" de se propager dans les futures generations de test.

A lancer une seule fois, avec le bon chemin vers ton fichier :
    python3 nettoyer_circulation_final.py
"""
import pandas as pd

CHEMIN = "circulation_final_2023_2025.parquet"


def main():
    circulation = pd.read_parquet(CHEMIN)
    avant = len(circulation)
    manquants = circulation["LiaisonId"].isna().sum()

    print(f"lignes avant : {avant}")
    print(f"LiaisonId manquants trouves : {manquants}")

    if manquants == 0:
        print("rien a faire")
        return

    circulation_propre = circulation.dropna(subset=["LiaisonId"]).reset_index(drop=True)
    circulation_propre.to_parquet(CHEMIN, index=False)
    print(f"lignes apres : {len(circulation_propre)}")
    print(f"-> {CHEMIN} sauvegarde")


if __name__ == "__main__":
    main()