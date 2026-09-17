"""Himalayas public jobs API (keyless remote-jobs aggregator).

https://himalayas.app/jobs/api?limit=50&offset=0

Optional source params:
  limit: postings per call (default 50)
  pages: how many pages of `limit` to walk (default 4)
"""
from __future__ import annotations

from typing import List

from http_util import get_json
from models import Job
from normalize import strip_html

BASE = "https://himalayas.app/jobs/api"


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


def fetch(company: dict) -> List[Job]:
    limit = int(company.get("limit", 50))
    pages = int(company.get("pages", 4))
    jobs: List[Job] = []
    for page in range(pages):
        payload = get_json(f"{BASE}?limit={limit}&offset={page * limit}")
        batch = parse(company, payload)
        if not batch:
            break
        jobs.extend(batch)
    return jobs
