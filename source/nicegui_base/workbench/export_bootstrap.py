#!/usr/bin/env python3
"""Install and run a generated NiceGUI Base app independently of its source repo.

Copied verbatim to generated apps as bootstrap.py. Uses only the standard library
until the app is started. Dependencies use the caller's configured pip index.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import socket
import subprocess
import sys
import tempfile


def clean_environment():
    env = os.environ.copy()
    for name in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'VIRTUAL_ENV'):
        env.pop(name, None)
    env['PYTHONNOUSERSITE'] = '1'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def safe_file(root: Path, relative: str) -> Path:
    rel = PurePosixPath(relative)
    if not relative or rel.is_absolute() or '..' in rel.parts or '\\' in relative:
        raise ValueError(f'Unsafe bundle path: {relative!r}')
    path = root.joinpath(*rel.parts)
    for part in (path, *path.parents):
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError(f'Symlink is not allowed in bundle files: {relative!r}')
    if not path.is_file():
        raise ValueError(f'Missing bundle file: {relative}')
    return path


def bundle_lock(root: Path) -> dict:
    lock = json.loads(safe_file(root, '.nicegui_base/runtime_bundle.json').read_text())
    if lock.get('schema_version') != 1 or lock.get('framework_version') != '3.0.0a8' or lock.get('nicegui_version') != '3.15.0':
        raise ValueError('Unsupported runtime bundle contract.')
    wheel = safe_file(root, lock['wheel'])
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != lock['wheel_sha256']:
        raise ValueError('Bundled framework wheel checksum mismatch. Nothing was installed.')
    if not isinstance(lock.get('source_sha256'), dict) or not lock['source_sha256']:
        raise ValueError('Runtime bundle has no source inventory.')
    return lock


# Run outside the generated app directory with -I, so neither the repository nor
# the generated app can shadow installed nicegui_base/nicegui packages.
PROVENANCE_CODE = r'''
import hashlib, importlib.metadata as md, json, pathlib, sys
lock = json.loads(pathlib.Path(sys.argv[1]).read_text())
import nicegui_base
from nicegui_base.workbench.update_identity import BUILD_ID
package = pathlib.Path(nicegui_base.__file__).resolve().parent
prefix = pathlib.Path(sys.prefix).resolve()
failures = []
if prefix not in package.parents:
    failures.append('framework_import_outside_isolated_environment')
if BUILD_ID != lock['build_id']:
    failures.append('build_identity_mismatch')
if md.version('nicegui') != lock['nicegui_version']:
    failures.append('nicegui_version_mismatch')
if md.version('nicegui-base') != lock['framework_version']:
    failures.append('framework_version_mismatch')
for rel, expected in lock['source_sha256'].items():
    path = package.parent.joinpath(*pathlib.PurePosixPath(rel).parts)
    try:
        path.resolve().relative_to(package.parent)
    except ValueError:
        failures.append('unsafe_installed_path:' + rel)
        continue
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        failures.append('installed_source_mismatch:' + rel)
print(json.dumps({'passed': not failures, 'failures': failures, 'build_id': BUILD_ID,
                  'framework_file': str(package / '__init__.py'), 'python': sys.executable,
                  'prefix': str(prefix), 'verified_files': len(lock['source_sha256']),
                  'wheel_sha256': lock['wheel_sha256']}, sort_keys=True))
raise SystemExit(0 if not failures else 1)
'''


def verify_install(root: Path, python: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix='ngb-independent-import-') as temp:
        proc = subprocess.run([str(python), '-I', '-c', PROVENANCE_CODE,
                               str(root / '.nicegui_base/runtime_bundle.json')],
                              cwd=temp, env=clean_environment(), text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    if proc.returncode:
        raise RuntimeError('Installed runtime verification failed. Run bootstrap.py --setup.\n' + proc.stdout + proc.stderr)
    return json.loads(proc.stdout)


def environment_python(root: Path) -> Path:
    env = root / '.venv'
    if env.is_symlink():
        raise ValueError('Refusing a symlinked generated-app .venv.')
    return env / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def setup(root: Path, lock: dict) -> Path:
    venv = root / '.venv'
    py = environment_python(root)
    owner_path = venv / 'NGB_BOOTSTRAP_OWNER.json'
    if venv.exists():
        if not owner_path.is_file() or owner_path.is_symlink():
            raise ValueError('An unmanaged .venv already exists. Move it aside yourself; it was not overwritten.')
        owner = json.loads(owner_path.read_text())
        if owner.get('root') != str(root):
            raise ValueError('This .venv belongs to a different location. Create a new environment after moving the app.')
    else:
        # Reserve ownership before venv creation, so a failed setup can be retried.
        venv.mkdir(mode=0o700)
        owner_path.write_text(json.dumps({'root': str(root)}))
    subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True, env=clean_environment(), timeout=120)
    config = (venv / 'pyvenv.cfg').read_text().lower()
    if 'include-system-site-packages = true' in config:
        raise ValueError('Generated app environment must not inherit system site-packages.')
    print('Installing exact runtime using the configured pip index (no index override).', flush=True)
    subprocess.run([str(py), '-m', 'pip', 'install', 'nicegui==' + lock['nicegui_version']],
                   check=True, cwd=root, env=clean_environment(), timeout=900)
    subprocess.run([str(py), '-m', 'pip', 'install', '--no-deps', '--force-reinstall',
                    str(safe_file(root, lock['wheel']))], check=True, cwd=root,
                   env=clean_environment(), timeout=180)
    subprocess.run([str(py), '-m', 'pip', 'check'], check=True, cwd=root,
                   env=clean_environment(), timeout=120)
    return py


def secret(root: Path) -> str:
    explicit = os.getenv('NICEGUI_BASE_STORAGE_SECRET')
    if explicit:
        return explicit
    path = root / '.nicegui_base/local-storage-secret'
    if path.is_symlink():
        raise ValueError('Storage secret must not be a symlink.')
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        value = path.read_text().strip()
        if len(value) < 32:
            raise ValueError('Existing storage secret is invalid.')
        return value
    value = secrets.token_urlsafe(48)
    with os.fdopen(fd, 'w') as stream:
        stream.write(value + '\n')
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup', action='store_true', help='Install bundled framework into app-local isolated .venv')
    parser.add_argument('--run', action='store_true', help='Verify then run the generated app in foreground')
    parser.add_argument('--check', action='store_true', help='Check installed source hashes and provenance; no installation')
    parser.add_argument('--port', type=int, default=8092)
    parser.add_argument('--output', type=Path, help='Write import-verification JSON to this path')
    args = parser.parse_args(argv)
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        parser.error('Use Python 3.11, 3.12, or 3.13.')
    if not 1024 <= args.port <= 65535:
        parser.error('Use a port between 1024 and 65535.')
    root = Path(__file__).resolve().parent
    try:
        lock = bundle_lock(root)
        py = setup(root, lock) if args.setup else environment_python(root)
        if not py.is_file():
            raise RuntimeError('Runtime is not installed. Run python3.13 bootstrap.py --setup --run.')
        report = verify_install(root, py)
        if Path(report['prefix']).resolve() != (root / '.venv').resolve():
            raise RuntimeError('Installed interpreter prefix is not this app\'s isolated .venv.')
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)
        if args.run:
            with socket.socket() as sock:
                try:
                    sock.bind(('127.0.0.1', args.port))
                except OSError as exc:
                    raise RuntimeError(f'Port {args.port} is occupied. No existing process was stopped.') from exc
            env = clean_environment()
            env.update(NICEGUI_BASE_HOST='127.0.0.1', NICEGUI_BASE_PORT=str(args.port),
                       NICEGUI_BASE_STORAGE_SECRET=secret(root))
            os.chdir(root)
            print(f'Open http://127.0.0.1:{args.port} · {lock["build_id"]}', flush=True)
            os.execve(str(py), [str(py), str(root / 'app.py')], env)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f'GENERATED_APP_SETUP=FAIL {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
