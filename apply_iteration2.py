#!/usr/bin/env python3
"""Apply NiceGUI Base Workbench Iteration 2 to an exact repository checkout/package.

This helper exists because the ChatGPT execution sandbox can read GitHub through the
connector but cannot clone/download the repository archive into its filesystem. It
copies the cumulative reviewed Iteration 1 + Iteration 2 files, rebuilds the bundled wheel without a
network dependency, regenerates source/package checksum manifests, and validates the
resulting wheel structure.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import stat
import sys
import tomllib
import zipfile

BASELINE_COMMIT = '62a06ce9fb976cfd93b746af807512ceda92c07e'
VERSION = '3.0.0a8'
DIST = 'nicegui-base'
WHEEL_NAME = f'nicegui_base-{VERSION}-py3-none-any.whl'


BASELINE_BLOB_SHA1 = {
    'setup_mac.sh': '4304e98288bf9f6efd9b20e119a28d2b3f461bfe',
    'setup_linux.sh': 'e504ae8a476357ee9872d5143265ce41eb849308',
    'run_lab_mac.sh': '55c829e74e69a9bc8e63bfe3be0f0264984293a1',
    'run_lab_linux.sh': '956aac440fe6a47803a1bd89b4a8bcc19de5524e',
    'source/nicegui_base/certification/mac_lab_cli.py': '2fb4f619b357d7a44ca932a2e31b0bc1634f6838',
    'source/nicegui_base/certification/live_lab_cli.py': '4f0e1bf53ddae8d614ce964afc8a0da72a67519e',
    'source/SHA256SUMS.txt': 'aeec80df96d202b58380bb8e9841ba1bc5a654b0',
    'PACKAGE_SHA256SUMS.txt': '9b0c19039141183efd360526e681bede938cac14',
}

OVERLAY_FILES = (
    'setup_mac.sh',
    'setup_linux.sh',
    'run_lab_mac.sh',
    'run_lab_linux.sh',
    'WORKBENCH_ITERATION1_REPORT.md',
    'WORKBENCH_ITERATION1_EVIDENCE.json',
    'WORKBENCH_ITERATION1_MANIFEST.json',
    'WORKBENCH_ITERATION2_REPORT.md',
    'WORKBENCH_ITERATION2_EVIDENCE.json',
    'WORKBENCH_ITERATION2_MANIFEST.json',
    'apply_iteration1.py',
    'apply_iteration2.py',
    'materialize_full_repository.py',
    'source/nicegui_base/certification/mac_lab_cli.py',
    'source/nicegui_base/certification/live_lab_cli.py',
    'source/tests/test_workbench_iteration1.py',
    'source/tests/test_workbench_iteration2.py',
)

EXCLUDED_DIRS = {'.git', '.venv', '__pycache__', '.pytest_cache'}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f'blob {len(data)}\0'.encode('ascii')
    return hashlib.sha1(header + data).hexdigest()


def _verify_checksum_manifest(root: Path, manifest_name: str) -> int:
    manifest = root / manifest_name
    if not manifest.is_file():
        raise SystemExit(f'ERROR: baseline checksum manifest is missing: {manifest}')
    failures: list[str] = []
    checked = 0
    for line_no, line in enumerate(manifest.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        if not line.strip():
            continue
        if '  ' not in line:
            failures.append(f'{manifest_name}:{line_no}: malformed row')
            continue
        expected, rel = line.split('  ', 1)
        expected = expected.strip().lower(); rel = rel.strip().replace('\\', '/')
        if len(expected) != 64 or not rel:
            failures.append(f'{manifest_name}:{line_no}: malformed digest/path')
            continue
        path = root / rel
        if not path.is_file():
            failures.append(f'{rel}: missing')
            continue
        observed = _sha256(path)
        checked += 1
        if observed != expected:
            failures.append(f'{rel}: expected {expected}, observed {observed}')
    if failures:
        preview = '\n  - '.join(failures[:20])
        extra = f'\n  ... and {len(failures)-20} more' if len(failures) > 20 else ''
        raise SystemExit(f'ERROR: baseline checksum verification failed for {manifest}:\n  - {preview}{extra}')
    if checked == 0:
        raise SystemExit(f'ERROR: baseline checksum verification failed for {manifest}: no valid rows')
    return checked


def _verify_overlay_manifest(overlay: Path) -> int:
    manifest = overlay / 'WORKBENCH_ITERATION2_MANIFEST.json'
    if not manifest.is_file():
        raise SystemExit('ERROR: Iteration 2 overlay manifest is missing.')
    try:
        payload = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f'ERROR: invalid Iteration 2 overlay manifest: {exc}') from exc
    if payload.get('baseline_commit') != BASELINE_COMMIT:
        raise SystemExit('ERROR: Iteration 2 overlay manifest targets a different baseline commit.')
    failures=[]; checked=0
    files = payload.get('files', ())
    if not isinstance(files, list):
        raise SystemExit('ERROR: Iteration 2 overlay manifest files must be a list.')
    for item in files:
        if not isinstance(item, dict) or not item.get('path') or not item.get('sha256'):
            failures.append('malformed overlay manifest row'); continue
        rel = str(item['path']).replace('\\','/')
        path = overlay / rel
        if not path.is_file():
            failures.append(f'{rel}: missing'); continue
        observed=_sha256(path); checked += 1
        if observed != str(item['sha256']).lower():
            failures.append(f'{rel}: hash mismatch')
        expected_bytes=item.get('bytes')
        if isinstance(expected_bytes, int) and path.stat().st_size != expected_bytes:
            failures.append(f'{rel}: byte-size mismatch')
    if failures:
        raise SystemExit('ERROR: Iteration 2 overlay manifest verification failed:\n  - ' + '\n  - '.join(failures[:20]))
    return checked


def _verify_baseline(target: Path) -> None:
    # A Git checkout is the strongest available baseline authority. The Wave 77
    # package checksum manifests shipped in the baseline contain stale/inapplicable
    # rows for a repository checkout, so they are intentionally NOT used as a
    # pre-apply gate. Fresh manifests are regenerated after the overlay is applied.
    git_dir = target / '.git'
    if git_dir.exists():
        try:
            commit = subprocess.check_output(
                ['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True, stderr=subprocess.STDOUT
            ).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SystemExit(f'ERROR: unable to verify target Git commit: {exc}') from exc
        if commit != BASELINE_COMMIT:
            raise SystemExit(
                f'ERROR: target Git checkout is not the reviewed baseline; expected {BASELINE_COMMIT}, found {commit}'
            )
        try:
            dirty = subprocess.check_output(
                ['git', '-C', str(target), 'status', '--porcelain'], text=True, stderr=subprocess.STDOUT
            ).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SystemExit(f'ERROR: unable to verify target Git worktree: {exc}') from exc
        if dirty:
            raise SystemExit('ERROR: target Git worktree has uncommitted changes; refusing to mix the update with local edits.')

    mismatches=[]
    for rel, expected in BASELINE_BLOB_SHA1.items():
        path=target / rel
        if not path.is_file():
            mismatches.append(f'{rel}: missing')
            continue
        observed=_git_blob_sha1(path)
        if observed != expected:
            mismatches.append(f'{rel}: expected blob {expected}, observed {observed}')
    if mismatches:
        raise SystemExit('ERROR: target does not match the exact reviewed baseline commit; refusing to overwrite:\n  - ' + '\n  - '.join(mismatches))


def _identity_ok(target: Path) -> None:
    pyproject = target / 'source' / 'pyproject.toml'
    package = target / 'source' / 'nicegui_base'
    if not pyproject.is_file() or not package.is_dir():
        raise SystemExit(f'ERROR: {target} is not a NiceGUI Base full repository/package root.')
    data = tomllib.loads(pyproject.read_text(encoding='utf-8'))
    project = data.get('project', {})
    if project.get('name') != DIST or project.get('version') != VERSION:
        raise SystemExit(
            f"ERROR: expected {DIST} {VERSION}; found {project.get('name')} {project.get('version')}"
        )
    deps = tuple(project.get('dependencies', ()))
    if 'nicegui==3.15.0' not in deps:
        raise SystemExit('ERROR: exact nicegui==3.15.0 dependency contract is not present.')


def _copy_overlay(overlay: Path, target: Path) -> list[Path]:
    copied: list[Path] = []
    for rel in OVERLAY_FILES:
        src = overlay / rel
        if not src.is_file():
            raise SystemExit(f'ERROR: overlay file is missing: {rel}')
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst)
    wb = overlay / 'source' / 'nicegui_base' / 'workbench'
    if not wb.is_dir():
        raise SystemExit('ERROR: Workbench source directory is missing from overlay.')
    for src in sorted(wb.rglob('*')):
        if not src.is_file() or src.suffix == '.pyc' or '__pycache__' in src.parts:
            continue
        rel = src.relative_to(overlay)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst)
    for rel in ('setup_mac.sh', 'setup_linux.sh', 'run_lab_mac.sh', 'run_lab_linux.sh'):
        path = target / rel
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return copied


def _zip_info(name: str, mode: int = 0o644) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(2026, 8, 30, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | mode) << 16
    return info


def _metadata_from_pyproject(pyproject: dict) -> str:
    project = pyproject['project']
    lines = [
        'Metadata-Version: 2.4',
        f"Name: {project['name']}",
        f"Version: {project['version']}",
        f"Summary: {project.get('description', '')}",
        f"Requires-Python: {project.get('requires-python', '')}",
    ]
    for dep in project.get('dependencies', ()):
        lines.append(f'Requires-Dist: {dep}')
    for extra, deps in project.get('optional-dependencies', {}).items():
        lines.append(f'Provides-Extra: {extra}')
        for dep in deps:
            lines.append(f'Requires-Dist: {dep}; extra == "{extra}"')
    lines += ['', 'NiceGUI Base', '']
    return '\n'.join(lines)


def _entry_points(pyproject: dict) -> str:
    scripts = pyproject.get('project', {}).get('scripts', {})
    lines = ['[console_scripts]']
    for name, target in sorted(scripts.items()):
        lines.append(f'{name}={target}')
    lines.append('')
    return '\n'.join(lines)


def _record_hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return 'sha256=' + base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')


def _build_wheel(source: Path, output: Path) -> None:
    pyproject = tomllib.loads((source / 'pyproject.toml').read_text(encoding='utf-8'))
    dist_info = f'nicegui_base-{VERSION}.dist-info'
    members: dict[str, tuple[bytes, int]] = {}
    for package_name in ('nicegui_base', 'company_ui'):
        package = source / package_name
        if not package.is_dir():
            raise SystemExit(f'ERROR: wheel source package missing: {package}')
        for path in sorted(package.rglob('*')):
            if not path.is_file() or path.suffix == '.pyc' or '__pycache__' in path.parts:
                continue
            arc = path.relative_to(source).as_posix()
            members[arc] = (path.read_bytes(), 0o644)
    members[f'{dist_info}/METADATA'] = (_metadata_from_pyproject(pyproject).encode(), 0o644)
    members[f'{dist_info}/WHEEL'] = (
        b'Wheel-Version: 1.0\nGenerator: nicegui-base-workbench-iteration2\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
        0o644,
    )
    members[f'{dist_info}/entry_points.txt'] = (_entry_points(pyproject).encode(), 0o644)
    members[f'{dist_info}/top_level.txt'] = (b'company_ui\nnicegui_base\n', 0o644)

    record_buffer = io.StringIO(newline='')
    writer = csv.writer(record_buffer, lineterminator='\n')
    for name in sorted(members):
        data, _ = members[name]
        writer.writerow((name, _record_hash(data), str(len(data))))
    record_name = f'{dist_info}/RECORD'
    writer.writerow((record_name, '', ''))
    members[record_name] = (record_buffer.getvalue().encode(), 0o644)

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in sorted(members):
            data, mode = members[name]
            zf.writestr(_zip_info(name, mode), data)
    with zipfile.ZipFile(output) as zf:
        bad = zf.testzip()
        if bad:
            raise SystemExit(f'ERROR: wheel CRC failure: {bad}')
        names = set(zf.namelist())
        for required in (
            'nicegui_base/workbench/app.py',
            'nicegui_base/certification/mac_lab_cli.py',
            'company_ui/__init__.py',
            f'{dist_info}/RECORD',
        ):
            if required not in names:
                raise SystemExit(f'ERROR: rebuilt wheel is missing {required}')
        metadata = zf.read(f'{dist_info}/METADATA').decode('utf-8')
        if 'Requires-Dist: nicegui==3.15.0' not in metadata:
            raise SystemExit('ERROR: rebuilt wheel lost the exact NiceGUI dependency pin.')


def _replace_wheel_copies(target: Path) -> list[Path]:
    temp = target / '.iteration2-wheel.tmp'
    try:
        _build_wheel(target / 'source', temp)
        destinations = (
            target / 'wheel' / WHEEL_NAME,
            target / 'source' / 'wheel' / WHEEL_NAME,
            target / 'source' / 'dist' / WHEEL_NAME,
        )
        for directory in {path.parent for path in destinations}:
            directory.mkdir(parents=True, exist_ok=True)
            for old in directory.glob(f'nicegui_base-{VERSION}-*.whl'):
                old.unlink()
        for destination in destinations:
            shutil.copy2(temp, destination)
        hashes = {_sha256(path) for path in destinations}
        if len(hashes) != 1:
            raise SystemExit('ERROR: rebuilt wheel mirror hashes differ.')
        return list(destinations)
    finally:
        temp.unlink(missing_ok=True)


def _iter_manifest_files(root: Path, manifest: Path):
    manifest = manifest.resolve()
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.resolve() == manifest:
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        if path.suffix == '.pyc' or path.name == '.DS_Store':
            continue
        yield path


def _existing_manifest_paths(root: Path, manifest: Path) -> set[str] | None:
    if not manifest.is_file():
        return None
    result: set[str] = set()
    valid = 0
    for line in manifest.read_text(encoding='utf-8', errors='replace').splitlines():
        if '  ' not in line:
            continue
        digest, rel = line.split('  ', 1)
        rel = rel.strip().replace('\\', '/')
        if len(digest.strip()) != 64 or not rel:
            continue
        path = root / rel
        if path.is_file() and path.resolve() != manifest.resolve():
            result.add(Path(rel).as_posix())
            valid += 1
    return result if valid else None


def _write_manifest(root: Path, manifest: Path, *, extra_paths=()) -> int:
    rels = _existing_manifest_paths(root, manifest)
    if rels is None:
        rels = {path.relative_to(root).as_posix() for path in _iter_manifest_files(root, manifest)}
    for path in extra_paths:
        path = Path(path)
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        if path.is_file() and path.resolve() != manifest.resolve():
            rels.add(rel)
    rows = []
    for rel in sorted(rels):
        path = root / rel
        if path.is_file() and path.resolve() != manifest.resolve():
            rows.append(f'{_sha256(path)}  {rel}')
    manifest.write_text('\n'.join(rows) + '\n', encoding='utf-8')
    return len(rows)


def apply(overlay: Path, target: Path) -> dict:
    overlay = overlay.resolve()
    target = target.resolve()
    _identity_ok(target)
    _verify_overlay_manifest(overlay)
    _verify_baseline(target)
    copied = _copy_overlay(overlay, target)
    wheels = _replace_wheel_copies(target)
    source_root = target / 'source'
    source_extras = [path for path in (*copied, *wheels) if path.is_relative_to(source_root)]
    source_entries = _write_manifest(source_root, source_root / 'SHA256SUMS.txt', extra_paths=source_extras)
    result_path = target / 'WORKBENCH_ITERATION2_APPLY_RESULT.json'
    package_extras = [*copied, *wheels, source_root / 'SHA256SUMS.txt', result_path]
    package_entries = _write_manifest(target, target / 'PACKAGE_SHA256SUMS.txt', extra_paths=package_extras)
    result = {
        'status': 'PASS',
        'baseline_commit': BASELINE_COMMIT,
        'framework_version': VERSION,
        'copied_files': len(copied),
        'source_manifest_entries': source_entries,
        'package_manifest_entries': package_entries,
        'wheel': WHEEL_NAME,
        'wheel_sha256': _sha256(wheels[0]),
        'wheel_mirrors': len(wheels),
    }
    result_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    # Result file is a new package artifact; include its final bytes in the package manifest.
    result['package_manifest_entries'] = _write_manifest(
        target, target / 'PACKAGE_SHA256SUMS.txt', extra_paths=package_extras
    )
    result_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    _write_manifest(target, target / 'PACKAGE_SHA256SUMS.txt', extra_paths=package_extras)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Apply cumulative NiceGUI Base Workbench Iteration 1 + Iteration 2 to a full repository/package')
    parser.add_argument('target', type=Path, help='Full NiceGUI Base repository/package root')
    args = parser.parse_args()
    result = apply(Path(__file__).resolve().parent, args.target)
    print(json.dumps(result, indent=2))
    print('\nNext: run ./setup_mac.sh (macOS) or ./setup_linux.sh (Linux), then ./run_lab.sh')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
