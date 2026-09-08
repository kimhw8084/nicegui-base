from __future__ import annotations

import ast
import io
import json
import zipfile
from pathlib import Path

from nicegui_base.workbench.builder import BuilderModel, BuilderStage
from nicegui_base.workbench.catalog import all_entries
from nicegui_base.workbench.generated_smoke import smoke_generated_zip, validate_public_call_signatures
from nicegui_base.workbench.project_codegen import _relative_written_paths, generate_project_zip, is_composable_entry, project_home_code
from nicegui_base.workbench.project_state import empty_state, normalize_state


def test_project_state_normalizes_and_deduplicates() -> None:
    state = normalize_state({'favorites':['a','a','b'], 'recents':['x','x'], 'project':{'queued_entry_keys':['q','q'], 'revision':'broken', 'theme':'nope', 'density':'tiny'}})
    assert state['favorites'] == ['a','b']
    assert state['recents'] == ['x']
    assert state['project']['queued_entry_keys'] == ['q']
    assert state['project']['revision'] == 0
    assert state['project']['theme'] == 'system'
    assert state['project']['density'] == 'compact'
    assert empty_state()['version'] == 6


def test_builder_uses_canonical_pattern_slots() -> None:
    model = BuilderModel(goal='monitor alerts and equipment health')
    recs = model.pattern_recommendations()
    assert len(recs) == 10
    model.select_pattern('monitoring')
    assert model.stage is BuilderStage.DATA
    assert 'metrics' in model.required_slots()
    assert 'primary' in model.required_slots()
    assert 'data' in model.allowed_slots()



def test_builder_blocks_invalid_generated_application_names() -> None:
    model = BuilderModel(app_name='1 bad name')
    model.select_pattern('dashboard')
    assert model.generation_issues()
    model.app_name = 'Good App'
    assert model.generation_issues() == ()

def test_composer_can_place_a_real_catalog_capability() -> None:
    model = BuilderModel(goal='visualize process trend')
    model.select_pattern('analysis_workspace')
    entry = next(entry for entry in all_entries() if is_composable_entry(entry))
    model.place(entry.key, 'primary')
    assert model.placements['primary'] == [entry.key]
    assert model.review()['placed_capabilities'] == 1


def test_generated_home_code_is_valid_python_and_uses_layout_slots() -> None:
    lookup = {entry.key: entry for entry in all_entries()}
    entry = next(entry for entry in lookup.values() if is_composable_entry(entry))
    project = {
        'name':'Smoke App', 'goal':'test', 'pattern_key':'dashboard',
        'placements':{'primary':[entry.key]}, 'theme':'system', 'density':'compact',
    }
    code = project_home_code(project, lookup)
    ast.parse(code)
    assert 'def build_page()' in code
    assert 'LayoutSlot.PRIMARY' in code
    assert 'company_ui' not in code



def test_full_project_generation_passes_smoke_gate() -> None:
    lookup = {entry.key: entry for entry in all_entries()}
    project = {
        'name':'Generated Smoke App', 'goal':'monitor process health', 'problem_type':'engineering analysis',
        'pattern_key':'monitoring', 'placements':{}, 'theme':'system', 'density':'compact',
    }
    payload, report = generate_project_zip(project, lookup)
    assert payload
    assert report.ok, report.findings

def test_generated_smoke_contract_matches_create_application_output() -> None:
    from nicegui_base.ai.project import create_application
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / 'app'
        created = create_application(root, name='Contract Probe', template='dashboard')
        generated = set(_relative_written_paths(root, created.written))
    # These are generator-owned anchors, not a parallel pyproject-based project model.
    assert {'app.py','pages/home.py','requirements.txt','nicegui_base.toml','tests/test_project_contract.py'} <= generated
    assert 'pyproject.toml' not in generated


def test_relative_written_paths_resolves_symlinked_roots(tmp_path: Path) -> None:
    real_root = tmp_path / 'real' / 'app'
    real_root.mkdir(parents=True)
    written = real_root / 'app.py'
    written.write_text('pass\n', encoding='utf-8')
    alias_parent = tmp_path / 'alias'
    try:
        alias_parent.symlink_to(tmp_path / 'real', target_is_directory=True)
    except (OSError, NotImplementedError):
        return
    alias_root = alias_parent / 'app'
    assert _relative_written_paths(alias_root, (written.resolve(),)) == ('app.py',)


def test_relative_written_paths_rejects_escape(tmp_path: Path) -> None:
    root = tmp_path / 'app'; root.mkdir()
    outside = tmp_path / 'outside.py'; outside.write_text('pass\n', encoding='utf-8')
    import pytest
    with pytest.raises(RuntimeError, match='escaped application root'):
        _relative_written_paths(root, (outside,))


def test_generated_zip_smoke_blocks_invalid_and_accepts_valid_shape() -> None:
    bad = smoke_generated_zip(b'not a zip')
    assert not bad.ok and 'bad_zip' in bad.findings
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        zf.writestr('app.py', 'def runtime():\n    return None\ndef main():\n    return None\n')
        zf.writestr('pages/home.py', 'from nicegui_base import LayoutSlot\ndef build_page():\n    x = LayoutSlot.PRIMARY\n')
        zf.writestr('requirements.txt', 'nicegui-base==3.0.0a8\n')
        zf.writestr('nicegui_base.toml', '[nicegui_base]\nframework_version="3.0.0a8"\nbuild_page="pages.home:build_page"\n')
        zf.writestr('tests/test_project_contract.py', 'def test_contract():\n    assert True\n')
        zf.writestr('.nicegui_base/workbench_project.json', json.dumps({'pattern_key':'dashboard','placements':{}}))
    good = smoke_generated_zip(buffer.getvalue())
    assert good.ok, good.findings



def test_generated_public_call_signatures_bind() -> None:
    import nicegui_base as nb
    lookup = {entry.key: entry for entry in all_entries()}
    composable = [entry for entry in lookup.values() if is_composable_entry(entry)]
    assert composable
    failures = {}
    for entry in composable:
        code = project_home_code(
            {'name':'Signature Probe','goal':'probe','pattern_key':'analysis_workspace','placements':{'primary':[entry.key]}},
            lookup,
        )
        findings = validate_public_call_signatures(code, nb)
        if findings:
            failures[entry.key] = findings
    assert not failures, failures


def test_project_codegen_uses_only_public_runtime_symbols() -> None:
    import nicegui_base as nb
    names = (
        'Alert','AnalysisContext','AnalysisWorkspacePage','AxisSpec','AxisType','Button','CrudPage','DashboardPage',
        'DataExplorerPage','DataTable','LayoutSlot','LineChart','MasterDetailPage','MetricCard','MonitoringPage',
        'SearchInput','SearchPage','Select','SelectionBus','SemiconductorAnalyticalPanel','SeriesSpec','SettingsPage',
        'StatusBadge','TableColumn','TextInput','WizardPage','ComparisonPage',
    )
    missing = [name for name in names if not hasattr(nb, name)]
    assert not missing, missing

def test_iteration_2_2_routes_and_studio_actions_are_wired() -> None:
    root = Path(__file__).resolve().parents[1]
    app_source = (root / 'nicegui_base' / 'workbench' / 'app.py').read_text(encoding='utf-8')
    studio_source = (root / 'nicegui_base' / 'workbench' / 'capability_studio.py').read_text(encoding='utf-8')
    assert "ui.page('/layouts')(layout_studio_page)" in app_source
    assert "NavItem('reference_patterns', 'Application Patterns', '/patterns'" in app_source
    assert "ui.page('/settings')(settings_page)" in app_source
    assert "NavItem('reference_components', 'Components', '/components'" in app_source
    assert "queue_entry(key)" not in app_source
    assert 'reference_only: bool = True' in studio_source
