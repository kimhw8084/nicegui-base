#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CLI="$ROOT/.venv/bin/nicegui-base-mac-lab"
PY="$ROOT/.venv/bin/python"
[[ -x "$CLI" ]] || { echo "Run ./setup_mac.sh first."; exit 1; }
"$ROOT/.venv/bin/nicegui-base" runtime-contract
"$ROOT/.venv/bin/nicegui-base" doctor --runtime-only --port 8080 --no-require-browser
URL="http://127.0.0.1:8080"
IDENTITY="$URL/_nicegui_base/workbench"
(
  for _ in $(seq 1 80); do
    if "$PY" -m nicegui_base.workbench.readiness "$IDENTITY" >/dev/null 2>&1; then
      if [[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then open -a "Google Chrome" "$URL"; else open "$URL"; fi
      exit 0
    fi
    sleep 0.25
  done
  echo "ERROR: NiceGUI Base Workbench identity/readiness was not confirmed at $IDENTITY" >&2
) &
exec "$CLI" --host 127.0.0.1 --port 8080
