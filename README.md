# Plateforme ONCF - Performance Commerciale

## 1. Ce qui a changé après lecture des notebooks EDA et FE

La première version du pipeline supposait que les fichiers déposés chaque jour seraient des
tables transactionnelles brutes agrégées par un script maison. La lecture de
`eda-generation-final.ipynb` et des trois notebooks de feature engineering a montré une
réalité plus précise, et le pipeline a été corrigé en conséquence :

- **Date et Heure sont deux colonnes séparées**, pas une colonne `DateHeureVente` combinée.
- **Les modèles 5 et 6 sont en réalité à grain horaire** (Date × Heure × Liaison), pas
  journalier. Seul le modèle 2 est journalier parmi les modèles de taux.
- **Le taux de vente guichet n'est pas filtré par canal** : `TauxVenteGuichet` est simplement
  `NbBillets / NbCirculations`, tous canaux confondus. La colonne `Code` n'intervient nulle part
  dans le calcul.
- **La définition de la fraude est une liste précise de dix messages**, recherchés par
  correspondance partielle (contains) dans `MessageControle`. Cette liste est reprise
  exactement dans `utils/feature_engineering.py`.
- **La colonne `EstActif` n'existe pas** dans le pipeline réel : elle a été retirée de l'app.
- **Les features sont beaucoup plus riches** que ce qui avait été prévu initialement : pour
  chaque cible pertinente, le pipeline calcule liaison_frequence, un encodage cible expanding
  (moyenne de tout l'historique avant le jour courant), une interaction jour×liaison expanding,
  des lags à 1, 7, 14, 30 et 365 jours, et des moyennes/écarts-types glissants sur 7, 14 et 30
  jours. Tout cela est maintenant reproduit dans `utils/feature_engineering.py` et
  `utils/inference.py`.
- **NbCirculations et NbControles peuvent être utilisés comme features du jour même**,
  pas seulement en décalé, car dans les notebooks ce sont des quantités déjà connues au moment
  de la prédiction (planification des circulations, planification des contrôles). Voir la
  section 6 ci-dessous pour la limite que cela pose en usage réel.

## 2. Structure du projet

```
plateforme_oncf/
├── app.py
├── requirements.txt
├── .streamlit/config.toml
├── config/
│   ├── modeles.py              registre des 7 modèles (famille, granularité, cibles)
│   ├── calendrier_maroc.py      périodes Ramadan et vacances scolaires
│   └── chemins.py               chemins partagés, lien Google Drive, schémas bruts
├── utils/
│   ├── style.py                 thème visuel
│   ├── chargement.py            lecture des fichiers exportés
│   ├── feature_engineering.py   pivots EDA, définition de la fraude, lags/rolling/encodages
│   ├── agregation.py            construction des 7 tables par modèle à partir du dépôt brut
│   ├── inference.py             reconstruction complète des features et appel predict()
│   ├── composants.py            composants d'affichage réutilisés par les pages
│   ├── intentions.py            chatbot à base de règles
│   ├── rapport.py               génération du PDF hebdomadaire
│   └── texte.py                 phrases d'anomalies
├── pages/
│   ├── predictions/nouvelles_predictions.py
│   ├── ventes/dashboard_ventes.py, anomalies_ventes.py, explicabilite_ventes.py
│   ├── controles/dashboard_controles.py, anomalies_controles.py, explicabilite_controles.py
│   └── transverse/comparaison_inter_annees.py, rapports.py, chatbot.py
├── scripts/
│   ├── telecharger_depot.py         télécharge les fichiers du jour depuis Drive
│   ├── traiter_depot_quotidien.py   pipeline nocturne complet
│   ├── cron_quotidien.sh            script à enregistrer dans crontab
│   ├── generer_rapport.py           génération du rapport en dehors de l'app
│   └── verifier_installation.py     vérifie la présence des fichiers exportés
└── data/
    ├── ventes/modele1_ventes, modele2_taux_vente_guichet, modele4_part_confort
    ├── controles/modele3_controles, modele5_taux_controle, modele6_taux_fraude, modele7_type_titre
    ├── depot_quotidien/ventes, controles, circulation
    ├── depot_traite/ventes, controles, circulation
    ├── historique/
    ├── predictions_nouvelles/
    ├── rapports/
    └── log_execution.json
```

## 3. Installation

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Placer les exports Kaggle des 7 modèles

Décompresser chaque export dans le dossier correspondant, exactement comme listé dans
`config/modeles.py`. Chaque dossier de modèle doit contenir : `modele_final.cbm` ou
`modele_final.txt` (ou un sous-dossier `modeles/` et un `mapping_modeles_*.json` pour les
modèles 4 et 7), `metriques.json`, `predictions_test*.parquet`, `historique_brut_*.parquet`,
`anomalies*.csv`, `seuil_anomalie.json`, `importance_features*.csv`, `importance_shap*.csv`,
`colonnes_features.json`, `colonnes_categorielles.json`, `colonnes_calendaires.json`,
`encodage_liaison.csv`, `saisonnalite_decomposition*.csv`, `calendrier_quotidien*.csv`,
`comparaison_inter_annees*.csv`.

Lancer `python scripts/verifier_installation.py` pour vérifier que rien ne manque.

## 5. Configurer le dossier Google Drive de dépôt quotidien

1. Créer un dossier Google Drive séparé du code, par exemple `depot_pda_oncf`.
2. Le mettre en partage "Toute personne disposant du lien peut consulter".
3. Compléter `LIEN_DOSSIER_DRIVE` dans `config/chemins.py`.

Ne jamais déposer de vraies données ONCF dans ce dossier, uniquement des données simulées.

## 6. Format des fichiers déposés chaque jour

Trois fichiers par jour, nommés avec la date au format `AAAA-MM-JJ` :

- `ventes_2026-07-30.csv` — colonnes essentielles : Date, Heure, NumBillet, LiaisonId,
  NiveauConfort (Montant, NbreVoyageurs, NumTrain, UserId, Code, Gamme peuvent être présentes
  mais ne sont pas utilisées par le pipeline actuel).
- `controles_2026-07-30.csv` — colonnes essentielles : Date, Heure, ControleId, LiaisonId,
  TypeTitre, MessageControle (NumBillet, NiveauConfort, NumTrain, StatutControle, GareId
  peuvent être présentes mais ne sont pas utilisées).
- `circulation_2026-07-30.csv` — colonnes : DateCirculation, Heure, LiaisonId,
  NombreBilletCircule.

Date et Heure sont deux colonnes séparées, pas un timestamp combiné.

## 7. Programmer l'exécution automatique nocturne

```
crontab -e
0 2 * * * /chemin/vers/plateforme_oncf/scripts/cron_quotidien.sh
0 6 * * 1 /chemin/vers/plateforme_oncf/.venv/bin/python /chemin/vers/plateforme_oncf/scripts/generer_rapport.py
```

Le pipeline nocturne : télécharge les nouveaux fichiers depuis Drive, reconstruit exactement
les sept tables agrégées (comptages horaires pour les modèles 1 et 3, taux journalier pour le
modèle 2, taux horaires pour les modèles 5 et 6, compositions journalières pour les modèles 4
et 7), met à jour l'historique, réconcilie la prédiction de la veille avec la valeur réelle
reçue, calcule la nouvelle prédiction pour le jour suivant, archive les fichiers traités et
journalise le résultat dans `data/log_execution.json`.

## 8. Lancer l'application

```
source .venv/bin/activate
streamlit run app.py

chmod +x scripts/lancer_api.sh
./scripts/lancer_api.sh
free -h
python scripts/traiter_depot_quotidien.py
```

## 9. Calendrier marocain à maintenir chaque année

`config/calendrier_maroc.py` contient les périodes de Ramadan et de vacances scolaires. La
liste des vacances scolaires est vide dans les notebooks fournis (la feature `EstVacances` était
donc constante pendant l'entraînement) ; à compléter avec le calendrier scolaire officiel si
cette feature doit devenir utile pour les nouvelles prédictions. Les dates de Ramadan doivent
être ajoutées chaque année, ce calendrier étant lunaire.

## 10. Limitations connues

- Aucune coordonnée GPS n'est exportée par les notebooks : la carte des lignes ONCF n'est pas incluse.
- `liaison_frequence` est calculé ici comme le nombre total d'observations historiques pour la
  liaison, sans distinction d'heure ni de catégorie, par souci de simplicité. Si les notebooks
  de modélisation utilisent un regroupement plus fin, ajuster `calculer_liaison_frequence`
  dans `utils/feature_engineering.py`.
- L'authentification n'est pas implémentée. `streamlit-authenticator` peut être ajouté en tête
  de `app.py` si nécessaire.
