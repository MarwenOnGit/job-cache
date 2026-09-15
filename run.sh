#!/usr/bin/env bash
# One-click: installs deps if needed, harvests on first run, launches the dashboard.
set -euo pipefail
cd "$(dirname "$0")"

# 1. Ensure dependencies.
if [ ! -d .venv ]; then
  ./install.sh
fi
# shellcheck disable=SC1091
source .venv/bin/activate

PORT="${PORT:-8000}"
URL="http://localhost:${PORT}"

# 2. First-run harvest so the dashboard isn't empty.
if [ ! -f data/jobs.db ]; then
  echo "First run — harvesting jobs (this hits free public job boards)…"
  python backend/harvester.py || echo "Harvest had issues; you can retry from the UI."
fi

# 3. Open the browser shortly after the server starts.
( sleep 1.5
  if command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
  fi ) &

echo "Dashboard: ${URL}  (Ctrl+C to stop)"
# Dual-stack launcher (backend/serve.py): one socket serving both IPv4 (127.0.0.1)
# and IPv6 (::1) so `localhost` always resolves, whichever family the browser picks.
cd backend
exec env PORT="$PORT" python serve.py
