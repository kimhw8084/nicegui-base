#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"

for required_cmd in sha256sum; do
  if ! command -v "$required_cmd" >/dev/null 2>&1; then
    echo "ERROR: required Linux command '$required_cmd' is not available."
    exit 1
  fi
done

find_python() {
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)
PY
    then echo "$candidate"; return 0; fi
  done
  return 1
}
PYTHON="$(find_python || true)"
if [[ -z "$PYTHON" ]]; then echo "ERROR: Python 3.11, 3.12, or 3.13 is required."; exit 1; fi
BASE_PY_MM="$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
venv_interpreter_ok() {
  [[ -x "$VENV/bin/python" ]] || return 1
  VENV="$VENV" BASE_PY_MM="$BASE_PY_MM" "$VENV/bin/python" - <<'PY' >/dev/null 2>&1
import os, pathlib, sys
expected = pathlib.Path(os.environ['VENV']).resolve()
actual = pathlib.Path(sys.prefix).resolve()
version = f"{sys.version_info.major}.{sys.version_info.minor}"
raise SystemExit(0 if actual == expected and version == os.environ['BASE_PY_MM'] and (3,11) <= sys.version_info[:2] < (3,14) else 1)
PY
}
if [[ -d "$VENV" ]] && ! venv_interpreter_ok; then
  echo "Existing .venv does not match the selected supported Python ($BASE_PY_MM); rebuilding it."
  rm -rf "$VENV"
fi

WHEEL="$(find "$ROOT/wheel" -maxdepth 1 -name 'nicegui_base-3.0.0a8-*.whl' -print -quit)"
if [[ -z "$WHEEL" ]]; then echo "ERROR: NiceGUI Base v3.0.0a8 wheel not found under $ROOT/wheel"; exit 1; fi

echo "NiceGUI Base Linux setup"
echo "  kernel: $(uname -sr)"
echo "  architecture: $(uname -m)"
echo "  python: $($PYTHON --version 2>&1)"
if [[ -f "$ROOT/SHA256SUMS.txt" ]]; then (cd "$ROOT" && sha256sum -c SHA256SUMS.txt); fi
if [[ ! -d "$VENV" ]]; then
  if ! "$PYTHON" -m venv "$VENV"; then
    echo "ERROR: Python venv creation failed. On some Linux distributions install the matching python3-venv package or use the approved company Python distribution."
    exit 1
  fi
fi
if ! venv_interpreter_ok; then echo "ERROR: failed to create a compatible package-local .venv"; exit 1; fi

REQ="$ROOT/requirements.txt"
if [[ ! -f "$REQ" ]]; then
  echo "ERROR: production requirements file not found: $REQ"
  exit 1
fi

echo "Installing production runtime from requirements.txt using the configured company Python package index..."
echo "  requirements: $REQ"
echo "  pip: $($VENV/bin/python -m pip --version)"
if ! "$VENV/bin/python" -m pip install -r "$REQ"; then
  echo
  echo "ERROR: company-index dependency resolution failed. Diagnostic context:"
  "$VENV/bin/python" -m pip config list || true
  "$VENV/bin/python" -m pip index versions nicegui || true
  echo "The deployment contract does not use public-PyPI or bundled-wheel fallbacks."
  exit 1
fi

echo "Installing the NiceGUI Base wheel without re-resolving external dependencies..."
PIP_FORCE_REINSTALL=1 "$VENV/bin/python" -m pip install --no-deps "$WHEEL"

mkdir -p "$ROOT/certification_output" "$ROOT/visual_baseline"
echo
echo "Verifying exact NiceGUI 3.15 runtime API contract..."
"$VENV/bin/nicegui-base" runtime-contract
echo
echo "Running Linux/platform preflight..."
"$VENV/bin/nicegui-base" doctor --runtime-only --ignore-port --port 8080 --no-require-browser
echo
echo "Starting the real installed NiceGUI server and smoke-testing every live route..."
"$VENV/bin/nicegui-base" runtime-smoke --output "$ROOT/certification_output/runtime_smoke"
echo
echo "SETUP COMPLETE"
echo "Run: ./run_lab.sh"
echo "Then: ./certify_linux.sh"
