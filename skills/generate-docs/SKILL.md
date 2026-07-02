---
name: generate-docs
description: Generate a tailored resume and cover letter for tracker roles in "To Apply" that don't have documents yet, and stamp them onto the cards. Use when the user says "generate my application docs", "tailor my resume for my to-apply roles", "make documents for a specific company", or when a docs-generation task fires (scheduled or via the Generate Now button).
---

# Generate tailored application documents

For each To Apply card without documents: fetch the real posting, tailor from the master resume, write the files, stamp the card.

## Ground rules
- `<root>` is the user's job-hunt folder (contains `Job-Thesis.md`, `Resume/Master-Resume.md`, `Cover Letters/Cover-Letter-Template.md`, `Job Tracker App/data.json`).
- `data.json` is the ONLY data store; never modify index.html; no .bak files. Git commits are best-effort and optional — skip silently if git is unavailable.
- NEVER fabricate: no invented skills, titles, dates, metrics — and no documents written against a job description you couldn't actually read.

## Step 1 — Select cards
Entries where status == "To Apply", all of resumeMD / coverMD / resumeLink / coverLink are empty/absent, and notes does not contain "[docs:" (a prior failure/skip marker — the user deletes the marker to request a retry). If none: report that in one line and stop. Process at most 4 per run, oldest first.

## Step 2 — Fetch the posting
Fetch the card's `url` (browser tools if the page is client-rendered and available). If unreachable, login-gated, expired, or a different role: append "[docs: skipped YYYY-MM-DD — <reason>]" to notes and move on. A mirror found by web search is acceptable only if it is unambiguously the same role. If the description is too thin to tailor against, treat as a skip.

## Step 3 — Tailor
Read `Job-Thesis.md` (positioning honesty rules), `Resume/Master-Resume.md` (trim/reorder from it, never invent), and `Cover Letters/Cover-Letter-Template.md` (structure, header block, 250-350 words). Mirror the posting's actual keywords truthfully. The cover letter opens with a specific, genuine hook about THIS company.

## Step 4 — Write the files
- `<root>/Resume/Tailored/<Company> - <Role> - Resume.md` and `.docx`
- `<root>/Cover Letters/Tailored/<Company> - <Role> - Cover Letter.md` and `.docx`
Sanitize "/" and ":" out of filenames. Build .docx with the docx skill (read its SKILL.md first): clean single-column professional layout matching the .md content.

## Step 5 — Stamp the card
For each processed entry set: `resumeMD` and `coverMD` = the full markdown (powers the app's built-in viewers), `resumeVersion` = "Tailored YYYY-MM-DD", `coverLetter` = "Yes", and append "[docs: generated YYYY-MM-DD]" to notes. Preserve everything else. VALIDATE: JSON parses, length unchanged, only intended entries differ. Best-effort: `git -C "<root>/Job Tracker App" add data.json && git commit -m "generate-docs: <companies>"`.

## Step 6 — Report
Which cards got documents, which were skipped and why, and remind the user to review drafts before sending. Never regenerate a card that already has documents.
