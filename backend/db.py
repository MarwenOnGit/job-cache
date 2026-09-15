"""SQLite persistence for jobs. Single-file DB, zero setup."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from models import JOB_COLUMNS, Job

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "jobs.db")

# Statuses that mean the user has engaged — a re-harvest must not downgrade them.
ENGAGED = {"queued", "materials_ready", "applied", "interview", "offer", "rejected"}
# Statuses shown in the Applications tab (the tracker).
TRACKED = ["queued", "materials_ready", "applied", "interview", "offer", "rejected"]
# Statuses a re-harvest may auto-close (i.e. already out of the browse view).
HIDDEN = ("closed", "dismissed")
# Hidden from the Jobs browse view: anything you've acted on. The Jobs page is the
# discovery inbox of NEW matches (status 'interested'); once a job is queued, has
# materials, is applied, progressed, rejected, or dismissed, it lives in Queue /
# Applications and drops out of browse.
BROWSE_HIDDEN = ("queued", "materials_ready", "applied", "interview", "offer", "rejected", "closed", "dismissed")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    company TEXT, ats_type TEXT, ats_job_id TEXT,
    title TEXT, location_raw TEXT, city TEXT,
    description TEXT, apply_url TEXT, role_family TEXT,
    is_startup INTEGER, sponsorship TEXT,
    seniority TEXT, req_years INTEGER,
    match_score REAL, match_reasons TEXT, status TEXT,
    first_seen TEXT, last_seen TEXT, posted_at TEXT,
    starred INTEGER DEFAULT 0, notes TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, job_id TEXT, action TEXT, features TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_action ON events(action);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    ts TEXT, job_id TEXT, company TEXT,
    question TEXT, answer TEXT, status TEXT
);
CREATE INDEX IF NOT EXISTS idx_questions_ts ON questions(ts);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Add newer columns to a pre-existing DB without dropping rows/statuses."""
    cols = {d[1] for d in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    if "seniority" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN seniority TEXT")
    if "req_years" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN req_years INTEGER")
    if "starred" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN starred INTEGER DEFAULT 0")
    if "notes" not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN notes TEXT DEFAULT ''")
    conn.commit()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    _migrate(conn)
    conn.commit()


def backfill_seniority(conn: sqlite3.Connection) -> int:
    """Populate seniority/req_years for rows that predate those columns. No network."""
    from seniority import classify_seniority, extract_required_years
    rows = conn.execute(
        "SELECT id, title, description FROM jobs WHERE seniority IS NULL").fetchall()
    for r in rows:
        conn.execute(
            "UPDATE jobs SET seniority=?, req_years=? WHERE id=?",
            (classify_seniority(r["title"], r["description"] or ""),
             extract_required_years(r["description"] or ""), r["id"]),
        )
    conn.commit()
    return len(rows)


def upsert_jobs(conn: sqlite3.Connection, jobs: List[Job]) -> int:
    now = _now()
    placeholders = ", ".join("?" for _ in JOB_COLUMNS)
    updates = ", ".join(f"{c}=excluded.{c}" for c in JOB_COLUMNS
                        if c not in ("id", "first_seen", "status"))
    sql = (
        f"INSERT INTO jobs ({', '.join(JOB_COLUMNS)}) VALUES ({placeholders}) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}, last_seen=excluded.last_seen"
    )
    for job in jobs:
        row = job.to_row()
        row["first_seen"] = now
        row["last_seen"] = now
        conn.execute(sql, [row[c] for c in JOB_COLUMNS])
    conn.commit()
    return len(jobs)


def mark_closed(conn: sqlite3.Connection, company: str, active_ids: List[str]) -> None:
    cur = conn.execute("SELECT id, status FROM jobs WHERE company=?", (company,))
    active = set(active_ids)
    for row in cur.fetchall():
        if row["id"] not in active and row["status"] not in ENGAGED and row["status"] not in HIDDEN:
            conn.execute("UPDATE jobs SET status='closed' WHERE id=?", (row["id"],))
    conn.commit()


def get_jobs(conn: sqlite3.Connection, city: Optional[str] = None,
             role_family: Optional[str] = None, sponsorship: Optional[str] = None,
             startup: Optional[bool] = None, status: Optional[str] = None,
             level: str = "all", sort: str = "score") -> List[dict]:
    clauses, params = [], []
    if city:
        clauses.append("city=?"); params.append(city)
    if role_family:
        clauses.append("role_family=?"); params.append(role_family)
    if sponsorship:
        clauses.append("sponsorship=?"); params.append(sponsorship)
    if startup is not None:
        clauses.append("is_startup=?"); params.append(1 if startup else 0)
    if status:
        clauses.append("status=?"); params.append(status)
    else:
        clauses.append(f"status NOT IN ({','.join('?' for _ in BROWSE_HIDDEN)})")
        params.extend(BROWSE_HIDDEN)
    # Experience-fit filter (Sami has ~3 yrs; avoid senior + >5-year roles).
    if level == "suitable":
        clauses.append("(seniority IS NULL OR seniority IN ('junior','mid'))")
        clauses.append("(req_years IS NULL OR req_years<=5)")
    elif level == "junior":
        clauses.append("seniority='junior'")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order = {"score": "match_score DESC", "date": "posted_at DESC",
             "company": "company ASC"}.get(sort, "match_score DESC")
    cur = conn.execute(f"SELECT * FROM jobs {where} ORDER BY {order}", params)
    return [Job.row_to_dict(r) for r in cur.fetchall()]


def get_tracked(conn: sqlite3.Connection) -> List[dict]:
    cur = conn.execute(
        f"SELECT * FROM jobs WHERE status IN ({','.join('?' for _ in TRACKED)}) "
        f"ORDER BY company ASC, match_score DESC", TRACKED)
    return [Job.row_to_dict(r) for r in cur.fetchall()]


def get_job(conn: sqlite3.Connection, job_id: str) -> Optional[dict]:
    cur = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
    row = cur.fetchone()
    return Job.row_to_dict(row) if row else None


def set_status(conn: sqlite3.Connection, job_id: str, status: str) -> bool:
    cur = conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()
    return cur.rowcount > 0


def set_starred(conn: sqlite3.Connection, job_id: str, starred: bool) -> bool:
    cur = conn.execute("UPDATE jobs SET starred=? WHERE id=?", (1 if starred else 0, job_id))
    conn.commit()
    return cur.rowcount > 0


def set_notes(conn: sqlite3.Connection, job_id: str, notes: str) -> bool:
    cur = conn.execute("UPDATE jobs SET notes=? WHERE id=?", (notes, job_id))
    conn.commit()
    return cur.rowcount > 0


def log_event(conn: sqlite3.Connection, job_id: str, action: str, features: Optional[dict] = None) -> None:
    """Append a decision/interaction to the events log (fuel for the learning model)."""
    import json as _json
    conn.execute(
        "INSERT INTO events (ts, job_id, action, features) VALUES (?,?,?,?)",
        (_now(), job_id, action, _json.dumps(features or {}, ensure_ascii=False)),
    )
    conn.commit()


def all_jobs(conn: sqlite3.Connection) -> List[dict]:
    """Every job regardless of status — used by the learning model for training signal."""
    cur = conn.execute("SELECT * FROM jobs")
    return [Job.row_to_dict(r) for r in cur.fetchall()]


def recent_events(conn: sqlite3.Connection, limit: int = 500) -> List[dict]:
    cur = conn.execute(
        "SELECT ts, job_id, action, features FROM events ORDER BY id DESC LIMIT ?", (limit,))
    return [dict(r) for r in cur.fetchall()]


# --- application Q&A --------------------------------------------------------
def add_question(conn: sqlite3.Connection, qid: str, question: str,
                 job_id: Optional[str], company: Optional[str]) -> dict:
    conn.execute(
        "INSERT INTO questions (id, ts, job_id, company, question, answer, status) "
        "VALUES (?,?,?,?,?,NULL,'pending')",
        (qid, _now(), job_id, company, question))
    conn.commit()
    return get_question(conn, qid)


def get_question(conn: sqlite3.Connection, qid: str) -> Optional[dict]:
    r = conn.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
    return dict(r) if r else None


def get_questions(conn: sqlite3.Connection) -> List[dict]:
    cur = conn.execute("SELECT * FROM questions ORDER BY ts ASC")
    return [dict(r) for r in cur.fetchall()]


def set_answer(conn: sqlite3.Connection, qid: str, answer: str) -> bool:
    cur = conn.execute(
        "UPDATE questions SET answer=?, status='answered' WHERE id=?", (answer, qid))
    conn.commit()
    return cur.rowcount > 0


def delete_question(conn: sqlite3.Connection, qid: str) -> bool:
    cur = conn.execute("DELETE FROM questions WHERE id=?", (qid,))
    conn.commit()
    return cur.rowcount > 0


def pending_question_ids(conn: sqlite3.Connection) -> List[str]:
    return [r["id"] for r in conn.execute(
        "SELECT id FROM questions WHERE status='pending'")]
