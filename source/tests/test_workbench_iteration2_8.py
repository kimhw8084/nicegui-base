from __future__ import annotations

import io
import json
import zipfile


def _text_files(payload: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name in archive.namelist():
            if name.endswith(('.py', '.json', '.toml', '.md', '.txt')):
                result[name] = archive.read(name).decode('utf-8', errors='replace')
    return result


def test_data_dock_schema_metadata_roundtrip() -> None:
    from nicegui_base.workbench.data_dock import DataDockModel

    rows = ({'record':'A','pressure':'1.2','tool':'ETCH-01'}, {'record':'B','pressure':'1.4','tool':'ETCH-02'})
    dock = DataDockModel(rows)
    dock.set_column_type('pressure', 'float')
    dock.set_semantic_role('pressure', 'measurement')
    dock.set_semantic_role('tool', 'entity')
    metadata = dock.schema_metadata()

    restored = DataDockModel(rows)
    restored.restore_schema_metadata(metadata)
    by_name = {item.name: item for item in restored.columns}
    assert by_name['pressure'].inferred_type == 'float'
    assert by_name['pressure'].role == 'measurement'
    assert by_name['tool'].role == 'entity'


def test_schema_only_handoff_never_uses_original_values() -> None:
    from nicegui_base.workbench.data_handoff import build_data_handoff_plan, validate_data_contract_manifest

    project = {
        'data_handoff_mode': 'schema_only',
        'data_source_name': 'Sensitive local paste',
        'data_rows': [
            {'lot':'SECRET-LOT-987','tool':'PRIVATE-TOOL-42','value':13.7},
            {'lot':'SECRET-LOT-654','tool':'PRIVATE-TOOL-77','value':14.1},
        ],
        'data_schema': [
            {'name':'lot','inferred_type':'string','role':'entity','nullable':False,'confidence':1.0},
            {'name':'tool','inferred_type':'string','role':'entity','nullable':False,'confidence':1.0},
            {'name':'value','inferred_type':'float','role':'measurement','nullable':False,'confidence':1.0},
        ],
    }
    plan = build_data_handoff_plan(project)
    assert plan.mode == 'schema_only'
    assert not plan.contains_original_values
    fixture = json.dumps(plan.fixture_rows, sort_keys=True)
    assert 'SECRET-LOT' not in fixture and 'PRIVATE-TOOL' not in fixture
    assert plan.measurement_field == 'value'
    assert plan.row_key in {field.name for field in plan.fields}
    assert not validate_data_contract_manifest(plan.to_manifest())


def test_include_development_rows_requires_explicit_mode() -> None:
    from nicegui_base.workbench.data_handoff import build_data_handoff_plan

    plan = build_data_handoff_plan({
        'data_handoff_mode': 'include_development_rows',
        'data_rows': [{'id':'SENSITIVE-ID','value':9.2}],
        'data_schema': [
            {'name':'id','inferred_type':'string','role':'identifier','nullable':False,'confidence':1.0},
            {'name':'value','inferred_type':'float','role':'measurement','nullable':False,'confidence':1.0},
        ],
    })
    assert plan.contains_original_values
    assert plan.fixture_rows[0]['id'] == 'SENSITIVE-ID'


def test_builder_generated_zip_is_data_contract_bound_and_schema_only_safe() -> None:
    from nicegui_base.workbench.builder import BuilderModel
    from nicegui_base.workbench.data_dock import DataDockModel

    model = BuilderModel()
    model.set_goal('Explore manufacturing records', problem_type='generic application')
    model.data = DataDockModel((
        {'record_id':'SECRET-REC-1','area':'ETCH-PRIVATE','measurement':10.2},
        {'record_id':'SECRET-REC-2','area':'CVD-PRIVATE','measurement':10.8},
    ))
    model.data.set_semantic_role('record_id', 'identifier')
    model.data.set_semantic_role('area', 'dimension')
    model.data.set_semantic_role('measurement', 'measurement')
    model.select_pattern('data_explorer')
    model.auto_compose(replace=True)
    model.set_data_handoff_mode('schema_only')
    payload, report = model.generate()
    assert report.ok, report.findings

    texts = _text_files(payload)
    assert '.nicegui_base/data_contract.json' in texts
    assert 'services/data_contract.py' in texts
    assert 'services/development_fixture.py' in texts
    assert 'services/app_data.py' in texts
    assert 'test_generated_data_contract' in texts['tests/test_project_contract.py']
    assert 'Production provider replacement boundary' in texts['README.md']
    contract = json.loads(texts['.nicegui_base/data_contract.json'])
    assert contract['mode'] == 'schema_only'
    assert contract['contains_original_values'] is False
    assert contract['provider_boundary'] == 'services.app_data:build_source'
    joined = '\n'.join(texts.values())
    assert 'SECRET-REC-1' not in joined
    assert 'ETCH-PRIVATE' not in joined
    home = texts['pages/home.py']
    assert 'DataSourceTable' in home
    assert 'from services.app_data import' in home
    assert 'ROWS = (' not in home
    assert "{'id':'R-001'" not in home


def test_multi_page_blueprint_uses_one_data_contract_on_every_page() -> None:
    from nicegui_base.workbench.builder import BuilderModel
    from nicegui_base.workbench.data_dock import DataDockModel

    model = BuilderModel()
    model.set_goal('Manage and search equipment records', problem_type='generic application')
    model.data = DataDockModel((
        {'equipment_id':'EQ-01','area':'ETCH','value':1.2},
        {'equipment_id':'EQ-02','area':'CVD','value':1.4},
    ))
    model.data.set_semantic_role('equipment_id', 'identifier')
    model.select_pattern('data_explorer')
    model.auto_compose(replace=True)
    model.set_blueprint('data-management-center')
    model.set_data_handoff_mode('schema_only')
    payload, report = model.generate()
    assert report.ok, report.findings
    texts = _text_files(payload)
    blueprint = json.loads(texts['.nicegui_base/app_blueprint.json'])
    for page in blueprint['pages']:
        source = texts[f"pages/{page['module']}.py"]
        assert 'from services.app_data import' in source
        assert 'DataSourceTable' in source or 'series_values' in source


def test_project_state_current_and_builder_data_policy_wiring() -> None:
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / 'nicegui_base' / 'workbench'
    state = (root / 'project_state.py').read_text(encoding='utf-8')
    builder = (root / 'builder.py').read_text(encoding='utf-8')
    codegen = (root / 'project_codegen.py').read_text(encoding='utf-8')
    from nicegui_base.workbench.project_state import STATE_VERSION
    assert STATE_VERSION >= 5
    assert "'data_schema': []" in state
    assert "'data_handoff_mode': 'schema_only'" in state
    assert 'set_data_handoff_mode' in builder
    assert 'schema_metadata()' in builder
    assert 'materialize_data_handoff' in codegen


def test_project_history_surfaces_data_contract_changes() -> None:
    from nicegui_base.workbench.project_history import diff_projects

    before = {
        'name': 'A', 'pattern_key': 'data_explorer', 'blueprint_key': None,
        'data_handoff_mode': 'schema_only', 'data_source_name': 'sample.csv',
        'data_schema': [{'name':'value','inferred_type':'float','role':'measurement'}],
    }
    after = {
        **before,
        'blueprint_key': 'data-management-center',
        'data_handoff_mode': 'include_development_rows',
        'data_source_name': 'approved-dev.csv',
        'data_schema': [{'name':'value','inferred_type':'float','role':'measurement'}, {'name':'area','inferred_type':'string','role':'dimension'}],
    }
    diff = diff_projects(before, after)
    assert {'blueprint_key', 'data_handoff_mode', 'data_source_name', 'data_schema'} <= set(diff.fields)


def test_empty_row_project_restores_persisted_schema_without_generic_sample() -> None:
    from nicegui_base.workbench.builder import BuilderModel

    snapshot = {
        'name':'Schema Only App', 'goal':'empty-state contract', 'problem_type':'generic application',
        'pattern_key':'data_explorer', 'data_rows':[], 'data_source_name':'approved_contract.csv',
        'data_handoff_mode':'schema_only',
        'data_schema':[
            {'name':'record_id','inferred_type':'string','role':'identifier','nullable':False,'confidence':1.0},
            {'name':'measurement','inferred_type':'float','role':'measurement','nullable':True,'confidence':1.0},
        ],
    }
    model = BuilderModel.from_snapshot(snapshot)
    assert model.data.rows == ()
    assert model.data.snapshot.source_name == 'approved_contract.csv'
    assert model.data.snapshot.column_names == ('record_id', 'measurement')
    assert {c.name:c.role for c in model.data.columns}['record_id'] == 'identifier'


def test_generated_smoke_rejects_workbench_data_contract_drift() -> None:
    from nicegui_base.workbench.builder import BuilderModel
    from nicegui_base.workbench.generated_smoke import smoke_generated_zip

    model = BuilderModel(); model.apply_golden_starter('record-manager')
    model.set_data_handoff_mode('schema_only')
    payload, report = model.generate(); assert report.ok, report.findings
    source = zipfile.ZipFile(io.BytesIO(payload))
    output = io.BytesIO()
    with source, zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in source.namelist():
            data = source.read(name)
            if name == '.nicegui_base/workbench_project.json':
                project = json.loads(data)
                project['data_contract']['contract_signature'] = '0' * 64
                data = (json.dumps(project, indent=2, sort_keys=True) + '\n').encode('utf-8')
            archive.writestr(name, data)
    drift = smoke_generated_zip(output.getvalue())
    assert not drift.ok
    assert 'data_contract:workbench_signature_drift' in drift.findings


def test_state_v4_migrates_to_current_data_contract_defaults() -> None:
    from nicegui_base.workbench.project_state import STATE_VERSION, normalize_state
    state = normalize_state({'version':4, 'project':{'name':'Previous 2.7 Project','blueprint_key':'compact-standard-app'}})
    assert STATE_VERSION >= 5
    assert state['version'] == STATE_VERSION
    assert state['project']['blueprint_key'] == 'compact-standard-app'
    assert state['project']['data_handoff_mode'] == 'schema_only'
    assert state['project']['data_schema'] == []


def test_explicit_handoff_rejects_nonfinite_values_before_codegen() -> None:
    import pytest
    from nicegui_base.workbench.data_handoff import build_data_handoff_plan

    with pytest.raises(ValueError, match='non-finite'):
        build_data_handoff_plan({
            'data_handoff_mode':'include_development_rows',
            'data_rows':[{'id':'A','value':float('nan')}],
            'data_schema':[
                {'name':'id','inferred_type':'string','role':'identifier','nullable':False},
                {'name':'value','inferred_type':'float','role':'measurement','nullable':False},
            ],
        })
