import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.rapport import generer_rapport_hebdomadaire

if __name__ == "__main__":
    chemin = generer_rapport_hebdomadaire()
    print(f"Rapport généré : {chemin}")
