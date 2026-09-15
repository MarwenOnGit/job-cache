---
description: Install and launch job-hunter on this machine (for a Claude Code agent)
---

Install and run the job-hunter app on this laptop, end to end. Do this:

1. Confirm `python3` is available (`python3 --version`). It needs Python 3.9+.
   If missing, tell the user how to install it (macOS: `brew install python`;
   Debian/Ubuntu: `sudo apt install python3 python3-venv`) and stop.
2. From the repo root, run `./run.sh`. This creates `.venv`, installs dependencies,
   harvests jobs from free public job boards on first run, and starts the dashboard
   at http://localhost:8000 (opening the browser automatically).
3. If port 8000 is busy, run `PORT=8080 ./run.sh` instead.
4. Tell the user: browse jobs, click **Queue for Claude** on the ones they like, then
   run `/apply` in Claude Code to generate tailored cover letters + CV bullets, which
   appear back in the dashboard.

If `./run.sh` fails, run `./install.sh` first to surface the dependency error, fix it,
then retry `./run.sh`. Never require any API key — there are none.
