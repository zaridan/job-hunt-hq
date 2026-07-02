#!/usr/bin/env python3
"""
Job Tracker launcher — cross-platform (macOS, Windows, Linux).

Starts the local server (server.py) if it isn't already running, then opens
the dashboard in its own Chrome/Edge app-style window (no tabs). Falls back
to the system default browser if no Chromium-family browser is found.

Run:  python3 launch.py            (Windows: py launch.py or double-click)
      python3 launch.py --port N
Environment: JOBTRACKER_PORT overrides the default port (8787).
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def server_healthy(url):
    try:
        with urllib.request.urlopen(url + "/health", timeout=1) as r:
            return b'"ok": true' in r.read()
    except Exception:  # noqa: BLE001
        return False


def start_server(port):
    kwargs = {}
    if sys.platform == "win32":
        # detach so the console window doesn't linger
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED | NEW_GROUP
    else:
        kwargs["start_new_session"] = True
    log = open(os.path.join(APP_DIR, "server.log"), "ab")
    subprocess.Popen([sys.executable, os.path.join(APP_DIR, "server.py"),
                      "--port", str(port)],
                     stdout=log, stderr=log, **kwargs)


def find_chromium():
    """Return the path of a Chromium-family browser, or None."""
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            home + "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    elif sys.platform == "win32":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local = os.environ.get("LocalAppData", home + r"\AppData\Local")
        candidates = [
            pf + r"\Google\Chrome\Application\chrome.exe",
            pf86 + r"\Google\Chrome\Application\chrome.exe",
            local + r"\Google\Chrome\Application\chrome.exe",
            pf + r"\Microsoft\Edge\Application\msedge.exe",
            pf86 + r"\Microsoft\Edge\Application\msedge.exe",
        ]
    else:
        candidates = []
        for name in ("google-chrome", "google-chrome-stable", "chromium",
                     "chromium-browser", "microsoft-edge"):
            for d in os.environ.get("PATH", "").split(os.pathsep):
                p = os.path.join(d, name)
                if os.access(p, os.X_OK):
                    candidates.append(p)
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def profile_dir():
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/JobTrackerApp")
    if sys.platform == "win32":
        return os.path.join(os.environ.get("LocalAppData",
                            os.path.expanduser("~")), "JobTrackerApp")
    return os.path.expanduser("~/.config/JobTrackerApp")


def main():
    ap = argparse.ArgumentParser(description="Job Tracker launcher")
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("JOBTRACKER_PORT", 8787)))
    args = ap.parse_args()
    url = f"http://localhost:{args.port}"

    if not server_healthy(url):
        start_server(args.port)
        for _ in range(20):
            if server_healthy(url):
                break
            time.sleep(0.25)

    chrome = find_chromium()
    if chrome:
        subprocess.Popen([chrome, "--user-data-dir=" + profile_dir(),
                          "--app=" + url, "--no-first-run",
                          "--no-default-browser-check"])
    else:
        webbrowser.open(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
