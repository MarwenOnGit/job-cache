"""Greenhouse public boards API: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"""
from __future__ import annotations

from typing import List

from http_util import get_json
from models import Job
from normalize import strip_html

BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


def parse(company: dict, payload: dict) -> List[Job]:
    jobs: List[Job] = []
    for j in payload.get("jobs", []) or []:
        loc = (j.get("location") or {}).get("name", "") or ""
        jobs.append(Job(
            company=company["name"],
            ats_type="greenhouse",
            ats_job_id=str(j.get("id")),
            title=j.get("title", "") or "",
            location_raw=loc,
            description=strip_html(j.get("content", "")),
            apply_url=j.get("absolute_url", "") or "",
            posted_at=j.get("first_published") or j.get("updated_at"),
            is_startup=bool(company.get("is_startup")),
        ))
    return jobs


def fetch(company: dict) -> List[Job]:
    url = BASE.format(slug=company["ats_slug"])
    return parse(company, get_json(url))
