import os

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DONNEES = os.path.join(RACINE, "data")

DEPOT_QUOTIDIEN_VENTES = os.path.join(DONNEES, "depot_quotidien", "ventes")
DEPOT_QUOTIDIEN_CONTROLES = os.path.join(DONNEES, "depot_quotidien", "controles")
DEPOT_QUOTIDIEN_CIRCULATION = os.path.join(DONNEES, "depot_quotidien", "circulation")

DEPOT_TRAITE_VENTES = os.path.join(DONNEES, "depot_traite", "ventes")
DEPOT_TRAITE_CONTROLES = os.path.join(DONNEES, "depot_traite", "controles")
DEPOT_TRAITE_CIRCULATION = os.path.join(DONNEES, "depot_traite", "circulation")

HISTORIQUE = os.path.join(DONNEES, "historique")
PREDICTIONS_NOUVELLES = os.path.join(DONNEES, "predictions_nouvelles")
RAPPORTS = os.path.join(DONNEES, "rapports")

LOG_EXECUTION = os.path.join(DONNEES, "log_execution.json")

LIEN_DOSSIER_DRIVE = ""

COLONNES_VENTEPDA = [
    "NumBillet", "Date", "Heure", "Montant", "NbreVoyageurs",
    "NiveauConfort", "LiaisonId", "NumTrain", "UserId", "Code", "Gamme",
]

COLONNES_ESSENTIELLES_VENTEPDA = ["Date", "Heure", "NumBillet", "LiaisonId", "NiveauConfort"]

COLONNES_CONTROLEPDA = [
    "ControleId", "NumBillet", "Date", "Heure", "NiveauConfort",
    "NumTrain", "LiaisonId", "MessageControle", "StatutControle",
    "TypeTitre", "GareId",
]

COLONNES_ESSENTIELLES_CONTROLEPDA = ["Date", "Heure", "ControleId", "LiaisonId", "TypeTitre", "MessageControle"]

COLONNES_CIRCULATION = [
    "NombreBilletCircule", "DateCirculation", "Heure", "LiaisonId",
]

COLONNES_ESSENTIELLES_CIRCULATION = ["DateCirculation", "Heure", "LiaisonId", "NombreBilletCircule"]
