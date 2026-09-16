"""Remotive public jobs API (keyless aggregator across many employers).

https://remotive.com/api/remote-jobs?limit=100&search=...&category=...

Each source entry fans out to every employer Remotive lists, so one line in
companies.yaml pulls hundreds of postings. Optional params on the source dict:
  search:   free-text query (e.g. "python")
  category: Remotive category slug (e.g. "software-dev", "data")
  limit:    max postings to fetch (default 200)
"""
from __future__ import annotations

from typing import List
from urllib.parse import urlencode

from http_util import get_json
from models import Job
from normalize import strip_html

BASE = "https://remotive.com/api/remote-jobs"


def parse(company: dict, payload: dict) -> List[Job]:
    jobs: List[Job] = []
    for j in payload.get("jobs", []) or []:
        jobs.append(Job(
            company=(j.get("company_name") or "").strip() or "Unknown",
            ats_type="remotive",
            ats_job_id=str(j.get("id")),
            title=j.get("title", "") or "",
            location_raw=j.get("candidate_required_location", "") or "Remote",
            description=strip_html(j.get("description", "")),
            apply_url=j.get("url", "") or "",
            posted_at=j.get("publication_date"),
            is_startup=False,
        ))
    return jobs


def fetch(company: dict) -> List[Job]:
    params = {"limit": company.get("limit", 200)}
    if company.get("search"):
        params["search"] = company["search"]
    if company.get("category"):
        params["category"] = company["category"]
    url = f"{BASE}?{urlencode(params)}"
    return parse(company, get_json(url))
