#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
MARKER="$VENV/.ngb-d6g-owned"

find_python() {
  for candidate in "${NICEGUI_BASE_PYTHON:-}" python3.13 python3.12 python3.11 python3; do
    [[ -n "$candidate" ]] || continue
    if [[ "$candidate" == */* ]]; then [[ -x "$candidate" ]] || continue; else command -v "$candidate" >/dev/null 2>&1 || continue; fi
    if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)
PY
    then echo "$candidate"; return 0; fi
  done
  return 1
}

PYTHON="$(find_python || true)"
if [[ -z "$PYTHON" ]]; then
  echo "ERROR: Python 3.11, 3.12, or 3.13 is required." >&2
  exit 2
fi

if [[ -d "$VENV" && ! -f "$MARKER" ]]; then
  backup="$ROOT/.venv.rollback.$(date +%Y%m%d%H%M%S)"
  echo "Existing unowned .venv detected; preserving it at $backup"
  mv "$VENV" "$backup"
fi
if [[ ! -d "$VENV" ]]; then "$PYTHON" -m venv "$VENV"; fi
if ! "$VENV/bin/python" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)
PY
then
  backup="$ROOT/.venv.rollback.$(date +%Y%m%d%H%M%S)"
  echo "Existing D6G environment has an unsupported interpreter; preserving it at $backup"
  mv "$VENV" "$backup"
  "$PYTHON" -m venv "$VENV"
fi

echo "NiceGUI Base @D6G_ID@ golden candidate"
echo "Installing exact production requirements..."
"$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt"
"$VENV/bin/python" -m pip install --no-deps "$ROOT/wheel/"*.whl
"$VENV/bin/python" -m pip check
"$VENV/bin/python" - <<'PY'
import importlib.metadata as metadata
from pathlib import Path
import nicegui_base

location = Path(nicegui_base.__file__).resolve()
if 'site-packages' not in location.parts:
    raise SystemExit(f'Import provenance is not site-packages: {location}')
if metadata.version('nicegui-base') != '3.0.0a8' or metadata.version('nicegui') != '3.15.0':
    raise SystemExit('installed framework/runtime version mismatch')
print(f'Installed nicegui-base {metadata.version("nicegui-base")} from {location}')
PY
touch "$MARKER"
echo "Install PASS. Launch with ./launch.sh; verify with ./verify.sh"
