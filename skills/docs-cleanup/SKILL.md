---
name: docs-cleanup
description: Archive tailored resumes and cover letters for roles that are no longer active, keeping the working Applications folder short. Use when the user says "clean up my tailored docs", "archive old application materials", "tidy my resume folder", or when a nightly cleanup task fires.
---

# Application docs cleanup

Run the maintenance script that ships with the tracker app:

```
python3 "<root>/Job Tracker App/cleanup_applied.py"
```

`<root>` is the user's job-hunt folder. The script is idempotent and safe to re-run. Per company (matched on the `Applications/<Company>/` folder name) it moves the whole company folder into `Applications/Archive/` — but only when that company has at least one role at Applied/Phone Screen/Interviewing/Offer AND no role still active (To Apply / Screening). This protects a shared resume + cover letter while any of a company's roles is still open. "Won't Apply", "Rejected", and "Closed" roles neither keep a folder active nor trigger archiving.

Report which files moved (the script prints them), or one line if nothing needed archiving. If the script is missing, say so and offer to reinstall it from the plugin's app files rather than improvising the logic.
