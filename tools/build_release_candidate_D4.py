#!/usr/bin/env python3
"""Build and qualify the self-contained NiceGUI Base D4 release candidate.

The builder uses a temporary source copy, so wheel construction never writes
build products into the dirty development checkout. Its output directory is
explicitly owned and may be rebuilt idempotently; an unmarked directory is
never removed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
import urllib.error
import urllib.request
import zipfile


CANDIDATE_ID = 'NGB-20260905-D4'
FRAMEWORK_VERSION = '3.0.0a8'
NICEGUI_VERSION = '3.15.0'
DEFAULT_OUTPUT = Path('/private/tmp/ngb_d4_rc')
OWNER_MARKER = '.ngb-d4-owned'
ERROR_MARKERS = ('Traceback (most recent call last):', 'Exception in ASGI application', 'ERROR:', 'AttributeError:', 'TypeError:', 'RuntimeError:')
TEMPLATE_ROOT = Path(__file__).with_name('rc_bundle')
# Installation creates these mutable runtime trees beside the immutable RC
# contents. They stay on disk for recovery, but never enter manifests/archives.
BUNDLE_RUNTIME_EXCLUDES = ('.venv', '.nicegui')


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + '\n', encoding='utf-8')


def source_files(source: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for package in ('nicegui_base', 'company_ui'):
        root = source / package
        if not root.is_dir():
            continue
        files.extend(path for path in root.rglob('*') if path.is_file() and '__pycache__' not in path.parts)
    return tuple(sorted(files))


def source_manifest(source: Path) -> dict[str, dict[str, Any]]:
    return {
        path.relative_to(source).as_posix(): {'sha256': sha256_file(path), 'size_bytes': path.stat().st_size}
        for path in source_files(source)
    }


def copy_source_snapshot(source: Path, destination: Path) -> None:
    def ignore(_directory: str, names: list[str]) -> set[str]:
        ignored = {'.git', '.pytest_cache', '__pycache__', 'build', 'dist'}
        return {name for name in names if name in ignored or name.endswith('.egg-info')}
    shutil.copytree(source, destination, ignore=ignore)


def wheel_names(path: Path) -> tuple[str, ...]:
    with zipfile.ZipFile(path) as archive:
        return tuple(name for name in archive.namelist() if name and not name.endswith('/'))


def verify_wheel_sources(source: Path, wheel: Path) -> dict[str, Any]:
    mismatches: list[str] = []
    missing_source: list[str] = []
    packaged: list[str] = []
    with zipfile.ZipFile(wheel) as archive:
        for name in sorted(wheel_names(wheel)):
            if '.dist-info/' in name:
                continue
            packaged.append(name)
            source_path = source / name
            if not source_path.is_file():
                missing_source.append(name)
            elif archive.read(name) != source_path.read_bytes():
                mismatches.append(name)
    return {
        'passed': not mismatches and not missing_source,
        'packaged_source_files': len(packaged),
        'mismatches': mismatches,
        'missing_source': missing_source,
        'wheel_sha256': sha256_file(wheel),
    }


def copy_templates(bundle: Path) -> None:
    for template in TEMPLATE_ROOT.iterdir():
        if not template.is_file():
            continue
        target = bundle / template.name
        text = template.read_text(encoding='utf-8').replace('@CANDIDATE_ID@', CANDIDATE_ID).replace('@OWNER_MARKER@', OWNER_MARKER)
        target.write_text(text, encoding='utf-8')
        if template.suffix == '.sh' or template.name == 'launch_rc.py':
            target.chmod(0o755)


def git_metadata(repo: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        result = subprocess.run(['git', *args], cwd=repo, check=False, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else ''
    diff = subprocess.run(['git', 'diff', '--no-ext-diff', '--binary', '--', 'source'], cwd=repo, check=False, capture_output=True)
    return {
        'head': run('rev-parse', 'HEAD'),
        'source_worktree_status': run('status', '--short', '--', 'source'),
        'source_worktree_diff_sha256': sha256_bytes(diff.stdout),
    }


def run_logged(command: list[str | Path], *, cwd: Path, log: Path, env: dict[str, str] | None = None, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run([str(item) for item in command], cwd=cwd, env=env, text=True, stdout=stream, stderr=subprocess.STDOUT, check=False, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'command failed ({result.returncode}): {command}; see {log}')
    return result


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in tuple(env):
        if key in {'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'VIRTUAL_ENV'} or key.startswith(('NICEGUI_', 'COMPANY_UI_')):
            env.pop(key, None)
    env.update(PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    return env


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def wait_http(url: str, timeout: float = 30.0) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout
    last = ''
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if 200 <= response.status < 400:
                    return True, ''
                last = f'HTTP {response.status}'
        except (OSError, urllib.error.URLError) as exc:
            last = str(exc)
        time.sleep(.2)
    return False, last


def qualify(bundle: Path, output: Path, python_executable: str) -> dict[str, Any]:
    qualification = output.parent / f'{output.name}_qualification'
    if qualification.exists():
        marker = qualification / OWNER_MARKER
        if not marker.is_file():
            raise RuntimeError(f'refusing to replace unowned qualification directory: {qualification}')
        shutil.rmtree(qualification)
    qualification.mkdir(parents=True)
    (qualification / OWNER_MARKER).write_text(CANDIDATE_ID + '\n', encoding='utf-8')
    neutral = qualification / 'neutral'
    neutral.mkdir()
    logs = qualification / 'logs'
    venv_dir = qualification / 'venv'
    if not venv_dir.exists():
        run_logged([python_executable, '-m', 'venv', str(venv_dir)], cwd=neutral, log=logs / 'create_venv.log', env=clean_env(), timeout=180)
    py = venv_dir / 'bin' / 'python'
    if not py.is_file():
        raise RuntimeError(f'qualification venv interpreter missing: {py}')
    run_logged([py, '-m', 'pip', 'install', '-r', bundle / 'requirements.txt'], cwd=neutral, log=logs / 'install_requirements.log', env=clean_env(), timeout=900)
    run_logged([py, '-m', 'pip', 'install', '--no-deps', *sorted((bundle / 'wheel').glob('*.whl'))], cwd=neutral, log=logs / 'install_wheel.log', env=clean_env(), timeout=300)
    run_logged([py, '-m', 'pip', 'check'], cwd=neutral, log=logs / 'pip_check.log', env=clean_env(), timeout=120)
    provenance = subprocess.run([py, '-I', '-c', "import json, nicegui_base, importlib.metadata as m; from pathlib import Path; p=Path(nicegui_base.__file__).resolve(); print(json.dumps({'package':str(p),'nicegui_base':m.version('nicegui-base'),'nicegui':m.version('nicegui'),'site_packages':'site-packages' in p.parts}))"], cwd=neutral, env=clean_env(), capture_output=True, text=True, check=False)
    if provenance.returncode or not json.loads(provenance.stdout).get('site_packages'):
        raise RuntimeError(f'installed import provenance failed: {provenance.stdout} {provenance.stderr}')
    (qualification / 'installed_import_provenance.json').write_text(provenance.stdout + '\n', encoding='utf-8')
    run_logged([venv_dir / 'bin' / 'nicegui-base', 'runtime-contract', '--format', 'json'], cwd=neutral, log=logs / 'runtime_contract.log', env=clean_env(), timeout=300)
    smoke_output = qualification / 'runtime_smoke'
    run_logged([venv_dir / 'bin' / 'nicegui-base', 'runtime-smoke', '--output', smoke_output, '--format', 'json'], cwd=neutral, log=logs / 'runtime_smoke.log', env=clean_env(), timeout=600)
    smoke = json.loads((smoke_output / 'RUNTIME_SMOKE_REPORT.json').read_text(encoding='utf-8'))
    if not smoke.get('ok'):
        raise RuntimeError(f'installed runtime smoke failed: {smoke_output}')

    port = free_port()
    server_log = logs / 'workbench_server.log'
    with server_log.open('w', encoding='utf-8') as stream:
        process = subprocess.Popen([py, str(bundle / 'launch_rc.py'), '--port', str(port)], cwd=neutral, env=clean_env(), stdout=stream, stderr=subprocess.STDOUT, text=True)
    ready, detail = wait_http(f'http://127.0.0.1:{port}/readyz')
    if not ready:
        process.terminate(); process.wait(timeout=10)
        raise RuntimeError(f'installed Workbench did not become ready: {detail}; see {server_log}')
    healthz = urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=3).read().decode()
    readyz = urllib.request.urlopen(f'http://127.0.0.1:{port}/readyz', timeout=3).read().decode()
    process.send_signal(signal.SIGTERM)
    returncode = process.wait(timeout=15)
    log_text = server_log.read_text(encoding='utf-8', errors='replace')
    markers = [marker for marker in ERROR_MARKERS if marker in log_text]
    if returncode not in (0, -signal.SIGTERM) or markers:
        raise RuntimeError(f'graceful Workbench shutdown failed (returncode={returncode}, markers={markers}); see {server_log}')
    result = {
        'candidate_id': CANDIDATE_ID,
        'status': 'PASS',
        'python': sys.version,
        'venv': str(venv_dir),
        'neutral_cwd': str(neutral),
        'pip_check': 'PASS',
        'installed_import_provenance': json.loads(provenance.stdout),
        'runtime_contract': 'PASS',
        'runtime_smoke': smoke,
        'workbench': {'healthz': healthz, 'readyz': readyz, 'graceful_shutdown': 'PASS', 'server_log': str(server_log), 'error_markers': markers},
    }
    write_json(bundle / 'QUALIFICATION_SUMMARY.json', result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--skip-qualification', action='store_true')
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[1]
    source = repo / 'source'
    if not source.is_dir() or not (source / 'pyproject.toml').is_file():
        raise SystemExit(f'authoritative source missing: {source}')
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        raise SystemExit('D4 build requires Python 3.11, 3.12, or 3.13')
    sys.path.insert(0, str(source))
    output = args.output.resolve()
    if output.exists():
        if not (output / OWNER_MARKER).is_file():
            raise SystemExit(f'refusing to replace unowned output directory: {output}')
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / OWNER_MARKER).write_text(CANDIDATE_ID + '\n', encoding='utf-8')
    bundle = output / 'bundle'
    wheel_dir = bundle / 'wheel'
    bundle.mkdir(); wheel_dir.mkdir()
    with tempfile.TemporaryDirectory(prefix='ngb-d4-source-') as temp:
        build_source = Path(temp) / 'source'
        copy_source_snapshot(source, build_source)
        run_logged([sys.executable, '-m', 'pip', 'wheel', '--no-deps', str(build_source), '--wheel-dir', str(wheel_dir)], cwd=Path(temp), log=output / 'wheel-build.log', env=clean_env(), timeout=900)
    wheels = sorted(wheel_dir.glob('nicegui_base-*.whl'))
    if len(wheels) != 1:
        raise SystemExit(f'expected exactly one D4 wheel, found {wheels}')
    wheel = wheels[0]
    from nicegui_base.governance.release_artifacts import verify_wheel
    wheel_report = verify_wheel(wheel)
    runtime_requires = tuple(item for item in wheel_report.requires_dist if 'extra ==' not in item)
    if not wheel_report.passed or wheel_report.metadata_name != 'nicegui-base' or wheel_report.metadata_version != FRAMEWORK_VERSION or runtime_requires != ('nicegui==3.15.0',):
        raise SystemExit(f'wheel integrity/metadata failed: {wheel_report}')
    source_report = verify_wheel_sources(source, wheel)
    if not source_report['passed']:
        raise SystemExit(f'wheel/source representation failed: {source_report}')
    source_hashes = source_manifest(source)
    write_json(bundle / 'SOURCE_PACKAGE_SHA256.json', {'candidate_id': CANDIDATE_ID, 'authoritative_root': 'source/', 'files': source_hashes, 'source_state_sha256': sha256_bytes(json.dumps(source_hashes, sort_keys=True).encode())})
    write_json(bundle / 'WHEEL_SOURCE_VERIFICATION.json', source_report)
    shutil.copy2(repo / 'requirements.txt', bundle / 'requirements.txt')
    copy_templates(bundle)
    provenance = {
        'candidate_id': CANDIDATE_ID, 'framework': 'nicegui-base', 'framework_version': FRAMEWORK_VERSION, 'nicegui_version': NICEGUI_VERSION,
        'authoritative_source': 'source/', 'source_package_sha256': sha256_bytes(json.dumps(source_hashes, sort_keys=True).encode()),
        'source_state': git_metadata(repo), 'wheel': {'path': f'wheel/{wheel.name}', 'sha256': sha256_file(wheel), 'size_bytes': wheel.stat().st_size},
        'requirements': {'path': 'requirements.txt', 'sha256': sha256_file(bundle / 'requirements.txt')},
        'builder': {'python': sys.version, 'pip': subprocess.run([sys.executable, '-m', 'pip', '--version'], capture_output=True, text=True, check=False).stdout.strip()},
    }
    write_json(bundle / 'BUILD_PROVENANCE.json', provenance)
    (bundle / 'QUALIFICATION_SUMMARY.json').write_text(json.dumps({'candidate_id': CANDIDATE_ID, 'status': 'NOT_RUN'}, indent=2) + '\n', encoding='utf-8')
    (bundle / 'CERTIFICATION_SUMMARY.md').write_text(f'# {CANDIDATE_ID} certification\n\nBuild and source/artifact provenance are complete. Installed qualification and browser evidence are written by the governed candidate verifiers.\n', encoding='utf-8')
    from nicegui_base.governance.release_artifacts import write_sha256_manifest, verify_sha256_manifest, build_deterministic_zip
    write_sha256_manifest(bundle, exclude=BUNDLE_RUNTIME_EXCLUDES)
    manifest_check = verify_sha256_manifest(bundle, exclude=BUNDLE_RUNTIME_EXCLUDES)
    if not manifest_check.passed:
        raise SystemExit(f'bundle manifest failed: {manifest_check}')
    qualification = None if args.skip_qualification else qualify(bundle, output, args.python)
    if qualification:
        # Qualification is a bundle authority file, so refresh the exact manifest
        # after the runtime result is recorded.
        write_sha256_manifest(bundle, exclude=BUNDLE_RUNTIME_EXCLUDES)
        manifest_check = verify_sha256_manifest(bundle, exclude=BUNDLE_RUNTIME_EXCLUDES)
        if not manifest_check.passed:
            raise SystemExit(f'bundle manifest failed after qualification: {manifest_check}')
    archive = build_deterministic_zip(bundle, output / f'{CANDIDATE_ID}_RC.zip', exclude=BUNDLE_RUNTIME_EXCLUDES)
    summary = {'candidate_id': CANDIDATE_ID, 'bundle_directory': str(bundle), 'archive': str(archive), 'archive_sha256': sha256_file(archive), 'wheel_sha256': sha256_file(wheel), 'source_package_files': len(source_hashes), 'packaged_source_files': source_report['packaged_source_files'], 'qualification': qualification or {'status': 'NOT_RUN'}}
    write_json(output / 'D4_BUILD_RESULT.json', summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
