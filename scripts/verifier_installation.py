import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.modeles import MODELES


def verifier():
    manquants_totaux = 0
    for cle_modele, info in MODELES.items():
        print(f"{cle_modele} ({info['dossier']})")
        for cle_fichier, nom_fichier in info["fichiers"].items():
            chemin = os.path.join(info["dossier"], nom_fichier)
            present = os.path.isfile(chemin)
            marqueur = "present" if present else "absent"
            if not present:
                manquants_totaux += 1
            print(f"  {cle_fichier} : {nom_fichier} -> {marqueur}")

        if info["multi_categorie"]:
            chemin_mapping = os.path.join(info["dossier"], info["mapping_modeles"])
            present = os.path.isfile(chemin_mapping)
            if not present:
                manquants_totaux += 1
            print(f"  mapping_modeles : {info['mapping_modeles']} -> {'present' if present else 'absent'}")
        else:
            chemin_modele_fichier = os.path.join(info["dossier"], info["fichier_modele"])
            present = os.path.isfile(chemin_modele_fichier)
            if not present:
                manquants_totaux += 1
            print(f"  fichier_modele : {info['fichier_modele']} -> {'present' if present else 'absent'}")

    print(f"\nTotal fichiers manquants : {manquants_totaux}")


if __name__ == "__main__":
    verifier()
