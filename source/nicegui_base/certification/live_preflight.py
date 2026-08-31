from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from nicegui_base.certification.mac_coverage import coverage_summary
from nicegui_base.certification.nicegui_runtime_contract import run_installed_runtime_contract
from nicegui_base.runtime.compatibility import load_compatibility_manifest
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION
from nicegui_base.visual import validate_visual_package

PLAYWRIGHT_VERSION='1.62.0'
PILLOW_VERSION='12.3.0'

@dataclass(frozen=True,slots=True)
class PreflightCheck:
    key:str; status:str; detail:str; required:bool=True

@dataclass(frozen=True,slots=True)
class BrowserInstall:
    key:str; name:str; executable:str; version:str|None=None


def _package_version(name:str)->str|None:
    try:return metadata.version(name)
    except metadata.PackageNotFoundError:return None


def _first_existing(candidates:list[str|Path])->str|None:
    for candidate in candidates:
        raw=str(candidate)
        found=shutil.which(raw) if not os.path.isabs(raw) else (raw if Path(raw).exists() else None)
        if found:return str(Path(found).resolve())
    return None


def _browser_version(executable:str)->str|None:
    try:return subprocess.run([executable,'--version'],capture_output=True,text=True,timeout=3,check=False).stdout.strip() or None
    except Exception:return None


def discover_browsers()->dict[str,BrowserInstall]:
    system=sys.platform
    chrome:list[str|Path]=[]; edge:list[str|Path]=[]
    if system.startswith('linux'):
        chrome=['google-chrome-stable','google-chrome','chromium','chromium-browser']
        edge=['microsoft-edge-stable','microsoft-edge']
    elif system=='darwin':
        chrome=[Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),Path('/Applications/Chromium.app/Contents/MacOS/Chromium')]
        edge=[Path('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')]
    elif system.startswith('win'):
        pf=Path(os.environ.get('PROGRAMFILES','C:/Program Files')); pfx=Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)')); local=Path(os.environ.get('LOCALAPPDATA',''))
        chrome=[pf/'Google/Chrome/Application/chrome.exe',pfx/'Google/Chrome/Application/chrome.exe',local/'Google/Chrome/Application/chrome.exe']
        edge=[pf/'Microsoft/Edge/Application/msedge.exe',pfx/'Microsoft/Edge/Application/msedge.exe']
    else:
        chrome=['google-chrome','chromium']; edge=['microsoft-edge']
    result={}
    c=_first_existing(chrome)
    if c:result['chrome']=BrowserInstall('chrome','Chrome/Chromium',c,_browser_version(c))
    e=_first_existing(edge)
    if e:result['msedge']=BrowserInstall('msedge','Microsoft Edge',e,_browser_version(e))
    return result


def _port_available(port:int)->bool:
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        try:sock.bind(('127.0.0.1',port));return True
        except OSError:return False


def run_preflight(*,port:int=8080,require_browser:bool=True,require_edge:bool=False,
                  require_certification_deps:bool=True,require_port:bool=True)->tuple[PreflightCheck,...]:
    checks=[];py=sys.version_info
    checks.append(PreflightCheck('python','pass' if (3,11)<=py[:2]<(3,14) else 'fail',f'Python {platform.python_version()}; supported >=3.11,<3.14'))
    checks.append(PreflightCheck('platform','pass',f'{platform.system()} {platform.machine()}'))
    checks.append(PreflightCheck('framework','pass',f'NiceGUI Base {FRAMEWORK_VERSION}'))
    nicegui=_package_version('nicegui');checks.append(PreflightCheck('nicegui','pass' if nicegui==NICEGUI_VERSION else 'fail',f'installed={nicegui or "missing"}; required={NICEGUI_VERSION}'))
    if nicegui == NICEGUI_VERSION:
        contract=run_installed_runtime_contract(); contract_detail=f'{contract.factories_checked} factories / {contract.calls_checked} calls; source={len(contract.source_issues)} runtime={len(contract.runtime_issues)} issues'
        checks.append(PreflightCheck('runtime-contract','pass' if contract.ok else 'fail',contract_detail))
    else:
        checks.append(PreflightCheck('runtime-contract','fail','NiceGUI runtime contract cannot run until exact NiceGUI 3.15.0 is installed'))

    playwright=_package_version('playwright')
    if playwright==PLAYWRIGHT_VERSION:
        checks.append(PreflightCheck('playwright','pass',f'installed={playwright}; required={PLAYWRIGHT_VERSION}',require_certification_deps))
    elif require_certification_deps:
        checks.append(PreflightCheck('playwright','fail',f'installed={playwright or "missing"}; required={PLAYWRIGHT_VERSION}',True))
    else:
        checks.append(PreflightCheck('playwright','skip',f'installed={playwright or "missing"}; certification-only={PLAYWRIGHT_VERSION}',False))

    pillow=_package_version('Pillow')
    if pillow==PILLOW_VERSION:
        checks.append(PreflightCheck('pillow','pass',f'installed={pillow}; required={PILLOW_VERSION}',require_certification_deps))
    elif require_certification_deps:
        checks.append(PreflightCheck('pillow','fail',f'installed={pillow or "missing"}; required={PILLOW_VERSION}',True))
    else:
        checks.append(PreflightCheck('pillow','skip',f'installed={pillow or "missing"}; certification-only={PILLOW_VERSION}',False))

    browsers=discover_browsers();chrome=browsers.get('chrome');edge=browsers.get('msedge')
    checks.append(PreflightCheck('browser','pass' if chrome else ('fail' if require_browser else 'warning'),f'{chrome.name}: {chrome.executable} · {chrome.version}' if chrome else 'Chrome/Chromium not discovered',require_browser))
    checks.append(PreflightCheck('edge','pass' if edge else ('fail' if require_edge else 'warning'),f'{edge.executable} · {edge.version}' if edge else 'Microsoft Edge not discovered',require_edge))
    available=_port_available(port)
    if available:
        checks.append(PreflightCheck('port','pass',f'127.0.0.1:{port} is available',require_port))
    elif require_port:
        checks.append(PreflightCheck('port','fail',f'127.0.0.1:{port} is already in use',True))
    else:
        checks.append(PreflightCheck('port','skip',f'127.0.0.1:{port} is already in use; setup smoke uses an ephemeral free port',False))
    issues=validate_visual_package();checks.append(PreflightCheck('visual-assets','pass' if not issues else 'fail',f'{len(issues)} visual asset validation issue(s)'))
    coverage=coverage_summary();checks.append(PreflightCheck('lab-coverage','pass' if not coverage['uncovered'] else 'fail',f"{coverage['covered_visual_components']}/{coverage['required_visual_components']} public visual integrations covered ({coverage.get('direct_visual_components')} direct + {coverage.get('composite_visual_components')} composite)"))
    comp=load_compatibility_manifest();checks.append(PreflightCheck('compatibility','pass' if comp.get('nicegui_version')==NICEGUI_VERSION else 'fail',f"manifest NiceGUI={comp.get('nicegui_version')}"))
    free=shutil.disk_usage(Path.home()).free;checks.append(PreflightCheck('disk','pass' if free>=1_000_000_000 else 'warning',f'{free/1_000_000_000:.1f} GB free',False))
    return tuple(checks)


def main()->int:
    p=argparse.ArgumentParser(description='NiceGUI Base platform-neutral live-certification preflight')
    p.add_argument('--port',type=int,default=8080)
    p.add_argument('--require-edge',action='store_true')
    p.add_argument('--no-require-browser',action='store_true')
    p.add_argument('--runtime-only',action='store_true',help='Check production runtime only; browser-certification packages are optional')
    p.add_argument('--ignore-port',action='store_true',help='Do not require the requested port to be free (setup smoke chooses its own free port)')
    p.add_argument('--format',choices=('text','json'),default='text')
    a=p.parse_args()
    checks=run_preflight(
        port=a.port,
        require_browser=not a.no_require_browser,
        require_edge=a.require_edge,
        require_certification_deps=not a.runtime_only,
        require_port=not a.ignore_port,
    )
    failed=[c for c in checks if c.required and c.status=='fail']
    profile='runtime' if a.runtime_only else 'certification'
    if a.format=='json':
        print(json.dumps({'ok':not failed,'profile':profile,'browsers':{k:asdict(v) for k,v in discover_browsers().items()},'checks':[asdict(c) for c in checks]},indent=2))
    else:
        for c in checks:print(f'[{c.status.upper():7}] {c.key:16} {c.detail}')
        label='Runtime preflight' if a.runtime_only else 'Live certification preflight'
        print(f'\n{label}: {"PASS" if not failed else "FAIL"}')
    return 0 if not failed else 1

if __name__=='__main__':raise SystemExit(main())

__all__=['PreflightCheck','BrowserInstall','PLAYWRIGHT_VERSION','PILLOW_VERSION','discover_browsers','run_preflight']
