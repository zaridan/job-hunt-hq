# Changelog

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
