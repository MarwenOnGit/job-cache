"""Core data model for a normalized job posting."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional

# Columns in the SQLite `jobs` table, in order.
JOB_COLUMNS = [
    "id", "company", "ats_type", "ats_job_id", "title", "location_raw", "city",
    "description", "apply_url", "role_family", "is_startup", "sponsorship",
    "seniority", "req_years", "match_score", "match_reasons", "status",
    "first_seen", "last_seen", "posted_at",
]


@dataclass
class Job:
    company: str
    ats_type: str
    ats_job_id: str
    title: str
    location_raw: str = ""
    description: str = ""
    apply_url: str = ""
    posted_at: Optional[str] = None
    is_startup: bool = False

    # Derived / enrichment fields (filled by normalize/rank/flag steps).
    city: str = "other"
    role_family: Optional[str] = None
    sponsorship: str = "silent"
    seniority: str = "mid"
    req_years: Optional[int] = None
    match_score: float = 0.0
    match_reasons: List[str] = field(default_factory=list)
    status: str = "interested"
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None

    @property
    def id(self) -> str:
        raw = f"{self.ats_type}:{self.company}:{self.ats_job_id}".lower()
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def to_row(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        d["is_startup"] = 1 if self.is_startup else 0
        d["match_reasons"] = json.dumps(self.match_reasons, ensure_ascii=False)
        return {k: d.get(k) for k in JOB_COLUMNS}

    @staticmethod
    def row_to_dict(row) -> dict:
        d = dict(row)
        d["is_startup"] = bool(d.get("is_startup"))
        d["starred"] = bool(d.get("starred"))
        d["notes"] = d.get("notes") or ""
        try:
            d["match_reasons"] = json.loads(d.get("match_reasons") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["match_reasons"] = []
        return d
