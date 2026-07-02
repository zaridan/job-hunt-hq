#!/bin/bash
# Job Tracker launcher (macOS/Linux shim) — delegates to the cross-platform
# Python launcher. Called by /Applications/Job Tracker.app, or run directly:
#   ./launch.sh
# Windows users: run  py launch.py  instead (or make a shortcut to it).

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec /usr/bin/env python3 "$APP_DIR/launch.py" "$@"
