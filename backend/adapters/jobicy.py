"""Jobicy public remote-jobs API (keyless aggregator).

https://jobicy.com/api/v2/remote-jobs?count=50&geo=europe&industry=...&tag=...

Optional source params:
  count:    max postings (default 50, API max 50 per call)
  geo:      region filter, e.g. "europe", "emea" (recommended for this tool)
  industry: e.g. "dev", "data-science"
  tag:      free-text query
"""
from __future__ import annotations

from typing import List
from urllib.parse import urlencode

from http_util import get_json
from models import Job
from normalize import extract_apply_link, strip_html

BASE = "https://jobicy.com/api/v2/remote-jobs"


def parse(company: dict, payload: dict) -> List[Job]:
    jobs: List[Job] = []
    for j in payload.get("jobs", []) or []:
        desc = j.get("jobDescription") or j.get("jobExcerpt") or ""
        listing_url = j.get("url", "") or ""
        # Jobicy's "url" is its own listing page — prefer the employer's real
        # apply link if one is linked from inside the posting.
        apply_url = extract_apply_link(desc, exclude_domain="jobicy.com") or listing_url
        jobs.append(Job(
            company=(j.get("companyName") or "").strip() or "Unknown",
            ats_type="jobicy",
            ats_job_id=str(j.get("id")),
            title=j.get("jobTitle", "") or "",
            location_raw=j.get("jobGeo", "") or "Remote",
            description=strip_html(desc),
            apply_url=apply_url,
            posted_at=j.get("pubDate"),
            is_startup=False,
        ))
    return jobs


def fetch(company: dict) -> List[Job]:
    params = {"count": company.get("count", 50)}
    for key in ("geo", "industry", "tag"):
        if company.get(key):
            params[key] = company[key]
    url = f"{BASE}?{urlencode(params)}"
    return parse(company, get_json(url))
