from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import os
import platform
import shutil
import socket
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from nicegui_base.certification.mac_coverage import coverage_summary
from nicegui_base.runtime.compatibility import load_compatibility_manifest
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION
from nicegui_base.visual import validate_visual_package


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    key: str
    status: str
    detail: str
    required: bool = True


CHROME_PATH = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
EDGE_PATH = Path('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')
PLAYWRIGHT_VERSION = '1.62.0'
PILLOW_VERSION = '12.3.0'


def _package_version(name: str) -> str | None:
    try: return metadata.version(name)
    except metadata.PackageNotFoundError: return None


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: sock.bind(('127.0.0.1', port)); return True
        except OSError: return False


def run_preflight(*, port: int = 8080, require_chrome: bool = True, require_edge: bool = False) -> tuple[PreflightCheck, ...]:
    checks: list[PreflightCheck] = []
    py = sys.version_info
    checks.append(PreflightCheck('python','pass' if (3,11) <= (py.major,py.minor) < (3,14) else 'fail',f'Python {platform.python_version()}; supported >=3.11,<3.14'))
    is_mac = sys.platform == 'darwin'
    checks.append(PreflightCheck('platform','pass' if is_mac else 'warning',f'{platform.system()} {platform.machine()}',required=False))
    checks.append(PreflightCheck('framework','pass',f'NiceGUI Base {FRAMEWORK_VERSION}'))
    nicegui = _package_version('nicegui')
    checks.append(PreflightCheck('nicegui','pass' if nicegui == NICEGUI_VERSION else 'fail',f'installed={nicegui or "missing"}; required={NICEGUI_VERSION}'))
    playwright = _package_version('playwright')
    checks.append(PreflightCheck('playwright','pass' if playwright == PLAYWRIGHT_VERSION else 'fail',f'installed={playwright or "missing"}; required={PLAYWRIGHT_VERSION}',required=True))
    pillow = _package_version('Pillow')
    checks.append(PreflightCheck('pillow','pass' if pillow == PILLOW_VERSION else 'fail',f'installed={pillow or "missing"}; required={PILLOW_VERSION}',required=True))
    chrome = CHROME_PATH.exists()
    checks.append(PreflightCheck('chrome','pass' if chrome else ('fail' if require_chrome else 'warning'),str(CHROME_PATH),required=require_chrome))
    edge = EDGE_PATH.exists()
    checks.append(PreflightCheck('edge','pass' if edge else ('fail' if require_edge else 'warning'),str(EDGE_PATH),required=require_edge))
    checks.append(PreflightCheck('port','pass' if _port_available(port) else 'fail',f'127.0.0.1:{port} is {"available" if _port_available(port) else "already in use"}'))
    asset_issues = validate_visual_package()
    checks.append(PreflightCheck('visual-assets','pass' if not asset_issues else 'fail',f'{len(asset_issues)} visual asset validation issue(s)'))
    coverage = coverage_summary()
    checks.append(PreflightCheck('lab-coverage','pass' if not coverage['uncovered'] else 'fail',f"{coverage['covered_visual_components']}/{coverage['required_visual_components']} public visual integration classes mapped to live lab routes"))
    compatibility = load_compatibility_manifest()
    checks.append(PreflightCheck('compatibility','pass' if compatibility.get('nicegui_version') == NICEGUI_VERSION else 'fail',f"manifest NiceGUI={compatibility.get('nicegui_version')}"))
    free = shutil.disk_usage(Path.home()).free
    checks.append(PreflightCheck('disk','pass' if free >= 1_000_000_000 else 'warning',f'{free/1_000_000_000:.1f} GB free',required=False))
    return tuple(checks)


def main() -> int:
    p=argparse.ArgumentParser(description='NiceGUI Base Mac live-certification preflight')
    p.add_argument('--port',type=int,default=8080)
    p.add_argument('--require-edge',action='store_true')
    p.add_argument('--no-require-chrome',action='store_true')
    p.add_argument('--format',choices=('text','json'),default='text')
    a=p.parse_args()
    checks=run_preflight(port=a.port,require_chrome=not a.no_require_chrome,require_edge=a.require_edge)
    failed=[c for c in checks if c.required and c.status=='fail']
    if a.format=='json': print(json.dumps({'ok':not failed,'checks':[asdict(c) for c in checks]},indent=2))
    else:
        for c in checks: print(f'[{c.status.upper():7}] {c.key:16} {c.detail}')
        print(f'\nMac preflight: {"PASS" if not failed else "FAIL"}')
    return 0 if not failed else 1


if __name__=='__main__': raise SystemExit(main())
