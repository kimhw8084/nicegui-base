#!/usr/bin/env python3
"""Clean-room D5 setup/launch/rollback simulation using only the team archive."""
from __future__ import annotations

import argparse
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
import urllib.request
import zipfile


ARCHIVE = Path('/private/tmp/ngb_d5_team/NGB-20260905-D5_TEAM.zip')
OWNER_MARKER = '.ngb-d5-harness-owned'
ERROR_MARKERS = ('Traceback (most recent call last):', 'Exception in ASGI application', 'ERROR:', 'AttributeError:', 'TypeError:', 'RuntimeError:')


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'VIRTUAL_ENV'):
        env.pop(key, None)
    env.update(PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    env.update(extra or {})
    return env


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def wait(url: str, timeout: float = 40.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 400:
                    return
        except OSError:
            pass
        time.sleep(.2)
    raise RuntimeError(f'timed out waiting for {url}')


def extract(archive: Path, target: Path) -> None:
    target.mkdir(parents=True)
    root = target.resolve()
    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            relative = Path(info.filename)
            if relative.is_absolute() or '..' in relative.parts:
                raise RuntimeError(f'unsafe package entry: {info.filename}')
            destination = (target / relative).resolve()
            destination.relative_to(root)
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read(info.filename))
                if destination.suffix == '.sh' or destination.name.endswith('.py'):
                    destination.chmod(0o755)


def command(command: list[str | Path], *, cwd: Path, log: Path, env: dict[str, str], timeout: int = 900) -> None:
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run([str(item) for item in command], cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, text=True, check=False, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'command failed with exit {result.returncode}; see {log}')


def launch_once(root: Path, attempt: int, output: Path, env: dict[str, str]) -> dict[str, object]:
    port = free_port()
    log = output / f'attempt_{attempt}_launch.log'
    with log.open('w', encoding='utf-8') as stream:
        process = subprocess.Popen([str(root / 'launch_d5.sh')], cwd=root / 'neutral', env=clean_env({'NGB_D5_PORT': str(port), **env}), stdout=stream, stderr=subprocess.STDOUT, text=True)
    try:
        wait(f'http://127.0.0.1:{port}/readyz')
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=5) as response:
            health = response.read().decode()
        if 'healthy' not in health:
            raise RuntimeError(f'health was not healthy: {health}')
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        process.wait(timeout=15)
    text = log.read_text(encoding='utf-8', errors='replace')
    markers = [marker for marker in ERROR_MARKERS if marker in text]
    if markers:
        raise RuntimeError(f'launch log contains error markers: {markers}')
    return {'status': 'PASS', 'port': port, 'healthz': health, 'log': str(log), 'returncode': process.returncode}


def one_attempt(source_archive: Path, attempt: int, output: Path, python: str, *, exercise_rollback: bool = False) -> dict[str, object]:
    root = output / f'attempt_{attempt}'
    extract(source_archive, root)
    neutral = root / 'neutral'
    neutral.mkdir()
    env = {'NICEGUI_BASE_PYTHON': python}
    command(['bash', root / 'install_d5.sh'], cwd=neutral, log=output / f'attempt_{attempt}_install_1.log', env=clean_env(env), timeout=1200)
    command(['bash', root / 'install_d5.sh'], cwd=neutral, log=output / f'attempt_{attempt}_install_2_idempotent.log', env=clean_env(env), timeout=1200)
    installed = root / '.venv' / 'bin' / 'python'
    import_log = output / f'attempt_{attempt}_import.log'
    command([installed, '-I', '-c', "import json, nicegui_base; from pathlib import Path; print(json.dumps({'package':str(Path(nicegui_base.__file__).resolve()),'site_packages':'site-packages' in Path(nicegui_base.__file__).resolve().parts}))"], cwd=neutral, log=import_log, env=clean_env(), timeout=90)
    return_value = launch_once(root, attempt, output, env)
    result = {'attempt': attempt, 'install_twice': 'PASS', 'import': json.loads(import_log.read_text(encoding='utf-8').strip()), 'launch': return_value}
    if exercise_rollback:
        command(['bash', root / 'uninstall_d5.sh'], cwd=neutral, log=output / f'attempt_{attempt}_uninstall.log', env=clean_env(), timeout=120)
        backups = sorted(root.glob('.venv.rollback.*'))
        if (root / '.venv').exists() or not backups:
            raise RuntimeError('uninstall did not remove the active D5 environment safely')
        command(['bash', root / 'uninstall_d5.sh'], cwd=neutral, log=output / f'attempt_{attempt}_uninstall_idempotent.log', env=clean_env(), timeout=120)
        command(['bash', root / 'install_d5.sh'], cwd=neutral, log=output / f'attempt_{attempt}_reinstall.log', env=clean_env(env), timeout=1200)
        result['rollback_reinstall'] = 'PASS'
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=ARCHIVE)
    parser.add_argument('--output', type=Path, default=Path('/private/tmp/ngb_d5_evidence/clean_room'))
    parser.add_argument('--python', default='python3.13', help='standalone Python 3.11–3.13 used to create the clean-room venv')
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output.exists():
        if not (output / OWNER_MARKER).is_file():
            raise SystemExit(f'refusing to replace unowned evidence directory: {output}')
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / OWNER_MARKER).write_text('NGB-20260905-D5\n', encoding='utf-8')
    if b'/Users/haewonkim/home/development/nicegui-base' in args.archive.read_bytes():
        raise SystemExit('team archive contains a development-repository path')
    results = []
    try:
        results.append(one_attempt(args.archive.resolve(), 1, output, args.python))
        results.append(one_attempt(args.archive.resolve(), 2, output, args.python, exercise_rollback=True))
        status = 'PASS'
    except Exception as exc:
        status = 'FAIL'
        results.append({'failure': f'{type(exc).__name__}: {exc}'})
    report = {'status': status, 'archive': str(args.archive.resolve()), 'python': args.python, 'attempts': results, 'development_repo_dependency': False}
    report_path = output / 'CLEAN_ROOM_RESULT.json'
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
