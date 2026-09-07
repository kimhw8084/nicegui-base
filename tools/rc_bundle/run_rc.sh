#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Run ./install_rc.sh first." >&2
  exit 1
fi
PORT="${NGB_RC_PORT:-8091}"
echo "NiceGUI Base @CANDIDATE_ID@ release candidate: http://127.0.0.1:$PORT"
exec "$ROOT/.venv/bin/python" "$ROOT/launch_rc.py" --port "$PORT" "$@"
