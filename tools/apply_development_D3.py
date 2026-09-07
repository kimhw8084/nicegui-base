#!/usr/bin/env python3
"""Apply or roll back the guarded D2 -> D3 development update.

Only the two explicit identity/provenance files are transaction targets. Product
contract markers are checked before a mutation so a stale or unrelated checkout
is refused instead of being partially upgraded. Backups are content-addressed by
the exact D2 bytes and rollback requires the exact D3 bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any


FROM_BUILD = 'NGB-20260905-D2'
TO_BUILD = 'NGB-20260905-D3'
UPDATE_SCHEMA = 1
STATE_RELATIVE = '.nicegui_base/development_update_D3.json'
BACKUP_RELATIVE = '.nicegui_base/update-backups/NGB-20260905-D3'

TARGETS = (
    'source/nicegui_base/workbench/update_identity.py',
    'source/nicegui_base/workbench/runtime_bundle.py',
)

# These hashes are the exact D2 and D3 target bytes. The runtime bundle target
# differs only in the wheel Generator provenance string; the identity target is
# fully explicit below so an accidental broad replacement cannot pass the guard.
D2_SHA256 = {
    TARGETS[0]: 'c0887109ffab5482092d5295f3e8fea55772ae0ee96d468574c0ea767144279b',
    TARGETS[1]: '5c02a4599b763fde910e4ac0558901ea1c92509cccd1090d0484e4413921e3f2',
}
D3_SHA256 = {
    TARGETS[0]: '7ae000a5399b0ed8a47564abe17f21c745009d8a9b3187ea6fba6ab2161d4cff',
    TARGETS[1]: '7c99bdd2602d73e77cbf9c3bcf725813616797ad3a7d37afebec071f07f21a13',
}
D3_IDENTITY = b"\"\"\"Identity of the applied development candidate, not a stable release promotion.\"\"\"\nBUILD_ID = 'NGB-20260905-D3'\nBUILD_LABEL = 'Development update D3'\n"

CONTRACT_MARKERS = {
    'source/nicegui_base/workbench/preview_data.py': 'def resolve_measurement_field',
    'source/nicegui_base/workbench/provider_preview.py': 'class ProviderQueryController',
    'source/nicegui_base/workbench/project_codegen.py': 'measurement_field=MEASUREMENT_FIELD',
    'source/nicegui_base/workbench/builder.py': 'def review_summary',
    'source/nicegui_base/integrations/nicegui_runtime.py': 'install_framework_theme',
    'run_development_D3.zsh': 'NGB-20260905-D3',
}


class UpdateConflict(RuntimeError):
    """The guarded update cannot prove that its target is safe."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _root(value: str | Path | None) -> Path:
    root = Path(value) if value is not None else Path(__file__).resolve().parents[1]
    root = root.resolve()
    if not root.is_dir():
        raise UpdateConflict(f'update root is not a directory: {root}')
    return root


def _relative_path(root: Path, relative: str) -> Path:
    parsed = PurePosixPath(relative)
    if not relative or parsed.is_absolute() or '..' in parsed.parts or '\\' in relative:
        raise UpdateConflict(f'unsafe update path: {relative!r}')
    path = root.joinpath(*parsed.parts)
    if path.is_symlink():
        raise UpdateConflict(f'update target must not be a symlink: {relative}')
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise UpdateConflict(f'update parent must not be a symlink: {relative}')
    return path


def _read_target(root: Path, relative: str) -> bytes:
    path = _relative_path(root, relative)
    if not path.is_file():
        raise UpdateConflict(f'missing guarded update target: {relative}')
    return path.read_bytes()


def _check_contract(root: Path) -> None:
    missing: list[str] = []
    for relative, marker in CONTRACT_MARKERS.items():
        path = _relative_path(root, relative)
        if not path.is_file() or marker not in path.read_text(encoding='utf-8'):
            missing.append(f'{relative} (requires {marker!r})')
    if missing:
        raise UpdateConflict('D3 product contract is incomplete; refusing update: ' + '; '.join(missing))


def _state_path(root: Path) -> Path:
    return _relative_path(root, STATE_RELATIVE)


def _backup_dir(root: Path) -> Path:
    return _relative_path(root, BACKUP_RELATIVE)


def _atomic_write(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + '.d3-tmp')
    if temporary.exists() or temporary.is_symlink():
        raise UpdateConflict(f'temporary update path already exists: {temporary}')
    try:
        temporary.write_bytes(data)
        temporary.replace(path)
    except Exception:
        if temporary.exists() and not temporary.is_symlink():
            temporary.unlink()
        raise


def _ensure_backup(root: Path, before: dict[str, bytes]) -> Path:
    directory = _backup_dir(root)
    manifest = directory / 'backup_manifest.json'
    expected = {
        'schema_version': UPDATE_SCHEMA,
        'from_build': FROM_BUILD,
        'to_build': TO_BUILD,
        'sha256': {relative: _sha(data) for relative, data in before.items()},
    }
    if manifest.exists():
        try:
            existing = json.loads(manifest.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise UpdateConflict(f'cannot read existing D3 backup manifest: {manifest}') from exc
        if existing != expected:
            raise UpdateConflict('existing D3 backup does not match the exact D2 target bytes; refusing overwrite')
    else:
        directory.mkdir(parents=True, exist_ok=True)
        for relative, data in before.items():
            backup_path = directory / PurePosixPath(relative)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            if backup_path.exists() or backup_path.is_symlink():
                raise UpdateConflict(f'backup path already exists: {backup_path}')
            backup_path.write_bytes(data)
        _json(manifest, expected)
    for relative, data in before.items():
        backup_path = directory / PurePosixPath(relative)
        if not backup_path.is_file() or _sha(backup_path.read_bytes()) != _sha(data):
            raise UpdateConflict(f'D3 backup verification failed for {relative}')
    return directory


def _desired(root: Path, relative: str, current: bytes) -> bytes:
    if relative == TARGETS[0]:
        return D3_IDENTITY
    if relative == TARGETS[1]:
        if _sha(current) != D2_SHA256[relative]:
            raise UpdateConflict(f'{relative} is not the exact D2 runtime bundle target')
        updated = current.replace(b'nicegui-base-runtime-bundle-D2', b'nicegui-base-runtime-bundle-D3')
        if updated == current or _sha(updated) != D3_SHA256[relative]:
            raise UpdateConflict(f'could not construct the exact D3 runtime bundle target for {relative}')
        return updated
    raise UpdateConflict(f'unknown D3 target: {relative}')


def _current_hashes(root: Path) -> dict[str, str]:
    return {relative: _sha(_read_target(root, relative)) for relative in TARGETS}


def apply(root: Path) -> dict[str, Any]:
    _check_contract(root)
    before = {relative: _read_target(root, relative) for relative in TARGETS}
    hashes = {relative: _sha(data) for relative, data in before.items()}
    if hashes == D3_SHA256:
        return {'status': 'already_applied', 'build_id': TO_BUILD, 'targets': hashes}
    if hashes != D2_SHA256:
        raise UpdateConflict(f'guarded update conflict; expected all D2 targets, found {hashes}')
    desired = {relative: _desired(root, relative, data) for relative, data in before.items()}
    backup = _ensure_backup(root, before)
    try:
        for relative, data in desired.items():
            _atomic_write(_relative_path(root, relative), data)
        after = _current_hashes(root)
        if after != D3_SHA256:
            raise UpdateConflict(f'post-apply hash mismatch: {after}')
    except Exception:
        for relative, data in before.items():
            _atomic_write(_relative_path(root, relative), data)
        raise
    state = {
        'schema_version': UPDATE_SCHEMA,
        'status': 'applied',
        'from_build': FROM_BUILD,
        'to_build': TO_BUILD,
        'backup_directory': backup.relative_to(root).as_posix(),
        'before_sha256': D2_SHA256,
        'after_sha256': D3_SHA256,
    }
    _json(_state_path(root), state)
    return state


def rollback(root: Path) -> dict[str, Any]:
    hashes = _current_hashes(root)
    if hashes == D2_SHA256:
        return {'status': 'already_rolled_back', 'build_id': FROM_BUILD, 'targets': hashes}
    if hashes != D3_SHA256:
        raise UpdateConflict(f'rollback conflict; expected all D3 targets, found {hashes}')
    state_path = _state_path(root)
    if not state_path.is_file():
        raise UpdateConflict('exact rollback requires the D3 update state and backup manifest')
    try:
        state = json.loads(state_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise UpdateConflict('D3 update state is unreadable; refusing rollback') from exc
    if state.get('schema_version') != UPDATE_SCHEMA or state.get('after_sha256') != D3_SHA256:
        raise UpdateConflict('D3 update state does not match the exact applied target')
    backup = _relative_path(root, str(state.get('backup_directory') or ''))
    restored: dict[str, bytes] = {}
    for relative in TARGETS:
        path = backup / PurePosixPath(relative)
        if not path.is_file() or _sha(path.read_bytes()) != D2_SHA256[relative]:
            raise UpdateConflict(f'exact D2 backup is missing or changed for {relative}')
        restored[relative] = path.read_bytes()
    for relative, data in restored.items():
        _atomic_write(_relative_path(root, relative), data)
    after = _current_hashes(root)
    if after != D2_SHA256:
        raise UpdateConflict(f'post-rollback hash mismatch: {after}')
    state = dict(state)
    state['status'] = 'rolled_back'
    state['rolled_back_sha256'] = after
    _json(state_path, state)
    return state


def status(root: Path) -> dict[str, Any]:
    hashes = _current_hashes(root)
    if hashes == D3_SHA256:
        state = 'applied'
    elif hashes == D2_SHA256:
        state = 'rolled_back_or_not_applied'
    else:
        state = 'conflict'
    return {'status': state, 'build_id': TO_BUILD if hashes == D3_SHA256 else FROM_BUILD, 'targets': hashes}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('action', choices=('apply', 'rollback', 'status'), nargs='?', default='status')
    args = parser.parse_args(argv)
    try:
        root = _root(args.root)
        result = apply(root) if args.action == 'apply' else rollback(root) if args.action == 'rollback' else status(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (UpdateConflict, OSError, UnicodeError) as exc:
        print(f'D3_UPDATE=FAIL {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
