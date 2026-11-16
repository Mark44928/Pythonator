#!/data/data/com.termux/files/usr/bin/env bash
# Pythonator installer: verify tests, then pip install into the default prefix.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if ! command -v python >/dev/null 2>&1; then
    echo "python is required" >&2
    exit 1
fi

python -m unittest discover -s tests -q
python -m pip install .
echo "Pythonator installed. Run: pythonator"
