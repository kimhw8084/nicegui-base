#!/usr/bin/env python3
"""Candidate-bound browser evidence for Data Lab generated-code copy semantics."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.verify_data_table_lab import (  # noqa: E402
    CANDIDATE,
    LABS,
    _inspect_code_copy_accessibility,
    _set_actual_theme,
    _switch_lab,
    _wait_for_settled_ready,
)


PROFILES = {
    'desktop-1440x900': (1440, 900),
    'mobile-390x844': (390, 844),
    'mobile-narrow-360x800': (360, 800),
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _wait_ready(process: subprocess.Popen[str], base_url: str, log_path: Path) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'Explorer exited before readiness; see {log_path}')
        try:
            with urlopen(base_url + '/healthz', timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(.2)
    raise TimeoutError(f'Explorer did not become ready at {base_url}; see {log_path}')


def _code_text(page: Page) -> str:
    for selector in ('.cui-data-lab-reference pre', '.cui-data-lab-reference code'):
        locator = page.locator(selector)
        if locator.count():
            return locator.first.inner_text()
    raise AssertionError('generated code text missing from open API disclosure')


def _clipboard_text(page: Page) -> str | None:
    return page.evaluate("() => navigator.clipboard ? navigator.clipboard.readText() : null")


def _exercise_copy(page: Page, *, profile: str, lab: str, records: list[dict[str, object]]) -> None:
    button = page.locator('.cui-data-lab-reference .nicegui-code-copy').first
    code = _code_text(page).strip()
    button.scroll_into_view_if_needed()
    button.focus()
    focused = page.evaluate('(selector) => document.activeElement?.matches(selector) === true', '.cui-data-lab-reference .nicegui-code-copy')
    keyboard_clipboard = None
    if focused:
        button.press('Enter')
        page.wait_for_timeout(180)
        keyboard_clipboard = _clipboard_text(page)
    page.evaluate(
        "(selector) => document.querySelector(selector)?.click()",
        '.cui-data-lab-reference .nicegui-code-copy',
    )
    page.wait_for_timeout(180)
    click_clipboard = _clipboard_text(page)
    behavior = {
        'profile': profile,
        'lab': lab,
        'keyboard_focus': focused,
        'keyboard_activatable': keyboard_clipboard == code,
        'click_activatable': click_clipboard == code,
        'copied_code_sha256': hashlib.sha256(code.encode()).hexdigest(),
    }
    records.append({'copy_behavior': behavior})
    if not focused or keyboard_clipboard != code or click_clipboard != code:
        raise AssertionError(f'copy behavior failed for {profile}/{lab}: {behavior}')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    port = args.port or _free_port()
    base_url = f'http://127.0.0.1:{port}'
    log_path = output / 'server.log'
    with log_path.open('w', encoding='utf-8') as server_log:
        env = dict(os.environ)
        env['PYTHONPATH'] = str(ROOT / 'source')
        process = subprocess.Popen(
            [sys.executable, str(ROOT / 'run_nicegui_base.py'), '--host', '127.0.0.1', '--port', str(port), '--no-show'],
            cwd=ROOT, env=env, stdout=server_log, stderr=subprocess.STDOUT, text=True,
        )
    results: list[dict[str, object]] = []
    try:
        _wait_ready(process, base_url, log_path)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for profile, (width, height) in PROFILES.items():
                context = browser.new_context(
                    viewport={'width': width, 'height': height},
                    permissions=['clipboard-read', 'clipboard-write'],
                )
                context.set_default_timeout(10000)
                for lab in LABS:
                    page = context.new_page()
                    console_errors: list[str] = []
                    page_errors: list[str] = []
                    failed_requests: list[str] = []
                    page.on('console', lambda message: console_errors.append(message.text) if message.type == 'error' else None)
                    page.on('pageerror', lambda error: page_errors.append(str(error)))
                    page.on('requestfailed', lambda request: failed_requests.append(f'{request.method} {request.url}: {request.failure}'))
                    response = page.goto(base_url + '/workbench/data', wait_until='domcontentloaded', timeout=45000)
                    if response is None or response.status != 200:
                        raise AssertionError(f'route status {response.status if response else None}')
                    page.get_by_role('radio', name='Grid', exact=True).wait_for(state='visible', timeout=10000)
                    _wait_for_settled_ready(page)
                    _set_actual_theme(page, 'light')
                    if lab != 'Grid':
                        _switch_lab(page, lab, wait=500)
                    _wait_for_settled_ready(page)
                    records = _inspect_code_copy_accessibility(page, viewport=profile, lab=lab)
                    if any(not bool(record['pass']) for record in records):
                        raise AssertionError(f'accessibility contract failed for {profile}/{lab}: {records}')
                    _exercise_copy(page, profile=profile, lab=lab, records=records)
                    overflow = page.evaluate(
                        "() => ({document: document.documentElement.scrollWidth, body: document.body.scrollWidth, viewport: document.documentElement.clientWidth})"
                    )
                    if max(overflow['document'], overflow['body']) > overflow['viewport'] + 1:
                        raise AssertionError(f'page-level horizontal overflow for {profile}/{lab}: {overflow}')
                    result = {
                        'profile': profile,
                        'viewport': {'width': width, 'height': height},
                        'lab': lab,
                        'route_status': response.status,
                        'accessibility': records,
                        'overflow': overflow,
                        'console_errors': console_errors,
                        'page_errors': page_errors,
                        'failed_requests': failed_requests,
                        'pass': not console_errors and not page_errors and not failed_requests,
                    }
                    results.append(result)
                    if not result['pass']:
                        raise AssertionError(f'browser errors for {profile}/{lab}: {result}')
                    if profile in {'desktop-1440x900', 'mobile-390x844'}:
                        screenshot = output / 'screenshots' / f'{profile}__{lab.lower()}.png'
                        screenshot.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(screenshot), full_page=False)
                    page.close()
                context.close()
            browser.close()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    payload = {
        'candidate': CANDIDATE,
        'route': '/workbench/data',
        'profiles': PROFILES,
        'labs': LABS,
        'settled_readiness': {'document_ready_state': 'complete', 'document_fonts_status': 'loaded'},
        'total': len(results),
        'passed': sum(bool(item['pass']) for item in results),
        'results': results,
    }
    result_path = output / 'DATA_LAB_CODE_COPY_A11Y_RESULT.json'
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'candidate': CANDIDATE, 'total': payload['total'], 'passed': payload['passed'], 'output': str(result_path)}))
    return 0 if payload['total'] == len(PROFILES) * len(LABS) and payload['passed'] == payload['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
