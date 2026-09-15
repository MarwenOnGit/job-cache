"""Maintains applications/applications.csv from the DB so the repo always has a record."""
from __future__ import annotations

import csv
import os

import db

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "applications", "applications.csv")

FIELDS = ["company", "title", "city", "role_family", "seniority", "req_years",
          "sponsorship", "match_score", "status", "apply_url", "first_seen",
          "last_seen", "id"]


def export_csv(conn, path: str = CSV_PATH) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = db.get_tracked(conn)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in FIELDS})
    return path
