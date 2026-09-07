#!/usr/bin/env python3
"""Self-contained D6G identity, runtime, browser and scaffold verifier."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile


D6G_ID = '@D6G_ID@'
FRAMEWORK_VERSION = '3.0.0a8'
NICEGUI_VERSION = '3.15.0'
ERROR_MARKERS = ('Traceback (most recent call last):', 'Exception in ASGI application', 'ERROR:', 'AttributeError:', 'TypeError:', 'RuntimeError:')
MUTABLE_PREFIXES = ('.venv', '.ngb-d6g-evidence', '.ngb-d6g-work')


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'VIRTUAL_ENV'):
        env.pop(key, None)
    env.update(PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    env.update(extra or {})
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


def run_logged(command: list[str | Path], *, cwd: Path, log: Path, timeout: int = 900, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run([str(item) for item in command], cwd=cwd, env=env or clean_env(), text=True, stdout=stream, stderr=subprocess.STDOUT, check=False, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'command failed with exit {result.returncode}; see {log}')
    return result


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


def terminate(process: subprocess.Popen, timeout: float = 15.0) -> int:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=5)


def verify_manifest(root: Path) -> dict[str, object]:
    entries: dict[str, str] = {}
    for line in (root / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if line.strip():
            digest, relative = line.split('  ', 1)
            entries[relative] = digest
    actual = set()
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative == 'SHA256SUMS.txt' or any(relative == prefix or relative.startswith(prefix + '/') for prefix in MUTABLE_PREFIXES):
            continue
        actual.add(relative)
    missing = sorted(relative for relative in entries if not (root / relative).is_file())
    mismatches = sorted(relative for relative, digest in entries.items() if (root / relative).is_file() and sha256(root / relative) != digest)
    extras = sorted(actual - set(entries))
    if missing or mismatches or extras:
        raise RuntimeError(f'manifest failed: missing={missing}, mismatches={mismatches}, extras={extras}')
    return {'status': 'PASS', 'entries': len(entries), 'verified': len(entries)}


def verify_identity(root: Path) -> dict[str, object]:
    identity = json.loads((root / 'RC_IDENTITY.json').read_text(encoding='utf-8'))
    if identity.get('team_package_id') != D6G_ID or identity.get('candidate_id') != D6G_ID:
        raise RuntimeError('candidate identity is inconsistent')
    if identity.get('framework_version') != FRAMEWORK_VERSION or identity.get('nicegui_version') != NICEGUI_VERSION:
        raise RuntimeError('runtime identity is inconsistent')
    wheels = sorted((root / 'wheel').glob('nicegui_base-*.whl'))
    if len(wheels) != 1 or wheels[0].name != identity.get('wheel_filename') or sha256(wheels[0]) != identity.get('wheel_sha256'):
        raise RuntimeError('wheel identity/hash failed')
    with zipfile.ZipFile(wheels[0]) as archive:
        metadata_name = next((name for name in archive.namelist() if name.endswith('.dist-info/METADATA')), None)
        record_name = next((name for name in archive.namelist() if name.endswith('.dist-info/RECORD')), None)
        if not metadata_name or not record_name:
            raise RuntimeError('wheel lacks RECORD or METADATA')
        if f'Version: {FRAMEWORK_VERSION}' not in archive.read(metadata_name).decode('utf-8'):
            raise RuntimeError('framework wheel version mismatch')
    return {'status': 'PASS', 'candidate_id': D6G_ID, 'wheel': wheels[0].name, 'wheel_sha256': sha256(wheels[0])}


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


def browser_smoke(base_url: str, evidence: Path) -> dict[str, object]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError('Playwright is required; set NGB_D6G_BROWSER_PYTHON') from exc
    events: list[str] = []
    routes = ('/', '/design', '/catalog', '/components', '/data', '/analytics', '/patterns', '/recipes', '/applications', '/ai-guide', '/quality')
    page = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='light')
            page = context.new_page()
            page.on('pageerror', lambda exc: events.append('pageerror: ' + str(exc)))
            page.on('console', lambda message: events.append(f'console:{message.type}: {message.text}') if message.type == 'error' else None)
            for route in routes:
                response = page.goto(base_url.rstrip('/') + route, wait_until='domcontentloaded', timeout=45000)
                page.wait_for_timeout(150)
                if response is None or response.status != 200:
                    raise RuntimeError(f'{route} returned {response.status if response else None}')
            page.goto(base_url.rstrip('/') + '/', wait_until='domcontentloaded', timeout=45000)
            nav = page.locator('nav').first.inner_text()
            if 'Start Here' not in nav or 'Design System' not in nav or 'Build' in nav:
                raise RuntimeError('golden Reference Explorer navigation contract failed')
            page.goto(base_url.rstrip('/') + '/design', wait_until='domcontentloaded', timeout=45000)
            if page.locator('[data-design-token-family]').count() < 12:
                raise RuntimeError('Design System reference is incomplete')
            page.goto(base_url.rstrip('/') + '/catalog', wait_until='domcontentloaded', timeout=45000)
            search = page.locator('input[placeholder*="Name, tag"]').first
            search.fill('monitor equipment health')
            page.wait_for_timeout(250)
            if 'FdcToolHealth' not in page.locator('body').inner_text():
                raise RuntimeError('catalog intent search did not return tool health')
            if events:
                raise RuntimeError('; '.join(events))
            context.close(); browser.close()
    except Exception:
        if page is not None:
            try:
                page.screenshot(path=str(evidence / 'failure_browser.png'), full_page=False)
            except Exception:
                pass
        raise
    (evidence / 'browser.log').write_text('\n'.join(events) + '\n', encoding='utf-8')
    return {'status': 'PASS', 'routes': len(routes), 'events': events, 'viewport': 'desktop-light'}


def generated_smoke(cli: Path, python: Path, work: Path, evidence: Path) -> dict[str, object]:
    pattern = work / 'pattern_app'
    recipe = work / 'recipe_app'
    run_logged([cli, 'create-pattern', pattern, '--name', 'D6G Pattern App', '--pattern', 'monitoring'], cwd=work, log=evidence / 'scaffold_pattern.log', timeout=180)
    run_logged([cli, 'create-recipe', recipe, '--name', 'D6G Recipe App', '--recipe', 'spc-monitor'], cwd=work, log=evidence / 'scaffold_recipe.log', timeout=180)
    results: list[dict[str, object]] = []
    for name, root in (('pattern', pattern), ('recipe', recipe)):
        # Production installs intentionally do not include pytest. The
        # package-level acceptance check therefore uses the installed agent
        # contract preflight here; the authoritative full gate is run in the
        # D6G evidence suite with the repository test environment.
        run_logged([cli, 'agent-check', root, '--format', 'json'], cwd=work, log=evidence / f'{name}_agent_check.log', timeout=300)
        run_logged([python, '-I', '-c', "import nicegui_base; from pathlib import Path; p=Path(nicegui_base.__file__).resolve(); assert 'site-packages' in p.parts; print(p)"], cwd=root, log=evidence / f'{name}_installed_import.log', timeout=120)
        port = free_port()
        log = evidence / f'{name}_generated_server.log'
        with log.open('w', encoding='utf-8') as stream:
            process = subprocess.Popen([str(python), str(root / 'app.py')], cwd=root, env=clean_env({'NICEGUI_BASE_PORT': str(port)}), stdout=stream, stderr=subprocess.STDOUT, text=True)
        try:
            wait_http(f'http://127.0.0.1:{port}/readyz')
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=5) as response:
                health = response.read().decode()
            if response.status != 200 or 'healthy' not in health:
                raise RuntimeError(f'{name} generated health failed: {health}')
        finally:
            returncode = terminate(process)
        server_text = log.read_text(encoding='utf-8', errors='replace')
        if returncode not in (0, -signal.SIGTERM) or any(marker in server_text for marker in ERROR_MARKERS):
            raise RuntimeError(f'{name} generated startup/shutdown failed')
        results.append({'name': name, 'healthz': health, 'returncode': returncode, 'installed_framework': FRAMEWORK_VERSION})
    return {'status': 'PASS', 'applications': results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence-dir', type=Path, default=Path('.ngb-d6g-evidence'))
    parser.add_argument('--evidence-zip', type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent
    evidence = args.evidence_dir.resolve()
    if evidence.exists():
        if not (evidence / '.ngb-d6g-evidence-owned').is_file():
            raise SystemExit(f'refusing to replace unowned evidence directory: {evidence}')
        for path in evidence.iterdir():
            if path.is_file(): path.unlink()
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / '.ngb-d6g-evidence-owned').write_text(D6G_ID + '\n', encoding='utf-8')
    evidence_zip = (args.evidence_zip or evidence.with_suffix('.zip')).resolve()
    result: dict[str, object] = {'candidate_id': D6G_ID, 'status': 'FAIL', 'checks': {}, 'evidence_dir': str(evidence), 'evidence_zip': str(evidence_zip)}
    work = Path(tempfile.mkdtemp(prefix='ngb-d6g-verify-'))
    neutral = work / 'neutral'; neutral.mkdir()
    python = root / '.venv' / 'bin' / 'python'
    process = None
    server_log = evidence / 'workbench.log'
    try:
        if not python.is_file(): raise RuntimeError('run ./install.sh first')
        result['checks']['identity'] = verify_identity(root)
        result['checks']['manifest'] = verify_manifest(root)
        result['checks']['runtime_import'] = verify_import(python, neutral, evidence / 'runtime_import.log')
        run_logged([python, '-m', 'pip', 'check'], cwd=neutral, log=evidence / 'pip_check.log', timeout=120)
        result['checks']['pip_check'] = 'PASS'
        run_logged([root / '.venv' / 'bin' / 'nicegui-base', 'runtime-contract', '--format', 'json'], cwd=neutral, log=evidence / 'runtime_contract.log', timeout=300)
        result['checks']['runtime_contract'] = 'PASS'
        port = free_port()
        with server_log.open('w', encoding='utf-8') as stream:
            process = subprocess.Popen([str(python), str(root / 'launch.py'), '--port', str(port)], cwd=neutral, env=clean_env(), stdout=stream, stderr=subprocess.STDOUT, text=True)
        wait_http(f'http://127.0.0.1:{port}/readyz')
        health = urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=5).read().decode()
        ready = urllib.request.urlopen(f'http://127.0.0.1:{port}/readyz', timeout=5).read().decode()
        if 'healthy' not in health or '"ready":true' not in ready:
            raise RuntimeError(f'Workbench readiness failed: health={health}; ready={ready}')
        result['checks']['workbench'] = {'healthz': health, 'readyz': ready}
        result['checks']['browser'] = browser_smoke(f'http://127.0.0.1:{port}', evidence)
        if terminate(process) not in (0, -signal.SIGTERM):
            raise RuntimeError('Workbench graceful shutdown failed')
        process = None
        result['checks']['generated_apps'] = generated_smoke(root / '.venv' / 'bin' / 'nicegui-base', python, work, evidence)
        result['checks']['graceful_shutdown'] = 'PASS'
        result['status'] = 'PASS'
    except Exception as exc:
        result['failure'] = f'{type(exc).__name__}: {exc}'
    finally:
        if process is not None:
            result['checks']['graceful_shutdown'] = 'PASS' if terminate(process) in (0, -signal.SIGTERM) else 'FAIL'
        server_text = server_log.read_text(encoding='utf-8', errors='replace') if server_log.is_file() else ''
        result['error_markers'] = [marker for marker in ERROR_MARKERS if marker in server_text]
        if result['status'] == 'PASS' and result['error_markers']:
            result['status'] = 'FAIL'; result['failure'] = 'server error markers found'
        (evidence / 'D6G_RESULT.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        with zipfile.ZipFile(evidence_zip, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for member in [evidence / 'D6G_RESULT.json', *sorted(evidence.glob('*.log')), *sorted(evidence.glob('failure*.png'))]:
                if member.is_file(): archive.write(member, member.name)
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
