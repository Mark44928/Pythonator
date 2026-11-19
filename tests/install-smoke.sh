#!/data/data/com.termux/files/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="${TMPDIR:-${RUNNER_TEMP:-$HOME/.cache}}/pythonator-install-smoke.$$"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/home" "$TMP/data" "$TMP/prefix"
export HOME="$TMP/home" XDG_DATA_HOME="$TMP/data" PREFIX="$TMP/prefix"

bash "$ROOT/install.sh" >/dev/null
test -L "$TMP/prefix/bin/pythonator"
"$TMP/prefix/bin/pythonator" --eval "2+3*4" | grep -Fxq "14"
bash "$ROOT/install.sh" --uninstall >/dev/null
test ! -e "$TMP/prefix/bin/pythonator"
test ! -e "$TMP/data/pythonator/venv"
custom="$TMP/custom"
bash "$ROOT/install.sh" --prefix "$custom" >/dev/null
test -L "$custom/bin/pythonator"
bash "$ROOT/install.sh" --uninstall >/dev/null
test ! -e "$custom/bin/pythonator"
echo "installer smoke OK"
