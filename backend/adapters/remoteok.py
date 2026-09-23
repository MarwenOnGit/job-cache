"""RemoteOK public API (keyless remote-jobs aggregator).

https://remoteok.com/api

The response is a JSON array whose first element is a legal/metadata notice, not a
job; it's skipped. RemoteOK prefers a browser-like User-Agent, so one is sent.
"""
from __future__ import annotations

from typing import List

from http_util import get_json
from models import Job
from normalize import extract_apply_link, strip_html

BASE = "https://remoteok.com/api"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}


def parse(company: dict, payload: list) -> List[Job]:
    jobs: List[Job] = []
    for j in payload or []:
        if not isinstance(j, dict) or not j.get("id"):
            continue  # first element is the legal notice / any non-job rows
        desc = j.get("description") or ""
        listing_url = j.get("url") or j.get("apply_url") or ""
        # RemoteOK rarely supplies a real "apply_url"; its "url" is its own
        # listing page — prefer a real apply link linked from the posting.
        apply_url = extract_apply_link(desc, exclude_domain="remoteok.com") or listing_url
        jobs.append(Job(
            company=(j.get("company") or "").strip() or "Unknown",
            ats_type="remoteok",
            ats_job_id=str(j.get("id")),
            title=j.get("position") or j.get("title") or "",
            location_raw=j.get("location") or "Remote",
            description=strip_html(desc),
            apply_url=apply_url,
            posted_at=j.get("date"),
            is_startup=False,
        ))
    return jobs


def fetch(company: dict) -> List[Job]:
    return parse(company, get_json(BASE, headers=_HEADERS))
