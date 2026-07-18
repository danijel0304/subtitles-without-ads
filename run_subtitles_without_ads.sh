#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if command -v python3 >/dev/null 2>&1; then
    exec python3 subtitles_without_ads.py
elif command -v python >/dev/null 2>&1; then
    exec python subtitles_without_ads.py
else
    echo "Python was not found. Install Python 3 and run this script again." >&2
    exit 1
fi
