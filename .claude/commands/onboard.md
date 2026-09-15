---
description: Generate a new user's preferences.md from their CV + onboarding form
---

A new user just onboarded in the dashboard. Turn their inputs into a personal
**`preferences.md`** that governs how `/apply` and `/answer` write their cover letters.

Read:
1. **`cv/cv.md`** — their CV (the source of truth for voice, seniority, and real experience).
2. **`data/onboarding.json`** — the form they filled: `owner_name`, `cities`, `experience`,
   `roles`, `language` (english / french / both), `tone` (free-text notes on how they want to
   sound). Any field may be empty.
3. **`preferences.example.md`** — the template/structure to follow.

Then **write `preferences.md`** modelled on `preferences.example.md`, personalized to this user:
- Keep the same section structure and the universal rules verbatim (first person, direct,
  confident, no clichés, **no bullshit**, honest about gaps framed as motivating, **no em dashes**,
  never mention nationality/visa/sponsorship in employer-facing text, never sound defensive about a
  senior role, stay general about the company, don't showcase tool gaps, match the posting's
  language).
- In "What defines me", infer 3-5 truthful bullets **from their CV** (their real strengths,
  domains, and how they work). Never invent.
- Honour `tone` and `language`: if they gave tone notes, fold them into the voice guidance; set the
  language rule to their preference (english / french / both).
- Write a short **reference cover letter** (~120-180 words) and a **reference short-form answer**
  in their voice, grounded in their actual CV, as the worked example at the bottom (like the
  template's reference section). This is the single most important part: it shows the model their
  voice. Keep it honest and specific to their background.

Do **not** touch `cities`/`roles`/`experience` beyond letting them inform tone and seniority
framing (those drive filters/harvest, not the cover-letter voice).

Finish with a one-line summary. The dashboard picks up `preferences.md` automatically.
