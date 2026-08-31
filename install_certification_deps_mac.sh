#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
REQ="$ROOT/requirements-certification.txt"
if [[ ! -x "$VENV/bin/python" ]]; then echo "Run ./setup_mac.sh first."; exit 1; fi
if [[ ! -f "$REQ" ]]; then echo "ERROR: certification requirements file not found: $REQ"; exit 1; fi
echo "Installing browser-certification dependencies from the configured company Python package index..."
"$VENV/bin/python" -m pip install -r "$REQ"
echo "Running browser-certification preflight..."
"$VENV/bin/nicegui-base-mac-preflight" --port 8080
echo "CERTIFICATION DEPENDENCIES READY"
