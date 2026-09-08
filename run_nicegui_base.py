#!/usr/bin/env python3
"""The one human starting file for NiceGUI Base.

Company usage:
    python run_nicegui_base.py

This file intentionally contains no UI implementation. It only makes a source
checkout importable and delegates to the canonical package launcher.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = REPO_ROOT / "source"

# Source checkout: no editable install is required. Installed distribution:
# if ./source is absent, normal Python package resolution is used unchanged.
if SOURCE_ROOT.is_dir():
    sys.path.insert(0, str(SOURCE_ROOT))

from nicegui_base.workbench.launcher import main


if __name__ == "__main__":
    raise SystemExit(main())
