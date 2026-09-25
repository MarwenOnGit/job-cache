"""Himalayas public jobs API (keyless remote-jobs aggregator).

https://himalayas.app/jobs/api?limit=50&offset=0          (newest postings)
https://himalayas.app/jobs/api/search?q=...&page=N        (keyword search)

Optional source params:
  q:     keyword search (e.g. "penetration testing"); uses the search endpoint.
         `q: auto` in companies.yaml expands to one search per profile search term.
  limit: postings per call (default 50, listing endpoint only)
  pages: how many pages to walk (default 4)
"""
from __future__ import annotations

from typing import List
from urllib.parse import urlencode

from http_util import get_json
from models import Job
from normalize import strip_html

BASE = "https://himalayas.app/jobs/api"
SEARCH = "https://himalayas.app/jobs/api/search"


def _location(j: dict) -> str:
    restrictions = j.get("locationRestrictions") or []
    if isinstance(restrictions, list) and restrictions:
        return ", ".join(str(r) for r in restrictions) + " (Remote)"
    return "Remote"


def parse(company: dict, payload: dict) -> List[Job]:
    jobs: List[Job] = []
    for j in payload.get("jobs", []) or []:
        pub = j.get("pubDate")
        jobs.append(Job(
            company=(j.get("companyName") or "").strip() or "Unknown",
            ats_type="himalayas",
            ats_job_id=str(j.get("guid") or j.get("applicationLink") or j.get("title")),
            title=j.get("title", "") or "",
            location_raw=_location(j),
            description=strip_html(j.get("description") or j.get("excerpt") or ""),
            apply_url=j.get("applicationLink") or j.get("guid") or "",
            posted_at=str(pub) if pub is not None else None,
            is_startup=False,
        ))
    return jobs


def _url(company: dict, page: int) -> str:
    if company.get("q"):
        return f"{SEARCH}?{urlencode({'q': company['q'], 'page': page + 1})}"
    limit = int(company.get("limit", 50))
    return f"{BASE}?limit={limit}&offset={page * limit}"


def fetch(company: dict) -> List[Job]:
    pages = int(company.get("pages", 4))
    jobs: List[Job] = []
    for page in range(pages):
        payload = get_json(_url(company, page))
        batch = parse(company, payload)
        if not batch:
            break
        jobs.extend(batch)
    return jobs
