"""The owner's saved profile: the app's memory between runs.

Three layers, most specific wins:
  1. Local, gitignored files: cv/cv.md, preferences.md, data/preferences.json.
  2. The committed owner profile: profile/cv.md, profile/preferences.md,
     profile/profile.yaml (no contact details).
  3. The shipped templates (cv/cv.example.md, preferences.example.md).

So a fresh clone on a new machine already knows who you are and what to search for,
and nothing is asked on startup. Everything the search and ranking use comes from
here: skills are read out of the CV itself, and the live search queries come from
profile.yaml plus any titles/keywords saved in the dashboard.
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_DIR = os.path.join(ROOT, "profile")
PROFILE_YAML = os.path.join(PROFILE_DIR, "profile.yaml")
PROFILE_CV = os.path.join(PROFILE_DIR, "cv.md")
PROFILE_PREFS = os.path.join(PROFILE_DIR, "preferences.md")

_cache: Dict[str, Tuple[float, object]] = {}


def _mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return -1.0


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def load(path: Optional[str] = None) -> dict:
    """profile.yaml as a dict ({} when missing or unreadable). Cached by mtime."""
    path = path or PROFILE_YAML
    key = f"yaml:{path}"
    mt = _mtime(path)
    hit = _cache.get(key)
    if hit and hit[0] == mt:
        return hit[1]  # type: ignore[return-value]
    data: dict = {}
    if mt >= 0:
        try:
            with open(path, encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
            data = loaded if isinstance(loaded, dict) else {}
        except (OSError, yaml.YAMLError):
            data = {}
    _cache[key] = (mt, data)
    return data


def _section(name: str, profile: Optional[dict] = None) -> dict:
    sec = (profile if profile is not None else load()).get(name)
    return sec if isinstance(sec, dict) else {}


def _str_list(value) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for v in value:
        s = str(v).strip()
        if s and s.lower() not in (x.lower() for x in out):
            out.append(s)
    return out


# --- CV + voice with fallbacks -----------------------------------------------
def cv_markdown(local_path: str) -> str:
    """The CV to use: local cv/cv.md if present, else the committed profile/cv.md."""
    local = _read_text(local_path)
    return local if local.strip() else _read_text(PROFILE_CV)


def preferences_markdown(local_path: str, example_path: str) -> str:
    """Voice rules: local preferences.md, else profile/preferences.md, else the example."""
    for p in (local_path, PROFILE_PREFS, example_path):
        text = _read_text(p)
        if text.strip():
            return text
    return ""


def has_saved_profile() -> bool:
    """True when the committed owner profile exists, so onboarding can be skipped."""
    return bool(_read_text(PROFILE_CV).strip()) and bool(load())


def owner_name() -> str:
    return str(load().get("name") or "").strip()


# --- skills, read out of the CV itself ----------------------------------------
# Skill-looking phrases worth matching even when the CV words them differently.
_BASE_VOCAB = [
    "penetration testing", "pentest", "red team", "offensive security", "vulnerability",
    "exploit", "active directory", "entra id", "azure ad", "privilege escalation",
    "lateral movement", "adversary emulation", "purple team", "bug bounty",
    "reverse engineering", "web application security", "source code review", "ctf", "cve",
    "cloud security", "iam", "devsecops", "c2", "osint", "threat modeling",
]
# CV skill items that are too generic or too short to match safely as substrings.
_SKIP = {"c", "git", "enumeration", "arabic", "french", "english", "native", "fluent"}
_SKILLS_HEADING = re.compile(r"^#{1,6}\s*(skills|compétences|competences)\b", re.I | re.M)
_ANY_HEADING = re.compile(r"^#{1,6}\s", re.M)
_LABEL = re.compile(r"\*\*[^*]+:\*\*|^[-*]\s*[^:]{1,40}:", re.M)


def _skills_section(cv: str) -> str:
    m = _SKILLS_HEADING.search(cv or "")
    if not m:
        return ""
    rest = cv[m.end():]
    nxt = _ANY_HEADING.search(rest)
    return rest[: nxt.start()] if nxt else rest


def extract_skills(cv: str) -> List[str]:
    """Skill terms listed in the CV's Skills section ("**Tools:** A, B, C" lines),
    lowercased and de-duplicated. Language lines are ignored."""
    out: List[str] = []
    for line in _skills_section(cv).splitlines():
        if re.search(r"languages?\s*:|langues?\s*:", line, re.I):
            continue
        body = _LABEL.sub("", line).strip(" -*\t")
        for part in re.split(r"[,;·|]", body):
            term = re.sub(r"\(.*?\)", "", part).strip(" .*").lower()
            term = term.replace("git/github", "github")
            if len(term) < 2 or term in _SKIP or len(term) > 40:
                continue
            if term not in out:
                out.append(term)
    return out


def skills(cv: str) -> List[str]:
    """Everything the ranker should reward: the CV's own skills + a small base
    vocabulary of security phrases."""
    out = list(_BASE_VOCAB)
    for s in extract_skills(cv):
        if s not in out:
            out.append(s)
    return out


# --- live search queries -------------------------------------------------------
def job_queries(prefs: Optional[dict] = None, limit: int = 10) -> List[str]:
    """Search terms sent to every search-capable job board on each harvest:
    profile.yaml jobs.search_terms, then titles saved in the dashboard."""
    jobs = _section("jobs")
    terms = _str_list(jobs.get("search_terms"))
    for t in _str_list((prefs or {}).get("titles")):
        if t.lower() not in (x.lower() for x in terms):
            terms.append(t)
    if not terms:
        terms = ["security engineer", "penetration testing", "cybersecurity internship"]
    return terms[:limit]


def local_job_queries() -> List[str]:
    """Non-English search terms (French / German postings)."""
    return _str_list(_section("jobs").get("local_terms"))


def study_queries(limit: int = 10) -> List[str]:
    terms = _str_list(_section("study").get("search_terms"))
    return (terms or ["cybersecurity master scholarship", "computer science masters scholarship"])[:limit]


def study_fields() -> List[str]:
    fields = [f.lower() for f in _str_list(_section("study").get("fields"))]
    return fields or ["cybersecurity", "computer science", "engineering"]


def study_countries() -> List[str]:
    return [c.lower() for c in _str_list(_section("study").get("countries"))]


def nationality() -> str:
    return str(load().get("nationality") or "").strip()


def default_search_prefs() -> dict:
    """Search preferences implied by profile.yaml, used when the dashboard has
    never saved any (data/preferences.json missing)."""
    jobs = _section("jobs")
    return {
        "locations": _str_list(jobs.get("locations")),
        "role_families": _str_list(jobs.get("role_families")),
        "titles": _str_list(jobs.get("titles")),
        "keywords": [],
        "experience": str(jobs.get("experience") or ""),
        "language": str(jobs.get("cover_letter_language") or ""),
    }
