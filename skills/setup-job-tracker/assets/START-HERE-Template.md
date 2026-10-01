# Job Hunt — Start Here

Your command center. The board lives in `Job Tracker App/` — open it by asking
Claude **"open my job tracker,"** or double-click your Job Tracker launcher
icon. (If the icon ever won't open, just ask Claude — it can rebuild the
shortcut.)

> Claude will occasionally ask permission to open this folder — on a new
> session, or when an automation or the Generate Now button runs. Just approve
> it; that access is what lets it help.

## The loop
1. **Find roles.** New matches land in the **Screening** column
   (automatically, if the daily scrub is on — or ask Claude to run a scrub).
2. **Screen.** Drag keepers to **To Apply**; delete or mark "Won't Apply"
   for the rest.
3. **Get documents.** Tailored resume + cover letter are generated per
   To Apply card (scheduled, on-demand button, or just ask Claude).
4. **Apply.** Use the card's 📄/✉ buttons; drag the card to **Applied**.
5. **Track replies.** The reply monitor advances cards when companies write
   back (or ask Claude to check).

## The files
- `Job-Thesis.md` — what "a fit" means; edit anytime, automations follow it.
- `Resume/Master-Resume.md` — canonical resume; tailored copies derive from it.
- `Data/data.json` — the single source of truth for the board (and
  `Data/contacts.json` for the People tab), kept apart from the app.
  Git-versioned; rolling backups in `Data/backups/`.

## Referral outreach (optional — keep this section only if it's set up)

1. **Every morning** the outreach prep adds new LinkedIn roles to Screening. For companies in **To Apply**, it finds people likely to refer you and drafts messages. It never sends anything.
2. **Switch the tracker to People** (Jobs | People, top right):
   - **Approve** the people you want to connect with. Use **+ Add person** for someone you already know at a company.
   - Tick **Send with a note** for the people worth one (LinkedIn's free plan allows only a few notes a month).
   - For connected people, check the drafted ask, pick the resume (tailored, base, or upload a PDF), and tick **Approve ask**.
3. **Say "send outreach"** to Claude. You'll see the exact list of requests and messages first, and nothing goes out until you say yes.

Settings (default resume, note length, pacing, optional limits) are in `Job Tracker App/outreach-config.json`.
