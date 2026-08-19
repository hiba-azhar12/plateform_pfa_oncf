import glob
import os

import pandas as pd

DOSSIER_HISTORIQUE = "data/historique"

for chemin in glob.glob(os.path.join(DOSSIER_HISTORIQUE, "*.parquet")):
    table = pd.read_parquet(chemin)
    if "LiaisonId" not in table.columns:
        continue
    if str(table["LiaisonId"].dtype) == "category":
        continue
    avant = round(table.memory_usage(deep=True).sum() / 1e6, 1)
    table["LiaisonId"] = table["LiaisonId"].astype(str).astype("category")
    apres = round(table.memory_usage(deep=True).sum() / 1e6, 1)
    table.to_parquet(chemin, index=False)
    print(f"{os.path.basename(chemin)} : {avant} Mo -> {apres} Mo")