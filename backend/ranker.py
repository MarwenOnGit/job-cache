"""Free deterministic ranker: scores a job against the owner's CV. No LLM, no network.

Score = 0.55 * skills_overlap + 0.30 * role_match + 0.15 * recency, clamped to [0, 1].
Claude Code does the *deep* tailoring later; this only gives the dashboard a good default sort.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from normalize import classify_role_family, title_matches_family
from seniority import is_internship

# Skills drawn from the CV (see cv/cv.md). Multi-word phrases matched as substrings.
# Tuned for an offensive-security / red-team profile.
CV_SKILLS = [
    # offensive security core
    "penetration testing", "red team", "offensive security", "vulnerability", "exploit",
    "active directory", "entra id", "azure ad", "privilege escalation", "lateral movement",
    "adversary emulation", "purple team", "bug bounty", "reverse engineering", "web application security",
    "whitebox", "white-box", "source code review", "ctf", "cve",
    # cloud / identity
    "azure", "aws", "rbac", "managed identities", "service principals", "adcs", "kubernetes",
    "cloud security", "iam", "devsecops",
    # tooling / tradecraft
    "mythic", "sliver", "cobalt strike", "c2", "evilginx", "bloodhound", "azurehound",
    "certipy", "impacket", "burp suite", "nmap", "wireshark", "metasploit", "chisel",
    "proxychains", "neo4j", "exegol", "sast", "dast", "siem", "sigma", "suricata", "snort",
    # programming / infra
    "python", "bash", "c++", "c#", ".net", "java", "javascript", "powershell",
    "docker", "terraform", "ansible", "github actions", "react", "next.js", "node.js", "flask",
]

# Number of matched skills that counts as a "full" overlap score.
_SKILLS_SATURATION = 8
# Postings older than this (days) get zero recency credit.
_RECENCY_WINDOW_DAYS = 60.0


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    v = value.strip()
    # Epoch millis or seconds.
    if v.isdigit():
        num = int(v)
        if num > 10_000_000_000:  # millis
            num //= 1000
        try:
            return datetime.fromtimestamp(num, tz=timezone.utc)
        except (ValueError, OSError):
            return None
    v = v.replace("Z", "+00:00")
    for parser in (datetime.fromisoformat,):
        try:
            dt = parser(v)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    # Fallback: leading YYYY-MM-DD.
    try:
        return datetime.strptime(v[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _recency(posted_at: Optional[str], now: Optional[datetime] = None) -> float:
    dt = _parse_date(posted_at)
    if dt is None:
        return 0.5  # unknown date → neutral
    now = now or datetime.now(timezone.utc)
    days = max(0.0, (now - dt).total_seconds() / 86400.0)
    return max(0.0, 1.0 - days / _RECENCY_WINDOW_DAYS)


def _skills_overlap(text: str, extra_skills: Optional[List[str]] = None) -> Tuple[float, List[str]]:
    hay = f" {text.lower()} "
    # The base CV skills plus any keywords/titles the user set in their search
    # preferences, so ranking follows what they actually want, not just the CV.
    vocab = list(CV_SKILLS)
    for s in (extra_skills or []):
        s = (s or "").strip().lower()
        if s and s not in vocab:
            vocab.append(s)
    matched = [s for s in vocab if s in hay]
    score = min(1.0, len(matched) / _SKILLS_SATURATION)
    return score, matched


def score_job(title: str, description: str, posted_at: Optional[str] = None,
              now: Optional[datetime] = None,
              extra_skills: Optional[List[str]] = None) -> Tuple[float, List[str]]:
    """Return (match_score in [0,1], human-readable reasons)."""
    combined = f"{title}\n{description}"
    skills_score, matched = _skills_overlap(combined, extra_skills)

    if title_matches_family(title):
        role_score = 1.0
    elif classify_role_family(title, description) is not None:
        role_score = 0.5
    else:
        role_score = 0.0

    rec = _recency(posted_at, now)
    total = 0.55 * skills_score + 0.30 * role_score + 0.15 * rec

    # PFE / end-of-studies internships are the primary target: give a real match
    # a boost so they sort to the top, ahead of otherwise-similar junior roles.
    intern = is_internship(title, description)
    if intern and role_score > 0:
        total += 0.12
    total = round(max(0.0, min(1.0, total)), 3)

    reasons: List[str] = []
    if intern:
        reasons.append("Internship / PFE role")
    if matched:
        top = ", ".join(matched[:6])
        reasons.append(f"Matches your skills: {top}")
    if role_score >= 1.0:
        reasons.append("Title is a direct role-family match")
    elif role_score > 0:
        reasons.append("Role-family match in description")
    if rec >= 0.7:
        reasons.append("Recently posted")
    if not reasons:
        reasons.append("Low relevance to your CV")
    return total, reasons
