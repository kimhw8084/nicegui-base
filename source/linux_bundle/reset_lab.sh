#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$ROOT/certification_output"; mkdir -p "$ROOT/certification_output"
echo "Certification output cleared. Approved baseline preserved."
if [[ "${1:-}" == "--including-baseline" ]]; then rm -rf "$ROOT/visual_baseline"; mkdir -p "$ROOT/visual_baseline"; echo "Visual baseline cleared."; fi
