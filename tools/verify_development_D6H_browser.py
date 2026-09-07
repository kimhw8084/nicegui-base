#!/usr/bin/env python3
"""D6H visual/reference closure acceptance against a live candidate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from verify_development_D6B_browser import THEMES, VIEWPORTS, _contact_sheet, _geometry


ANALYTICS = (
    'spc_i_mr', 'spc_ewma', 'spc_cusum', 'capability_histogram',
    'qq_probability', 'ecdf', 'box_distribution', 'violin_distribution',
    'ridge_distribution', 'wafer_categorical', 'wafer_defect',
)
RECIPES = ('spc-monitor', 'fdc-tool-health', 'excursion-defense-line', 'lot-wafer-explorer', 'yield-loss', 'pm-effect-analysis', 'chamber-matching', 'rca-cockpit')
TOP_LEVEL_ROUTES = (
    '/', '/design', '/components', '/patterns', '/quality', '/workbench/data',
    '/analytics', '/layouts', '/recipes', '/applications', '/ai-guide',
)
ROUTES = (
    *TOP_LEVEL_ROUTES,
    *tuple(f'/analytics/{key}' for key in ANALYTICS),
    *tuple(f'/recipes/{key}' for key in RECIPES),
    '/applications/spc-control-center', '/applications/fdc-health-center', '/applications/excursion-investigation',
)

SEMANTIC_TITLES = {
    'spc_i_mr': 'SPC I-MR', 'spc_ewma': 'SPC EWMA', 'spc_cusum': 'SPC CUSUM',
    'capability_histogram': 'Capability Histogram', 'qq_probability': 'Q-Q Probability',
    'ecdf': 'ECDF', 'box_distribution': 'Box Distribution',
    'violin_distribution': 'Violin Distribution', 'ridge_distribution': 'Ridge Distribution',
    'wafer_categorical': 'Wafer Categorical', 'wafer_defect': 'Wafer Defect',
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, str]] = []
    console_errors: list[dict[str, str]] = []
    overflow: list[dict[str, object]] = []
    screenshots: list[Path] = []
    checks: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for viewport_name, (width, height) in VIEWPORTS.items():
            for theme in THEMES:
                context = browser.new_context(viewport={'width': width, 'height': height}, color_scheme=theme)
                context.add_init_script(f"localStorage.setItem('nicegui_base_theme', {theme!r})")
                page = context.new_page()
                page.on('console', lambda message, viewport=viewport_name, mode=theme: console_errors.append({'viewport': viewport, 'theme': mode, 'text': message.text}) if message.type == 'error' else None)
                for route in ROUTES:
                    try:
                        response = page.goto(args.url.rstrip('/') + route, wait_until='domcontentloaded', timeout=45000)
                        page.wait_for_timeout(300)
                        body = page.locator('body').inner_text()
                        lower = body.casefold()
                        if response is None or response.status != 200:
                            raise AssertionError(f'HTTP {response.status if response else None}')
                        if 'NGB-20260906-D6H.1' not in body or 'NGB-20260905-D3' in body or 'NGB-20260906-D6G' in body:
                            raise AssertionError('stale or missing D6H.1 identity')
                        if 'workbench' in lower or 'builder' in lower:
                            raise AssertionError('retired product terminology leaked into the reference surface')
                        if route == '/components':
                            text = page.locator('.cui-workbench-catalog-results').inner_text().casefold()
                            if not text or 'spc' in text or 'recipe' in text or 'pattern' in text:
                                raise AssertionError('Components is not scoped to component authority')
                        elif route == '/patterns':
                            text = page.locator('.cui-workbench-catalog-results').inner_text().casefold()
                            if not text or 'button' in text or 'spc' in text or 'recipe' in text:
                                raise AssertionError('Application Patterns is not scoped to pattern authority')
                        elif route.startswith('/analytics/'):
                            if 'measurement mapping required' in lower or page.locator('.cui-chart-panel').count() < 1:
                                raise AssertionError('analytical reference did not render a live chart')
                            key = route.rsplit('/', 1)[-1]
                            semantic_root = page.locator(f'[data-visual-semantic="{key}"]').first
                            if semantic_root.count() < 1:
                                raise AssertionError(f'{key} has no semantic reference wrapper')
                            if semantic_root.locator('.cui-chart-panel__body, .cui-spatial-svg-host').count() < 1:
                                raise AssertionError(f'{key} has no rendered chart body')
                            if semantic_root.locator('canvas, svg').count() < 1:
                                raise AssertionError(f'{key} rendered no chart geometry')
                            if SEMANTIC_TITLES[key] not in body:
                                raise AssertionError(f'{key} title does not match its semantic family')
                            if key == 'violin_distribution' and not page.locator('[data-visual-semantic="violin"]').count():
                                raise AssertionError('violin reference has no violin semantic renderer')
                            if key == 'ridge_distribution' and not page.locator('[data-visual-semantic="ridge"]').count():
                                raise AssertionError('ridge reference has no ridge semantic renderer')
                            if key == 'wafer_categorical' and 'Category' not in body:
                                raise AssertionError('categorical wafer legend is not discrete')
                            if key == 'wafer_defect' and 'Defect state' not in body:
                                raise AssertionError('defect wafer legend is not discrete')
                        elif route.startswith('/recipes/'):
                            if 'canonical sample composition' not in lower or 'preview mounts on demand' in lower:
                                raise AssertionError('recipe does not show an immediate sample composition')
                            if page.locator('.cui-workbench-panel-preview').count() < 1:
                                raise AssertionError('recipe preview panels are missing')
                        elif route.startswith('/applications/'):
                            required = {
                                'spc-control-center': 'Control chart',
                                'fdc-health-center': 'Aligned sensor traces',
                                'excursion-investigation': 'Affected vs control distribution',
                            }
                            if not any(value in body for value in required.values()):
                                raise AssertionError('domain-specific full application composition missing')
                        elif route == '/quality' and 'Golden reference readiness' not in body:
                            raise AssertionError('diagnostics does not expose the promoted readiness authority')
                        geometry = _geometry(page)
                        if geometry['overflow']:
                            overflow.append({'route': route, 'viewport': viewport_name, 'theme': theme, 'geometry': geometry})
                        shot = output / f'{route.strip("/").replace("/", "_") or "start"}_{viewport_name}_{theme}.png'
                        page.screenshot(path=str(shot), full_page=True)
                        screenshots.append(shot)
                        checks.append({'route': route, 'viewport': viewport_name, 'theme': theme, 'passed': True, 'geometry': geometry})
                    except Exception as exc:
                        failures.append({'route': route, 'viewport': viewport_name, 'theme': theme, 'error': f'{type(exc).__name__}: {exc}'})
                        shot = output / f'FAIL_{route.strip("/").replace("/", "_") or "start"}_{viewport_name}_{theme}.png'
                        page.screenshot(path=str(shot), full_page=True)
                        screenshots.append(shot)
                context.close()
        browser.close()

    result = {
        'status': 'PASS' if not failures and not console_errors and not overflow else 'FAIL',
        'candidate': 'NGB-20260906-D6H.1',
        'browser_backend': 'local pinned Playwright Chromium; in-app browser connector unavailable',
        'routes': len(ROUTES), 'viewports': list(VIEWPORTS), 'themes': list(THEMES),
        'checks': checks, 'failures': failures, 'console_errors': console_errors, 'overflow': overflow,
        'screenshots': [str(path) for path in screenshots], 'contact_sheet': str(output / 'contact_sheet.png'),
    }
    _contact_sheet(screenshots, output / 'contact_sheet.png')
    (output / 'D6H1_BROWSER_RESULT.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
