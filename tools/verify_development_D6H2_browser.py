#!/usr/bin/env python3
"""D6H.2 installed-candidate visual and semantic acceptance."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from verify_development_D6B_browser import THEMES, VIEWPORTS, _contact_sheet, _geometry


CANDIDATE = 'NGB-20260906-D6H.2'
EXPECTED_COMPONENTS = 34
EXPECTED_PATTERNS = 10
EXPECTED_ANALYTICS = 58
ANALYTICS = (
    'spc_i_mr', 'spc_xbar_r', 'spc_xbar_s', 'spc_p', 'spc_np', 'spc_c', 'spc_u', 'spc_ewma', 'spc_cusum',
    'capability_histogram', 'qq_probability', 'ecdf', 'box_distribution', 'violin_distribution', 'ridge_distribution',
    'wafer_continuous', 'wafer_categorical', 'wafer_defect', 'wafer_delta', 'wafer_comparison', 'lot_wafer_strip',
    'wafer_small_multiples', 'wafer_contour', 'wafer_radial', 'wafer_center_edge', 'wafer_ring', 'wafer_sector', 'wafer_defect_clusters',
    'fdc_recipe_step_trace', 'fdc_golden_envelope', 'fdc_multi_sensor', 'fdc_tool_chamber_compare', 'fdc_chamber_fingerprint',
    'fdc_sensor_fingerprint', 'fdc_alarm_overlay', 'fdc_equipment_event_overlay', 'fdc_pca_scores', 'fdc_pca_loadings',
    'fdc_hotelling_t2', 'fdc_spe_q', 'rca_affected_control', 'rca_commonality_ranking', 'rca_enrichment', 'rca_commonality_matrix',
    'rca_contribution_waterfall', 'rca_correlation_matrix', 'rca_evidence_matrix', 'rca_genealogy_graph', 'rca_cause_tree',
    'rca_fault_tree', 'rca_sankey', 'yield_pareto', 'bin_pareto', 'yield_waterfall', 'weibull_reliability',
    'doe_main_effects', 'doe_interactions', 'doe_response_surface',
)
COMPONENTS = (
    'button_group', 'split_button', 'divider', 'collapsible_panel', 'accordion', 'chip', 'count_badge',
    'severity_indicator', 'freshness_indicator', 'data_quality_badge', 'button', 'action_button', 'icon_button',
    'surface', 'badge', 'text_input', 'number_input', 'textarea', 'search_input', 'select', 'multi_select',
    'autocomplete', 'combobox', 'checkbox', 'checkbox_group', 'radio_group', 'switch', 'slider', 'range_slider',
    'date_picker', 'date_range_picker', 'time_picker', 'datetime_picker', 'file_upload',
)
PATTERNS = ('dashboard', 'data_explorer', 'master_detail', 'crud', 'monitoring', 'search', 'settings', 'wizard', 'comparison', 'analysis_workspace')
RECIPES = ('spc-monitor', 'fdc-tool-health', 'excursion-defense-line', 'lot-wafer-explorer', 'yield-loss', 'pm-effect-analysis', 'chamber-matching', 'rca-cockpit')
PRIMARY = (
    ('start', '/'), ('design', '/design'), ('components', '/components'), ('data', '/workbench/data'),
    ('visualizations', '/analytics'), ('layouts', '/layouts'), ('patterns', '/patterns'), ('recipes', '/recipes'),
    ('applications', '/applications'), ('ai-guide', '/ai-guide'), ('diagnostics', '/quality'),
)
KEY_ANALYTICS = ('spc_i_mr', 'spc_ewma', 'spc_cusum', 'qq_probability', 'ecdf', 'box_distribution', 'violin_distribution', 'ridge_distribution', 'wafer_categorical', 'wafer_defect')
SEMANTIC_TITLES = {key: key.replace('_', ' ').title() for key in ANALYTICS}
SEMANTIC_TITLES.update({'spc_i_mr': 'SPC I-MR', 'spc_ewma': 'SPC EWMA', 'spc_cusum': 'SPC CUSUM', 'qq_probability': 'Q-Q Probability', 'ecdf': 'ECDF'})


def _capture_name(route: str) -> str:
    return route.strip('/').replace('/', '_').replace('%3A', '_') or 'start'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, str]] = []
    page_errors: list[dict[str, str]] = []
    console_errors: list[dict[str, str]] = []
    overflow: list[dict[str, object]] = []
    screenshots: list[Path] = []
    checks: list[dict[str, object]] = []

    def check_page(page, route: str, *, section: str) -> None:
        response = page.goto(args.url.rstrip('/') + route, wait_until='domcontentloaded', timeout=45000)
        # NiceGUI sends the initial component tree over the page websocket; wait
        # for the chart accessibility/data alternative to arrive before judging
        # semantic labels or taking the human-review screenshot.
        page.wait_for_timeout(800)
        body = page.locator('body').inner_text()
        lower = body.casefold()
        if response is None or response.status != 200:
            raise AssertionError(f'HTTP {response.status if response else None}')
        if CANDIDATE not in body or 'NGB-20260905-D3' in body or 'NGB-20260906-D6G' in body:
            raise AssertionError('missing current D6H.2 identity or stale release identity')
        if 'workbench' in lower or 'builder' in lower:
            raise AssertionError('retired product terminology leaked into the user-facing reference surface')
        if section == 'primary':
            if route == '/quality' and ('Golden promoted contracts' not in body or '76 / 76' not in body):
                raise AssertionError('Diagnostics does not report a complete promoted Golden denominator')
            if route == '/layouts' and page.locator('[data-live-layout-pattern]').count() < 1:
                raise AssertionError('Layouts has no live governed composition')
            if route == '/ai-guide' and ('Requirement' not in body or 'nicegui-base agent-check .' not in body or page.locator('[data-agent-workflow]').count() != 1):
                raise AssertionError('AI guide is missing the deterministic end-to-end workflow')
            if route == '/components':
                text = page.locator('.cui-workbench-catalog-results').inner_text().casefold()
                if not text or any(token in text for token in ('spc', 'recipe', 'pattern')):
                    raise AssertionError('Components is not scoped to component authority')
            if route == '/patterns':
                text = page.locator('.cui-workbench-catalog-results').inner_text().casefold()
                if not text or any(token in text for token in ('button', 'spc', 'recipe')):
                    raise AssertionError('Application Patterns is not scoped to pattern authority')
        elif section == 'component':
            if page.locator('[data-reference-example]').count() < 1 or page.locator('[data-reference-contract]').count() < 1:
                raise AssertionError('component detail lacks live example or typed contract')
        elif section == 'pattern':
            if page.locator('[data-reference-example]').count() < 1:
                raise AssertionError('pattern detail lacks live governed example')
        elif section == 'analytic':
            key = route.rsplit('/', 1)[-1]
            if 'measurement mapping required' in lower:
                raise AssertionError(f'{key} requires setup instead of showing its canonical fixture')
            root = page.locator(f'[data-visual-semantic="{key}"]').first
            if root.count() < 1:
                raise AssertionError(f'{key} has no semantic reference wrapper')
            if root.locator('.cui-chart-panel__body, .cui-spatial-svg-host, .cui-workbench-flow, .cui-workbench-tree').count() < 1:
                raise AssertionError(f'{key} has no rendered geometry body')
            if key in KEY_ANALYTICS and SEMANTIC_TITLES[key] not in body:
                raise AssertionError(f'{key} title does not match its semantic identity')
            if key == 'spc_i_mr':
                if page.locator('[data-visual-semantic="spc_i_mr-individuals"]').count() != 1 or page.locator('[data-visual-semantic="spc_i_mr-moving-range"]').count() != 1:
                    raise AssertionError('I-MR does not show Individuals and Moving Range charts')
                if 'Moving Range' not in body or 'Measurement' not in body:
                    raise AssertionError('I-MR axis/series semantics are not visible')
            if key == 'spc_ewma' and page.locator('[data-chart-semantics="center-ucl-lcl"]').count() < 1:
                raise AssertionError('EWMA center/UCL/LCL semantics are missing')
            if key == 'spc_cusum' and page.locator('[data-chart-semantics="positive-negative-decision-limits"]').count() < 1:
                raise AssertionError('CUSUM positive/negative decision semantics are missing')
            qq_semantics = ' '.join(page.locator('[data-chart-semantics="observed-vs-expected"]').all_text_contents())
            if key == 'qq_probability' and ('Expected line' not in qq_semantics or page.locator('[data-chart-semantics="observed-vs-expected"]').count() < 1):
                raise AssertionError('Q-Q observed/expected semantics are missing')
            if key == 'ecdf' and page.locator('[data-chart-semantics="monotone-cdf"]').count() < 1:
                raise AssertionError('ECDF monotone cumulative semantics are missing')
            if key == 'box_distribution' and page.locator('[data-chart-semantics="quartiles-median-whiskers"]').count() < 1:
                raise AssertionError('Box distribution quartile semantics are missing')
            if key == 'violin_distribution' and page.locator('[data-visual-semantic="violin"]').count() < 1:
                raise AssertionError('Violin silhouette is missing')
            if key == 'ridge_distribution' and page.locator('[data-visual-semantic="ridge"]').count() < 1:
                raise AssertionError('Ridge offset geometry is missing')
            if key == 'wafer_categorical' and 'Category' not in body:
                raise AssertionError('categorical wafer legend is not discrete')
            if key == 'wafer_defect' and 'Defect state' not in body:
                raise AssertionError('defect wafer legend is not discrete')
        elif section == 'recipe':
            if 'canonical sample composition' not in lower or 'preview mounts on demand' in lower:
                raise AssertionError('recipe does not show an immediate sample composition')
            if page.locator('.cui-workbench-panel-preview').count() < 1:
                raise AssertionError('recipe preview panels are missing')
        elif section == 'application':
            required = {
                'spc-control-center': ('Control chart', 'critical dimension'),
                'fdc-health-center': ('Aligned sensor traces', 'pressure'),
                'excursion-investigation': ('Affected vs control distribution', 'Affected'),
            }
            app_key = route.rsplit('/', 1)[-1]
            if not all(value in body for value in required[app_key]):
                raise AssertionError(f'{app_key} lacks its domain-specific first-screen evidence')
        geometry = _geometry(page)
        if geometry['overflow']:
            overflow.append({'route': route, 'section': section, 'geometry': geometry})
        shot = output / f'{section}_{_capture_name(route)}_{page.viewport_size["width"]}x{page.viewport_size["height"]}_{page.evaluate("document.documentElement.dataset.theme || localStorage.getItem(\'nicegui_base_theme\') || \'system\'")}.png'
        page.screenshot(path=str(shot), full_page=True)
        screenshots.append(shot)
        checks.append({'route': route, 'section': section, 'passed': True, 'geometry': geometry})

    schedules: list[tuple[str, str, tuple[str, ...], tuple[str, ...]]] = []
    for name, route in PRIMARY:
        schedules.append(('primary', route, tuple(VIEWPORTS), THEMES))
    for key in COMPONENTS:
        schedules.append(('component', f'/catalog/component/{key}', ('desktop',), ('light',)))
    for key in ('button', 'text_input', 'select', 'date_picker', 'file_upload', 'data_quality_badge'):
        schedules.append(('component', f'/catalog/component/{key}', ('desktop', 'phone'), ('dark', 'light')))
    for key in PATTERNS:
        schedules.append(('pattern', f'/studio/pattern%3A{key}', ('desktop',), ('light',)))
    for key in ('dashboard', 'analysis_workspace', 'settings', 'comparison'):
        schedules.append(('pattern', f'/studio/pattern%3A{key}', ('desktop', 'phone'), ('dark', 'light')))
    for key in ANALYTICS:
        schedules.append(('analytic', f'/analytics/{key}', ('desktop',), ('light',)))
    for key in KEY_ANALYTICS:
        schedules.append(('analytic', f'/analytics/{key}', ('desktop', 'phone'), ('dark', 'light')))
    for key in RECIPES:
        schedules.append(('recipe', f'/recipes/{key}', ('desktop',), ('light',)))
    for key in ('spc-monitor', 'excursion-defense-line', 'pm-effect-analysis'):
        schedules.append(('recipe', f'/recipes/{key}', ('desktop', 'phone'), ('dark', 'light')))
    for key in ('spc-control-center', 'fdc-health-center', 'excursion-investigation'):
        schedules.append(('application', f'/applications/{key}', tuple(VIEWPORTS), THEMES))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for section, route, viewport_names, themes in schedules:
            for viewport_name in viewport_names:
                width, height = VIEWPORTS[viewport_name]
                for theme in themes:
                    context = browser.new_context(viewport={'width': width, 'height': height}, color_scheme=theme)
                    context.add_init_script(f"localStorage.setItem('nicegui_base_theme', {theme!r})")
                    page = context.new_page()
                    page.on('pageerror', lambda exc, v=viewport_name, t=theme, r=route: page_errors.append({'route': r, 'viewport': v, 'theme': t, 'error': str(exc)}))
                    page.on('console', lambda message, v=viewport_name, t=theme, r=route: console_errors.append({'route': r, 'viewport': v, 'theme': t, 'text': message.text}) if message.type == 'error' else None)
                    try:
                        check_page(page, route, section=section)
                    except Exception as exc:
                        failures.append({'route': route, 'section': section, 'viewport': viewport_name, 'theme': theme, 'error': f'{type(exc).__name__}: {exc}'})
                        shot = output / f'FAIL_{section}_{_capture_name(route)}_{viewport_name}_{theme}.png'
                        page.screenshot(path=str(shot), full_page=True)
                        screenshots.append(shot)
                    context.close()
        browser.close()

    result = {
        'status': 'PASS' if not failures and not page_errors and not console_errors and not overflow else 'FAIL',
        'candidate': CANDIDATE,
        'browser_backend': 'local pinned Playwright Chromium; installed candidate process',
        'scheduled_checks': len(schedules), 'executed_checks': len(checks),
        'expected_catalog': {'components': EXPECTED_COMPONENTS, 'patterns': EXPECTED_PATTERNS, 'analytics': EXPECTED_ANALYTICS},
        'sections': {'primary': len(PRIMARY), 'components': len(COMPONENTS), 'patterns': len(PATTERNS), 'analytics': len(ANALYTICS), 'recipes': len(RECIPES), 'applications': 3},
        'checks': checks, 'failures': failures, 'page_errors': page_errors, 'console_errors': console_errors, 'overflow': overflow,
        'screenshots': [str(path) for path in screenshots], 'contact_sheet': str(output / 'contact_sheet.png'),
    }
    _contact_sheet(screenshots, output / 'contact_sheet.png')
    (output / 'D6H2_BROWSER_RESULT.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
