#!/usr/bin/env python3
"""Launch the installed NiceGUI Base Workbench for the D6G distribution."""
from __future__ import annotations

import argparse
from pathlib import Path

EXPECTED_CANDIDATE = '@D6G_ID@'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8091)
    args = parser.parse_args()
    import nicegui_base
    package_path = Path(nicegui_base.__file__).resolve()
    if 'site-packages' not in package_path.parts:
        raise RuntimeError(f'release candidate must import from site-packages, got {package_path}')
    print(f'NiceGUI Base {EXPECTED_CANDIDATE}', flush=True)
    print(f'Package: {package_path}', flush=True)
    from nicegui_base.workbench.app import run_workbench
    run_workbench(host=args.host, port=args.port, show=False)


if __name__ == '__main__':
    main()
