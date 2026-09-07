#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Run ./install.sh first." >&2
  exit 1
fi
PORT="${NGB_D6G_PORT:-8091}"
echo "NiceGUI Base @D6G_ID@ golden candidate: http://127.0.0.1:$PORT"
exec "$ROOT/.venv/bin/python" "$ROOT/launch.py" --port "$PORT" "$@"
