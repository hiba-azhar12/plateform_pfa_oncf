import pandas as pd

from config.modeles import MODELES, chemin_fichier

for cle_modele in MODELES:
    info = MODELES[cle_modele]
    if info["format_modele"] == "catboost":
        continue

    encodage = pd.read_csv(chemin_fichier(cle_modele, "encodage_liaison"))
    historique = pd.read_parquet(f"data/historique/{cle_modele}.parquet")

    connues = set(encodage["LiaisonId"].astype(str))
    presentes = set(historique["LiaisonId"].astype(str))
    inconnues = presentes - connues

    if inconnues:
        print(cle_modele, "->", sorted(inconnues))
