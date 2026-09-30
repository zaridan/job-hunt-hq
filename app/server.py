#!/usr/bin/env python3
"""
Job Tracker local server — the tiny backend that makes the tracker rock solid.

Serves the app and owns all reads/writes of data.json. No dependencies
(Python 3 stdlib only), localhost-only, single instance.

Endpoints:
  GET  /            -> index.html (and any static file in this folder)
  GET  /data.json   -> current data, never cached
  POST /save        -> body = JSON array of applications; written atomically,
                       previous version kept in backups/ (last 20 retained)
  GET  /contacts.json -> referral contacts ([] if none yet), never cached;
                       response header X-Contacts-Revision is a content hash
                       for optimistic concurrency (see /save-contacts)
  POST /save-contacts -> body = JSON array of contacts; validated (required
                       fields, known stage, unique id and LinkedIn URL),
                       written atomically, backed up as backups/contacts-*.json.
                       An X-Base-Revision request header, if present, must
                       match the current X-Contacts-Revision or the save is
                       rejected with 409 (someone else wrote first); requests
                       without the header are accepted unconditionally, for
                       manual tools. On success the response body's
                       "revision" is the new X-Contacts-Revision.
  POST /upload-attachment?contact=<id>&name=<file> -> body = PDF bytes (<=10 MB);
                       saved as Resume/Uploads/<Company>/<file>.pdf, returns its path
  GET  /open?url=   -> opens an http(s) link in the system default browser
                       (so links never open inside the app window)
  GET  /reveal?path= -> shows a file in the platform file manager (Finder /
                       Explorer with the file selected; folder on Linux) so
                       it can be dragged into an application form. Path is
                       relative to the job-hunt folder (parent of this app)
                       and must stay inside it. Falls back to opening the
                       containing folder if the exact file is missing.
  GET  /claude      -> opens/focuses the Claude desktop app, where the
                       "Job Docs — Generate Now" artifact button lives
  GET  /health      -> {"ok": true, ...} — lets the app detect server mode

Run:  python3 server.py            (default port 8787)
      python3 server.py --port N
If the port is already in use, an instance is assumed to be running and we
exit 0 — safe for a launcher to call unconditionally.
"""
import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "data.json")
BACKUP_DIR = os.path.join(APP_DIR, "backups")
KEEP_BACKUPS = 20
VERSION = "1.0.0"
ROOT_DIR = os.path.dirname(APP_DIR)  # the job-hunt repo root
CONTACTS_FILE = os.path.join(APP_DIR, "contacts.json")
CONTACT_STAGES = ("Found", "Queued", "Requested", "Connected", "Asked",
                  "Referred", "Declined", "No response", "Skipped")
MAX_JSON_BYTES = 20_000_000
NO_STORE_PATHS = ("/data.json", "/contacts.json", "/outreach-config.json", "/health")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
UPLOAD_DIR = os.path.join(ROOT_DIR, "Resume", "Uploads")
# Guards the read-revision/write-contacts sequence in _save_contacts so two
# concurrent saves (e.g. a browser tab and a skill run) can't both pass the
# revision check against the same stale value and then both write.
CONTACTS_LOCK = threading.Lock()


def rotate_backup(path, prefix):
    """Copy `path` to backups/<prefix>-<stamp>.json and keep the newest KEEP_BACKUPS per prefix."""
    if not os.path.exists(path):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"{prefix}-{stamp}.json")
    try:
        with open(path, "rb") as src, open(dest, "wb") as dst:
            dst.write(src.read())
    except OSError:
        return
    pattern = re.compile(re.escape(prefix) + r"-\d{8}-\d{6}\.json")
    backups = sorted(f for f in os.listdir(BACKUP_DIR) if pattern.fullmatch(f))
    for old in backups[:-KEEP_BACKUPS]:
        try:
            os.remove(os.path.join(BACKUP_DIR, old))
        except OSError:
            pass


def atomic_write_bytes(path, data):
    directory = os.path.dirname(path) or "."
    basename = os.path.basename(path)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=basename + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def atomic_write(path, text):
    atomic_write_bytes(path, text.encode("utf-8"))


def normalize_linkedin_url(url):
    """The contact dedupe key: https, lowercase, no www., no query/fragment/trailing slash."""
    url = (url or "").strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return f"https://{host}{parsed.path.rstrip('/')}".lower()


def validate_contacts(data):
    """Raise ValueError unless `data` is a list of well-formed, unique contacts."""
    if not isinstance(data, list):
        raise ValueError("expected a JSON array of contacts")
    ids, urls = set(), set()
    for i, c in enumerate(data):
        if not isinstance(c, dict):
            raise ValueError(f"contact {i} must be an object")
        for key in ("id", "name", "company"):
            if not str(c.get(key) or "").strip():
                raise ValueError(f"contact {i} is missing {key}")
        if c.get("stage") not in CONTACT_STAGES:
            raise ValueError(f"contact {c['id']} has unknown stage {c.get('stage')!r}")
        if c["id"] in ids:
            raise ValueError(f"duplicate contact id {c['id']}")
        ids.add(c["id"])
        url = normalize_linkedin_url(c.get("linkedinUrl"))
        if url:
            if url in urls:
                raise ValueError(f"duplicate linkedinUrl {url}")
            urls.add(url)
    return data


def read_contacts():
    try:
        with open(CONTACTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def contacts_revision():
    """SHA-256 hex of contacts.json's current bytes; "" if the file is missing.
    A cheap optimistic-concurrency token so a stale writer (an open People
    tab, a skill run) can detect it's about to overwrite someone else's save."""
    try:
        with open(CONTACTS_FILE, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return ""


def safe_segment(text, fallback):
    """Keep letters, digits, space, '-', '_' and '.'; no leading dots; never empty."""
    cleaned = re.sub(r"[^A-Za-z0-9 _.\-]", "", text or "").strip().lstrip(".")
    return cleaned or fallback


class Handler(SimpleHTTPRequestHandler):
    server_version = "JobTracker/" + VERSION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=APP_DIR, **kwargs)

    # ---- helpers -------------------------------------------------------
    def _same_origin(self):
        """Best-effort check that the request came from our own page."""
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        referer = self.headers.get("Referer")
        fetch_site = self.headers.get("Sec-Fetch-Site")
        if fetch_site is not None:
            return fetch_site in ("same-origin", "none")
        for h in (origin, referer):
            if h:
                netloc = urlparse(h).netloc
                return netloc == host
        return True  # curl / same-machine tools

    def _json(self, code, obj, headers=None):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # Tracker data must always be fresh. The app's own files (html/js/css)
        # may be cached but must be revalidated on every load; otherwise a
        # browser keeps running old scripts against new data or config after
        # an update (it showed "0/null" when the config changed shape).
        if self.path.split("?")[0] in NO_STORE_PATHS:
            self.send_header("Cache-Control", "no-store")
        else:
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    # ---- routes --------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self._json(200, {"ok": True, "version": VERSION,
                                    "dataFile": os.path.basename(DATA_FILE)})
        if parsed.path == "/contacts.json":
            return self._json(200, read_contacts(), {"X-Contacts-Revision": contacts_revision()})
        if parsed.path == "/open":
            return self._open_url(parsed)
        if parsed.path == "/reveal":
            return self._reveal(parsed)
        if parsed.path == "/claude":
            return self._open_claude()
        # never serve git internals, backups, or ourselves
        if parsed.path.startswith(("/.git", "/backups", "/server.py")):
            return self._json(404, {"ok": False, "error": "not found"})
        return super().do_GET()

    def _open_url(self, parsed):
        if not self._same_origin():
            return self._json(403, {"ok": False, "error": "forbidden"})
        url = (parse_qs(parsed.query).get("url") or [""])[0]
        if not re.match(r"^https?://", url):
            return self._json(400, {"ok": False, "error": "http(s) URLs only"})
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", url])
            else:
                webbrowser.open(url)
            return self._json(200, {"ok": True})
        except Exception as e:  # noqa: BLE001
            return self._json(500, {"ok": False, "error": str(e)})

    def _reveal(self, parsed):
        if not self._same_origin():
            return self._json(403, {"ok": False, "error": "forbidden"})
        rel = (parse_qs(parsed.query).get("path") or [""])[0]
        root = os.path.realpath(os.path.dirname(APP_DIR))  # the job-hunt folder
        if not rel or rel.startswith(("/", "~")) or ".." in rel:
            return self._json(400, {"ok": False, "error": "bad path"})
        target = os.path.realpath(os.path.join(root, rel))
        if not target.startswith(root + os.sep):
            return self._json(400, {"ok": False, "error": "path outside project"})
        try:
            if os.path.isfile(target):
                self._show_in_file_manager(target, select=True)
                return self._json(200, {"ok": True, "revealed": os.path.basename(target)})
            folder = os.path.dirname(target)
            if os.path.isdir(folder):
                self._show_in_file_manager(folder, select=False)
                return self._json(200, {"ok": True, "note": "Exact file not found — opened its folder instead."})
            return self._json(404, {"ok": False, "error": "file and folder not found"})
        except Exception as e:  # noqa: BLE001
            return self._json(500, {"ok": False, "error": str(e)})

    @staticmethod
    def _show_in_file_manager(path, select):
        """Open the platform file manager; select the file where supported."""
        if sys.platform == "darwin":  # Finder
            subprocess.Popen(["open", "-R", path] if select else ["open", path])
        elif sys.platform == "win32":  # Explorer ('/select,path' is one arg)
            subprocess.Popen(["explorer", "/select," + path] if select
                             else ["explorer", path])
        else:  # Linux/BSD: no portable 'select' — open the containing folder
            folder = os.path.dirname(path) if select else path
            subprocess.Popen(["xdg-open", folder])

    def _open_claude(self):
        """Open/focus the Claude desktop app (where the docs artifact lives)."""
        if not self._same_origin():
            return self._json(403, {"ok": False, "error": "forbidden"})
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "Claude"])
            elif sys.platform == "win32":
                exe = os.path.join(os.environ.get("LocalAppData", ""),
                                   "AnthropicClaude", "claude.exe")
                if not os.path.isfile(exe):
                    return self._json(404, {"ok": False,
                                            "error": "Claude desktop not found"})
                subprocess.Popen([exe])
            else:
                return self._json(501, {"ok": False,
                                        "error": "Claude desktop not available"})
            return self._json(200, {"ok": True})
        except Exception as e:  # noqa: BLE001
            return self._json(500, {"ok": False, "error": str(e)})

    def _drain(self, length):
        """Read and discard a rejected body (capped) so the client isn't reset mid-send."""
        remaining = min(length, 64 * 1024 * 1024)
        while remaining > 0:
            chunk = self.rfile.read(min(65536, remaining))
            if not chunk:
                break
            remaining -= len(chunk)

    def _upload_attachment(self):
        query = parse_qs(urlparse(self.path).query)
        contact_id = (query.get("contact") or [""])[0]
        name = (query.get("name") or [""])[0]
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except (TypeError, ValueError):
            return self._json(400, {"ok": False, "error": "bad content length"})
        if length > MAX_UPLOAD_BYTES:
            self._drain(length)
            return self._json(413, {"ok": False, "error": "PDF must be 10 MB or smaller"})
        body = self.rfile.read(length) if length > 0 else b""
        if not body.startswith(b"%PDF-"):
            return self._json(400, {"ok": False, "error": "only PDF files can be uploaded"})
        if not name or "/" in name or "\\" in name or ".." in name:
            return self._json(400, {"ok": False, "error": "bad file name"})
        contact = next((c for c in read_contacts() if c.get("id") == contact_id), None)
        if contact is None:
            return self._json(404, {"ok": False, "error": "unknown contact"})
        filename = safe_segment(name, "resume")
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        uploads = os.path.realpath(UPLOAD_DIR)
        target = os.path.realpath(
            os.path.join(uploads, safe_segment(contact.get("company"), "Company"), filename))
        if not target.startswith(uploads + os.sep):
            return self._json(400, {"ok": False, "error": "path outside uploads"})
        os.makedirs(os.path.dirname(target), exist_ok=True)
        atomic_write_bytes(target, body)
        rel = os.path.relpath(target, os.path.realpath(ROOT_DIR)).replace(os.sep, "/")
        return self._json(200, {"ok": True, "path": rel})

    def do_POST(self):
        routes = {"/save": self._save_apps, "/save-contacts": self._save_contacts, "/upload-attachment": self._upload_attachment}
        handler = routes.get(urlparse(self.path).path)
        if handler is None:
            return self._json(404, {"ok": False, "error": "not found"})
        if not self._same_origin():
            return self._json(403, {"ok": False, "error": "forbidden"})
        return handler()

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except (TypeError, ValueError):
            raise ValueError("bad content length")
        if length <= 0 or length > MAX_JSON_BYTES:
            raise ValueError("bad content length")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _save_apps(self):
        try:
            data = self._read_json_body()
            if not isinstance(data, list):
                raise ValueError("expected a JSON array of applications")
            if not all(isinstance(item, dict) for item in data):
                raise ValueError("every application must be an object")
        except ValueError as e:
            return self._json(400, {"ok": False, "error": str(e)})
        rotate_backup(DATA_FILE, "data")
        atomic_write(DATA_FILE, json.dumps(data, indent=2, ensure_ascii=False))
        return self._json(200, {"ok": True, "count": len(data)})

    def _save_contacts(self):
        try:
            data = validate_contacts(self._read_json_body())
        except ValueError as e:
            return self._json(400, {"ok": False, "error": str(e)})
        base_revision = self.headers.get("X-Base-Revision")
        # Requests without the header are accepted unconditionally (manual
        # tools, curl); a mismatched header means someone else wrote since
        # this client last loaded, so refuse rather than clobber their save.
        with CONTACTS_LOCK:
            current_revision = contacts_revision()
            if base_revision is not None and base_revision != current_revision:
                return self._json(409, {"ok": False,
                                        "error": "contacts changed since you loaded them",
                                        "revision": current_revision})
            rotate_backup(CONTACTS_FILE, "contacts")
            atomic_write(CONTACTS_FILE, json.dumps(data, indent=2, ensure_ascii=False))
            new_revision = contacts_revision()
        return self._json(200, {"ok": True, "count": len(data), "revision": new_revision})

    def log_message(self, fmt, *args):  # quiet: log errors only
        if args and str(args[1] if len(args) > 1 else "").startswith(("4", "5")):
            super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser(description="Job Tracker local server")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()

    # single instance: if the port is taken, assume we're already running
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if probe.connect_ex(("127.0.0.1", args.port)) == 0:
        probe.close()
        print(f"Job Tracker already running on http://localhost:{args.port}")
        return 0
    probe.close()

    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Job Tracker serving on http://localhost:{args.port}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
