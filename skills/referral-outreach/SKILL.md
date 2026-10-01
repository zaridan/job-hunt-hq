---
name: referral-outreach
description: Draft and send tailored LinkedIn referral asks (with a resume attached) to the user's connected contacts, check their replies, and handle the single follow-up. Use for "draft referral asks", "ask for referrals", "check replies from my contacts", "send the approved asks", "send outreach", or when the outreach-prep task runs.
---

# Referral outreach

Read `Outreach-Rules.md` (next to this file) first; it applies to every step (including what `<root>` and `store` mean). Templates are the user's copies in `<root>/Referral/Templates/`, falling back to this skill's `templates/` folder.

- **Draft** (including the reply check) is read-only on LinkedIn and can run on schedule.
- **Send** is supervised.

"Config" means `Job Tracker App/outreach-config.json`. The user reviews every draft in the tracker's **People** tab and ticks **Approve ask** before anything can be sent.

## Draft (read-only)

### 1. Replies

Run `store list --stage Asked`. For each person, open their conversation at `https://www.linkedin.com/messaging/` (search their name) and read anything after `dateAsked`:
- **Any reply:** if `dateReplied` is empty, set it to today.
- **A clear yes** (for example, "send me the link" or "I'll refer you"): run `store update <id>` with `{"stage": "Referred"}` and draft the after-yes reply (step 5).
- **A clear no:** `{"stage": "Declined"}`.
- **Anything else:** append a one-line summary to `notes` for the user.

### 2. Resolve the attachment

For each contact from `store list --stage Connected` whose `attachment` is empty, go by `attachmentSource`:
- **`tailored`:** look in `Applications/<Company>/` for the tailored resume PDF that `generate-docs` wrote for the card in `appIds` (`<Candidate Name> - Resume.pdf`, or `<Candidate Name> - <Role> - Resume.pdf`).
  - If none exists, run the `generate-docs` skill. It handles To Apply cards without documents.
  - If that produces the PDF, use it.
  - If it skipped the card (the card's notes gain `[docs: skipped …]`), run `store update <id>` with `{"attachmentSource": "base", "notes": "<existing notes> [outreach: tailored resume unavailable — <reason>, using base]"}`.
- **`base`:** `attachment` should already be `baseResumePath`. If it's empty, set it to that. If `baseResumePath` itself is empty, leave the attachment empty and note `set baseResumePath in outreach-config.json` for the user.
- **`upload`:** use `attachment` if it's set. If it's empty, still draft the message (step 3), and add `waiting for upload` to `notes`.

Save a resolved file with `store update <id>` and `{"attachment": "<path relative to <root>>"}`.

### 3. Draft the ask

For each Connected contact whose `askMessage` is empty, use `ask-recruiter.md` if `relation` is `recruiter`, and `ask-engineer.md` otherwise. Fill in:
- `{first_name}` from the contact.
- `{role}` and `{company}` from the linked card.
- `{job_link}` from the card's `url`.
- `{job_id}` from the posting, if it shows one.
- `{intro}` and `{sender_name}` from `Resume/Master-Resume.md`.
- `{fit_points}`:
  1. Read the job description, from `Job Listings/<Company> - <Role>.md` or else the card's URL.
  2. Pick the two needs where the master resume has the strongest real match.
  3. Write each as one plain sentence about what the user did, with numbers exactly as in the resume.

Follow the message rules, and compare against other asks at the same company (`store list --company`). Save with `{"askMessage": "<text>", "askApproved": false}`.

### 4. Follow-ups and close-out

These apply only to Asked contacts with an empty `dateReplied`:
- **Draft a follow-up** from `follow-up.md` when all of these hold: `dateFollowedUp` is empty, `followupMessage` is empty, and `dateAsked` is at least `followupAfterDays` days ago. Save it as `followupMessage`.
- **Close out** with `{"stage": "No response"}` when `dateFollowedUp` is at least `followupAfterDays` days ago.

### 5. After a yes

Draft a reply from `referral-yes.md`. For `{referral_note}`, use the body of `Referral/Referral-Note.md` (everything after its `---` line). If that file doesn't exist, offer to write it from the master resume (setup's `Referral-Note-Template.md`) instead of drafting the reply. Append the draft to the contact's `notes` as `[reply draft] <text>` for the user to review.

At the end of Draft, commit per Outreach-Rules.md.

## Send (supervised)

Only when the user asks in chat. "Send outreach" means `people-finder`'s Send (connection requests) first, then this mode, each with its own list and its own yes; see Outreach-Rules.md.

1. **Build the batch:**
   - Connected contacts with `askApproved: true`. Check that each one's `attachment` file exists under `<root>`. If it doesn't, leave that person out and say why.
   - Asked contacts with a non-empty `followupMessage`, an empty `dateFollowedUp`, and an empty `dateReplied`.
   - Any `[reply draft]` the user has approved in this conversation.
2. **Show the user the batch:** recipient · company · ask, follow-up or reply · the full text · the attachment file name. Ask: "Send these N messages?" Wait for an explicit yes. A yes covers only this list.
3. **Send each message:**
   1. Open their profile and click **Message**. If there's no Message button, skip them per the rules.
   2. Type the exact approved text.
   3. For an ask, attach the PDF: use the paperclip control, and upload `<root>/<attachment>` (absolute path) with the Chrome file-upload tool. Wait until it shows as attached.
   4. Click **Send** and confirm the message appears in the thread.
   5. Update the contact straight away:
      - ask: `{"stage": "Asked"}`, which stamps `dateAsked`;
      - follow-up: `{"dateFollowedUp": "<today>"}`;
      - reply: append `[reply sent YYYY-MM-DD]` to `notes`.
   6. Wait a random `minSendGapSeconds`–`maxSendGapSeconds` before the next one.
4. **Report** what was sent and what was skipped (and why), then commit per Outreach-Rules.md.
