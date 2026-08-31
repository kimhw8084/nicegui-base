#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CLI="$ROOT/.venv/bin/nicegui-base-mac-certify"
if [[ ! -x "$CLI" ]]; then echo "Run ./setup_mac.sh first."; exit 1; fi
if ! "$ROOT/.venv/bin/python" - <<'PY' >/dev/null 2>&1
from importlib.metadata import version
raise SystemExit(0 if version('playwright') == '1.62.0' and version('Pillow') == '12.3.0' else 1)
PY
then
  echo "Browser-certification dependencies are not ready."
  echo "Run ./install_certification_deps.sh first."
  exit 1
fi
"$ROOT/.venv/bin/nicegui-base-mac-preflight" --port 8080
ARGS=(--root "$ROOT/source" --output "$ROOT/certification_output" --baseline "$ROOT/visual_baseline")
if [[ "${1:-}" == "--exhaustive" ]]; then ARGS+=(--exhaustive); shift; fi
if [[ -f "$ROOT/visual_baseline/BASELINE_MANIFEST.json" ]]; then ARGS+=(--require-baseline); fi
exec "$CLI" "${ARGS[@]}" "$@"
