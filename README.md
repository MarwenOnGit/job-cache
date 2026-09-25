# job cache

A local, **fully free** job-search + assisted-application tool tuned for
**offensive-security / red-team** roles (pentest, red team, AppSec, cloud security,
SOC/DFIR) — **PFE end-of-studies internships and junior roles** — across **Europe,
North America, and remote worldwide**. It aggregates real postings from free public
job-board APIs, ranks them against your CV, and — with **no API keys and no paid
services** — drafts tailored application materials using an **AI coding agent running in
your terminal** (**Claude Code** or **OpenCode**) as the engine.

> Assisted apply, not auto-apply: the tool finds, ranks, and drafts; **you** review and
> submit. No scraping of LinkedIn/Indeed, no bots, no bans.

## How it works

```
Harvester (free)  →  SQLite  →  Dashboard  →  you select jobs  →  queue/pending/*.json
                                                                          │
        dashboard shows materials  ←  queue/done/*.md  ←  Claude Code (/apply) reads
        → you review & click Apply                         CV + job → cover letter,
                                                            tailored bullets, fit analysis
```

The "AI" is you running `claude` (Claude Code) or `opencode` in this repo. The app and Claude Code talk through the
`queue/` folder — so there's nothing to pay for and no key to manage.

## Quick start

```bash
./run.sh
```

That's it. On first run it creates a virtualenv, installs dependencies, harvests jobs, and
opens the dashboard at <http://localhost:8000>. (Port busy? `PORT=8080 ./run.sh`.)

**First run — onboarding.** A new user gets a welcome form: paste or upload your CV, pick your
target cities / experience / role types / cover-letter language, and add a note on how you want
to sound. Then run **`/onboard`** in Claude Code and it writes your personal `preferences.md`
(voice rules + a reference cover letter drawn from your CV). Your CV and preferences live only on
your machine (see [Your data](#your-data)).

Then:
1. Browse / filter / sort ranked jobs.
2. Click **Queue for Claude** on the ones you like.
3. In a terminal in this repo: `claude` (Claude Code) or `opencode`, then run `/apply`.
4. Back in the dashboard, review the generated cover letter + CV bullets, click **Open
   apply page**, submit, and set the status.

### Starting over

`./reset.sh` wipes every harvested job, the decision log and the learned model, then
searches again from `profile/profile.yaml`. Your CV, `preferences.md`, `applications/`
and the queue are kept. (The first launch after this update does this once automatically.)
Only internship, junior and mid-level roles asking for at most 3 years are stored.

## Data sources

Two complementary, entirely keyless layers, both configured in [`companies.yaml`](companies.yaml):

- **Curated single-company ATS boards** — Greenhouse, Lever, Ashby, SmartRecruiters,
  Workable, and best-effort Workday — for the ~70 employers you specifically care about
  (security vendors, pentest consultancies, and big-tech security orgs). Adding one is a single line.
- **Keyless aggregators** — Remotive, Arbeitnow, Jobicy, Himalayas, RemoteOK, and The Muse.
  Each source fans out to *hundreds* of employers in one call, so the search is wide out of
  the box (a fresh harvest of just the aggregators pulls ~900 relevant EU/remote roles across
  ~500 companies). Tune their params (region, category, pages) or comment any out.

No scraping, no ToS risk. Sources that stop resolving are skipped and reported in the summary.

## What you search for

Your **search preferences** — locations/countries, role families, target job titles,
keywords, experience, language — drive both what gets harvested and how it's ranked. Edit
them any time in **Profile → Search preferences** (no need to re-onboard). Leave any group
empty to include everything, which is the broadest possible search.

## Ranking & flags

- **Match score** (free heuristic): skills overlap with your CV + role-family fit + recency.
- **Experience fit**: detects seniority + required years; the default view hides senior/staff/
  principal roles and anything needing >5 years. Toggle to “All levels” anytime.
- **Sponsorship flag**: `likely_sponsors` / `silent` / `no_sponsorship` — a *hint*, never a
  filter (you can apply even when sponsorship is unstated).
- **Startup / city tags** for quick filtering toward the highest-odds roles.

## Dashboard

A keyboard-first, single-page app (dark **and** light themes) with a left sidebar:

- **Overview** — a greeting, key tiles (jobs that fit, ready to review, applied, starred),
  your top picks *for you*, and a pipeline funnel.
- **Jobs** — browse / filter / search / sort (default **For you**), star, take notes, queue
  for Claude, or dismiss. Every job shows both its match score and its learned *for-you* score.
- **Queue** — jobs handed to Claude + materials waiting for your review (inline **Mark as
  applied**), plus an **Application Q&A** chat: paste any question a form asks (e.g. "describe a
  full-stack project you made") and Claude drafts the answer in your voice from your CV. Type
  **`@`** to reference any job you've generated materials for (e.g. `@Wise @Dataiku`) — Claude then
  has that role's context *and its generated materials* (cover letter, answers) to draw on, so you
  can say things like "@Wise rewrite this as a cover letter" or "combine my @Wise and @Dataiku
  angles". Ask in the app, run `/answer` in Claude Code, and the answer appears with a copy button
  (same file-handshake as `/apply`, no API keys).
- **Applications** — your tracker (*Applied → Interviewing → Offers → Closed*) + **CSV** export.
- **Insights** — *what the model has learned about you* (see below).
- **Profile** — your **Search preferences** (locations/countries, role families, target
  titles, keywords, experience, language — with a **Save & re-harvest** button), plus view
  **and edit** `cv/cv.md` and your application-voice `preferences.md` right in the app.

**Command palette** (`⌘K` / `Ctrl+K`): jump to any page, search jobs, run commands.
**Shortcuts**: `g` then `o/j/q/a/i/p` for pages · `j/k` move · `s` star · `e` queue · `x`
dismiss · `/` search · `?` help.

### Apply workspace

Open any job's **Apply workspace** for a split screen: your generated materials with
**copy-to-clipboard** (whole cover letter, each paragraph, and each form answer) on the left,
and the **live apply page embedded in an iframe** on the right — copy on one side, paste on
the other. Pages that block embedding (some SPA ATSs) fall back to **Direct** / **Pop out**.

### The learning model

job cache learns your taste from your own decisions — no LLM, pure stdlib, zero setup. Every
time you queue, apply, star (positive) or dismiss / reject (negative) a role, it updates a
smoothed log-odds model over the job's features (role family, city, seniority, company,
startup-vs-big, sponsorship, and title/skill keywords). It then:

- powers the **For you** sort (base relevance fused with learned taste once it has enough
  signal),
- explains **why** it rates each job (the exact features pushing the score up or down), and
- surfaces aggregate **Insights**: what you pursue, what you pass on, your pursue-rate, and
  activity over time.

It starts as *"still learning"* and sharpens the more you use it.

## Your data

**The repo is the app; your data is yours and stays local.** Your CV (`cv/cv.md`), your
`preferences.md`, everything under `applications/`, the `queue/`, the SQLite DB, and the learned
model are all **gitignored** — they never get committed. The dashboard listens on loopback only
(`127.0.0.1` / `::1`), so other machines on your network can't reach it, and its API refuses
requests from other websites. The repo ships example templates
(`cv/cv.example.md`, `preferences.example.md`) so a fresh clone knows the format.

To move machines, back up, or share: **Settings → Export everything** writes one JSON file with
your CV, preferences, decisions, generated cover letters + notes, Q&A, and settings. **Import**
restores all of it. A friend just clones the repo, runs `./run.sh`, and onboards with their own CV.

## What gets saved (locally)

`/apply` groups queued jobs **by company** and writes to `applications/<company>/`:
`cover-letter.md` (one letter reused across that company's roles), `cv.md` (only if the base CV
needs changes), and `<job_id>.md` per-role notes. These are your working record on disk (not in
git); `applications/applications.csv` tracks status. Export them any time from Settings.

## Stack

Python **FastAPI** + **SQLite** + a **no-build** vanilla-JS dashboard. The only requirement
is **Python 3.9+** — deliberately no Node/React build step so it installs anywhere in one
command.

## Layout

```
companies.yaml            # curated company ATS boards + keyless aggregator sources
cv/cv.example.md          # CV template (your real cv/cv.md is gitignored)
preferences.example.md    # preferences template (your real preferences.md is gitignored)
backend/                  # FastAPI app, harvester, ranker, flagger, seniority, tracker, learn, prefs, adapters, tests
  prefs.py                # structured search preferences (locations/roles/titles/keywords)
  learn.py                # the preference-learning model (pure stdlib)
  serve.py                # dual-stack launcher (localhost over IPv4 + IPv6)
frontend/                 # vanilla-JS dashboard (Overview / Jobs / Queue / Applications / Insights / Profile / How-to-use)
queue/pending/            # the Claude Code trigger (job selections) — gitignored
applications/             # your generated materials per company — gitignored
data/                     # SQLite DB, model.json, config.json, onboarding.json, preferences.json — gitignored
queue/questions/          # Application Q&A handshake (pending/*.json -> answered/*.md) — gitignored
.claude/commands/         # /onboard (new user), /apply (materials), /answer (questions), /setup (install)
run.sh · install.sh       # one-click launch / setup
```

## Tests

```bash
./install.sh && source .venv/bin/activate
python -m pytest backend/tests -q      # or: python -m unittest discover backend/tests
```

Tests run fully offline against saved ATS fixtures.

## Notes

- Everything is local; the SQLite DB and queue files are gitignored.
- Companies whose ATS endpoint doesn't resolve are skipped and reported in the harvest
  summary — grow or prune `companies.yaml` freely.
