"""ATS adapter registry. Each adapter exposes fetch(company) -> List[Job]."""
from __future__ import annotations

from typing import List

from models import Job
from adapters import (arbeitnow, ashby, greenhouse, himalayas, jobicy, lever,
                      remoteok, remotive, smartrecruiters, themuse, workable,
                      workable_search, workday)

# Single-company ATS boards: one slug == one employer.
_COMPANY_ATS = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "workday": workday.fetch,
    "workable": workable.fetch,
}

# Keyless aggregators: one source fans out to many employers.
_AGGREGATOR_ATS = {
    "remotive": remotive.fetch,
    "arbeitnow": arbeitnow.fetch,
    "jobicy": jobicy.fetch,
    "himalayas": himalayas.fetch,
    "remoteok": remoteok.fetch,
    "themuse": themuse.fetch,
    "workable_search": workable_search.fetch,
}

REGISTRY = {**_COMPANY_ATS, **_AGGREGATOR_ATS}
AGGREGATORS = set(_AGGREGATOR_ATS)
SUPPORTED = sorted(REGISTRY)


def fetch_company(company: dict) -> List[Job]:
    ats = (company.get("ats_type") or "").lower()
    fn = REGISTRY.get(ats)
    if fn is None:
        raise ValueError(f"Unsupported ats_type: {ats!r} (supported: {SUPPORTED})")
    return fn(company)
