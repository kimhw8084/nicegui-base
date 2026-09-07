#!/usr/bin/env python3
"""Self-contained D5 teammate verifier for an installed D4 RC package."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile


D5_ID = '@D5_PACKAGE_ID@'
RC_ID = '@RC_CANDIDATE_ID@'
FRAMEWORK_VERSION = '3.0.0a8'
NICEGUI_VERSION = '3.15.0'
ERROR_MARKERS = ('Traceback (most recent call last):', 'Exception in ASGI application', 'ERROR:', 'AttributeError:', 'TypeError:', 'RuntimeError:')
MUTABLE_PREFIXES = ('.venv', '.nicegui', '.ngb-d5-evidence')
FIXTURE = 'id,thickness,batch,note\n0000,0.125,A,alpha\n0001,1.125,B,alpha\n0002,2.125,A,beta\n0003,3.125,B,gamma\n'


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'VIRTUAL_ENV'):
        env.pop(key, None)
    env.update(PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    return env


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def wait_http(url: str, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last = ''
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 400:
                    return
                last = f'HTTP {response.status}'
        except (OSError, urllib.error.URLError) as exc:
            last = str(exc)
        time.sleep(.2)
    raise RuntimeError(f'{url} did not become ready: {last}')


def run_logged(command: list[str | Path], *, cwd: Path, log: Path, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run([str(item) for item in command], cwd=cwd, env=clean_env(), text=True, stdout=stream, stderr=subprocess.STDOUT, check=False, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'command failed with exit {result.returncode}; see {log}')
    return result


def verify_manifest(root: Path) -> dict[str, object]:
    entries: dict[str, str] = {}
    for line in (root / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        try:
            digest, relative = line.split('  ', 1)
        except ValueError as exc:
            raise RuntimeError(f'invalid SHA256SUMS line: {line!r}') from exc
        relative_path = Path(relative)
        if relative_path.is_absolute() or '..' in relative_path.parts or relative in entries:
            raise RuntimeError(f'unsafe or duplicate manifest path: {relative!r}')
        entries[relative] = digest
    missing = [relative for relative in entries if not (root / relative).is_file()]
    mismatches = [relative for relative, expected in entries.items() if (root / relative).is_file() and sha256(root / relative) != expected]
    actual = set()
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative == 'SHA256SUMS.txt' or any(relative == prefix or relative.startswith(prefix + '/') for prefix in MUTABLE_PREFIXES):
            continue
        actual.add(relative)
    extras = sorted(actual - set(entries))
    if missing or mismatches or extras:
        raise RuntimeError(f'package manifest failed: missing={missing}, mismatches={mismatches}, extras={extras}')
    return {'status': 'PASS', 'entries': len(entries), 'verified': len(entries)}


def verify_identity(root: Path) -> dict[str, object]:
    identity = json.loads((root / 'RC_IDENTITY.json').read_text(encoding='utf-8'))
    if identity.get('d5_package_id') != D5_ID or identity.get('rc_candidate_id') != RC_ID:
        raise RuntimeError('team package identity is inconsistent')
    if identity.get('framework_version') != FRAMEWORK_VERSION or identity.get('nicegui_version') != NICEGUI_VERSION:
        raise RuntimeError('team package runtime identity is inconsistent')
    wheels = sorted((root / 'wheel').glob('nicegui_base-*.whl'))
    if len(wheels) != 1 or wheels[0].name != identity.get('wheel_filename') or sha256(wheels[0]) != identity.get('wheel_sha256'):
        raise RuntimeError('team package wheel identity/hash failed')
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
        record = next((name for name in names if name.endswith('.dist-info/RECORD')), None)
        metadata = next((name for name in names if name.endswith('.dist-info/METADATA')), None)
        if not record or not metadata:
            raise RuntimeError('candidate wheel lacks RECORD or METADATA')
        if 'Version: ' + FRAMEWORK_VERSION not in archive.read(metadata).decode('utf-8'):
            raise RuntimeError('candidate wheel framework version mismatch')
    return {'status': 'PASS', 'rc_candidate_id': RC_ID, 'wheel_filename': wheels[0].name, 'wheel_sha256': sha256(wheels[0]), 'd4_bundle_sha256': identity['d4_bundle_sha256']}


def verify_import(python: Path, cwd: Path, log: Path) -> dict[str, object]:
    code = "import importlib.metadata as m, json, nicegui_base; from pathlib import Path; p=Path(nicegui_base.__file__).resolve(); print(json.dumps({'package':str(p),'nicegui_base':m.version('nicegui-base'),'nicegui':m.version('nicegui'),'site_packages':'site-packages' in p.parts}))"
    result = subprocess.run([str(python), '-I', '-c', code], cwd=cwd, env=clean_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=90)
    log.write_text(result.stdout, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'installed import failed; see {log}')
    payload = json.loads(result.stdout.strip())
    if not payload.get('site_packages') or payload.get('nicegui') != NICEGUI_VERSION or payload.get('nicegui_base') != FRAMEWORK_VERSION:
        raise RuntimeError(f'installed import provenance failed: {payload}')
    return payload


def safe_extract(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    root = target.resolve()
    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            relative = Path(info.filename)
            if relative.is_absolute() or '..' in relative.parts:
                raise RuntimeError(f'unsafe generated ZIP entry: {info.filename}')
            destination = (target / relative).resolve()
            destination.relative_to(root)
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read(info.filename))


def terminate(process: subprocess.Popen, timeout: float = 15.0) -> int:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=5)


def log_errors(*paths: Path) -> list[str]:
    found = []
    for path in paths:
        if path.is_file():
            text = path.read_text(encoding='utf-8', errors='replace')
            found.extend(f'{path.name}:{marker}' for marker in ERROR_MARKERS if marker in text)
    return found


def browser_acceptance(base_url: str, python: Path, work: Path, evidence: Path, browser_log: Path) -> dict[str, object]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError('focused browser smoke requires Playwright; set NGB_D5_BROWSER_PYTHON to a Python 3.11–3.13 interpreter with it installed') from exc

    events: list[str] = []
    page = None
    generated_process = None
    generated_log = evidence / 'generated_app.log'
    generated_zip = work / 'generated.zip'
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True, viewport={'width': 1440, 'height': 900})
            page = context.new_page()
            page.on('pageerror', lambda exc: events.append('pageerror: ' + str(exc)))
            page.on('console', lambda message: events.append(f'console:{message.type}: {message.text}') if message.type == 'error' else None)

            def step(name: str) -> None:
                events.append('PASS ' + name)

            page.goto(base_url.rstrip('/') + '/', wait_until='networkidle', timeout=30000)
            if 'NiceGUI Base' not in page.locator('body').inner_text():
                raise RuntimeError('Workbench did not render its product identity')
            step('open Workbench')
            page.goto(base_url.rstrip('/') + '/build', wait_until='networkidle', timeout=30000)
            page.get_by_role('textbox', name='What are you trying to build?').fill('Analyze thickness by batch and export a chart')
            page.get_by_role('button', name='Get recommendation').click()
            page.wait_for_timeout(350)
            page.get_by_role('button', name='Use recommended structure').click()
            page.wait_for_timeout(600)
            step('create starter project')
            page.get_by_role('radio', name='Paste').click()
            page.wait_for_timeout(250)
            page.get_by_role('textbox', name='Paste data').fill(FIXTURE)
            page.get_by_role('button', name='Load pasted data').click()
            page.locator('[data-dock-rows="4"]').wait_for(state='attached', timeout=10000)
            page.wait_for_timeout(700)
            step('import 4-row semiconductor fixture')
            page.get_by_role('button', name='Continue to compose').click()
            page.wait_for_timeout(700)
            page.get_by_role('button', name='Replace with recommended composition').click()
            page.wait_for_timeout(900)
            page.get_by_role('textbox', name='Application name').fill('D5 Acceptance App')
            page.get_by_role('button', name='Apply project settings').click()
            page.wait_for_timeout(800)
            if 'LineChart' not in page.locator('body').inner_text() or 'DataTable' not in page.locator('body').inner_text():
                raise RuntimeError('real chart/table composition was not configured')
            step('configure chart and table')
            page.reload(wait_until='networkidle', timeout=30000)
            page.get_by_role('button', name='Review app').wait_for(state='visible', timeout=10000)
            page.get_by_role('button', name='Review app').click()
            page.wait_for_timeout(800)
            review_text = page.locator('body').inner_text()
            if 'Chart mapping · measurement: thickness' not in review_text or 'Blocking\n0' not in review_text:
                raise RuntimeError('saved/reopened project lost its real measurement mapping or readiness')
            step('save and reopen project')
            page.get_by_role('button', name='Generate project').click()
            page.wait_for_timeout(1800)
            page.get_by_role('button', name='Run live startup proof').click()
            page.get_by_role('button', name='Download starter ZIP (local startup checked)').wait_for(state='visible', timeout=120000)
            with page.expect_download(timeout=30000) as download_info:
                page.get_by_role('button', name='Download starter ZIP (local startup checked)').click()
            download_info.value.save_as(str(generated_zip))
            step('generate and export app')

            with zipfile.ZipFile(generated_zip) as archive:
                required = {'app.py', 'bootstrap.py', 'pages/home.py', 'services/app_data.py', 'vendor/nicegui_base-3.0.0a8-py3-none-any.whl'}
                missing = sorted(required - set(archive.namelist()))
                if missing:
                    raise RuntimeError(f'generated ZIP is incomplete: {missing}')
            generated_root = work / 'generated'
            safe_extract(generated_zip, generated_root)
            app_text = (generated_root / 'app.py').read_text(encoding='utf-8') + (generated_root / 'pages/home.py').read_text(encoding='utf-8')
            if 'D5 Acceptance App' not in app_text or 'LineChart' not in app_text or 'DataTable' not in app_text:
                raise RuntimeError('generated app does not retain the configured chart/table')
            run_logged([python, generated_root / 'bootstrap.py', '--setup', '--check', '--output', generated_root / 'bootstrap_proof.json'], cwd=generated_root, log=evidence / 'generated_bootstrap.log', timeout=1200)
            proof = json.loads((generated_root / 'bootstrap_proof.json').read_text(encoding='utf-8'))
            if not proof.get('passed') or int(proof.get('verified_files', 0)) != 551:
                raise RuntimeError(f'generated app bundled provenance failed: {proof}')
            generated_port = free_port()
            generated_stream = generated_log.open('w', encoding='utf-8')
            generated_process = subprocess.Popen([str(python), str(generated_root / 'bootstrap.py'), '--run', '--port', str(generated_port)], cwd=generated_root, env=clean_env(), stdout=generated_stream, stderr=subprocess.STDOUT, text=True)
            wait_http(f'http://127.0.0.1:{generated_port}/readyz')
            with urllib.request.urlopen(f'http://127.0.0.1:{generated_port}/healthz', timeout=5) as response:
                if response.status != 200:
                    raise RuntimeError('generated app health check failed')
            page.goto(f'http://127.0.0.1:{generated_port}/', wait_until='networkidle', timeout=30000)
            generated_text = page.locator('body').inner_text()
            if 'D5 Acceptance App' not in generated_text or not page.locator('.cui-chart-canvas, canvas').count():
                raise RuntimeError('independently installed generated app did not render its chart surface')
            step('independently install and launch generated app')
            return {'status': 'PASS', 'generated_zip_sha256': sha256(generated_zip), 'generated_runtime_verified_files': proof.get('verified_files'), 'events': events}
    except Exception:
        if page is not None and not page.is_closed():
            try:
                page.screenshot(path=str(evidence / 'failure.png'), full_page=False)
            except Exception:
                pass
        raise
    finally:
        if generated_process is not None:
            terminate(generated_process)
        if 'generated_stream' in locals():
            generated_stream.close()
        browser_log.write_text('\n'.join(events) + '\n', encoding='utf-8')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path)
    parser.add_argument('--evidence-zip', type=Path)
    parser.add_argument('--port', type=int)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent
    evidence = (args.evidence_dir or Path(tempfile.mkdtemp(prefix='ngb-d5-evidence-'))).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    evidence_zip = (args.evidence_zip or evidence.with_suffix('.zip')).resolve()
    result: dict[str, object] = {'d5_package_id': D5_ID, 'rc_candidate_id': RC_ID, 'status': 'FAIL', 'evidence_dir': str(evidence), 'evidence_zip': str(evidence_zip), 'checks': {}}
    process = None
    work_temp = tempfile.TemporaryDirectory(prefix='ngb-d5-work-')
    work = Path(work_temp.name)
    neutral = work / 'neutral'
    neutral.mkdir()
    workbench_log = evidence / 'workbench.log'
    try:
        result['checks']['identity_hashes'] = verify_identity(root)
        result['checks']['manifest'] = verify_manifest(root)
        python = root / '.venv' / 'bin' / 'python'
        if not python.is_file():
            raise RuntimeError('D5 environment is not installed; run ./install_d5.sh first')
        result['checks']['runtime_import'] = verify_import(python, neutral, evidence / 'runtime_import.log')
        run_logged([root / '.venv' / 'bin' / 'nicegui-base', 'runtime-contract'], cwd=neutral, log=evidence / 'runtime_contract.log', timeout=300)
        result['checks']['runtime_contract'] = 'PASS'
        port = args.port or free_port()
        log_stream = workbench_log.open('w', encoding='utf-8')
        process = subprocess.Popen([str(python), str(root / 'launch_d5.py'), '--port', str(port)], cwd=neutral, env=clean_env(), stdout=log_stream, stderr=subprocess.STDOUT, text=True)
        wait_http(f'http://127.0.0.1:{port}/readyz')
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=5) as response:
            health = response.read().decode()
        if 'healthy' not in health:
            raise RuntimeError(f'Workbench health is not healthy: {health}')
        result['checks']['workbench'] = {'status': 'PASS', 'healthz': health, 'port': port}
        result['checks']['first_30_minutes'] = browser_acceptance(f'http://127.0.0.1:{port}', python, work, evidence, evidence / 'browser.log')
        result['status'] = 'PASS'
    except Exception as exc:
        result['failure'] = f'{type(exc).__name__}: {exc}'
        screenshot_target = evidence / 'failure.png'
        if screenshot_target.exists():
            result['failure_screenshot'] = str(screenshot_target)
    finally:
        if process is not None:
            result.setdefault('checks', {})['graceful_shutdown'] = 'PASS' if terminate(process) in (0, -signal.SIGTERM) else 'FAIL'
        if 'log_stream' in locals():
            log_stream.close()
        result['error_markers'] = log_errors(workbench_log, evidence / 'generated_app.log')
        if result['status'] == 'PASS' and result['error_markers']:
            result['status'] = 'FAIL'
            result['failure'] = 'server error markers found: ' + ', '.join(result['error_markers'])
        result['logs'] = sorted(str(path) for path in evidence.glob('*.log'))
        (evidence / 'D5_RESULT.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        members = [evidence / 'D5_RESULT.json', *sorted(evidence.glob('*.log'))]
        failure_screens = sorted(evidence.glob('failure*.png'))
        members.extend(failure_screens)
        with zipfile.ZipFile(evidence_zip, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for member in members:
                if member.is_file():
                    archive.write(member, member.name)
        work_temp.cleanup()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
