import json
import math
import os
import shutil
import subprocess
import sys
import uuid
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile

from config.chemins import (
    DEPOT_QUOTIDIEN_CIRCULATION,
    DEPOT_QUOTIDIEN_CONTROLES,
    DEPOT_QUOTIDIEN_VENTES,
    JOURNAUX_DIRECTS,
    LOG_EXECUTION,
)
from config.modeles import (
    MODELES,
    MODELES_HORIZON_DEDIE,
    HORIZONS_DEDIES,
    chemin_fichier,
    chemin_fichier_horizon,
)
from utils.temps import horodatage_maroc

app = FastAPI(title="API Plateforme ONCF")

DOSSIERS_DEPOT = {
    "ventes": DEPOT_QUOTIDIEN_VENTES,
    "controles": DEPOT_QUOTIDIEN_CONTROLES,
    "circulation": DEPOT_QUOTIDIEN_CIRCULATION,
}

PROCESSUS_EN_COURS = {}


def _job_deja_en_cours(cle):
    processus = PROCESSUS_EN_COURS.get(cle)
    return processus is not None and processus.poll() is None


def _chemin_journal_direct(nom):
    os.makedirs(JOURNAUX_DIRECTS, exist_ok=True)
    return os.path.join(JOURNAUX_DIRECTS, f"{nom}.log")


def _nettoyer_nan(objet):
    if isinstance(objet, float) and math.isnan(objet):
        return None
    if isinstance(objet, dict):
        return {cle: _nettoyer_nan(valeur) for cle, valeur in objet.items()}
    if isinstance(objet, list):
        return [_nettoyer_nan(valeur) for valeur in objet]
    return objet


@app.get("/etat-pipeline")
async def etat_pipeline():
    if not os.path.isfile(LOG_EXECUTION):
        return []
    with open(LOG_EXECUTION, "r") as fichier:
        journal = json.load(fichier)
    return _nettoyer_nan(journal)

@app.get("/sante")
async def verifier_sante():
    return {"statut": "ok", "heure": horodatage_maroc()}


@app.get("/journal-direct/{nom}")
async def journal_direct(nom: str):
    chemin = _chemin_journal_direct(nom)
    if not os.path.isfile(chemin):
        return {"contenu": ""}
    with open(chemin, "r", errors="replace") as fichier:
        return {"contenu": fichier.read()}


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
    if _job_deja_en_cours("traitement"):
        raise HTTPException(status_code=409, detail="traitement_deja_en_cours")

    id_declenchement = str(uuid.uuid4())
    chemin_log = _chemin_journal_direct("traitement")
    with open(chemin_log, "w") as fichier_log:
        processus = subprocess.Popen(
            [sys.executable, "scripts/traiter_depot_quotidien.py", "--id-declenchement", id_declenchement],
            stdout=fichier_log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    PROCESSUS_EN_COURS["traitement"] = processus
    return {"statut": "traitement_lance", "horodatage": horodatage_maroc(), "id_declenchement": id_declenchement}


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
async def obtenir_metriques(cle_modele: str, horizon: Optional[int] = None):
    if cle_modele not in MODELES:
        raise HTTPException(status_code=404, detail="modele inconnu")
    if horizon is not None:
        if cle_modele not in MODELES_HORIZON_DEDIE or horizon not in HORIZONS_DEDIES:
            raise HTTPException(status_code=400, detail="horizon indisponible pour ce modele")
        chemin = chemin_fichier_horizon(cle_modele, horizon, "metriques")
    else:
        chemin = chemin_fichier(cle_modele, "metriques")
    if not os.path.isfile(chemin):
        return {}
    with open(chemin, "r") as fichier:
        return json.load(fichier)


@app.post("/reentrainer/{cle_modele}")
async def declencher_reentrainement(cle_modele: str, horizon: Optional[int] = None):
    if cle_modele not in MODELES:
        raise HTTPException(status_code=404, detail="modele inconnu")

    if horizon is not None and (cle_modele not in MODELES_HORIZON_DEDIE or horizon not in HORIZONS_DEDIES):
        raise HTTPException(status_code=400, detail="horizon indisponible pour ce modele")

    nom_journal_direct = f"reentrainement_{cle_modele}" if horizon is None else f"reentrainement_{cle_modele}_h{horizon}"

    if _job_deja_en_cours(nom_journal_direct):
        raise HTTPException(status_code=409, detail="reentrainement_deja_en_cours")

    id_declenchement = str(uuid.uuid4())
    commande = [sys.executable, "scripts/reentrainer_modeles.py", "--modele", cle_modele, "--id-declenchement", id_declenchement]
    if horizon is not None:
        commande += ["--horizon", str(horizon)]

    chemin_log = _chemin_journal_direct(nom_journal_direct)
    with open(chemin_log, "w") as fichier_log:
        processus = subprocess.Popen(
            commande,
            stdout=fichier_log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    PROCESSUS_EN_COURS[nom_journal_direct] = processus
    return {"statut": "reentrainement_lance", "horodatage": horodatage_maroc(), "id_declenchement": id_declenchement}