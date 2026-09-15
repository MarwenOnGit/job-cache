"""Shared normalization helpers: HTML stripping, city + role-family classification."""
from __future__ import annotations

import html
import re
from typing import Optional

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\r\f\v]+")
_NL_RE = re.compile(r"\n{3,}")

# --- Target cities ----------------------------------------------------------
TARGET_CITIES = {"paris", "brussels", "geneva", "london", "remote-eu"}

_CITY_PATTERNS = [
    ("paris", ["paris", "ile-de-france", "île-de-france", "ile de france", "boulogne", "montrouge"]),
    ("brussels", ["brussels", "bruxelles", "brussel", "belgium", "belgique"]),
    ("geneva", ["geneva", "genève", "geneve", "zurich", "zürich", "lausanne", "switzerland", "suisse"]),
    ("london", ["london", "united kingdom", "england", ", uk", "(uk)", "uk)"]),
]

_REMOTE_HINTS = ["remote", "télétravail", "teletravail", "anywhere"]
_EU_HINTS = ["europe", "eu", "emea", "france", "eea", "cet", "cest"]

# --- Role families ----------------------------------------------------------
# Ordered by priority: first family whose keywords hit wins the label.
ROLE_FAMILIES = [
    ("ai_agentic", ["llm", "large language model", "agentic", "ai agent", "generative ai",
                     "gen ai", "genai", "rag", "prompt", "foundation model"]),
    ("ai_ml", ["machine learning", " ml ", "ml engineer", "mlops", "deep learning", "nlp",
               "computer vision", "data scientist", "research scientist", "ai engineer",
               "artificial intelligence", "recommendation", "ranking"]),
    ("data_eng", ["data engineer", "data engineering", "etl", "elt", "spark", "kafka",
                  "airflow", "data platform", "analytics engineer", "data pipeline",
                  "data infrastructure", "warehouse", "databricks"]),
    ("swe", ["software engineer", "software developer", "backend", "back-end", "back end",
             "frontend", "front-end", "front end", "full stack", "full-stack", "fullstack",
             "developer", "sde", "platform engineer", "web engineer", "python engineer"]),
]


def slugify(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "company"


def strip_html(text: Optional[str]) -> str:
    if not text:
        return ""
    # Unescape first: some ATSs (e.g. Greenhouse) return entity-encoded HTML ("&lt;p&gt;"),
    # so real tags only appear after unescaping. Then strip tags, then unescape any leftovers.
    text = html.unescape(text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _WS_RE.sub(" ", text)
    text = _NL_RE.sub("\n\n", text)
    return text.strip()


def classify_city(location_raw: Optional[str]) -> str:
    loc = (location_raw or "").lower()
    if not loc:
        return "other"
    for city, needles in _CITY_PATTERNS:
        if any(n in loc for n in needles):
            return city
    is_remote = any(h in loc for h in _REMOTE_HINTS)
    if is_remote and any(h in f" {loc} " for h in _EU_HINTS):
        return "remote-eu"
    if is_remote and loc.strip() in ("remote", "fully remote"):
        # Bare "remote" — assume EU-eligible; the sponsorship flag is the real filter.
        return "remote-eu"
    return "other"


def classify_role_family(title: str, description: str = "") -> Optional[str]:
    hay = f" {title.lower()} \n {description.lower()} "
    for family, needles in ROLE_FAMILIES:
        if any(n in hay for n in needles):
            return family
    return None


def title_matches_family(title: str) -> bool:
    """True if the *title alone* (strong signal) matches a target family."""
    return classify_role_family(title, "") is not None
