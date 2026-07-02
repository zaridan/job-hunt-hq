#!/usr/bin/env python3
"""
Nightly tidy: move tailored resumes & cover letters for roles that are already
applied (or further along) into an `Applied/` subfolder, so the working list of
tailored materials stays short.

Rule (per company, matched on the "Company - ..." filename prefix):
  - Archive a company's tailored files only if that company has at least one role
    at status Applied / Phone Screen / Interviewing / Offer AND has NO role still
    active (To Apply / Screening). This protects shared resumes (e.g. one Samsara
    resume used by several roles) from being archived while any of those roles is
    still open.
  - "Won't Apply" roles are ignored (left where they are).

Idempotent and safe to run repeatedly. Resolves the Job Hunt root relative to this
script's own location, so it works regardless of absolute path.
"""
import json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent            # <root>/Job Tracker App/.. = <root>
DATA = ROOT / "Job Tracker App" / "data.json"
TAILORED_DIRS = [ROOT / "Resume" / "Tailored", ROOT / "Cover Letters" / "Tailored"]

ARCHIVE_STATUSES = {"Applied", "Phone Screen", "Interviewing", "Offer"}
ACTIVE_STATUSES  = {"To Apply", "Screening"}

def company_of_filename(name: str) -> str:
    # "Capacity - Solution Consultant - Resume.docx" -> "Capacity"
    return name.split(" - ", 1)[0].strip().lower()

def main():
    apps = json.load(open(DATA))
    archive_co, active_co = set(), set()
    for a in apps:
        co = (a.get("company") or "").strip().lower()
        if not co:
            continue
        if a.get("status") in ACTIVE_STATUSES:
            active_co.add(co)
        elif a.get("status") in ARCHIVE_STATUSES:
            archive_co.add(co)
    # A company is archivable only if it has applied-stage roles and no active ones.
    archivable = archive_co - active_co

    moved, summary = [], []
    for d in TAILORED_DIRS:
        if not d.is_dir():
            continue
        applied_dir = d / "Applied"
        applied_dir.mkdir(exist_ok=True)
        for f in d.iterdir():
            if not f.is_file():
                continue
            if company_of_filename(f.name) in archivable:
                dest = applied_dir / f.name
                shutil.move(str(f), str(dest))
                moved.append(str(dest.relative_to(ROOT)))
        remaining = sorted(p.name for p in d.iterdir() if p.is_file())
        summary.append((str(d.relative_to(ROOT)), remaining))

    print(f"Archived {len(moved)} file(s).")
    for m in moved:
        print("  moved:", m)
    print()
    for dname, remaining in summary:
        print(f"Still active in {dname}/ ({len(remaining)}):")
        for r in remaining:
            print("   ", r)
        print()

if __name__ == "__main__":
    main()
