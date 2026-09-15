"""Ashby public job-board API: https://api.ashbyhq.com/posting-api/job-board/{slug}"""
from __future__ import annotations

from typing import List

from http_util import get_json
from models import Job
from normalize import strip_html

BASE = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"


def parse(company: dict, payload: dict) -> List[Job]:
    jobs: List[Job] = []
    for j in payload.get("jobs", []) or []:
        loc = j.get("location") or ""
        if not loc and j.get("isRemote"):
            loc = "Remote"
        desc = j.get("descriptionPlain") or strip_html(j.get("descriptionHtml", ""))
        jobs.append(Job(
            company=company["name"],
            ats_type="ashby",
            ats_job_id=str(j.get("id")),
            title=j.get("title", "") or "",
            location_raw=loc,
            description=desc or "",
            apply_url=j.get("jobUrl") or j.get("applyUrl") or "",
            posted_at=j.get("publishedAt") or j.get("publishedDate"),
            is_startup=bool(company.get("is_startup")),
        ))
    return jobs


def fetch(company: dict) -> List[Job]:
    url = BASE.format(slug=company["ats_slug"])
    return parse(company, get_json(url))
