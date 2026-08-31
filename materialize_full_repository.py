#!/usr/bin/env python3
"""Materialize the exact GitHub baseline, apply cumulative Iteration 1 + Iteration 2, and emit the full ZIP."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from apply_iteration2 import BASELINE_COMMIT, apply, _verify_checksum_manifest

REPO = 'kimhw8084/nicegui-base'
DEFAULT_OUTPUT = 'nicegui-base_v3.0.0a8_WORKBENCH_ITERATION2.zip'
EXCLUDED_DIRS = {'.git', '.venv', '__pycache__', '.pytest_cache'}


def _safe_extract(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            rel = Path(info.filename)
            if rel.is_absolute() or '..' in rel.parts:
                raise SystemExit(f'ERROR: unsafe archive path: {info.filename}')
            out = destination / rel
            if info.is_dir():
                out.mkdir(parents=True, exist_ok=True); continue
            out.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, out.open('wb') as dst:
                shutil.copyfileobj(src, dst)
            mode=(info.external_attr >> 16) & 0o777
            if mode: out.chmod(mode)
    candidates=[p for p in destination.iterdir() if p.is_dir() and (p/'source'/'pyproject.toml').is_file()]
    if len(candidates) != 1:
        raise SystemExit('ERROR: source archive did not contain exactly one NiceGUI Base repository root.')
    return candidates[0]


def _copy_repository(source: Path, destination: Path) -> Path:
    source=source.resolve(); destination=destination.resolve()
    if not (source/'source'/'pyproject.toml').is_file():
        raise SystemExit(f'ERROR: --source-repo is not a NiceGUI Base repository root: {source}')
    if destination.exists(): shutil.rmtree(destination)
    def ignore(_dir, names):
        return {name for name in names if name in EXCLUDED_DIRS or name == '.DS_Store'}
    shutil.copytree(source, destination, ignore=ignore, copy_function=shutil.copy2)
    return destination


def _download_baseline(destination: Path) -> Path:
    archive=destination/'baseline.zip'
    url=f'https://github.com/{REPO}/archive/{BASELINE_COMMIT}.zip'
    request=urllib.request.Request(url, headers={'User-Agent':'nicegui-base-workbench-iteration2'})
    print(f'Downloading exact baseline {BASELINE_COMMIT}...')
    with urllib.request.urlopen(request, timeout=120) as response, archive.open('wb') as out:
        shutil.copyfileobj(response, out)
    return _safe_extract(archive, destination/'repository')


def _package_manifest_paths(root: Path) -> tuple[str, ...]:
    manifest=root/'PACKAGE_SHA256SUMS.txt'
    _verify_checksum_manifest(root, 'PACKAGE_SHA256SUMS.txt')
    paths=[]
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if '  ' not in line: continue
        digest, rel=line.split('  ',1); rel=rel.strip().replace('\\','/')
        if len(digest.strip()) == 64 and rel and (root/rel).is_file():
            paths.append(Path(rel).as_posix())
    return tuple(sorted(dict.fromkeys(paths)))


def _write_full_zip(root: Path, output: Path) -> None:
    root=root.resolve(); output=output.resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    allowlist=_package_manifest_paths(root)
    members=(*allowlist, 'PACKAGE_SHA256SUMS.txt')
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for rel in sorted(dict.fromkeys(members)):
            path=root/rel
            if not path.is_file():
                raise SystemExit(f'ERROR: final-package allowlisted file is missing: {rel}')
            info=zipfile.ZipInfo(rel,date_time=(2026,8,30,0,0,0)); info.create_system=3; info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(stat.S_IFREG | (path.stat().st_mode & 0o777)) << 16
            zf.writestr(info,path.read_bytes())
    with zipfile.ZipFile(output) as zf:
        bad=zf.testzip()
        if bad: raise SystemExit(f'ERROR: final ZIP CRC failure: {bad}')
        names=set(zf.namelist())
        expected=set(allowlist)|{'PACKAGE_SHA256SUMS.txt'}
        if names != expected:
            raise SystemExit(f'ERROR: final ZIP manifest mismatch; missing={sorted(expected-names)}, extra={sorted(names-expected)}')
        required={
            'source/nicegui_base/workbench/app.py','source/tests/test_workbench_iteration1.py','source/tests/test_workbench_iteration2.py',
            'WORKBENCH_ITERATION2_REPORT.md','apply_iteration2.py','materialize_full_repository.py',
            'wheel/nicegui_base-3.0.0a8-py3-none-any.whl','source/SHA256SUMS.txt','PACKAGE_SHA256SUMS.txt',
        }
        missing=required-names
        if missing: raise SystemExit(f'ERROR: final ZIP is incomplete: {sorted(missing)}')


def main() -> int:
    parser=argparse.ArgumentParser(description='Materialize the exact NiceGUI Base baseline, apply cumulative Workbench Iteration 1 + 2, and create a full repository ZIP')
    parser.add_argument('--output',type=Path,default=Path(DEFAULT_OUTPUT))
    source=parser.add_mutually_exclusive_group()
    source.add_argument('--source-zip',type=Path,help='Use an existing GitHub baseline ZIP instead of downloading it')
    source.add_argument('--source-repo',type=Path,help='Copy an existing exact-baseline repository checkout without modifying it')
    args=parser.parse_args(); overlay=HERE
    with tempfile.TemporaryDirectory(prefix='nicegui-base-iteration2-') as tmp_name:
        tmp=Path(tmp_name)
        if args.source_repo is not None:
            root=_copy_repository(args.source_repo,tmp/'repository')
        elif args.source_zip is not None:
            if not args.source_zip.is_file(): raise SystemExit(f'ERROR: --source-zip not found: {args.source_zip}')
            root=_safe_extract(args.source_zip.resolve(),tmp/'repository-archive')
        else:
            root=_download_baseline(tmp)
        print('Applying cumulative Workbench Iteration 1 + 2 and rebuilding package authorities...')
        apply(overlay,root)
        print(f'Writing full repository ZIP: {args.output}')
        _write_full_zip(root,args.output.resolve())
    print(f'Created: {args.output.resolve()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
