"""RemoteOK public API (keyless remote-jobs aggregator).

https://remoteok.com/api

Optional source params:
  tag: a RemoteOK tag (e.g. "security"); multi-word values are hyphenated.

The response is a JSON array whose first element is a legal/metadata notice, not a
job; it's skipped. RemoteOK prefers a browser-like User-Agent, so one is sent.
"""
from __future__ import annotations

from typing import List
from urllib.parse import urlencode

from http_util import get_json
from models import Job
from normalize import strip_html

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
        jobs.append(Job(
            company=(j.get("company") or "").strip() or "Unknown",
            ats_type="remoteok",
            ats_job_id=str(j.get("id")),
            title=j.get("position") or j.get("title") or "",
            location_raw=j.get("location") or "Remote",
            description=strip_html(desc),
            apply_url=j.get("url") or j.get("apply_url") or "",
            posted_at=j.get("date"),
            is_startup=False,
        ))
    return jobs


def fetch(company: dict) -> List[Job]:
    url = BASE
    if company.get("tag"):
        url = f"{BASE}?{urlencode({'tag': '-'.join(str(company['tag']).lower().split())})}"
    return parse(company, get_json(url, headers=_HEADERS))
