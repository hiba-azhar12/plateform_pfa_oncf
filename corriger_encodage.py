import pandas as pd

chemin = "data/controles/modele6_taux_fraude/encodage_liaison.csv"
encodage = pd.read_csv(chemin)
encodage["LiaisonId"] = encodage["LiaisonId"].astype(str).str.replace(r"\.0$", "", regex=True)
encodage.to_parquet if False else encodage.to_csv(chemin, index=False)
print(encodage.head())