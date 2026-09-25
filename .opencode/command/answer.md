---
description: Answer application-form questions the user asked from the dashboard — in their voice
---

Read `.claude/commands/answer.md` in this repository and follow it exactly.

That file is the single source of truth for the `/answer` workflow, shared between
Claude Code and OpenCode so both agents behave identically. Do what it says, using
your file read/write tools to work with the `queue/`, `applications/`, `cv/` and
`preferences.md` paths it references.
