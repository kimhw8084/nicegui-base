#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ -n "${NGB_D6G_BROWSER_PYTHON:-}" ]]; then
  exec "$NGB_D6G_BROWSER_PYTHON" "$ROOT/verify.py" "$@"
fi
for candidate in python3.13 python3.12 python3.11 "$ROOT/.venv/bin/python"; do
  [[ -n "$candidate" ]] || continue
  if [[ "$candidate" == */* ]]; then [[ -x "$candidate" ]] || continue; else command -v "$candidate" >/dev/null 2>&1 || continue; fi
  if "$candidate" -c 'import sys; import playwright; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)' >/dev/null 2>&1; then
    exec "$candidate" "$ROOT/verify.py" "$@"
  fi
done
echo "ERROR: focused browser verification needs Playwright. Set NGB_D6G_BROWSER_PYTHON to a Python 3.11–3.13 interpreter with approved Playwright tooling." >&2
exit 2
