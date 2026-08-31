#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CLI="$ROOT/.venv/bin/nicegui-base-mac-approve-baseline"
if [[ ! -x "$CLI" ]]; then echo "Run ./setup_mac.sh first."; exit 1; fi
cat <<'TXT'
This command freezes the screenshots from the last PASSING browser run as your approved local visual baseline.
Do this only after you manually review certification_output/screenshots and approve the visual design.
TXT
read -r -p "Type APPROVE to freeze this visual baseline: " ANSWER
if [[ "$ANSWER" != "APPROVE" ]]; then echo "Baseline not changed."; exit 1; fi
FORCE=""
if [[ -f "$ROOT/visual_baseline/BASELINE_MANIFEST.json" ]]; then FORCE="--force"; fi
exec "$CLI" --output "$ROOT/certification_output" --baseline "$ROOT/visual_baseline" $FORCE
