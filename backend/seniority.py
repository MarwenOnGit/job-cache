"""Free heuristic seniority + required-years detection, to match Sami's ~3 years of experience.

Sami: ~1 year full-time + engineering degree + internships (~3 yrs total). Target: roles up to
~5 years required, NOT senior/staff/principal. These are hints for filtering, not hard truth.
"""
from __future__ import annotations

import re
from typing import Optional

_SENIOR = [
    "senior", "sr.", "sr ", "staff", "principal", "lead ", " lead", "head of", "head,",
    "director", "vp ", "vice president", "distinguished", "expert", "architect",
    "manager", "fellow",
]
_JUNIOR = [
    "junior", "jr.", "jr ", "graduate", "grad ", "entry", "entry-level", "intern",
    "internship", "apprentice", "apprenti", "alternance", "working student", "trainee",
    "stage", "stagiaire", "early career", "new grad",
]

# "5+ years", "5 years", "3-5 years", "at least 4 years", "minimum 3 ans", "5 ans d'expérience"
_YEARS_RE = re.compile(
    r"(\d{1,2})\s*(?:\+|-\s*\d{1,2})?\s*(?:years|year|yrs|ans|année|annees|années)",
    re.IGNORECASE,
)


def classify_seniority(title: str, description: str = "") -> str:
    t = f" {(title or '').lower()} "
    if any(k in t for k in _JUNIOR):
        return "junior"
    if any(k in t for k in _SENIOR):
        return "senior_plus"
    # Title is neutral: a description demanding many years still implies senior.
    yrs = extract_required_years(description)
    if yrs is not None and yrs >= 6:
        return "senior_plus"
    return "mid"


def extract_required_years(description: str) -> Optional[int]:
    """Smallest 'N years' figure mentioned in an experience context (the entry bar)."""
    if not description:
        return None
    nums = []
    for m in _YEARS_RE.finditer(description):
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        if 0 < n <= 20:  # ignore noise like "2024 years"
            nums.append(n)
    return min(nums) if nums else None
