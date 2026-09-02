from __future__ import annotations

import inspect
import io
import json
import zipfile


def test_app_blueprint_catalog_is_governed_and_unique():
    from nicegui_base.workbench.app_blueprints import APP_BLUEPRINTS
    assert len(APP_BLUEPRINTS) == 6
    assert len({item.key for item in APP_BLUEPRINTS}) == len(APP_BLUEPRINTS)
    for blueprint in APP_BLUEPRINTS:
        routes = [page.route for page in blueprint.pages]
        modules = [page.module for page in blueprint.pages]
        assert routes[0] == '/'
        assert len(routes) == len(set(routes))
        assert len(modules) == len(set(modules))
        assert 2 <= len(routes) <= 6


def test_every_blueprint_resolves_from_canonical_catalog():
    from nicegui_base.workbench.app_blueprints import APP_BLUEPRINTS, resolve_app_blueprint
    from nicegui_base.workbench.catalog import all_entries
    from nicegui_base.workbench.data_dock import default_data_dock
    from nicegui_base.workbench.starter_kits import get_golden_starter, resolve_starter

    entries = all_entries()
    data = default_data_dock()
    starter = get_golden_starter('operations-dashboard')
    primary = resolve_starter(starter, entries, data_model=data)
    base = {
        'name': 'Blueprint Probe', 'goal': starter.goal, 'problem_type': starter.problem_type,
        'pattern_key': primary.pattern_key,
        'placements': {slot: list(keys) for slot, keys in primary.placements.items()},
    }
    for blueprint in APP_BLUEPRINTS:
        resolved = resolve_app_blueprint({**base, 'blueprint_key': blueprint.key}, entries, data_model=data)
        assert resolved.key == blueprint.key
        assert resolved.routes[0] == '/'
        assert len(resolved.pages) == len(blueprint.pages)
        assert all(page.pattern_key for page in resolved.pages)


def test_builder_snapshot_roundtrip_preserves_blueprint():
    from nicegui_base.workbench.builder import BuilderModel
    model = BuilderModel()
    model.apply_golden_starter('operations-dashboard')
    model.set_blueprint('engineering-control-center')
    snapshot = model.snapshot()
    restored = BuilderModel.from_snapshot(snapshot)
    assert restored.blueprint_key == 'engineering-control-center'
    assert restored.snapshot()['blueprint_key'] == 'engineering-control-center'
    assert restored.blueprint_plan().routes == ('/', '/overview', '/data', '/investigate', '/compare', '/settings')


def test_single_page_generation_remains_backward_compatible():
    from nicegui_base.workbench.builder import BuilderModel
    model = BuilderModel(); model.apply_golden_starter('record-manager')
    payload, report = model.generate()
    assert report.ok, report.findings
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert '.nicegui_base/app_blueprint.json' not in names
        browser = json.loads(archive.read('.nicegui_base/browser_acceptance.json'))
        assert browser['routes'] == ['/']


def test_multi_page_generation_contains_shell_navigation_and_route_manifest():
    from nicegui_base.workbench.builder import BuilderModel
    from nicegui_base.workbench.app_blueprints import validate_app_blueprint_manifest
    model = BuilderModel(); model.apply_golden_starter('operations-dashboard')
    model.set_blueprint('engineering-control-center')
    payload, report = model.generate()
    assert report.ok, report.findings
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        blueprint = json.loads(archive.read('.nicegui_base/app_blueprint.json'))
        assert validate_app_blueprint_manifest(blueprint) == ()
        expected = {'pages/home.py','pages/overview.py','pages/data.py','pages/investigate.py','pages/compare.py','pages/settings.py'}
        assert expected <= names
        assert 'pages=ROUTES' in archive.read('app.py').decode('utf-8')
        for page in expected:
            source = archive.read(page).decode('utf-8')
            assert 'AppShell(' in source
            assert 'NavigationModel(' in source
        browser = json.loads(archive.read('.nicegui_base/browser_acceptance.json'))
        assert browser['routes'] == blueprint['routes']


def test_runtime_adapter_exposes_governed_multi_page_registration():
    from nicegui_base import NiceGUIRuntimeAdapter
    signature = inspect.signature(NiceGUIRuntimeAdapter.run)
    assert 'pages' in signature.parameters
    assert hasattr(NiceGUIRuntimeAdapter, 'install_pages')


def test_generated_live_smoke_discovers_all_declared_routes():
    from nicegui_base.workbench.builder import BuilderModel
    from nicegui_base.workbench.runtime_proof import _generated_routes
    model = BuilderModel(); model.apply_golden_starter('operations-dashboard')
    model.set_blueprint('compact-standard-app')
    payload, report = model.generate(); assert report.ok, report.findings
    assert _generated_routes(payload) == ('/', '/settings')


def test_state_schema_v4_contains_blueprint_key():
    from nicegui_base.workbench.project_state import STATE_VERSION, normalize_state
    state = normalize_state({'version': 3, 'project': {'name': 'Migrated', 'blueprint_key': 'data-management-center'}})
    assert STATE_VERSION >= 4
    assert state['version'] == STATE_VERSION
    assert state['project']['blueprint_key'] == 'data-management-center'


def test_blueprint_manifest_rejects_canonical_route_or_pattern_drift():
    from nicegui_base.workbench.app_blueprints import resolve_app_blueprint, validate_app_blueprint_manifest
    from nicegui_base.workbench.catalog import all_entries
    from nicegui_base.workbench.data_dock import default_data_dock
    from nicegui_base.workbench.starter_kits import get_golden_starter, resolve_starter
    entries = all_entries(); data = default_data_dock()
    starter = get_golden_starter('operations-dashboard')
    primary = resolve_starter(starter, entries, data_model=data)
    project = {
        'name':'Probe','goal':starter.goal,'problem_type':starter.problem_type,
        'pattern_key':primary.pattern_key,'placements':{k:list(v) for k,v in primary.placements.items()},
        'blueprint_key':'compact-standard-app',
    }
    value = resolve_app_blueprint(project, entries, data_model=data).to_dict()
    assert validate_app_blueprint_manifest(value) == ()
    value['pages'][1]['route'] = '/other'
    value['routes'][1] = '/other'
    findings = validate_app_blueprint_manifest(value)
    assert 'blueprint:canonical_routes' in findings
