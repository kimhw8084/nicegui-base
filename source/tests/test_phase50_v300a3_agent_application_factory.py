from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from nicegui_base.ai.gate import run_application_gate
from nicegui_base.ai.preflight import run_agent_preflight
from nicegui_base.ai.project import create_application
from nicegui_base.version import FRAMEWORK_VERSION

TEMPLATES = ('dashboard', 'data-explorer', 'crud', 'analysis-workspace', 'responsive-operations', 'async-workflow')


def _load_home(root: Path, template: str) -> None:
    path = root / 'pages' / 'home.py'
    module_name = f'_nicegui_base_dogfood_{template.replace("-", "_")}'
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    old = list(sys.path)
    try:
        sys.path.insert(0, str(root))
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old
    assert callable(module.build_page)


@pytest.mark.parametrize('template', TEMPLATES)
def test_all_agent_starters_are_validator_clean_and_importable(tmp_path: Path, template: str) -> None:
    root = tmp_path / template
    created = create_application(root, name=f'Dogfood {template}', template=template)
    assert created.framework_version == FRAMEWORK_VERSION
    assert (root / 'nicegui_base.toml').exists()
    assert (root / 'requirements.txt').read_text(encoding='utf-8') == f'nicegui-base=={FRAMEWORK_VERSION}\n'
    report = run_agent_preflight(root)
    assert report.passed, report.issues
    _load_home(root, template)


def test_application_gate_passes_generated_source_project(tmp_path: Path) -> None:
    root = tmp_path / 'dashboard'
    create_application(root, name='Gate Dogfood', template='dashboard')
    report = run_application_gate(root)
    assert report.passed, report.to_dict()
    assert {check.name for check in report.checks} == {'manifest', 'agent-preflight', 'dependency-pin', 'python-compile', 'entrypoint', 'build-page', 'tests'}


def test_release_gate_is_stricter_than_source_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / 'dashboard'
    create_application(root, name='Release Dogfood', template='dashboard')
    monkeypatch.setattr('nicegui_base.ai.gate._run_live_release_gate', lambda root: (False, 'target browser unavailable'))
    report = run_application_gate(root, release=True)
    assert not report.passed
    live = next(check for check in report.checks if check.name == 'live-uiux')
    assert live.status == 'FAIL'
    assert 'target browser unavailable' in live.detail


def test_create_refuses_nonempty_directory_without_explicit_overwrite(tmp_path: Path) -> None:
    root = tmp_path / 'existing'
    root.mkdir()
    (root / 'business_data.csv').write_text('do not overwrite', encoding='utf-8')
    with pytest.raises(FileExistsError):
        create_application(root, name='Existing App', template='dashboard')


def test_agent_context_selects_application_factory_templates() -> None:
    from nicegui_base import build_agent_context
    assert build_agent_context('build an executive KPI dashboard').starter_template == 'dashboard'
    assert build_agent_context('build an RCA analysis workspace with wafer chart and filters').starter_template == 'analysis-workspace'
    assert build_agent_context('build a responsive operations monitoring screen').starter_template == 'responsive-operations'
    assert build_agent_context('build an async submit workflow with retry').starter_template == 'async-workflow'
    pack = build_agent_context('build a CRUD page')
    assert pack.validation_commands == ('nicegui-base agent-check .', 'nicegui-base gate .')
