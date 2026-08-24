# Plateforme ONCF — Prédiction de Performance Commerciale

## 1. Prérequis : Git LFS


Installer Git LFS avant de cloner le dépôt :

```
sudo apt-get update && sudo apt-get install -y git-lfs
git lfs install
```

Si le dépôt a déjà été cloné avant cette étape, récupérer les vrais fichiers
après coup :

```
git lfs pull
```

Vérifier que les fichiers sont bien téléchargés (statut `*`, pas `-`) :

```
git lfs ls-files
```

## 2. Installation

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Lancer l'application

### Interface Streamlit (Terminal 1)

```
source .venv/bin/activate
streamlit run app.py
```

### API (Terminal 2)

```
chmod +x scripts/lancer_api.sh
./scripts/lancer_api.sh
```

## 4. Scripts manuels

### Traitement du dépôt quotidien

```
python scripts/traiter_depot_quotidien.py
```

### Réentraînement d'un modèle

```
python scripts/reentrainer_modeles.py --modele modele1_ventes --horizon 7
```

`--horizon` est optionnel et ne s'applique qu'aux modèles à horizons dédiés
(`modele1_ventes`, `modele3_controles`) 

## 5. Suivi mémoire

```
free -h
```