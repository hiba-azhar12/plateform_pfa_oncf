
## 1. Installation

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Lancer l'application

```
source .venv/bin/activate
streamlit run app.py

chmod +x scripts/lancer_api.sh
./scripts/lancer_api.sh
free -h
python scripts/traiter_depot_quotidien.py

sudo apt-get update && sudo apt-get install -y git-lfs
git lfs install
git lfs pull
```