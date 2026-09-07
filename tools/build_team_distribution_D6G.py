#!/usr/bin/env python3
"""Build the clean, source-independent D6G teammate distribution."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import zipfile


D6G_ID = 'NGB-20260906-D6G'
RC_ROOT = Path('/private/tmp/ngb_d6g_rc')
DEFAULT_OUTPUT = Path('/private/tmp/ngb_d6g_team')
OWNER_MARKER = '.ngb-d6g-team-owned'
TEMPLATE_ROOT = Path(__file__).with_name('d6g_package')
MUTABLE = ('.venv', '.ngb-d6g-evidence', '.ngb-d6g-work')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def release_files(root: Path, *, exclude_manifest: bool = False) -> list[Path]:
    files = []
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if (exclude_manifest and relative == 'SHA256SUMS.txt') or any(relative == item or relative.startswith(item + '/') for item in MUTABLE):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def write_manifest(root: Path) -> None:
    lines = [f'{sha256(path)}  {path.relative_to(root).as_posix()}' for path in release_files(root, exclude_manifest=True)]
    (root / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def deterministic_zip(root: Path, target: Path) -> None:
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in release_files(root):
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | stat.S_IMODE(path.stat().st_mode)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--rc-root', type=Path, default=RC_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    rc_root = args.rc_root.resolve()
    rc_bundle = rc_root / 'bundle'
    build_result = json.loads((rc_root / 'D4_BUILD_RESULT.json').read_text(encoding='utf-8'))
    if build_result.get('candidate_id') != D6G_ID or build_result.get('qualification', {}).get('status') != 'PASS':
        raise SystemExit('D6G RC authority is not a single qualified PASS')
    wheel_paths = sorted((rc_bundle / 'wheel').glob('nicegui_base-*.whl'))
    if len(wheel_paths) != 1:
        raise SystemExit(f'expected one D6G wheel, found {wheel_paths}')
    wheel = wheel_paths[0]
    if args.output.exists():
        if not (args.output / OWNER_MARKER).is_file():
            raise SystemExit(f'refusing to replace unowned output: {args.output}')
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True)
    (args.output / OWNER_MARKER).write_text(D6G_ID + '\n', encoding='utf-8')
    package = args.output / 'package'
    (package / 'wheel').mkdir(parents=True)
    shutil.copy2(wheel, package / 'wheel' / wheel.name)
    shutil.copy2(rc_bundle / 'requirements.txt', package / 'requirements.txt')
    source = json.loads((rc_bundle / 'SOURCE_PACKAGE_SHA256.json').read_text(encoding='utf-8'))
    rc_provenance = json.loads((rc_bundle / 'BUILD_PROVENANCE.json').read_text(encoding='utf-8'))
    # The RC builder's local pip diagnostic can contain the development
    # checkout path. Keep the reproducibility facts while making the team
    # distribution independent of that machine and directory.
    builder_provenance = rc_provenance.get('builder', {})
    rc_provenance['builder'] = {
        'python': builder_provenance.get('python', ''),
        'pip_version': str(builder_provenance.get('pip', '')).split(' from ', 1)[0],
    }
    identity = {
        'team_package_id': D6G_ID,
        'candidate_id': D6G_ID,
        'framework': 'nicegui-base',
        'framework_version': '3.0.0a8',
        'nicegui_version': '3.15.0',
        'wheel_filename': wheel.name,
        'wheel_sha256': sha256(wheel),
        'wheel_size_bytes': wheel.stat().st_size,
        'source_package_files': len(source['files']),
        'source_package_sha256': source['source_state_sha256'],
        'rc_bundle_sha256': sha256(rc_root / f'{D6G_ID}_RC.zip'),
        'rollback_baseline': 'NGB-20260905-D5',
    }
    (package / 'RC_IDENTITY.json').write_text(json.dumps(identity, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    provenance = {
        'candidate_id': D6G_ID,
        'distribution': 'team',
        'rc_authority': rc_provenance,
        'wheel_sha256': identity['wheel_sha256'],
        'source_package_sha256': identity['source_package_sha256'],
        'source_package_files': identity['source_package_files'],
        'requirements_sha256': sha256(package / 'requirements.txt'),
    }
    (package / 'BUILD_PROVENANCE.json').write_text(json.dumps(provenance, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    for template in sorted(TEMPLATE_ROOT.iterdir()):
        if not template.is_file():
            continue
        target = package / template.name
        target.write_text(template.read_text(encoding='utf-8').replace('@D6G_ID@', D6G_ID), encoding='utf-8')
        if target.suffix in {'.sh', '.py'}:
            target.chmod(0o755)
    write_manifest(package)
    archive = args.output / f'{D6G_ID}_TEAM.zip'
    deterministic_zip(package, archive)
    summary = {
        'candidate_id': D6G_ID,
        'package': str(package),
        'archive': str(archive),
        'archive_sha256': sha256(archive),
        'wheel_filename': wheel.name,
        'wheel_sha256': identity['wheel_sha256'],
        'package_files': len(release_files(package)),
    }
    (args.output / 'D6G_BUILD_RESULT.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
