# Job Tracker

A local-first job-application tracker. One HTML file, an optional tiny local
server, no build step, no account. Your data lives on your own computer.

## Quick start

**Simplest (browser-only):** open `index.html` in any modern browser. Edits
save to that browser's storage. Good for trying it out or GitHub Pages hosting.

**Recommended (server mode):** run `python3 server.py` (stdlib only, no
installs) and open http://localhost:8787. Now `data.json` on disk is the
single source of truth — every edit is written to it atomically, with rolling
backups in `backups/` (last 20 kept). The status chip shows
`🖥 data.json · server-synced`.

**One step (any platform):** `python3 launch.py` (Windows: `py launch.py`)
starts the server if needed and opens the tracker in its own Chrome/Edge
app-style window, falling back to your default browser. On macOS,
`launch.sh` is a thin shim around it — wrap either in an Automator/app
bundle (macOS) or a desktop shortcut (Windows/Linux) for one-click launch.

## The app

- **Board view** — drag cards between stages (Screening → To Apply → Applied →
  Phone Screen → Interviewing → Offer). Moves save instantly.
- **Table view** — sortable columns, click a row to edit.
- **+ Add / Edit / Delete** — full details per application (company, role,
  status, salary, excitement, dates, contact, resume version, notes, link).
- **Search & filter** — by text or status; hide closed/won't-apply.
- **Action panel** — surfaces follow-ups due and highest-excitement
  "To Apply" roles.

## Storage modes (auto-detected, in priority order)

1. **Server mode** — when served by `server.py`, the app loads `data.json` on
   every open and POSTs every change back. Atomic writes, rolling backups, no
   permission prompts, works in every browser. Job links open in your system
   default browser (never inside an app-mode window).
2. **Linked file** — on static hosting (or `file://`), Chrome-family browsers
   can link a `data.json` via the File System Access API (**Open file** /
   **Save As file** buttons).
3. **Browser storage** — the always-on fallback; edits persist in
   `localStorage` (key `jobhunt_v1`).

**Always available:** **Export** (JSON snapshot), **Import** (restore/replace),
and **CSV** for spreadsheets.

## Server endpoints (`server.py`)

| Route | What it does |
|---|---|
| `GET /` | serves the app |
| `GET /data.json` | current data, never cached |
| `POST /save` | validates + atomically writes `data.json`, rotates a backup |
| `GET /open?url=` | opens an http(s) link in the default browser |
| `GET /reveal?path=` | shows a tailored PDF in the file manager (Finder/Explorer select the file; Linux opens its folder) for drag-and-drop into applications |
| `GET /health` | lets the app detect server mode |

Localhost-only, single instance (safe to invoke repeatedly), Python 3 stdlib.
Cross-platform: macOS, Windows, and Linux.

## Version history

The folder works well as a git repo — `data.json` diffs make a clean audit
trail of your search. `backups/`, `server.log`, and `.DS_Store` are
gitignored.

## Automation (optional, how the original setup uses it)

Claude (Cowork) scheduled tasks keep the tracker fresh by editing `data.json`
directly — the app picks changes up on next load:

- **daily-job-scrub** — searches job boards for roles matching a written
  "thesis," writes a dated review file, appends new roles as `Screening`.
- **job-reply-monitor** — scans Gmail for application replies and advances
  statuses (`Phone Screen`, `Interviewing`, `Rejected`, …).
- **nightly-tailored-cleanup** — archives a company's Applications/<Company>/ folder once all its roles are applied and none are active
  for roles that are no longer active (`cleanup_applied.py`).

Resumes and cover letters themselves are generated in chat — the app just
links to them (`resumeLink` / `coverLink` fields).

## Host on GitHub Pages (optional)

Put `index.html` in a repo, enable Pages. Visitors get their own private,
browser-local copy seeded with the demo rows. (Server mode doesn't apply on
Pages; the FS-API "linked file" mode does.)

## Seed data

`index.html` ships with three demo rows so first-time users see how it works.
Real data never lives in the HTML — it's in `data.json` (server mode), a
linked file, or browser storage.
