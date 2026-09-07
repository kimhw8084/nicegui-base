#!/usr/bin/env python3
"""D6H.3 installed-candidate semantic browser and human-evidence verifier."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from verify_development_D6B_browser import THEMES, VIEWPORTS, _contact_sheet, _geometry


CANDIDATE = 'NGB-20260906-D6H.3'
EXPECTED_COMPONENTS = 34
EXPECTED_PATTERNS = 10
EXPECTED_ANALYTICS = 58

PRIMARY = (
    ('start', '/'), ('design', '/design'), ('components', '/components'), ('data', '/workbench/data'),
    ('visualizations', '/analytics'), ('layouts', '/layouts'), ('patterns', '/patterns'), ('recipes', '/recipes'),
    ('applications', '/applications'), ('ai-guide', '/ai-guide'), ('diagnostics', '/quality'),
)
PATTERN_ROUTES = {
    'dashboard': '/studio/pattern%3Adashboard', 'data_explorer': '/studio/pattern%3Adata_explorer',
    'master_detail': '/studio/pattern%3Amaster_detail', 'crud': '/studio/pattern%3Acrud',
    'monitoring': '/studio/pattern%3Amonitoring', 'search': '/studio/pattern%3Asearch',
    'settings': '/studio/pattern%3Asettings', 'wizard': '/studio/pattern%3Awizard',
    'comparison': '/studio/pattern%3Acomparison', 'analysis_workspace': '/studio/pattern%3Aanalysis_workspace',
}
PATTERN_ANATOMY = {
    'dashboard': ('kpis', 'trend', 'exceptions'),
    'data_explorer': ('filters', 'primary_table', 'selected_detail'),
    'master_detail': ('master', 'selected_detail'),
    'crud': ('create', 'read', 'update', 'delete', 'validation'),
    'monitoring': ('status_kpis', 'health_trend', 'alerts', 'supporting_data'),
    'search': ('query', 'facets', 'results', 'selected_context', 'empty_state'),
    'settings': ('section_navigation', 'settings_form', 'dirty_state', 'save', 'reset', 'validation'),
    'wizard': ('progress', 'back', 'next', 'validation', 'review'),
    'comparison': ('populations', 'delta', 'comparison_visual', 'aligned_evidence'),
    'analysis_workspace': ('analysis_filters', 'primary_visual', 'supporting_table', 'selected_inspector'),
}
PATTERN_REPRESENTATIVE = ('dashboard', 'monitoring', 'analysis_workspace', 'comparison', 'crud')

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
KEY_ANALYTICS = (
    'spc_i_mr', 'spc_xbar_r', 'spc_xbar_s', 'spc_ewma', 'spc_cusum', 'capability_histogram',
    'qq_probability', 'ecdf', 'box_distribution', 'violin_distribution', 'ridge_distribution',
    'rca_sankey', 'rca_fault_tree', 'rca_genealogy_graph', 'doe_main_effects', 'doe_interactions',
    'wafer_categorical', 'wafer_defect',
)

# Actual production-renderer contracts for every promoted analytical capability.
# These selectors are independent of the catalog metadata wrapper, so a correctly
# described entry cannot pass while mounting the wrong geometry.
EXPECTED_RENDERER = {
    **{key: 'chart:control' for key in ANALYTICS[:9]},
    'capability_histogram': 'chart:histogram', 'qq_probability': 'chart:scatter', 'ecdf': 'chart:line',
    'box_distribution': 'chart:box_plot', 'violin_distribution': 'semantic:violin', 'ridge_distribution': 'semantic:ridge',
    'wafer_continuous': 'renderer:wafer_map', 'wafer_categorical': 'renderer:wafer_map', 'wafer_defect': 'renderer:wafer_map',
    'wafer_delta': 'renderer:wafer_map', 'wafer_comparison': 'renderer:wafer_comparison', 'lot_wafer_strip': 'renderer:wafer_map',
    'wafer_small_multiples': 'renderer:wafer_map', 'wafer_contour': 'renderer:wafer_contour', 'wafer_radial': 'renderer:radial_profile',
    'wafer_center_edge': 'chart:bar', 'wafer_ring': 'chart:bar', 'wafer_sector': 'chart:bar', 'wafer_defect_clusters': 'renderer:wafer_map',
    'fdc_recipe_step_trace': 'chart:line', 'fdc_golden_envelope': 'chart:line', 'fdc_multi_sensor': 'chart:line',
    'fdc_tool_chamber_compare': 'chart:bar', 'fdc_chamber_fingerprint': 'renderer:fingerprint_matrix',
    'fdc_sensor_fingerprint': 'renderer:fingerprint_matrix', 'fdc_alarm_overlay': 'chart:line',
    'fdc_equipment_event_overlay': 'chart:line', 'fdc_pca_scores': 'chart:scatter', 'fdc_pca_loadings': 'chart:bar',
    'fdc_hotelling_t2': 'chart:line', 'fdc_spe_q': 'chart:line', 'rca_affected_control': 'chart:box_plot',
    'rca_commonality_ranking': 'chart:bar', 'rca_enrichment': 'chart:bar', 'rca_commonality_matrix': 'renderer:commonality_matrix',
    'rca_contribution_waterfall': 'renderer:waterfall', 'rca_correlation_matrix': 'chart:heatmap',
    'rca_evidence_matrix': 'renderer:commonality_matrix', 'rca_genealogy_graph': 'renderer:relationship_graph',
    'rca_cause_tree': 'renderer:cause_tree', 'rca_fault_tree': 'renderer:fault_tree', 'rca_sankey': 'renderer:sankey',
    'yield_pareto': 'chart:pareto', 'bin_pareto': 'chart:pareto', 'yield_waterfall': 'renderer:waterfall',
    'weibull_reliability': 'chart:line', 'doe_main_effects': 'chart:line', 'doe_interactions': 'chart:line',
    'doe_response_surface': 'chart:heatmap',
}
assert set(EXPECTED_RENDERER) == set(ANALYTICS)

COMPONENTS = (
    'button_group', 'split_button', 'divider', 'collapsible_panel', 'accordion', 'chip', 'count_badge',
    'severity_indicator', 'freshness_indicator', 'data_quality_badge', 'button', 'action_button', 'icon_button',
    'surface', 'badge', 'text_input', 'number_input', 'textarea', 'search_input', 'select', 'multi_select',
    'autocomplete', 'combobox', 'checkbox', 'checkbox_group', 'radio_group', 'switch', 'slider', 'range_slider',
    'date_picker', 'date_range_picker', 'time_picker', 'datetime_picker', 'file_upload',
)
COMPONENT_REPRESENTATIVE = ('button', 'action_button', 'text_input', 'select', 'checkbox', 'data_quality_badge', 'file_upload')
RECIPES = ('spc-monitor', 'fdc-tool-health', 'excursion-defense-line', 'lot-wafer-explorer', 'yield-loss', 'pm-effect-analysis', 'chamber-matching', 'rca-cockpit')
RECIPE_REPRESENTATIVE = ('spc-monitor', 'excursion-defense-line', 'pm-effect-analysis')
APPLICATIONS = ('spc-control-center', 'fdc-health-center', 'excursion-investigation')


def _capture_name(route: str) -> str:
    return route.strip('/').replace('/', '_').replace('%3A', '_') or 'start'


def _option_markers(page: Page, key: str) -> None:
    required = {
        'spc_i_mr': ('[data-visual-semantic="spc_i_mr-individuals"]', '[data-visual-semantic="spc_i_mr-moving-range"]'),
        'spc_xbar_r': ('[data-visual-semantic="spc_xbar_r-xbar"]', '[data-visual-semantic="spc_xbar_r-range"]'),
        'spc_xbar_s': ('[data-visual-semantic="spc_xbar_s-xbar"]', '[data-visual-semantic="spc_xbar_s-standard-deviation"]'),
    }
    for selector in required.get(key, ()):
        if page.locator(selector).count() != 1:
            raise AssertionError(f'{key} is missing required paired panel {selector}')
    marker = {
        'spc_ewma': '[data-chart-semantics="center-ucl-lcl"]',
        'spc_cusum': '[data-chart-semantics="positive-negative-decision-limits"]',
        'capability_histogram': '[data-spec-lines="LSL Target USL"]',
        'qq_probability': '[data-chart-semantics="observed-vs-expected"]',
        'ecdf': '[data-chart-step="end"]',
        'box_distribution': '[data-chart-semantics="quartiles-median-whiskers"]',
        'violin_distribution': '[data-visual-semantic="violin"]',
        'ridge_distribution': '[data-visual-semantic="ridge"]',
        'rca_sankey': '[data-renderer-type="sankey"][data-chart-semantics="quantity-weighted-flow-bands"]',
        'rca_fault_tree': '[data-renderer-type="fault_tree"][data-chart-semantics="hierarchy-connectors-and-or-gates"]',
        'rca_genealogy_graph': '[data-renderer-type="relationship_graph"][data-chart-semantics="branching-merging-directed-relationships"]',
        'rca_cause_tree': '[data-renderer-type="cause_tree"][data-chart-semantics="hierarchical-causal-candidates"]',
        'doe_main_effects': '[data-chart-semantics="clear-opposing-main-effect-slopes"]',
        'doe_interactions': '[data-chart-semantics="non-parallel-crossing-interaction"]',
        'wafer_contour': '[data-renderer-type="wafer_contour"][data-chart-semantics="clipped-contour-isolines"]',
        'fdc_alarm_overlay': '[data-chart-semantics="trace-with-event-marker"]',
        'fdc_equipment_event_overlay': '[data-chart-semantics="trace-with-event-marker"]',
        'rca_contribution_waterfall': '[data-renderer-type="waterfall"][data-chart-semantics="cumulative-signed-bridge"]',
        'yield_waterfall': '[data-renderer-type="waterfall"][data-chart-semantics="cumulative-signed-bridge"]',
    }.get(key)
    if marker and page.locator(marker).count() < 1:
        raise AssertionError(f'{key} is missing its semantic renderer/option marker')
    if key == 'wafer_categorical' and 'Category' not in page.locator('body').inner_text():
        raise AssertionError('Wafer Categorical has no discrete Category legend')
    if key == 'wafer_defect' and 'Defect state' not in page.locator('body').inner_text():
        raise AssertionError('Wafer Defect has no discrete Defect state legend')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, str]] = []
    page_errors: list[dict[str, str]] = []
    console_errors: list[dict[str, str]] = []
    overflow: list[dict[str, object]] = []
    checks: list[dict[str, object]] = []
    screenshots: list[Path] = []

    def open_and_base(page: Page, route: str) -> str:
        response = page.goto(args.url.rstrip('/') + route, wait_until='domcontentloaded', timeout=45000)
        page.wait_for_timeout(900)
        body = page.locator('body').inner_text()
        lower = body.casefold()
        if response is None or response.status != 200:
            raise AssertionError(f'HTTP {response.status if response else None}')
        stale = ('NGB-20260905-D3', 'NGB-20260906-D6G', 'NGB-20260906-D6H.1', 'NGB-20260906-D6H.2')
        if CANDIDATE not in body or any(identity in body for identity in stale):
            raise AssertionError('missing D6H.3 identity or stale candidate identity leaked')
        if 'workbench' in lower or 'builder' in lower:
            raise AssertionError('retired product terminology leaked into a visible reference')
        if 'measurement mapping required' in lower or 'internal server error' in lower:
            raise AssertionError('canonical reference did not render out of the box')
        return body

    def shot(page: Page, *, section: str, route: str, viewport: str, theme: str, suffix: str = '') -> None:
        geometry = _geometry(page)
        if geometry['overflow']:
            overflow.append({'route': route, 'section': section, 'viewport': viewport, 'theme': theme, 'geometry': geometry})
        name = f'{section}_{_capture_name(route)}_{viewport}_{theme}{("_" + suffix) if suffix else ""}.png'
        path = output / name
        page.screenshot(path=str(path), full_page=True)
        screenshots.append(path)

    def check_primary(page: Page, route: str, body: str) -> None:
        if route == '/quality' and ('Golden promoted contracts' not in body or '76 / 76' not in body):
            raise AssertionError('Diagnostics Golden promoted denominator is incomplete')
        if route == '/layouts':
            live = page.locator('[data-live-layout-pattern]')
            if live.count() < 10 or live.locator('[data-layout-slot]').count() < 20:
                raise AssertionError('Layouts does not visually demonstrate the governed shells and semantic slots')
        if route == '/ai-guide' and ('requirement' not in body.casefold() or 'business/domain logic' not in body.casefold() or 'nicegui-base agent-check .' not in body or page.locator('[data-agent-workflow]').count() != 1):
            raise AssertionError('AI guide is missing the compact end-to-end agent workflow')
        if route == '/components':
            text = page.locator('.cui-workbench-catalog-results').inner_text().casefold()
            if not text or any(token in text for token in ('spc', 'recipe', 'application pattern')):
                raise AssertionError('Components is not scoped to component authority')
        if route == '/patterns':
            text = page.locator('.cui-workbench-catalog-results').inner_text().casefold()
            if not text or any(token in text for token in ('button', 'spc', 'recipe')):
                raise AssertionError('Application Patterns is not scoped to pattern authority')

    def check_pattern(page: Page, key: str) -> None:
        root = page.locator(f'[data-pattern-semantic="{key}"]')
        if root.count() != 1:
            raise AssertionError(f'{key} has no unique governed PatternPage anatomy')
        for region in PATTERN_ANATOMY[key]:
            if root.locator(f'[data-pattern-region="{region}"]').count() < 1:
                raise AssertionError(f'{key} is missing defining region {region}')
        required_class = {
            'dashboard': '.cui-metric-strip', 'data_explorer': '.cui-data-table', 'master_detail': '.cui-property-grid',
            'crud': '.cui-form', 'monitoring': '.cui-search-results', 'search': '.cui-search-results',
            'settings': '.cui-form', 'wizard': '.cui-progress-steps', 'comparison': '.cui-difference-table',
            'analysis_workspace': '.cui-chart-panel',
        }[key]
        if root.locator(required_class).count() < 1:
            raise AssertionError(f'{key} does not use its defining governed component {required_class}')
        expected_tables = {'dashboard': 1, 'data_explorer': 1, 'master_detail': 1, 'crud': 1, 'monitoring': 1, 'analysis_workspace': 1}
        if key in expected_tables and root.locator('.cui-data-table').count() != expected_tables[key]:
            raise AssertionError(f'{key} has a duplicate or missing primary/supporting DataTable')
        body = root.inner_text()
        lower_body = body.casefold()
        contracts = {
            'dashboard': (root.locator('.cui-metric-card').count() >= 3 and root.locator('[data-chart-kind="line"]').count() >= 1 and 'Recent exceptions' in body),
            'data_explorer': (root.locator('input').count() >= 1 and 'Selected lot' in body),
            'master_detail': ('Master lots' in body and 'Selected from the master list' in body),
            'crud': (all(label in lower_body for label in ('create recipe', 'delete selected', 'edit selected recipe', 'owner is required'))),
            'monitoring': (root.locator('.cui-metric-card').count() >= 3 and root.locator('[data-chart-kind="line"]').count() >= 1 and 'Active alerts' in body),
            'search': (all(label in lower_body for label in ('search lots, tools, or recipes', 'representative results', 'selected result context', 'no-result behavior'))),
            'settings': (all(label in body for label in ('Settings sections', 'Save settings', 'Reset changes', 'Enable paging'))),
            'wizard': (all(label in lower_body for label in ('scope', 'map fields', 'review preview', 'back', 'next: review'))),
            'comparison': (root.locator('[data-chart-kind="bar"][data-series-count="2"]').count() >= 1 and all(label in body for label in ('Golden tool', 'Candidate tool', 'Mean thickness'))),
            'analysis_workspace': (root.locator('[data-chart-kind="line"]').count() >= 1 and all(label in body for label in ('Linked lot records', 'Selected excursion'))),
        }
        if not contracts[key]:
            raise AssertionError(f'{key} is missing its pattern-specific semantic evidence')

        # The defining paired surfaces must genuinely coexist on desktop. This
        # catches full-width stacked skeletons and giant blank grid regions.
        paired_regions = {
            'data_explorer': ('primary_table', 'selected_detail'),
            'master_detail': ('master', 'selected_detail'),
            'analysis_workspace': ('primary_visual', 'selected_inspector'),
        }
        if key in paired_regions and (page.viewport_size or {}).get('width', 0) >= 1200:
            left_name, right_name = paired_regions[key]
            left = root.locator(f'[data-pattern-region="{left_name}"]').bounding_box()
            right = root.locator(f'[data-pattern-region="{right_name}"]').bounding_box()
            if left is None or right is None:
                raise AssertionError(f'{key} paired regions are not visible')
            overlap = min(left['y'] + left['height'], right['y'] + right['height']) - max(left['y'], right['y'])
            if right['x'] <= left['x'] or overlap < min(100.0, left['height'] * 0.35, right['height'] * 0.35):
                raise AssertionError(f'{key} does not keep its primary and contextual surfaces balanced on the same screen')

    def check_analytic(page: Page, key: str) -> None:
        contract = page.locator(f'[data-analytic-key="{key}"]')
        if contract.count() != 1:
            raise AssertionError(f'{key} has no unique semantic contract')
        if not contract.get_attribute('data-semantic-geometry') or not contract.get_attribute('data-semantic-x') or not contract.get_attribute('data-semantic-y'):
            raise AssertionError(f'{key} semantic geometry/axis contract is incomplete')
        root = page.locator(f'[data-visual-semantic="{key}"]').first
        if root.count() != 1 or root.locator('canvas, svg').count() < 1:
            raise AssertionError(f'{key} has no actual rendered chart body')
        renderer_kind, renderer_value = EXPECTED_RENDERER[key].split(':', 1)
        selector = {
            'chart': f'[data-chart-kind="{renderer_value}"]',
            'renderer': f'[data-renderer-type="{renderer_value}"]',
            'semantic': f'[data-visual-semantic="{renderer_value}"]',
        }[renderer_kind]
        actual = contract.locator(selector)
        if actual.count() < 1:
            raise AssertionError(f'{key} mounted the wrong production geometry; expected {EXPECTED_RENDERER[key]}')
        if renderer_kind == 'chart':
            panel = actual.first
            if not panel.get_attribute('data-chart-x') or not panel.get_attribute('data-chart-y') or not panel.get_attribute('data-series-labels'):
                raise AssertionError(f'{key} production chart is missing visible axis/series semantics')
        _option_markers(page, key)

    def check_component(page: Page, key: str, *, section: str, route: str, viewport: str, theme: str) -> None:
        if page.locator(f'[data-component-specimen="{key}"]').count() != 1:
            raise AssertionError(f'{key} Preview does not use its production component specimen')
        if page.locator('[data-reference-contract]').count() != 1:
            raise AssertionError(f'{key} lacks its typed reference contract')
        shot(page, section=section, route=route, viewport=viewport, theme=theme, suffix='preview')
        page.get_by_role('tab', name='States', exact=True).click(); page.wait_for_timeout(350)
        state_body = page.locator('body').inner_text()
        if not all(name in state_body for name in ('Default', 'Loading', 'Empty', 'Error', 'Disabled')):
            raise AssertionError(f'{key} States does not expose canonical variants')
        shot(page, section=section, route=route, viewport=viewport, theme=theme, suffix='states')
        page.get_by_role('tab', name='Code', exact=True).click(); page.wait_for_timeout(350)
        code = page.locator('.cui-studio-code').inner_text()
        if 'from nicegui_base import' not in code or key not in code.casefold().replace(' ', '_'):
            raise AssertionError(f'{key} Code does not expose the canonical reusable API')
        shot(page, section=section, route=route, viewport=viewport, theme=theme, suffix='code')

    def check_recipe(page: Page, body: str) -> None:
        if 'canonical sample composition' not in body.casefold() or page.locator('.cui-workbench-panel-preview').count() < 1:
            raise AssertionError('recipe has no immediate governed sample composition')

    def check_application(page: Page, key: str, body: str) -> None:
        definition = {
            'spc-control-center': ('spc_i_mr', 'critical dimension', '[data-chart-kind="control"]'),
            'fdc-health-center': ('fdc_recipe_step_trace', 'pressure', '[data-chart-kind="line"]'),
            'excursion-investigation': ('rca_affected_control', 'Affected', '[data-chart-kind="box_plot"]'),
        }[key]
        host = page.locator(f'[data-governed-analytic="{definition[0]}"]')
        if host.count() != 1 or definition[1].casefold() not in body.casefold() or host.locator('canvas, svg').count() < 1 or host.locator(definition[2]).count() < 1:
            raise AssertionError(f'{key} lacks its governed primary analytical renderer')
        if key == 'spc-control-center' and (host.locator('[data-visual-semantic="spc_i_mr-individuals"]').count() != 1 or host.locator('[data-visual-semantic="spc_i_mr-moving-range"]').count() != 1):
            raise AssertionError('SPC Control Center approximates I-MR instead of reusing the paired renderer')

    schedules: list[tuple[str, str, str, str, str]] = []
    for _name, route in PRIMARY:
        for viewport in VIEWPORTS:
            for theme in THEMES: schedules.append(('primary', route, '', viewport, theme))
    for key, route in PATTERN_ROUTES.items(): schedules.append(('pattern', route, key, 'desktop', 'light'))
    for key in PATTERN_REPRESENTATIVE:
        schedules.extend((('pattern', PATTERN_ROUTES[key], key, 'desktop', 'dark'), ('pattern', PATTERN_ROUTES[key], key, 'phone', 'light')))
    for key in ANALYTICS: schedules.append(('analytic', f'/analytics/{key}', key, 'desktop', 'light'))
    for key in KEY_ANALYTICS:
        schedules.extend((('analytic', f'/analytics/{key}', key, 'desktop', 'dark'), ('analytic', f'/analytics/{key}', key, 'phone', 'light')))
    for key in COMPONENTS: schedules.append(('component', f'/catalog/component/{key}', key, 'desktop', 'light'))
    for key in COMPONENT_REPRESENTATIVE:
        schedules.extend((('component', f'/catalog/component/{key}', key, 'desktop', 'dark'), ('component', f'/catalog/component/{key}', key, 'phone', 'light')))
    for key in RECIPES: schedules.append(('recipe', f'/recipes/{key}', key, 'desktop', 'light'))
    for key in RECIPE_REPRESENTATIVE:
        schedules.extend((('recipe', f'/recipes/{key}', key, 'desktop', 'dark'), ('recipe', f'/recipes/{key}', key, 'phone', 'light')))
    for key in APPLICATIONS:
        schedules.extend((('application', f'/applications/{key}', key, 'desktop', 'light'), ('application', f'/applications/{key}', key, 'desktop', 'dark'), ('application', f'/applications/{key}', key, 'phone', 'light')))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for section, route, key, viewport_name, theme in schedules:
            width, height = VIEWPORTS[viewport_name]
            context = browser.new_context(viewport={'width': width, 'height': height}, color_scheme=theme)
            context.add_init_script(f"localStorage.setItem('nicegui_base_theme', {theme!r}); localStorage.setItem('cui_lab_theme', {theme!r})")
            page = context.new_page()
            page.on('pageerror', lambda exc, r=route, v=viewport_name, t=theme: page_errors.append({'route': r, 'viewport': v, 'theme': t, 'error': str(exc)}))
            page.on('console', lambda message, r=route, v=viewport_name, t=theme: console_errors.append({'route': r, 'viewport': v, 'theme': t, 'text': message.text}) if message.type == 'error' else None)
            try:
                body = open_and_base(page, route)
                if section == 'primary': check_primary(page, route, body)
                elif section == 'pattern': check_pattern(page, key)
                elif section == 'analytic': check_analytic(page, key)
                elif section == 'component': check_component(page, key, section=section, route=route, viewport=viewport_name, theme=theme)
                elif section == 'recipe': check_recipe(page, body)
                elif section == 'application': check_application(page, key, body)
                if section != 'component': shot(page, section=section, route=route, viewport=viewport_name, theme=theme)
                checks.append({'section': section, 'route': route, 'key': key, 'viewport': viewport_name, 'theme': theme, 'passed': True, 'geometry': _geometry(page)})
            except Exception as exc:
                failures.append({'section': section, 'route': route, 'key': key, 'viewport': viewport_name, 'theme': theme, 'error': f'{type(exc).__name__}: {exc}'})
                failure_path = output / f'FAIL_{section}_{_capture_name(route)}_{viewport_name}_{theme}.png'
                try: page.screenshot(path=str(failure_path), full_page=True); screenshots.append(failure_path)
                except Exception: pass
            context.close()
        browser.close()

    desktop_light = {(item['section'], item['key']) for item in checks if item['viewport'] == 'desktop' and item['theme'] == 'light'}
    result = {
        'status': 'PASS' if not failures and not page_errors and not console_errors and not overflow else 'FAIL',
        'candidate': CANDIDATE,
        'browser_backend': 'local pinned Playwright Chromium against installed candidate',
        'scheduled_checks': len(schedules), 'executed_checks': len(checks),
        'semantic_counts': {
            'patterns': sum(('pattern', key) in desktop_light for key in PATTERN_ROUTES),
            'analytics': sum(('analytic', key) in desktop_light for key in ANALYTICS),
            'components_human_evidence': sum(('component', key) in desktop_light for key in COMPONENTS),
        },
        'expected': {'patterns': EXPECTED_PATTERNS, 'analytics': EXPECTED_ANALYTICS, 'components': EXPECTED_COMPONENTS},
        'checks': checks, 'failures': failures, 'page_errors': page_errors, 'console_errors': console_errors, 'overflow': overflow,
        'screenshots': [str(path) for path in screenshots], 'contact_sheet': str(output / 'contact_sheet.png'),
    }
    _contact_sheet(screenshots, output / 'contact_sheet.png')
    (output / 'D6H3_BROWSER_RESULT.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
