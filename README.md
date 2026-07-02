# Job Hunt HQ

A complete, local-first job-hunt system for Claude Cowork. Your data never
leaves your computer: a kanban tracker app lives in a folder you own, and
Claude skills do the legwork around it — finding and fit-scoring openings
against *your* thesis, watching your inbox for replies, and tailoring your
resume and cover letter for every role you decide to chase.

Job Hunt HQ makes you faster and more thorough — but you stay the one who
applies. See "What it doesn't do" below.

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
| `job-scrub` | Searches job boards for new roles, fit-scores each 0–100 against your thesis, captures the posting text, adds them to Screening (sorted by fit) |
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

## What it doesn't do

- **It never applies for you.** No auto-submitting applications, no posting
  your resume to boards, no sending email on your behalf. Recruiters can
  tell when applications are automated, and it burns your credibility. Every
  application is you, clicking submit.
- **It doesn't replace your judgment.** Fit scores are a triage aid, not a
  verdict — you decide what's worth chasing.
- **Its drafts are drafts.** Always proofread the generated resume and cover
  letter before submitting. They're built only from your master resume and
  the real posting, but you own every word that goes out under your name.
  Read them the way you'd read anything with your signature on it.

## Make it yours

There are no settings screens — the whole system is plain files and skills
Claude can read and edit, so you customize it by asking. After setup, try
things like:

- **Change what "a fit" means:** edit `Job-Thesis.md` yourself, or say
  "update my job thesis — I'm now open to hybrid in Denver" and every future
  scrub and document follows suit.
- **Add job boards:** "also cover Otta and RemoteOK in my job scrub" — the
  scrub is instructions, not code, so new sources are one sentence.
- **Tune the cadence:** "run the scrub twice a day" or "pause the reply
  monitor while I'm on vacation."
- **Shape the documents:** "keep my cover letters under 250 words" or "always
  lead my resume with the platform-migration story."
- **Extend the tracker:** "add a Referrals column to the board" or "track
  which applications came from referrals" — the app is one readable HTML
  file, and Claude can modify your copy safely (it's git-versioned).

If a customization works well, it persists — the files are the memory.

## License

MIT — © 2026 Zaridan (TJ Baker)
