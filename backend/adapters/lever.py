"""Lever public postings API: https://api.lever.co/v0/postings/{slug}?mode=json"""
from __future__ import annotations

from typing import List

from http_util import get_json
from models import Job
from normalize import strip_html

BASE = "https://api.lever.co/v0/postings/{slug}?mode=json"


def parse(company: dict, payload: list) -> List[Job]:
    jobs: List[Job] = []
    for j in payload or []:
        cats = j.get("categories") or {}
        loc = cats.get("location", "") or ""
        desc = j.get("descriptionPlain") or strip_html(j.get("description", ""))
        jobs.append(Job(
            company=company["name"],
            ats_type="lever",
            ats_job_id=str(j.get("id")),
            title=j.get("text", "") or "",
            location_raw=loc,
            description=desc or "",
            apply_url=j.get("hostedUrl", "") or j.get("applyUrl", "") or "",
            posted_at=str(j["createdAt"]) if j.get("createdAt") else None,
            is_startup=bool(company.get("is_startup")),
        ))
    return jobs


def fetch(company: dict) -> List[Job]:
    url = BASE.format(slug=company["ats_slug"])
    return parse(company, get_json(url))
