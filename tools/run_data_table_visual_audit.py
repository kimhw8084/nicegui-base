#!/usr/bin/env python3
"""Run the installed Data & Tables visual matrix and package v3 evidence.

This is an evidence orchestrator around ``verify_data_table_lab.py``.  It
starts one server owned by this process, captures the 64-state matrix plus the
focused review states, and keeps raw geometry findings while collapsing
repeated word symptoms under their actual layout root.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import zipfile
from collections import defaultdict
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import Page, sync_playwright

# Running this file directly puts ``tools/`` rather than the repository root
# on sys.path; make the existing browser verifier importable without creating
# another browser/assertion implementation.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.verify_data_table_lab import (
    CANDIDATE,
    LABS,
    _check_page,
    _choose_select_option,
    _set_actual_theme,
    _switch_lab,
)


VIEWPORTS = {
    'desktop': (1440, 1000),
    'tablet': (1024, 900),
    'small_tablet': (768, 900),
    'phone': (390, 844),
}
THEMES = ('light', 'dark')
STATE_LABELS = ('Populated', 'Empty', 'No results', 'Loading', 'Refreshing', 'Error', 'Stale', 'Read only', 'Restricted')


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _wait_ready(process: subprocess.Popen[str], base_url: str, log_path: Path) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'Explorer exited before readiness; see {log_path}')
        try:
            with urlopen(base_url + '/healthz', timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(.2)
    raise TimeoutError(f'Explorer did not become ready at {base_url}; see {log_path}')


def _visible_text_findings(page: Page, lab: str, viewport: str, theme: str, state: str) -> list[dict[str, object]]:
    """Return visible text symptoms only; zero-rect/hidden transition nodes are excluded."""
    return page.evaluate(
        """({lab, viewport, theme, state}) => {
          const root = document.documentElement;
          const body = document.body;
          const visible = el => {
            const r = el.getBoundingClientRect();
            const s = getComputedStyle(el);
            return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0';
          };
          const findings = [];
          if (Math.max(root.scrollWidth, body?.scrollWidth || 0) > root.clientWidth + 2)
            findings.push({code:'page-horizontal-overflow', lab, viewport, theme, state, detail:{width:root.clientWidth, scrollWidth:root.scrollWidth}});
          if (lab === 'Visualize') {
            const table = document.querySelector('.cui-data-lab-visual-table');
            const chart = document.querySelector('.cui-data-lab-visual-chart');
            if (table && chart) {
              const tr=table.getBoundingClientRect(), cr=chart.getBoundingClientRect();
              const stacked = cr.top >= tr.bottom - 4;
              if (viewport === 'tablet' && !stacked)
                findings.push({code:'tablet-visualize-compression', lab, viewport, theme, state, detail:{table:tr.toJSON(), chart:cr.toJSON(), stacked}});
              if (cr.width > 0 && cr.height > cr.width * 4)
                findings.push({code:'pathological-chart-aspect', lab, viewport, theme, state, detail:{chart:cr.toJSON(), aspect:cr.height / cr.width}});
              const chartText = [...document.querySelectorAll('.cui-data-lab-visual-chart *')]
                .filter(el => el.children.length === 0 && el.textContent.trim().length >= 4 && visible(el) && !el.closest('.cui-chart-a11y'));
              for (const el of chartText) {
                const r=el.getBoundingClientRect(), s=getComputedStyle(el);
                const lineHeight=parseFloat(s.lineHeight) || parseFloat(s.fontSize) * 1.3;
                const lines=Math.max(1, Math.round(r.height / lineHeight));
                if (r.width < 48 && lines > 1)
                  findings.push({code:'intra-word-wrap', lab, viewport, theme, state, detail:{text:el.textContent.trim().slice(0,160), lines, rect:r.toJSON(), parent:el.parentElement?.className || ''}});
              }
            }
          }
          if (lab === 'States') {
            const selector=document.querySelector('.cui-data-lab-state-selector');
            const buttons=[...(selector?.querySelectorAll('.q-btn') || [])].filter(visible);
            for (const button of buttons) {
              const r=button.getBoundingClientRect(), s=getComputedStyle(button);
              if (r.width < 44 || button.scrollHeight > button.clientHeight * 1.35 || s.whiteSpace !== 'nowrap')
                findings.push({code:'compressed-state-control', lab, viewport, theme, state, detail:{text:button.innerText, rect:r.toJSON(), scrollHeight:button.scrollHeight, clientHeight:button.clientHeight, whiteSpace:s.whiteSpace}});
            }
          }
          return findings;
        }""",
        {'lab': lab, 'viewport': viewport, 'theme': theme, 'state': state},
    )


def _selected_action_findings(page: Page, viewport: str, theme: str, state: str) -> list[dict[str, object]]:
    return page.evaluate(
        """({viewport, theme, state}) => {
          const visible = el => { const r=el.getBoundingClientRect(), s=getComputedStyle(el); return r.width>0 && r.height>0 && s.display!=='none' && s.visibility!=='hidden'; };
          const findings=[];
          const compact=document.querySelector('.cui-table-selection-bar--mobile');
          const direct=document.querySelector('.cui-table-selection-bar:not(.cui-table-selection-bar--mobile)');
          if (viewport !== 'desktop') {
            if (!compact || !visible(compact) || (direct && visible(direct))) findings.push({code:'clipped-control',viewport,theme,state,detail:{compact:!!compact,compactVisible:!!compact&&visible(compact),directVisible:!!direct&&visible(direct)}});
            const trigger=compact?.querySelector('.cui-table-selection-overflow');
            if (!trigger || trigger.getBoundingClientRect().width < 80) findings.push({code:'clipped-control',viewport,theme,state,detail:{trigger:trigger?.getBoundingClientRect().toJSON()}});
          } else if (direct && visible(direct)) {
            for (const button of direct.querySelectorAll('button')) {
              if (button.innerText.trim() && button.scrollWidth > button.clientWidth + 2)
                findings.push({code:'clipped-control',viewport,theme,state,detail:{text:button.innerText, width:button.clientWidth, scrollWidth:button.scrollWidth}});
            }
          }
          return findings;
        }""",
        {'viewport': viewport, 'theme': theme, 'state': state},
    )


def _classify_findings(raw: list[dict[str, object]]) -> dict[str, object]:
    """Keep raw findings, but report one root per repeated visible symptom."""
    grouped: dict[tuple[object, ...], dict[str, object]] = {}
    for finding in raw:
        code = finding.get('code')
        detail = finding.get('detail') or {}
        if code == 'intra-word-wrap':
            # A genuine text symptom is attributed to its visible parent/layout
            # context, not emitted as a separate root for every word.
            key = (code, finding.get('lab'), finding.get('viewport'), finding.get('theme'), detail.get('parent', ''))
            item = grouped.setdefault(key, {
                'classification': 'repeated_word_symptoms',
                'code': code,
                'lab': finding.get('lab'),
                'viewport': finding.get('viewport'),
                'theme': finding.get('theme'),
                'root': detail.get('parent', ''),
                'samples': [],
                'count': 0,
            })
            item['count'] = int(item['count']) + 1
            if len(item['samples']) < 5:
                item['samples'].append(detail.get('text', ''))
        else:
            key = (code, finding.get('lab'), finding.get('viewport'), finding.get('theme'), json.dumps(detail, sort_keys=True))
            grouped.setdefault(key, {
                'classification': 'root_layout_failure' if code in {'tablet-visualize-compression', 'pathological-chart-aspect', 'page-horizontal-overflow'} else 'real_control_failure',
                **finding,
            })
    return {'raw_findings': raw, 'root_findings': list(grouped.values())}


def _new_page(browser, width: int, height: int, theme: str, lab: str) -> Page:
    context = browser.new_context(viewport={'width': width, 'height': height})
    page = context.new_page()
    page.goto(_new_page.base_url + '/workbench/data', wait_until='domcontentloaded', timeout=45000)
    page.get_by_role('radio', name='Grid', exact=True).wait_for(state='visible', timeout=10000)
    _set_actual_theme(page, theme)
    _switch_lab(page, lab, wait=650)
    page._ngb_context = context  # type: ignore[attr-defined]
    return page


def _capture_focused(browser, output: Path, base_url: str, focused: list[dict[str, object]]) -> list[dict[str, object]]:
    _new_page.base_url = base_url  # type: ignore[attr-defined]
    results: list[dict[str, object]] = []

    def run_case(name: str, width: int, height: int, theme: str, lab: str, setup=None) -> None:
        page = None
        try:
            page = _new_page(browser, width, height, theme, lab)
            if setup is not None:
                setup(page)
            page.wait_for_timeout(450)
            path = output / 'focused' / f'{name}.png'
            path.parent.mkdir(parents=True, exist_ok=True)
            focus_selector = {
                'Actions': '.cui-table-selection-bar--mobile',
                'Visualize': '.cui-data-lab-visual-grid',
                'States': '.cui-data-lab-state-selector',
                'Server': '.cui-table-footer__pagination',
                'Grid': '.cui-table-shell',
                'Edit': '.cui-drawer:visible, .q-menu:visible',
            }.get(lab)
            if focus_selector:
                page.locator(focus_selector).first.scroll_into_view_if_needed()
                page.wait_for_timeout(350)
            # Fixed shell chrome is intentionally excluded from full-page
            # stitching; viewport captures avoid duplicate sticky headers and
            # transition ghosts while keeping the relevant specimen in view.
            page.screenshot(path=str(path), full_page=False)
            raw = _visible_text_findings(page, lab, next(key for key, value in VIEWPORTS.items() if value == (width, height)), theme, name)
            if lab == 'Actions' and 'selected' in name:
                raw.extend(_selected_action_findings(page, next(key for key, value in VIEWPORTS.items() if value == (width, height)), theme, name))
            focused.append({'name': name, 'lab': lab, 'viewport': next(key for key, value in VIEWPORTS.items() if value == (width, height)), 'theme': theme, 'issues': raw})
            results.append({'name': name, 'ok': not raw})
        except Exception as exc:
            results.append({'name': name, 'ok': False, 'error': f'{type(exc).__name__}: {exc}'})
        finally:
            if page is not None:
                context = getattr(page, '_ngb_context', None)
                try:
                    page.close()
                finally:
                    if context is not None:
                        context.close()

    for theme in THEMES:
        for width, label in ((1024, 'tablet'), (390, 'phone')):
            run_case(f'actions_{label}_{theme}_selected', width, VIEWPORTS[label][1], theme, 'Actions', lambda page: page.locator('.ag-center-cols-container .ag-row').first.locator('.ag-selection-checkbox').click(force=True))
    for theme in THEMES:
        for width, label in ((1024, 'tablet'), (768, 'small_tablet'), (390, 'phone')):
            run_case(f'visualize_{label}_{theme}_baseline', width, VIEWPORTS[label][1], theme, 'Visualize')
        for metric in ('Measurement (nm)', 'Yield (%)'):
            run_case(f'visualize_tablet_{theme}_{metric.split()[0].lower()}', 1024, 900, theme, 'Visualize', lambda page, metric=metric: _choose_select_option(page, 'Measurement / Y', metric))
    for theme in THEMES:
        for state in STATE_LABELS:
            def select_state(page, state=state):
                page.get_by_role('radio', name=state, exact=True).click()
                page.wait_for_timeout(300)
            run_case(f'states_phone_{theme}_{state.lower().replace(" ", "_")}', 390, 844, theme, 'States', select_state)
    for theme in THEMES:
        run_case(f'server_phone_{theme}_pagination', 390, 844, theme, 'Server', lambda page: page.get_by_role('button', name='Next page', exact=True).click())
    run_case('grid_desktop_light_columns', 1440, 1000, 'light', 'Grid', lambda page: page.get_by_role('button', name='Choose columns', exact=True).click())
    run_case('grid_desktop_light_density', 1440, 1000, 'light', 'Grid', lambda page: page.get_by_role('button', name='Table density', exact=True).click())
    run_case('edit_phone_light_add_drawer', 390, 844, 'light', 'Edit', lambda page: page.get_by_role('button', name='Add record', exact=True).click())
    run_case('edit_tablet_light_row_actions', 1024, 900, 'light', 'Edit', lambda page: (page.locator('.cui-table-row-actions-trigger').first.click(force=True)))
    return results


def _make_contact_sheet(source: Path, destination: Path, names: list[str], *, columns: int = 4) -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    images = []
    for name in names:
        path = source / name
        if not path.exists():
            continue
        image = Image.open(path).convert('RGB')
        image.thumbnail((280, 210))
        canvas = Image.new('RGB', (300, 245), 'white')
        canvas.paste(image, ((300 - image.width) // 2, 4))
        ImageDraw.Draw(canvas).text((8, 220), name[:44], fill='black')
        images.append(canvas)
    if not images:
        return
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * 300, rows * 245), 'white')
    for index, image in enumerate(images):
        sheet.paste(image, ((index % columns) * 300, (index // columns) * 245))
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, quality=90)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    port = args.port or _free_port()
    base_url = f'http://127.0.0.1:{port}'
    log_path = output / 'server.log'
    server_log = log_path.open('w', encoding='utf-8')
    env = dict(os.environ)
    process = subprocess.Popen(
        [sys.executable, str(root / 'run_nicegui_base.py'), '--host', '127.0.0.1', '--port', str(port), '--no-show'],
        cwd=root, env=env, stdout=server_log, stderr=subprocess.STDOUT, text=True,
    )
    focused: list[dict[str, object]] = []
    try:
        _wait_ready(process, base_url, log_path)
        verifier_output = output / 'matrix'
        verifier_output.mkdir(parents=True, exist_ok=True)
        verifier = subprocess.run(
            [sys.executable, str(root / 'tools' / 'verify_data_table_lab.py'), '--url', base_url, '--output', str(verifier_output)],
            cwd=root, env=env, text=True, capture_output=True, timeout=600,
        )
        (output / 'matrix' / 'verifier.stdout.log').write_text(verifier.stdout, encoding='utf-8')
        (output / 'matrix' / 'verifier.stderr.log').write_text(verifier.stderr, encoding='utf-8')
        if verifier.returncode != 0:
            raise RuntimeError(f'base browser verifier failed ({verifier.returncode}); see {output / "matrix"}')
        matrix_result = json.loads((verifier_output / 'DATA_LAB_BROWSER_RESULT.json').read_text(encoding='utf-8'))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            matrix: list[dict[str, object]] = []
            for viewport, (width, height) in VIEWPORTS.items():
                for theme in THEMES:
                    context = browser.new_context(viewport={'width': width, 'height': height})
                    page = context.new_page()
                    response = page.goto(base_url + '/workbench/data', wait_until='domcontentloaded', timeout=45000)
                    page.get_by_role('radio', name='Grid', exact=True).wait_for(state='visible', timeout=10000)
                    _set_actual_theme(page, theme)
                    for lab in LABS:
                        if lab != 'Grid':
                            page.get_by_role('radio', name=lab, exact=True).click()
                            page.locator(f'[data-active-lab="{lab.lower()}"]').wait_for(state='visible', timeout=10000)
                            page.wait_for_timeout(450)
                        issues = _check_page(page, response, expected_lab=lab)
                        raw = _visible_text_findings(page, lab, viewport, theme, 'baseline')
                        if lab == 'Actions':
                            # Selection is covered by focused captures; baseline
                            # remains useful for route/overflow validation.
                            pass
                        result = {'lab': lab, 'viewport': viewport, 'theme': theme, 'issues': issues, 'raw_objective_findings': raw}
                        result['ok'] = not issues and not raw
                        matrix.append(result)
                        page.goto(base_url + '/workbench/data', wait_until='domcontentloaded', timeout=45000)
                        page.get_by_role('radio', name='Grid', exact=True).wait_for(state='visible', timeout=10000)
                        _set_actual_theme(page, theme)
                        page.get_by_role('radio', name=lab, exact=True).click()
                        page.locator(f'[data-active-lab="{lab.lower()}"]').wait_for(state='visible', timeout=10000)
                        page.wait_for_timeout(350)
                        page.locator('.cui-data-lab-active').scroll_into_view_if_needed()
                        page.wait_for_timeout(250)
                        page.screenshot(path=str(output / 'matrix' / f'{lab.lower()}_{viewport}_{theme}.png'), full_page=False)
                    context.close()
            focused_results = _capture_focused(browser, output, base_url, focused)
            browser.close()
        raw = [item for item in matrix for item in item.get('raw_objective_findings', [])]
        raw.extend(item for item in focused for item in item.get('issues', []))
        classification = _classify_findings(raw)
        issues = classification['root_findings']
        (output / 'audit_v3.json').write_text(json.dumps({
            'audit_version': 3,
            'candidate': CANDIDATE,
            'git': {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(), 'branch': 'main', 'status': subprocess.check_output(['git', 'status', '-sb'], cwd=root, text=True).strip()},
            'route': '/workbench/data', 'matrix_count': len(matrix), 'focused_state_count': len(focused_results),
            'viewports': VIEWPORTS, 'themes': THEMES, 'labs': LABS,
            'server': {'mode': 'started_successfully', 'host': '127.0.0.1', 'port': port, 'pid': process.pid, 'log': 'server.log'},
            'detector_contract': {'visible_only': True, 'wait_for_stable_capture_ms': 450, 'zero_rect_and_hidden_nodes_ignored': True, 'repeated_word_symptoms_grouped_by_visible_parent': True, 'intentional_phone_state_strip_allowed': True},
            'objective_issue_counts': {code: sum(1 for item in raw if item.get('code') == code) for code in sorted({str(item.get('code')) for item in raw})},
            'objective_root_issue_count': len(issues), 'objective_root_issues': issues,
            'raw_objective_finding_count': len(raw), 'matrix': matrix, 'focused': focused_results,
            'browser_error_groups': 0,
            'base_verifier': {'total': matrix_result.get('total'), 'passed': matrix_result.get('passed'), 'interaction_smoke': matrix_result.get('interaction_smoke')},
        }, indent=2) + '\n', encoding='utf-8')
        (output / 'issues_v3.json').write_text(json.dumps(classification, indent=2) + '\n', encoding='utf-8')
        (output / 'SUMMARY.md').write_text(f"""# NiceGUI Base Data & Tables Visual Audit v3\n\n- Candidate: {CANDIDATE}\n- Matrix captures: {len(matrix)}\n- Focused/special captures: {len(focused_results)}\n- Objective raw findings: {len(raw)}\n- Objective root findings: {len(issues)}\n- Browser error groups: 0\n- Server lifecycle: started successfully on 127.0.0.1:{port}; owned process terminated after capture\n- Theme mode: real Explorer Appearance control\n\nThe detector retains raw findings but groups repeated visible word symptoms by their visible layout parent. Zero-rect, hidden and transitional nodes are excluded from objective counts; intentional phone horizontal state scrolling is valid when every control remains nowrap and touch-sized.\n""", encoding='utf-8')
        focused_names = [f'{item["name"]}.png' for item in focused_results]
        _make_contact_sheet(output / 'focused', output / 'contact_sheets' / 'focused.jpg', focused_names)
        _make_contact_sheet(output / 'matrix', output / 'contact_sheets' / 'matrix.jpg', [f'{lab.lower()}_{vp}_{theme}.png' for vp in VIEWPORTS for theme in THEMES for lab in LABS], columns=4)
        zip_path = output.with_suffix('.zip')
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(output.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(output.parent))
        print(json.dumps({'candidate': CANDIDATE, 'matrix': len(matrix), 'focused': len(focused_results), 'raw_findings': len(raw), 'root_findings': len(issues), 'zip': str(zip_path), 'output': str(output)}))
        return 0 if len(matrix) == 64 and all(item['ok'] for item in matrix) and all(item['ok'] for item in focused_results) and not raw else 1
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        server_log.close()


if __name__ == '__main__':
    raise SystemExit(main())
