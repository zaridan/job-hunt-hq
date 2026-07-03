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
- NEVER lift language from the posting. Do not copy the posting's phrases, adjectives, or sentence stems into the resume or cover letter. The posting tells you what to *select and foreground* from real experience — it is not source text to echo. A hiring committee ranks down any document that reads like the job description handed back to them.
- Every claim must trace to a specific, real thing in the master resume — a named project, team, system, or outcome. If a requirement in the posting has no genuine match in the user's experience, leave it unaddressed rather than papering over it with generic phrasing.
- Numbers come from the master resume verbatim or not at all. Never invent, round up, or generate a plausible-looking metric, and never reuse the same stat as a near-duplicate across different bullets (the "increased efficiency by 20% / 23% / 18%" tell).

## Step 1 — Select cards
Entries where status == "To Apply", all of resumeMD / coverMD / resumeLink / coverLink are empty/absent, and notes does not contain "[docs:" (a prior failure/skip marker — the user deletes the marker to request a retry). If none: report that in one line and stop. Process at most 4 per run, oldest first.

## Step 2 — Get the job description
FIRST check `<root>/Job Listings/<Company> - <Role>.md` — the job scrub saves captured postings there. If present and substantive, use it (no fetch needed). Otherwise fetch the card's `url` (browser tools if the page is client-rendered and available). If unreachable, login-gated, expired, or a different role: append "[docs: skipped YYYY-MM-DD — <reason>]" to notes and move on. A mirror found by web search is acceptable only if it is unambiguously the same role. When a fetch succeeds, save the description to `<root>/Job Listings/<Company> - <Role>.md` for next time. If the description is too thin to tailor against, treat as a skip.

## Step 3 — Tailor
Read `Job-Thesis.md` (positioning honesty rules), `Resume/Master-Resume.md` (trim/reorder from it, never invent), and `Cover Letters/Cover-Letter-Template.md` (structure, header block, 250-350 words).

Work from experience toward the posting, never the reverse:
1. Read the posting and list what this employer actually cares about (the underlying needs, not the buzzwords).
2. For each need, find the strongest REAL match in the master resume and lead with it. Reorder and trim so the most relevant genuine experience is on top; drop what doesn't serve this role.
3. Write each bullet as concrete evidence — what the user actually did, the situation, and the real outcome — in the user's own plain phrasing. Prefer specifics ("stood up a weekly triage between support and product and cut the escalation backlog") over restated competencies ("leveraged cross-functional collaboration").
4. Use the employer's vocabulary only where it is genuinely also the user's — matching a real shared term is fine; adopting their phrasing to seem like a fit is the slop failure.

The cover letter opens with a specific, genuine hook about THIS company (something true about the role, product, team, or problem — not a template line with the company name slotted in). It should read as if this user wrote it about this one job, and could not be sent to any other company unchanged.

## Step 4 — Authenticity self-check (before writing files)
Read each draft back and verify all of the following. If any fails, revise before writing — do not ship a draft that fails these:
- **Uniqueness test:** could this exact sentence appear on a stranger's resume for this job? If yes, it's generic — rewrite it around the user's specific experience or cut it.
- **No echo:** no phrase or sentence stem is lifted from the posting; the cover letter is not the job description rephrased.
- **No template smell:** bullets don't share a repeated stem with only the noun/number swapped; the cover letter opening is not reusable across companies.
- **Traceable:** every skill, title, date, and metric maps to something real in the master resume.
- **Sounds human:** read it aloud in your head — if it sounds like LinkedIn boilerplate rather than a person describing their own work, fix it.
If a card can only be filled with generic material because the genuine match is weak, prefer a shorter, rougher, honest document over a polished generic one — and note the weak fit in the report rather than hiding it.

## Step 5 — Write the files
- `<root>/Resume/Tailored/<Company> - <Role> - Resume.md` and `.docx`
- `<root>/Cover Letters/Tailored/<Company> - <Role> - Cover Letter.md` and `.docx`
Sanitize "/" and ":" out of filenames. Build .docx with the docx skill (read its SKILL.md first): clean single-column professional layout matching the .md content.

## Step 6 — Stamp the card
For each processed entry set: `resumeMD` and `coverMD` = the full markdown (powers the app's built-in viewers), `resumeVersion` = "Tailored YYYY-MM-DD", `coverLetter` = "Yes", and append "[docs: generated YYYY-MM-DD]" to notes. Preserve everything else. VALIDATE: JSON parses, length unchanged, only intended entries differ. Best-effort: `git -C "<root>/Job Tracker App" add data.json && git commit -m "generate-docs: <companies>"`.

## Step 7 — Report
Which cards got documents, which were skipped and why, and flag any where the genuine fit was weak so the user can decide whether to apply. Remind the user to review drafts before sending. Never regenerate a card that already has documents.
