from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import socket
import ssl
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from nicegui_base.security.redaction import redact
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

from .engine import run_certification
from .live_models import (
    AuthProbeConfig,
    BrowserProbeConfig,
    GoldCertificationReport,
    LiveCertificationConfig,
    LiveGateResult,
    LiveGateStatus,
    LoadProbeConfig,
)


def _result(key: str, label: str, status: LiveGateStatus, detail: str, category: str,
            *, required: bool = True, duration_ms: float | None = None,
            evidence: dict[str, object] | None = None) -> LiveGateResult:
    return LiveGateResult(key, label, status, detail, category, required, duration_ms, evidence or {})


def _join(base: str, path: str) -> str:
    if path.startswith('http://') or path.startswith('https://'):
        return path
    parsed = urlsplit(base)
    base_path = parsed.path.rstrip('/')
    path = '/' + path.lstrip('/')
    return f'{parsed.scheme}://{parsed.netloc}{base_path}{path}'


def _request(url: str, headers: dict[str, str], timeout: float) -> tuple[int, dict[str, str], bytes, str, float]:
    req = Request(url, headers=headers, method='GET')
    started = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout) as response:
            body = response.read(1_000_000)
            elapsed = (time.perf_counter() - started) * 1000
            return response.status, {k.lower(): v for k, v in response.headers.items()}, body, response.geturl(), elapsed
    except HTTPError as exc:
        body = exc.read(1_000_000)
        elapsed = (time.perf_counter() - started) * 1000
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, body, exc.geturl(), elapsed




class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request_no_redirect(url: str, headers: dict[str, str], timeout: float) -> tuple[int, dict[str, str], bytes, str, float]:
    req = Request(url, headers=headers, method='GET')
    started = time.perf_counter()
    opener = build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as response:
            body = response.read(1_000_000)
            elapsed = (time.perf_counter() - started) * 1000
            return response.status, {k.lower(): v for k, v in response.headers.items()}, body, response.geturl(), elapsed
    except HTTPError as exc:
        body = exc.read(1_000_000)
        elapsed = (time.perf_counter() - started) * 1000
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, body, exc.geturl(), elapsed


def probe_http(config: LiveCertificationConfig) -> list[LiveGateResult]:
    checks: list[LiveGateResult] = []
    headers = dict(config.headers)
    try:
        status, response_headers, body, final_url, elapsed = _request(config.target_url, headers, config.timeout_seconds)
        if status == config.expected_status:
            checks.append(_result('live-http', 'Application HTTP', LiveGateStatus.PASS,
                                  f'{status} from {final_url}', 'live-http', duration_ms=elapsed,
                                  evidence={'status': status, 'final_url': final_url, 'bytes_sampled': len(body)}))
        else:
            checks.append(_result('live-http', 'Application HTTP', LiveGateStatus.FAIL,
                                  f'Expected HTTP {config.expected_status}, received {status}', 'live-http', duration_ms=elapsed,
                                  evidence={'status': status, 'final_url': final_url}))

        target = urlsplit(config.target_url)
        final = urlsplit(final_url)
        target_prefix = target.path.rstrip('/')
        prefix_ok = not target_prefix or final.path == target_prefix or final.path.startswith(target_prefix + '/')
        checks.append(_result('base-path', 'Reverse-proxy/base path',
                              LiveGateStatus.PASS if prefix_ok else LiveGateStatus.FAIL,
                              f'Final path {final.path!r} remains under configured prefix {target_prefix or "/"!r}' if prefix_ok
                              else f'Final URL escaped configured prefix {target_prefix!r}: {final_url}',
                              'proxy'))

        if config.require_security_headers:
            missing = [h for h in config.expected_security_headers if h.lower() not in response_headers]
            checks.append(_result('security-headers', 'Security response headers',
                                  LiveGateStatus.PASS if not missing else LiveGateStatus.FAIL,
                                  'Required headers present' if not missing else f'Missing: {", ".join(missing)}',
                                  'security', evidence={'present': sorted(h for h in config.expected_security_headers if h.lower() in response_headers), 'missing': missing}))
    except (URLError, OSError, TimeoutError) as exc:
        checks.append(_result('live-http', 'Application HTTP', LiveGateStatus.FAIL, str(exc), 'live-http'))
        checks.append(_result('base-path', 'Reverse-proxy/base path', LiveGateStatus.SKIP, 'HTTP probe failed', 'proxy'))
        if config.require_security_headers:
            checks.append(_result('security-headers', 'Security response headers', LiveGateStatus.SKIP, 'HTTP probe failed', 'security'))
    return checks


def probe_health(config: LiveCertificationConfig) -> list[LiveGateResult]:
    results: list[LiveGateResult] = []
    for key, label, path in (
        ('health', 'Liveness endpoint', config.health_path),
        ('readiness', 'Readiness endpoint', config.readiness_path),
    ):
        url = _join(config.target_url, path)
        try:
            status, _, body, _, elapsed = _request(url, dict(config.headers), config.timeout_seconds)
            ok = 200 <= status < 300
            detail = f'HTTP {status}'
            try:
                payload = json.loads(body.decode('utf-8'))
                if isinstance(payload, dict):
                    state = payload.get('status') or payload.get('state')
                    if state: detail += f'; state={state}'
            except Exception:
                pass
            results.append(_result(key, label, LiveGateStatus.PASS if ok else LiveGateStatus.FAIL,
                                   detail, 'runtime', duration_ms=elapsed, evidence={'url': url, 'status': status}))
        except (URLError, OSError, TimeoutError) as exc:
            results.append(_result(key, label, LiveGateStatus.FAIL, str(exc), 'runtime', evidence={'url': url}))
    return results


def probe_auth(config: LiveCertificationConfig) -> list[LiveGateResult]:
    auth = config.auth
    if auth is None:
        return [_result('auth', 'Authentication/RBAC probe', LiveGateStatus.SKIP, 'Auth probe not configured', 'security', required=False)]
    url = _join(config.target_url, auth.path)
    results: list[LiveGateResult] = []
    try:
        status, response_headers, _, final_url, elapsed = _request_no_redirect(url, {}, config.timeout_seconds)
        ok = status in auth.unauthenticated_statuses
        results.append(_result('auth-unauthenticated', 'Fail-closed unauthenticated access',
                               LiveGateStatus.PASS if ok else LiveGateStatus.FAIL,
                               f'HTTP {status}; expected one of {auth.unauthenticated_statuses}', 'security', required=auth.required,
                               duration_ms=elapsed, evidence={'url': url, 'status': status, 'location_present': 'location' in response_headers}))
    except Exception as exc:
        results.append(_result('auth-unauthenticated', 'Fail-closed unauthenticated access', LiveGateStatus.FAIL, str(exc), 'security', required=auth.required))
    if config.headers:
        try:
            status, _, _, final_url, elapsed = _request(url, dict(config.headers), config.timeout_seconds)
            ok = status == auth.authenticated_status
            results.append(_result('auth-authenticated', 'Authenticated application access',
                                   LiveGateStatus.PASS if ok else LiveGateStatus.FAIL,
                                   f'HTTP {status}; expected {auth.authenticated_status}', 'security', required=auth.required,
                                   duration_ms=elapsed, evidence={'url': url, 'status': status, 'final_url': final_url}))
        except Exception as exc:
            results.append(_result('auth-authenticated', 'Authenticated application access', LiveGateStatus.FAIL, str(exc), 'security', required=auth.required))
    else:
        results.append(_result('auth-authenticated', 'Authenticated application access', LiveGateStatus.SKIP,
                               'No request headers supplied; use browser storage state for SSO or --header for header/token authentication',
                               'security', required=False))
    return results


def probe_websocket(config: LiveCertificationConfig) -> LiveGateResult:
    url = _join(config.target_url, config.websocket_path)
    parsed = urlsplit(url)
    secure = parsed.scheme == 'https'
    port = parsed.port or (443 if secure else 80)
    path = parsed.path + (f'?{parsed.query}' if parsed.query else '')
    key = base64.b64encode(os.urandom(16)).decode('ascii')
    expected_accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode('ascii')).digest()).decode('ascii')
    request_headers = {
        'Host': parsed.netloc,
        'Upgrade': 'websocket',
        'Connection': 'Upgrade',
        'Sec-WebSocket-Key': key,
        'Sec-WebSocket-Version': '13',
        'Origin': f'{parsed.scheme}://{parsed.netloc}',
        **dict(config.headers),
    }
    wire = f'GET {path} HTTP/1.1\r\n' + ''.join(f'{k}: {v}\r\n' for k, v in request_headers.items()) + '\r\n'
    started = time.perf_counter()
    try:
        raw = socket.create_connection((parsed.hostname or '', port), timeout=config.timeout_seconds)
        sock = ssl.create_default_context().wrap_socket(raw, server_hostname=parsed.hostname) if secure else raw
        with sock:
            sock.settimeout(config.timeout_seconds)
            sock.sendall(wire.encode('ascii'))
            response = b''
            while b'\r\n\r\n' not in response and len(response) < 65536:
                chunk = sock.recv(4096)
                if not chunk: break
                response += chunk
        elapsed = (time.perf_counter() - started) * 1000
        head = response.decode('latin1', errors='replace').split('\r\n\r\n', 1)[0]
        lines = head.split('\r\n')
        status_line = lines[0] if lines else ''
        response_headers: dict[str, str] = {}
        for line in lines[1:]:
            if ':' in line:
                k, v = line.split(':', 1); response_headers[k.strip().lower()] = v.strip()
        accepted = status_line.startswith('HTTP/1.1 101') or status_line.startswith('HTTP/1.0 101')
        accept_ok = response_headers.get('sec-websocket-accept') == expected_accept
        ok = accepted and accept_ok
        return _result('websocket', 'NiceGUI WebSocket upgrade', LiveGateStatus.PASS if ok else LiveGateStatus.FAIL,
                       f'{status_line}; upgrade handshake verified' if ok else f'{status_line}; websocket accept verification failed',
                       'proxy', duration_ms=elapsed,
                       evidence={'url': url, 'status_line': status_line, 'upgrade': response_headers.get('upgrade')})
    except (OSError, ssl.SSLError, TimeoutError) as exc:
        return _result('websocket', 'NiceGUI WebSocket upgrade', LiveGateStatus.FAIL, str(exc), 'proxy', evidence={'url': url})


def _percentile(values: list[float], q: float) -> float:
    if not values: return 0.0
    values = sorted(values)
    idx = min(len(values) - 1, max(0, int(round((len(values) - 1) * q))))
    return values[idx]


def probe_load(load: LoadProbeConfig, headers: dict[str, str]) -> LiveGateResult:
    def one(_: int) -> tuple[bool, float, int | None]:
        try:
            status, _, _, _, elapsed = _request(load.url, headers, load.timeout_seconds)
            return 200 <= status < 400, elapsed, status
        except Exception:
            return False, load.timeout_seconds * 1000, None
    started = time.perf_counter()
    samples: list[tuple[bool, float, int | None]] = []
    with ThreadPoolExecutor(max_workers=load.concurrency) as pool:
        futures = [pool.submit(one, i) for i in range(load.requests)]
        for future in as_completed(futures): samples.append(future.result())
    elapsed_total = (time.perf_counter() - started) * 1000
    durations = [x[1] for x in samples]
    successes = sum(x[0] for x in samples)
    success_rate = successes / len(samples) if samples else 0.0
    p50 = statistics.median(durations) if durations else 0.0
    p95 = _percentile(durations, .95)
    max_ms = max(durations, default=0.0)
    ok = success_rate >= load.min_success_rate and (load.max_p95_ms is None or p95 <= load.max_p95_ms)
    detail = f'{successes}/{len(samples)} success ({success_rate:.1%}); p50={p50:.1f} ms, p95={p95:.1f} ms, max={max_ms:.1f} ms'
    return _result('load', 'HTTP concurrency/load probe', LiveGateStatus.PASS if ok else LiveGateStatus.FAIL,
                   detail, 'performance', duration_ms=elapsed_total,
                   evidence={'requests': len(samples), 'concurrency': load.concurrency, 'success_rate': success_rate, 'p50_ms': p50, 'p95_ms': p95, 'max_ms': max_ms, 'threshold_p95_ms': load.max_p95_ms})


def probe_browser(config: BrowserProbeConfig, target_url: str) -> list[LiveGateResult]:
    if not config.enabled:
        return [_result('browser', 'Browser automation', LiveGateStatus.SKIP, 'Browser probe disabled', 'browser', required=config.required)]
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception:
        return [_result('browser', 'Browser automation', LiveGateStatus.FAIL if config.required else LiveGateStatus.SKIP,
                        'Playwright is not installed in this environment', 'browser', required=config.required)]

    results: list[LiveGateResult] = []
    screenshot_dir = config.screenshot_dir
    if screenshot_dir: screenshot_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        for browser_name in config.browsers:
            if browser_name in {'chrome', 'msedge'}:
                browser_type = p.chromium
                launch_kwargs = {'headless': True, 'channel': browser_name}
            else:
                browser_type = getattr(p, browser_name, None)
                launch_kwargs = {'headless': True}
            if browser_type is None:
                results.append(_result(f'browser-{browser_name}', f'Browser: {browser_name}', LiveGateStatus.FAIL,
                                       'Unsupported Playwright browser name', 'browser', required=config.required)); continue
            try:
                browser = browser_type.launch(**launch_kwargs)
            except Exception as exc:
                results.append(_result(f'browser-{browser_name}', f'Browser: {browser_name}',
                                       LiveGateStatus.FAIL if config.required else LiveGateStatus.SKIP,
                                       f'Browser launch failed: {exc}', 'browser', required=config.required)); continue
            try:
                for viewport_name, width, height in config.viewports:
                    context_kwargs = {'viewport': {'width': width, 'height': height}}
                    if config.storage_state is not None:
                        context_kwargs['storage_state'] = str(config.storage_state)
                    context = browser.new_context(**context_kwargs)
                    page = context.new_page()
                    console_errors: list[str] = []
                    page_errors: list[str] = []
                    websockets: list[str] = []
                    page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
                    page.on('pageerror', lambda exc: page_errors.append(str(exc)))
                    page.on('websocket', lambda ws: websockets.append(ws.url))
                    started = time.perf_counter()
                    try:
                        response = page.goto(target_url, wait_until='networkidle', timeout=config.timeout_ms)
                        page.wait_for_timeout(500)
                        elapsed = (time.perf_counter() - started) * 1000
                        audit = page.evaluate("""() => {
                          const interactive = [...document.querySelectorAll('button,a[href],input,select,textarea,[role=button],[tabindex]')];
                          const missingNames = interactive.filter(el => {
                            if (el.getAttribute('aria-hidden') === 'true' || el.disabled) return false;
                            const name = (el.getAttribute('aria-label') || '').trim();
                            const labelled = el.getAttribute('aria-labelledby');
                            const text = (el.innerText || el.value || el.getAttribute('title') || '').trim();
                            return !name && !labelled && !text;
                          }).length;
                          const ids = [...document.querySelectorAll('[id]')].map(el => el.id);
                          const duplicateIds = ids.length - new Set(ids).size;
                          const imagesMissingAlt = [...document.querySelectorAll('img')].filter(img => !img.hasAttribute('alt')).length;
                          const leakRules = [
                            ['q-notification', '.q-notification', el => false],
                            ['q-checkbox', '.q-checkbox', el => el.classList.contains('cui-choice') || !!el.closest('.cui-data-table,.cui-tree')],
                            ['q-radio', '.q-radio', el => el.classList.contains('cui-choice')],
                            ['q-toggle', '.q-toggle', el => false],
                            ['q-slider', '.q-slider', el => el.classList.contains('cui-slider')],
                            ['q-tabs', '.q-tabs', el => el.classList.contains('cui-tabs-region')],
                            ['q-stepper', '.q-stepper', el => el.classList.contains('cui-stepper')],
                            ['q-tree', '.q-tree', el => el.classList.contains('cui-tree')],
                            ['q-uploader', '.q-uploader', el => el.classList.contains('cui-upload')],
                            ['q-field', '.q-field', el => el.classList.contains('cui-field-control') || !!el.closest('.cui-data-table,.cui-command-palette')],
                            ['ag-grid', '.ag-root-wrapper', el => !!el.closest('.cui-data-table')],
                          ];
                          const stockLeaks = [];
                          for (const [kind, selector, approved] of leakRules) {
                            for (const el of document.querySelectorAll(selector)) {
                              if (!approved(el)) stockLeaks.push({kind, cls: (el.className || '').toString().slice(0,160)});
                            }
                          }
                          const visibleMaterialIcons = [...document.querySelectorAll('.material-icons,.material-symbols-outlined,.q-icon')].filter(el => {
                            const style=getComputedStyle(el);
                            if(style.display==='none' || style.visibility==='hidden' || Number(style.opacity)===0) return false;
                            return !el.closest('.cui-field-control,.cui-collapsible,.cui-nav-expansion,.cui-stepper,.cui-tree,.cui-upload,.cui-data-table');
                          });
                          return {
                            horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
                            mainLandmark: !!document.querySelector('main,[role=main]'),
                            missingAccessibleNames: missingNames,
                            duplicateIds, imagesMissingAlt, interactiveCount: interactive.length,
                            stockVisualLeakCount: stockLeaks.length,
                            stockVisualLeakSamples: stockLeaks.slice(0,10),
                            unapprovedMaterialIconCount: visibleMaterialIcons.length,
                          };
                        }""")
                        page.keyboard.press('Tab')
                        keyboard_focus = page.evaluate("document.activeElement && document.activeElement !== document.body")
                        ok = bool(response and response.ok) and not console_errors and not page_errors and not audit['horizontalOverflow'] and audit['mainLandmark'] and audit['missingAccessibleNames'] == 0 and audit['duplicateIds'] == 0 and audit['imagesMissingAlt'] == 0 and audit['stockVisualLeakCount'] == 0 and audit['unapprovedMaterialIconCount'] == 0 and bool(keyboard_focus)
                        detail = f'HTTP {response.status if response else "?"}; console={len(console_errors)}, page_errors={len(page_errors)}, websocket={len(websockets)}, overflow={audit["horizontalOverflow"]}, a11y_names={audit["missingAccessibleNames"]}, duplicate_ids={audit["duplicateIds"]}, img_alt={audit["imagesMissingAlt"]}, stock_leaks={audit["stockVisualLeakCount"]}, material_icons={audit["unapprovedMaterialIconCount"]}, keyboard_focus={bool(keyboard_focus)}'
                        if screenshot_dir:
                            page.screenshot(path=str(screenshot_dir / f'{browser_name}_{viewport_name}.png'), full_page=True)
                        results.append(_result(f'browser-{browser_name}-{viewport_name}', f'{browser_name} {viewport_name}',
                                               LiveGateStatus.PASS if ok else LiveGateStatus.FAIL, detail, 'browser', required=config.required,
                                               duration_ms=elapsed, evidence={'width': width, 'height': height, 'console_errors': console_errors[:10], 'page_errors': page_errors[:10], 'websocket_count': len(websockets), 'horizontal_overflow': audit['horizontalOverflow'], 'main_landmark': audit['mainLandmark'], 'missing_accessible_names': audit['missingAccessibleNames'], 'duplicate_ids': audit['duplicateIds'], 'images_missing_alt': audit['imagesMissingAlt'], 'interactive_count': audit['interactiveCount'], 'stock_visual_leak_count': audit['stockVisualLeakCount'], 'stock_visual_leak_samples': audit['stockVisualLeakSamples'], 'unapproved_material_icon_count': audit['unapprovedMaterialIconCount'], 'keyboard_focus': bool(keyboard_focus)}))
                    except Exception as exc:
                        results.append(_result(f'browser-{browser_name}-{viewport_name}', f'{browser_name} {viewport_name}', LiveGateStatus.FAIL,
                                               str(exc), 'browser', required=config.required))
                    finally:
                        context.close()
            finally:
                browser.close()
    return results


def run_gold_certification(config: LiveCertificationConfig, *, root: str | Path | None = None) -> GoldCertificationReport:
    checks: list[LiveGateResult] = []
    if config.require_offline_certification:
        offline = run_certification(root=root, require_nicegui=config.require_nicegui_runtime)
        status = LiveGateStatus.PASS if offline.passed else LiveGateStatus.FAIL
        checks.append(_result('offline', 'Offline framework certification', status,
                              f'{offline.summary}', 'offline', evidence={'summary': offline.summary}))
    checks.extend(probe_http(config))
    checks.extend(probe_health(config))
    checks.extend(probe_auth(config))
    checks.append(probe_websocket(config))
    checks.extend(probe_browser(config.browser, config.target_url))
    if config.load:
        checks.append(probe_load(config.load, dict(config.headers)))
    else:
        checks.append(_result('load', 'HTTP concurrency/load probe', LiveGateStatus.SKIP,
                              'Load probe disabled', 'performance', required=False))
    metadata = {
        'python': platform.python_version(),
        'platform': platform.platform(),
        'nicegui_required': NICEGUI_VERSION,
        'headers_supplied': sorted(config.headers),
    }
    return GoldCertificationReport(FRAMEWORK_VERSION, config.target_url, tuple(checks), metadata)


def write_evidence(report: GoldCertificationReport, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = redact(report.to_dict())
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + '.sha256').write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    return output
