#!/usr/bin/env bash
# Wipe all harvested jobs + the learned model and search again from profile/profile.yaml.
# Keeps your CV, preferences.md, applications/ and the queue. Stop the app first.
set -euo pipefail
cd "$(dirname "$0")"
if [ -f .venv/Scripts/activate ]; then source .venv/Scripts/activate; elif [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi
python backend/reset.py
cd backend && python harvester.py
