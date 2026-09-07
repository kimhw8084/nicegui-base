#!/usr/bin/env python3
"""Outcome-based D3 verifier for source, exports and the real browser workflow.

The browser portion reuses the D2 Workflow Check V3 helpers from the supplied
Downloads package in a temporary copy with only its D2 identity/title literals
advanced to D3. It never writes repository source or user state. A missing
NiceGUI/Playwright/Chromium environment is reported as NOT_RUN/BLOCKED and can
never become a passing result.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
from typing import Any
import zipfile


BUILD_ID = 'NGB-20260905-D3'
CHECKER_REVISION = 'D3-OUTCOME-V2'
DEFAULT_D2_TOOLING = Path.home() / 'Library/Mobile Documents/com~apple~CloudDocs/Downloads/nicegui_base_D2_workflow_check_v3'


SCHEMA = (
    {'name': 'id', 'inferred_type': 'string', 'role': 'identifier', 'nullable': False, 'confidence': 1.0},
    {'name': 'thickness', 'inferred_type': 'float', 'role': 'measurement', 'nullable': False, 'confidence': 1.0},
    {'name': 'batch', 'inferred_type': 'category', 'role': 'dimension', 'nullable': False, 'confidence': 1.0},
    {'name': 'note', 'inferred_type': 'string', 'role': 'attribute', 'nullable': False, 'confidence': 1.0},
)


def _rows(count: int = 257) -> list[dict[str, Any]]:
    return [
        {'id': f'{index:04d}', 'thickness': index + 0.125, 'batch': 'A' if index % 2 == 0 else 'B', 'note': 'alpha' if index < 2 else 'beta'}
        for index in range(count)
    ]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_hashes(repo: Path) -> dict[str, str]:
    package = repo / 'source/nicegui_base'
    return {
        path.relative_to(package).as_posix(): _sha(path)
        for path in sorted(package.rglob('*'))
        if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts
        and path.suffix in {'.py', '.json', '.svg', '.md', '.css', '.html', '.js'}
    }


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + '\n', encoding='utf-8')


def _run(command: list[str | Path], *, cwd: Path, env: dict[str, str] | None, log: Path, timeout: int) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w', encoding='utf-8') as stream:
        stream.write('Command arguments are omitted from this evidence log.\n')
        stream.flush()
        try:
            return subprocess.run([str(item) for item in command], cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            stream.write('\nPROCESS TIMEOUT\n')
            return 124


def _clean_env(*, source: Path | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    for key in tuple(environment):
        if key in {'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'VIRTUAL_ENV'} or key.startswith(('NICEGUI_', 'COMPANY_UI_')):
            environment.pop(key, None)
    environment.update(PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    if source is not None:
        environment['PYTHONPATH'] = str(source)
    return environment


def _record(report: dict[str, Any], name: str, status: str, *, detail: Any = None, **extra: Any) -> None:
    value: dict[str, Any] = {'status': status, 'passed': status == 'PASS'}
    if detail is not None:
        value['detail'] = detail
    value.update(extra)
    report['steps'][name] = value


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot load verifier helper: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check_archive(path: Path, *, expected_rows: int) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f'Missing generated archive: {path}')
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError(f'ZIP CRC failure: {path.name}')
        names = set(archive.namelist())
        required = {'app.py', 'bootstrap.py', '.nicegui_base/runtime_bundle.json', 'services/app_data.py'}
        missing = sorted(required - names)
        if missing:
            raise RuntimeError(f'{path.name} missing generated files: {missing}')
        lock = json.loads(archive.read('.nicegui_base/runtime_bundle.json'))
        if lock.get('build_id') != BUILD_ID:
            raise RuntimeError(f'{path.name} has build {lock.get("build_id")!r}, expected {BUILD_ID!r}')
        wheel_name = str(lock.get('wheel') or '')
        wheel = archive.read(wheel_name)
        if hashlib.sha256(wheel).hexdigest() != lock.get('wheel_sha256'):
            raise RuntimeError(f'{path.name} bundled wheel checksum mismatch')
        with zipfile.ZipFile(__import__('io').BytesIO(wheel)) as wheel_archive:
            identity = wheel_archive.read('nicegui_base/workbench/update_identity.py').decode('utf-8')
            wheel_metadata = wheel_archive.read(f'nicegui_base-{lock["framework_version"]}.dist-info/WHEEL').decode('utf-8')
            if BUILD_ID not in identity or 'runtime-bundle-D3' not in wheel_metadata:
                raise RuntimeError(f'{path.name} bundled provenance does not identify D3')
        contract = json.loads(archive.read('.nicegui_base/data_contract.json'))
        if contract.get('fixture_rows') != expected_rows or contract.get('measurement_field') != 'thickness':
            raise RuntimeError(f'{path.name} data contract lost the 257-row thickness mapping: {contract}')
        app_data = archive.read('services/app_data.py').decode('utf-8')
        home = archive.read('pages/home.py').decode('utf-8')
        if 'MEASUREMENT_FIELD' not in app_data or 'DATA_SCHEMA' not in app_data:
            raise RuntimeError(f'{path.name} has no generated semantic data contract')
        if 'measurement_field=MEASUREMENT_FIELD' not in home:
            raise RuntimeError(f'{path.name} page does not pass the measurement mapping')
        return {
            'sha256': _sha(path),
            'files': len(names),
            'build_id': lock['build_id'],
            'wheel_sha256': lock['wheel_sha256'],
            'verified_source_files': len(lock.get('source_sha256') or {}),
            'fixture_rows': contract['fixture_rows'],
            'measurement_field': contract['measurement_field'],
            'home_has_provider_context': 'AnalysisContext' in home and 'render_provider_capability' in home,
        }


def _static_checks(repo: Path, output: Path, report: dict[str, Any], python: Path) -> None:
    identity = (repo / 'source/nicegui_base/workbench/update_identity.py').read_text(encoding='utf-8')
    requirements = (repo / 'requirements.txt').read_text(encoding='utf-8')
    if BUILD_ID not in identity:
        raise RuntimeError(f'current source identity is not {BUILD_ID}')
    if 'nicegui==3.15.0' not in requirements:
        raise RuntimeError('requirements.txt does not retain exact nicegui==3.15.0')
    for relative, marker in {
        'source/nicegui_base/workbench/preview_data.py': 'def resolve_measurement_field',
        'source/nicegui_base/workbench/provider_preview.py': 'class ProviderQueryController',
        'source/nicegui_base/workbench/project_codegen.py': 'measurement_field=MEASUREMENT_FIELD',
        'source/nicegui_base/workbench/builder.py': 'def review_summary',
        'source/nicegui_base/integrations/nicegui_runtime.py': 'install_framework_theme',
        'run_development_D3.zsh': BUILD_ID,
    }.items():
        if marker not in (repo / relative).read_text(encoding='utf-8'):
            raise RuntimeError(f'{relative} lacks required D3 contract marker {marker!r}')
    _record(report, 'source_identity_and_contract', 'PASS', detail={'build_id': BUILD_ID, 'nicegui_pin': '3.15.0'})

    test_targets = [
        'source/tests/test_workbench_development_d3.py',
        'source/tests/test_workbench_development_d3_update.py',
    ]
    rc = _run([python, '-m', 'pytest', '-q', *test_targets], cwd=repo, env=_clean_env(source=repo / 'source'), log=output / 'TARGETED_TESTS.log', timeout=300)
    _record(report, 'targeted_d3_regressions', 'PASS' if rc == 0 else 'FAIL', returncode=rc, log='TARGETED_TESTS.log')
    if rc:
        raise RuntimeError('targeted D3 regressions failed; see TARGETED_TESTS.log')

    from nicegui_base.workbench.catalog_runtime import entries_by_key
    from nicegui_base.workbench.codegen import CapabilityConfiguration, generate_application_zip
    from nicegui_base.workbench.project_codegen import generate_project_zip

    rows = _rows()
    line_key = 'framework:visualizations:LineChart'
    table_key = 'framework:tables:data_table'
    search_key = 'component:search_input'
    select_key = 'component:select'
    studio_payload = generate_application_zip(
        entries_by_key()[line_key], app_name='D3 Studio Outcome',
        config=CapabilityConfiguration(title='D3 Studio Outcome', options={'measurement': 'thickness', 'label_field': 'id'}),
        rows=rows, data_schema=SCHEMA, data_mode='include_development_rows',
    )
    studio_path = output / 'synthetic_studio_export.zip'
    studio_path.write_bytes(studio_payload)
    studio_report = _check_archive(studio_path, expected_rows=257)
    project = {
        'name': 'D3 Builder Outcome', 'goal': 'Explore and filter semiconductor measurements',
        'pattern_key': 'data_explorer', 'data_rows': rows, 'data_schema': list(SCHEMA),
        'data_handoff_mode': 'include_development_rows',
        'placements': {'filters': [search_key, select_key], 'primary': [line_key], 'data': [table_key]},
        'capability_configurations': {
            line_key: {'title': 'D3 Studio Outcome', 'options': {'measurement': 'thickness', 'label_field': 'id'}},
            select_key: {'options': {'filter_field': 'batch'}},
        },
    }
    builder_payload, builder_smoke = generate_project_zip(project, entries_by_key())
    builder_path = output / 'synthetic_builder_export.zip'
    builder_path.write_bytes(builder_payload)
    builder_report = _check_archive(builder_path, expected_rows=257)
    if not builder_smoke.ok:
        raise RuntimeError(f'Builder generated-code smoke failed: {builder_smoke.findings}')
    report['synthetic_exports'] = {'studio': studio_report, 'builder': {**builder_report, 'smoke': builder_smoke.__dict__ if hasattr(builder_smoke, '__dict__') else str(builder_smoke)}}
    _record(report, 'synthetic_studio_and_builder_contracts', 'PASS', detail=report['synthetic_exports'])


DATA_PROBE = r'''
import asyncio, importlib.metadata as md, json, pathlib, sys
import nicegui_base
from nicegui_base.workbench.update_identity import BUILD_ID
assert BUILD_ID == 'NGB-20260905-D3'
assert md.version('nicegui') == '3.15.0'
app = pathlib.Path(sys.argv[1]).resolve()
assert pathlib.Path(nicegui_base.__file__).resolve().parent.parent == pathlib.Path(sys.prefix).resolve().joinpath('lib', 'python' + '.'.join(map(str, sys.version_info[:2]))) or pathlib.Path(sys.prefix).resolve() in pathlib.Path(nicegui_base.__file__).resolve().parents
sys.path.insert(0, str(app))
from services.app_data import CATEGORY_FIELD, DATA_SCHEMA, MEASUREMENT_FIELD, SOURCE, series_values
assert MEASUREMENT_FIELD == 'thickness', MEASUREMENT_FIELD
assert CATEGORY_FIELD in {'id', 'batch'}, CATEGORY_FIELD
async def read():
    return await SOURCE.query(__import__('nicegui_base').Query(limit=5000))
rows = asyncio.run(read()).rows
assert len(rows) == 257, len(rows)
assert rows[0]['id'] == '0000' and rows[-1]['id'] == '0256', rows[-1]
assert series_values()[0] == .125 and series_values()[-1] == 256.125
print(json.dumps({'passed': True, 'build_id': BUILD_ID, 'row_count': len(rows), 'measurement_field': MEASUREMENT_FIELD, 'category_field': CATEGORY_FIELD, 'series_endpoints': [series_values()[0], series_values()[-1]], 'framework_file': nicegui_base.__file__}))
'''


GEOMETRY_PROBE = r"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument('--url', required=True)
parser.add_argument('--route', default='/')
parser.add_argument('--mapping-url')
parser.add_argument('--mapping-route', default='/studio/framework%3Avisualizations%3ALineChart')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
report = {'passed': False, 'checks': [], 'page_errors': [], 'console_errors': [], 'screenshots': []}
args.output.mkdir(parents=True, exist_ok=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    for name, viewport, theme in (
        ('desktop_light', {'width': 1440, 'height': 1000}, 'light'),
        ('phone_light', {'width': 390, 'height': 844}, 'light'),
        ('desktop_dark', {'width': 1440, 'height': 1000}, 'dark'),
    ):
        context = browser.new_context(viewport=viewport)
        context.add_init_script(f"localStorage.setItem('nicegui_base_theme', {theme!r})")
        page = context.new_page()
        page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
        page.on('console', lambda message: report['console_errors'].append({'text': message.text, 'type': message.type}) if message.type == 'error' else None)
        try:
            if args.mapping_url:
                mapping_response = page.goto(args.mapping_url.rstrip('/') + args.mapping_route, wait_until='domcontentloaded', timeout=45000)
                assert mapping_response and mapping_response.status == 200
                expect(page.locator('.cui-alert').first).to_be_visible(timeout=30000)
                expect(page.locator('.cui-alert').first).to_contain_text('Choose one measurement field', timeout=30000)
                page.screenshot(path=str(args.output / (name + '_mapping_error.png')), full_page=True)
                report['screenshots'].append(name + '_mapping_error.png')
            response = page.goto(args.url.rstrip('/') + args.route, wait_until='domcontentloaded', timeout=45000)
            assert response and response.status == 200
            expect(page.locator('.cui-chart-data-disclosure summary').first).to_be_visible(timeout=30000)
            data_alternative = page.locator('.cui-chart-data-disclosure__scroll').first
            expect(data_alternative).to_contain_text('0.125', timeout=30000)
            page.wait_for_function('''() => {
                const host=document.querySelector('.cui-chart-canvas');
                const nodes=host ? [host,...host.querySelectorAll('*')] : [];
                const niceguiElement=host && typeof getElement === 'function' ? getElement(host.id?.slice(1)) : null;
                const vueElement=nodes.map(node => node.__vueParentComponent?.proxy).find(proxy => proxy?.chart?.getOption);
                const dom=nodes.find(node => node.getAttribute && node.getAttribute('_echarts_instance_'));
                const chart=vueElement?.chart || niceguiElement?.chart || (dom && window.echarts?.getInstanceByDom(dom));
                const series=chart?.getOption?.().series?.[0];
                return series?.data?.length === 257;
            }''', timeout=30000)
            chart_series = page.evaluate('''() => {
                const host=document.querySelector('.cui-chart-canvas');
                const nodes=host ? [host,...host.querySelectorAll('*')] : [];
                const niceguiElement=host && typeof getElement === 'function' ? getElement(host.id?.slice(1)) : null;
                const vueElement=nodes.map(node => node.__vueParentComponent?.proxy).find(proxy => proxy?.chart?.getOption);
                const dom=nodes.find(node => node.getAttribute && node.getAttribute('_echarts_instance_'));
                const chart=vueElement?.chart || niceguiElement?.chart || (dom && window.echarts?.getInstanceByDom(dom));
                const series=chart?.getOption?.().series?.[0];
                return series ? {name: series.name, data: (series.data || []).map(item => typeof item === 'object' && item !== null ? item.value : item)} : null;
            }''')
            assert chart_series and chart_series['name'] == 'Thickness', chart_series
            assert chart_series['data'][0] == 0.125 and chart_series['data'][-1] == 256.125, chart_series
            page.locator('.cui-chart-data-disclosure summary').first.focus()
            assert page.evaluate('document.activeElement?.closest(".cui-chart-data-disclosure") !== null')
            geometry = page.evaluate('''() => { const root=document.documentElement; const page=document.querySelector('.cui-page,.cui-workbench-page'); const disclosure=document.querySelector('.cui-chart-data-disclosure__scroll'); const r=page?.getBoundingClientRect(); const d=disclosure ? getComputedStyle(disclosure) : null; return {scrollWidth:root.scrollWidth,clientWidth:root.clientWidth, pageRight:r?.right ?? null, viewport:innerWidth, disclosureOverflow:d?.overflowY ?? null, disclosureMaxHeight:d?.maxHeight ?? null, theme:root.dataset.theme ?? null}; }''')
            assert geometry['scrollWidth'] <= geometry['clientWidth'] + 1, geometry
            assert geometry['pageRight'] is None or geometry['pageRight'] <= geometry['viewport'] + 1, geometry
            assert geometry['disclosureOverflow'] in {'auto', 'scroll'}, geometry
            assert geometry['disclosureMaxHeight'] not in {None, 'none'}, geometry
            if theme == 'dark':
                assert geometry['theme'] == 'dark', geometry
            page.screenshot(path=str(args.output / (name + '.png')), full_page=True)
            report['screenshots'].append(name + '.png')
            report['checks'].append({'name': name, 'passed': True, 'geometry': geometry})
        except Exception as exc:
            report['checks'].append({'name': name, 'passed': False, 'error': f'{type(exc).__name__}: {exc}'})
            try:
                page.screenshot(path=str(args.output / (name + '_FAIL.png')), full_page=True)
            except Exception:
                pass
        finally:
            context.close()
    browser.close()
report['passed'] = bool(report['checks']) and all(check['passed'] for check in report['checks']) and not report['page_errors'] and not report['console_errors']
(args.output / 'GEOMETRY_RESULT.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, sort_keys=True))
raise SystemExit(0 if report['passed'] else 1)
"""


def _d2_tooling(path: Path | None) -> Path | None:
    candidate = path or (Path(os.environ['NGB_D2_TOOLING']) if os.environ.get('NGB_D2_TOOLING') else DEFAULT_D2_TOOLING)
    candidate = candidate.expanduser().resolve()
    return candidate if (candidate / 'verify_D2_v3.py').is_file() and (candidate / 'verification/browser_workflow.py').is_file() else None


def _record_browser_runtime_block(report: dict[str, Any], detail: str) -> None:
    for name in (
        'd2_workflow_v3_replayed_as_d3',
        'presentation_geometry_theme_keyboard_and_overflow',
        'studio_independent_runtime_and_browser',
        'builder_independent_runtime_and_browser',
    ):
        _record(report, name, 'BLOCKED', detail=detail)
    report.setdefault('not_run_reasons', []).append(
        'Browser gates are BLOCKED because the independent NiceGUI/Playwright/Chromium runtime is unavailable: ' + detail
    )


def _browser_checks(repo: Path, output: Path, report: dict[str, Any], d2_path: Path) -> None:
    verification_path = d2_path / 'verification'
    sys.path.insert(0, str(verification_path))
    d2 = _load_script(d2_path / 'verify_D2_v3.py', 'd3_d2_workflow_helpers')
    with tempfile.TemporaryDirectory(prefix='nicegui-base-D3-browser-') as temporary:
        work = Path(temporary)
        helper_copy = work / 'verification'
        helper_copy.mkdir()
        for source in verification_path.glob('*.py'):
            target = helper_copy / source.name
            value = source.read_text(encoding='utf-8')
            if source.name in {'support.py', 'browser_workflow.py'}:
                value = value.replace('D2', 'D3')
            target.write_text(value, encoding='utf-8')
        browser_workflow = helper_copy / 'browser_workflow.py'
        try:
            python = d2.ready_python(repo, work, output)
            d2.browser_preflight(python, work, output)
        except (FileNotFoundError, OSError) as exc:
            _record_browser_runtime_block(report, f'{type(exc).__name__}: {exc}')
            return
        except RuntimeError as exc:
            detail = str(exc)
            if any(marker in detail for marker in (
                'Could not create the external test environment',
                'Dependency installation failed',
                'Chromium installation failed',
                'Chromium could not launch',
            )):
                _record_browser_runtime_block(report, f'{type(exc).__name__}: {detail}')
                return
            raise
        state = work / 'workbench_state'
        state.mkdir()
        environment = d2.clean_env(source=repo / 'source')
        environment['NICEGUI_BASE_STORAGE_SECRET'] = 'D3-verifier-' + 'x' * 48
        server_port = d2.port()
        base = f'http://127.0.0.1:{server_port}'
        process, stream = d2.launch(
            python,
            ['-m', 'nicegui_base.certification.live_lab_cli', '--host', '127.0.0.1', '--port', str(server_port)],
            cwd=state, env=environment, log=output / 'WORKBENCH_SERVER.log',
        )
        try:
            identity = d2.wait_json(base + '/_nicegui_base/workbench', process)
            if identity.get('build_id') != BUILD_ID or identity.get('ready') is not True:
                raise RuntimeError(f'Unexpected D3 Workbench identity/readiness: {identity}')
            report['workbench_identity'] = identity
            browser_output = output / 'workbench_browser'
            rc = d2.command(
                [python, browser_workflow, '--url', base, '--output', browser_output],
                cwd=work, env=d2.clean_env(), log=output / 'BROWSER_WORKFLOW.log', timeout=1500,
            )
            body = json.loads((browser_output / 'BROWSER_WORKFLOW.json').read_text(encoding='utf-8')) if (browser_output / 'BROWSER_WORKFLOW.json').is_file() else {}
            if rc or body.get('passed') is not True:
                _record(report, 'd2_workflow_v3_replayed_as_d3', 'FAIL', returncode=rc, workflow_report=body, log='BROWSER_WORKFLOW.log')
                raise RuntimeError(f'D3 replayed D2 workflow failed at {body.get("failed_step", "unknown")}')
            _record(report, 'd2_workflow_v3_replayed_as_d3', 'PASS', returncode=rc, workflow_report=body, log='BROWSER_WORKFLOW.log')

            # The D2 workflow intentionally exercises a table export. Use a
            # separate synthetic 257-row Builder export for the D3 chart
            # outcome so the browser assertion sees the real thickness series,
            # its bounded accessible data alternative, and the same provider
            # query path used by the generated application.
            from nicegui_base.workbench.catalog_runtime import entries_by_key
            from nicegui_base.workbench.project_codegen import generate_project_zip
            chart_key = 'framework:visualizations:LineChart'
            table_key = 'framework:tables:data_table'
            search_key = 'component:search_input'
            select_key = 'component:select'
            chart_project = {
                'name': 'D3 Presentation Chart',
                'goal': 'Explore and filter semiconductor measurements',
                'pattern_key': 'data_explorer',
                'data_rows': _rows(),
                'data_schema': list(SCHEMA),
                'data_handoff_mode': 'include_development_rows',
                'placements': {
                    'filters': [search_key, select_key],
                    'primary': [chart_key],
                    'data': [table_key],
                },
                'capability_configurations': {
                    chart_key: {'title': 'D3 Presentation Chart', 'options': {'measurement': 'thickness', 'label_field': 'id'}},
                    select_key: {'options': {'filter_field': 'batch'}},
                },
            }
            chart_payload, chart_smoke = generate_project_zip(chart_project, entries_by_key())
            if not chart_smoke.ok:
                raise RuntimeError(f'D3 presentation export smoke failed: {chart_smoke.findings}')
            chart_archive = output / 'presentation_chart_synthetic.zip'
            chart_archive.write_bytes(chart_payload)
            chart_app = work / 'presentation_chart_app'
            d2.safe_extract(chart_archive, chart_app)
            chart_port = d2.port()
            chart_base = f'http://127.0.0.1:{chart_port}'
            chart_environment = dict(environment)
            chart_environment.update(NICEGUI_BASE_HOST='127.0.0.1', NICEGUI_BASE_PORT=str(chart_port))
            chart_process, chart_stream = d2.launch(
                python, [chart_app / 'app.py'], cwd=chart_app, env=chart_environment,
                log=output / 'PRESENTATION_SERVER.log',
            )
            try:
                chart_health = d2.wait_json(chart_base + '/readyz', chart_process)
                if chart_health.get('ready') is not True:
                    raise RuntimeError(f'D3 presentation chart app is not ready: {chart_health}')
                geometry_script = work / 'geometry_probe.py'
                geometry_script.write_text(textwrap.dedent(GEOMETRY_PROBE), encoding='utf-8')
                geometry_output = output / 'presentation_geometry'
                geometry_rc = d2.command(
                    [python, geometry_script, '--url', chart_base, '--route', '/', '--mapping-url', base, '--output', geometry_output],
                    cwd=work, env=d2.clean_env(), log=output / 'PRESENTATION_GEOMETRY.log', timeout=240,
                )
                geometry_report = json.loads((geometry_output / 'GEOMETRY_RESULT.json').read_text(encoding='utf-8')) if (geometry_output / 'GEOMETRY_RESULT.json').is_file() else {}
                _record(report, 'presentation_geometry_theme_keyboard_and_overflow', 'PASS' if geometry_rc == 0 and geometry_report.get('passed') else 'FAIL', returncode=geometry_rc, chart_health=chart_health, geometry_report=geometry_report, log='PRESENTATION_GEOMETRY.log')
                if geometry_rc:
                    raise RuntimeError('D3 presentation geometry/browser checks failed')
            finally:
                report.setdefault('shutdown', {})['presentation'] = d2.stop(chart_process)
                chart_stream.close()

            for kind in ('studio', 'builder'):
                archive = browser_output / f'{kind}_included.zip'
                if not archive.is_file():
                    _record(report, kind + '_independent_runtime_and_browser', 'NOT_RUN', detail='The current browser workflow did not produce an eligible download.')
                    continue
                app = work / f'{kind}_independent_app'
                d2.safe_extract(archive, app)
                proof = output / f'{kind}_installed.json'
                setup_rc = d2.command([python, app / 'bootstrap.py', '--setup', '--check', '--output', proof], cwd=app, env=d2.clean_env(), log=output / f'{kind}_INSTALL.log', timeout=1800)
                if setup_rc or not proof.is_file():
                    _record(report, kind + '_independent_runtime_and_browser', 'FAIL', returncode=setup_rc, log=f'{kind}_INSTALL.log')
                    raise RuntimeError(f'{kind} independent install/provenance failed')
                installed = json.loads(proof.read_text(encoding='utf-8'))
                if installed.get('build_id') != BUILD_ID or not installed.get('passed'):
                    raise RuntimeError(f'{kind} independent provenance is not D3: {installed}')
                installed_python = app / '.venv/bin/python'
                probe_file = work / f'{kind}_data_probe.py'
                probe_file.write_text(textwrap.dedent(DATA_PROBE), encoding='utf-8')
                probe_rc = d2.command([installed_python, '-I', probe_file, app, kind], cwd=work, env=d2.clean_env(), log=output / f'{kind}_DATA_ADAPTER.log', timeout=120)
                if probe_rc:
                    _record(report, kind + '_independent_runtime_and_browser', 'FAIL', returncode=probe_rc, log=f'{kind}_DATA_ADAPTER.log', provenance=installed)
                    raise RuntimeError(f'{kind} installed app failed the 257-row semantic data probe')
                app_port = d2.port()
                app_base = f'http://127.0.0.1:{app_port}'
                app_process, app_stream = d2.launch(python, [app / 'bootstrap.py', '--run', '--port', str(app_port)], cwd=app, env=d2.clean_env(), log=output / f'{kind}_SERVER.log')
                try:
                    health = d2.wait_json(app_base + '/readyz', app_process)
                    if health.get('ready') is not True:
                        raise RuntimeError(f'{kind} generated app is not ready: {health}')
                    generated_output = output / f'{kind}_browser'
                    generated_rc = d2.command([python, browser_workflow, '--generated', kind, '--url', app_base, '--output', generated_output], cwd=work, env=d2.clean_env(), log=output / f'{kind}_BROWSER.log', timeout=240)
                    generated_report = json.loads((generated_output / 'BROWSER_WORKFLOW.json').read_text(encoding='utf-8')) if (generated_output / 'BROWSER_WORKFLOW.json').is_file() else {}
                    if generated_rc or generated_report.get('passed') is not True:
                        raise RuntimeError(f'{kind} generated browser check failed: {generated_report.get("error", "see report")}')
                    _record(report, kind + '_independent_runtime_and_browser', 'PASS', provenance=installed, health=health, generated_report=generated_report, log=f'{kind}_BROWSER.log')
                finally:
                    shutdown = d2.stop(app_process)
                    app_stream.close()
                    report.setdefault('shutdown', {})[kind] = shutdown
        except Exception as exc:
            if 'd2_workflow_v3_replayed_as_d3' not in report['steps']:
                _record(report, 'd2_workflow_v3_replayed_as_d3', 'BLOCKED', detail=f'{type(exc).__name__}: {exc}')
            report.setdefault('errors', []).append(f'{type(exc).__name__}: {exc}')
        finally:
            report['shutdown'] = {**report.get('shutdown', {}), 'workbench': d2.stop(process)}
            stream.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--output-parent', type=Path)
    parser.add_argument('--d2-tooling', type=Path)
    parser.add_argument('--skip-browser', action='store_true', help='Record browser/download gates as NOT_RUN; never reports an overall PASS.')
    args = parser.parse_args(argv)
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        parser.error('Use Python 3.11, 3.12, or 3.13.')
    repo = args.repo.expanduser().resolve()
    if args.output:
        output = args.output.expanduser().resolve()
        output.mkdir(parents=True, exist_ok=False)
    else:
        parent = (args.output_parent or Path.home() / 'Downloads').expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        output = parent / ('nicegui_base_D3_outcome_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + str(os.getpid()))
        output.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {
        'passed': False, 'status': 'RUNNING', 'build_id': BUILD_ID, 'checker_revision': CHECKER_REVISION,
        'repository_source_written': False, 'evidence_directory': str(output), 'steps': {}, 'errors': [],
        'scope': 'D3 semantic contract, 257-row Studio/Builder synthetic generation, D2 Workflow V3 replay, independent ZIP provenance, and presentation geometry when runtime access is available',
    }
    before = _source_hashes(repo)
    python = Path(os.environ.get('NICEGUI_BASE_PYTHON') or repo / '.venv/bin/python')
    if not python.is_file():
        python = Path(sys.executable)
    try:
        _static_checks(repo, output, report, python)
        d2_path = None if args.skip_browser else _d2_tooling(args.d2_tooling)
        if args.skip_browser:
            for name in ('d2_workflow_v3_replayed_as_d3', 'presentation_geometry_theme_keyboard_and_overflow', 'studio_independent_runtime_and_browser', 'builder_independent_runtime_and_browser'):
                _record(report, name, 'NOT_RUN', detail='Browser execution was explicitly skipped.')
        elif d2_path is None:
            for name in ('d2_workflow_v3_replayed_as_d3', 'presentation_geometry_theme_keyboard_and_overflow', 'studio_independent_runtime_and_browser', 'builder_independent_runtime_and_browser'):
                _record(report, name, 'NOT_RUN', detail='D2 Workflow Check V3 tooling was not found; set --d2-tooling to its directory.')
            report.setdefault('not_run_reasons', []).append('Browser workflow is NOT_RUN because D2 tooling is unavailable.')
        else:
            _browser_checks(repo, output, report, d2_path)
    except Exception as exc:
        report['errors'].append(f'{type(exc).__name__}: {exc}')
        report['status'] = 'FAIL'
    finally:
        after = _source_hashes(repo)
        changed = sorted({*before, *after} - {key for key in before if before.get(key) == after.get(key)})
        report['source_integrity'] = {'passed': not changed, 'changed_paths': changed}
        if changed:
            report['errors'].append('Repository source changed during verification; no local edit was reverted.')
        required = ('source_identity_and_contract', 'targeted_d3_regressions', 'synthetic_studio_and_builder_contracts', 'd2_workflow_v3_replayed_as_d3', 'presentation_geometry_theme_keyboard_and_overflow', 'studio_independent_runtime_and_browser', 'builder_independent_runtime_and_browser')
        report['passed'] = all(report['steps'].get(name, {}).get('passed') is True for name in required) and report['source_integrity']['passed'] and not report['errors']
        if report['passed']:
            report['status'] = 'PASS'
        elif report['errors']:
            report['status'] = 'FAIL'
        elif any(item.get('status') == 'BLOCKED' for item in report['steps'].values()):
            report['status'] = 'BLOCKED'
        elif report['status'] != 'FAIL':
            report['status'] = 'NOT_RUN' if any(item.get('status') in {'NOT_RUN', 'BLOCKED'} for item in report['steps'].values()) else 'FAIL'
        _dump(output / 'FINAL_RESULT.json', report)
        summary = f'D3_OUTCOME_VERIFY={report["status"]}\n' + '\n'.join(f'{name}: {step.get("status")}' for name, step in report['steps'].items())
        if report.get('not_run_reasons'):
            summary += '\n' + '\n'.join(report['not_run_reasons'])
        if report['errors']:
            summary += '\n' + '\n'.join(report['errors'])
        (output / 'SUMMARY.txt').write_text(summary + '\n', encoding='utf-8')
        print(summary)
        print('Evidence:', output)
    if report['status'] == 'PASS':
        return 0
    if report['status'] in {'NOT_RUN', 'BLOCKED'}:
        return 2
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
