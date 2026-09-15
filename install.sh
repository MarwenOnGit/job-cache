#!/usr/bin/env bash
# One-time setup: create a local venv and install Python deps. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.9+ and re-run." >&2
  exit 1
fi

if [ ! -d .venv ]; then
  echo "Creating virtual environment (.venv)…"
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
echo "Dependencies installed. Run ./run.sh to launch."
