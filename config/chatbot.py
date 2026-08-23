CATEGORIES = {
    "performance": {
        "libelle": "Performance",
        "necessite_modele": True,
        "necessite_liaison": False,
        "necessite_periode": False,
        "necessite_horizon": False,
    },
    "anomalies": {
        "libelle": "Anomalies",
        "necessite_modele": True,
        "necessite_liaison": True,
        "necessite_periode": True,
        "necessite_horizon": False,
    },
    "predictions": {
        "libelle": "Prédictions",
        "necessite_modele": True,
        "necessite_liaison": True,
        "necessite_periode": False,
        "necessite_horizon": True,
    },
    "historique": {
        "libelle": "Historique",
        "necessite_modele": True,
        "necessite_liaison": True,
        "necessite_periode": True,
        "necessite_horizon": False,
    },
    "explicabilite": {
        "libelle": "Explicabilité",
        "necessite_modele": True,
        "necessite_liaison": False,
        "necessite_periode": False,
        "necessite_horizon": False,
    },
    "comparaison": {
        "libelle": "Comparaison / Tendances",
        "necessite_modele": True,
        "necessite_liaison": True,
        "necessite_periode": False,
        "necessite_horizon": False,
    },
    "pipeline": {
        "libelle": "État du pipeline",
        "necessite_modele": False,
        "necessite_liaison": False,
        "necessite_periode": False,
        "necessite_horizon": False,
    },
    "rapports": {
        "libelle": "Rapports",
        "necessite_modele": False,
        "necessite_liaison": False,
        "necessite_periode": False,
        "necessite_horizon": False,
    },
}

ORDRE_CATEGORIES = [
    "performance", "anomalies", "predictions", "historique", "explicabilite",
    "comparaison", "pipeline", "rapports",
]

MOTS_CLES_MODELE = {
    "modele1_ventes": [
        "billet vendu", "billets vendus", "nombre de billets", "ventes de billets", "billets",
    ],
    "modele2_taux_vente_guichet": [
        "taux de vente", "taux vente pda", "vente pda", "pda",
    ],
    "modele4_part_confort": [
        "confort", "classe de confort", "niveau de confort", "repartition confort", "part confort",
    ],
    "modele3_controles": [
        "billet controle", "billets controles", "nombre de controles", "controles effectues",
    ],
    "modele5_taux_controle": [
        "taux de controle", "taux controle",
    ],
    "modele6_taux_fraude": [
        "fraude", "taux de fraude", "fraudeurs", "fraudeur",
    ],
    "modele7_part_type": [
        "type de titre", "titre de transport", "repartition type", "part type",
    ],
}

MOTS_CLES_INTENTION = {
    "performance": ["performance", "precision", "rmse", "mae", "wmape", "fiabilite", "qualite du modele", "score"],
    "anomalies": ["anomalie", "anomalies", "ecart", "ecarts", "probleme", "incident"],
    "predictions": ["prediction", "predictions", "prevision", "previsions", "demain", "prochain", "prochaine"],
    "historique": ["historique", "evolution reelle", "suivi reel", "reel contre prediction", "courbe reelle", "valeurs passees"],
    "explicabilite": ["explicabilite", "shap", "importance", "variable importante", "feature", "pourquoi"],
    "comparaison": [
        "comparaison", "compare", "comparer", "evolution", "tendance", "annee derniere",
        "inter-annee", "inter annee", "saisonnalite", "saisonnier", "calendrier des ecarts", "calendrier",
    ],
    "pipeline": ["pipeline", "log d'execution", "execution", "depot quotidien", "derniere execution", "traitement quotidien"],
    "rapports": ["rapport", "rapports", "generer un rapport", "pdf"],
    "aide": ["aide", "help", "que peux-tu faire", "capacites", "guide"],
}

HORIZONS_RECURSIFS_CHATBOT = [1, 2, 3, 4, 5, 6]
HORIZONS_DEDIES_CHATBOT = [7, 15, 30]
HORIZONS_CHATBOT_VALIDES = HORIZONS_RECURSIFS_CHATBOT + HORIZONS_DEDIES_CHATBOT

MODELES_HORIZON_DEDIE_CHATBOT = ["modele1_ventes", "modele3_controles"]

LIBELLES_HORIZON = {
    1: "J+1 (demain)",
    2: "J+2",
    3: "J+3",
    4: "J+4",
    5: "J+5",
    6: "J+6",
    7: "J+7 (1 semaine)",
    15: "J+15 (2 semaines)",
    30: "J+30 (1 mois)",
}

MOTS_CLES_HORIZON_VERBAL = {
    1: ["demain"],
    7: ["dans une semaine", "a horizon d'une semaine", "sur une semaine", "a une semaine", "a horizon 1 semaine"],
    15: ["dans quinze jours", "a horizon de quinze jours", "sur quinze jours", "a quinze jours", "a horizon 2 semaines", "dans deux semaines"],
    30: ["dans un mois", "a horizon d'un mois", "sur un mois", "a un mois", "a horizon 1 mois"],
}

GLOSSAIRE = {
    "WMAPE": "Weighted Mean Absolute Percentage Error, erreur moyenne pondérée en pourcentage.",
    "RMSE": "Root Mean Squared Error, racine de l'erreur quadratique moyenne.",
    "MAE": "Mean Absolute Error, erreur absolue moyenne.",
    "PDA": "Terminal portable (Portable Data Acquisition) utilisé pour la vente et le contrôle des billets.",
    "SHAP": "Méthode d'explicabilité qui mesure la contribution de chaque variable à une prédiction donnée.",
}

OPTION_TOUTES_LIAISONS_CHATBOT = "Toutes les liaisons"
OPTION_LIAISON_PRECISE = "Une liaison précise"
OPTION_TOUTES_HEURES_CHATBOT = "Toutes les heures"
OPTIONS_PERIODE = ["Toutes les dates", "Cette semaine", "2 dernières semaines", "Ce mois", "Date précise"]

SUGGESTIONS_CONTEXTUELLES = {
    "performance": ["anomalies", "explicabilite", "predictions"],
    "anomalies": ["comparaison", "predictions", "explicabilite"],
    "predictions": ["historique", "anomalies", "comparaison"],
    "historique": ["predictions", "anomalies"],
    "explicabilite": ["performance", "anomalies"],
    "comparaison": ["anomalies", "predictions"],
    "pipeline": ["rapports", "anomalies"],
    "rapports": ["pipeline", "performance"],
}

EXEMPLES_QUESTIONS = {
    "performance": [
        ("Quelle est la performance du modèle billets vendus ?", "RMSE, MAE et WMAPE du modèle sur le jeu de test (horizon J+1)."),
        ("Quelle est la précision du modèle de taux de fraude ?", "Les métriques de qualité du modèle taux de fraude."),
    ],
    "anomalies": [
        ("Y a-t-il des anomalies sur le taux de fraude cette semaine ?", "Nombre d'anomalies détectées sur la période, avec le détail des 10 écarts les plus importants."),
        ("Anomalies sur la liaison 100 pour les contrôles", "Anomalies filtrées sur cette liaison et ce modèle, toutes dates."),
    ],
    "predictions": [
        ("Quelle est la prochaine prédiction de billets vendus sur la liaison 100 ?", "Prédiction J+1 disponible pour ce modèle et cette liaison."),
        ("Prédiction des billets vendus dans 7 jours", "Prédiction à l'horizon J+7 (modèle dédié), toutes liaisons."),
        ("Prédiction du taux de fraude à J+4", "Prédiction récursive à l'horizon J+4, calculée pour tous les modèles."),
        ("Prédiction des billets contrôlés à 14h sur la liaison 100", "Prédiction J+1 filtrée sur l'heure et la liaison précisées (modèles horaires)."),
    ],
    "historique": [
        ("Historique du taux de fraude", "Courbe réel vs prédiction sur tout l'historique disponible."),
        ("Historique des billets vendus sur la liaison 100 ce mois", "Courbe réel vs prédiction sur les 30 derniers jours, pour cette liaison."),
        ("Historique des billets contrôlés à 9h", "Courbe réel vs prédiction filtrée sur cette heure (modèles horaires)."),
    ],
    "explicabilite": [
        ("Quelles sont les variables les plus importantes pour le modèle fraude ?", "Classement des variables par importance SHAP, en graphique et en tableau."),
    ],
    "comparaison": [
        ("Compare le taux de fraude à l'année dernière", "Graphique de comparaison mensuelle entre années disponibles."),
        ("Montre la saisonnalité des billets vendus sur la liaison 100", "Décomposition tendance / saisonnalité pour cette liaison."),
        ("Calendrier des écarts du taux de contrôle", "Carte de chaleur des écarts prédiction-réel, jour par jour."),
    ],
    "pipeline": [
        ("Quel est le dernier traitement du pipeline ?", "Statut, date traitée, nombre de fichiers traités et liaisons inconnues du dernier dépôt quotidien."),
    ],
    "rapports": [
        ("Quels rapports ont déjà été générés ?", "Liste des rapports PDF existants avec leur date de génération."),
        ("Génère un rapport", "Génération d'un nouveau rapport hebdomadaire, avec bouton de téléchargement."),
    ],
}