---
name: reply-monitor
description: Scan the user's email for replies to job applications and advance the matching tracker cards (Phone Screen, Interviewing, Rejected, etc.). Use when the user says "check for job replies", "any word from companies?", "scan my email for application updates", or when a scheduled reply monitor fires. Requires an email connector.
---

# Reply monitor

Find application replies in ~~email and update the tracker to match. Read-and-update only — never send email or take irreversible action.

## Ground rules
- `<root>` is the user's job-hunt folder; `<root>/Job Tracker App/data.json` is the ONLY data store. Never modify index.html; no .bak files. Git commits are best-effort and optional — skip silently if git is unavailable.
- Requires a connected ~~email connector (see CONNECTORS.md). Without one, tell the user and stop.
- WRITE PATH: if the tracker server is running (`curl -s -m 2 http://localhost:8787/health` returns ok — check from the host if your shell is sandboxed), an open tracker tab will re-POST its in-memory array on the user's next board action, silently clobbering direct disk edits. When the server is up, write THROUGH it: GET `/data.json`, mutate the array, POST the FULL array to `/save` (Content-Type: application/json), and tell the user to refresh the tracker tab (Cmd-R) before touching the board. Only edit data.json directly when the health check fails.

## Steps
1. Read `data.json`. Roles "in play" (can receive replies): status Applied, Phone Screen, Interviewing, or Offer.
2. Search ~~email for the last ~2 days: (a) company names of in-play roles; (b) common ATS domains: greenhouse.io, lever.co, ashbyhq.com, rippling.com, myworkday.com, icims.com, smartrecruiters.com, workable.com, jobvite.com. Read full bodies of hits.
3. Classify each genuinely relevant message: which company/role; interview request, scheduling, assessment, recruiter outreach, or rejection.
4. Update matched entries ONLY (company + role, case-insensitive). Set `status` to exactly one of: "Phone Screen", "Interviewing" (scheduling/assessments/ongoing), "Offer", "Rejected", "Closed". Leave "Applied" for automated acknowledgements with no human next step. Set `lastContact` to today (YYYY-MM-DD), set a sensible `nextFollowup` if action is needed, and append a short dated note to `notes` (never delete existing note text). Preserve every other field and entry.
4b. Follow-up sweep (no email needed): scan entries with status "Applied". Any with `nextFollowup` <= today, or 14+ days silent since `dateApplied` (no newer `lastContact`), goes in the report under "Needs a nudge" — company, role, dateApplied, days silent — then bump its `nextFollowup` +7 days so it isn't re-flagged daily. At 21+ days silent, recommend marking it Ghosted (never change the status yourself). Set `nextFollowup` = `dateApplied` + 7 for any Applied entry missing one.
5. VALIDATE: JSON parses, array length unchanged, only intended entries differ. Best-effort: `git -C "<root>/Job Tracker App" add data.json && git commit -m "reply-monitor: <summary>"`.
6. Report a digest: company, role, what they said, recommended next action; offer to draft any needed reply (but never send). One line if nothing new.
