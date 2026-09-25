"""Shared normalization helpers: HTML stripping, city + role-family classification."""
from __future__ import annotations

import html
import re
from typing import Optional
from urllib.parse import urlparse

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\r\f\v]+")
_NL_RE = re.compile(r"\n{3,}")
_HREF_RE = re.compile(r'<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
_SOCIAL_DOMAINS = {"linkedin.com", "twitter.com", "x.com", "facebook.com", "instagram.com", "youtube.com"}

# --- Target locations -------------------------------------------------------
# Canonical location buckets. Ordered: specific cities first, then country-level
# catch-alls, so "Paris" wins over the generic "france" bucket. Every token here
# is a location the harvester can keep; the user's preferences (prefs.py) pick a
# subset, and an empty preference means "all of these".
_CITY_PATTERNS = [
    # --- specific cities ---
    ("paris", ["paris", "ile-de-france", "île-de-france", "ile de france", "boulogne", "montrouge"]),
    ("london", ["london"]),
    ("brussels", ["brussels", "bruxelles", "brussel"]),
    ("geneva", ["geneva", "genève", "geneve", "zurich", "zürich", "lausanne", "basel", "bern", "zug"]),
    ("amsterdam", ["amsterdam"]),
    ("berlin", ["berlin"]),
    ("munich", ["munich", "münchen", "muenchen"]),
    ("dublin", ["dublin"]),
    ("madrid", ["madrid"]),
    ("barcelona", ["barcelona", "barcelone"]),
    ("lisbon", ["lisbon", "lisboa", "lisbonne"]),
    ("milan", ["milan", "milano"]),
    ("stockholm", ["stockholm"]),
    ("copenhagen", ["copenhagen", "københavn", "kobenhavn"]),
    # --- country-level catch-alls (only reached if no specific city matched) ---
    ("france", ["france", "lyon", "toulouse", "nantes", "bordeaux", "lille", "marseille",
                "nice", "sophia antipolis", "rennes", "grenoble", "montpellier", "strasbourg"]),
    ("uk", ["united kingdom", "england", "scotland", "wales", ", uk", "(uk)", "uk)"]),
    ("belgium", ["belgium", "belgique", "belgië", "antwerp", "antwerpen", "ghent", "gent", "leuven"]),
    ("switzerland", ["switzerland", "suisse", "schweiz"]),
    ("netherlands", ["netherlands", "nederland", "holland", "rotterdam", "utrecht", "eindhoven", "the hague"]),
    ("germany", ["germany", "deutschland", "hamburg", "frankfurt", "cologne", "köln", "koeln",
                 "stuttgart", "düsseldorf", "dusseldorf", "leipzig"]),
    ("spain", ["spain", "españa", "espana", "valencia", "seville", "sevilla", "málaga", "malaga", "bilbao"]),
    ("italy", ["italy", "italia", "rome", "roma", "turin", "torino", "bologna"]),
    ("portugal", ["portugal", "porto"]),
    ("ireland", ["ireland", "irlande"]),
    ("sweden", ["sweden", "sverige", "gothenburg", "göteborg", "malmö", "malmo"]),
    ("denmark", ["denmark", "danmark"]),
    ("poland", ["poland", "polska", "warsaw", "warszawa", "kraków", "krakow", "wrocław", "wroclaw"]),
    ("eu-other", ["vienna", "austria", "wien", "helsinki", "finland", "oslo", "norway", "prague",
                  "praha", "czech", "budapest", "hungary", "athens", "greece", "luxembourg",
                  "tallinn", "estonia", "vilnius", "lithuania", "bucharest", "romania",
                  "sofia", "bulgaria"]),
    # --- North America (kept: the user is open to roles abroad, not EU-only) ---
    ("usa", ["united states", " usa", "(usa", "u.s.a", "u.s.", ", us", "(us)", "us-based",
             "us based", "new york", "san francisco", "seattle", "austin", "boston", "washington",
             "chicago", "los angeles", "denver", "atlanta", "remote us", "remote - us",
             "california", "texas", "virginia", "maryland", "florida", "north america"]),
    ("canada", ["canada", "toronto", "vancouver", "montreal", "montréal", "ottawa", "canadian"]),
    ("americas-other", ["brazil", "brasil", "mexico", "méxico", "argentina", "latam",
                        "latin america", "colombia", "chile", "são paulo", "sao paulo"]),
]

# Human labels + a stable display order for every canonical bucket. Single source
# of truth reused by the harvester filter, the API catalog, and the dashboard.
LOCATION_LABELS = [
    ("paris", "Paris"),
    ("london", "London"),
    ("brussels", "Brussels"),
    ("geneva", "Switzerland (Geneva / Zürich)"),
    ("amsterdam", "Amsterdam"),
    ("berlin", "Berlin"),
    ("munich", "Munich"),
    ("dublin", "Dublin"),
    ("madrid", "Madrid"),
    ("barcelona", "Barcelona"),
    ("lisbon", "Lisbon"),
    ("milan", "Milan"),
    ("stockholm", "Stockholm"),
    ("copenhagen", "Copenhagen"),
    ("france", "France (other cities)"),
    ("uk", "UK (other cities)"),
    ("belgium", "Belgium (other)"),
    ("switzerland", "Switzerland (other)"),
    ("netherlands", "Netherlands"),
    ("germany", "Germany (other)"),
    ("spain", "Spain (other)"),
    ("italy", "Italy (other)"),
    ("portugal", "Portugal (other)"),
    ("ireland", "Ireland (other)"),
    ("sweden", "Sweden"),
    ("denmark", "Denmark"),
    ("poland", "Poland"),
    ("eu-other", "Rest of Europe"),
    ("usa", "United States"),
    ("canada", "Canada"),
    ("americas-other", "Latin America (other)"),
    ("remote-eu", "Remote (EU eligible)"),
    ("remote-global", "Remote (Worldwide)"),
]

# The full set of locations the harvester can keep (used as the "all" default).
TARGET_CITIES = {tok for tok, _ in LOCATION_LABELS}

_REMOTE_HINTS = ["remote", "télétravail", "teletravail", "anywhere", "worldwide",
                 "work from home", "distributed", "wfh"]
_EU_HINTS = ["europe", " eu ", "eu)", "(eu", "emea", "france", "eea", "cet", "cest",
             "united kingdom", "germany", "spain", "ireland", "netherlands", "belgium"]
_GLOBAL_HINTS = ["anywhere", "worldwide", "global", "world wide", "work from anywhere"]
# Region-level EU eligibility stated without a city or the word "remote"
# (aggregators often list just "Europe", "EMEA", "EU", "United Kingdom").
_EU_REGION = ["europe", "emea", "eea", "european union", " eu ", "(eu", "eu)",
              "united kingdom", " uk "]
# Remote roles that explicitly restrict to a non-EU region: dropped as "other".
_NON_EU_HINTS = ["united states", " usa", "(usa", "u.s.", ", us", "(us)", "us only",
                 "us-based", "us based", "canada", "brazil", "latam", "apac", "india",
                 "australia", "singapore", "philippines", "nigeria", "mexico", "argentina",
                 "united arab", "uae", "americas only", "north america"]

# --- Role families ----------------------------------------------------------
# Ordered by priority: first family whose keywords hit wins the label. Offensive
# security is first so a "Security Engineer, Red Team" reads as offensive_security,
# not swe. Tuned for an offensive-security / red-team profile (see cv/cv.md).
ROLE_FAMILIES = [
    ("offensive_security", [
        "penetration test", "penetration tester", "pentest", "pen test", "pen tester",
        "red team", "red-team", "red teamer", "offensive security", "offensive security engineer",
        "ethical hacker", "ethical hacking", "vulnerability research", "vulnerability researcher",
        "exploit development", "exploit developer", "adversary emulation", "adversary simulation",
        "purple team", "purple-team", "security researcher", "reverse engineer", "reverse engineering",
        "bug bounty", "offensive engineer", "attack simulation", "breach and attack",
        "test d'intrusion", "testeur d'intrusion", "pentesteur", "red teaming",
    ]),
    ("appsec", [
        "application security", "appsec", "product security", "prodsec", "secure code review",
        "software security engineer", "security code review", "sast", "dast", "sdlc security",
        "security champion", "appsec engineer", "web application security", "api security",
    ]),
    ("blue_team", [
        "soc analyst", "security operations", "blue team", "blue-team", "threat hunting",
        "threat hunter", "incident response", "incident responder", "dfir", "digital forensics",
        "detection engineer", "detection engineering", "threat intelligence", "threat intel",
        "malware analyst", "security analyst", "csirt", "cert analyst", "siem",
        "analyste soc", "réponse à incident", "reponse a incident",
    ]),
    ("cloud_grc", [
        "cloud security", "devsecops", "devsec", "security engineer, cloud", "iam engineer",
        "identity and access", "kubernetes security", "container security", "security architect",
        "grc", "governance risk", "risk and compliance", "security compliance", "security audit",
        "iso 27001", "soc 2", "security consultant", "cybersecurity consultant",
        "sécurité cloud", "ingénieur sécurité", "consultant cybersécurité", "cybersécurité",
    ]),
    # General security net: catches "security engineer / cybersecurity" titles that
    # didn't hit a more specific family above, before falling through to non-security roles.
    ("security_other", [
        "security engineer", "cyber security", "cybersecurity", "information security",
        "infosec", "security specialist", "network security", "sécurité informatique",
        "sécurité des systèmes", "cybersécurité",
    ]),
    ("ai_ml", ["machine learning", " ml ", "ml engineer", "mlops", "deep learning", "nlp",
               "data scientist", "ai engineer", "artificial intelligence", "llm", "rag"]),
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


def extract_apply_link(raw_html: Optional[str], exclude_domain: str = "") -> Optional[str]:
    """Best-effort pull of the real application-form link out of an aggregator's
    raw HTML job description.

    Boards like Arbeitnow, Jobicy and Remotive don't host a form themselves —
    their API's own "url" field just points back to their own listing page, and
    the actual link to the employer's ATS is buried as an <a href> somewhere in
    the description ("Apply here: ..."). Call this BEFORE strip_html() throws
    the tags away. Prefers a link whose text/href mentions "apply"; otherwise
    falls back to the last external, non-social link (apply links are usually
    near the end of the posting). Returns None if nothing usable is found, so
    callers can fall back to the aggregator's own URL unchanged.
    """
    if not raw_html:
        return None
    candidates = []
    for href, text in _HREF_RE.findall(html.unescape(raw_html)):
        href = href.strip()
        if not href.lower().startswith("http"):
            continue
        host = urlparse(href).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        if exclude_domain and exclude_domain in host:
            continue
        if any(d in host for d in _SOCIAL_DOMAINS):
            continue
        candidates.append((href, _TAG_RE.sub(" ", text).strip().lower()))
    if not candidates:
        return None
    for href, text in candidates:
        if "apply" in text or "apply" in href.lower():
            return href
    return candidates[-1][0]


def classify_city(location_raw: Optional[str]) -> str:
    loc = (location_raw or "").lower()
    if not loc:
        return "other"
    for city, needles in _CITY_PATTERNS:
        if any(n in loc for n in needles):
            return city
    padded = f" {loc} "
    # A bare EU region ("Europe", "EMEA", "EU") with no city is EU-eligible.
    if any(h in padded for h in _EU_REGION):
        return "remote-eu"
    is_remote = any(h in loc for h in _REMOTE_HINTS)
    if is_remote:
        # The user is open to roles abroad (Europe + Americas + worldwide), so a
        # remote role pinned to a non-EU region is kept as worldwide, not dropped.
        if any(h in padded for h in _NON_EU_HINTS):
            return "remote-global"
        if any(h in padded for h in _EU_HINTS):
            return "remote-eu"
        if loc.strip() in ("remote", "fully remote", "100% remote", "remote work"):
            # Bare "remote" — assume EU-eligible; the sponsorship flag is the real filter.
            return "remote-eu"
        if any(h in padded for h in _GLOBAL_HINTS):
            return "remote-global"
        # Generic remote with no geo at all: keep as worldwide-eligible.
        return "remote-global"
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
