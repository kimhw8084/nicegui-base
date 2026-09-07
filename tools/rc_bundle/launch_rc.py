#!/usr/bin/env python3
"""Run the installed NiceGUI Base Reference Explorer release candidate."""
from __future__ import annotations

import argparse
import importlib.metadata
from pathlib import Path


EXPECTED_CANDIDATE = '@CANDIDATE_ID@'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8091)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be between 1024 and 65535')
    import nicegui_base
    package_path = Path(nicegui_base.__file__).resolve()
    if 'site-packages' not in package_path.parts:
        raise RuntimeError(f'release candidate must import from site-packages, got {package_path}')
    if importlib.metadata.version('nicegui') != '3.15.0':
        raise RuntimeError('expected nicegui==3.15.0')
    print(f'NiceGUI Base {EXPECTED_CANDIDATE}', flush=True)
    print(f'Package: {package_path}', flush=True)
    print(f'Open: http://{args.host}:{args.port}', flush=True)
    from nicegui_base.workbench.app import run_workbench
    run_workbench(host=args.host, port=args.port, show=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
