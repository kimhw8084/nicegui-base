#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
OWNER="$VENV/.ngb-d5-owned"

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

if [[ -e "$VENV" && ! -f "$OWNER" ]]; then
  backup="$ROOT/.venv.rollback.$(date +%Y%m%d%H%M%S)"
  if [[ -e "$backup" ]]; then
    echo "Refusing to overwrite existing rollback target: $backup" >&2
    exit 2
  fi
  echo "Existing unmanaged .venv detected; preserving it at $backup"
  mv "$VENV" "$backup"
fi
if [[ -d "$VENV" ]]; then
  if ! "$VENV/bin/python" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)
PY
  then
    backup="$ROOT/.venv.rollback.$(date +%Y%m%d%H%M%S)"
    if [[ -e "$backup" ]]; then
      echo "Refusing to overwrite existing rollback target: $backup" >&2
      exit 2
    fi
    echo "Existing D5 environment has an unsupported interpreter; preserving it at $backup"
    mv "$VENV" "$backup"
  fi
fi
if [[ ! -d "$VENV" ]]; then
  "$PYTHON" -m venv "$VENV"
fi

echo "NiceGUI Base @D5_PACKAGE_ID@ team package for @RC_CANDIDATE_ID@"
echo "Installing exact production requirements through the configured Python index..."
"$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt"
"$VENV/bin/python" -m pip install --no-deps --force-reinstall "$ROOT/wheel/"*.whl
"$VENV/bin/python" -m pip check
"$VENV/bin/python" - <<'PY'
import importlib.metadata as metadata
from pathlib import Path
import nicegui_base

location = Path(nicegui_base.__file__).resolve()
if 'site-packages' not in location.parts:
    raise SystemExit(f'Import provenance is not site-packages: {location}')
if metadata.version('nicegui') != '3.15.0' or metadata.version('nicegui-base') != '3.0.0a8':
    raise SystemExit('Installed version contract is not NiceGUI Base 3.0.0a8 / NiceGUI 3.15.0')
print(f'Installed nicegui-base {metadata.version("nicegui-base")} from {location}')
PY
touch "$OWNER"
"$VENV/bin/nicegui-base" runtime-contract
echo "Install PASS. Launch with ./launch_d5.sh"
