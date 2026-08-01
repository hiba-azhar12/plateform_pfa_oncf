#!/bin/bash
cd "$(dirname "$0")/.."
source .venv/bin/activate
python scripts/traiter_depot_quotidien.py >> data/log_execution_brut.txt 2>&1
