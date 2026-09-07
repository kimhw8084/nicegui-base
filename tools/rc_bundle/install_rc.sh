#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"

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

if [[ -d "$VENV" && ! -f "$VENV/@OWNER_MARKER@" ]]; then
  backup="$ROOT/.venv.rollback.$(date +%Y%m%d%H%M%S)"
  echo "Existing non-RC .venv detected; preserving it at $backup"
  mv "$VENV" "$backup"
fi
if [[ ! -d "$VENV" ]]; then "$PYTHON" -m venv "$VENV"; fi
if ! "$VENV/bin/python" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)
PY
then
  backup="$ROOT/.venv.rollback.$(date +%Y%m%d%H%M%S)"
  echo "Existing RC .venv has an unsupported interpreter; preserving it at $backup"
  mv "$VENV" "$backup"
  "$PYTHON" -m venv "$VENV"
fi

echo "NiceGUI Base @CANDIDATE_ID@ release-candidate install"
echo "Installing exact production requirements through the configured Python index..."
"$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt"
"$VENV/bin/python" -m pip install --no-deps "$ROOT/wheel/"*.whl
"$VENV/bin/python" -m pip check
"$VENV/bin/python" - <<'PY'
import importlib.metadata as metadata
import nicegui_base
from pathlib import Path

location = Path(nicegui_base.__file__).resolve()
if 'site-packages' not in location.parts:
    raise SystemExit(f'Import provenance is not site-packages: {location}')
print(f'Installed nicegui-base {metadata.version("nicegui-base")} from {location}')
PY
touch "$VENV/@OWNER_MARKER@"
"$VENV/bin/nicegui-base" runtime-contract
echo "Install PASS. Launch with ./run_rc.sh"
