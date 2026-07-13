#!/usr/bin/env python3
"""Nightly tidy: move a company's application folder into Applications/Archive/
once all of that company's roles are applied (or further along) and none are
still active, so the working Applications/ list stays short.

Rule (per company, matched on the Applications/<Company>/ folder name):
  - Archive a company's folder only if that company has at least one role at
    status Applied / Phone Screen / Interviewing / Offer AND has NO role still
    active (To Apply / Screening). This protects a shared resume + cover letter
    while any of that company's roles is still open.
  - "Won't Apply" / "Rejected" / "Closed" roles neither keep a folder active nor
    trigger archiving on their own.

Idempotent and safe to run repeatedly. Resolves the Job Hunt root relative to
this script's own location, so it works regardless of absolute path.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent            # <root>/Job Tracker App/.. = <root>
DATA = ROOT / "Job Tracker App" / "data.json"
APPS_DIR = ROOT / "Applications"
ARCHIVE_DIR = APPS_DIR / "Archive"
ARCHIVE_STATUSES = {"Applied", "Phone Screen", "Interviewing", "Offer"}
ACTIVE_STATUSES = {"To Apply", "Screening"}


def norm(name: str) -> str:
    # match generate-docs folder naming (company with "/" and ":" stripped)
    return (name or "").replace("/", "").replace(":", "").strip().lower()


def main():
    apps = json.load(open(DATA))
    archive_co, active_co = set(), set()
    for a in apps:
        co = norm(a.get("company"))
        if not co:
            continue
        if a.get("status") in ACTIVE_STATUSES:
            active_co.add(co)
        elif a.get("status") in ARCHIVE_STATUSES:
            archive_co.add(co)

    # A company is archivable only if it has applied-stage roles and no active ones.
    archivable = archive_co - active_co

    moved, remaining = [], []
    if APPS_DIR.is_dir():
        for d in sorted(APPS_DIR.iterdir()):
            if not d.is_dir() or d.resolve() == ARCHIVE_DIR.resolve():
                continue
            if norm(d.name) in archivable:
                ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                dest = ARCHIVE_DIR / d.name
                if dest.exists():
                    # merge into the existing archive folder, then drop the empty source
                    for f in d.iterdir():
                        shutil.move(str(f), str(dest / f.name))
                    d.rmdir()
                else:
                    shutil.move(str(d), str(dest))
                moved.append(d.name)
            else:
                remaining.append(d.name)

    print(f"Archived {len(moved)} company folder(s).")
    for m in moved:
        print("  archived:", m)
    print()
    print(f"Still active in Applications/ ({len(remaining)}):")
    for r in remaining:
        print("   ", r)


if __name__ == "__main__":
    main()
