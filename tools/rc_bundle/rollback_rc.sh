#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
if [[ ! -d "$VENV" ]]; then
  echo "No RC virtual environment is present; nothing to roll back."
  exit 0
fi
if [[ ! -f "$VENV/@OWNER_MARKER@" ]]; then
  echo "Refusing to move an unowned .venv. Inspect it and recover it manually." >&2
  exit 2
fi
backup="$ROOT/.venv.rollback.$(date +%Y%m%d%H%M%S)"
mv "$VENV" "$backup"
echo "Moved the RC-owned environment to $backup. Re-run ./install_rc.sh to recover the candidate."
