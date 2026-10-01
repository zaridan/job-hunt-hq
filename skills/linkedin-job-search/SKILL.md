---
name: linkedin-job-search
description: Search LinkedIn Jobs (in the user's own logged-in Chrome) for roles that fit their Job-Thesis.md and master resume, score them, and add new ones to the tracker's Screening column. Use when asked to "search LinkedIn for jobs", "find new roles on LinkedIn", or when the outreach-prep task runs. Read-only on LinkedIn; complements job-scrub, which searches public boards.
---

# LinkedIn job search

Read `${CLAUDE_PLUGIN_ROOT}/skills/referral-outreach/Outreach-Rules.md` first; it applies to every step (including what `<root>` means). This skill is read-only on LinkedIn.

## 1. Know what a fit is

Read `Job-Thesis.md` and `Resume/Master-Resume.md`. From the thesis, you need:
- the role tiers (Tier A titles become the searches);
- any target companies and their priority;
- the arrangement and location;
- the compensation floor;
- the background reality check.

## 2. Search

Open LinkedIn Jobs searches in Chrome, one query at a time:

`https://www.linkedin.com/jobs/search/?keywords=<url-encoded query>&location=<thesis location>&f_TPR=r604800`

- `f_TPR=r604800` means posted in the past week. Add `&f_WT=2` for one remote-only pass if the thesis allows remote. If the thesis targets senior roles, add `&f_E=4` (Mid-Senior level).
- Run the queries in this order:
  1. The Tier A titles from the thesis.
  2. `<Company> <role area>`, for each target company in the thesis, highest priority first.
- Before opening a posting, skip it if `data.json` already has the same company and role (case-insensitive), a recent `New-Openings-*.md` lists it, or it already appeared in this run.
- Read at most 25 postings per run.

## 3. Score

Open each posting (`https://www.linkedin.com/jobs/view/<id>/`) and read the full description. Score it 0–100 against the thesis and the resume:

| Score | Meaning |
|---|---|
| 90+ | Tier A title, constraints met, strong resume match |
| 70–89 | Strong fit with one real gap |
| 50–69 | Plausible with caveats, or Tier B (always flag Tier B) |
| below 50 | Drop it |

Don't score up roles that oversell the user; the reality check wins. If the posting states pay, compare it to the floor. If it doesn't, write "comp not stated".

## 4. Save and add (roles scoring 50+)

1. Save the description to `Job Listings/<Company> - <Role>.md`, replacing `/` and `:` with `-`. Put the posting URL and today's date on the first two lines.
2. Append this entry to the tracker's `data.json` (`Data/data.json`; older installs: `Job Tracker App/data.json`), using the write path in Outreach-Rules.md:

   ```json
   {"id": "app-<base36 of Date.now()><4 random base36 chars>", "company": "", "role": "",
    "location": "", "arrangement": "Remote|Hybrid|Onsite",
    "url": "https://www.linkedin.com/jobs/view/<id>/", "dateAdded": "<today>", "dateApplied": "",
    "status": "Screening", "resumeVersion": "", "coverLetter": "", "contact": "", "lastContact": "",
    "nextFollowup": "", "salary": "<stated pay or empty>", "excitement": "", "fitScore": "<score>",
    "notes": "<tier> · <one-line why> · <anything to verify>", "source": "LinkedIn"}
   ```

3. Check the result: the JSON parses, the array grew by exactly the number you added, and no existing entry changed.

## 5. Review file

Write `<root>/New-Openings-<today>.md`:
- one intro line;
- one table per tier (Company | Role | Comp | Fit | Notes | Link), sorted by fit;
- a list of anything to verify;
- a short "Reality check" paragraph.

If today's file already exists (e.g. from job-scrub), append a `## LinkedIn` section to it instead.

## 6. Commit and report

Commit per Outreach-Rules.md. Report the new roles by tier, the top 3, and the review file's name. If there's nothing new, say so in one line.
