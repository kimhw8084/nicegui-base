from __future__ import annotations

import argparse
import json
from pathlib import Path

from .live_checks import run_gold_certification, write_evidence
from .live_models import AuthProbeConfig, BrowserProbeConfig, LiveCertificationConfig, LoadProbeConfig


def _header(value: str) -> tuple[str, str]:
    if '=' not in value:
        raise argparse.ArgumentTypeError('headers must use NAME=VALUE')
    name, val = value.split('=', 1)
    if not name.strip(): raise argparse.ArgumentTypeError('header name cannot be empty')
    return name.strip(), val


def main() -> int:
    p = argparse.ArgumentParser(description='Run NiceGUI Base company-environment Gold promotion certification')
    p.add_argument('target_url', help='Deployed NiceGUI Base application URL, including reverse-proxy base path')
    p.add_argument('--root', default='.', help='Framework/application root used for offline certification')
    p.add_argument('--health-path', default='/healthz')
    p.add_argument('--readiness-path', default='/readyz')
    p.add_argument('--websocket-path', default='/_nicegui_ws/socket.io/?EIO=4&transport=websocket')
    p.add_argument('--header', action='append', default=[], type=_header, metavar='NAME=VALUE', help='Request header; values are never written to evidence')
    p.add_argument('--timeout', type=float, default=10.0)
    p.add_argument('--evidence', default='GOLD_CERTIFICATION_EVIDENCE.json')
    p.add_argument('--browser', action='store_true', help='Run optional Playwright browser probes')
    p.add_argument('--require-browser', action='store_true', help='Fail if browser probes cannot run or fail')
    p.add_argument('--browser-name', action='append', choices=('chrome', 'msedge', 'chromium', 'firefox', 'webkit'), dest='browsers')
    p.add_argument('--screenshots', type=Path)
    p.add_argument('--browser-storage-state', type=Path, help='Playwright storage-state JSON for an ephemeral authenticated SSO session; never embedded into evidence')
    p.add_argument('--auth-path', help='Protected path used to verify fail-closed unauthenticated access and optional authenticated access')
    p.add_argument('--require-auth-probe', action='store_true', help='Require an explicit auth-path probe for Gold promotion')
    p.add_argument('--auth-unauth-status', type=int, action='append', dest='auth_statuses', help='Allowed unauthenticated status; repeatable (default: 302,401,403)')
    p.add_argument('--load', action='store_true', help='Run bounded HTTP concurrency probe')
    p.add_argument('--load-url')
    p.add_argument('--load-requests', type=int, default=100)
    p.add_argument('--load-concurrency', type=int, default=10)
    p.add_argument('--load-min-success', type=float, default=.99)
    p.add_argument('--load-max-p95-ms', type=float)
    p.add_argument('--no-security-header-check', action='store_true')
    p.add_argument('--no-require-nicegui', action='store_true', help='Allow offline cert without local NiceGUI runtime; company Gold promotion should normally not use this')
    p.add_argument('--format', choices=('text', 'json'), default='text')
    a = p.parse_args()

    headers = dict(a.header)
    browser = BrowserProbeConfig(
        enabled=a.browser or a.require_browser,
        required=a.require_browser,
        browsers=tuple(a.browsers or (('chrome','msedge') if a.require_browser else ('chromium',))),
        screenshot_dir=a.screenshots,
        storage_state=a.browser_storage_state,
    )
    auth = None
    if a.auth_path:
        auth = AuthProbeConfig(path=a.auth_path, unauthenticated_statuses=tuple(a.auth_statuses or (302,401,403)), required=True)
    elif a.require_auth_probe:
        p.error('--require-auth-probe requires --auth-path')
    load = None
    if a.load:
        load = LoadProbeConfig(
            url=a.load_url or a.target_url,
            requests=max(1, a.load_requests),
            concurrency=max(1, a.load_concurrency),
            min_success_rate=max(0.0, min(1.0, a.load_min_success)),
            max_p95_ms=a.load_max_p95_ms,
            timeout_seconds=a.timeout,
        )
    config = LiveCertificationConfig(
        target_url=a.target_url,
        health_path=a.health_path,
        readiness_path=a.readiness_path,
        websocket_path=a.websocket_path,
        timeout_seconds=a.timeout,
        headers=headers,
        browser=browser,
        auth=auth,
        load=load,
        evidence_path=Path(a.evidence),
        require_security_headers=not a.no_security_header_check,
        require_nicegui_runtime=not a.no_require_nicegui,
    )
    report = run_gold_certification(config, root=Path(a.root))
    evidence = write_evidence(report, a.evidence)

    if a.format == 'json':
        print(json.dumps(report.to_dict(), indent=2))
    else:
        for check in report.checks:
            req = 'required' if check.required else 'optional'
            print(f'[{check.status.value.upper():7}] {check.label} ({req}): {check.detail}')
        print(f'\nGold eligible: {report.gold_eligible}; summary={report.summary}; evidence={evidence}')
    return 0 if report.gold_eligible else 1


if __name__ == '__main__':
    raise SystemExit(main())
