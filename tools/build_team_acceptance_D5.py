#!/usr/bin/env python3
"""Build the compact, source-independent D5 teammate package around the D4 RC."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import zipfile


D5_ID = 'NGB-20260905-D5'
D4_ID = 'NGB-20260905-D4'
FRAMEWORK_VERSION = '3.0.0a8'
NICEGUI_VERSION = '3.15.0'
DEFAULT_D4 = Path('/private/tmp/ngb_d4_rc')
DEFAULT_OUTPUT = Path('/private/tmp/ngb_d5_team')
OWNER_MARKER = '.ngb-d5-owned'
MUTABLE = ('.venv', '.nicegui', '.ngb-d5-evidence')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def release_files(root: Path, *, exclude_manifest: bool = False) -> list[Path]:
    excluded = {item.rstrip('/') for item in MUTABLE}
    files = []
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if (exclude_manifest and rel == 'SHA256SUMS.txt') or any(rel == item or rel.startswith(item + '/') for item in excluded):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def write_manifest(root: Path) -> Path:
    target = root / 'SHA256SUMS.txt'
    lines = [f'{sha256(path)}  {path.relative_to(root).as_posix()}' for path in release_files(root, exclude_manifest=True)]
    target.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return target


def deterministic_zip(root: Path, target: Path) -> Path:
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in release_files(root):
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            mode = stat.S_IMODE(path.stat().st_mode)
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return target


def d4_authority(d4_root: Path, d4_archive: Path) -> dict:
    result_path = d4_root / 'D4_FINAL_RESULT.json'
    result = json.loads(result_path.read_text(encoding='utf-8'))
    static = result.get('static', {})
    wheel_paths = sorted((d4_root / 'bundle' / 'wheel').glob('nicegui_base-*.whl'))
    if result.get('candidate_id') != D4_ID or result.get('status') != 'PASS' or len(wheel_paths) != 1:
        raise RuntimeError(f'authoritative D4 result is not a single PASS: {result_path}')
    archive_hash = sha256(d4_archive)
    wheel_hash = sha256(wheel_paths[0])
    if archive_hash != result.get('archive_sha256') or wheel_hash != static.get('wheel_sha256'):
        raise RuntimeError('D4 authority hash does not match its current archive or wheel')
    if static.get('packaged_source_files') != 551 or static.get('source_state_sha256') != result.get('static', {}).get('source_state_sha256'):
        raise RuntimeError('D4 authority lacks the expected 551-file source authority')
    provenance = json.loads((d4_root / 'bundle' / 'BUILD_PROVENANCE.json').read_text(encoding='utf-8'))
    if provenance.get('candidate_id') != D4_ID or provenance.get('framework_version') != FRAMEWORK_VERSION or provenance.get('nicegui_version') != NICEGUI_VERSION:
        raise RuntimeError('D4 build provenance identity is inconsistent')
    return {
        'rc_candidate_id': D4_ID,
        'd4_bundle_sha256': archive_hash,
        'wheel_filename': wheel_paths[0].name,
        'wheel_sha256': wheel_hash,
        'wheel_size_bytes': wheel_paths[0].stat().st_size,
        'framework_version': FRAMEWORK_VERSION,
        'nicegui_version': NICEGUI_VERSION,
        'source_state_sha256': static['source_state_sha256'],
        'packaged_source_files': static['packaged_source_files'],
        'd4_authority_files': ['D4_FINAL_RESULT.json', 'bundle/BUILD_PROVENANCE.json', 'bundle/SHA256SUMS.txt'],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--d4-root', type=Path, default=DEFAULT_D4)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    d4_root = args.d4_root.resolve()
    d4_archive = d4_root / f'{D4_ID}_RC.zip'
    d4_bundle = d4_root / 'bundle'
    if not d4_archive.is_file() or not d4_bundle.is_dir():
        raise SystemExit(f'D4 authority is missing: {d4_root}')
    if args.output.exists():
        if not (args.output / OWNER_MARKER).is_file():
            raise SystemExit(f'refusing to replace unowned D5 output: {args.output}')
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True)
    (args.output / OWNER_MARKER).write_text(D5_ID + '\n', encoding='utf-8')
    package = args.output / 'package'
    package.mkdir()
    authority = d4_authority(d4_root, d4_archive)
    wheel_source = d4_bundle / 'wheel' / authority['wheel_filename']
    (package / 'wheel').mkdir()
    shutil.copy2(wheel_source, package / 'wheel' / wheel_source.name)
    shutil.copy2(d4_bundle / 'requirements.txt', package / 'requirements.txt')

    identity = {
        'd5_package_id': D5_ID,
        **authority,
        'provenance_files': ['RC_IDENTITY.json', 'SHA256SUMS.txt'],
        'installation_contract': 'Python 3.11–3.13; exact production requirements; site-packages import required',
    }
    (package / 'RC_IDENTITY.json').write_text(json.dumps(identity, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    template_root = Path(__file__).with_name('d5_package')
    for template in sorted(template_root.iterdir()):
        if not template.is_file():
            continue
        target = package / template.name
        if template.suffix in {'.py', '.sh', '.md'}:
            text = template.read_text(encoding='utf-8')
            text = text.replace('@D5_PACKAGE_ID@', D5_ID).replace('@RC_CANDIDATE_ID@', D4_ID)
            target.write_text(text, encoding='utf-8')
        else:
            shutil.copy2(template, target)
        if target.suffix == '.sh' or target.name == 'launch_d5.py' or target.name == 'verify_d5.py':
            target.chmod(0o755)
    write_manifest(package)
    archive = deterministic_zip(package, args.output / f'{D5_ID}_TEAM.zip')
    summary = {
        'd5_package_id': D5_ID,
        'rc_candidate_id': D4_ID,
        'package': str(package),
        'archive': str(archive),
        'archive_sha256': sha256(archive),
        'wheel_filename': authority['wheel_filename'],
        'wheel_sha256': authority['wheel_sha256'],
        'package_files': len(release_files(package)),
    }
    (args.output / 'D5_BUILD_RESULT.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
