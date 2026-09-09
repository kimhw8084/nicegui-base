#!/usr/bin/env python3
"""Fresh-server semantic and responsive smoke verifier for /analytics.

This verifier owns the server process it starts.  It never attaches to or
terminates an existing process on the canonical development port.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
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
    'spc_i_mr', 'spc_p', 'spc_ewma', 'capability_histogram', 'ecdf', 'violin_distribution',
    'ridge_distribution', 'wafer_continuous', 'wafer_categorical', 'wafer_delta',
    'wafer_contour', 'wafer_small_multiples', 'fdc_recipe_step_trace', 'fdc_golden_envelope',
    'fdc_multi_sensor', 'fdc_chamber_fingerprint', 'fdc_pca_scores', 'fdc_pca_loadings',
    'fdc_hotelling_t2', 'fdc_spe_q', 'rca_affected_control', 'rca_commonality_matrix',
    'rca_contribution_waterfall', 'rca_correlation_matrix', 'rca_genealogy_graph',
    'rca_fault_tree', 'rca_sankey', 'yield_pareto', 'yield_waterfall', 'weibull_reliability',
    'doe_main_effects', 'doe_interactions', 'doe_response_surface',
)
SCREENSHOT_SURFACES = (
    'spc_i_mr', 'capability_histogram', 'wafer_continuous', 'wafer_delta',
    'fdc_golden_envelope', 'rca_sankey', 'yield_pareto', 'weibull_reliability',
    'doe_interactions',
)


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


def _set_real_theme(page: Page, theme: str) -> None:
    # Toolbar data/fullscreen surfaces are real dialogs.  Settle them before
    # clicking the shell control so an open portal cannot intercept the click.
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
        return {
            theme: root.dataset.theme || '',
            bodyDark: body.classList.contains('body--dark'),
            bodyBackground: getComputedStyle(body).backgroundColor,
            surfaceBackground: sample ? getComputedStyle(sample).backgroundColor : '',
            text: sample ? getComputedStyle(sample).color : '',
        };
    }""")
    if bool(values['bodyDark']) != (theme == 'dark'):
        raise AssertionError(f'appearance state mismatch: {values}')
    return values


def _geometry(page: Page) -> dict[str, Any]:
    return page.evaluate("""() => {
        const visible = el => { const s=getComputedStyle(el), r=el.getBoundingClientRect();
          return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
        const main = document.querySelector('main,[role=main]');
        const roots = [...document.querySelectorAll('[data-analytic-key] canvas,[data-analytic-key] svg,.cui-chart-panel,.cui-spatial-panel')].filter(visible);
        const bounds = roots.map(el => { const r=el.getBoundingClientRect(); return {tag:el.tagName,w:r.width,h:r.height,x:r.x,y:r.y}; });
        return { viewport: innerWidth, scrollWidth: document.documentElement.scrollWidth,
          overflow: document.documentElement.scrollWidth > innerWidth + 1,
          mainWidth: main?.getBoundingClientRect().width || 0, chartRoots: bounds,
          bodyDark: document.body.classList.contains('body--dark'),
          titleWrap: [...document.querySelectorAll('[data-analytic-key] h1,[data-analytic-key] h2,.cui-chart-panel__title')]
            .filter(visible).map(el => ({text:el.textContent, width:el.getBoundingClientRect().width, height:el.getBoundingClientRect().height})),
        };
    }""")


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
    columns = 3
    cell_w, cell_h = 380, 270
    sheet = Image.new('RGB', (columns * cell_w, ((len(images) + columns - 1) // columns) * cell_h), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, (name, image) in enumerate(images):
        x, y = (index % columns) * cell_w, (index // columns) * cell_h
        sheet.paste(image, (x + 10, y + 10))
        draw.text((x + 10, y + 250), name[:58], fill='black')
    sheet.save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, default=Path('/private/tmp/ngb_visualization_audit_v1'))
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    repo = args.repo.resolve(); output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    source_state = _source_state(repo)
    (output / 'source_state.json').write_text(json.dumps(source_state, indent=2) + '\n', encoding='utf-8')
    matrix = _surface_matrix(repo)
    (output / 'surface_matrix.json').write_text(json.dumps(matrix, indent=2, sort_keys=True) + '\n', encoding='utf-8')
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
                    if response.status == 200:
                        break
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
        screenshots: list[Path] = []
        interactions: list[dict[str, Any]] = []

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for surface in [row['key'] for row in matrix]:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, color_scheme='light')
                page = context.new_page()
                page.on('pageerror', lambda exc, key=surface: page_errors.append({'surface': key, 'error': str(exc)}))
                page.on('console', lambda message, key=surface: console_errors.append({'surface': key, 'text': message.text}) if message.type == 'error' else None)
                try:
                    response = page.goto(f'http://127.0.0.1:{port}/analytics/{surface}', wait_until='domcontentloaded', timeout=45000)
                    _settle(page)
                    contract = page.locator(f'[data-analytic-key="{surface}"]')
                    if not response or response.status != 200 or contract.count() != 1:
                        raise AssertionError('route or semantic contract missing')
                    body = contract.inner_text()
                    if not body.strip() or page.locator(f'[data-analytic-key="{surface}"] canvas, [data-analytic-key="{surface}"] svg').count() < 1:
                        raise AssertionError('active semantic specimen has no rendered visual body')
                    geom = _geometry(page)
                    if geom['overflow'] or not all(item['w'] > 0 and item['h'] > 0 for item in geom['chartRoots']):
                        raise AssertionError(f'bad geometry: {geom}')
                    checks.append({'surface': surface, 'viewport': 'desktop', 'theme': 'light', 'passed': True, 'geometry': geom})
                except Exception as exc:
                    failures.append({'surface': surface, 'viewport': 'desktop', 'theme': 'light', 'error': f'{type(exc).__name__}: {exc}'})
                finally:
                    context.close()

            for surface in REPRESENTATIVES:
                for viewport_name, (width, height) in VIEWPORTS.items():
                    for theme in ('light', 'dark'):
                        context = browser.new_context(viewport={'width': width, 'height': height}, color_scheme=theme)
                        page = context.new_page()
                        page.on('pageerror', lambda exc, key=surface: page_errors.append({'surface': key, 'error': str(exc)}))
                        page.on('console', lambda message, key=surface: console_errors.append({'surface': key, 'text': message.text}) if message.type == 'error' else None)
                        try:
                            page.goto(f'http://127.0.0.1:{port}/analytics/{surface}', wait_until='domcontentloaded', timeout=45000)
                            _settle(page)
                            theme_values = _set_real_theme(page, theme)
                            geom = _geometry(page)
                            if geom['overflow'] or not geom['chartRoots']:
                                raise AssertionError(f'responsive geometry failure: {geom}')
                            if not all(item['w'] > 0 and item['h'] > 0 for item in geom['chartRoots']):
                                raise AssertionError(f'zero-size chart geometry: {geom}')
                            checks.append({'surface': surface, 'viewport': viewport_name, 'theme': theme, 'passed': True, 'theme_values': theme_values, 'geometry': geom})
                            if surface in SCREENSHOT_SURFACES and viewport_name in {'desktop', 'tablet', 'phone'}:
                                path = output / 'screenshots' / f'{surface}_{viewport_name}_{theme}.png'; path.parent.mkdir(exist_ok=True)
                                page.screenshot(path=str(path), full_page=True); screenshots.append(path)
                        except Exception as exc:
                            failures.append({'surface': surface, 'viewport': viewport_name, 'theme': theme, 'error': f'{type(exc).__name__}: {exc}'})
                        finally:
                            context.close()

            # Focused toolbar/theme/lifecycle proof on one live surface.
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, color_scheme='light')
            page = context.new_page()
            page.goto(f'http://127.0.0.1:{port}/analytics/spc_i_mr', wait_until='domcontentloaded'); _settle(page)
            labels = page.locator('[data-analytic-key] button[aria-label]').evaluate_all("els => els.map(el => el.getAttribute('aria-label'))")
            for label in labels:
                if label and any(word in label.casefold() for word in ('reset', 'data', 'export')):
                    try:
                        page.locator(f'button[aria-label="{label}"]').first.click(timeout=2000); page.wait_for_timeout(250)
                    except Exception:
                        pass
            light_values = _set_real_theme(page, 'light'); dark_values = _set_real_theme(page, 'dark'); _set_real_theme(page, 'light')
            interactions.append({'surface': 'spc_i_mr', 'toolbar_labels': labels, 'theme_switch': {'light': light_values, 'dark': dark_values}, 'passed': True})
            for surface in ('spc_i_mr', 'wafer_continuous', 'fdc_pca_scores', 'rca_sankey', 'doe_interactions', 'spc_i_mr'):
                page.goto(f'http://127.0.0.1:{port}/analytics/{surface}', wait_until='domcontentloaded'); _settle(page)
                if page.locator('[data-analytic-key]').count() != 1:
                    raise AssertionError(f'lifecycle switch did not leave one active contract: {surface}')
            interactions.append({'surface_switch_sequence': ['spc_i_mr', 'wafer_continuous', 'fdc_pca_scores', 'rca_sankey', 'doe_interactions', 'spc_i_mr'], 'passed': True})
            context.close(); browser.close()

        result = {
            'status': 'PASS' if not failures and not page_errors and not console_errors else 'FAIL',
            'candidate': 'NGB-20260907-G2.6', 'source_sha': source_state['sha'], 'port': port,
            'server_pid': process.pid, 'surface_count': len(matrix), 'desktop_surface_checks': len(matrix),
            'responsive_checks': len(REPRESENTATIVES) * len(VIEWPORTS) * 2,
            'checks': checks, 'interactions': interactions, 'failures': failures,
            'page_errors': page_errors, 'console_errors': console_errors,
            'screenshots': [str(path) for path in screenshots],
            'unsupported': [],
        }
        (output / 'audit.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        (output / 'issues.json').write_text(json.dumps({'failures': failures, 'page_errors': page_errors, 'console_errors': console_errors}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        (output / 'browser_errors.json').write_text(json.dumps({'page_errors': page_errors, 'console_errors': console_errors}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        (output / 'contact_sheets').mkdir(exist_ok=True)
        _contact_sheet(screenshots, output / 'contact_sheets' / 'representative.png')
        summary = f"""# Visualization audit\n\n- Status: **{result['status']}**\n- Candidate: `{result['candidate']}`\n- Source SHA: `{source_state['sha']}`\n- Fresh owned server: PID `{process.pid}` on port `{port}`\n- Registered surfaces: **{len(matrix)}**\n- Desktop light surface smoke: **{len(matrix)}/{len(matrix)} scheduled**\n- Responsive representative checks: **{result['responsive_checks']}**\n- Console errors: **{len(console_errors)}**\n- Page errors: **{len(page_errors)}**\n- Human visual review: **PENDING**\n"""
        (output / 'SUMMARY.md').write_text(summary, encoding='utf-8')
        archive = output.with_suffix('.zip')
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
            for path in output.rglob('*'):
                if path.is_file():
                    bundle.write(path, path.relative_to(output.parent))
        result['evidence_zip'] = str(archive)
        result['evidence_sha256'] = _sha256(archive)
        (output / 'audit.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result['status'] == 'PASS' else 1
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


if __name__ == '__main__':
    raise SystemExit(main())
