#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ ! -x "$ROOT/.venv/bin/python" || ! -f "$ROOT/.venv/.ngb-d5-owned" ]]; then
  echo "Run ./install_d5.sh first." >&2
  exit 1
fi
PORT="${NGB_D5_PORT:-8091}"
echo "NiceGUI Base @D5_PACKAGE_ID@ team package for @RC_CANDIDATE_ID@: http://127.0.0.1:$PORT"
exec "$ROOT/.venv/bin/python" "$ROOT/launch_d5.py" --port "$PORT" "$@"
