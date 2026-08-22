import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gdown

from config.chemins import (
    DEPOT_QUOTIDIEN_CIRCULATION,
    DEPOT_QUOTIDIEN_CONTROLES,
    DEPOT_QUOTIDIEN_VENTES,
    DEPOT_TRAITE_CIRCULATION,
    DEPOT_TRAITE_CONTROLES,
    DEPOT_TRAITE_VENTES,
    LIEN_DOSSIER_DRIVE,
)

PREFIXES_VERS_DOSSIER = {
    "ventes_": DEPOT_QUOTIDIEN_VENTES,
    "controles_": DEPOT_QUOTIDIEN_CONTROLES,
    "circulation_": DEPOT_QUOTIDIEN_CIRCULATION,
}

PREFIXES_VERS_DOSSIER_TRAITE = {
    "ventes_": DEPOT_TRAITE_VENTES,
    "controles_": DEPOT_TRAITE_CONTROLES,
    "circulation_": DEPOT_TRAITE_CIRCULATION,
}


def telecharger_nouveaux_fichiers():
    if not LIEN_DOSSIER_DRIVE:
        raise ValueError("LIEN_DOSSIER_DRIVE doit être renseigné dans config/chemins.py")

    racine = os.path.dirname(DEPOT_QUOTIDIEN_VENTES)
    dossier_temporaire = os.path.join(os.path.dirname(racine), "_telechargement_temporaire")
    os.makedirs(dossier_temporaire, exist_ok=True)

    gdown.download_folder(url=LIEN_DOSSIER_DRIVE, output=dossier_temporaire, quiet=False, use_cookies=False)

    fichiers_deplaces = []
    for racine_courante, _, noms_fichiers in os.walk(dossier_temporaire):
        for nom_fichier in noms_fichiers:
            for prefixe, dossier_cible in PREFIXES_VERS_DOSSIER.items():
                if nom_fichier.startswith(prefixe):
                    source = os.path.join(racine_courante, nom_fichier)
                    destination = os.path.join(dossier_cible, nom_fichier)
                    destination_traitee = os.path.join(PREFIXES_VERS_DOSSIER_TRAITE[prefixe], nom_fichier)
                    if not os.path.isfile(destination) and not os.path.isfile(destination_traitee):
                        shutil.move(source, destination)
                        fichiers_deplaces.append(nom_fichier)
                    break

    shutil.rmtree(dossier_temporaire, ignore_errors=True)
    return fichiers_deplaces


if __name__ == "__main__":
    fichiers = telecharger_nouveaux_fichiers()
    print(f"{len(fichiers)} fichier(s) téléchargé(s) : {fichiers}")