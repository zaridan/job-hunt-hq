# Contributing to Job Hunt HQ

Contributions are welcome, and they don't have to be big. Fixing a typo in a
skill, improving a prompt, or reporting a confusing moment during setup all
count.

## The short version

1. **Found a problem or have an idea?** [Open an issue](https://github.com/zaridan/job-hunt-hq/issues).
   Plain language is fine — "the setup asked me the same question twice" is a
   great bug report.
2. **Want to change something?** Fork the repo, make your change on a branch,
   and open a pull request. Direct pushes to `main` are disabled — everything
   lands through PRs, including small ones.
3. That's it. No CLA, no template maze. A sentence or two in the PR about
   what changed and why is plenty.

## What's especially welcome

- **Skill improvements** — the automations are plain-English instructions in
  `skills/*/SKILL.md`, so you can contribute without writing code. Better
  phrasing, new job boards for the scrub, sharper guardrails.
- **Tracker app fixes** — `app/index.html` (the board) and `app/server.py`
  (the tiny local server).
- **Windows and Linux testing** — the launcher paths are the least-exercised
  part of the project.
- **Docs** — anything that confused you probably confuses others.

## Ground rules (there are only three)

1. **Zero dependencies stays zero.** The app is one HTML file and
   stdlib-only Python. PRs that add npm, pip packages, or build steps will
   be asked to find another way.
2. **Local-first stays local-first.** No telemetry, no network calls except
   the ones the user explicitly drives, nothing leaves the user's machine.
3. **It never applies for the user.** No auto-submit features, ever — that's
   a core promise, not a missing feature.

## Testing your change

- App changes: run `python3 app/server.py` from a scratch folder and click
  around the board.
- Skill changes: read your edit out loud — skills are instructions for
  Claude, so clarity is correctness. If you have Claude Code:
  `claude --plugin-dir . ` loads the plugin locally, and
  `claude plugin validate .` runs the structural check.

Thanks for helping make the job hunt a little less lonely.
