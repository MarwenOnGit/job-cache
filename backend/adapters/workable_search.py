"""Workable's public cross-employer job search (keyless).

https://jobs.workable.com/api/v1/jobs?query=...&location=...&pageToken=...

Unlike the single-company `workable` adapter, this searches every employer hosted on
Workable, which covers a lot of European security consultancies and scale-ups that
post internships. Optional source params:
  query:    free-text search (`query: auto` expands to one search per profile term)
  location: free-text location (e.g. "France"); omitted = everywhere
  pages:    result pages to walk (default 2)
"""
from __future__ import annotations

from typing import List
from urllib.parse import urlencode

from http_util import get_json
from models import Job
from normalize import strip_html

BASE = "https://jobs.workable.com/api/v1/jobs"


def _location(j: dict) -> str:
    parts: List[str] = []
    locs = j.get("locations")
    if isinstance(locs, list) and locs:
        for loc in locs:
            if isinstance(loc, str):
                parts.append(loc)
            elif isinstance(loc, dict):
                parts.append(", ".join(str(loc[k]) for k in ("city", "subregion", "countryName", "country")
                                       if loc.get(k)))
    loc = j.get("location")
    if not parts and isinstance(loc, dict):
        parts.append(", ".join(str(loc[k]) for k in ("city", "subregion", "countryName", "country")
                               if loc.get(k)))
    elif not parts and isinstance(loc, str):
        parts.append(loc)
    text = "; ".join(p for p in parts if p)
    workplace = str(j.get("workplace") or "").lower()
    if workplace == "remote" or j.get("remote") is True:
        text = f"{text} (Remote)".strip() if text else "Remote"
    return text


def parse(company: dict, payload: dict) -> List[Job]:
    jobs: List[Job] = []
    for j in (payload or {}).get("jobs", []) or []:
        if not isinstance(j, dict):
            continue
        co = j.get("company")
        name = (co.get("title") or co.get("name")) if isinstance(co, dict) else co
        desc = " ".join(str(j.get(k) or "") for k in ("description", "requirementsSection", "benefitsSection"))
        jobs.append(Job(
            company=(str(name or "").strip() or "Unknown"),
            ats_type="workable_search",
            ats_job_id=str(j.get("id") or j.get("shortcode") or j.get("url")),
            title=str(j.get("title") or ""),
            location_raw=_location(j),
            description=strip_html(desc),
            apply_url=str(j.get("url") or j.get("applyUrl") or ""),
            posted_at=j.get("created") or j.get("updated"),
            is_startup=False,
        ))
    return jobs


def fetch(company: dict) -> List[Job]:
    pages = int(company.get("pages", 2))
    params = {"query": company.get("query") or "security"}
    if company.get("location"):
        params["location"] = company["location"]
    jobs: List[Job] = []
    token = None
    for _ in range(pages):
        q = dict(params, **({"pageToken": token} if token else {}))
        payload = get_json(f"{BASE}?{urlencode(q)}")
        jobs.extend(parse(company, payload))
        token = (payload or {}).get("nextPageToken")
        if not token:
            break
    return jobs
