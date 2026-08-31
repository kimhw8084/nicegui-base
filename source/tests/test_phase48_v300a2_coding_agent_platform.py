from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from nicegui_base import build_agent_context, run_agent_preflight
from nicegui_base.ai import GOLDEN_EXAMPLE_NAMES, install_ai_materials
from nicegui_base.ai.validator import validate_app, validate_python_file

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / 'nicegui_base' / 'ai' / 'templates' / 'golden'


def _codes(issues):
    return {item.code for item in issues}


def test_agent_context_routes_dashboard_and_analysis_tasks_deterministically():
    dashboard = build_agent_context('Build an executive dashboard with KPIs, trend chart and table')
    assert dashboard.dominant_pattern == 'dashboard'
    assert {'page_pattern', 'table', 'visualization', 'state_async'} <= {item.category for item in dashboard.recommendations}
    assert 'examples/nicegui_base/golden_dashboard.py' in dashboard.golden_examples

    workspace = build_agent_context('Build an RCA investigation workspace with filters, wafer chart, table and persisted state')
    assert workspace.dominant_pattern == 'analysis_workspace'
    assert {'engineering', 'visualization', 'table', 'state_async'} <= {item.category for item in workspace.recommendations}
    assert 'examples/nicegui_base/golden_analysis_workspace.py' in workspace.golden_examples


def test_agent_context_rejects_empty_task():
    import pytest
    with pytest.raises(ValueError):
        build_agent_context('   ')


def test_agent_scaffold_installs_versioned_golden_paths_and_guides(tmp_path):
    written = install_ai_materials(tmp_path)
    assert written
    assert (tmp_path / 'AGENTS.md').exists()
    assert (tmp_path / 'docs/nicegui_base/AGENT_WORKFLOW.md').exists()
    assert (tmp_path / 'docs/nicegui_base/OPENCODE_GEMMA_BOOTSTRAP.md').exists()
    for name in GOLDEN_EXAMPLE_NAMES:
        assert (tmp_path / 'examples/nicegui_base' / name).exists()
    manifest = json.loads((tmp_path / '.nicegui_base/install_manifest.json').read_text())
    assert manifest['agent_context_command'] == 'nicegui-base agent-context <task>'
    assert manifest['agent_check_command'] == 'nicegui-base agent-check .'
    assert len(manifest['golden_examples']) == 4


def test_golden_examples_are_zero_warning_nicegui_base_consumers():
    report = validate_app(GOLDEN)
    assert report.ok
    assert not report.warnings
    assert report.scanned_files == 5


def test_golden_nonrender_runtime_contracts_execute_without_nicegui():
    for name in ('golden_data_explorer.py', 'golden_analysis_workspace.py'):
        path = GOLDEN / name
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        if name == 'golden_data_explorer.py':
            session = module.make_session()
            assert session.metric('output') == 455
            session.close()
        else:
            runtime, workspace_id = module.build_runtime()
            assert workspace_id == 'investigation'
            diagnostics = runtime.diagnostics()
            assert diagnostics.active_workspaces == 1
            assert diagnostics.active_data_sessions == 1
            assert diagnostics.workspace_panels == 2


def test_agent_preflight_passes_fresh_scaffold_and_fails_stale_scaffold(tmp_path):
    install_ai_materials(tmp_path)
    (tmp_path / 'app.py').write_text('from nicegui_base import Icons\nICON = Icons.CHECK\n', encoding='utf-8')
    report = run_agent_preflight(tmp_path)
    assert report.passed

    install_manifest = tmp_path / '.nicegui_base/install_manifest.json'
    payload = json.loads(install_manifest.read_text())
    payload['framework_version'] = '0.0.0'
    install_manifest.write_text(json.dumps(payload), encoding='utf-8')
    stale = run_agent_preflight(tmp_path)
    assert not stale.passed
    assert any('does not match installed NiceGUI Base' in issue for issue in stale.issues)


def test_validator_warns_unowned_async_tasks_raw_props_and_renderer_internal_imports(tmp_path):
    path = tmp_path / 'pages' / 'bad.py'
    path.parent.mkdir()
    path.write_text(
        'import asyncio\n'
        'from nicegui_base.integrations.nicegui_components import Button\n'
        'async def run(coro, item):\n'
        '    asyncio.create_task(coro)\n'
        '    item.props("dense flat")\n',
        encoding='utf-8',
    )
    found = _codes(validate_python_file(path, root=tmp_path))
    assert {'AI015', 'AI016', 'AI017'} <= found


def test_agent_cli_context_init_and_check(tmp_path):
    init = subprocess.run(
        [sys.executable, '-m', 'nicegui_base.cli', 'agent-init', str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert init.returncode == 0, init.stderr
    assert (tmp_path / 'AGENTS.md').exists()

    context = subprocess.run(
        [sys.executable, '-m', 'nicegui_base.cli', 'agent-context', 'Build a CRUD page with table editing', '--format', 'json'],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert context.returncode == 0, context.stderr
    payload = json.loads(context.stdout)
    assert payload['dominant_pattern'] == 'crud'

    check = subprocess.run(
        [sys.executable, '-m', 'nicegui_base.cli', 'agent-check', str(tmp_path), '--format', 'json'],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert check.returncode == 0, check.stderr
    assert json.loads(check.stdout)['passed'] is True
