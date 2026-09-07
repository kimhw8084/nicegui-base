#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ -n "${NGB_D5_BROWSER_PYTHON:-}" ]]; then
  exec "$NGB_D5_BROWSER_PYTHON" "$ROOT/verify_d5.py" "$@"
fi
for candidate in python3.13 python3.12 python3.11 python "$ROOT/.venv/bin/python"; do
  [[ -n "$candidate" ]] || continue
  if [[ "$candidate" == */* ]]; then [[ -x "$candidate" ]] || continue; else command -v "$candidate" >/dev/null 2>&1 || continue; fi
  if "$candidate" -c 'import sys; import playwright; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)' >/dev/null 2>&1; then
    exec "$candidate" "$ROOT/verify_d5.py" "$@"
  fi
done
echo "ERROR: focused browser smoke needs a Python 3.11–3.13 interpreter with Playwright." >&2
echo "Set NGB_D5_BROWSER_PYTHON to that interpreter, then rerun ./verify_d5.sh." >&2
exit 2
