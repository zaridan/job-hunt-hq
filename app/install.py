#!/usr/bin/env python3
"""
Job Hunt HQ installer — the deterministic part of setup.

Run by the setup-job-tracker skill (any model) or by hand:

    python3 install.py --target /path/to/job-hunt-folder

Idempotent: safe to re-run; never overwrites an existing data.json or any
file the user may have edited (existing files are left untouched).

Does, in order:
 1. Creates the folder structure (Resume/Tailored, Cover Letters/Tailored,
    Company Research, Job Listings, Job Tracker App).
 2. Copies the app files (this script's siblings) into Job Tracker App/.
 3. Creates data.json ([]) if absent; marks launch.sh executable.
 4. Generates a double-clickable launcher-maker:
      macOS  -> "Make Job Tracker Launcher.command" (builds an /Applications
                app bundle, ad-hoc codesigns it, then deletes itself)
      Windows -> "Job Tracker.bat" (dropped in the root; user can pin it)
      Linux  -> "job-tracker.desktop" (dropped in the root)
 5. Prints a JSON summary so the calling assistant can verify the result.
"""
import argparse
import json
import os
import shutil
import stat
import sys

APP_FILES = ["index.html", "server.py", "launch.py", "launch.sh",
             "cleanup_applied.py", "README.md", ".gitignore"]
SUBDIRS = ["Job Tracker App", "Resume/Tailored", "Cover Letters/Tailored",
           "Company Research", "Job Listings"]

MAC_COMMAND = """#!/bin/bash
# Double-click me once. I create a "Job Tracker" app you can open from
# Spotlight or your Applications folder — then I delete myself.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="/Applications/Job Tracker.app"
mkdir -p "$APP/Contents/MacOS"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
\t<key>CFBundleName</key><string>Job Tracker</string>
\t<key>CFBundleDisplayName</key><string>Job Tracker</string>
\t<key>CFBundleIdentifier</key><string>org.jobhunthq.tracker</string>
\t<key>CFBundleVersion</key><string>1.0</string>
\t<key>CFBundlePackageType</key><string>APPL</string>
\t<key>CFBundleExecutable</key><string>launch</string>
</dict></plist>
PLIST
printf 'APPL????' > "$APP/Contents/PkgInfo"
cat > "$APP/Contents/MacOS/launch" <<SHIM
#!/bin/bash
exec "$HERE/Job Tracker App/launch.sh"
SHIM
chmod +x "$APP/Contents/MacOS/launch"
codesign --force --deep -s - "$APP"
echo "Done! Open 'Job Tracker' from Spotlight or /Applications."
open "$APP"
rm -- "$0"
"""

WIN_BAT = """@echo off
rem Double-click to open your Job Tracker. Pin me to Start for one click.
cd /d "%~dp0Job Tracker App"
start "" pyw launch.py 2>nul || py launch.py
"""

LINUX_DESKTOP = """[Desktop Entry]
Type=Application
Name=Job Tracker
Exec=python3 "{root}/Job Tracker App/launch.py"
Terminal=false
Categories=Office;
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="job-hunt root folder")
    args = ap.parse_args()
    root = os.path.abspath(os.path.expanduser(args.target))
    src = os.path.dirname(os.path.abspath(__file__))
    result = {"root": root, "created": [], "skipped": [], "launcher": None}

    for d in SUBDIRS:
        os.makedirs(os.path.join(root, d), exist_ok=True)

    appdir = os.path.join(root, "Job Tracker App")
    for f in APP_FILES:
        s, t = os.path.join(src, f), os.path.join(appdir, f)
        if not os.path.exists(s):
            continue
        if os.path.exists(t):
            result["skipped"].append(f)
        else:
            shutil.copy2(s, t)
            result["created"].append(f)

    data = os.path.join(appdir, "data.json")
    if not os.path.exists(data):
        with open(data, "w", encoding="utf-8") as fh:
            fh.write("[]")
        result["created"].append("data.json")
    else:
        result["skipped"].append("data.json")

    sh = os.path.join(appdir, "launch.sh")
    if os.path.exists(sh):
        os.chmod(sh, os.stat(sh).st_mode | stat.S_IXUSR | stat.S_IXGRP)

    # Launcher-maker per platform. The folder lives on the HOST, which may
    # differ from where this script runs (assistants run it in a Linux
    # sandbox) — so callers MUST set JOBHUNT_HOST_OS=mac|windows|linux.
    # Falls back to sys.platform for direct human runs.
    plat = os.environ.get("JOBHUNT_HOST_OS", "").lower() or sys.platform
    if plat.startswith(("darwin", "mac")):
        name = "Make Job Tracker Launcher.command"
        path = os.path.join(root, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(MAC_COMMAND)
        os.chmod(path, 0o755)
        result["launcher"] = name
    elif plat.startswith("win"):
        name = "Job Tracker.bat"
        with open(os.path.join(root, name), "w", encoding="utf-8") as fh:
            fh.write(WIN_BAT)
        result["launcher"] = name
    else:
        name = "job-tracker.desktop"
        with open(os.path.join(root, name), "w", encoding="utf-8") as fh:
            fh.write(LINUX_DESKTOP.format(root=root))
        result["launcher"] = name

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
