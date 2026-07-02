---
name: setup-job-tracker
description: Set up the Job Hunt HQ system — install the local tracker app into the user's folder, build their personal job thesis and master resume, and optionally wire up automations. Use when the user says "set up my job tracker", "install job hunt hq", "start my job hunt", "get me set up for job hunting", or has just installed this plugin and asks how to begin.
---

# Set up Job Hunt HQ

Install the tracker app into a folder the user owns, then personalize the system around them. Everything downstream (job-scrub, generate-docs) depends on the two files this skill creates: `Job-Thesis.md` and `Resume/Master-Resume.md`.

## Step 1 — Pick the home folder

If a folder is already connected to this session/project, DEFAULT to it: confirm with one question ("I'll set everything up in <folder name> — good?") rather than asking the user to pick a folder from scratch. Only if no folder is connected, ask where the job hunt should live (suggest `~/job-hunt`) and request access. Create this structure:

```
<root>/
├── START-HERE.md
├── Job-Thesis.md
├── Job Tracker App/          (the app — copied in Step 2)
├── Resume/
│   ├── Master-Resume.md
│   └── Tailored/
├── Cover Letters/
│   ├── Cover-Letter-Template.md
│   └── Tailored/
├── Company Research/
│   └── Company-Research-Template.md
└── Job Listings/
```

## Step 2 — Install the app (run the script — do NOT hand-build)

The entire deterministic install is one command. Determine the user's host OS (mac, windows, or linux — from context or one question), then run:

```
JOBHUNT_HOST_OS=<mac|windows|linux> python3 "${CLAUDE_PLUGIN_ROOT}/app/install.py" --target "<root>"
```

The script creates the folder structure, copies the app files, creates an empty data.json, and drops a launcher-maker in `<root>`. It prints a JSON summary — read it and confirm `created` lists the app files (or `skipped` on re-runs) and `launcher` is set. Do not create folders, copy files, or improvise placeholder files (like .gitkeep) yourself; the script is the install.

Then activate the one-click launcher BY DEFAULT: on macOS, if host-control tools are available, run the generated "Make Job Tracker Launcher.command" for the user; otherwise tell them (one plain sentence) to double-click it once in their folder. Windows/Linux: the script already dropped the shortcut. The launcher icon is how the user opens the tracker from now on — never by terminal.

Git is OPTIONAL — if available, init a repo in `Job Tracker App/` only and commit; if not, skip silently (the server keeps rolling backups regardless).

Port note: the tracker server uses port 8787; if another instance already owns it on this machine, bake `--port <free port>` into the launcher shim.

## Step 3 — Build the Job Thesis (the most important step)

Interview the user, then write `<root>/Job-Thesis.md` from `${CLAUDE_PLUGIN_ROOT}/skills/setup-job-tracker/assets/Job-Thesis-Template.md`.

Interview mechanics (follow exactly):
- BATCH questions into at most two grouped rounds using a multi-question form (the question tool supports several questions per call) — never a long series of one-question turns. Round 1: background + target roles. Round 2: constraints (arrangement, company size, comp floor, industries, dealbreakers).
- Track what has been answered. NEVER re-ask a question that has an answer. If the user picks "Other"/"I'll type it" and provides text, that text IS the answer — do not show the same question again.
- Only follow up on a specific answer when it fails the sanity check below, and phrase it as a follow-up ("You said $10K — did you mean $100K?"), not a repeat of the original question.

Cover:

- Target roles in tiers: Tier A (primary fit — roles they're most competitive for), Tier B (stretch — wanted but needing honest flagging), Tier C (solid individual-contributor targets). Push for honesty: the thesis works only if Tier A reflects what their track record actually supports, not aspiration. Ask what they've *actually* run/built/led vs. been adjacent to.
- Arrangement (remote/hybrid/onsite + location), company size/stage preference, compensation floor (plus any mission-driven exception), industries to favor or avoid, and dealbreakers.

Sanity-check answers as they come in: an implausible value (a "$10K" comp floor, an empty Tier A, a location that contradicts "remote only") gets one friendly follow-up question, not silently written into the thesis.

## Step 4 — Build the Master Resume

If the user has a resume (any format), convert it into `Resume/Master-Resume.md` — complete history, everything included (tailored copies trim from it). If they don't, interview them role-by-role. Copy `assets/Cover-Letter-Template.md` and `assets/Company-Research-Template.md` into their folders, filling in the user's name and contact details. Write `START-HERE.md` from `assets/START-HERE-Template.md`, adapted to their setup.

## Step 5 — Offer the automations (optional, each independently)

1. **Daily job scrub** — a scheduled task (suggest 7 AM) running the `job-scrub` skill's workflow against their thesis.
2. **Reply monitor** — a scheduled task (suggest 8 AM) running the `reply-monitor` workflow. Requires an ~~email connector; check `${CLAUDE_PLUGIN_ROOT}/CONNECTORS.md`.
3. **Tailored docs** — either a scheduled sweep or an on-demand artifact: create an ad-hoc scheduled task from the `generate-docs` workflow, then a pinned artifact page whose button triggers it via `runScheduledTask`.
4. **Nightly docs cleanup** — scheduled task (suggest 10 PM) running `Job Tracker App/cleanup_applied.py`.

For any scheduled task created, write the prompt to be fully self-contained (each run has no memory): include the user's folder paths and the rules from the corresponding skill in this plugin. Recommend the user click "Run now" once per task to pre-approve its tools.

## Step 6 — Hand off

Launch the app FOR the user (open the launcher created in Step 2; don't tell them to run anything). Confirm the status chip reads "data.json · server-synced".

The handoff message must pass the non-technical-reader test:
- Plain language only. NO terminal commands, no `cd`, no `python3`, no ports, no localhost URLs, no escaped file paths. "Open Job Tracker from your Applications folder / desktop icon" is the only launch instruction that should ever appear.
- No implementation details (servers, JSON, sync, backups). One reassurance sentence is allowed: "Everything lives in your <folder> folder on your computer — nothing goes to the cloud."
- Keep it short: what got set up (in their words — "your board", "your resume file"), the loop in 3-4 plain sentences (new roles appear in Screening → drag the ones you like to To Apply → documents get written for you → apply and drag the card along), and ONE clear next action, not a week-by-week plan.
- If the user seems technical (they asked about ports, git, code), match their level instead — this rule is about defaults, not ability.

## Step 7 — Self-check (run before sending the handoff)

Verify every line; fix anything that fails before finishing:
1. install.py's JSON summary showed the app files present and a launcher created.
2. `<root>/Job-Thesis.md` exists, has no unfilled [BRACKETS], and contains no implausible values you failed to question.
3. `<root>/Resume/Master-Resume.md` exists and reflects the user's actual history.
4. The launcher exists (or the one-sentence double-click instruction was given).
5. Your handoff message contains no terminal commands, paths with backslash escapes, ports, or localhost URLs (unless the user is technical).
6. You did not create any files beyond: the script's output, the four documents/templates, and START-HERE.md.
