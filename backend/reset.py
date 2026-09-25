"""Wipe the harvested search data so the next harvest starts from scratch.

Removes the SQLite DB (all harvested jobs, their statuses and the decision log), the
learned preference model, saved dashboard search preferences and the old onboarding
form, so everything is rebuilt from profile/profile.yaml. Your CV, preferences.md,
generated application materials (applications/) and the queue are NOT touched.

    python backend/reset.py          # wipe now
    python backend/reset.py --once   # wipe only if this reset version hasn't run yet
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
# Bump to force one more automatic wipe on every machine at next launch.
RESET_VERSION = "1"
MARKER = os.path.join(DATA, f".reset-{RESET_VERSION}")

TARGETS = ["jobs.db", "jobs.db-wal", "jobs.db-shm", "model.json",
           "preferences.json", "onboarding.json", "harvest.log"]


def wipe(data_dir: str = "") -> list:
    data_dir = data_dir or DATA
    removed = []
    for name in TARGETS:
        path = os.path.join(data_dir, name)
        if os.path.exists(path):
            os.remove(path)
            removed.append(name)
    return removed


def mark(marker: str = "") -> None:
    marker = marker or MARKER
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    with open(marker, "w", encoding="utf-8") as f:
        f.write("done\n")


def main(argv: list) -> None:
    if "--once" in argv and os.path.exists(MARKER):
        return
    removed = wipe()
    mark()
    print("Reset search data: " + (", ".join(removed) if removed else "nothing to remove")
          + ". Next harvest rebuilds everything from profile/profile.yaml.")


if __name__ == "__main__":
    main(sys.argv[1:])
