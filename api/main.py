import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile

from config.chemins import (
    DEPOT_QUOTIDIEN_CIRCULATION,
    DEPOT_QUOTIDIEN_CONTROLES,
    DEPOT_QUOTIDIEN_VENTES,
    LOG_EXECUTION,
)
from config.modeles import MODELES, chemin_fichier
from scripts.traiter_depot_quotidien import executer as executer_traitement_quotidien

app = FastAPI(title="API Plateforme ONCF")

DOSSIERS_DEPOT = {
    "ventes": DEPOT_QUOTIDIEN_VENTES,
    "controles": DEPOT_QUOTIDIEN_CONTROLES,
    "circulation": DEPOT_QUOTIDIEN_CIRCULATION,
}


@app.get("/sante")
async def verifier_sante():
    return {"statut": "ok", "heure": datetime.now().isoformat()}


@app.post("/deposer-donnees/{type_donnee}")
async def deposer_donnees(type_donnee: str, fichier: UploadFile):
    if type_donnee not in DOSSIERS_DEPOT:
        raise HTTPException(status_code=400, detail="type_donnee invalide")
    dossier_cible = DOSSIERS_DEPOT[type_donnee]
    os.makedirs(dossier_cible, exist_ok=True)
    chemin_destination = os.path.join(dossier_cible, fichier.filename)
    with open(chemin_destination, "wb") as sortie:
        shutil.copyfileobj(fichier.file, sortie)
    return {"statut": "recu", "fichier": fichier.filename}


@app.post("/traiter-quotidien")
async def traiter_quotidien():
    executer_traitement_quotidien()
    return {"statut": "traitement_lance"}


@app.get("/predictions/{cle_modele}")
async def obtenir_predictions(cle_modele: str):
    if cle_modele not in MODELES:
        raise HTTPException(status_code=404, detail="modele inconnu")
    from config.chemins import PREDICTIONS_NOUVELLES
    chemin = os.path.join(PREDICTIONS_NOUVELLES, f"{cle_modele}.parquet")
    if not os.path.isfile(chemin):
        return []
    table = pd.read_parquet(chemin)
    return json.loads(table.to_json(orient="records", date_format="iso"))


@app.get("/metriques/{cle_modele}")
async def obtenir_metriques(cle_modele: str):
    if cle_modele not in MODELES:
        raise HTTPException(status_code=404, detail="modele inconnu")
    chemin = chemin_fichier(cle_modele, "metriques")
    if not os.path.isfile(chemin):
        return {}
    with open(chemin, "r") as fichier:
        return json.load(fichier)


@app.post("/reentrainer/{cle_modele}")
async def declencher_reentrainement(cle_modele: str):
    if cle_modele not in MODELES:
        raise HTTPException(status_code=404, detail="modele inconnu")

    resultat = subprocess.run(
        [sys.executable, "scripts/reentrainer_modeles.py", "--modele", cle_modele],
        capture_output=True, text=True, timeout=1800,
    )

    if resultat.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"le processus de reentrainement a echoue (code {resultat.returncode}) : {resultat.stderr[-2000:]}",
        )

    lignes = resultat.stdout.splitlines()
    indice_ouverture = None
    for indice in range(len(lignes) - 1, -1, -1):
        if lignes[indice].strip() == "{":
            indice_ouverture = indice
            break

    if indice_ouverture is None:
        raise HTTPException(status_code=500, detail=f"sortie inattendue : {resultat.stdout[-2000:]}")

    bloc_json = "\n".join(lignes[indice_ouverture:])

    try:
        return json.loads(bloc_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"sortie inattendue : {resultat.stdout[-2000:]}")


@app.get("/etat-pipeline")
async def etat_pipeline():
    if not os.path.isfile(LOG_EXECUTION):
        return []
    with open(LOG_EXECUTION, "r") as fichier:
        return json.load(fichier)