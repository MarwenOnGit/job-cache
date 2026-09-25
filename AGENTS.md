# AGENTS.md — job cache

Shared instructions for coding agents (Claude Code, OpenCode, and any other agent
that reads `AGENTS.md`). This file plus `.claude/commands/` and `.opencode/command/`
let the same commands work across agents.

## What this project is

A local, keyless job-search + assisted-application tool. A Python/FastAPI backend
harvests security jobs from free public job-board APIs, ranks them against the
user's CV, and hands selected jobs to an AI coding agent (you) through a file
queue. **You** draft the application materials; the user reviews and submits.
The search is tuned for an **offensive-security / red-team** profile looking for
a **PFE (end-of-studies) internship or junior role** — see `cv/cv.md` and
`preferences.md`.

## The file handshake (how the app talks to you)

- The dashboard writes `queue/pending/<job_id>.json` — each holds the job, the
  user's CV (`cv_markdown`), voice rules (`preferences_markdown`), and instructions.
- You write results under `applications/<company-slug>/`:
  `cover-letter.md` (one per company), `<job_id>.md` (per-role notes), and
  `cv.md` only when the base CV needs tailoring — then delete the pending file.
- Application-form questions arrive as `queue/questions/pending/<id>.json`; you
  answer to `queue/questions/answered/<id>.md` and delete the pending file.
- The backend polls these folders and updates the dashboard.

## Commands

| Command | What it does | Canonical instructions |
|---|---|---|
| `/apply`   | Draft cover letters + per-job notes for queued jobs | `.claude/commands/apply.md` |
| `/answer`  | Answer queued application-form questions | `.claude/commands/answer.md` |
| `/onboard` | Generate `preferences.md` from CV + onboarding form | `.claude/commands/onboard.md` |
| `/setup`   | Install and launch the app | `.claude/commands/setup.md` |

The `.claude/commands/*.md` files are the single source of truth; the
`.opencode/command/*.md` files are thin wrappers that defer to them, so behavior
is identical whichever agent runs the command.

## Rules for generated materials

- Write in the user's voice per `preferences.md`: first person, direct, confident,
  no clichés, no em dashes, no defensive hedging.
- Ground everything in the real CV (offensive security, cloud/identity, tooling,
  CTF, CVE/VDP research). **Never invent experience or claim an unused tool.**
- Match the posting's language (French posting → French letter).
- The user needs visa sponsorship: track it only in the per-job "Sponsorship note",
  never in anything an employer reads first.

## Repo conventions

- Backend: Python 3.9+, stdlib + FastAPI/uvicorn/PyYAML only, no other deps.
- Tests: `cd backend && python -m pytest tests`. Keep them green.
- Personal data (`cv/cv.md`, `preferences.md`, `applications/`, `queue/`, the DB)
  is gitignored — never commit it.
