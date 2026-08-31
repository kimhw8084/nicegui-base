#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CLI="$ROOT/.venv/bin/nicegui-base"
PY="$ROOT/.venv/bin/python"
if [[ ! -x "$CLI" ]]; then echo "Run ./setup_linux.sh first."; exit 1; fi
"$CLI" runtime-contract
"$CLI" doctor --runtime-only --port 8080 --no-require-browser
URL="http://127.0.0.1:8080"
(
  for _ in $(seq 1 100); do
    if "$PY" - "$URL/healthz" <<'PY' >/dev/null 2>&1
import sys, urllib.request
with urllib.request.urlopen(sys.argv[1], timeout=.3) as response:
    raise SystemExit(0 if 200 <= response.status < 400 else 1)
PY
    then
      if command -v xdg-open >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then xdg-open "$URL" >/dev/null 2>&1 || true; fi
      echo "NiceGUI Base lab: $URL"
      exit 0
    fi
    sleep .2
  done
) &
exec "$CLI" lab --host 127.0.0.1 --port 8080
