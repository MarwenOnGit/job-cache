# Install job cache on any laptop

Goal: get the app running in **one command**, with **no API keys** and **no paid services**.

## For a human

```bash
./run.sh
```

Requires **Python 3.9+**. First run installs everything, harvests jobs, and opens
<http://localhost:8000>. Port busy? `PORT=8080 ./run.sh`.

## For a Claude Code agent

If you're an agent asked to install this, run the shipped command:

```
/setup
```

or do it manually:

1. Check `python3 --version` (need 3.9+). If missing:
   - macOS: `brew install python`
   - Debian/Ubuntu: `sudo apt install python3 python3-venv`
2. `./run.sh` (creates `.venv`, installs deps, harvests, launches).
3. If it fails, run `./install.sh` to surface the dependency error, fix it, retry `./run.sh`.

## What gets installed

A local Python virtualenv (`.venv/`) with three packages: `fastapi`, `uvicorn`, `PyYAML`.
Nothing global, nothing cloud, no credentials.

## Daily use

1. `./run.sh` → dashboard.
2. **Queue for Claude** on jobs you like.
3. In the repo terminal: `claude` → `/apply` → materials appear back in the dashboard.
