#!/usr/bin/env python3
"""Capture the bounded CHG-203 explicit/system dark theme diagnostic matrix."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image
from playwright.sync_api import Page, sync_playwright


SURFACES = (
    ('analytics-spc-i-mr', '/analytics/spc_i_mr', 'affected'),
    ('analytics-spc-xbar-r', '/analytics/spc_xbar_r', 'affected'),
    ('analytics-spc-xbar-s', '/analytics/spc_xbar_s', 'affected'),
    ('analytics-capability-histogram', '/analytics/capability_histogram', 'affected'),
    ('analytics-fdc-alarm-overlay', '/analytics/fdc_alarm_overlay', 'affected'),
    ('analytics-fdc-equipment-event-overlay', '/analytics/fdc_equipment_event_overlay', 'affected'),
    ('analytics-fdc-hotelling-t2', '/analytics/fdc_hotelling_t2', 'affected'),
    ('analytics-fdc-spe-q', '/analytics/fdc_spe_q', 'affected'),
    ('recipe-spc-monitor', '/recipes/spc-monitor', 'affected'),
    ('recipe-fdc-tool-health', '/recipes/fdc-tool-health', 'affected'),
    ('recipe-pm-effect-analysis', '/recipes/pm-effect-analysis', 'affected'),
    ('lab-charts', '/charts', 'control'),
    ('lab-engineering', '/engineering', 'control'),
    ('reference-pattern-analysis-workspace', '/patterns/analysis', 'control'),
    ('reference-pattern-data-explorer', '/patterns/explorer', 'control'),
    ('application-spc-control-center', '/applications/spc-control-center', 'control'),
)

R1_REFERENCES = {
    'analytics-spc-i-mr': ('chart-theme-01-analytics-spc-i-mr.png', 'e4b5e0b44ea9833ec66e8e7ec66c56a85badb7b732fc39f1a935f324b1871c29'),
    'analytics-capability-histogram': ('chart-theme-02-analytics-capability-histogram.png', '3c6d857213da04f9b2097d4ebe27471fb3f768ba2125c8fb0ea9d06b6e50defa'),
    'analytics-fdc-alarm-overlay': ('chart-theme-03-analytics-fdc-alarm-overlay.png', '148c7207b4f9d28e79d60fa66011f1499cf113c70ad504b72f335cfe2850fb07'),
}
R1_EVIDENCE_COMMIT = 'cae078a5c60e43c05fc69650630ce249f938555c'
R1_ARTIFACT_COMMIT = '9f1ed9e2efda1a7b384b625d4951d0aedf6a2764'


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _wait_for_server(process: subprocess.Popen, port: int) -> None:
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError(f'Reference Explorer exited with status {process.returncode}')
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(.2)
    raise RuntimeError('Reference Explorer did not become ready on its owned port')


def _select_appearance(page: Page, preference: str, base_url: str) -> None:
    target = {'system': 'System', 'light': 'Light', 'dark': 'Dark'}[preference]
    control = page.locator('button[aria-label^="Appearance theme:"]').first
    if not control.count():
        route = page.url
        page.goto(f'{base_url}/settings', wait_until='domcontentloaded', timeout=45000)
        page.wait_for_selector('button[aria-label^="Appearance theme:"]', timeout=15000)
        control = page.locator('button[aria-label^="Appearance theme:"]').first
        _cycle_appearance(page, control, target)
        page.goto(route, wait_until='domcontentloaded', timeout=45000)
        return
    _cycle_appearance(page, control, target)


def _cycle_appearance(page: Page, control, target: str) -> None:
    for _ in range(4):
        label = control.get_attribute('aria-label') or ''
        if label.endswith(target):
            return
        control.click()
        page.wait_for_timeout(400)
    label = control.get_attribute('aria-label') or ''
    if not label.endswith(target):
        raise AssertionError(f'appearance control did not select {target}: {label!r}')


def _settle_charts(page: Page, expected_mode: str) -> None:
    page.wait_for_function(
        """mode => {
          const charts=[...document.querySelectorAll('[data-chart-theme]')];
          return charts.length>0 && charts.every(chart => chart.getAttribute('data-chart-theme')===mode)
            && charts.every(chart => chart.querySelector('canvas,svg') || chart.matches('[data-visual-semantic]'));
        }""",
        arg=expected_mode,
        timeout=20000,
    )
    nodes = page.locator('[data-chart-theme]')
    for index in range(nodes.count()):
        nodes.nth(index).scroll_into_view_if_needed(timeout=5000)
        page.wait_for_timeout(90)
    page.evaluate('window.scrollTo(0,0)')
    page.wait_for_timeout(350)


def _browser_snapshot(page: Page) -> dict[str, Any]:
    return page.evaluate("""() => {
      const rgb = value => {
        const m=value.match(/[\\d.]+/g)||[];
        return m.slice(0,3).map(Number);
      };
      const chartNodes=[...document.querySelectorAll('[data-chart-theme]')];
      const charts=chartNodes.map(node=>{
        const panel=node.closest('.cui-chart-panel,.cui-spatial-panel,.cui-plotly-panel')||node;
        const plot=panel.querySelector('canvas')||panel.querySelector('svg')||node.querySelector('canvas,svg');
        const panelRect=panel.getBoundingClientRect();
        const plotRect=plot?.getBoundingClientRect();
        let plotPoint=null,plotBox=null,alpha=null,canvasSize=null;
        if(plotRect) plotBox={x:plotRect.x+window.scrollX,y:plotRect.y+window.scrollY,
          width:plotRect.width,height:plotRect.height};
        if(plot?.tagName==='CANVAS' && plot.width && plot.height){
          canvasSize={width:plot.width,height:plot.height};
          try {
            const context=plot.getContext('2d');
            const fractions=[.24,.42,.60,.78];
            outer: for(const fy of fractions) for(const fx of fractions){
              const x=Math.round(plot.width*fx),y=Math.round(plot.height*fy);
              const a=context.getImageData(x,y,1,1).data[3];
              if(a===0){
                alpha=a;
                plotPoint={x:plotRect.x+window.scrollX+(x/plot.width)*plotRect.width,
                  y:plotRect.y+window.scrollY+(y/plot.height)*plotRect.height};
                break outer;
              }
            }
            if(!plotPoint){
              const x=Math.round(plot.width*.5),y=Math.round(plot.height*.5);
              alpha=context.getImageData(x,y,1,1).data[3];
              plotPoint={x:plotRect.x+window.scrollX+(x/plot.width)*plotRect.width,
                y:plotRect.y+window.scrollY+(y/plot.height)*plotRect.height};
            }
          } catch (_) {}
        }
        if(!plotPoint && plotRect) plotPoint={x:plotRect.x+window.scrollX+plotRect.width*.5,
          y:plotRect.y+window.scrollY+plotRect.height*.65};
        const frame=node.closest('.cui-studio-preview-frame');
        const panelStyle=getComputedStyle(panel);
        return {
          chartTheme:node.getAttribute('data-chart-theme'),
          localThemeScope:frame?.getAttribute('data-theme')||null,
          effectiveSurfaceTheme:frame && ['light','dark'].includes(frame.dataset.theme)?frame.dataset.theme:
            (document.documentElement.dataset.theme==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):(document.documentElement.dataset.theme||'light')),
          panelBackground:panelStyle.backgroundColor,
          panelSurfaceVariable:panelStyle.getPropertyValue('--cui-surface').trim(),
          plotBackground:plot?getComputedStyle(plot).backgroundColor:null,
          title:panel.querySelector('.cui-chart-panel__title')?.innerText||panel.getAttribute('aria-label')||'',
          toolbarLabels:[...panel.querySelectorAll('.cui-chart-toolbar button[aria-label]')].map(button=>button.getAttribute('aria-label')),
          geometry:{x:panelRect.x+window.scrollX,y:panelRect.y+window.scrollY,width:panelRect.width,height:panelRect.height},
          surfacePoint:{x:panelRect.x+window.scrollX+8,y:panelRect.y+window.scrollY+8},
          plotPoint,plotBox,canvasAlphaAtPlotPoint:alpha,canvasSize,
          chartRootTag:node.tagName,
        };
      });
      const body=getComputedStyle(document.body);
      const root=getComputedStyle(document.documentElement);
      const frame=document.querySelector('.cui-studio-preview-frame');
      const rootThemeAttribute=document.documentElement.dataset.theme||'';
      const prefersDark=matchMedia('(prefers-color-scheme: dark)').matches;
      const resolvedTheme=rootThemeAttribute==='system'?(prefersDark?'dark':'light'):rootThemeAttribute;
      return {
        requestedControl:document.querySelector('button[aria-label^="Appearance theme:"]')?.getAttribute('aria-label')||null,
        rootThemeAttribute,
        resolvedTheme,
        prefersDark,
        bodyDark:document.body.classList.contains('body--dark'),
        bodyBackground:body.backgroundColor,
        rootBackground:root.backgroundColor,
        rootSurfaceVariable:root.getPropertyValue('--cui-surface').trim(),
        frameTheme:frame?.getAttribute('data-theme')||null,
        frameSurfaceVariable:frame?getComputedStyle(frame).getPropertyValue('--cui-surface').trim():null,
        pageTitle:document.querySelector('h1')?.innerText||document.title,
        chartCount:charts.length,
        charts,
      };
    }""")


def _with_pixels(snapshot: dict[str, Any], screenshot: bytes) -> dict[str, Any]:
    image = Image.open(io.BytesIO(screenshot)).convert('RGB')
    for chart in snapshot['charts']:
        surface_point = chart.get('surfacePoint')
        if surface_point:
            x = min(image.width - 1, max(0, round(surface_point['x'])))
            y = min(image.height - 1, max(0, round(surface_point['y'])))
            chart['surfacePixel'] = list(image.getpixel((x, y)))
        else:
            chart['surfacePixel'] = None
        plot_point = chart.get('plotPoint')
        if plot_point:
            x = min(image.width - 1, max(0, round(plot_point['x'])))
            y = min(image.height - 1, max(0, round(plot_point['y'])))
            chart['plotPixelSample'] = list(image.getpixel((x, y)))
            chart['plotPixelSamplePoint'] = {'x': x, 'y': y}
        else:
            chart['plotPixelSample'] = None
            chart['plotPixelSamplePoint'] = None
        box = chart.get('plotBox')
        if box and box['width'] > 2 and box['height'] > 2:
            # ECharts canvas is transparent and SVG spatial panels can contain
            # categorical/data colors. The dominant interior pixel represents
            # the plot background; retain a point sample above for auditability.
            left = min(image.width - 1, max(0, round(box['x'] + box['width'] * .12)))
            right = min(image.width, max(left + 1, round(box['x'] + box['width'] * .88)))
            top = min(image.height - 1, max(0, round(box['y'] + box['height'] * .12)))
            bottom = min(image.height, max(top + 1, round(box['y'] + box['height'] * .88)))
            crop = image.crop((left, top, right, bottom))
            step_x = max(1, crop.width // 32)
            step_y = max(1, crop.height // 32)
            colors = Counter(
                crop.getpixel((x, y))
                for y in range(step_y // 2, crop.height, step_y)
                for x in range(step_x // 2, crop.width, step_x)
            )
            chart['plotPixel'] = list(colors.most_common(1)[0][0]) if colors else None
            surface = chart.get('surfacePixel')
            matching_surface = sum(
                count for color, count in colors.items()
                if surface and max(abs(color[channel] - surface[channel]) for channel in range(3)) <= 12
            )
            chart['plotPixelProbe'] = {
                'method': 'dominant-interior-rgb',
                'sample_count': sum(colors.values()),
                'dominant_fraction': colors.most_common(1)[0][1] / sum(colors.values()) if colors else 0,
                'surface_match_fraction': matching_surface / sum(colors.values()) if colors else 0,
                'crop': {'x': left, 'y': top, 'width': right - left, 'height': bottom - top},
            }
            chart['plotSurfaceMatchFraction'] = matching_surface / sum(colors.values()) if colors else 0
        else:
            chart['plotPixel'] = chart['plotPixelSample']
            chart['plotPixelProbe'] = {'method': 'point-sample-fallback', 'sample_count': 1}
            chart['plotSurfaceMatchFraction'] = 0
        chart.pop('surfacePoint', None)
        chart.pop('plotPoint', None)
        chart.pop('plotBox', None)
    return snapshot


def _luminance(rgb: list[int]) -> float:
    return .2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2]


def _chart_is_coherent(chart: dict[str, Any]) -> bool:
    mode = chart['effectiveSurfaceTheme']
    surface_pixel = chart.get('surfacePixel')
    plot_pixel = chart.get('plotPixel')
    if chart['chartTheme'] != mode or not surface_pixel or not plot_pixel:
        return False
    surface_luma = _luminance(surface_pixel)
    plot_luma = _luminance(plot_pixel)
    surface_matches_mode = surface_luma < 128 if mode == 'dark' else surface_luma > 200
    plot_matches_mode = plot_luma < 128 if mode == 'dark' else plot_luma > 200
    background_matches = chart.get('plotSurfaceMatchFraction', 0) >= .08
    return surface_matches_mode and (plot_matches_mode or background_matches)


def _capture_route(page: Page, *, base_url: str, surface: str, route: str,
                   preference: str, source_key: str, screenshot_path: Path) -> dict[str, Any]:
    url = base_url + route
    response = page.goto(url, wait_until='domcontentloaded', timeout=45000)
    if response is None or response.status != 200:
        raise AssertionError(f'route returned {response.status if response else "no response"}: {route}')
    _select_appearance(page, preference, base_url)
    expected_mode = 'dark' if source_key in {'explicit-dark', 'system-dark'} else preference
    try:
        page.wait_for_function(
            """expected => {
              const requested=document.documentElement.dataset.theme||'';
              const resolved=requested==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):requested;
              return resolved===expected;
            }""",
            arg=expected_mode,
            timeout=15000,
        )
    except Exception as exc:
        context = page.evaluate("""() => ({url:location.href,rootTheme:document.documentElement.dataset.theme||null,
          bodyClasses:document.body.className,title:document.title,text:document.body.innerText.slice(0,500)})""")
        raise AssertionError(f'theme did not resolve on {route}: expected={expected_mode}, context={context}') from exc
    _settle_charts(page, expected_mode)
    snapshot = _browser_snapshot(page)
    if source_key == 'explicit-dark':
        if snapshot['requestedControl']:
            if snapshot['requestedControl'] != 'Appearance theme: Dark':
                raise AssertionError(f'explicit Dark preference was not selected on {route}: {snapshot["requestedControl"]}')
            request_evidence = 'appearance-control'
        else:
            if snapshot['prefersDark'] or snapshot['resolvedTheme'] != 'dark':
                raise AssertionError(f'explicit Dark did not resolve Dark under browser Light on {route}')
            request_evidence = 'settings-selection; browser-Light/resolved-Dark'
    elif source_key == 'system-dark':
        if snapshot['requestedControl']:
            if snapshot['requestedControl'] != 'Appearance theme: System':
                raise AssertionError(f'System preference was not selected on {route}: {snapshot["requestedControl"]}')
            request_evidence = 'appearance-control'
        else:
            if not snapshot['prefersDark'] or snapshot['resolvedTheme'] != 'dark':
                raise AssertionError(f'System preference did not resolve Dark under browser Dark on {route}')
            request_evidence = 'settings-selection; browser-Dark/resolved-Dark'
    if not snapshot['charts']:
        raise AssertionError(f'no rendered chart theme nodes on {route}')
    screenshot = page.screenshot(path=str(screenshot_path), full_page=True, animations='disabled')
    snapshot = _with_pixels(snapshot, screenshot)
    failures = [chart for chart in snapshot['charts'] if not _chart_is_coherent(chart)]
    return {
        'surface_key': surface,
        'route': route,
        'route_status': response.status,
        'preference_source': source_key,
        'requested_theme': preference,
        'requested_theme_evidence': request_evidence,
        'resolved_theme': snapshot['resolvedTheme'],
        'root_theme_attribute': snapshot['rootThemeAttribute'],
        'state_identity': f'{route} · {source_key} · 1440x900@1',
        'page_title': snapshot['pageTitle'],
        'body_dark': snapshot['bodyDark'],
        'body_background': snapshot['bodyBackground'],
        'root_background': snapshot['rootBackground'],
        'root_surface_variable': snapshot['rootSurfaceVariable'],
        'frame_theme': snapshot['frameTheme'],
        'frame_surface_variable': snapshot['frameSurfaceVariable'],
        'chart_count': snapshot['chartCount'],
        'charts': snapshot['charts'],
        'screenshot': screenshot_path.relative_to(screenshot_path.parents[2]).as_posix(),
        'screenshot_sha256': _sha256(screenshot),
        'coherent': not failures,
        'coherence_failure_count': len(failures),
        'coherence_failures': [
            {'title': chart['title'], 'chart_theme': chart['chartTheme'],
             'surface_theme': chart['effectiveSurfaceTheme'], 'surface_pixel': chart.get('surfacePixel'),
             'plot_pixel': chart.get('plotPixel'), 'plot_surface_match_fraction': chart.get('plotSurfaceMatchFraction')}
            for chart in failures
        ],
    }


def _select_local_preview_theme(page: Page, local_theme: str) -> None:
    fields = page.locator('.cui-studio-preview-controls .q-field')
    if fields.count() < 2:
        raise AssertionError('specimen theme control is not present on the representative analytics route')
    fields.nth(1).click()
    page.get_by_role('option', name=local_theme.title(), exact=True).last.click()
    page.wait_for_function(
        'theme => document.querySelector(".cui-studio-preview-frame")?.dataset.theme===theme',
        arg=local_theme,
        timeout=10000,
    )
    page.wait_for_function(
        'theme => [...document.querySelectorAll("[data-chart-theme]")].length>0 && [...document.querySelectorAll("[data-chart-theme]")].every(node=>node.dataset.chartTheme===theme)',
        arg=local_theme,
        timeout=10000,
    )
    page.wait_for_timeout(250)


def _run_local_scope_regression(page: Page, base_url: str) -> dict[str, Any]:
    response = page.goto(base_url + '/analytics/spc_i_mr', wait_until='domcontentloaded', timeout=45000)
    if response is None or response.status != 200:
        raise AssertionError('local theme scope route failed to load')
    _select_appearance(page, 'dark', base_url)
    page.wait_for_function("document.documentElement.dataset.theme==='dark'")
    _select_local_preview_theme(page, 'light')
    observations = []
    for global_mode in ('light', 'dark'):
        _select_appearance(page, global_mode, base_url)
        page.wait_for_function(
            'mode => document.documentElement.dataset.theme===mode',
            arg=global_mode,
            timeout=10000,
        )
        page.wait_for_function(
            """() => [...document.querySelectorAll('[data-chart-theme]')].length>0
              && [...document.querySelectorAll('[data-chart-theme]')].every(node=>node.dataset.chartTheme==='light')""",
            timeout=10000,
        )
        _settle_charts(page, 'light')
        screenshot = page.screenshot(full_page=True, animations='disabled')
        snapshot = _with_pixels(_browser_snapshot(page), screenshot)
        if snapshot['frameTheme'] != 'light' or not all(_chart_is_coherent(chart) for chart in snapshot['charts']):
            raise AssertionError(f'global {global_mode} forced a conflict with the local Light preview: {snapshot}')
        observations.append({
            'global_resolved_theme': global_mode,
            'frame_theme': snapshot['frameTheme'],
            'chart_themes': sorted({chart['chartTheme'] for chart in snapshot['charts']}),
            'panel_background': snapshot['charts'][0]['panelBackground'],
            'surface_pixel': snapshot['charts'][0]['surfacePixel'],
            'plot_pixel': snapshot['charts'][0]['plotPixel'],
            'coherent': True,
        })
    return {'status': 'PASS', 'observations': observations}


def _run_negative_control(page: Page, base_url: str) -> dict[str, Any]:
    response = page.goto(base_url + '/analytics/spc_i_mr', wait_until='domcontentloaded', timeout=45000)
    if response is None or response.status != 200:
        raise AssertionError('negative-control route failed to load')
    _select_appearance(page, 'dark', base_url)
    _settle_charts(page, 'dark')
    page.evaluate("""() => {
      const frame=document.querySelector('.cui-studio-preview-frame');
      if(!frame) throw new Error('preview theme scope is missing');
      frame.dataset.theme='light';
    }""")
    page.wait_for_function("getComputedStyle(document.querySelector('.cui-chart-panel')).backgroundColor==='rgb(255, 255, 255)'")
    snapshot = _with_pixels(_browser_snapshot(page), page.screenshot(full_page=True, animations='disabled'))
    detected = any(not _chart_is_coherent(chart) for chart in snapshot['charts'])
    if not detected:
        raise AssertionError('negative control failed to expose the simulated legacy mixed-theme state')
    chart = snapshot['charts'][0]
    return {
        'status': 'PASS_ORACLE_DETECTED_SIMULATED_REGRESSION',
        'simulated_scope': 'system preview resolved as Light beneath explicit global Dark',
        'resolved_global_theme': snapshot['resolvedTheme'],
        'local_scope_theme': snapshot['frameTheme'],
        'chart_theme': chart['chartTheme'],
        'panel_background': chart['panelBackground'],
        'surface_pixel': chart['surfacePixel'],
        'plot_pixel': chart['plotPixel'],
        'oracle_detected_incoherence': detected,
    }


def _comparison_markdown(records: list[dict[str, Any]]) -> str:
    by_key = {(row['surface_key'], row['preference_source']): row for row in records}
    lines = [
        '# CHG-203 chart theme comparison references',
        '',
        f'R1 audit authority: `{R1_ARTIFACT_COMMIT}`; immutable Fabric evidence commit: `{R1_EVIDENCE_COMMIT}`.',
        'Predecessor PNG bytes remain at their original Git paths and are referenced by commit and SHA256 only.',
        '',
        '| Surface | R1 predecessor evidence | Candidate explicit Dark | Candidate System-dark |',
        '| --- | --- | --- | --- |',
    ]
    for key, (name, digest) in R1_REFERENCES.items():
        explicit = by_key[(key, 'explicit-dark')]
        system = by_key[(key, 'system-dark')]
        predecessor = f'`{R1_EVIDENCE_COMMIT}:v3-audit/contact-sheets/{name}`<br>SHA256 `{digest}`'
        lines.append(
            f'| `{key}` | {predecessor} | `{explicit["screenshot"]}`<br>SHA256 `{explicit["screenshot_sha256"]}` | `{system["screenshot"]}`<br>SHA256 `{system["screenshot_sha256"]}` |'
        )
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f'refusing to overwrite non-empty evidence directory: {output}')
    output.mkdir(parents=True, exist_ok=True)
    screenshot_root = output / 'screenshots'
    screenshot_root.mkdir()
    candidate = _git(repo, 'rev-parse', 'HEAD')
    candidate_tree = _git(repo, 'rev-parse', 'HEAD^{tree}')
    parent = _git(repo, 'rev-parse', 'HEAD^')
    branch = _git(repo, 'branch', '--show-current')
    if branch != 'codex/nicegui-base-golden-ui-v3-explicit-dark-chart-canvas-fix-1':
        raise AssertionError(f'unexpected candidate branch: {branch}')
    if parent != '1bc15bbb197245e8a6367de9161dc7f63001b71a':
        raise AssertionError(f'candidate parent is not the requested exact base: {parent}')

    port = _free_port()
    base_url = f'http://127.0.0.1:{port}'
    env = os.environ.copy()
    env['PYTHONPATH'] = str(repo / 'source')
    server = subprocess.Popen(
        [sys.executable, str(repo / 'run_nicegui_base.py'), '--host', '127.0.0.1', '--port', str(port)],
        cwd=repo, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    records: list[dict[str, Any]] = []
    page_errors: list[dict[str, str]] = []
    console_errors: list[dict[str, str]] = []
    current = {'surface': 'startup', 'theme': 'startup'}
    try:
        _wait_for_server(server, port)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser_identity = {
                'engine': 'Chromium', 'version': browser.version,
                'executable': playwright.chromium.executable_path,
            }
            for source_key, preference, color_scheme in (
                ('explicit-dark', 'dark', 'light'),
                ('system-dark', 'system', 'dark'),
            ):
                context = browser.new_context(
                    viewport={'width': 1440, 'height': 900}, device_scale_factor=1, color_scheme=color_scheme,
                )
                context.add_init_script(
                    f"localStorage.setItem('nicegui_base_theme',{json.dumps(preference)});"
                    f"localStorage.setItem('cui_lab_theme',{json.dumps(preference)});"
                )
                page = context.new_page()
                browser_identity['user_agent'] = page.evaluate('navigator.userAgent')
                page.on('pageerror', lambda exc: page_errors.append({**current, 'error': str(exc)}))
                page.on('console', lambda msg: console_errors.append({**current, 'error': msg.text}) if msg.type == 'error' else None)
                for surface, route, category in SURFACES:
                    current.update(surface=surface, theme=source_key)
                    destination = screenshot_root / source_key
                    destination.mkdir(exist_ok=True)
                    screenshot_path = destination / f'{surface}.png'
                    page_error_start, console_error_start = len(page_errors), len(console_errors)
                    record = _capture_route(
                        page, base_url=base_url, surface=surface, route=route,
                        preference=preference, source_key=source_key, screenshot_path=screenshot_path,
                    )
                    record['category'] = category
                    record['viewport'] = {'width': 1440, 'height': 900, 'device_scale_factor': 1}
                    record['browser'] = browser_identity
                    record['page_errors'] = page_errors[page_error_start:]
                    record['console_errors'] = console_errors[console_error_start:]
                    records.append(record)
                if source_key == 'explicit-dark':
                    current.update(surface='local-theme-scope', theme=source_key)
                    scope_regression = _run_local_scope_regression(page, base_url)
                    current.update(surface='negative-control', theme=source_key)
                    negative_control = _run_negative_control(page, base_url)
                context.close()
            browser.close()
    finally:
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=10)

    manifest = {
        'schema_version': 1,
        'project': 'nicegui-base',
        'change': 'CHG-203',
        'request': 'golden-ui-v3-explicit-dark-chart-canvas-fix-1',
        'operation': 'FIX',
        'fabric_job': os.environ.get('CODEX_FABRIC_JOB_ID') or os.environ.get('FABRIC_JOB_ID') or 'CF-d597eb46581e1da3e7937cd7',
        'work_branch': branch,
        'candidate_sha': candidate,
        'candidate_tree': candidate_tree,
        'candidate_parent': parent,
        'target_branch': 'main',
        'target_artifact_ref': 'refs/heads/project-os-artifacts/nicegui-base/golden-ui-v3-explicit-dark-chart-canvas-fix-1',
        'fabric_evidence_ref': 'refs/heads/codex-fabric/evidence/nicegui-base/golden-ui-v3-explicit-dark-chart-canvas-fix-1',
        'browser': browser_identity,
        'server': {'entrypoint': 'python run_nicegui_base.py', 'http': '127.0.0.1', 'port': port, 'runtime': 'installed candidate source'},
        'matrix': {'viewport': '1440x900', 'device_scale_factor': 1, 'surface_count': 16, 'theme_sources': ['explicit-dark', 'system-dark'], 'expected_png_count': 32},
        'records': records,
        'local_theme_scope_regression': scope_regression,
        'negative_control': negative_control,
        'page_errors': page_errors,
        'console_errors': console_errors,
        'r1_predecessor': {
            'audit_artifact_commit': R1_ARTIFACT_COMMIT,
            'deterministic_evidence_commit': R1_EVIDENCE_COMMIT,
            'contact_sheets_referenced_only': True,
        },
        'status': 'PASS' if len(records) == 32 and all(row['coherent'] for row in records) and not page_errors and not console_errors and scope_regression['status'] == 'PASS' and negative_control['oracle_detected_incoherence'] else 'FAIL',
    }
    manifest_path = output / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    comparisons_path = output / 'comparisons.md'
    comparisons_path.write_text(_comparison_markdown(records), encoding='utf-8')
    files = sorted(path for path in output.rglob('*') if path.is_file())
    (output / 'SHA256SUMS.txt').write_text(
        ''.join(f'{_sha256(path.read_bytes())}  {path.relative_to(output).as_posix()}\n' for path in files),
        encoding='utf-8',
    )
    print(json.dumps({'status': manifest['status'], 'candidate_sha': candidate, 'candidate_tree': candidate_tree, 'records': len(records), 'png_count': len(list(screenshot_root.rglob('*.png'))), 'output': str(output), 'page_errors': page_errors, 'console_errors': console_errors}, indent=2))
    return 0 if manifest['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
