#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
if [[ ! -d "$VENV" ]]; then
  echo "No D6G virtual environment is present; nothing to roll back."
  exit 0
fi
if [[ ! -f "$VENV/.ngb-d6g-owned" ]]; then
  echo "Refusing to move an unowned .venv. Inspect it and recover it manually." >&2
  exit 2
fi
backup="$ROOT/.venv.rollback.$(date +%Y%m%d%H%M%S)"
mv "$VENV" "$backup"
echo "Moved the D6G-owned environment to $backup. Rerun ./install.sh to reinstall."
