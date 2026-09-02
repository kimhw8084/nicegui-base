from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urljoin


@dataclass(frozen=True, slots=True)
class BrowserViewportEvidence:
    viewport: str
    route: str
    status: int | None
    checks: Mapping[str, bool]
    findings: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 400 and all(self.checks.values()) and not self.findings

    def to_dict(self) -> dict[str, object]:
        return {
            'viewport': self.viewport,
            'route': self.route,
            'status': self.status,
            'checks': dict(self.checks),
            'findings': list(self.findings),
            'ok': self.ok,
        }


@dataclass(frozen=True, slots=True)
class BrowserAcceptanceEvidence:
    status: str
    backend: str
    results: tuple[BrowserViewportEvidence, ...]
    findings: tuple[str, ...]
    manual_pending: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status in {'PASS', 'PASS_AUTOMATED_WITH_MANUAL_PENDING'} and all(item.ok for item in self.results)

    def to_dict(self) -> dict[str, object]:
        return {
            'schema_version': 1,
            'status': self.status,
            'backend': self.backend,
            'results': [item.to_dict() for item in self.results],
            'findings': list(self.findings),
            'manual_pending': list(self.manual_pending),
        }


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


def _page_checks(page) -> dict[str, bool]:
    return page.evaluate('''() => {
      const root = document.documentElement;
      const body = document.body;
      const focusables = [...document.querySelectorAll('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])')]
        .filter(el => !el.disabled && el.getClientRects().length > 0);
      const active = document.activeElement;
      let focusVisible = false;
      if (active && active !== document.body && active !== root) {
        const style = getComputedStyle(active);
        const width = parseFloat(style.outlineWidth || '0') || 0;
        focusVisible = width > 0 || (style.boxShadow && style.boxShadow !== 'none');
      }
      const primary = [...document.querySelectorAll('button,a[href],[role="button"]')]
        .some(el => el.getClientRects().length > 0 && !el.disabled);
      return {
        no_horizontal_document_overflow: Math.max(root.scrollWidth, body ? body.scrollWidth : 0) <= root.clientWidth + 2,
        first_interactive_control_keyboard_reachable: focusables.length === 0 ? false : active === focusables[0] || focusables.includes(active),
        visible_focus_indicator: focusVisible,
        primary_action_reachable_without_pointer_only_interaction: primary,
      };
    }''')


def run_browser_acceptance(contract: Mapping[str, Any], base_url: str, *, headless: bool = True) -> BrowserAcceptanceEvidence:
    sync_playwright = _load_playwright()
    manual = tuple(str(item) for item in contract.get('manual_checks', ()) if str(item))
    if sync_playwright is None:
        return BrowserAcceptanceEvidence(
            'SKIPPED_BROWSER_BACKEND_UNAVAILABLE',
            'none',
            (),
            ('Playwright is not installed. Install it only on a browser-proof workstation, then rerun this command.',),
            manual,
        )
    results: list[BrowserViewportEvidence] = []
    findings: list[str] = []
    routes = tuple(str(route) for route in contract.get('routes', ('/',))) or ('/',)
    viewports = tuple(item for item in contract.get('viewports', ()) if isinstance(item, Mapping))
    try:
        manager = sync_playwright()
        playwright = manager.__enter__()
        try:
            browser = playwright.chromium.launch(headless=headless)
        except Exception as exc:
            manager.__exit__(None, None, None)
            return BrowserAcceptanceEvidence(
                'SKIPPED_BROWSER_BACKEND_UNAVAILABLE',
                'playwright-chromium',
                (),
                (f'Playwright browser executable is unavailable: {type(exc).__name__}: {exc}',),
                manual,
            )
        try:
            for viewport in viewports:
                key = str(viewport.get('key') or 'viewport')
                width = max(320, int(viewport.get('width') or 1280))
                height = max(480, int(viewport.get('height') or 800))
                context = browser.new_context(viewport={'width': width, 'height': height})
                page = context.new_page()
                console_errors: list[str] = []
                page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
                page.on('pageerror', lambda exc: console_errors.append(str(exc)))
                try:
                    for route in routes:
                        response = page.goto(urljoin(base_url.rstrip('/') + '/', route.lstrip('/')), wait_until='networkidle')
                        status = response.status if response is not None else None
                        theme_before = page.evaluate("() => document.documentElement.dataset.theme || localStorage.getItem('nicegui_base_theme') || ''")
                        page.keyboard.press('Tab')
                        checks = _page_checks(page)
                        page.reload(wait_until='networkidle')
                        theme_after = page.evaluate("() => document.documentElement.dataset.theme || localStorage.getItem('nicegui_base_theme') || ''")
                        checks['root_route_http_success'] = status is not None and 200 <= int(status) < 400
                        checks['no_uncaught_console_errors'] = not console_errors
                        checks['theme_preference_survives_navigation'] = theme_before == theme_after
                        local_findings = tuple(f'console:{item}' for item in console_errors[-5:])
                        result = BrowserViewportEvidence(key, route, int(status) if status is not None else None, checks, local_findings)
                        results.append(result)
                        if not result.ok:
                            findings.append(f'{key}:{route}:browser checks failed')
                finally:
                    context.close()
        finally:
            browser.close()
            manager.__exit__(None, None, None)
    except Exception as exc:
        return BrowserAcceptanceEvidence(
            'FAIL', 'playwright-chromium', tuple(results),
            tuple(dict.fromkeys((*findings, f'browser_runner:{type(exc).__name__}:{exc}'))), manual,
        )
    status = 'FAIL' if findings else ('PASS_AUTOMATED_WITH_MANUAL_PENDING' if manual else 'PASS')
    return BrowserAcceptanceEvidence(status, 'playwright-chromium', tuple(results), tuple(dict.fromkeys(findings)), manual)


def run_browser_acceptance_file(contract_path: str | Path, base_url: str, *, output_path: str | Path | None = None, headless: bool = True) -> BrowserAcceptanceEvidence:
    path = Path(contract_path)
    contract = json.loads(path.read_text(encoding='utf-8'))
    evidence = run_browser_acceptance(contract, base_url, headless=headless)
    destination = Path(output_path) if output_path is not None else path.with_name('browser_acceptance_evidence.json')
    destination.write_text(json.dumps(evidence.to_dict(), indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return evidence


def generated_browser_runner_source() -> str:
    return '''from __future__ import annotations\n\nimport argparse\nimport json\nfrom pathlib import Path\n\nfrom nicegui_base.workbench.browser_acceptance_runner import run_browser_acceptance_file\n\n\ndef main() -> int:\n    parser = argparse.ArgumentParser(description="Run NiceGUI Base browser acceptance against this generated app")\n    parser.add_argument("base_url", nargs="?", default="http://127.0.0.1:8080")\n    parser.add_argument("--headed", action="store_true")\n    args = parser.parse_args()\n    root = Path(__file__).resolve().parents[1]\n    contract = root / ".nicegui_base" / "browser_acceptance.json"\n    evidence = run_browser_acceptance_file(contract, args.base_url, headless=not args.headed)\n    print(json.dumps(evidence.to_dict(), indent=2))\n    if evidence.status == "SKIPPED_BROWSER_BACKEND_UNAVAILABLE":\n        return 2\n    return 0 if evidence.ok else 1\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'''


__all__ = [
    'BrowserAcceptanceEvidence', 'BrowserViewportEvidence', 'generated_browser_runner_source',
    'run_browser_acceptance', 'run_browser_acceptance_file',
]
