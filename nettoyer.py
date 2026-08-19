import pandas as pd
import os

CHEMINS = {
    "modele2_taux_vente_guichet": ["LiaisonId"],
    "modele3_controles": ["LiaisonId"],
    "modele6_taux_fraude": ["LiaisonId"],
    "modele4_part_confort": ["LiaisonId", "NiveauConfort"],
}

for cle_modele, colonnes in CHEMINS.items():
    chemin = f"data/predictions_nouvelles/{cle_modele}.parquet"
    if not os.path.isfile(chemin):
        print(cle_modele, "-> fichier absent, rien a faire")
        continue
    df = pd.read_parquet(chemin)
    for colonne in colonnes:
        if colonne in df.columns:
            df[colonne] = df[colonne].astype(str)
    df.to_parquet(chemin, index=False)
    print(cle_modele, "-> corrige,", len(df), "lignes")