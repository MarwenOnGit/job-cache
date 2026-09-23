"""FastAPI app: REST API + serves the static dashboard. Run: uvicorn app:app"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
import urllib.error
import uuid
from typing import Optional
from urllib.parse import urljoin, urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
import http_util
import queue_io
import tracker
import harvester
import learn
import prefs as prefs_mod

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(ROOT, "frontend")
CONFIG_PATH = os.path.join(ROOT, "data", "config.json")

VALID_STATUSES = {
    "interested", "queued", "materials_ready", "applied",
    "interview", "offer", "rejected", "closed", "dismissed",
}

app = FastAPI(title="job cache")


@app.middleware("http")
async def _no_store(request, call_next):
    """Local dev tool: never let a browser serve a stale/empty cached page."""
    resp = await call_next(request)
    resp.headers["Cache-Control"] = "no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    return resp


def _conn():
    conn = db.connect()
    db.init_db(conn)
    return conn


def _reconcile(conn) -> None:
    """Promote queued jobs to materials_ready once Claude has written their per-job note."""
    ready = queue_io.done_ids()
    for job_id in ready:
        job = db.get_job(conn, job_id)
        if job and job["status"] in ("queued", "interested"):
            db.set_status(conn, job_id, "materials_ready")


def _refresh_csv(conn) -> None:
    try:
        tracker.export_csv(conn)
    except Exception:  # noqa: BLE001 - tracker is best-effort, never break a request
        pass


def _resolve_arbeitnow_apply_url(conn, job: dict) -> None:
    """Arbeitnow doesn't host an application form itself: its own "Apply Now"
    button is a same-site /apply route that either 302s to the real ATS, or
    (for jobs using Arbeitnow's own quick-apply form: name, CV, Apply button,
    nothing else) answers 200 right there. Resolve it once, lazily, the first
    time this job's detail is opened, and cache the result so it's a one-time
    cost per job rather than something every harvest has to pay for.
    """
    url = job.get("apply_url") or ""
    if job.get("ats_type") != "arbeitnow" or "arbeitnow.com" not in url:
        return
    probe = url.rstrip("/") + "/apply"
    result = http_util.resolve_redirect(probe)
    if result is None:
        return  # network hiccup — leave apply_url as-is, retry on the next open
    status, location = result
    if status in (301, 302, 303, 307, 308) and location:
        dest = urljoin(probe, location)
        if urlparse(dest).netloc and "arbeitnow.com" not in urlparse(dest).netloc:
            job["apply_url"] = dest
            db.set_apply_url(conn, job["id"], dest)
    elif status == 200:
        # this IS the final page (Arbeitnow's own quick-apply form), not a
        # listing to redirect away from.
        job["apply_url"] = probe
        db.set_apply_url(conn, job["id"], probe)
    # else (404/5xx/...): leave apply_url unchanged.


def _snapshot(job: dict) -> dict:
    return {k: job.get(k) for k in
            ("company", "role_family", "city", "seniority", "is_startup", "sponsorship", "match_score")}


class StatusBody(BaseModel):
    status: str


class NotesBody(BaseModel):
    notes: str


class StarBody(BaseModel):
    starred: bool


class ProfileBody(BaseModel):
    cv: Optional[str] = None
    preferences: Optional[str] = None


class ConfigBody(BaseModel):
    owner_name: Optional[str] = None
    theme: Optional[str] = None


# --- jobs -------------------------------------------------------------------
@app.get("/api/jobs")
def list_jobs(city: Optional[str] = None, role_family: Optional[str] = None,
              sponsorship: Optional[str] = None, startup: Optional[bool] = None,
              status: Optional[str] = None, level: str = "suitable", sort: str = "score",
              starred: Optional[bool] = None, q: Optional[str] = None):
    conn = _conn()
    try:
        _reconcile(conn)
        jobs = db.get_jobs(conn, city=city, role_family=role_family,
                           sponsorship=sponsorship, startup=startup, status=status,
                           level=level, sort="score")
        model = learn.load(conn)
        for j in jobs:
            j["learned_score"] = learn.score(j, model)
            j["for_you"] = learn.blended_score(j, model)
        if starred:
            jobs = [j for j in jobs if j.get("starred")]
        if q:
            ql = q.lower()
            jobs = [j for j in jobs if ql in (j.get("title", "") + " " + j.get("company", "")).lower()]
        if sort == "for_you":
            jobs.sort(key=lambda j: j["for_you"], reverse=True)
        elif sort == "date":
            jobs.sort(key=lambda j: j.get("posted_at") or "", reverse=True)
        elif sort == "company":
            jobs.sort(key=lambda j: (j.get("company") or "").lower())
        return {"count": len(jobs), "jobs": jobs, "model_ready": model.get("ready")}
    finally:
        conn.close()


@app.get("/api/stats")
def stats():
    conn = _conn()
    try:
        _reconcile(conn)
        by_status = {r["status"]: r["c"] for r in
                     conn.execute("SELECT status, count(*) c FROM jobs GROUP BY status")}
        browsable = db.get_jobs(conn, level="suitable")
        starred = conn.execute("SELECT count(*) c FROM jobs WHERE starred=1").fetchone()["c"]
        model = learn.load(conn)
        return {"browsable": len(browsable), "by_status": by_status,
                "starred": starred, "model_ready": model.get("ready")}
    finally:
        conn.close()


@app.get("/api/insights")
def insights():
    conn = _conn()
    try:
        _reconcile(conn)
        return learn.insights(conn)
    finally:
        conn.close()


# --- update check -------------------------------------------------------
_VERSION_CACHE = {"checked_at": 0.0, "data": None}
_VERSION_CACHE_TTL = 600  # seconds; a git fetch hits the network, don't do it on every poll


def _git(*args, timeout=6) -> Optional[str]:
    try:
        res = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return res.stdout.strip() if res.returncode == 0 else None
    except Exception:  # noqa: BLE001 - best-effort, git/network may be unavailable
        return None


def _check_update() -> dict:
    """Compare local HEAD to origin/main. Silent (available: False) on any git/network failure."""
    local_sha = _git("rev-parse", "HEAD")
    if not local_sha:
        return {"available": False}
    if _git("fetch", "origin", "main", "--quiet") is None:
        return {"available": False}
    remote_sha = _git("rev-parse", "origin/main")
    if not remote_sha:
        return {"available": False}
    if remote_sha == local_sha:
        return {"available": True, "up_to_date": True}
    behind = _git("rev-list", "--count", f"{local_sha}..origin/main")
    behind_n = int(behind) if behind and behind.isdigit() else None
    if not behind_n:
        # sha differs but origin/main has nothing local doesn't already have
        # (e.g. a local feature branch ahead of main) — nothing to pull.
        return {"available": True, "up_to_date": True}
    return {
        "available": True,
        "up_to_date": False,
        "behind": behind_n,
        "current": local_sha[:7],
        "latest": remote_sha[:7],
    }


@app.get("/api/version")
def version_check():
    now = time.time()
    if _VERSION_CACHE["data"] is None or now - _VERSION_CACHE["checked_at"] > _VERSION_CACHE_TTL:
        _VERSION_CACHE["data"] = _check_update()
        _VERSION_CACHE["checked_at"] = now
    return _VERSION_CACHE["data"]


def _reconcile_questions(conn) -> None:
    """Pull in answers Claude wrote to queue/questions/answered/<id>.md."""
    for qid in queue_io.answered_question_ids():
        q = db.get_question(conn, qid)
        if q and q["status"] == "pending":
            ans = queue_io.read_answered_question(qid)
            if ans:
                db.set_answer(conn, qid, ans)


class QuestionBody(BaseModel):
    question: str
    job_id: Optional[str] = None
    job_ids: Optional[list] = None


@app.get("/api/questions")
def list_questions():
    conn = _conn()
    try:
        _reconcile_questions(conn)
        rows = db.get_questions(conn)
        pending = sum(1 for r in rows if r["status"] == "pending")
        return {"questions": rows, "pending": pending, "count": len(rows)}
    finally:
        conn.close()


@app.post("/api/questions")
def create_question(body: QuestionBody):
    q = (body.question or "").strip()
    if not q:
        raise HTTPException(400, "empty question")
    conn = _conn()
    try:
        qid = uuid.uuid4().hex[:16]
        ids = body.job_ids if body.job_ids else ([body.job_id] if body.job_id else [])
        seen: set = set()
        ids = [i for i in ids if i and not (i in seen or seen.add(i))]  # dedupe, keep order
        jobs = [j for j in (db.get_job(conn, i) for i in ids) if j]
        company = ", ".join(dict.fromkeys(j["company"] for j in jobs)) or None
        primary = jobs[0]["id"] if jobs else None
        row = db.add_question(conn, qid, q, primary, company)
        queue_io.write_question_pending(qid, q, jobs)
        db.log_event(conn, primary or "", "ask_question", {"company": company, "refs": len(jobs)})
        return row
    finally:
        conn.close()


@app.delete("/api/questions/{qid}")
def remove_question(qid: str):
    conn = _conn()
    try:
        db.delete_question(conn, qid)
        queue_io.clear_question_files(qid)
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/applications")
def applications():
    conn = _conn()
    try:
        _reconcile(conn)
        rows = db.get_tracked(conn)
        groups = {s: [] for s in db.TRACKED}
        for r in rows:
            groups.setdefault(r["status"], []).append(r)
        return {"count": len(rows), "groups": groups}
    finally:
        conn.close()


@app.get("/api/applications.csv")
def applications_csv():
    conn = _conn()
    try:
        path = tracker.export_csv(conn)
        return PlainTextResponse(open(path, encoding="utf-8").read(), media_type="text/csv")
    finally:
        conn.close()


# --- profile + config -------------------------------------------------------
@app.get("/api/profile")
def profile():
    return {"cv": queue_io._read(queue_io.CV_PATH),
            "preferences": queue_io._read(queue_io.PREFS_PATH),
            "preferences_effective": queue_io.read_preferences()}


@app.post("/api/profile")
def save_profile(body: ProfileBody):
    if body.cv is not None:
        with open(queue_io.CV_PATH, "w", encoding="utf-8") as f:
            f.write(body.cv)
    if body.preferences is not None:
        with open(queue_io.PREFS_PATH, "w", encoding="utf-8") as f:
            f.write(body.preferences)
    return {"ok": True}


# --- structured search preferences (countries, roles, titles, keywords) ------
class SearchPrefsBody(BaseModel):
    locations: Optional[list] = None
    role_families: Optional[list] = None
    titles: Optional[list] = None
    keywords: Optional[list] = None
    experience: Optional[str] = None
    language: Optional[str] = None


@app.get("/api/preferences")
def get_preferences():
    """The structured search preferences (what/where to search), plus the option
    catalog for the editor. Seeded from onboarding on first view so nothing is
    hidden behind a from-scratch re-onboarding."""
    return {"preferences": prefs_mod.load_or_seed(),
            "saved": os.path.exists(prefs_mod.PREFS_JSON_PATH),
            "catalog": prefs_mod.catalog()}


@app.post("/api/preferences")
def set_preferences(body: SearchPrefsBody):
    saved = prefs_mod.save_structured(body.model_dump())
    return {"ok": True, "preferences": saved}


def _read_config() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


@app.get("/api/config")
def get_config():
    cfg = _read_config()
    cfg.setdefault("owner_name", "")
    cfg.setdefault("theme", "dark")
    return cfg


@app.post("/api/config")
def set_config(body: ConfigBody):
    cfg = _read_config()
    if body.owner_name is not None:
        cfg["owner_name"] = body.owner_name.strip()
    if body.theme is not None:
        cfg["theme"] = body.theme
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return {"ok": True, **cfg}


# --- onboarding -------------------------------------------------------------
class OnboardingBody(BaseModel):
    owner_name: Optional[str] = None
    cv: Optional[str] = None
    cities: Optional[list] = None
    experience: Optional[str] = None
    roles: Optional[list] = None
    language: Optional[str] = None
    tone: Optional[str] = None


def _prefs_ready() -> bool:
    return bool(queue_io._read(queue_io.PREFS_PATH).strip())


@app.get("/api/onboarding")
def get_onboarding():
    """Whether the user still needs to onboard, and their saved form (if any)."""
    cv = queue_io._read(queue_io.CV_PATH).strip()
    return {"has_cv": bool(cv), "preferences_ready": _prefs_ready(),
            "onboarding": queue_io.read_onboarding(),
            "needs_onboarding": not (cv and _prefs_ready())}


@app.post("/api/onboarding")
def save_onboarding(body: OnboardingBody):
    """Save the new-user form: CV -> cv/cv.md, the rest -> data/onboarding.json for
    the /onboard Claude Code command, which turns it into a personal preferences.md."""
    if body.cv:
        os.makedirs(os.path.dirname(queue_io.CV_PATH), exist_ok=True)
        with open(queue_io.CV_PATH, "w", encoding="utf-8") as f:
            f.write(body.cv)
    form = {"owner_name": body.owner_name or "", "cities": body.cities or [],
            "experience": body.experience or "", "roles": body.roles or [],
            "language": body.language or "", "tone": body.tone or ""}
    queue_io.write_onboarding(form)
    if body.owner_name is not None:
        cfg = _read_config(); cfg["owner_name"] = body.owner_name.strip()
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    return {"ok": True, "preferences_ready": _prefs_ready()}


# --- single job -------------------------------------------------------------
@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    conn = _conn()
    try:
        job = db.get_job(conn, job_id)
        if not job:
            raise HTTPException(404, "job not found")
        _resolve_arbeitnow_apply_url(conn, job)
        job["materials"] = queue_io.read_materials(job_id)
        job["materials_struct"] = queue_io.read_materials_structured(job_id)
        model = learn.load(conn)
        job["learned_score"] = learn.score(job, model)
        job["for_you"] = learn.blended_score(job, model)
        job["learned_reasons"] = learn.explain(job, model)
        job["model_ready"] = model.get("ready")
        return job
    finally:
        conn.close()


@app.post("/api/jobs/{job_id}/queue")
def queue_job(job_id: str):
    conn = _conn()
    try:
        job = db.get_job(conn, job_id)
        if not job:
            raise HTTPException(404, "job not found")
        path = queue_io.write_pending(job)
        db.set_status(conn, job_id, "queued")
        db.log_event(conn, job_id, "queue", _snapshot(job))
        _refresh_csv(conn)
        return {"ok": True, "queued": os.path.basename(path)}
    finally:
        conn.close()


@app.post("/api/jobs/{job_id}/dismiss")
def dismiss_job(job_id: str):
    conn = _conn()
    try:
        job = db.get_job(conn, job_id)
        if not job:
            raise HTTPException(404, "job not found")
        db.set_status(conn, job_id, "dismissed")
        db.log_event(conn, job_id, "dismiss", _snapshot(job))
        return {"ok": True, "status": "dismissed"}
    finally:
        conn.close()


@app.post("/api/jobs/{job_id}/star")
def star_job(job_id: str, body: StarBody):
    conn = _conn()
    try:
        job = db.get_job(conn, job_id)
        if not job:
            raise HTTPException(404, "job not found")
        db.set_starred(conn, job_id, body.starred)
        db.log_event(conn, job_id, "star" if body.starred else "unstar", _snapshot(job))
        return {"ok": True, "starred": body.starred}
    finally:
        conn.close()


@app.post("/api/jobs/{job_id}/notes")
def notes_job(job_id: str, body: NotesBody):
    conn = _conn()
    try:
        if not db.set_notes(conn, job_id, body.notes):
            raise HTTPException(404, "job not found")
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/jobs/{job_id}/materials")
def materials(job_id: str):
    text = queue_io.read_materials(job_id)
    if text is None:
        raise HTTPException(404, "materials not ready")
    return {"id": job_id, "materials": text}


@app.post("/api/jobs/{job_id}/status")
def set_status(job_id: str, body: StatusBody):
    if body.status not in VALID_STATUSES:
        raise HTTPException(400, f"invalid status: {body.status}")
    conn = _conn()
    try:
        job = db.get_job(conn, job_id)
        if not job:
            raise HTTPException(404, "job not found")
        db.set_status(conn, job_id, body.status)
        db.log_event(conn, job_id, f"status:{body.status}", _snapshot(job))
        _refresh_csv(conn)
        return {"ok": True, "status": body.status}
    finally:
        conn.close()


@app.post("/api/harvest")
def run_harvest():
    conn = _conn()
    try:
        summary = harvester.harvest(conn, verbose=False)
        return summary
    finally:
        conn.close()


# --- share: export / import -------------------------------------------------
@app.get("/api/export")
def export_all():
    """Your complete personal snapshot — CV, preferences, decisions, generated
    materials, Q&A, and settings. This is how your data lives outside the repo:
    back it up, move machines, or share it. The repo itself stays data-free."""
    conn = _conn()
    try:
        return JSONResponse({
            "version": 2,
            "profile": {"cv": queue_io._read(queue_io.CV_PATH),
                        "preferences": queue_io.read_preferences()},
            "config": _read_config(),
            "onboarding": queue_io.read_onboarding(),
            "jobs": db.all_jobs(conn),
            "events": db.recent_events(conn, limit=100000),
            "questions": db.get_questions(conn),
            "materials": queue_io.export_materials(),
            "insights": learn.insights(conn),
        }, headers={"Content-Disposition": "attachment; filename=job-cache-export.json"})
    finally:
        conn.close()


class ImportBody(BaseModel):
    jobs: Optional[list] = None
    events: Optional[list] = None
    questions: Optional[list] = None
    materials: Optional[dict] = None
    profile: Optional[dict] = None
    config: Optional[dict] = None
    merge: bool = True


@app.post("/api/import")
def import_all(body: ImportBody):
    """Import a friend's export: adds their jobs + decision history (star/notes/status)."""
    conn = _conn()
    added = updated = 0
    requeued = 0
    try:
        done = queue_io.done_ids()
        pending_ids = {fn[:-5] for fn in os.listdir(queue_io.PENDING_DIR)} \
            if os.path.isdir(queue_io.PENDING_DIR) else set()
        for j in (body.jobs or []):
            existing = db.get_job(conn, j.get("id"))
            cols = ("company", "ats_type", "ats_job_id", "title", "location_raw", "city",
                    "description", "apply_url", "role_family", "is_startup", "sponsorship",
                    "seniority", "req_years", "match_score", "match_reasons", "status",
                    "first_seen", "last_seen", "posted_at", "starred", "notes")
            row = {c: j.get(c) for c in cols}
            row["id"] = j.get("id")
            row["is_startup"] = 1 if j.get("is_startup") else 0
            row["starred"] = 1 if j.get("starred") else 0
            mr = j.get("match_reasons")
            row["match_reasons"] = json.dumps(mr) if isinstance(mr, list) else (mr or "[]")
            if existing and not body.merge:
                continue
            placeholders = ", ".join("?" for _ in row)
            names = ", ".join(row)
            conn.execute(
                f"INSERT INTO jobs ({names}) VALUES ({placeholders}) "
                f"ON CONFLICT(id) DO UPDATE SET status=excluded.status, "
                f"starred=excluded.starred, notes=excluded.notes",
                list(row.values()))
            updated += 1 if existing else 0
            added += 0 if existing else 1
            # imported jobs already marked "queued" need their queue/pending/<id>.json
            # handshake file recreated too -- it doesn't travel with the DB export.
            if row["status"] == "queued" and row["id"] not in done and row["id"] not in pending_ids:
                queue_io.write_pending(row)
                requeued += 1
        # decisions history
        for e in (body.events or []):
            conn.execute("INSERT INTO events (ts, job_id, action, features) VALUES (?,?,?,?)",
                         (e.get("ts"), e.get("job_id"), e.get("action"), e.get("features") or "{}"))
        # Q&A history
        for q in (body.questions or []):
            conn.execute(
                "INSERT OR REPLACE INTO questions (id, ts, job_id, company, question, answer, status) "
                "VALUES (?,?,?,?,?,?,?)",
                (q.get("id"), q.get("ts"), q.get("job_id"), q.get("company"),
                 q.get("question"), q.get("answer"), q.get("status") or "answered"))
        conn.commit()
        # profile + generated materials + config (files on disk)
        prof = body.profile or {}
        if prof.get("cv"):
            with open(queue_io.CV_PATH, "w", encoding="utf-8") as f:
                f.write(prof["cv"])
        if prof.get("preferences"):
            with open(queue_io.PREFS_PATH, "w", encoding="utf-8") as f:
                f.write(prof["preferences"])
        mats = queue_io.write_materials(body.materials or {})
        if body.config:
            cfg = _read_config(); cfg.update({k: v for k, v in body.config.items() if v is not None})
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        return {"ok": True, "added": added, "updated": updated, "materials": mats,
                "requeued": requeued,
                "questions": len(body.questions or []), "events": len(body.events or [])}
    finally:
        conn.close()


# --- apply workspace: iframe proxy -----------------------------------------
@app.get("/api/proxy")
def proxy(url: str):
    """Best-effort fetch of an apply page with frame-blocking headers stripped, so it
    can render inside the Apply Workspace iframe for side-by-side copy-paste.

    Classic server-rendered ATS pages (Greenhouse, Lever) usually work; heavy SPAs
    (Ashby, Workday) may not fully render — the UI offers a 'pop out' fallback.

    On failure (dead link, refuses to answer, times out, isn't HTML) this returns
    a JSON error with a non-2xx status instead of a 200 HTML page, so the frontend
    can tell success from failure and show its own blocked-embed card rather than
    an error snippet rendered inside the iframe.
    """
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(400, "bad url")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            ctype = r.headers.get("Content-Type", "text/html")
            raw = r.read()
    except urllib.error.HTTPError as e:
        return JSONResponse({"ok": False, "status": e.code, "reason": str(e.reason)}, status_code=502)
    except (urllib.error.URLError, TimeoutError) as e:  # noqa
        reason = str(getattr(e, "reason", e)) or type(e).__name__
        return JSONResponse({"ok": False, "status": None, "reason": reason}, status_code=502)
    if "html" not in ctype:
        return JSONResponse({"ok": False, "status": 200, "reason": "Not an HTML page"}, status_code=502)
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:  # noqa
        text = raw.decode("latin-1", errors="replace")
    # inject <base> so relative assets/links resolve against the origin
    base_tag = f'<base href="{url}">'
    lower = text.lower()
    if "<head" in lower:
        idx = lower.index("<head")
        end = text.index(">", idx) + 1
        text = text[:end] + base_tag + text[end:]
    else:
        text = base_tag + text
    # response omits X-Frame-Options / CSP, so it is embeddable
    return HTMLResponse(text)


def _inlined_index() -> str:
    """Serve the whole dashboard as ONE self-contained document: CSS + JS inlined.

    Some environments (content blockers, corporate security proxies) let the HTML
    document through but block or blank separate /app.js and /styles.css requests.
    Inlining means there's exactly one request — if the page loads at all, the whole
    app loads. Source files stay separate on disk for maintainability.
    """
    html = queue_io._read(os.path.join(FRONTEND_DIR, "index.html"))
    css = queue_io._read(os.path.join(FRONTEND_DIR, "styles.css"))
    js = queue_io._read(os.path.join(FRONTEND_DIR, "app.js"))
    import re as _re
    # function replacements so backslashes in CSS/JS are NOT treated as regex group refs
    html = _re.sub(r'<link rel="stylesheet"[^>]*>', lambda _m: f"<style>{css}</style>", html, count=1)
    html = _re.sub(r'<script src="/app\.js[^"]*"></script>', lambda _m: f"<script>{js}</script>", html, count=1)
    return html


# --- static frontend (mounted last so /api/* wins) --------------------------
if os.path.isdir(FRONTEND_DIR):
    @app.get("/")
    def index():
        return HTMLResponse(_inlined_index())

    # keep the separate assets available too (harmless), but the app loads from "/" alone
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")
