#!/usr/bin/env python3
"""Launch the installed D4 RC with an explicit D5 team-package identity."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8091)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be between 1024 and 65535')
    root = Path(__file__).resolve().parent
    identity = json.loads((root / 'RC_IDENTITY.json').read_text(encoding='utf-8'))
    import nicegui_base
    package_path = Path(nicegui_base.__file__).resolve()
    if 'site-packages' not in package_path.parts:
        raise RuntimeError(f'release candidate must import from site-packages, got {package_path}')
    if importlib.metadata.version('nicegui') != identity['nicegui_version']:
        raise RuntimeError('installed NiceGUI version does not match RC identity')
    print(f"NiceGUI Base {identity['d5_package_id']} team package / RC {identity['rc_candidate_id']}", flush=True)
    print(f'Package: {package_path}', flush=True)
    print(f'Open: http://{args.host}:{args.port}', flush=True)
    from nicegui_base.workbench.app import run_workbench
    run_workbench(host=args.host, port=args.port, show=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
