#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CLI="$ROOT/.venv/bin/nicegui-base"
if [[ ! -x "$CLI" ]]; then echo "Run ./setup_linux.sh first."; exit 1; fi
cat <<'TXT'
This freezes the screenshots from the last PASSING browser run as the approved visual baseline.
Do this only after manually reviewing the live application and certification_output/screenshots.
TXT
read -r -p "Type APPROVE to freeze this visual baseline: " ANSWER
if [[ "$ANSWER" != "APPROVE" ]]; then echo "Baseline not changed."; exit 1; fi
ARGS=(approve-baseline --output "$ROOT/certification_output" --baseline "$ROOT/visual_baseline")
if [[ -f "$ROOT/visual_baseline/BASELINE_MANIFEST.json" ]]; then ARGS+=(--force); fi
exec "$CLI" "${ARGS[@]}"
