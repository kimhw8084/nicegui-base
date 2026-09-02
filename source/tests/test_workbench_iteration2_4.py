from __future__ import annotations

import io
import json
import zipfile


def test_golden_starter_catalog_is_unique_and_covers_real_app_shapes():
    from nicegui_base.workbench.starter_kits import GOLDEN_STARTERS
    keys = [item.key for item in GOLDEN_STARTERS]
    assert len(keys) == len(set(keys))
    assert len(GOLDEN_STARTERS) >= 16
    assert {item.category for item in GOLDEN_STARTERS} == {'Engineering', 'Generic'}
    patterns = {item.pattern_key for item in GOLDEN_STARTERS}
    assert {'dashboard', 'data_explorer', 'crud', 'monitoring', 'settings', 'wizard', 'comparison', 'analysis_workspace'} <= patterns


def test_every_golden_starter_resolves_against_canonical_catalog():
    from nicegui_base.patterns.registry import get_pattern
    from nicegui_base.workbench.catalog import all_entries
    from nicegui_base.workbench.data_dock import default_data_dock
    from nicegui_base.workbench.starter_kits import GOLDEN_STARTERS, resolve_starter

    entries = all_entries()
    data = default_data_dock()
    for starter in GOLDEN_STARTERS:
        result = resolve_starter(starter, entries, data_model=data)
        definition = get_pattern(starter.pattern_key)
        allowed = {slot.value for slot in definition.slot_order if slot.value != 'header'}
        assert result.pattern_key == starter.pattern_key
        assert result.selected_keys, starter.key
        assert not result.unresolved, (starter.key, result.unresolved)
        assert set(result.placements) <= allowed
        flattened = [key for keys in result.placements.values() for key in keys]
        assert len(flattened) == len(set(flattened)), starter.key


def test_auto_compose_all_canonical_patterns_is_deterministic_and_valid():
    from nicegui_base.patterns.registry import PATTERN_REGISTRY
    from nicegui_base.workbench.catalog import all_entries
    from nicegui_base.workbench.data_dock import default_data_dock
    from nicegui_base.workbench.starter_kits import recommend_composition

    entries = all_entries()
    data = default_data_dock()
    for definition in PATTERN_REGISTRY.values():
        key = definition.pattern.value
        first = recommend_composition(key, entries, goal='reduce engineer TAT and expose reusable evidence', data_model=data)
        second = recommend_composition(key, entries, goal='reduce engineer TAT and expose reusable evidence', data_model=data)
        assert first == second
        allowed = {slot.value for slot in definition.slot_order if slot.value != 'header'}
        assert set(first.placements) <= allowed
        flattened = [item for items in first.placements.values() for item in items]
        assert len(flattened) == len(set(flattened))


def test_builder_golden_starter_and_project_audit_have_no_blocking_findings():
    from nicegui_base.workbench.builder import BuilderModel
    from nicegui_base.workbench.starter_kits import GOLDEN_STARTERS

    for starter in GOLDEN_STARTERS:
        model = BuilderModel()
        resolution = model.apply_golden_starter(starter.key)
        assert model.pattern_key == starter.pattern_key
        assert model.stage.value == 'compose'
        assert resolution.selected_keys
        audit = model.audit()
        assert not audit.blocking, (starter.key, audit.blocking)
        assert not model.generation_issues(), (starter.key, model.generation_issues())


def test_project_audit_blocks_duplicate_or_unknown_capabilities():
    from nicegui_base.workbench.catalog import all_entries
    from nicegui_base.workbench.project_audit import audit_project

    entries = all_entries()
    composable = next(entry for entry in entries if getattr(getattr(entry, 'kind', None), 'value', '') in {'analytic', 'component'})
    project = {
        'pattern_key': 'dashboard',
        'placements': {'metrics': [composable.key], 'primary': [composable.key], 'data': ['missing:capability']},
    }
    audit = audit_project(project, entries)
    codes = {item.code for item in audit.blocking}
    assert 'duplicate_capability' in codes
    assert 'missing_capability' in codes
    assert audit.status == 'BLOCKED'


def test_browser_acceptance_contract_is_machine_readable_and_pending_until_browser_execution():
    from nicegui_base.workbench.browser_contract import build_browser_acceptance_contract, validate_browser_acceptance_contract

    contract = build_browser_acceptance_contract({'pattern_key': 'monitoring', 'placements': {'primary': ['x']}})
    assert contract['status'] == 'PENDING_BROWSER_EXECUTION'
    assert {item['key'] for item in contract['viewports']} == {'desktop', 'tablet', 'phone'}
    assert '/' in contract['routes']
    assert not validate_browser_acceptance_contract(contract)


def test_generated_project_contains_browser_acceptance_contract():
    from nicegui_base.workbench.builder import BuilderModel
    from nicegui_base.workbench.browser_contract import validate_browser_acceptance_contract

    model = BuilderModel()
    model.apply_golden_starter('operations-dashboard')
    payload, report = model.generate()
    assert report.ok, report.findings
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        name = '.nicegui_base/browser_acceptance.json'
        assert name in archive.namelist()
        contract = json.loads(archive.read(name))
        assert contract['pattern_key'] == 'dashboard'
        assert contract['status'] == 'PENDING_BROWSER_EXECUTION'
        assert not validate_browser_acceptance_contract(contract)


def test_composition_diff_reports_add_remove_and_move_without_duplicates():
    from nicegui_base.workbench.starter_kits import composition_diff

    diff = composition_diff(
        {'primary': ['a', 'b'], 'data': ['c']},
        {'primary': ['a'], 'secondary': ['b'], 'data': ['d']},
    )
    assert diff.added == (('data', 'd'),)
    assert diff.removed == (('data', 'c'),)
    assert diff.moved == (('b', 'primary', 'secondary'),)


def test_canonical_framework_reference_authorities_are_composable():
    from nicegui_base.workbench.catalog import all_entries
    from nicegui_base.workbench.project_codegen import is_composable_entry, project_home_code

    lookup = {entry.key: entry for entry in all_entries()}
    required = (
        'framework:tables:data_table',
        'framework:visualizations:LineChart',
        'framework:content:metric_card',
        'framework:interactions:alert',
        'component:search_input',
        'component:select',
        'component:text_input',
        'component:action_button',
    )
    missing = [key for key in required if key not in lookup]
    assert not missing, missing
    hidden = [key for key in required if not is_composable_entry(lookup[key])]
    assert not hidden, hidden

    placements = {
        'metrics': ['framework:content:metric_card'],
        'primary': ['framework:visualizations:LineChart'],
        'data': ['framework:tables:data_table'],
        'actions': ['component:action_button'],
    }
    source = project_home_code(
        {'name':'Canonical Authority Probe','goal':'probe','pattern_key':'dashboard','placements':placements},
        lookup,
    )
    assert "DataTable(ROWS, COLUMNS" in source
    assert "LineChart(" in source
    assert "MetricCard(" in source
    assert "Button(" in source


def test_lot_wafer_explorer_required_table_resolves_from_framework_reference_catalog():
    from nicegui_base.workbench.catalog import all_entries
    from nicegui_base.workbench.data_dock import default_data_dock
    from nicegui_base.workbench.starter_kits import get_golden_starter, resolve_starter

    resolution = resolve_starter(
        get_golden_starter('lot-wafer-explorer'),
        all_entries(),
        data_model=default_data_dock(),
    )
    assert not resolution.unresolved, resolution.unresolved
    selected = {key for keys in resolution.placements.values() for key in keys}
    assert any(key.startswith('framework:tables:') for key in selected), selected
