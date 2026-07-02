---
name: job-scrub
description: Scan job boards for new openings matching the user's job thesis, dedupe against their tracker, and add matches to the Screening column. Use when the user says "run a job scrub", "find new roles", "look for new openings", "any new jobs today?", or when a scheduled daily scrub fires.
---

# Job scrub

Find newly posted openings that fit the user's thesis, then (1) write a dated review file and (2) append genuinely new roles to the tracker.

## Ground rules
- `<root>` is the user's job-hunt folder (contains `Job-Thesis.md` and `Job Tracker App/data.json`). If unknown, ask, or locate with: `find ~ -maxdepth 4 -name data.json -path '*Job Tracker App*'`.
- `data.json` is the ONLY data store. Never modify `index.html`. Never create `.bak` files. If the app folder is a git repo, commit changes; if not, skip git silently — it is optional.
- Never fabricate listings. If zero new roles, say so.

## Step 1 — Read the thesis
Read `<root>/Job-Thesis.md`. It defines Tier A (weight highest), Tier B (stretch — surface only when its stated conditions are met, and flag it), Tier C (IC targets), plus arrangement, company-size, comp-floor, and industry constraints. Judge every result against it, including its "background reality check" — do not surface roles that oversell the user.

## Step 2 — Search
Run several searches per tier (Tier A phrasings first) across:
- Any connected ~~job boards connectors (Indeed, ZipRecruiter, Dice, etc.)
- Public boards via web search/fetch: Google Jobs, We Work Remotely, Built In (best comp data), Wellfound (often login-gated — skip gracefully), and any boards named in the thesis (e.g., Idealist for mission-driven).
Prefer postings from the last 1-3 days. Keep apply URLs intact; tag each role with its true source. Verify remote eligibility and comp against the thesis rather than trusting board filters; flag uncertainties instead of dropping roles silently.

## Step 3 — Dedupe (critical)
Match on company + role, case-insensitive, against every entry in `data.json`, recent `New-Openings-*.md` files in `<root>`, and duplicates within today's results (keep the source with the cleanest URL/comp). Quality over quantity.

## Step 4 — Write the review file
`<root>/New-Openings-YYYY-MM-DD.md`: short intro, then a table per tier (Company | Role | Comp | Notes | Link), flags for anything to verify, and an honest "Reality check" paragraph at the end.

## Step 5 — Append to data.json
Read, parse, append, write valid JSON preserving all existing entries. New entry shape:
```json
{ "id": "app-XXX (continue after current highest)", "company": "", "role": "",
  "location": "", "arrangement": "Remote|Hybrid|Onsite", "url": "<apply link>",
  "dateApplied": "", "status": "Screening", "resumeVersion": "", "coverLetter": "",
  "contact": "", "lastContact": "", "nextFollowup": "", "salary": "",
  "excitement": "", "notes": "<tier + verify flags>", "source": "<board>" }
```
Status exactly `"Screening"`. VALIDATE after writing: JSON parses, length grew by exactly the appended count, no pre-existing entry changed. Then best-effort: `git -C "<root>/Job Tracker App" add data.json && git commit -m "job-scrub: add N roles"`.

## Step 6 — Report
How many new roles, the Tier A standouts, link to the review file. New roles appear in the app's Screening column on next load.
