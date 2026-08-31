from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import socket
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from nicegui_base.version import NICEGUI_VERSION


@dataclass(frozen=True, slots=True)
class LiveCheck:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {'name': self.name, 'passed': self.passed, 'detail': self.detail}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _wait_http(url: str, process: subprocess.Popen[str], timeout: float = 30.0) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout
    last = 'server did not respond'
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ''
            return False, f'application exited with {process.returncode}: {output[-1500:]}'
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                return (200 <= response.status < 500), f'HTTP {response.status}'
        except Exception as exc:
            last = str(exc)
            time.sleep(0.2)
    return False, last


def _browser_checks(page, *, mobile: bool) -> list[LiveCheck]:
    result = page.evaluate("""() => {
      const visible = el => { const r=el.getBoundingClientRect(), s=getComputedStyle(el); return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'; };
      const buttons=[...document.querySelectorAll('button,[role="button"]')].filter(visible);
      const named=buttons.filter(el => ((el.getAttribute('aria-label')||el.getAttribute('title')||el.textContent||'').trim().length>0));
      const ids=[...document.querySelectorAll('[id]')].map(el=>el.id).filter(Boolean); const duplicates=ids.filter((id,i)=>ids.indexOf(id)!==i);
      const utilities=[...document.querySelectorAll('.cui-sidebar-footer__action')].filter(visible);
      const utilityLabels=utilities.map(el=>(el.getAttribute('aria-label')||'').trim()).filter(Boolean);
      const root=document.documentElement;
      const overflow=Math.max(root.scrollWidth,document.body?document.body.scrollWidth:0)-innerWidth;
      return {bodyText:(document.body?.innerText||'').trim().length, buttonCount:buttons.length, namedButtons:named.length,
        duplicateIds:[...new Set(duplicates)], utilityLabels, overflow, domNodes:document.querySelectorAll('*').length};
    }""")
    checks = [
        LiveCheck('content-visible', result['bodyText'] > 0, f"body text chars={result['bodyText']}"),
        LiveCheck('horizontal-overflow', result['overflow'] <= 1.5, f"overflow={result['overflow']:.1f}px"),
        LiveCheck('button-accessible-names', result['namedButtons'] == result['buttonCount'], f"named={result['namedButtons']}/{result['buttonCount']}"),
        LiveCheck('duplicate-ids', not result['duplicateIds'], f"duplicates={result['duplicateIds'][:8]}"),
        LiveCheck('dom-budget', result['domNodes'] < 15000, f"nodes={result['domNodes']}"),
    ]
    if result['utilityLabels']:
        allowed = {'Support', 'Documentation'}
        checks.append(LiveCheck('sidebar-utilities', set(result['utilityLabels']).issubset(allowed) and len(result['utilityLabels']) <= 2, f"labels={result['utilityLabels']}"))
    if not mobile:
        centered = page.evaluate("""async () => {
          document.documentElement.dataset.sidebar='compact'; await new Promise(r=>setTimeout(r, 320));
          const visible=el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'};
          return [...document.querySelectorAll('.cui-sidebar-footer__action')].filter(visible).map(button=>{const icon=button.querySelector('.cui-svg-icon-host,svg');if(!icon)return {label:button.getAttribute('aria-label'),dx:999,dy:999};const b=button.getBoundingClientRect(),i=icon.getBoundingClientRect();return {label:button.getAttribute('aria-label'),dx:Math.abs((b.left+b.width/2)-(i.left+i.width/2)),dy:Math.abs((b.top+b.height/2)-(i.top+i.height/2))};});
        }""")
        if centered:
            worst = max(max(float(item['dx']), float(item['dy'])) for item in centered)
            checks.append(LiveCheck('compact-sidebar-icon-centering', worst <= 2.5, f'worst delta={worst:.2f}px'))
    return checks


def run_live_gate(root: str | Path='.') -> tuple[LiveCheck, ...]:
    root = Path(root).resolve()
    checks: list[LiveCheck] = []
    try:
        installed = importlib.metadata.version('nicegui')
    except importlib.metadata.PackageNotFoundError:
        return (LiveCheck('nicegui-runtime', False, f'nicegui=={NICEGUI_VERSION} is not installed'),)
    checks.append(LiveCheck('nicegui-runtime', installed == NICEGUI_VERSION, f'installed={installed}; required={NICEGUI_VERSION}'))
    if installed != NICEGUI_VERSION:
        return tuple(checks)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        checks.append(LiveCheck('playwright', False, 'playwright is not installed; install the NiceGUI Base browser-check dependencies'))
        return tuple(checks)

    port = _free_port()
    env = dict(os.environ)
    env['NICEGUI_BASE_HOST'] = '127.0.0.1'
    env['NICEGUI_BASE_PORT'] = str(port)
    env.setdefault('PYTHONUNBUFFERED', '1')
    process = subprocess.Popen([sys.executable, 'app.py'], cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        ready, detail = _wait_http(f'http://127.0.0.1:{port}/', process)
        checks.append(LiveCheck('application-server', ready, detail))
        if not ready:
            return tuple(checks)
        console_errors: list[str] = []
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch(headless=True)
                browser_detail = 'Playwright managed Chromium'
            except Exception as exc:
                system_chromium = next((shutil.which(name) for name in ('chromium', 'chromium-browser', 'google-chrome', 'microsoft-edge') if shutil.which(name)), None)
                if not system_chromium:
                    checks.append(LiveCheck('browser-runtime', False, f'Playwright browser launch failed and no system Chromium was found: {exc}'))
                    return tuple(checks)
                browser = pw.chromium.launch(headless=True, executable_path=system_chromium, args=['--no-sandbox'])
                browser_detail = f'system Chromium fallback: {system_chromium}'
            checks.append(LiveCheck('browser-runtime', True, browser_detail))
            try:
                for label, viewport, mobile in (
                    ('desktop', {'width': 1440, 'height': 900}, False),
                    ('mobile', {'width': 390, 'height': 844}, True),
                ):
                    page = browser.new_page(viewport=viewport)
                    page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
                    page.on('pageerror', lambda exc: console_errors.append(str(exc)))
                    started = time.monotonic()
                    response = page.goto(f'http://127.0.0.1:{port}/', wait_until='networkidle', timeout=30000)
                    elapsed = (time.monotonic() - started) * 1000
                    checks.append(LiveCheck(f'{label}-http', bool(response and response.ok), f'status={response.status if response else "none"}'))
                    checks.append(LiveCheck(f'{label}-load-budget', elapsed < 10000, f'{elapsed:.0f}ms'))
                    checks.extend(LiveCheck(f'{label}-{c.name}', c.passed, c.detail) for c in _browser_checks(page, mobile=mobile))
                    if mobile:
                        page.emulate_media(reduced_motion='reduce')
                        reduced = page.evaluate("""() => {const v=getComputedStyle(document.documentElement).getPropertyValue('--cui-duration-feedback').trim();return v;}""")
                        checks.append(LiveCheck('mobile-reduced-motion-token', reduced in {'1ms','0.001s','0s','0ms'}, f'value={reduced or "unset"}'))
                    page.close()
            finally:
                browser.close()
        checks.append(LiveCheck('browser-console', not console_errors, '; '.join(console_errors[:5]) if console_errors else 'no console/page errors'))
        return tuple(checks)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run the live UI/UX browser checks for a NiceGUI Base generated application.')
    parser.add_argument('--root', default='.')
    parser.add_argument('--format', choices=('text','json'), default='text')
    args = parser.parse_args(argv)
    checks = run_live_gate(args.root)
    passed = sum(check.passed for check in checks)
    payload = {'root': str(Path(args.root).resolve()), 'passed': passed == len(checks), 'passed_checks': passed, 'total_checks': len(checks), 'checks': [check.to_dict() for check in checks]}
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for check in checks:
            print(f'[{"PASS" if check.passed else "FAIL"}] {check.name}: {check.detail}')
        print(f'Application live gate: {passed}/{len(checks)} PASS')
    return 0 if payload['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
