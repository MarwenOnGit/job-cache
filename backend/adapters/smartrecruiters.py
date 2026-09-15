"""SmartRecruiters public postings API.

List: https://api.smartrecruiters.com/v1/companies/{slug}/postings
Detail (for description): https://api.smartrecruiters.com/v1/companies/{slug}/postings/{id}
"""
from __future__ import annotations

from typing import List

from http_util import get_json
from models import Job
from normalize import strip_html

LIST = "https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100"
DETAIL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings/{id}"
APPLY = "https://jobs.smartrecruiters.com/{slug}/{id}"


def _location(loc: dict) -> str:
    parts = [loc.get("city"), loc.get("region"), loc.get("country")]
    text = ", ".join(p for p in parts if p)
    if loc.get("remote"):
        text = (text + " (Remote)").strip()
    return text


def _description(slug: str, job_id: str) -> str:
    try:
        detail = get_json(DETAIL.format(slug=slug, id=job_id))
    except Exception:
        return ""
    sections = ((detail.get("jobAd") or {}).get("sections") or {})
    chunks = []
    for key in ("jobDescription", "qualifications", "additionalInformation"):
        text = (sections.get(key) or {}).get("text")
        if text:
            chunks.append(strip_html(text))
    return "\n\n".join(chunks)


def parse(company: dict, payload: dict, with_detail: bool = True) -> List[Job]:
    slug = company["ats_slug"]
    jobs: List[Job] = []
    for j in payload.get("content", []) or []:
        job_id = str(j.get("id"))
        desc = _description(slug, job_id) if with_detail else ""
        jobs.append(Job(
            company=company["name"],
            ats_type="smartrecruiters",
            ats_job_id=job_id,
            title=j.get("name", "") or "",
            location_raw=_location(j.get("location") or {}),
            description=desc,
            apply_url=APPLY.format(slug=slug, id=job_id),
            posted_at=j.get("releasedDate"),
            is_startup=bool(company.get("is_startup")),
        ))
    return jobs


def fetch(company: dict) -> List[Job]:
    url = LIST.format(slug=company["ats_slug"])
    return parse(company, get_json(url))
