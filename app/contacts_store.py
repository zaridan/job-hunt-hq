#!/usr/bin/env python3
"""contacts.json access for the outreach skills. Never hand-edit contacts.json.

Writes go through the running tracker server when it is up; otherwise
straight to the file with the same validation and backups the server uses.
Either way, a write is guarded by an optimistic-concurrency revision: this
tool captures contacts.json's revision when it loads (the server's
X-Contacts-Revision header, or a hash of the file), and the write is
rejected if the revision has since moved — an open People tab saved, or
another skill run wrote first. On that conflict this tool reloads and
retries the whole load-apply-save once; a second conflict fails hard
("contacts changed while updating; re-run the command") rather than
silently overwriting someone else's write.

  list   [--stage STAGE] [--company NAME]   matching contacts as JSON
  add                                       JSON array of new people on stdin
  update ID                                 JSON object of fields on stdin
  quota                                     request/note usage (and what's left under any limits)

Env: JOBTRACKER_PORT (default 8787), OUTREACH_TODAY (YYYY-MM-DD, tests only).
"""
import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta

import server  # same folder: validation, atomic writes, backups

BASE_URL = f"http://127.0.0.1:{os.environ.get('JOBTRACKER_PORT', '8787')}"
CONFIG_FILE = os.path.join(server.APP_DIR, "outreach-config.json")
DEFAULT_CONFIG = {
    # None (JSON null) = no limit for the three caps; set a number to cap one.
    "maxRequestsPerDay": None, "maxRequestsPerWeek": None, "noteSelection": "manual",
    "noteBudgetPerMonth": None, "noteCharLimit": 200, "maxProfileViewsPerRun": 40,
    "contactsPerCompany": 5, "minSendGapSeconds": 20, "maxSendGapSeconds": 60,
    "followupAfterDays": 6, "staleInviteDays": 21, "defaultAttachment": "tailored",
    "baseResumePath": "",
}
STAGE_DATE_FIELD = {"Queued": "dateQueued", "Requested": "dateRequested",
                    "Connected": "dateConnected", "Asked": "dateAsked"}
BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
MAX_SAVE_ATTEMPTS = 2


class ConflictError(RuntimeError):
    """contacts.json changed underneath us (stale revision) between load and save."""


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    return cfg


def server_up():
    try:
        with urllib.request.urlopen(BASE_URL + "/health", timeout=2) as r:
            return json.load(r).get("ok") is True
    except (OSError, ValueError):
        return False


def load_contacts():
    """Return (contacts, revision). `revision` is the concurrency token to
    pass back to save_contacts: the server's X-Contacts-Revision response
    header in server mode, or a hash of the file in file mode."""
    if server_up():
        with urllib.request.urlopen(BASE_URL + "/contacts.json", timeout=5) as r:
            data = json.load(r)
            revision = r.headers.get("X-Contacts-Revision", "")
        return data, revision
    return server.read_contacts(), server.contacts_revision()


def save_contacts(contacts, base_revision):
    """Write `contacts`, but only if `base_revision` (from load_contacts)
    still matches the current revision. Raises ConflictError otherwise."""
    server.validate_contacts(contacts)
    body = json.dumps(contacts, indent=2, ensure_ascii=False)
    if server_up():
        req = urllib.request.Request(BASE_URL + "/save-contacts", data=body.encode("utf-8"),
                                     method="POST",
                                     headers={"Content-Type": "application/json",
                                              "X-Base-Revision": base_revision})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                json.load(r)
        except urllib.error.HTTPError as e:
            payload = json.loads(e.read() or b"{}")
            message = payload.get("error", str(e))
            if e.code == 409:
                raise ConflictError(message) from e
            raise RuntimeError(message) from e
        return "server"
    if server.contacts_revision() != base_revision:
        raise ConflictError("contacts changed while updating; re-run the command")
    server.rotate_backup(server.CONTACTS_FILE, "contacts")
    server.atomic_write(server.CONTACTS_FILE, body)
    return "file"


def new_id():
    ms, out = int(time.time() * 1000), ""
    while ms:
        ms, r = divmod(ms, 36)
        out = BASE36[r] + out
    return "ct-" + out + "".join(random.choice(BASE36) for _ in range(4))


def to_likelihood(value):
    """int(value), or 0 for null/missing/non-numeric input."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def add_contacts(contacts, people, cfg, today):
    seen = {server.normalize_linkedin_url(c.get("linkedinUrl")) for c in contacts}
    added, skipped = [], []
    for p in people:
        url = server.normalize_linkedin_url(p.get("linkedinUrl"))
        if not url or url in seen or not p.get("name") or not p.get("company"):
            skipped.append(p.get("linkedinUrl") or p.get("name") or "?")
            continue
        seen.add(url)
        source = cfg["defaultAttachment"]
        c = {
            "id": new_id(), "company": p["company"], "appIds": p.get("appIds", []),
            "name": p["name"], "title": p.get("title", ""), "linkedinUrl": url,
            "location": p.get("location", ""), "relation": p.get("relation", ""),
            "likelihood": to_likelihood(p.get("likelihood", 0)), "why": p.get("why", ""),
            "stage": p.get("stage", "Found"), "useNote": False, "connectNote": "",
            "askMessage": "", "askApproved": False, "followupMessage": "",
            "attachmentSource": source,
            "attachment": cfg["baseResumePath"] if source == "base" else "",
            "dateFound": today, "dateQueued": "", "dateRequested": "", "dateConnected": "",
            "dateAsked": "", "dateFollowedUp": "", "dateReplied": "", "nextFollowup": "",
            "notes": p.get("notes", ""),
        }
        date_field = STAGE_DATE_FIELD.get(c["stage"])
        if date_field:
            c[date_field] = today
        contacts.append(c)
        added.append(c["id"])
    return added, skipped


def update_contact(contacts, cid, fields, cfg, today):
    c = next((x for x in contacts if x.get("id") == cid), None)
    if c is None:
        raise KeyError(f"no contact with id {cid}")
    old_stage = c.get("stage")
    c.update(fields)
    if "linkedinUrl" in fields:
        c["linkedinUrl"] = server.normalize_linkedin_url(fields["linkedinUrl"])
    if "attachmentSource" in fields:
        if "attachment" not in fields:
            c["attachment"] = cfg["baseResumePath"] if fields["attachmentSource"] == "base" else ""
        if "askApproved" not in fields:
            c["askApproved"] = False
    if "stage" in fields and fields["stage"] != old_stage and "askApproved" not in fields:
        c["askApproved"] = False
    date_field = STAGE_DATE_FIELD.get(fields.get("stage"))
    if date_field and not c.get(date_field):
        c[date_field] = today
    return c


def _left(limit, used):
    """Remaining under a cap, or None when that cap is off."""
    return None if limit is None else max(0, limit - used)


def quota(contacts, cfg, today):
    week_start = (date.fromisoformat(today) - timedelta(days=6)).isoformat()
    month = today[:7]
    q = {"requestsToday": 0, "requestsWeek": 0, "notesSent": 0, "notesSelected": 0}
    for c in contacts:
        sent = c.get("dateRequested") or ""
        q["requestsToday"] += sent == today
        q["requestsWeek"] += bool(sent) and week_start <= sent <= today
        q["notesSent"] += bool(c.get("useNote") and c.get("connectNote")) and sent[:7] == month
        # Only Found/Queued contacts still consume the note budget by being
        # selected; a Skipped or other closed-stage card with useNote left
        # on (the toggle is hidden there) must not tie up the budget forever.
        q["notesSelected"] += bool(c.get("useNote")) and c.get("stage") in ("Found", "Queued")
    q["remainingWeek"] = _left(cfg.get("maxRequestsPerWeek"), q["requestsWeek"])
    caps = [r for r in (_left(cfg.get("maxRequestsPerDay"), q["requestsToday"]), q["remainingWeek"])
            if r is not None]
    q["remainingToday"] = min(caps) if caps else None
    q["remainingNotes"] = _left(cfg.get("noteBudgetPerMonth"), q["notesSent"] + q["notesSelected"])
    return q


def run_add(people, cfg, today):
    """Load, apply add_contacts, save — retried once on a revision conflict."""
    for attempt in range(MAX_SAVE_ATTEMPTS):
        contacts, revision = load_contacts()
        added, skipped = add_contacts(contacts, people, cfg, today)
        if not added:
            return {"added": added, "skipped": skipped, "savedVia": "unchanged"}
        try:
            saved_via = save_contacts(contacts, revision)
        except ConflictError:
            if attempt < MAX_SAVE_ATTEMPTS - 1:
                continue
            raise RuntimeError("contacts changed while updating; re-run the command")
        return {"added": added, "skipped": skipped, "savedVia": saved_via}


def run_update(cid, fields, cfg, today):
    """Load, apply update_contact, save — retried once on a revision conflict."""
    for attempt in range(MAX_SAVE_ATTEMPTS):
        contacts, revision = load_contacts()
        c = update_contact(contacts, cid, fields, cfg, today)
        try:
            saved_via = save_contacts(contacts, revision)
        except ConflictError:
            if attempt < MAX_SAVE_ATTEMPTS - 1:
                continue
            raise RuntimeError("contacts changed while updating; re-run the command")
        return {"contact": c, "savedVia": saved_via}


def main(argv=None):
    ap = argparse.ArgumentParser(description="contacts.json helper for the outreach skills")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--stage")
    ls.add_argument("--company")
    sub.add_parser("add")
    up = sub.add_parser("update")
    up.add_argument("id")
    sub.add_parser("quota")
    args = ap.parse_args(argv)

    today = os.environ.get("OUTREACH_TODAY") or date.today().isoformat()
    try:
        cfg = load_config()
        if args.cmd == "list":
            contacts, _ = load_contacts()
            out = [c for c in contacts
                   if (not args.stage or c.get("stage") == args.stage)
                   and (not args.company
                        or (c.get("company") or "").strip().lower() == args.company.strip().lower())]
        elif args.cmd == "quota":
            contacts, _ = load_contacts()
            out = quota(contacts, cfg, today)
        elif args.cmd == "add":
            payload = json.load(sys.stdin)
            if not isinstance(payload, list):
                raise TypeError("add stdin must be a JSON array")
            out = run_add(payload, cfg, today)
        else:
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict):
                raise TypeError("update stdin must be a JSON object")
            out = run_update(args.id, payload, cfg, today)
    except (KeyError, ValueError, RuntimeError, OSError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
