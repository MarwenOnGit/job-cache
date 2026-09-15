"""Workable public jobs widget API.

https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true
"""
from __future__ import annotations

from typing import List

from http_util import get_json
from models import Job
from normalize import strip_html

BASE = "https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true"


def _location(j: dict) -> str:
    parts = [j.get("city"), j.get("state"), j.get("country")]
    text = ", ".join(p for p in parts if p)
    if j.get("telecommuting"):
        text = (text + " (Remote)").strip()
    return text


def parse(company: dict, payload: dict) -> List[Job]:
    jobs: List[Job] = []
    for j in payload.get("jobs", []) or []:
        jobs.append(Job(
            company=company["name"],
            ats_type="workable",
            ats_job_id=str(j.get("shortcode") or j.get("code")),
            title=j.get("title", "") or "",
            location_raw=_location(j),
            description=strip_html(j.get("description", "")),
            apply_url=j.get("url") or j.get("application_url") or j.get("shortlink") or "",
            posted_at=j.get("published_on") or j.get("created_at"),
            is_startup=bool(company.get("is_startup")),
        ))
    return jobs


def fetch(company: dict) -> List[Job]:
    url = BASE.format(slug=company["ats_slug"])
    return parse(company, get_json(url))
