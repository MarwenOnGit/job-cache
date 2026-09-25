#!/usr/bin/env bash
# One-click: installs deps if needed, harvests on first run, launches the dashboard.
set -euo pipefail
cd "$(dirname "$0")"

# 1. Ensure dependencies.
if [ ! -d .venv ]; then
  ./install.sh
fi
# shellcheck disable=SC1091
if [ -f .venv/Scripts/activate ]; then
  source .venv/Scripts/activate
else
  source .venv/bin/activate
fi

PORT="${PORT:-8000}"
URL="http://localhost:${PORT}"

# 2. One-time clean slate: drops the old harvested jobs so everything is rebuilt from
#    profile/profile.yaml (no-op once done; run ./reset.sh to wipe again later).
python backend/reset.py --once

# 3. Fresh live search on every launch (in the background, so the dashboard opens
#    right away with the jobs you already have; refresh the page when it finishes).
mkdir -p data
echo "Searching job boards with your profile's search terms (log: data/harvest.log)…"
( cd backend && python harvester.py > ../data/harvest.log 2>&1 \
    || echo "Harvest had issues; retry from the UI." >> ../data/harvest.log ) &

# 4. Open the browser shortly after the server starts.
( sleep 1.5
  if command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
  elif command -v cmd.exe >/dev/null 2>&1; then cmd.exe /c start "" "$URL"
  fi ) &

echo "Dashboard: ${URL}  (Ctrl+C to stop)"
# Dual-stack launcher (backend/serve.py): one socket serving both IPv4 (127.0.0.1)
# and IPv6 (::1) so `localhost` always resolves, whichever family the browser picks.
cd backend
exec env PORT="$PORT" python serve.py
