"""The Muse public jobs API (keyless aggregator across many employers).

https://www.themuse.com/api/public/jobs?page=0&category=...&location=...

Optional source params:
  pages:    how many pages to walk (default 3; each page ~20 postings)
  category: e.g. "Software Engineering", "Data Science"
  location: a city name, e.g. "London, United Kingdom" (may be a list)
"""
from __future__ import annotations

from typing import List
from urllib.parse import urlencode

from http_util import get_json
from models import Job
from normalize import strip_html

BASE = "https://www.themuse.com/api/public/jobs"


def _location(j: dict) -> str:
    locs = [l.get("name") for l in (j.get("locations") or []) if l.get("name")]
    return ", ".join(locs)


def parse(company: dict, payload: dict) -> List[Job]:
    jobs: List[Job] = []
    for j in payload.get("results", []) or []:
        co = (j.get("company") or {}).get("name") or "Unknown"
        refs = j.get("refs") or {}
        jobs.append(Job(
            company=co.strip() or "Unknown",
            ats_type="themuse",
            ats_job_id=str(j.get("id")),
            title=j.get("name", "") or "",
            location_raw=_location(j),
            description=strip_html(j.get("contents", "")),
            apply_url=refs.get("landing_page", "") or "",
            posted_at=j.get("publication_date"),
            is_startup=False,
        ))
    return jobs


def _params(company: dict, page: int) -> str:
    pairs = [("page", page)]
    cats = company.get("category")
    for c in (cats if isinstance(cats, list) else [cats] if cats else []):
        pairs.append(("category", c))
    locs = company.get("location")
    for l in (locs if isinstance(locs, list) else [locs] if locs else []):
        pairs.append(("location", l))
    return urlencode(pairs)


def fetch(company: dict) -> List[Job]:
    pages = int(company.get("pages", 3))
    jobs: List[Job] = []
    for page in range(pages):
        payload = get_json(f"{BASE}?{_params(company, page)}")
        batch = parse(company, payload)
        if not batch:
            break
        jobs.extend(batch)
    return jobs
