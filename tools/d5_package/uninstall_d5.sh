#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
if [[ ! -e "$VENV" ]]; then
  echo "No D5-owned environment is present; nothing to uninstall."
  exit 0
fi
if [[ ! -f "$VENV/.ngb-d5-owned" ]]; then
  echo "Refusing to move an unowned .venv. Inspect it and recover it manually." >&2
  exit 2
fi
backup="$ROOT/.venv.rollback.$(date +%Y%m%d%H%M%S)"
if [[ -e "$backup" ]]; then
  echo "Refusing to overwrite existing rollback target: $backup" >&2
  exit 2
fi
mv "$VENV" "$backup"
echo "Removed the active D5 environment by moving it to $backup. No unrelated files were touched."
