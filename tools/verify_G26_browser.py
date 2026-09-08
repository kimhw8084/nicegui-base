#!/usr/bin/env python3
"""G2.6 Reference Explorer browser acceptance and human-evidence capture.

This verifier checks the current candidate identity, real route responses, semantic
preview markers, browser errors, and overflow while producing a bounded screenshot
set for human review. It intentionally imports no release history.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


CANDIDATE = 'NGB-20260907-G2.6'
PRIMARY = (
    ('start', '/'), ('design', '/design'), ('components', '/components'),
    ('data', '/workbench/data'), ('visualizations', '/analytics'), ('layouts', '/layouts'),
    ('patterns', '/patterns'), ('recipes', '/recipes'), ('applications', '/applications'),
    ('ai-guide', '/ai-guide'), ('settings', '/settings'), ('diagnostics', '/quality'),
)
ANALYTICS = (
    'spc_i_mr','spc_xbar_r','spc_xbar_s','spc_p','spc_np','spc_c','spc_u','spc_ewma','spc_cusum',
    'capability_histogram','qq_probability','ecdf','box_distribution','violin_distribution','ridge_distribution',
    'wafer_continuous','wafer_categorical','wafer_defect','wafer_delta','wafer_comparison','lot_wafer_strip',
    'wafer_small_multiples','wafer_contour','wafer_radial','wafer_center_edge','wafer_ring','wafer_sector',
    'wafer_defect_clusters','fdc_recipe_step_trace','fdc_golden_envelope','fdc_multi_sensor','fdc_tool_chamber_compare',
    'fdc_chamber_fingerprint','fdc_sensor_fingerprint','fdc_alarm_overlay','fdc_equipment_event_overlay','fdc_pca_scores',
    'fdc_pca_loadings','fdc_hotelling_t2','fdc_spe_q','rca_affected_control','rca_commonality_ranking','rca_enrichment',
    'rca_commonality_matrix','rca_contribution_waterfall','rca_correlation_matrix','rca_evidence_matrix','rca_genealogy_graph',
    'rca_cause_tree','rca_fault_tree','rca_sankey','yield_pareto','bin_pareto','yield_waterfall','weibull_reliability',
    'doe_main_effects','doe_interactions','doe_response_surface',
)
PATTERNS = ('dashboard','data_explorer','master_detail','crud','monitoring','search','settings','wizard','comparison','analysis_workspace')
RECIPES = ('spc-monitor','fdc-tool-health','excursion-defense-line','lot-wafer-explorer','yield-loss','pm-effect-analysis','chamber-matching','rca-cockpit')
APPLICATIONS = ('spc-control-center','fdc-health-center','excursion-investigation')
STALE = ('NGB-20260905-D3','NGB-20260906-D6G','NGB-20260906-D6H','NGB-20260907-G2.5.1')


def _name(route: str, viewport: str, theme: str) -> str:
    return (route.strip('/').replace('/', '_').replace('%3A', '_') or 'start') + f'_{viewport}_{theme}.png'


def _check(page, response, route: str, *, semantic: bool = False) -> list[str]:
    body = page.locator('body').inner_text()
    identity_surface = ' '.join(page.locator('[data-build-id]').all_text_contents())
    searchable = f'{body}\n{identity_surface}'
    lower = searchable.casefold()
    issues: list[str] = []
    if response is None or response.status != 200:
        issues.append(f'http:{response.status if response else None}')
    # Build identity is intentionally absent from the primary toolbar. The
    # shell owns it in the navigation/footer identity surface; use that
    # governed marker for desktop/tablet and the visible footer on phone.
    if CANDIDATE not in searchable:
        issues.append('missing-candidate-identity')
    if any(value.casefold() in lower for value in STALE):
        issues.append('stale-candidate-identity')
    if 'internal server error' in lower or 'measurement mapping required' in lower:
        issues.append('reference-not-ready')
    if 'workbench' in lower or 'builder' in lower:
        issues.append('retired-terminology')
    if page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth + 1'):
        issues.append('horizontal-overflow')
    if semantic and page.locator('[data-visual-semantic]').count() < 1:
        issues.append('missing-rendered-semantic-body')
    return issues


def _prime_full_page_media(page) -> None:
    """Paint below-the-fold media before a long human-review screenshot.

    Chromium can report a loaded data URI while its compositor has not painted an
    off-screen image yet. Scrolling the bounded page once makes evidence faithful
    without changing the product's lazy/lifecycle behavior.
    """
    if page.locator('img').count():
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(120)
        page.evaluate('window.scrollTo(0, 0)')
        page.wait_for_timeout(120)


def _interaction_result(page, base: str, *, width: int) -> dict[str, object]:
    """Exercise the high-risk shell and discovery interactions on a live page."""
    issues: list[str] = []
    page.goto(base.rstrip('/') + '/', wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(350)
    mobile = page.locator('button.cui-shell-mobile-menu').first
    if width >= 900:
        if mobile.is_visible():
            issues.append('desktop-hamburger-visible')
        if not page.locator('button.cui-shell-settings').is_visible():
            issues.append('settings-action-hidden')
    else:
        if not mobile.is_visible():
            issues.append('mobile-hamburger-hidden')
        else:
            mobile.click(); page.wait_for_timeout(180)
            if page.locator('html[data-mobile-nav="open"]').count() != 1 or mobile.get_attribute('aria-expanded') != 'true':
                issues.append('mobile-drawer-not-open')
            page.keyboard.press('Escape'); page.wait_for_timeout(180)
            if page.locator('html[data-mobile-nav="open"]').count() or mobile.get_attribute('aria-expanded') != 'false':
                issues.append('mobile-drawer-not-closed')
    if width >= 900:
        recommendation = page.get_by_role('button', name='View recommendation').first
        if recommendation.count():
            before = page.evaluate('window.scrollY')
            recommendation.click(); page.wait_for_timeout(260)
            if page.get_by_role('button', name='Clear recommendation').count() != 1:
                issues.append('recommendation-not-open')
            if page.evaluate('window.scrollY') != before:
                issues.append('recommendation-scroll-jump')
            page.get_by_role('button', name='Clear recommendation').click(); page.wait_for_timeout(160)
            if page.get_by_role('button', name='Clear recommendation').count():
                issues.append('recommendation-not-cleared')
    settings_response = page.goto(base.rstrip('/') + '/settings', wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(250)
    if settings_response is None or settings_response.status != 200:
        issues.append('settings-route-failed')
    if page.locator('.cui-page-title').filter(has_text='Settings').count() != 1:
        issues.append('settings-title-missing')
    if width >= 900 and not page.locator('.cui-app-sidebar').is_visible():
        issues.append('settings-shell-missing')
    return {'label': f'shell-interactions-{width}', 'route': '/ and /settings', 'issues': issues}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(); screenshots = output / 'screenshots'
    screenshots.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    targets = list(PRIMARY)
    targets += [(f'analytic-{key}', f'/analytics/{key}') for key in ANALYTICS]
    targets += [(f'pattern-{key}', f'/studio/pattern%3A{key}') for key in PATTERNS]
    targets += [(f'recipe-{key}', f'/recipes/{key}') for key in RECIPES]
    targets += [(f'application-{key}', f'/applications/{key}') for key in APPLICATIONS]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for viewport, size in (('desktop', (1440, 1000)), ('tablet', (1024, 1000)), ('phone', (390, 844))):
            for theme in ('light', 'dark'):
                context = browser.new_context(viewport={'width': size[0], 'height': size[1]})
                page = context.new_page()
                events = {'console': [], 'page': []}
                page.on('console', lambda message: events['console'].append(message.text) if message.type == 'error' else None)
                page.on('pageerror', lambda error: events['page'].append(str(error)))
                for label, route in PRIMARY:
                    events['console'].clear(); events['page'].clear()
                    response = page.goto(args.url.rstrip('/') + route, wait_until='domcontentloaded', timeout=45000)
                    page.wait_for_timeout(350)
                    page.evaluate('(theme) => { document.documentElement.dataset.theme = theme; document.body.classList.toggle("q-dark", theme === "dark") }', theme)
                    _prime_full_page_media(page)
                    issues = _check(page, response, route)
                    if events['console'] or events['page']:
                        issues.append('browser-error')
                    page.screenshot(path=str(screenshots / f'{label}_{viewport}_{theme}.png'), full_page=True)
                    results.append({'label': label, 'route': route, 'viewport': viewport, 'theme': theme, 'issues': issues, 'console': events['console'][:3], 'page_errors': events['page'][:3], 'height': page.evaluate('document.body.scrollHeight')})
                context.close()
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        events = {'console': [], 'page': []}
        page.on('console', lambda message: events['console'].append(message.text) if message.type == 'error' else None)
        page.on('pageerror', lambda error: events['page'].append(str(error)))
        for label, route in targets[len(PRIMARY):]:
            events['console'].clear(); events['page'].clear()
            response = page.goto(args.url.rstrip('/') + route, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(350)
            _prime_full_page_media(page)
            semantic = label.startswith('analytic-')
            issues = _check(page, response, route, semantic=semantic)
            if events['console'] or events['page']:
                issues.append('browser-error')
            page.screenshot(path=str(screenshots / f'{label}_desktop_light.png'), full_page=True)
            results.append({'label': label, 'route': route, 'viewport': 'desktop', 'theme': 'light', 'issues': issues, 'console': events['console'][:3], 'page_errors': events['page'][:3], 'height': page.evaluate('document.body.scrollHeight')})
        for width in (1440, 390):
            context.close()
            context = browser.new_context(viewport={'width': width, 'height': 1000 if width >= 900 else 844})
            page = context.new_page()
            results.append(_interaction_result(page, args.url, width=width))
        context.close(); browser.close()
    payload = {'candidate': CANDIDATE, 'total': len(results), 'passed': sum(not item['issues'] for item in results), 'results': results}
    (output / 'G26_BROWSER_RESULT.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    try:
        from PIL import Image, ImageDraw
        files = sorted(screenshots.glob('*.png'))
        thumbs = []
        for path in files:
            image = Image.open(path).convert('RGB'); image.thumbnail((260, 170)); thumbs.append((path.name, image.copy()))
        sheet = Image.new('RGB', (780, max(190, ((len(thumbs) + 2) // 3) * 200)), 'white'); draw = ImageDraw.Draw(sheet)
        for index, (name, image) in enumerate(thumbs):
            x = (index % 3) * 260; y = (index // 3) * 200; sheet.paste(image, (x, y)); draw.text((x + 4, y + 174), name[:38], fill='black')
        sheet.save(output / 'contact_sheet.png')
    except Exception:
        pass
    print(json.dumps({'candidate': CANDIDATE, 'total': len(results), 'passed': payload['passed'], 'failed': payload['total'] - payload['passed'], 'output': str(output)}))
    return 0 if payload['passed'] == payload['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
