#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
case "$(uname -s)" in
  Darwin) exec "$ROOT/approve_visual_baseline_mac.sh" "$@" ;;
  Linux) exec "$ROOT/approve_visual_baseline_linux.sh" "$@" ;;
  *) echo "ERROR: supported platforms are macOS (Darwin) and Linux."; exit 1 ;;
esac
