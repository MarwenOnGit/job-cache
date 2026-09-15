"""ATS adapter registry. Each adapter exposes fetch(company) -> List[Job]."""
from __future__ import annotations

from typing import List

from models import Job
from adapters import greenhouse, lever, ashby, smartrecruiters, workday, workable

REGISTRY = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "workday": workday.fetch,
    "workable": workable.fetch,
}

SUPPORTED = sorted(REGISTRY)


def fetch_company(company: dict) -> List[Job]:
    ats = (company.get("ats_type") or "").lower()
    fn = REGISTRY.get(ats)
    if fn is None:
        raise ValueError(f"Unsupported ats_type: {ats!r} (supported: {SUPPORTED})")
    return fn(company)
