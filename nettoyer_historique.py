"""
Nettoie les fichiers data/historique/*.parquet :
- convertit les vrais NaN de LiaisonId en la chaine "nan" (coherent avec le
  comportement de gestion des liaisons inconnues du pipeline)
- force NiveauConfort en str partout ou la colonne existe, pour eviter les
  colonnes a types Python melanges (int + str) illisibles par PyArrow

A lancer une seule fois, depuis la racine du projet :
    python3 nettoyer_historique.py
"""
import glob
import os

import pandas as pd

DOSSIER = "data/historique"


def nettoyer_fichier(chemin):
    df = pd.read_parquet(chemin)
    modifie = False

    if "LiaisonId" in df.columns:
        avant = df["LiaisonId"].isna().sum()
        if avant:
            df["LiaisonId"] = df["LiaisonId"].map(str)
            modifie = True
            print(f"  LiaisonId : {avant} NaN convertis en chaine 'nan'")

    if "NiveauConfort" in df.columns:
        types_avant = df["NiveauConfort"].map(lambda v: type(v).__name__).unique().tolist()
        if types_avant != ["str"]:
            df["NiveauConfort"] = df["NiveauConfort"].map(str)
            modifie = True
            print(f"  NiveauConfort : types {types_avant} -> uniformises en str")

    if modifie:
        df.to_parquet(chemin, index=False)
        print(f"  -> {chemin} sauvegarde")
    else:
        print("  -> rien a faire")


def main():
    for chemin in sorted(glob.glob(os.path.join(DOSSIER, "*.parquet"))):
        print(os.path.basename(chemin))
        nettoyer_fichier(chemin)


if __name__ == "__main__":
    main()