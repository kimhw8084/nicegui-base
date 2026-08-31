#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CLI="$ROOT/.venv/bin/nicegui-base"
PY="$ROOT/.venv/bin/python"
CERT_REQ="$ROOT/requirements-certification.txt"
if [[ ! -x "$CLI" || ! -x "$PY" ]]; then echo "Run ./setup_linux.sh first."; exit 1; fi
if ! "$PY" -c 'import playwright, PIL' >/dev/null 2>&1; then
  echo "Browser certification dependencies are not installed."
  echo "Install them from the company package index only:"
  echo "  $PY -m pip install -r $CERT_REQ"
  exit 1
fi
ARGS=(certify --root "$ROOT/source" --output "$ROOT/certification_output" --baseline "$ROOT/visual_baseline")
if [[ -f "$ROOT/visual_baseline/BASELINE_MANIFEST.json" ]]; then ARGS+=(--require-baseline); fi
exec "$CLI" "${ARGS[@]}" "$@"
