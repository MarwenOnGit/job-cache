"""Harvest orchestrator: companies.yaml + profile search terms -> live queries ->
adapters -> enrich -> filter -> SQLite."""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import yaml

from adapters import AGGREGATORS, fetch_company
from flagger import classify_sponsorship
from models import Job
from normalize import classify_city, classify_role_family
from ranker import score_job
from seniority import classify_seniority, extract_required_years
import db
import prefs as prefs_mod
import profile_store
import queue_io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPANIES_PATH = os.path.join(ROOT, "companies.yaml")
_WORKERS = 8


def load_companies(path: Optional[str] = None) -> List[dict]:
    """Every source to harvest: the curated per-company ATS list plus the keyless
    aggregator boards (each aggregator entry fans out to many employers)."""
    with open(path or COMPANIES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return (data.get("companies", []) or []) + (data.get("sources", []) or [])


def _is_aggregator(company: dict) -> bool:
    return bool(company.get("aggregator")) or (company.get("ats_type") or "").lower() in AGGREGATORS


def enrich(job: Job, extra_keywords: Optional[List[str]] = None) -> Job:
    job.city = classify_city(job.location_raw)
    job.role_family = classify_role_family(job.title, job.description)
    job.sponsorship = classify_sponsorship(job.description)
    job.seniority = classify_seniority(job.title, job.description)
    job.req_years = extract_required_years(job.description)
    job.match_score, job.match_reasons = score_job(
        job.title, job.description, job.posted_at, extra_skills=extra_keywords)
    return job


def keep(job: Job, prefs: Optional[dict] = None) -> bool:
    """A job is kept when its location and role family are both in the user's
    search preferences. `prefs=None` means the broadest search (keep every
    supported location and role family)."""
    prefs = prefs if prefs is not None else prefs_mod.DEFAULTS
    return (job.city in prefs_mod.target_locations(prefs)
            and job.role_family in prefs_mod.target_role_families(prefs))


def ranking_terms(prefs: dict) -> List[str]:
    """Terms the ranker rewards on top of its base vocabulary: the skills listed in
    the user's own CV, plus titles/keywords saved in the search preferences."""
    terms = prefs_mod.extra_keywords(prefs)
    for s in profile_store.extract_skills(queue_io.read_cv()):
        if s not in terms:
            terms.append(s)
    return terms


def expand_sources(companies: List[dict], prefs: dict) -> List[dict]:
    """Turn every `auto` query param into one live search per profile search term.

    A source like `{ats_type: remotive, search: auto}` becomes one Remotive query for
    each term in profile.yaml `jobs.search_terms` (+ titles saved in the dashboard);
    `auto_local` uses the French/German `jobs.local_terms`. So what gets searched
    follows the profile instead of search strings hard-coded in companies.yaml."""
    queries = profile_store.job_queries(prefs)
    local = profile_store.local_job_queries()
    out: List[dict] = []
    for company in companies:
        key = next((k for k, v in company.items()
                    if isinstance(v, str) and v in ("auto", "auto_local")), None)
        if key is None:
            out.append(company)
            continue
        terms = local if company[key] == "auto_local" else queries
        for term in terms:
            entry = dict(company)
            entry[key] = term
            entry["name"] = f"{company.get('name', company.get('ats_type'))}: {term}"
            out.append(entry)
    return out


def harvest(conn, companies: Optional[List[dict]] = None, verbose: bool = True) -> dict:
    prefs = prefs_mod.load_structured()
    companies = expand_sources(companies if companies is not None else load_companies(), prefs)
    extra_kw = ranking_terms(prefs)
    db.init_db(conn)
    summary = {"companies": 0, "fetched": 0, "kept": 0, "errors": []}
    seen: set = set()

    # Network-bound: fetch every source concurrently, then process in order.
    def _fetch(company: dict):
        try:
            return fetch_company(company), None
        except Exception as e:  # noqa: BLE001 - one bad source must not abort the run
            return None, e

    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        results = list(pool.map(_fetch, companies))

    for company, (raw, err) in zip(companies, results):
        name = company.get("name", "?")
        summary["companies"] += 1
        if err is not None:
            e = err
            summary["errors"].append(f"{name} ({company.get('ats_type')}): {e}")
            if verbose:
                print(f"  ! {name}: {e}", file=sys.stderr)
            continue

        summary["fetched"] += len(raw)
        kept: List[Job] = []
        for job in raw:
            if job.id in seen:      # the same posting returned by several queries
                continue
            enrich(job, extra_kw)
            if keep(job, prefs):
                kept.append(job)
                seen.add(job.id)

        db.upsert_jobs(conn, kept)
        # Only single-company ATS boards own their full job set, so only they can
        # safely close roles that disappeared. Aggregators return an employer per
        # posting, not one company, so we never auto-close from them.
        if not _is_aggregator(company):
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
