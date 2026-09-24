"""Preference-learning model — learns Sami's taste from his own decisions.

Pure stdlib, no numpy/sklearn (so a friend who clones the repo needs zero setup).
It's a smoothed log-odds (naive-Bayes-flavoured) model: for every feature value it
compares how often that value shows up in jobs Sami *pursued* vs jobs he *rejected*,
and turns that into a weight. A job's "for you" score is the logistic of the sum of
its feature weights. Everything is explainable — every score comes with the exact
features that pushed it up or down.

Training signal comes straight from the jobs table (current decisions), so it works
even before any event history exists, and gets sharper every time Sami acts.
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(ROOT, "data", "model.json")

# What counts as Sami pursuing vs rejecting a job.
POSITIVE_STATUS = {"queued", "materials_ready", "applied", "interview", "offer"}
NEGATIVE_STATUS = {"dismissed", "rejected"}
# "closed" = the posting vanished from the ATS, not a decision → never a training label.

_STOP = {
    "the", "and", "for", "with", "you", "our", "your", "are", "will", "who", "that",
    "this", "from", "have", "has", "was", "not", "but", "all", "can", "job", "role",
    "team", "work", "working", "years", "year", "experience", "x", "f", "m", "h",
    "senior", "junior", "staff", "principal", "lead", "mid", "level",  # seniority handled separately
    # generic title nouns already captured by role_family — leaving them
    # learnable would let one over-dismissed title (e.g. every "Site
    # Reliability Engineer") smear a strong negative weight onto every
    # other job that merely happens to share the word "engineer".
    "engineer", "developer", "scientist", "analyst", "architect", "specialist", "consultant", "manager",
}
_TOKEN_RE = re.compile(r"[a-z0-9+#]+")

# Skill tokens worth learning on even when they appear only in the description.
_SKILL_KW = [
    "python", "javascript", "react", "java", "sql", "kafka", "spark", "aws", "gcp",
    "azure", "kubernetes", "docker", "llm", "rag", "agentic", "mcp", "etl", "nlp",
    "tensorflow", "pytorch", "postgresql", "redshift", "databricks", "airflow",
    "microservices", "distributed", "streaming", "backend", "frontend", "fullstack",
    "platform", "data", "ml", "ai", "api", "golang", "rust", "scala", "typescript",
]

NAMESPACES = ["role", "city", "seniority", "startup", "sponsorship", "company", "kw"]
NS_LABELS = {
    "role": "Role family", "city": "Location", "seniority": "Seniority",
    "startup": "Company type", "sponsorship": "Sponsorship", "company": "Company",
    "kw": "Keyword",
}


def _tokens(job: dict) -> List[str]:
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    # Free-form tokenization stays title-only: descriptions are long, often in
    # other languages, and quickly drown the model in noise (foreign stopwords,
    # filler words) that just happens to correlate with a handful of decisions.
    # Description text still counts, but only through the curated skill list
    # below, which is exactly the trade-off that keeps this explainable.
    title_words = [t for t in _TOKEN_RE.findall(title) if len(t) >= 3 and t not in _STOP]
    toks = set(title_words)
    # adjacent-word phrases from the title — specific enough to isolate one
    # exact title pattern ("site reliability") from the generic words it's
    # built from, so a title that gets dismissed a lot doesn't smear its
    # negative weight onto every other job sharing one of those words.
    toks |= {f"{a} {b}" for a, b in zip(title_words, title_words[1:])}
    hay = f" {title} {desc} "
    for kw in _SKILL_KW:
        if f" {kw} " in hay or kw in title:
            toks.add(kw)
    return sorted(toks)


def features(job: dict) -> List[Tuple[str, str]]:
    """The (namespace, value) feature pairs that describe a job."""
    feats: List[Tuple[str, str]] = [
        ("role", job.get("role_family") or "unknown"),
        ("city", job.get("city") or "other"),
        ("seniority", job.get("seniority") or "unknown"),
        ("startup", "startup" if job.get("is_startup") else "big"),
        ("sponsorship", job.get("sponsorship") or "silent"),
        ("company", (job.get("company") or "").strip().lower() or "unknown"),
    ]
    feats += [("kw", t) for t in _tokens(job)]
    return feats


def _label(job: dict) -> Optional[int]:
    if job.get("starred"):
        return 1
    st = job.get("status")
    if st in POSITIVE_STATUS:
        return 1
    if st in NEGATIVE_STATUS:
        return 0
    return None  # unlabeled (interested / closed)


def train(jobs: List[dict]) -> dict:
    """Build the weight table from labelled jobs. Returns a serialisable model."""
    pos = Counter()   # feature -> # positive jobs with it
    neg = Counter()
    P = N = 0
    for job in jobs:
        lab = _label(job)
        if lab is None:
            continue
        if lab == 1:
            P += 1
        else:
            N += 1
        seen = set()
        for ns, val in features(job):
            key = f"{ns}:{val}"
            if key in seen:
                continue
            seen.add(key)
            (pos if lab == 1 else neg)[key] += 1

    base = math.log((P + 1) / (N + 1))
    weights: Dict[str, float] = {}
    support: Dict[str, List[int]] = {}
    CAT_SHRINK = 2.0   # categorical facets (role/city/company/…): trust grows quickly with evidence
    KW_SHRINK = 3.0    # keywords/phrases: needs more evidence before being trusted at all
    KW_CAP = 1.5       # ...and even then, never swing a score harder than a strong categorical signal
    for key in set(pos) | set(neg):
        p, n = pos[key], neg[key]
        total = p + n
        # keywords need to appear at least twice to earn a weight (kills one-off noise);
        # categorical facets (role/city/…) are meaningful even from a single job.
        is_kw = key.startswith("kw:")
        min_support = 2 if is_kw else 1
        if total < min_support:
            continue
        # log-odds relative to base rate, Laplace-smoothed.
        raw = math.log((p + 1.0) / (n + 1.0)) - base
        if is_kw:
            # Confidence grows with log(evidence), not evidence itself: dismissing
            # 1000 postings that share one phrase carries barely more weight than
            # dismissing 50 of them, so one over-represented title can't drown out
            # every other job that happens to share a common word with it.
            conf = math.log1p(total) / (math.log1p(total) + KW_SHRINK)
            w = max(-KW_CAP, min(KW_CAP, raw * conf))
        else:
            # categorical facets: shrink toward 0 in proportion to how little
            # evidence backs them, but let real volume compound normally.
            w = raw * (total / (total + CAT_SHRINK))
        if abs(w) < 0.01:
            continue
        weights[key] = round(w, 4)
        support[key] = [p, n]

    return {
        "weights": weights, "support": support, "base": round(base, 4),
        "pos": P, "neg": N, "trained_at": _now_iso(),
        "ready": P >= 3 and N >= 2,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def score(job: dict, model: dict) -> float:
    """Logistic 'for you' score in [0,1]. 0.5 when the model has nothing to say."""
    w = model.get("weights", {})
    if not w:
        return 0.5
    z = 0.0
    for ns, val in features(job):
        z += w.get(f"{ns}:{val}", 0.0)
    # temper keyword pile-up; z is already relative to base rate
    return round(1.0 / (1.0 + math.exp(-max(-8.0, min(8.0, z)))), 4)


def explain(job: dict, model: dict, top: int = 4) -> List[dict]:
    """Top contributing features (why this score), most influential first."""
    w = model.get("weights", {})
    contribs = []
    for ns, val in features(job):
        key = f"{ns}:{val}"
        wt = w.get(key)
        if wt:
            contribs.append({"ns": ns, "label": NS_LABELS.get(ns, ns), "value": val, "weight": wt})
    contribs.sort(key=lambda c: abs(c["weight"]), reverse=True)
    return contribs[:top]


def blended_score(job: dict, model: dict) -> float:
    """What powers the 'For you' sort: base relevance fused with learned taste."""
    base = float(job.get("match_score") or 0.0)
    if not model.get("ready"):
        return base
    return round(0.45 * base + 0.55 * score(job, model), 4)


# --- persistence + insights -------------------------------------------------

# Training re-tokenizes every job's title+description and writes model.json to
# disk — real work, not free. Every page load used to call load() 2-3 times
# (jobs/stats/insights all fire in parallel) and every one of those retrained
# from scratch, even though nothing about Sami's decisions had changed since
# the last request. Cache the trained model in memory and only retrain when a
# decision actually changes (queue/dismiss/star/status/harvest/import) —
# invalidate() is called from those spots in app.py.
_CACHE: Dict[str, object] = {"model": None, "dirty": True}


def invalidate() -> None:
    _CACHE["dirty"] = True


def load(conn) -> dict:
    if not _CACHE["dirty"] and _CACHE["model"] is not None:
        return _CACHE["model"]
    import db
    model = train(db.all_jobs(conn))
    try:
        with open(MODEL_PATH, "w", encoding="utf-8") as f:
            json.dump(model, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    _CACHE["model"] = model
    _CACHE["dirty"] = False
    return model


def _top(model: dict, ns: str, sign: int, limit: int = 6) -> List[dict]:
    out = []
    for key, wt in model.get("weights", {}).items():
        if not key.startswith(ns + ":"):
            continue
        if (sign > 0 and wt > 0) or (sign < 0 and wt < 0):
            p, n = model.get("support", {}).get(key, [0, 0])
            out.append({"value": key.split(":", 1)[1], "weight": wt, "pos": p, "neg": n})
    out.sort(key=lambda x: x["weight"], reverse=(sign > 0))
    return out[:limit]


def insights(conn) -> dict:
    import db
    jobs = db.all_jobs(conn)
    model = load(conn)

    funnel = Counter(j.get("status") for j in jobs)
    likes = {ns: _top(model, ns, +1) for ns in NAMESPACES}
    dislikes = {ns: _top(model, ns, -1) for ns in NAMESPACES}

    # activity timeline from the events log (last 30 days, by day)
    events = db.recent_events(conn, limit=2000)
    by_day = Counter()
    action_counts = Counter()
    for e in events:
        day = (e.get("ts") or "")[:10]
        if day:
            by_day[day] += 1
        action_counts[e.get("action")] += 1
    timeline = [{"day": d, "n": by_day[d]} for d in sorted(by_day)][-30:]

    pursued = sum(funnel[s] for s in POSITIVE_STATUS)
    rejected = sum(funnel[s] for s in NEGATIVE_STATUS)
    decided = pursued + rejected

    return {
        "model": {
            "ready": model["ready"], "pos": model["pos"], "neg": model["neg"],
            "trained_at": model["trained_at"], "n_features": len(model.get("weights", {})),
        },
        "funnel": dict(funnel),
        "totals": {
            "jobs": len(jobs), "pursued": pursued, "rejected": rejected,
            "decided": decided,
            "pursue_rate": round(pursued / decided, 3) if decided else None,
            "applied": funnel.get("applied", 0) + funnel.get("interview", 0) + funnel.get("offer", 0),
            "starred": sum(1 for j in jobs if j.get("starred")),
        },
        "likes": likes,
        "dislikes": dislikes,
        "timeline": timeline,
        "actions": dict(action_counts),
    }
