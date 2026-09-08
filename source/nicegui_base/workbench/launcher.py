from __future__ import annotations

"""Canonical human launcher for the NiceGUI Base Reference Explorer.

All UI registration remains owned by ``nicegui_base.workbench.app.run_workbench``.
This module only owns startup validation and human-friendly launch configuration.
"""

import argparse
import importlib.metadata
import os
import socket
import sys
from dataclasses import dataclass

SUPPORTED_PYTHON = ">=3.11,<3.14"
REQUIRED_NICEGUI = "3.15.0"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8091

_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"0", "false", "no", "off"})


class LauncherError(RuntimeError):
    """Human-readable startup contract failure."""


@dataclass(frozen=True, slots=True)
class LaunchConfig:
    host: str
    port: int
    show: bool
    check_only: bool


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().casefold()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise LauncherError(
        f"{name} must be one of 1/0, true/false, yes/no, on/off; got {raw!r}."
    )


def _env_port() -> int:
    raw = os.getenv("NICEGUI_BASE_PORT", str(DEFAULT_PORT)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise LauncherError(f"NICEGUI_BASE_PORT must be an integer; got {raw!r}.") from exc
    if not 1 <= value <= 65535:
        raise LauncherError(f"NICEGUI_BASE_PORT must be between 1 and 65535; got {value}.")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python run_nicegui_base.py",
        description=(
            "Launch the NiceGUI Base Reference Explorer using the current company Python environment."
        ),
    )
    parser.add_argument(
        "--host",
        default=os.getenv("NICEGUI_BASE_HOST", DEFAULT_HOST),
        help=f"Bind host (NICEGUI_BASE_HOST; default {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_env_port(),
        help=f"Bind port (NICEGUI_BASE_PORT; default {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--show",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("NICEGUI_BASE_SHOW", False),
        help="Open a browser automatically (NICEGUI_BASE_SHOW; default false).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate Python, NiceGUI, and NiceGUI Base imports, then exit.",
    )
    return parser


def _config(argv: list[str] | None = None) -> LaunchConfig:
    args = _parser().parse_args(argv)
    host = str(args.host).strip()
    if not host:
        raise LauncherError("--host / NICEGUI_BASE_HOST cannot be empty.")
    port = int(args.port)
    if not 1 <= port <= 65535:
        raise LauncherError(f"--port must be between 1 and 65535; got {port}.")
    return LaunchConfig(host=host, port=port, show=bool(args.show), check_only=bool(args.check))


def _validate_python() -> None:
    version = sys.version_info
    if not ((3, 11) <= version[:2] < (3, 14)):
        raise LauncherError(
            "NiceGUI Base requires Python >=3.11,<3.14. "
            f"This interpreter is {version.major}.{version.minor}.{version.micro} "
            f"at {sys.executable}."
        )


def _validate_nicegui() -> str:
    try:
        version = importlib.metadata.version("nicegui")
    except importlib.metadata.PackageNotFoundError as exc:
        raise LauncherError(
            "NiceGUI is not installed in the Python environment running this file. "
            f"Interpreter: {sys.executable}. Required: nicegui=={REQUIRED_NICEGUI}."
        ) from exc
    if version != REQUIRED_NICEGUI:
        raise LauncherError(
            f"NiceGUI Base requires nicegui=={REQUIRED_NICEGUI}; this environment has "
            f"nicegui=={version}. Interpreter: {sys.executable}."
        )
    return version


def _framework_identity() -> tuple[str, str]:
    try:
        from nicegui_base.version import FRAMEWORK_VERSION
        from nicegui_base.workbench.update_identity import BUILD_ID
    except Exception as exc:
        raise LauncherError(
            "NiceGUI Base could not be imported. Run this file from the NiceGUI Base "
            "repository root, or install nicegui-base into the current company Python environment."
        ) from exc
    return str(FRAMEWORK_VERSION), str(BUILD_ID)


def _port_is_available(host: str, port: int) -> bool:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
    except OSError:
        return False
    return True


def _print_banner(
    config: LaunchConfig,
    *,
    nicegui_version: str,
    framework_version: str,
    build_id: str,
) -> None:
    browser_host = "127.0.0.1" if config.host in {"0.0.0.0", "::"} else config.host
    print()
    print("=" * 68)
    print("NiceGUI Base Reference Explorer")
    print(f"Build            : {build_id}")
    print(f"Framework        : {framework_version}")
    print(f"NiceGUI          : {nicegui_version}")
    print(f"Python           : {sys.version.split()[0]}")
    print(f"Interpreter      : {sys.executable}")
    print(f"URL              : http://{browser_host}:{config.port}")
    print(f"Bind             : {config.host}:{config.port}")
    print(f"Open browser     : {'yes' if config.show else 'no'}")
    print(
        "Storage secret   : "
        + (
            "NICEGUI_BASE_STORAGE_SECRET"
            if os.getenv("NICEGUI_BASE_STORAGE_SECRET")
            else "runtime-generated ephemeral"
        )
    )
    print("=" * 68)
    print()


def validate_environment(config: LaunchConfig) -> tuple[str, str, str]:
    _validate_python()
    nicegui_version = _validate_nicegui()
    framework_version, build_id = _framework_identity()
    if not config.check_only and not _port_is_available(config.host, config.port):
        raise LauncherError(
            f"Cannot bind {config.host}:{config.port}. The port may already be in use "
            "or the host may not exist in this environment. Set NICEGUI_BASE_PORT "
            "or pass --port."
        )
    return nicegui_version, framework_version, build_id


def main(argv: list[str] | None = None) -> int:
    try:
        config = _config(argv)
        nicegui_version, framework_version, build_id = validate_environment(config)
        _print_banner(
            config,
            nicegui_version=nicegui_version,
            framework_version=framework_version,
            build_id=build_id,
        )

        if config.check_only:
            print("ENVIRONMENT CHECK: PASS")
            return 0

        from nicegui_base.workbench.app import run_workbench

        # Keep this call exactly aligned with run_workbench's supported signature.
        # Storage-secret handling belongs to run_workbench itself through
        # NICEGUI_BASE_STORAGE_SECRET; it is not a run_workbench keyword argument.
        run_workbench(
            host=config.host,
            port=config.port,
            show=config.show,
        )
        return 0
    except LauncherError as exc:
        print(f"STARTUP CHECK FAILED: {exc}", file=sys.stderr)
        return 2


__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "LaunchConfig",
    "LauncherError",
    "REQUIRED_NICEGUI",
    "SUPPORTED_PYTHON",
    "main",
    "validate_environment",
]
