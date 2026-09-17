"""Arbeitnow public job-board API (keyless aggregator, Europe-heavy).

https://www.arbeitnow.com/api/job-board-api?page=N

Arbeitnow is a German/EU job board, so its postings skew toward European cities and
EU-eligible remote roles — a strong broadener for this tool. Optional source params:
  pages: how many pages to walk (default 5, ~100 postings)
"""
from __future__ import annotations

from typing import List

from http_util import get_json
from models import Job
from normalize import strip_html

BASE = "https://www.arbeitnow.com/api/job-board-api"


def _location(j: dict) -> str:
    loc = (j.get("location") or "").strip()
    if j.get("remote"):
        loc = (loc + " (Remote)").strip() if loc else "Remote"
    return loc


def parse(company: dict, payload: dict) -> List[Job]:
    jobs: List[Job] = []
    for j in payload.get("data", []) or []:
        created = j.get("created_at")
        jobs.append(Job(
            company=(j.get("company_name") or "").strip() or "Unknown",
            ats_type="arbeitnow",
            ats_job_id=str(j.get("slug") or j.get("url")),
            title=j.get("title", "") or "",
            location_raw=_location(j),
            description=strip_html(j.get("description", "")),
            apply_url=j.get("url", "") or "",
            posted_at=str(created) if created is not None else None,
            is_startup=False,
        ))
    return jobs


def fetch(company: dict) -> List[Job]:
    pages = int(company.get("pages", 5))
    jobs: List[Job] = []
    for page in range(1, pages + 1):
        payload = get_json(f"{BASE}?page={page}")
        batch = parse(company, payload)
        if not batch:
            break
        jobs.extend(batch)
    return jobs
