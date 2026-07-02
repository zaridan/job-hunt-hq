# Job Hunt HQ

A complete, local-first job-hunt system for Claude Cowork. Your data never
leaves your computer: a kanban tracker app lives in a folder you own, and
Claude skills do the legwork around it — finding openings that match *your*
thesis, watching your inbox for replies, and tailoring your resume and cover
letter for every role you decide to chase.

## What you get

**The tracker app** (`app/`) — a single-page kanban board (Screening →
To Apply → Applied → Phone Screen → Interviewing → Offer) backed by one
`data.json` file on your disk. A tiny stdlib-Python local server gives it
atomic saves, rolling backups, and opens job links in your default browser.
No accounts, no cloud, no build step. Works standalone even without Claude.

**Five skills:**

| Skill | What it does |
|---|---|
| `setup-job-tracker` | Installs the app into your folder, interviews you to build your Job Thesis and Master Resume, offers the automations |
| `job-scrub` | Searches job boards for new roles matching your thesis, dedupes, adds them to Screening |
| `reply-monitor` | Scans your email for application replies and advances the matching cards |
| `generate-docs` | Tailors a resume + cover letter (.md + .docx) for each To Apply role, from the real posting |
| `docs-cleanup` | Archives materials for roles you've finished applying to |

## Getting started

The smoothest path, as field-tested:

1. Install the plugin (download the `.plugin` file from Releases and open it
   in Claude, or via Settings → Capabilities).
2. In Claude's Cowork mode, create a **new project** and select a folder for
   it — that folder becomes your job-hunt home.
3. Say **"set up my job tracker"**. That's it — no other instructions needed.

Setup takes about 15 minutes — most of it the interview that builds your Job
Thesis, the honest, tiered definition of what a "fit" means for you. Every
automated search and every tailored document is judged against it. When it
finishes, the tracker opens on its own; from then on you launch it from its
icon.

**No Claude?** The tracker app works standalone: run
`python3 app/install.py --target <your folder>` and use the launcher it
creates. You'll manage cards by hand; see `app/README.md`.

## The loop

New roles land in Screening (daily scrub or on demand) → you drag keepers to
To Apply → documents get generated → you apply and move the card → replies
advance it automatically. You do the judgment; Claude does the legwork.

## Connectors

Optional but recommended — see `CONNECTORS.md`. Job-board connectors
(Indeed, ZipRecruiter, Dice) improve the scrub; an email connector (Gmail,
Outlook) is required only for the reply monitor.

## Honesty by design

Two guardrails run through every skill: documents are never written against
a posting Claude couldn't actually read, and nothing is ever added to your
resume that isn't in your master copy. The Job Thesis includes a "background
reality check" so searches target roles your track record actually supports.

## License

MIT — © 2026 Zaridan (TJ Baker)
