# Job Tracker

A local-first job-application tracker. One HTML file, an optional tiny local
server, no build step, no account. Your data lives on your own computer.

## Quick start

**Simplest (browser-only):** open `index.html` in any modern browser. Edits
save to that browser's storage. Good for trying it out or GitHub Pages hosting.

**Recommended (server mode):** run `python3 server.py` (stdlib only, no
installs) and open http://localhost:8787. Now `data.json` on disk is the
single source of truth — every edit is written to it atomically, with rolling
backups (last 20 of each file kept). The status chip shows
`🖥 data.json · server-synced`.

**Where the data lives:** not in this folder. `data.json`, `contacts.json`
and `backups/` live in `../Data/`, next to the app, so code and data stay
apart. `storage.py` decides the folder: `TRACKER_DATA_DIR` if set, else
`../Data` if it holds `data.json`, else this folder if it still holds
`data.json` (installs from before the Data folder keep working), else `../Data`.

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
- **People tab** — the **Jobs | People** switch opens the referral pipeline
  (`contacts.json`), with its own Board and Table, stat cards, and a form to
  add, edit or delete a person. Needs server mode. The URL remembers which
  screen you're on (`#people/table`, …), so a refresh keeps your place.
  `contacts_store.py` is the command-line door the outreach skills use; it
  writes through the server when it's running. Settings (default resume,
  note length, pacing, optional request/note limits) are in
  `outreach-config.json`.

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
| `GET /data.json` | current data, never cached; `X-Data-Revision` header for conflict checks |
| `POST /save` | validates + atomically writes `data.json`, rotates a backup; a stale `X-Base-Revision` gets a 409 (the page reloads instead of overwriting a Claude run's changes) |
| `GET /contacts.json` | referral contacts for the People tab (`[]` if none), never cached; `X-Contacts-Revision` header for conflict checks |
| `POST /save-contacts` | validates + atomically writes `contacts.json`, rotates a `contacts-*` backup; a stale `X-Base-Revision` gets a 409 |
| `POST /upload-attachment?contact=&name=` | saves an uploaded resume PDF (≤10 MB) to `Resume/Uploads/<Company>/` and returns its path |
| `GET /open?url=` | opens an http(s) link in the default browser |
| `GET /reveal?path=` | shows a tailored PDF in the file manager (Finder/Explorer select the file; Linux opens its folder) for drag-and-drop into applications |
| `GET /health` | lets the app detect server mode |

Localhost-only by default, single instance (safe to invoke repeatedly),
Python 3 stdlib. Cross-platform: macOS, Windows, and Linux. The app's own
`.py` files are never served.

## Hosting it (optional)

To run it on a host like Render, listen on all interfaces and set a password:
`HOST=0.0.0.0` (or `--host 0.0.0.0`) plus `TRACKER_PASSWORD`, which turns on a
browser login (any username) for everything except `/health`. The server
refuses to listen beyond localhost without a password. `PORT` is read from
the environment.

If the host's disk doesn't survive restarts, turn on GitHub sync (the
job-hunt folder must be the repo root): set `TRACKER_GITHUB_TOKEN` (a token
that can write the repo's contents) and `TRACKER_GITHUB_REPO` (`owner/name`;
optional `TRACKER_GITHUB_BRANCH`, default `main`). The server then pulls the
latest data on start-up and before serving it, and commits every save (and
uploaded PDF) to the repo. If the repo copy changed meanwhile, the save is
refused with a 409 and the page reloads; your version is kept in `backups/`.
If GitHub is unreachable, the save stays local and is retried. Without those
variables nothing touches the network.

## Version history

The job-hunt folder works well as a git repo — `Data/data.json` diffs make a
clean audit trail of your search. `backups/`, `server.log`, and `.DS_Store` are
gitignored.

## Automation (optional, how the original setup uses it)

Claude (Cowork) scheduled tasks keep the tracker fresh by editing
`Data/data.json` (through the server when it's running) — an open tab picks
the changes up when you switch back to it:

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
