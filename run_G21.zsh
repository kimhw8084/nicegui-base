#!/bin/zsh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PORT="${1:-8091}"
PY="$HERE/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "ERROR: $PY not found. Run from the NiceGUI Base repository with its qualified .venv."
  exit 2
fi
"$PY" - <<'PY'
from importlib.metadata import version
assert version('nicegui') == '3.15.0', version('nicegui')
PY
STATE_ROOT="$HOME/.local/state/nicegui-base/g21-reference-explorer"
mkdir -p "$STATE_ROOT"
SECRET_FILE="$STATE_ROOT/storage_secret"
if [[ ! -f "$SECRET_FILE" ]]; then
  "$PY" - <<'PY' > "$SECRET_FILE"
import secrets
print(secrets.token_urlsafe(48))
PY
  chmod 600 "$SECRET_FILE"
fi
export NICEGUI_STORAGE_SECRET="$(cat "$SECRET_FILE")"
export PYTHONPATH="$HERE/source"
cd "$STATE_ROOT"
exec "$PY" - "$PORT" <<'PY'
import sys
from nicegui_base.workbench.app import run_workbench
from nicegui_base.workbench.update_identity import BUILD_ID
port=int(sys.argv[1])
if BUILD_ID != 'NGB-20260907-G2.1':
    raise SystemExit(f'Wrong source identity: {BUILD_ID}')
print(f'NiceGUI Base {BUILD_ID} -> http://127.0.0.1:{port}', flush=True)
run_workbench(host='127.0.0.1', port=port, show=False)
PY
