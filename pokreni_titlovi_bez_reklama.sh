#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if command -v python3 >/dev/null 2>&1; then
    exec python3 titlovi_bez_reklama.py
elif command -v python >/dev/null 2>&1; then
    exec python titlovi_bez_reklama.py
else
    echo "Python nije pronadjen. Instalirajte Python 3 i pokrenite skriptu ponovno." >&2
    exit 1
fi
