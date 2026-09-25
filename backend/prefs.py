"""Structured search preferences: the countries, role families, job titles and
keywords that actually drive what gets harvested and how it's ranked.

This is separate from `preferences.md` (which is the *voice* Claude writes in).
This module is the *search* side: where you want to work, what you want to do.

Storage: data/preferences.json. When that file doesn't exist yet, the API seeds a
view from the onboarding form (data/onboarding.json) so a new user sees their
onboarding choices pre-filled and editable — no need to re-run onboarding to change
a country or add a keyword. With no saved file, the harvester uses the owner profile's
defaults (profile/profile.yaml); any empty field means "no restriction".
"""
from __future__ import annotations

import json
import os
from typing import List

import profile_store
from normalize import (LOCATION_LABELS, ROLE_FAMILIES, TARGET_CITIES,
                       classify_city)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFS_JSON_PATH = os.path.join(ROOT, "data", "preferences.json")
ONBOARDING_PATH = os.path.join(ROOT, "data", "onboarding.json")

# Empty list means "no restriction" for that dimension (the broadest search).
DEFAULTS = {
    "locations": [],       # canonical location tokens (see normalize.LOCATION_LABELS)
    "role_families": [],   # subset of normalize.ROLE_FAMILIES keys
    "titles": [],          # free-text job titles to boost / target
    "keywords": [],        # free-text skills/keywords to boost in ranking
    "experience": "",      # e.g. "1-3"
    "language": "",        # cover-letter default language
}

ROLE_FAMILY_LABELS = [
    ("offensive_security", "Offensive Security (pentest, red team, vuln research)"),
    ("appsec", "Application / Product Security"),
    ("blue_team", "Blue Team / SOC / DFIR"),
    ("cloud_grc", "Cloud Security / DevSecOps / GRC"),
    ("security_other", "Security Engineering (general)"),
    ("ai_ml", "AI / ML (adjacent, optional)"),
    ("swe", "Software Engineering (adjacent, optional)"),
]
_ROLE_FAMILY_KEYS = {k for k, _ in ROLE_FAMILY_LABELS}


def _read_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _clean_list(value) -> List[str]:
    if not isinstance(value, list):
        return []
    out, seen = [], set()
    for item in value:
        s = str(item).strip()
        key = s.lower()
        if s and key not in seen:
            seen.add(key)
            out.append(s)
    return out


def _normalize(raw: dict) -> dict:
    prefs = dict(DEFAULTS)
    prefs["locations"] = [t for t in _clean_list(raw.get("locations")) if t in TARGET_CITIES]
    prefs["role_families"] = [t for t in _clean_list(raw.get("role_families")) if t in _ROLE_FAMILY_KEYS]
    prefs["titles"] = _clean_list(raw.get("titles"))
    prefs["keywords"] = _clean_list(raw.get("keywords"))
    prefs["experience"] = str(raw.get("experience") or "").strip()
    prefs["language"] = str(raw.get("language") or "").strip()
    return prefs


def profile_defaults() -> dict:
    """Search preferences implied by the committed owner profile (profile/profile.yaml),
    or the all-inclusive DEFAULTS when there is no profile."""
    return _normalize(profile_store.default_search_prefs())


def load_structured() -> dict:
    """The user's saved search preferences; else the owner profile's defaults (so a
    fresh clone searches for the right things without asking)."""
    if os.path.exists(PREFS_JSON_PATH):
        return _normalize(_read_json(PREFS_JSON_PATH))
    return profile_defaults()


def seed_from_onboarding() -> dict:
    """Best-effort structured prefs derived from the onboarding form, for first-time
    display. Location display strings ('Paris', 'Remote (EU)', custom) map to canonical
    tokens; role chips split into known families vs. free-text titles."""
    ob = _read_json(ONBOARDING_PATH)
    locations, seen = [], set()
    for city in _clean_list(ob.get("cities")):
        tok = classify_city(city)
        if tok != "other" and tok not in seen:
            seen.add(tok)
            locations.append(tok)
    role_families, titles = [], []
    for role in _clean_list(ob.get("roles")):
        if role in _ROLE_FAMILY_KEYS:
            role_families.append(role)
        else:
            titles.append(role)
    return _normalize({
        "locations": locations,
        "role_families": role_families,
        "titles": titles,
        "keywords": [],
        "experience": ob.get("experience") or "",
        "language": ob.get("language") or "",
    })


def load_or_seed() -> dict:
    """Saved prefs if present; otherwise a view seeded from onboarding (not persisted)."""
    if os.path.exists(PREFS_JSON_PATH):
        return load_structured()
    if os.path.exists(ONBOARDING_PATH):
        return seed_from_onboarding()
    return profile_defaults()


def save_structured(raw: dict) -> dict:
    prefs = _normalize(raw)
    os.makedirs(os.path.dirname(PREFS_JSON_PATH), exist_ok=True)
    with open(PREFS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2)
    return prefs


# --- what the harvester / ranker actually consume ---------------------------
def target_locations(prefs: dict) -> set:
    """The set of canonical location buckets to keep. Empty pref = every bucket."""
    picked = set(prefs.get("locations") or [])
    return picked or set(TARGET_CITIES)


def target_role_families(prefs: dict) -> set:
    """The role families to keep. Empty pref = all four families."""
    picked = set(prefs.get("role_families") or [])
    return picked or _ROLE_FAMILY_KEYS


def extra_keywords(prefs: dict) -> List[str]:
    """Extra skill/title terms to fold into the ranker's skills overlap."""
    terms = []
    for term in list(prefs.get("keywords") or []) + list(prefs.get("titles") or []):
        s = str(term).strip().lower()
        if s and s not in terms:
            terms.append(s)
    return terms


def catalog() -> dict:
    """Option lists for the dashboard preferences editor."""
    return {
        "locations": [[tok, label] for tok, label in LOCATION_LABELS],
        "role_families": [[tok, label] for tok, label in ROLE_FAMILY_LABELS],
    }
