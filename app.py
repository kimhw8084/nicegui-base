"""Single-file deployment entrypoint for the complete NiceGUI Base reference app.

Standard launch::

    python app.py

The company publisher only needs to select this file.  External runtime
requirements are declared in ``requirements.txt``.  The bundled ``source``
tree is placed on ``sys.path`` before importing NiceGUI Base so this entrypoint
always launches the exact framework source shipped beside it rather than an
unrelated globally-installed version.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
_SOURCE_ROOT = _PACKAGE_ROOT / "source"
if _SOURCE_ROOT.is_dir():
    source_path = str(_SOURCE_ROOT)
    if not sys.path or sys.path[0] != source_path:
        sys.path.insert(0, source_path)

from nicegui_base.certification.live_lab import run_live_lab


def _legacy_env_name(name: str) -> str | None:
    if name.startswith("NICEGUI_BASE_"):
        return "COMPANY_UI_" + name[len("NICEGUI_BASE_"):]
    return None


def _env(name: str, fallback: str, default: str) -> str:
    """Resolve NiceGUI Base, then deprecated legacy, then platform settings."""
    legacy = _legacy_env_name(name)
    return os.environ.get(name) or (os.environ.get(legacy) if legacy else None) or os.environ.get(fallback) or default


def _root_path() -> str:
    """Resolve an optional reverse-proxy mount path used by company publishers.

    The explicit NiceGUI Base variable wins. Common platform variables are
    accepted so a publisher can mount the app below e.g. ``/my-app`` without
    editing source. An empty value means the app is served at ``/``.
    """
    raw = (
        os.environ.get("NICEGUI_BASE_ROOT_PATH")
        or os.environ.get("COMPANY_UI_ROOT_PATH")
        or os.environ.get("ROOT_PATH")
        or os.environ.get("SCRIPT_NAME")
        or os.environ.get("APPLICATION_ROOT")
        or os.environ.get("MOUNT_PATH")
        or ""
    ).strip()
    if raw in {"", "/"}:
        return ""
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw.rstrip("/")


def _port() -> int:
    raw = _env("NICEGUI_BASE_PORT", "PORT", "8080")
    try:
        port = int(raw)
    except ValueError as exc:
        raise SystemExit(f"Invalid port {raw!r}: expected an integer from NICEGUI_BASE_PORT or PORT") from exc
    if not 1 <= port <= 65535:
        raise SystemExit(f"Invalid port {port}: expected 1..65535")
    return port


def main() -> None:
    """Launch the exact full NiceGUI Base live reference application."""
    run_live_lab(
        host=_env("NICEGUI_BASE_HOST", "HOST", "0.0.0.0"),
        port=_port(),
        show=False,
        root_path=_root_path(),
    )


if __name__ == "__main__":
    main()
