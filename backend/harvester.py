"""Harvest orchestrator: companies.yaml -> adapters -> enrich -> filter -> SQLite."""
from __future__ import annotations

import os
import sys
from typing import List, Optional

import yaml

from adapters import fetch_company
from flagger import classify_sponsorship
from models import Job
from normalize import TARGET_CITIES, classify_city, classify_role_family
from ranker import score_job
from seniority import classify_seniority, extract_required_years
import db

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPANIES_PATH = os.path.join(ROOT, "companies.yaml")


def load_companies(path: Optional[str] = None) -> List[dict]:
    with open(path or COMPANIES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("companies", []) or []


def enrich(job: Job) -> Job:
    job.city = classify_city(job.location_raw)
    job.role_family = classify_role_family(job.title, job.description)
    job.sponsorship = classify_sponsorship(job.description)
    job.seniority = classify_seniority(job.title, job.description)
    job.req_years = extract_required_years(job.description)
    job.match_score, job.match_reasons = score_job(job.title, job.description, job.posted_at)
    return job


def keep(job: Job) -> bool:
    return job.city in TARGET_CITIES and job.role_family is not None


def harvest(conn, companies: Optional[List[dict]] = None, verbose: bool = True) -> dict:
    companies = companies if companies is not None else load_companies()
    db.init_db(conn)
    summary = {"companies": 0, "fetched": 0, "kept": 0, "errors": []}

    for company in companies:
        name = company.get("name", "?")
        summary["companies"] += 1
        try:
            raw = fetch_company(company)
        except Exception as e:  # noqa: BLE001 - one bad company must not abort the run
            summary["errors"].append(f"{name} ({company.get('ats_type')}): {e}")
            if verbose:
                print(f"  ! {name}: {e}", file=sys.stderr)
            continue

        summary["fetched"] += len(raw)
        kept: List[Job] = []
        for job in raw:
            enrich(job)
            if keep(job):
                kept.append(job)

        db.upsert_jobs(conn, kept)
        db.mark_closed(conn, name, [j.id for j in kept])
        summary["kept"] += len(kept)
        if verbose:
            print(f"  + {name}: {len(kept)} kept / {len(raw)} fetched")

    return summary


def main() -> None:
    conn = db.connect()
    print("Harvesting jobs...")
    summary = harvest(conn)
    print(f"\nDone. {summary['kept']} relevant jobs from {summary['companies']} companies "
          f"({summary['fetched']} fetched, {len(summary['errors'])} errors).")
    conn.close()


if __name__ == "__main__":
    main()
