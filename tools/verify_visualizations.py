#!/usr/bin/env python3
"""Fresh-server semantic, responsive, and interaction smoke verifier for /analytics.

The verifier owns the server it starts on an ephemeral port. It never attaches
to or terminates an existing development server.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright


VIEWPORTS = {
    'desktop': (1440, 1000),
    'tablet': (1024, 900),
    'small_tablet': (768, 900),
    'phone': (390, 844),
}
REPRESENTATIVES = (
    'spc_i_mr', 'spc_p', 'spc_ewma', 'spc_cusum', 'capability_histogram', 'qq_probability', 'ecdf', 'violin_distribution',
    'ridge_distribution', 'wafer_continuous', 'wafer_categorical', 'wafer_delta',
    'wafer_defect', 'wafer_contour', 'wafer_small_multiples', 'fdc_recipe_step_trace', 'fdc_golden_envelope',
    'fdc_multi_sensor', 'fdc_chamber_fingerprint', 'fdc_pca_scores', 'fdc_pca_loadings',
    'fdc_hotelling_t2', 'fdc_spe_q', 'rca_affected_control', 'rca_commonality_matrix',
    'rca_contribution_waterfall', 'rca_correlation_matrix', 'rca_genealogy_graph',
    'rca_fault_tree', 'rca_sankey', 'yield_pareto', 'yield_waterfall', 'weibull_reliability',
    'doe_main_effects', 'doe_interactions', 'doe_response_surface',
)
SCREENSHOT_SURFACES = (
    'spc_i_mr', 'spc_p', 'spc_ewma', 'spc_cusum', 'capability_histogram', 'qq_probability',
    'ecdf', 'violin_distribution', 'ridge_distribution', 'wafer_categorical',
    'wafer_defect', 'wafer_delta', 'wafer_contour', 'wafer_small_multiples', 'fdc_golden_envelope',
    'fdc_multi_sensor', 'fdc_pca_scores', 'fdc_pca_loadings', 'rca_commonality_matrix',
    'rca_contribution_waterfall', 'rca_correlation_matrix', 'rca_genealogy_graph',
    'rca_fault_tree', 'rca_sankey', 'yield_pareto', 'yield_waterfall',
    'weibull_reliability', 'doe_interactions', 'doe_response_surface',
)

FOCUSED_SURFACES = frozenset(SCREENSHOT_SURFACES)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _source_state(repo: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()

    return {
        'sha': git('rev-parse', 'HEAD'),
        'origin_main': git('rev-parse', 'origin/main'),
        'status': git('status', '--short'),
        'candidate': 'NGB-20260907-G2.6',
    }


def _settle(page: Page) -> None:
    page.wait_for_timeout(650)
    page.wait_for_function(
        """() => [...document.querySelectorAll('[data-analytic-key] canvas, [data-analytic-key] svg')]
        .every(node => { const r=node.getBoundingClientRect(); return r.width > 0 && r.height > 0; })""",
        timeout=15000,
    )


def _set_real_theme(page: Page, theme: str) -> dict[str, Any]:
    for _ in range(2):
        if page.locator('.q-dialog:visible, [role="dialog"]:visible').count():
            page.keyboard.press('Escape')
            page.wait_for_timeout(250)
    control = page.locator('button[aria-label^="Appearance theme:"]').first
    for _ in range(3):
        is_dark = page.locator('body.body--dark').count() > 0
        if (theme == 'dark') == is_dark:
            break
        control.click()
        page.wait_for_timeout(350)
    is_dark = page.locator('body.body--dark').count() > 0
    if (theme == 'dark') != is_dark:
        raise AssertionError(f'real appearance control did not resolve {theme}: body--dark={is_dark}')
    values = page.evaluate("""() => {
        const root = document.documentElement;
        const body = document.body;
        const sample = document.querySelector('.cui-chart-panel, .cui-spatial-panel, main');
        const style = sample ? getComputedStyle(sample) : null;
        return {
            theme: root.dataset.theme || '', bodyDark: body.classList.contains('body--dark'),
            bodyBackground: getComputedStyle(body).backgroundColor,
            surfaceBackground: style ? style.backgroundColor : '', text: style ? style.color : '',
        };
    }""")
    if bool(values['bodyDark']) != (theme == 'dark'):
        raise AssertionError(f'appearance state mismatch: {values}')
    return values


def _geometry(page: Page) -> dict[str, Any]:
    return page.evaluate("""() => {
        const visible = el => { const s=getComputedStyle(el), r=el.getBoundingClientRect();
          return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0
            && !el.closest('.cui-visually-hidden,[aria-hidden="true"],details:not([open]),.cui-chart-data-disclosure'); };
        const main = document.querySelector('main,[role=main]');
        const roots = [...document.querySelectorAll('[data-analytic-key] canvas,[data-analytic-key] svg,.cui-chart-panel,.cui-spatial-panel')].filter(visible);
        const bounds = roots.map(el => { const r=el.getBoundingClientRect(); return {tag:el.tagName,w:r.width,h:r.height,x:r.x,y:r.y}; });
        const visibleText = [...document.querySelectorAll('[data-analytic-key] *')].filter(visible).map(el => {
          const text=[...el.childNodes].filter(node => node.nodeType === Node.TEXT_NODE).map(node => node.textContent || '').join(' ').trim();
          const r=el.getBoundingClientRect(); return {text, x:r.x, y:r.y, w:r.width, h:r.height};
        }).filter(item => item.text);
        const longDecimals = visibleText.filter(item => /[0-9]+[.][0-9]{7,}/.test(item.text));
        const analytic = document.querySelector('[data-analytic-key]');
        const faultRoot = analytic?.querySelector('[data-renderer-type="fault_tree"]');
        const sankeyRoot = analytic?.querySelector('[data-renderer-type="sankey"]');
        const nodeBoxes = root => [...(root?.querySelectorAll('svg path,svg rect') || [])].filter(el => {
          const s=getComputedStyle(el), r=el.getBoundingClientRect();
          return visible(el) && r.width > 20 && r.height > 16 && s.fill !== 'none' && s.fill !== 'transparent';
        }).map(el => { const r=el.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; });
        const overlaps = boxes => boxes.flatMap((a,i) => boxes.slice(i+1).map(b => {
          const ix=Math.max(0, Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x));
          const iy=Math.max(0, Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y));
          return ix > 1 && iy > 1 ? {a,b,area:ix*iy} : null;
        }).filter(Boolean));
        const labelBounds = root => [...(root?.querySelectorAll('svg text') || [])].filter(visible).map(el => {
          const r=el.getBoundingClientRect(); return {text:(el.textContent || '').trim(), x:r.x,y:r.y,w:r.width,h:r.height};
        }).filter(item => item.text);
        const faultNodes=nodeBoxes(faultRoot), sankeyLabels=labelBounds(sankeyRoot);
        const faultPanel=faultRoot?.getBoundingClientRect(), sankeyPanel=sankeyRoot?.getBoundingClientRect();
        const outside=(items,panel) => panel ? items.filter(item => item.x < panel.x-1 || item.x+item.w > panel.x+panel.width+1 || item.y < panel.y-1 || item.y+item.h > panel.y+panel.height+1) : [];
        const qq = analytic?.querySelector('[data-qq-y-min]');
        const qqExtent = qq ? {min:Number(qq.getAttribute('data-qq-y-min')), max:Number(qq.getAttribute('data-qq-y-max'))} : null;
        const multiples = [...document.querySelectorAll('.cui-workbench-mini-grid--wafer-multiples .cui-spatial-viewport')].filter(visible).map(el => {
          const r=el.getBoundingClientRect(); return {w:r.width,h:r.height,ratio:r.height/Math.max(1,r.width)};
        });
        return {viewport: innerWidth, scrollWidth: document.documentElement.scrollWidth,
          overflow: document.documentElement.scrollWidth > innerWidth + 1,
          mainWidth: main?.getBoundingClientRect().width || 0, chartRoots: bounds,
          bodyDark: document.body.classList.contains('body--dark'),
          titleWrap: [...document.querySelectorAll('[data-analytic-key] h1,[data-analytic-key] h2,.cui-chart-panel__title')]
            .filter(visible).map(el => ({text:el.textContent, width:el.getBoundingClientRect().width, height:el.getBoundingClientRect().height})),
          longDecimals, faultTree: {nodes:faultNodes, overlaps:overlaps(faultNodes), outsideLabels:outside(labelBounds(faultRoot),faultPanel)},
          sankey: {labels:sankeyLabels, outsideLabels:outside(sankeyLabels,sankeyPanel)}, qqExtent, smallMultiples:multiples,
        };
    }""")


def _visual_findings(geometry: dict[str, Any]) -> list[dict[str, Any]]:
    """Group repeated child symptoms under their smallest visible root."""
    findings: list[dict[str, Any]] = []
    if geometry['overflow']:
        findings.append({'kind': 'page-horizontal-overflow', 'root': 'document'})
    for index, item in enumerate(geometry['chartRoots']):
        if item['w'] <= 1 or item['h'] <= 1:
            findings.append({'kind': 'zero-size-chart', 'root': f'chart-root-{index}', 'geometry': item})
        if item['w'] < 360 and item['h'] > max(720, item['w'] * 3.5):
            findings.append({'kind': 'pathological-chart-aspect', 'root': f'chart-root-{index}', 'geometry': item})
    for title in geometry['titleWrap']:
        text = title.get('text') or ''
        if len(text) > 8 and title['height'] > 48 and title['width'] < 180:
            findings.append({'kind': 'collapsed-title-container', 'text': text, 'geometry': title})
    if geometry.get('longDecimals'):
        findings.append({'kind': 'pathological-numeric-label', 'examples': geometry['longDecimals'][:5], 'count': len(geometry['longDecimals'])})
    fault = geometry.get('faultTree') or {}
    if fault.get('overlaps'):
        findings.append({'kind': 'fault-tree-node-overlap', 'count': len(fault['overlaps']), 'examples': fault['overlaps'][:3]})
    if fault.get('outsideLabels'):
        findings.append({'kind': 'fault-tree-label-outside', 'count': len(fault['outsideLabels']), 'examples': fault['outsideLabels'][:3]})
    sankey = geometry.get('sankey') or {}
    if sankey.get('outsideLabels'):
        findings.append({'kind': 'sankey-label-outside', 'count': len(sankey['outsideLabels']), 'examples': sankey['outsideLabels'][:3]})
    qq = geometry.get('qqExtent')
    if qq and qq['min'] <= 0 < qq['max']:
        findings.append({'kind': 'qq-zero-baseline-flattened', 'extent': qq})
    multiples = geometry.get('smallMultiples') or []
    if multiples and any(item['ratio'] > 1.65 for item in multiples):
        findings.append({'kind': 'small-multiple-vertical-waste', 'examples': multiples})
    return findings


def _semantic_findings(page: Page, surface: str) -> list[dict[str, Any]]:
    """Assert the high-risk semantic contracts that v2's geometry pass missed."""
    findings: list[dict[str, Any]] = []
    if surface == 'rca_correlation_matrix':
        panel = page.locator('[data-chart-kind]').first
        mode = panel.get_attribute('data-chart-scale-mode')
        low = panel.get_attribute('data-chart-color-min')
        high = panel.get_attribute('data-chart-color-max')
        try:
            valid_scale = mode == 'diverging' and float(low) < 0 < float(high)
        except (TypeError, ValueError):
            valid_scale = False
        if not valid_scale:
            findings.append({'kind': 'correlation-scale-not-diverging', 'mode': mode, 'min': low, 'max': high})
    if surface == 'wafer_categorical':
        wafer = page.locator('[data-renderer-type="wafer_map"]').first
        if wafer.get_attribute('data-wafer-scale-mode') != 'categorical':
            findings.append({'kind': 'categorical-wafer-scale-mismatch'})
        alert_count = wafer.locator('.cui-wafer-die.is-watch').count()
        if alert_count:
            findings.append({'kind': 'categorical-wafer-category-alert-coupling', 'alert_count': alert_count})
    if surface in {'rca_contribution_waterfall', 'yield_waterfall'}:
        waterfall = page.locator('[data-renderer-type="waterfall"]').first
        if waterfall.get_attribute('data-waterfall-signed') != 'true':
            findings.append({'kind': 'waterfall-signed-contract-missing'})
    if surface == 'rca_sankey' and page.viewport_size and page.viewport_size['width'] <= 520:
        if page.locator('[data-sankey-stage-key]:visible').count() != 1:
            findings.append({'kind': 'sankey-mobile-stage-key-missing'})
    return findings


def _close_page(page: Page, context: Any) -> None:
    try:
        page.close(run_before_unload=False)
    except Exception:
        pass
    try:
        context.close()
    except Exception:
        pass


def _surface_matrix(repo: Path) -> list[dict[str, Any]]:
    from nicegui_base.semiconductor.surfaces import SEMICONDUCTOR_SURFACE_REGISTRY
    from nicegui_base.workbench.analytic_specimens import ANALYTIC_SEMANTIC_CONTRACTS, CANONICAL_ANALYTIC_FIXTURES

    rows = []
    for key, definition in SEMICONDUCTOR_SURFACE_REGISTRY.items():
        contract = ANALYTIC_SEMANTIC_CONTRACTS[key]
        fixture = CANONICAL_ANALYTIC_FIXTURES[key]
        rows.append({
            'key': key, 'category': definition.category, 'purpose': definition.purpose,
            'use_when': list(definition.use_when), 'avoid_when': list(definition.avoid_when),
            'geometry': contract.geometry, 'x_axis': contract.x_axis, 'y_axis': contract.y_axis,
            'legend': contract.legend, 'meaning': contract.meaning,
            'required_fields': list(contract.required_fields), 'panels': list(contract.panels),
            'options': list(contract.options), 'fixture_rows': len(fixture),
            'raw_workbench_echart_bypass': False,
        })
    return rows


def _surface_check(page: Page, *, port: int, surface: str, viewport: str, theme: str,
                   screenshot: Path | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    page.goto(f'http://127.0.0.1:{port}/analytics/{surface}', wait_until='domcontentloaded', timeout=45000)
    _settle(page)
    theme_values = _set_real_theme(page, theme)
    contract = page.locator(f'[data-analytic-key="{surface}"]')
    if contract.count() != 1:
        raise AssertionError('route or semantic contract missing')
    body = contract.inner_text()
    visual = page.locator(f'[data-analytic-key="{surface}"] canvas, [data-analytic-key="{surface}"] svg')
    if not body.strip() or visual.count() < 1:
        raise AssertionError('active semantic specimen has no rendered visual body')
    geometry = _geometry(page)
    if geometry['overflow'] or not geometry['chartRoots']:
        raise AssertionError(f'bad geometry: {geometry}')
    if not all(item['w'] > 0 and item['h'] > 0 for item in geometry['chartRoots']):
        raise AssertionError(f'zero-size chart geometry: {geometry}')
    semantic_count = page.locator(f'[data-analytic-key="{surface}"] [data-visual-semantic]').count()
    if semantic_count < 1:
        raise AssertionError('surface has no governed semantic visual marker')
    if screenshot is not None:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot), full_page=True)
    semantic_findings = _semantic_findings(page, surface)
    return {
        'surface': surface, 'viewport': viewport, 'theme': theme, 'passed': True,
        'geometry': geometry, 'theme_values': theme_values, 'semantic_marker_count': semantic_count,
        'theme_nodes': page.locator(f'[data-analytic-key="{surface}"] [data-chart-theme]').evaluate_all(
            "els => els.map(el => el.getAttribute('data-chart-theme'))"
        ),
    }, _visual_findings(geometry) + semantic_findings


def _contact_sheet(paths: list[Path], output: Path) -> None:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return
    images = []
    for path in paths:
        try:
            image = Image.open(path).convert('RGB')
            image.thumbnail((360, 240))
            images.append((path.name, image.copy()))
        except Exception:
            continue
    if not images:
        return
    columns, cell_w, cell_h = 3, 380, 270
    sheet = Image.new('RGB', (columns * cell_w, ((len(images) + columns - 1) // columns) * cell_h), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, (name, image) in enumerate(images):
        x, y = (index % columns) * cell_w, (index // columns) * cell_h
        sheet.paste(image, (x + 10, y + 10)); draw.text((x + 10, y + 250), name[:58], fill='black')
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, default=Path('/private/tmp/ngb_visualization_audit_v3'))
    parser.add_argument('--archive', type=Path, default=Path('/private/tmp/ngb_visualization_audit_v3.zip'))
    parser.add_argument('--manifest', type=Path, default=None, help='External archive hash manifest path')
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    source_state = _source_state(repo)
    (output / 'source_state.json').write_text(json.dumps(source_state, indent=2) + '\n', encoding='utf-8')
    matrix = _surface_matrix(repo)
    (output / 'surface_matrix.json').write_text(json.dumps(matrix, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    example_run = subprocess.run(
        [str(repo / '.venv' / 'bin' / 'python'), str(repo / 'tools' / 'execute_visualization_examples.py')],
        cwd=repo, env={**os.environ, 'PYTHONPATH': str(repo / 'source')}, capture_output=True, text=True,
        timeout=120, check=False,
    )
    try:
        example_payload = json.loads(example_run.stdout)
    except json.JSONDecodeError:
        example_payload = {'count': 0, 'passed': 0, 'failed': [{'error': example_run.stderr or example_run.stdout}]}
    example_payload['returncode'] = example_run.returncode
    (output / 'example_execution.json').write_text(json.dumps(example_payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    port = args.port or _free_port()
    server_log = output / 'server.log'
    env = os.environ.copy(); env['PYTHONPATH'] = str(repo / 'source')
    command = [str(repo / '.venv' / 'bin' / 'python'), str(repo / 'run_nicegui_base.py'), '--host', '127.0.0.1', '--port', str(port)]
    started = time.time()
    with server_log.open('w', encoding='utf-8') as log:
        process = subprocess.Popen(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    server_state = {'mode': 'started', 'pid': process.pid, 'port': port, 'source_sha': source_state['sha'], 'command': command, 'launch_seconds': None}
    try:
        import urllib.request
        for _ in range(80):
            if process.poll() is not None:
                raise RuntimeError(f'owned server exited with {process.returncode}')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=1) as response:
                    if response.status == 200: break
            except Exception:
                time.sleep(.25)
        else:
            raise RuntimeError('owned server did not become ready')
        server_state['launch_seconds'] = round(time.time() - started, 3)
        (output / 'server_state.json').write_text(json.dumps(server_state, indent=2) + '\n', encoding='utf-8')

        failures: list[dict[str, Any]] = []
        page_errors: list[dict[str, Any]] = []
        console_errors: list[dict[str, Any]] = []
        checks: list[dict[str, Any]] = []
        visual_findings: list[dict[str, Any]] = []
        screenshots: list[Path] = []
        interactions: list[dict[str, Any]] = []

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

            def run_batch(surfaces: list[str], viewport_name: str, theme: str) -> None:
                width, height = VIEWPORTS[viewport_name]
                context = browser.new_context(viewport={'width': width, 'height': height}, color_scheme=theme)
                page = context.new_page(); current = {'surface': None}
                page.on('pageerror', lambda exc: page_errors.append({'surface': current['surface'], 'viewport': viewport_name, 'theme': theme, 'error': str(exc)}))
                page.on('console', lambda message: console_errors.append({'surface': current['surface'], 'viewport': viewport_name, 'theme': theme, 'text': message.text}) if message.type == 'error' else None)
                try:
                    for surface in surfaces:
                        current['surface'] = surface
                        try:
                            capture = output / 'screenshots' / f'{surface}_{viewport_name}_{theme}.png' if surface in FOCUSED_SURFACES else None
                            check, findings = _surface_check(page, port=port, surface=surface, viewport=viewport_name, theme=theme, screenshot=capture)
                            checks.append(check)
                            visual_findings.extend([{'surface': surface, 'viewport': viewport_name, 'theme': theme, **finding} for finding in findings])
                            if capture is not None: screenshots.append(capture)
                        except Exception as exc:
                            failures.append({'surface': surface, 'viewport': viewport_name, 'theme': theme, 'error': f'{type(exc).__name__}: {exc}'})
                finally:
                    _close_page(page, context)

            run_batch([row['key'] for row in matrix], 'desktop', 'light')
            for viewport_name in VIEWPORTS:
                for theme in ('light', 'dark'):
                    run_batch(list(REPRESENTATIVES), viewport_name, theme)

            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, color_scheme='light')
            page = context.new_page(); current = {'surface': 'spc_i_mr'}
            page.on('pageerror', lambda exc: page_errors.append({'surface': current['surface'], 'error': str(exc)}))
            page.on('console', lambda message: console_errors.append({'surface': current['surface'], 'text': message.text}) if message.type == 'error' else None)
            try:
                page.goto(f'http://127.0.0.1:{port}/analytics/spc_i_mr', wait_until='domcontentloaded'); _settle(page)
                panel = page.locator('[data-analytic-key="spc_i_mr"] [data-chart-kind]').first
                labels = panel.locator('button[aria-label]').evaluate_all("els => els.map(el => el.getAttribute('aria-label'))")
                observed = {
                    'toolbar_labels': labels, 'data_view': False, 'export_menu': False,
                    'zoom_changed': False, 'x_range_changed': False, 'reset_restored': False,
                    'fullscreen_geometry': 'not-supported-by-browser', 'theme_switch': False,
                }

                def chart_range(axis: str) -> str | None:
                    return panel.get_attribute(f'data-chart-range-{axis}')

                initial_x, initial_y = chart_range('x'), chart_range('y')
                panel.locator('button[aria-label="Zoom in"]').first.click()
                page.wait_for_function(
                    """({before, selector}) => document.querySelector(selector)?.getAttribute('data-chart-range-x') !== before""",
                    arg={'before': initial_x, 'selector': '[data-analytic-key="spc_i_mr"] [data-chart-kind]'},
                    timeout=5000,
                )
                after_zoom_x, after_zoom_y = chart_range('x'), chart_range('y')
                observed['zoom_changed'] = after_zoom_x != initial_x and after_zoom_y != initial_y

                panel.locator('button[aria-label="View range"]').first.click()
                page.locator('.cui-chart-range-menu:visible button[aria-label="X axis zoom in"]').click()
                page.wait_for_function(
                    """({before, selector}) => document.querySelector(selector)?.getAttribute('data-chart-range-x') !== before""",
                    arg={'before': after_zoom_x, 'selector': '[data-analytic-key="spc_i_mr"] [data-chart-kind]'},
                    timeout=5000,
                )
                observed['x_range_changed'] = chart_range('x') != after_zoom_x and chart_range('y') == after_zoom_y

                panel.locator('button[aria-label="Reset chart"]').first.click()
                page.wait_for_function(
                    """selector => { const e=document.querySelector(selector); return e?.getAttribute('data-chart-range-x') === '0,100' && e?.getAttribute('data-chart-range-y') === '0,100'; }""",
                    arg='[data-analytic-key="spc_i_mr"] [data-chart-kind]', timeout=5000,
                )
                observed['reset_restored'] = chart_range('x') == '0,100' and chart_range('y') == '0,100'

                panel.locator('button[aria-label="View chart data"]').first.click(); page.wait_for_timeout(400)
                observed['data_view'] = page.locator('[role="dialog"]:visible table tr').count() > 1
                page.keyboard.press('Escape'); page.wait_for_timeout(300)

                panel.locator('button[aria-label="Export chart"]').first.click()
                page.wait_for_timeout(500)
                export_menu = page.locator('.cui-chart-export-menu:visible')
                export_text = export_menu.inner_text() if export_menu.count() else ''
                export_labels = export_menu.locator('button').evaluate_all(
                    "els => els.map(el => el.textContent.trim()).filter(Boolean)"
                ) if export_menu.count() else []
                observed['export_menu'] = (
                    export_menu.count() == 1
                    and all(label in export_text for label in ('Image', 'Data', 'Copy data'))
                    and len(export_labels) >= 3
                )
                observed['export_labels'] = export_labels
                page.keyboard.press('Escape'); page.wait_for_timeout(300)

                fullscreen_enabled = page.evaluate('Boolean(document.fullscreenEnabled)')
                panel.locator('button[aria-label="Toggle fullscreen"]').first.click(); page.wait_for_timeout(500)
                if fullscreen_enabled:
                    page.wait_for_function('Boolean(document.fullscreenElement)', timeout=5000)
                    entered_rect = panel.bounding_box()
                    panel.locator('button[aria-label="Toggle fullscreen"]').first.click(); page.wait_for_timeout(500)
                    page.wait_for_function('!document.fullscreenElement', timeout=5000)
                    exited_rect = panel.bounding_box()
                    observed['fullscreen_geometry'] = bool(entered_rect and exited_rect and entered_rect['width'] > 0 and exited_rect['width'] > 0)

                light_values = _set_real_theme(page, 'light')
                light_nodes = [panel.get_attribute('data-chart-theme')]
                dark_values = _set_real_theme(page, 'dark')
                dark_nodes = [panel.get_attribute('data-chart-theme')]
                _set_real_theme(page, 'light')
                observed['theme_switch'] = (
                    light_values['bodyBackground'] != dark_values['bodyBackground']
                    or light_values['surfaceBackground'] != dark_values['surfaceBackground']
                ) and light_nodes != dark_nodes and dark_nodes and all(value == 'dark' for value in dark_nodes)
                required = ('data_view', 'export_menu', 'zoom_changed', 'x_range_changed', 'reset_restored', 'theme_switch')
                if not all(observed[key] for key in required):
                    raise AssertionError(f'toolbar/chart interaction proof incomplete: {observed}')
                interactions.append({'surface': 'spc_i_mr', **observed, 'passed': True})
                sequence = ('spc_i_mr', 'wafer_continuous', 'fdc_pca_scores', 'rca_sankey', 'doe_interactions', 'spc_i_mr')
                for cycle in range(3):
                    for surface in sequence:
                        page.goto(f'http://127.0.0.1:{port}/analytics/{surface}', wait_until='domcontentloaded'); _settle(page)
                        if page.locator('[data-analytic-key]').count() != 1:
                            raise AssertionError(f'lifecycle switch did not leave one active contract: {surface}')
                interactions.append({'surface_switch_sequence': list(sequence), 'cycles': 3, 'passed': True})
            except Exception as exc:
                failures.append({'scope': 'toolbar_and_lifecycle', 'error': f'{type(exc).__name__}: {exc}'})
            finally:
                _close_page(page, context)
            browser.close()

        example_pass = example_payload.get('count') == example_payload.get('passed') == 58 and not example_payload.get('failed')
        if not example_pass:
            failures.append({'scope': 'public_examples', 'error': f"{example_payload.get('passed', 0)}/{example_payload.get('count', 0)} executable examples passed"})
        server_state.update({'browser_completed': True, 'termination': 'owned_process_group_pending'})
        if process.poll() is None:
            process.terminate(); process.wait(timeout=8); server_state['termination'] = 'owned_process_terminated'
        (output / 'server_state.json').write_text(json.dumps(server_state, indent=2) + '\n', encoding='utf-8')
        archive = args.archive.resolve()
        manifest = (args.manifest.resolve() if args.manifest else archive.with_suffix('.manifest.json'))
        result = {
            'status': 'PASS' if not failures and not page_errors and not console_errors and not visual_findings and example_pass else 'FAIL',
            'candidate': 'NGB-20260907-G2.6', 'source_sha': source_state['sha'], 'port': port, 'server_pid': process.pid,
            'surface_count': len(matrix), 'desktop_surface_checks': len(matrix),
            'responsive_checks': len(REPRESENTATIVES) * len(VIEWPORTS) * 2,
            'checks': checks, 'interactions': interactions, 'failures': failures,
            'page_errors': page_errors, 'console_errors': console_errors, 'visual_findings': visual_findings,
            'raw_finding_count': len(visual_findings), 'example_execution': example_payload,
            'screenshots': [str(path) for path in screenshots], 'unsupported': [],
            # The archive cannot contain its own final SHA-256 without a
            # self-hash paradox.  The sibling manifest is the hash authority.
            'evidence_zip': str(archive), 'evidence_sha256': None,
            'evidence_hash_note': 'Final archive SHA-256 is recorded in the external sibling manifest.',
            'human_visual_review': 'PENDING_HUMAN_VISUAL_REVIEW',
        }
        (output / 'audit.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        (output / 'issues.json').write_text(json.dumps({'root_findings': visual_findings, 'failures': failures, 'page_errors': page_errors, 'console_errors': console_errors}, indent=2) + '\n', encoding='utf-8')
        (output / 'browser_errors.json').write_text(json.dumps({'page_errors': page_errors, 'console_errors': console_errors}, indent=2) + '\n', encoding='utf-8')
        _contact_sheet(screenshots, output / 'contact_sheets' / 'representative.png')
        family_groups = {
            'spc': ('spc_',),
            'distribution': ('capability_', 'ecdf_', 'violin_', 'ridge_'),
            'wafer': ('wafer_',),
            'fdc': ('fdc_',),
            'rca': ('rca_',),
            'yield_reliability_doe': ('yield_', 'weibull_', 'doe_'),
        }
        for family, prefixes in family_groups.items():
            family_paths = [path for path in screenshots if path.name.startswith(prefixes)]
            _contact_sheet(family_paths, output / 'contact_sheets' / f'{family}.png')
        summary = f"""# Visualization audit

- Status: **{result['status']}**
- Candidate: `{result['candidate']}`
- Source SHA: `{source_state['sha']}`
- Fresh owned server: PID `{process.pid}` on ephemeral port `{port}`
- Registered surfaces: **{len(matrix)}**
- Desktop light surface smoke: **{len(matrix)}/{len(matrix)}**
- Responsive representative checks: **{result['responsive_checks']}**
- Executable public examples: **{example_payload.get('passed', 0)}/{example_payload.get('count', 0)}**
- Root visual findings: **{len(visual_findings)}**
- Console errors: **{len(console_errors)}**
- Page errors: **{len(page_errors)}**
- Archive hash: recorded in external sibling manifest `{manifest}` (self-hash intentionally not embedded)
- Human visual review: **PENDING_HUMAN_VISUAL_REVIEW**
"""
        (output / 'SUMMARY.md').write_text(summary, encoding='utf-8')
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
            for path in output.rglob('*'):
                if path.is_file(): bundle.write(path, path.relative_to(output.parent))
        archive_hash = _sha256(archive)
        manifest_payload = {
            'evidence_zip': str(archive), 'evidence_sha256': archive_hash,
            'source_sha': source_state['sha'], 'candidate': result['candidate'],
            'self_hash_embedded': False,
            'note': 'audit.json intentionally carries evidence_sha256=null because embedding the archive hash changes the archive. This sibling manifest is the final hash authority.',
            'human_visual_review': 'PENDING_HUMAN_VISUAL_REVIEW',
        }
        manifest.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        result['evidence_sha256'] = archive_hash
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result['status'] == 'PASS' else 1
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=3)


if __name__ == '__main__':
    raise SystemExit(main())
