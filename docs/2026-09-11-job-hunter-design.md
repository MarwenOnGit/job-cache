# job cache — Design Spec

> Originally shipped as "job-hunter"; renamed to **job cache**.

**Date:** 2026-09-11
**Owner:** Marouan Ben Hmed
**Status:** Approved design → ready for implementation plan

## 1. Purpose

A local, fully free job-search + assisted-application tool for a software engineer
(AI/ML, Data Eng, general SWE, AI/agentic tooling) targeting **Paris and nearby hubs
(Brussels, Geneva, London)** plus remote-EU. It aggregates real job postings, ranks them
against the owner's CV, and produces tailored application materials — with **no paid API
and no API keys**. The "AI" is the owner running **Claude Code in the terminal**; the app
and Claude Code communicate through files in the repo.

### Non-goals
- No auto-submission of applications (fragile, ToS-violating, ban risk). The tool is
  *assisted apply*: it drafts materials and deep-links to the real form; the human submits.
- No scraping of LinkedIn/Indeed/Welcome-to-the-Jungle (ToS + anti-bot). Sourcing is via
  free public ATS JSON endpoints only.
- No hosted service, no accounts, no cloud. Everything runs locally over SQLite.

## 2. Core loop (how "no key, no nothing" works)

```
Harvester (free) → SQLite → Dashboard → user selects jobs → queue/pending/<id>.json
                                                                    ↓
   dashboard shows materials ← queue/done/<id>.md ← Claude Code (terminal) reads
   → user reviews & clicks Apply                     CV + job, writes cover letter,
                                                      tailored bullets, match analysis
```

The owner runs `claude` in the repo and invokes a shipped slash command
(`/apply`, defined in `.claude/commands/apply.md`) which tells Claude to process every file
in `queue/pending/`, write tailored materials to `queue/done/`, and mark them done. The
dashboard watches `queue/done/` and surfaces the materials for review. No network AI calls.

## 3. Components

### 3.1 Harvester (Python)
- Reads `companies.yaml` (curated target list).
- For each company, calls the relevant free public ATS endpoint and normalizes results.
- **Supported ATS adapters** (all free, public JSON, no auth):
  - **Greenhouse** — `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`
  - **Lever** — `https://api.lever.co/v0/postings/{slug}?mode=json`
  - **Ashby** — `https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true`
  - **SmartRecruiters** — `https://api.smartrecruiters.com/v1/companies/{slug}/postings`
  - **Workday** — best-effort JSON POST to the company's `*.myworkdayjobs.com` CxS endpoint
    (per-tenant; may be marked experimental and skipped if unavailable).
- Normalizes every posting to a common `Job` record (see §5).
- Idempotent upsert into SQLite keyed by `(company, ats_job_id)`. Re-running refreshes
  and marks vanished postings as `closed`.
- Location filter: keep jobs whose location matches target cities (Paris, Île-de-France,
  Brussels, Geneva/Zürich, London) or remote-EU; drop obviously out-of-region roles.
- Role filter: keep jobs whose title/keywords match the target families
  (AI/ML, Data Eng, SWE, AI/agentic); everything else dropped.

### 3.2 Ranker (Python, free heuristic — no LLM)
- Deterministic score in [0,1] combining:
  - **Skills overlap** between CV skills and the job description (weighted keyword match).
  - **Role-family match** (title alignment to targeted families).
  - **Recency** (newer postings score higher).
- Produces `match_score` + a short human-readable `match_reasons` list, so the dashboard is
  instantly sortable without invoking Claude.
- Optional future toggle (documented, not built in v1): Claude re-ranks the top ~50.

### 3.3 Sponsorship + startup flagger (Python, free)
- Scans each description for visa/sponsorship language and labels:
  - `likely_sponsors` — mentions visa sponsorship / relocation support.
  - `no_sponsorship` — explicitly states no sponsorship / must have right to work.
  - `silent` — no mention (default).
- Tags `is_startup` (from `companies.yaml`) and `city`.
- These are **hints, never filters** — the owner applies even when sponsorship is unstated.

### 3.4 Dashboard (React + Vite, local)
- Job list: sortable by match score, date, company; filterable by city, role family,
  sponsorship label, startup/big-co, and status.
- Job detail: full description, match reasons, sponsorship label, apply URL.
- Actions: **Select → queue** (writes `queue/pending/<id>.json`), view generated materials
  once ready, **copy cover letter**, **open apply URL**, and set **status**.
- Status pipeline: `interested → queued → materials_ready → applied → interview → offer/rejected`.
- Polls the backend for queue/materials updates (simple interval; no websockets needed).

### 3.5 Backend API (FastAPI)
- Serves the built frontend and a small REST API:
  - `GET /api/jobs` (with filter/sort params)
  - `GET /api/jobs/{id}`
  - `POST /api/jobs/{id}/queue` → writes `queue/pending/<id>.json` (job + CV snapshot)
  - `POST /api/jobs/{id}/status` → updates status
  - `GET /api/jobs/{id}/materials` → returns parsed `queue/done/<id>.md` if present
  - `POST /api/harvest` → triggers a harvest run (also runnable via CLI)
- Reconciles `queue/done/` into the DB (`materials_ready`) on read/poll.

### 3.6 Claude handshake
- `queue/pending/<id>.json`: `{ job: {...}, cv_markdown: "...", instructions: "..." }`.
- `.claude/commands/apply.md`: a slash command instructing Claude to, for each pending job,
  produce a tailored **cover letter**, **3–5 tailored CV bullets**, and a **match/sponsorship
  analysis**, write them to `queue/done/<id>.md` (a defined template), and delete the pending
  file. Idempotent and resumable.
- `cv/cv.md`: the owner's CV converted from the PDF to markdown (source of truth for tailoring).

## 4. Stack & repo layout

Python **FastAPI** (harvester + API + static serving) · **React + Vite** frontend ·
**SQLite** store · file-based `queue/` for the Claude handshake. One launch script.

```
job-cache/
  companies.yaml              # curated company boards + keyless aggregator sources
  cv/ cv.md                   # CV as markdown
  backend/
    app.py                    # FastAPI app + routes
    harvester.py              # orchestrates adapters → DB
    adapters/                 # greenhouse.py, lever.py, ashby.py, smartrecruiters.py, workday.py
    ranker.py                 # heuristic scoring
    flagger.py                # sponsorship + startup/city tagging
    db.py                     # SQLite schema + access
    models.py                 # Job dataclass / pydantic
    tests/                    # adapter/ranker/flagger unit tests (offline fixtures)
  frontend/                   # React + Vite dashboard
  queue/ pending/ done/       # Claude handshake
  data/ jobs.db               # SQLite (gitignored)
  .claude/commands/apply.md   # "/apply" slash command
  run.sh                      # harvest + launch API + frontend
  README.md
```

## 5. Data model (SQLite `jobs` table, key fields)

```
id                TEXT PK      # stable hash of (company, ats_job_id)
company           TEXT
ats_type          TEXT         # greenhouse|lever|ashby|smartrecruiters|workday
ats_job_id        TEXT
title             TEXT
location_raw      TEXT
city              TEXT         # normalized: paris|brussels|geneva|london|remote-eu|other
description       TEXT
apply_url         TEXT
role_family       TEXT         # ai_ml|data_eng|swe|ai_agentic
is_startup        INTEGER
sponsorship       TEXT         # likely_sponsors|no_sponsorship|silent
match_score       REAL
match_reasons     TEXT         # JSON array
status            TEXT         # interested|queued|materials_ready|applied|interview|offer|rejected|closed
first_seen        TEXT
last_seen         TEXT
posted_at         TEXT
```

## 6. Company list strategy

Seed `companies.yaml` with ~150–200 entries, **weighted toward Paris startups** (best
interview + visa odds), then Brussels/Geneva/London startups, then big AI/tech as
nice-to-have. Each entry: `{ name, ats_type, ats_slug, hq_city, is_startup }`. Adding a
company is a one-line change. The seed list will be validated during implementation
(only companies whose ATS endpoint actually resolves are kept).

## 7. Testing

- **Adapters:** parse saved sample JSON fixtures → normalized `Job` (offline, deterministic).
- **Ranker:** known CV + job pairs → expected relative ordering.
- **Flagger:** description snippets → expected sponsorship label.
- **API:** queue write/read + status transitions against a temp SQLite DB.
- No network required for the test suite.

## 8. How the owner runs it

1. `./run.sh` → harvests, starts API + dashboard at `localhost:5173`.
2. Browse/sort/filter jobs; click **Queue** on the promising ones.
3. In a terminal in the repo: `claude` → `/apply` (processes the queue).
4. Back in the dashboard: review generated cover letter + tailored bullets, **open apply URL**,
   submit manually, set status to `applied`.

## 9. Risks & mitigations

- **ATS endpoint drift / rate limits** → adapters are isolated + tested against fixtures;
  failures per-company are caught and logged, never abort the whole harvest.
- **Workday variability** → treated as best-effort; skipped cleanly when a tenant differs.
- **Stale/duplicate postings** → idempotent upsert + `closed` marking on disappearance.
- **Coverage limited to the list** → by design (clean > noisy); list is trivial to grow.
