#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CLI="$ROOT/.venv/bin/nicegui-base"
PY="$ROOT/.venv/bin/python"
[[ -x "$CLI" ]] || { echo "Run ./setup_linux.sh first."; exit 1; }
"$CLI" runtime-contract
"$CLI" doctor --runtime-only --port 8080 --no-require-browser
URL="http://127.0.0.1:8080"
IDENTITY="$URL/_nicegui_base/workbench"
(
  for _ in $(seq 1 100); do
    if "$PY" -m nicegui_base.workbench.readiness "$IDENTITY" >/dev/null 2>&1; then
      if command -v xdg-open >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then xdg-open "$URL" >/dev/null 2>&1 || true; fi
      echo "NiceGUI Base Workbench: $URL"; exit 0
    fi
    sleep .2
  done
  echo "ERROR: NiceGUI Base Workbench identity/readiness was not confirmed at $IDENTITY" >&2
) &
exec "$CLI" lab --host 127.0.0.1 --port 8080
