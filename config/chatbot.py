CATEGORIES = {
    "performance": {
        "libelle": "Performance",
        "necessite_modele": True,
        "necessite_liaison": False,
        "necessite_periode": False,
        "necessite_horizon": True,
    },
    "anomalies": {
        "libelle": "Anomalies",
        "necessite_modele": True,
        "necessite_liaison": True,
        "necessite_periode": True,
        "necessite_horizon": True,
    },
    "predictions": {
        "libelle": "Prédictions",
        "necessite_modele": True,
        "necessite_liaison": True,
        "necessite_periode": True,
        "necessite_horizon": True,
    },
    "explicabilite": {
        "libelle": "Explicabilité",
        "necessite_modele": True,
        "necessite_liaison": False,
        "necessite_periode": False,
        "necessite_horizon": True,
    },
    "comparaison": {
        "libelle": "Comparaison / Tendances",
        "necessite_modele": True,
        "necessite_liaison": True,
        "necessite_periode": False,
        "necessite_horizon": True,
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
    "performance", "anomalies", "predictions", "explicabilite",
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
    "TauxFraude": "Part des contrôles ayant révélé une fraude, sur l'ensemble des contrôles.",
    "PDA": "Terminal portable (Portable Data Acquisition) utilisé pour la vente et le contrôle des billets.",
    "SHAP": "Méthode d'explicabilité qui mesure la contribution de chaque variable à une prédiction donnée.",
    "Horizon (J+N)": (
        "Nombre de jours entre la date du dernier dépôt de données et la date prédite. "
        "J+1 à J+6 sont calculés de façon récursive à partir du modèle standard, pour les 7 modèles de la plateforme. "
        "J+7, J+15 et J+30 s'appuient sur des modèles dédiés, entraînés spécifiquement pour cet horizon, "
        "disponibles uniquement pour les modèles Billets vendus et Billets contrôlés."
    ),
}

OPTION_TOUTES_LIAISONS_CHATBOT = "Toutes les liaisons"
OPTION_LIAISON_PRECISE = "Une liaison précise"
OPTIONS_PERIODE = ["Cette semaine", "2 dernières semaines", "Ce mois", "Date précise"]

SUGGESTIONS_CONTEXTUELLES = {
    "performance": ["anomalies", "explicabilite", "predictions"],
    "anomalies": ["comparaison", "predictions", "explicabilite"],
    "predictions": ["anomalies", "comparaison"],
    "explicabilite": ["performance", "anomalies"],
    "comparaison": ["anomalies", "predictions"],
    "pipeline": ["rapports", "anomalies"],
    "rapports": ["pipeline", "performance"],
}

EXEMPLES_QUESTIONS = {
    "performance": [
        ("Quelle est la performance du modèle billets vendus ?", "RMSE, MAE et WMAPE du modèle sur le jeu de test (horizon J+1 par défaut)."),
        ("Quelle est la précision du modèle de taux de fraude ?", "Les métriques de qualité du modèle taux de fraude."),
        ("Performance du modèle billets vendus à horizon J+15", "Métriques du modèle dédié entraîné spécifiquement pour l'horizon J+15."),
    ],
    "anomalies": [
        ("Y a-t-il des anomalies sur le taux de fraude cette semaine ?", "Nombre d'anomalies détectées sur la période, avec le détail des 10 écarts les plus importants."),
        ("Anomalies sur la liaison 100 pour les contrôles", "Anomalies filtrées sur cette liaison et ce modèle."),
        ("Anomalies des billets contrôlés à J+30", "Anomalies détectées par le modèle dédié à l'horizon J+30."),
    ],
    "predictions": [
        ("Quelle est la prochaine prédiction de billets vendus sur la liaison 100 ?", "Dernière prédiction disponible pour ce modèle et cette liaison, avec l'historique récent."),
        ("Prédiction du taux de contrôle cette semaine", "Dernière valeur prédite sur la période demandée."),
        ("Prédiction des billets vendus dans 7 jours", "Prédiction à l'horizon J+7 (modèle dédié)."),
        ("Prédiction du taux de fraude à J+4", "Prédiction récursive à l'horizon J+4, calculée pour tous les modèles."),
    ],
    "explicabilite": [
        ("Quelles sont les variables les plus importantes pour le modèle fraude ?", "Classement des variables par importance SHAP, en graphique et en tableau."),
        ("Variables importantes du modèle billets contrôlés à horizon J+7", "Importance des variables du modèle dédié à J+7."),
    ],
    "comparaison": [
        ("Compare le taux de fraude à l'année dernière", "Graphique de comparaison mensuelle entre années disponibles."),
        ("Montre la saisonnalité des billets vendus sur la liaison 100", "Décomposition tendance / saisonnalité pour cette liaison."),
        ("Calendrier des écarts du taux de contrôle", "Carte de chaleur des écarts prédiction-réel, jour par jour."),
        ("Calendrier des écarts des billets vendus à J+15", "Carte de chaleur des écarts calculée sur le modèle dédié à J+15."),
    ],
    "pipeline": [
        ("Quel est le dernier traitement du pipeline ?", "Statut, date traitée, nombre de fichiers traités et liaisons inconnues du dernier dépôt quotidien."),
    ],
    "rapports": [
        ("Quels rapports ont déjà été générés ?", "Liste des rapports PDF existants avec leur date de génération."),
        ("Génère un rapport", "Génération d'un nouveau rapport hebdomadaire, avec bouton de téléchargement."),
    ],
}