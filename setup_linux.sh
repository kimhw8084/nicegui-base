#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
command -v sha256sum >/dev/null 2>&1 || { echo "ERROR: required Linux command 'sha256sum' is not available."; exit 1; }
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
verify_package_manifest() {
  local manifest="$ROOT/PACKAGE_SHA256SUMS.txt"
  [[ -f "$manifest" ]] || { echo "ERROR: package checksum manifest not found: $manifest"; return 1; }
  echo "Verifying immutable package files..."
  (cd "$ROOT" && sha256sum -c PACKAGE_SHA256SUMS.txt)
}

verify_source_manifest() {
  local manifest="$ROOT/source/SHA256SUMS.txt"
  [[ -f "$manifest" ]] || { echo "ERROR: source checksum manifest not found: $manifest"; return 1; }
  echo "Verifying immutable source files..."
  (cd "$ROOT/source" && sha256sum -c SHA256SUMS.txt)
}
PYTHON="$(find_python || true)"; [[ -n "$PYTHON" ]] || { echo "ERROR: Python 3.11, 3.12, or 3.13 is required."; exit 1; }
BASE_PY_MM="$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
venv_interpreter_ok() {
  [[ -x "$VENV/bin/python" ]] || return 1
  VENV="$VENV" BASE_PY_MM="$BASE_PY_MM" "$VENV/bin/python" - <<'PY' >/dev/null 2>&1
import os, pathlib, sys
raise SystemExit(0 if pathlib.Path(sys.prefix).resolve() == pathlib.Path(os.environ['VENV']).resolve() and f"{sys.version_info.major}.{sys.version_info.minor}" == os.environ['BASE_PY_MM'] and (3,11) <= sys.version_info[:2] < (3,14) else 1)
PY
}
if [[ -d "$VENV" ]] && ! venv_interpreter_ok; then echo "Existing .venv does not match the selected supported Python ($BASE_PY_MM); rebuilding it."; rm -rf "$VENV"; fi
WHEEL="$(find "$ROOT/wheel" -maxdepth 1 -name 'nicegui_base-3.0.0a8-*.whl' -print -quit)"; [[ -n "$WHEEL" ]] || { echo "ERROR: NiceGUI Base v3.0.0a8 wheel not found under $ROOT/wheel"; exit 1; }
REQ="$ROOT/requirements.txt"; [[ -f "$REQ" ]] || { echo "ERROR: production requirements file not found: $REQ"; exit 1; }
echo "NiceGUI Base Linux setup"; echo "  kernel: $(uname -sr)"; echo "  architecture: $(uname -m)"; echo "  python: $($PYTHON --version 2>&1)"
verify_package_manifest
verify_source_manifest
if [[ ! -d "$VENV" ]]; then "$PYTHON" -m venv "$VENV" || { echo "ERROR: Python venv creation failed."; exit 1; }; fi
venv_interpreter_ok || { echo "ERROR: failed to create a compatible package-local .venv"; exit 1; }
echo "Installing production runtime from requirements.txt using the configured company Python package index..."
"$VENV/bin/python" -m pip install -r "$REQ" || { echo "ERROR: company-index dependency resolution failed."; exit 1; }
PIP_FORCE_REINSTALL=1 "$VENV/bin/python" -m pip install --no-deps "$WHEEL"
mkdir -p "$ROOT/certification_output" "$ROOT/visual_baseline"
"$VENV/bin/nicegui-base" runtime-contract
"$VENV/bin/nicegui-base" doctor --runtime-only --ignore-port --port 8080 --no-require-browser
"$VENV/bin/nicegui-base" runtime-smoke --output "$ROOT/certification_output/runtime_smoke"
echo "SETUP COMPLETE"; echo "Run: ./run_lab.sh"; echo "Then: ./certify_linux.sh"
