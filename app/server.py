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
import json
import os
import re
import socket
import subprocess
import sys
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "data.json")
BACKUP_DIR = os.path.join(APP_DIR, "backups")
KEEP_BACKUPS = 20
VERSION = "1.0.0"


def rotate_backup():
    """Copy current data.json into backups/ (timestamped), prune old ones."""
    if not os.path.exists(DATA_FILE):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"data-{stamp}.json")
    try:
        with open(DATA_FILE, "rb") as src, open(dest, "wb") as dst:
            dst.write(src.read())
    except OSError:
        return
    backups = sorted(
        f for f in os.listdir(BACKUP_DIR)
        if re.fullmatch(r"data-\d{8}-\d{6}\.json", f)
    )
    for old in backups[:-KEEP_BACKUPS]:
        try:
            os.remove(os.path.join(BACKUP_DIR, old))
        except OSError:
            pass


def atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


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

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # data.json must always be fresh
        if self.path.split("?")[0] in ("/data.json", "/health"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    # ---- routes --------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self._json(200, {"ok": True, "version": VERSION,
                                    "dataFile": os.path.basename(DATA_FILE)})
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

    def do_POST(self):
        if urlparse(self.path).path != "/save":
            return self._json(404, {"ok": False, "error": "not found"})
        if not self._same_origin():
            return self._json(403, {"ok": False, "error": "forbidden"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 20_000_000:
                raise ValueError("bad content length")
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, list):
                raise ValueError("expected a JSON array of applications")
            for item in data:
                if not isinstance(item, dict):
                    raise ValueError("every application must be an object")
        except (ValueError, json.JSONDecodeError) as e:
            return self._json(400, {"ok": False, "error": str(e)})
        rotate_backup()
        atomic_write(DATA_FILE, json.dumps(data, indent=2, ensure_ascii=False))
        return self._json(200, {"ok": True, "count": len(data)})

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
