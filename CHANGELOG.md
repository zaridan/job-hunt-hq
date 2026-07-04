# Changelog

## 0.1.10 — 2026-07-04
- Tracker cards now show an "added" date (＋ date, with a relative-age
  tooltip) so you can see at a glance when a role landed in Screening.
  Manually added cards are stamped on creation.
- job-scrub: new Screening roles are stamped with `dateAdded` (the scrub run
  date) so auto-found roles carry the date too.
- Removed the "⚡ Generate docs" button from the tracker toolbar (docs are
  generated on demand from chat / the Cowork artifact; the toolbar button
  was redundant noise).

## 0.1.9 — 2026-07-04
- Tracker board: narrower-screen ergonomics for the kanban board.
  - Collapsible columns: each column header has a chevron that collapses it
    to a thin vertical strip (name + count). Collapsed strips still accept
    drops, so you can park a distant column (e.g. "Won't Apply") next to
    "Screening" and drag cards straight onto it; click a strip to expand.
  - Show/hide columns menu: a "Columns" dropdown to fully hide/show any
    column, plus "Reset columns".
  - Both collapse and hide states persist per browser (localStorage). No
    change to data.json or the existing "Hide closed & won't-apply" filter.

## 0.1.8 — 2026-07-02
- Screening-robustness pass across all three review layers:
  - ATS: explicit .docx formatting rules (single column, no tables/text
    boxes/graphics, contact info in body not header/footer, standard section
    headings, plain bullets, "Month YYYY" dates, standard fonts); canonical
    hard-skill terms with a keyword-coverage check (exact true terms present
    once, no stuffing); acronyms spelled out once.
  - LLM screening: resume/cover-letter cross-consistency check (same titles,
    dates, numbers, voice); explicit ban on hidden text, white-on-white
    keywords, and instructions addressed to AI screeners.
  - Human screening: expanded AI-register avoid-list ("delve", "testament",
    "synergy", "I am writing to express my interest", no-substance flattery);
    no mid-sentence bolding; sentence-rhythm variation; every claim must be
    interview-survivable (two minutes of unprompted detail).
  - setup-job-tracker: master-resume build rules — user's own words, verbatim
    numbers or none, canonical skill names, standard structure, adjacent vs.
    owned experience distinction.
  - Report step: remind users to rename uploads to "<First-Last> - Resume"
    (candidate name, not company, in the filename).

## 0.1.7 — 2026-07-02
- Anti-slop hardening for generated documents (includes the previously
  unreleased JD-echo pass plus a portfolio-level pass):
  - generate-docs: no lifted posting language; every claim traces to the
    master resume; numbers verbatim or not at all; banned stock openers/
    closers ("I'm writing to apply...", "I'd welcome the chance to
    discuss..."); a stock-phrase avoid-list; em-dash and rhythm checks; and
    a cross-letter check — each new letter is compared against the 2–3 most
    recent so openers, closers, and anecdote phrasing never repeat.
  - Cover-Letter-Template asset: boilerplate opener/closer removed from the
    template body; cross-letter comparison added to the send checklist.

## 0.1.6 — 2026-07-02
- Docs: first-run folder-access note — Claude asks permission to open your
  job-hunt folder during setup and again on new sessions, or the first time an
  automation or the Generate Now button runs. Approve it; a pending or expired
  prompt is the usual reason a scrub, reply check, or button "does nothing."
- Docs: how to open the tracker — just ask Claude "open my job tracker" (always
  works, even when the icon is fussy), or use the launcher icon. If the icon
  won't open, Claude can rebuild the shortcut. Added to README, the setup
  handoff, and START-HERE.
- Setup skill: the on-demand Generate Now task must stay registered as a
  manual-only ad-hoc task — deleting it to "pause" generation makes the button
  silently fail.

## 0.1.5 — 2026-07-02
- Fit score: job-scrub rates every new role 0-100 against the Job Thesis;
  the app shows the score on cards and sorts Screening by fit.
- Posting capture: the scrub saves each job description to Job Listings/,
  so document generation works even after a posting goes down;
  generate-docs reads the saved copy first.
- README: explicit no-auto-apply stance and a JobOps comparison.

## 0.1.4 — 2026-07-02
- Setup interview: batched question rounds, never re-asks answered questions,
  follow-ups reference the prior answer.

## 0.1.3 — 2026-07-02
- New `app/install.py`: the entire deterministic install is now a script, so
  setup behaves identically on every model. Idempotent; never overwrites
  user-edited files. Generates a per-platform one-click launcher-maker.
- Setup self-check rubric before handoff.

## 0.1.2 — 2026-07-02
- Handoff message rules: plain language, no terminal commands; the app is
  launched for the user. One-click launcher created by default.
- Thesis interview sanity-checks implausible answers.

## 0.1.1 — 2026-07-02
- Setup defaults to the already-connected project folder.
- Git made explicitly optional; no more .gitkeep placeholder files.
- Free-port fallback when 8787 is taken.

## 0.1.0 — 2026-07-02
- Initial release: tracker app + five skills (setup, job-scrub,
  reply-monitor, generate-docs, docs-cleanup).
