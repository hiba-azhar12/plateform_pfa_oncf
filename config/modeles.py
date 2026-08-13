import os

RACINE_DONNEES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

FICHIERS_COMMUNS = {
    "metriques": "metriques.json",
    "seuil_anomalie": "seuil_anomalie.json",
    "importance_features": "importance_features.csv",
    "importance_shap": "importance_shap.csv",
    "colonnes_features": "colonnes_features.json",
    "colonnes_categorielles": "colonnes_categorielles.json",
    "colonnes_calendaires": "colonnes_calendaires.json",
    "encodage_liaison": "encodage_liaison.csv",
    "comparaison_inter_annees": "comparaison_inter_annees.csv",
    "calendrier_quotidien": "calendrier_quotidien.csv",
    "saisonnalite": "saisonnalite_decomposition.csv",
}


def _fichiers(predictions, historique, anomalies, comparaison=None, calendrier=None):
    fichiers = dict(FICHIERS_COMMUNS)
    fichiers["predictions"] = predictions
    fichiers["historique"] = historique
    fichiers["anomalies"] = anomalies
    if comparaison is not None:
        fichiers["comparaison_inter_annees"] = comparaison
    if calendrier is not None:
        fichiers["calendrier_quotidien"] = calendrier
    return fichiers


MODELES = {
    "modele1_ventes": {
        "domaine": "ventes",
        "famille": "comptages",
        "granularite": "horaire",
        "cible": "NbBillets",
        "cible_denominateur": None,
        "libelle": "Nombre de billets vendus",
        "libelle_court": "Billets vendus",
        "dossier": os.path.join(RACINE_DONNEES, "ventes", "modele1_ventes"),
        "multi_categorie": False,
        "colonne_categorie": None,
        "format_modele": "catboost",
        "fichier_modele": "modele_final.cbm",
        "fichiers": _fichiers("predictions_test.parquet", "historique_brut_ventes.parquet", "anomalies.csv"),
    },
    "modele2_taux_vente_guichet": {
        "domaine": "ventes",
        "famille": "taux",
        "granularite": "journaliere",
        "cible": "TauxVenteGuichet",
        "cible_denominateur": "NbCirculations",
        "libelle": "Taux de ventes guichet",
        "libelle_court": "Taux vente guichet",
        "dossier": os.path.join(RACINE_DONNEES, "ventes", "modele2_taux_vente_guichet"),
        "multi_categorie": False,
        "colonne_categorie": None,
        "format_modele": "lightgbm",
        "fichier_modele": "modele_final.txt",
        "fichiers": _fichiers("predictions_test.parquet", "historique_brut_ventes_guichet.parquet", "anomalies.csv"),
    },
    "modele4_part_confort": {
        "domaine": "ventes",
        "famille": "composition",
        "granularite": "journaliere",
        "cible": "PartConfort",
        "cible_denominateur": None,
        "libelle": "Répartition des ventes par classe de confort",
        "libelle_court": "Part confort",
        "dossier": os.path.join(RACINE_DONNEES, "ventes", "modele4_part_confort"),
        "multi_categorie": True,
        "colonne_categorie": "NiveauConfort",
        "format_modele": "lightgbm",
        "dossier_modeles": "modeles",
        "mapping_modeles": "mapping_modeles_NiveauConfort.json",
        "fichiers": _fichiers(
            "predictions_test_confort.parquet", "historique_brut_confort.parquet", "anomalies_confort.csv",
            comparaison="comparaison_inter_annees_confort.csv", calendrier="calendrier_quotidien_confort.csv",
        ),
    },
    "modele3_controles": {
        "domaine": "controles",
        "famille": "comptages",
        "granularite": "horaire",
        "cible": "NbControles",
        "cible_denominateur": None,
        "libelle": "Nombre de billets contrôlés",
        "libelle_court": "Billets contrôlés",
        "dossier": os.path.join(RACINE_DONNEES, "controles", "modele3_controles"),
        "multi_categorie": False,
        "colonne_categorie": None,
        "format_modele": "lightgbm",
        "fichier_modele": "modele_final.txt",
        "fichiers": _fichiers("predictions_test.parquet", "historique_brut_controles.parquet", "anomalies.csv"),
    },
    "modele5_taux_controle": {
        "domaine": "controles",
        "famille": "taux",
        "granularite": "journaliere",
        "cible": "TauxControle",
        "cible_denominateur": "NbCirculations",
        "libelle": "Taux de billets contrôlés",
        "libelle_court": "Taux contrôle",
        "dossier": os.path.join(RACINE_DONNEES, "controles", "modele5_taux_controle"),
        "multi_categorie": False,
        "colonne_categorie": None,
        "format_modele": "catboost",
        "fichier_modele": "modele_final.cbm",
        "fichiers": _fichiers("predictions_test.parquet", "historique_brut_controle.parquet", "anomalies.csv"),
    },
    "modele6_taux_fraude": {
        "domaine": "controles",
        "famille": "taux",
        "granularite": "journaliere",
        "cible": "TauxFraude",
        "cible_denominateur": "NbControles",
        "libelle": "Taux de fraude",
        "libelle_court": "Taux fraude",
        "dossier": os.path.join(RACINE_DONNEES, "controles", "modele6_taux_fraude"),
        "multi_categorie": False,
        "colonne_categorie": None,
        "format_modele": "lightgbm",
        "fichier_modele": "modele_final.txt",
        "fichiers": _fichiers("predictions_test.parquet", "historique_brut_fraude.parquet", "anomalies.csv"),
    },
    "modele7_part_type": {
        "domaine": "controles",
        "famille": "composition",
        "granularite": "journaliere",
        "cible": "PartType",
        "cible_denominateur": None,
        "libelle": "Répartition des contrôles par type de titre",
        "libelle_court": "Part type de titre",
        "dossier": os.path.join(RACINE_DONNEES, "controles", "modele7_type_titre"),
        "multi_categorie": True,
        "colonne_categorie": "TypeTitre",
        "format_modele": "lightgbm",
        "dossier_modeles": "modeles",
        "mapping_modeles": "mapping_modeles_TypeTitre.json",
        "fichiers": _fichiers(
            "predictions_test_type.parquet", "historique_brut_type.parquet", "anomalies_type.csv",
            comparaison="comparaison_inter_annees_type.csv", calendrier="calendrier_quotidien_type.csv",
        ),
    },
}

MODELES_PAR_DOMAINE = {
    "ventes": ["modele1_ventes", "modele2_taux_vente_guichet", "modele4_part_confort"],
    "controles": ["modele3_controles", "modele5_taux_controle", "modele6_taux_fraude", "modele7_part_type"],
}

LAGS = [1, 7, 14, 30, 365]
FENETRES_ROLLING = [7, 14, 30]


def chemin_fichier(cle_modele, cle_fichier):
    info = MODELES[cle_modele]
    return os.path.join(info["dossier"], info["fichiers"][cle_fichier])


def chemin_modele(cle_modele, nom_categorie=None):
    info = MODELES[cle_modele]
    if info["multi_categorie"]:
        return os.path.join(info["dossier"], info["dossier_modeles"], nom_categorie)
    return os.path.join(info["dossier"], info["fichier_modele"])