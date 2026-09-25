# Application preferences — Marouan Ben Hmed

These rules govern how `/apply` and `/answer` write cover letters, motivation letters and
short-form answers. Committed as the owner's default; a local `preferences.md` at the repo root
overrides it.

## Cover-letter voice
- First person, natural and direct. Confident, human, not corporate.
- **No generic openers** ("I am writing to apply for…"), no clichés, no buzzword soup, **no bullshit**.
- Lead with **who you are and how you think** (autonomy, curiosity, depth, end-to-end ownership), not a résumé recap.
- **Do not over-tailor and do not list all your experiences.** Pick at most **1-2** concrete, relevant points, or none if the personality angle is stronger. Quality over coverage.
- **Keep it short: ~120-200 words.** Tight, no padding.
- **Match the language of the job posting** (French posting means a French letter; English posting means an English letter). Default: English for international roles, French for French-speaking postings.
- **Never mention nationality or visa/sponsorship** in the cover letter or short-form answers. Track sponsorship only in the per-job "Sponsorship note", kept out of anything the employer reads first.
- **Never sound defensive, apologetic, or afraid of a bigger/more senior role.** No "I'm earlier in my career", no hedging about the title. Frame a stretch as ambition and capability, always confident.
- **Stay a bit general about the company.** Do NOT pretend to know it inside-out or quote its blog/values/team names back at it. Over-specific "research" reads as an automated cover letter to HR, which hurts. One light, genuine nod to what the company does is enough; spend the words on how you think and work.
- **Do NOT showcase weakness in the letter.** Never name a specific tool or framework you haven't used in the cover letter or short-form answer. Talk about the strengths and transferable patterns you bring; skill gaps belong only in the per-job "Match analysis → Gaps". A broad, confident line about a *domain* being new and motivating is fine; naming a missing *tool* is not.
- **No em dashes.** Use commas, periods, colons, or parentheses instead.

## What defines me (raw material, not a script to recite)
- Final-year computer engineering student at ENIT (Tunis) working where red teaming meets software engineering: most of what I do ends up as a tool or a lab other people can run.
- Cloud and identity attacker first: Azure, Entra ID, managed identities and on-prem Active Directory. I built Fenrir (Azure managed-identity attack-path CLI, 146 tests) and a hybrid AD + Entra ID red team range with Mythic C2, Evilginx and redirectors, then ran a full chain from AiTM phishing to a Golden Ticket.
- I go from finding to proof: a white-box assessment that caught an RCE before a platform went live, and a triage-validated broken-access-control report in Grafana's VDP.
- Consistent and competitive: Top 5 nationally on HackTheBox (70+ machines, Puppet Pro Lab), HTB University CTF 77/1200 in 2025.
- I publish what I learn (m0rgxn.me) and build things for others, like the CTF infrastructure and web challenges at Securinets ENIT.

## Motivation letters (master's programmes and scholarships)
- Same voice rules as cover letters, ~300-450 words unless the programme sets a limit.
- Structure: what I work on and why, what I have already built (1-2 concrete points), what this programme adds that I can't get on my own, and what I'll do with it afterwards.
- Mentioning nationality/home country is fine here when the scholarship targets it (e.g. programmes for Tunisian, African or MENA students). Never in job applications.

## CV tailoring
- **Minimize changes. Keep the CV essentially as-is.**
- Only suggest a tweak if something is clearly misaligned with the role; otherwise output exactly: **"No CV changes needed."**
- Never rewrite bullets wholesale, never keyword-stuff, never invent experience.

## Reference cover letter (match THIS voice)

> Most of my work starts as an attack and ends as a tool. This summer at Keystone Group I researched privilege-escalation paths through Azure RBAC, managed identities and service principals, and extended attack-path tooling to model them, validating every edge on a live tenant. That work grew into Fenrir, an open-source CLI that automates the managed-identity attack chain end to end.
>
> I like owning the whole path. On my own hybrid Active Directory and Entra ID range I went from an AiTM phishing session to Global Administrator, into the on-prem domain and a Golden Ticket, then wrote it up so others could reproduce it.
>
> I'm looking for a team where offensive work is taken seriously and engineering matters as much as the exploit. I learn fast, I document what I find, and I'd like to bring that to your red team for my end-of-studies internship.

### Reference "What brings you to apply?" answer (short-form, same voice)

> I want to spend my end-of-studies internship on real offensive engagements, not labs alone. I've already built cloud attack tooling (Fenrir) and run full AD and Entra ID chains on my own range, and I reported a validated vulnerability to Grafana. Your team works on exactly the kind of problems I keep choosing in my free time, and I'd like to learn from people who do it at a higher level.
