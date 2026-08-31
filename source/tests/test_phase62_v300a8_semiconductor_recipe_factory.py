from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from nicegui_base import (
    AnalysisContext, Comparison, ComparisonOperator, DataSchema, FieldRole, FieldType,
    InMemoryDataSource, SelectionBus, SelectionKind, SemanticField, WorkspaceBreakpoint,
)
from nicegui_base.ai.context import build_agent_context, render_agent_context
from nicegui_base.ai.gate import run_application_gate
from nicegui_base.ai.preflight import run_agent_preflight
from nicegui_base.ai.project import create_application
from nicegui_base.semiconductor import (
    RecipeCompatibilityError, RecipePanelKind, SEMICONDUCTOR_RECIPE_REGISTRY,
    assemble_semiconductor_application, get_semiconductor_recipe, recipe_catalog_entries,
    recommend_semiconductor_recipe, resolve_recipe_source,
)

RECIPE_KEYS = tuple(SEMICONDUCTOR_RECIPE_REGISTRY)

WIDE_ROWS = (
    {'id':'M1','timestamp':'2026-08-29T08:00:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':-1.0,'y':0.0,'value':10.0,'sensor':'pressure','sensor_value':1.0,'bin':'PASS','count':95.0,'yield_pct':99.1,'category':'PASS','defect_class':'none'},
    {'id':'M2','timestamp':'2026-08-29T08:01:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':0.0,'y':0.0,'value':10.4,'sensor':'pressure','sensor_value':1.2,'bin':'B1','count':3.0,'yield_pct':98.7,'category':'B1','defect_class':'particle'},
    {'id':'M3','timestamp':'2026-08-29T08:02:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'B','lot':'L2','wafer':'W02','x':1.0,'y':0.0,'value':9.9,'sensor':'pressure','sensor_value':1.1,'bin':'B2','count':2.0,'yield_pct':99.0,'category':'B2','defect_class':'scratch'},
)


def _source(key: str = 'semiconductor') -> InMemoryDataSource:
    return InMemoryDataSource(key, WIDE_ROWS)


def _load_home(root: Path, name: str):
    path = root / 'pages' / 'home.py'
    module_name = f'_wave62_{name.replace("-", "_")}'
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    old = list(sys.path)
    try:
        sys.path.insert(0, str(root))
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old
    return module


def test_wave62_registry_contains_exactly_the_eight_approved_application_recipes():
    assert set(RECIPE_KEYS) == {
        'spc-monitor','excursion-defense-line','fdc-tool-health','lot-wafer-explorer',
        'yield-loss','pm-effect-analysis','chamber-matching','rca-cockpit',
    }
    assert {item.application_name for item in SEMICONDUCTOR_RECIPE_REGISTRY.values()} == {
        'SPCMonitor','ExcursionDefenseLine','FdcToolHealth','LotWaferExplorer',
        'YieldLoss','PMEffectAnalysis','ChamberMatching','RcaCockpit',
    }


@pytest.mark.parametrize('key', RECIPE_KEYS)
def test_wave62_every_recipe_is_complete_machine_guidance_not_just_a_surface_list(key: str):
    recipe = get_semiconductor_recipe(key)
    assert recipe.purpose and recipe.use_when and recipe.avoid_when and recipe.entities
    assert recipe.filters and recipe.panels and recipe.interactions and recipe.record_views
    assert recipe.base_template == 'analysis-workspace'
    assert any(panel.kind is RecipePanelKind.ANALYTICAL for panel in recipe.panels)
    assert all(panel.surface_key in __import__('nicegui_base.semiconductor', fromlist=['SEMICONDUCTOR_SURFACE_REGISTRY']).SEMICONDUCTOR_SURFACE_REGISTRY for panel in recipe.analytical_panels)


@pytest.mark.parametrize('alias,key', [
    ('SPCMonitor','spc-monitor'),('ExcursionDefenseLine','excursion-defense-line'),('FdcToolHealth','fdc-tool-health'),
    ('LotWaferExplorer','lot-wafer-explorer'),('YieldLoss','yield-loss'),('PMEffectAnalysis','pm-effect-analysis'),
    ('ChamberMatching','chamber-matching'),('RcaCockpit','rca-cockpit'),
])
def test_wave62_recipe_lookup_accepts_product_names_and_slugs(alias: str, key: str):
    assert get_semiconductor_recipe(alias).key == key
    assert get_semiconductor_recipe(key).application_name == alias


@pytest.mark.parametrize('intent,expected', [
    ('compare chambers after PM','pm-effect-analysis'),
    ('is chamber B drifting?','spc-monitor'),
    ('FDC sensor drift on chamber B','fdc-tool-health'),
    ('where on wafer did the process change?','excursion-defense-line'),
    ('explore all wafers in lot L123','lot-wafer-explorer'),
    ('why did yield drop and which bins dominate?','yield-loss'),
    ('match chambers and explain fingerprint separation','chamber-matching'),
    ('RCA commonality with hypotheses and evidence','rca-cockpit'),
])
def test_wave62_recommendation_maps_engineer_intent_to_complete_app(intent: str, expected: str):
    assert recommend_semiconductor_recipe(intent).key == expected


def test_wave62_recipe_source_resolution_prefers_aliases_then_semantic_roles_and_supports_overrides():
    schema = DataSchema((
        SemanticField('record_id',type=FieldType.STRING,role=FieldRole.IDENTIFIER),
        SemanticField('critical_dimension',type=FieldType.FLOAT,role=FieldRole.MEASUREMENT),
        SemanticField('event_time',type=FieldType.DATETIME,role=FieldRole.TIMESTAMP),
        SemanticField('product',type=FieldType.STRING,role=FieldRole.ENTITY),
    ), key='record_id')
    result = resolve_recipe_source('spc-monitor', schema)
    assert result.compatible
    assert result.bindings['measurement'] == 'critical_dimension'
    assert result.bindings['time'] == 'event_time'
    assert result.bindings['row_id'] == 'record_id'
    assert result.available_filters == ('product',)
    override = resolve_recipe_source('spc-monitor', schema, field_overrides={'measurement':'critical_dimension'})
    assert override.bindings['measurement'] == 'critical_dimension'
    with pytest.raises(KeyError):
        resolve_recipe_source('spc-monitor', schema, field_overrides={'measurement':'missing'})


def test_wave62_strict_assembly_fails_explicitly_for_missing_required_source_semantics():
    source = InMemoryDataSource('bad', ({'id':1,'label':'x'},))
    with pytest.raises(RecipeCompatibilityError) as exc:
        asyncio.run(assemble_semiconductor_application('spc-monitor', source))
    assert 'measurement' in exc.value.compatibility.missing_required
    asyncio.run(source.aclose())


def test_wave62_non_strict_assembly_degrades_by_removing_unbindable_panels_not_faking_data():
    source = InMemoryDataSource('partial', ({'id':1,'value':1.0}, {'id':2,'value':2.0}))
    assembly = asyncio.run(assemble_semiconductor_application('spc-monitor', source, strict=False))
    assert assembly.compatibility.compatible
    assert 'wafer' in assembly.compatibility.unavailable_panels
    assert 'control' in assembly.compatibility.available_panels
    assert 'wafer' not in assembly.surfaces
    asyncio.run(assembly.aclose(close_source=True))


@pytest.mark.parametrize('key', RECIPE_KEYS)
def test_wave62_all_recipes_assemble_over_wave59_60_61_authorities(key: str):
    source = _source(key)
    assembly = asyncio.run(assemble_semiconductor_application(key, source))
    assert assembly.context.source_key == key
    assert assembly.semiconductor.context is assembly.context
    assert assembly.coordinator.context is assembly.context
    assert assembly.coordinator.selections is assembly.selections
    assert assembly.manufacturing_filters.source is source
    assert assembly.compatibility.compatible
    assert assembly.panels
    assert set(assembly.surfaces) == {panel.panel_id for panel in assembly.panels if panel.kind is RecipePanelKind.ANALYTICAL}
    assert all(surface.context is assembly.context and surface.selections is assembly.selections for surface in assembly.surfaces.values())
    metadata = assembly.context.metadata['semiconductor_recipe']
    assert metadata['key'] == key and metadata['bindings'] == dict(assembly.bindings)
    asyncio.run(assembly.aclose(close_source=True))


@pytest.mark.parametrize('key', RECIPE_KEYS)
def test_wave62_recipe_layouts_are_collision_free_and_phone_full_width(key: str):
    source = _source(key)
    assembly = asyncio.run(assemble_semiconductor_application(key, source))
    for breakpoint in WorkspaceBreakpoint:
        placements = assembly.workspace.layout.layout(breakpoint)
        assert len(placements) == len(assembly.panels)
        for index, item in enumerate(placements):
            assert not any(item.intersects(other) for other in placements[index+1:])
    assert all(item.column == 0 and item.column_span == 4 for item in assembly.workspace.layout.layout(WorkspaceBreakpoint.PHONE))
    asyncio.run(assembly.aclose(close_source=True))


def test_wave62_recipe_assembly_preserves_external_context_and_selection_ownership():
    source = _source('external')
    context = AnalysisContext(source_key='external')
    selections = SelectionBus()
    assembly = asyncio.run(assemble_semiconductor_application('spc-monitor', source, context=context, selections=selections))
    asyncio.run(assembly.aclose())
    # External authorities remain usable after assembly teardown.
    context.add_filter(Comparison('product', ComparisonOperator.EQ, 'P1'))
    selections.clear(source='test')
    assert context.filters
    selections.close(); context.close(); asyncio.run(source.aclose())


def test_wave62_surface_selection_crossfilters_complete_recipe_through_one_bus():
    source = _source('crossfilter')
    assembly = asyncio.run(assemble_semiconductor_application('excursion-defense-line', source))
    expr = Comparison('chamber', ComparisonOperator.EQ, 'A')
    assembly.surfaces['wafer_delta'].select(SelectionKind.WAFER, 'W01', {'filter':expr,'wafer':'W01'})
    assert expr in assembly.context.filters
    assert all(surface.selections is assembly.selections for surface in assembly.surfaces.values())
    asyncio.run(assembly.aclose(close_source=True))


def test_wave62_manufacturing_filter_availability_is_schema_driven_not_invented():
    source = InMemoryDataSource('small', ({'product':'P1','route':'R1','value':1.0},{'product':'P1','route':'R2','value':2.0}))
    assembly = asyncio.run(assemble_semiconductor_application('spc-monitor', source, strict=False))
    assert assembly.compatibility.available_filters == ('product','route')
    assert 'tool' in assembly.compatibility.unavailable_filters
    assembly.semiconductor.set('product','P1')
    assert asyncio.run(assembly.manufacturing_filters.options('route')) == ('R1','R2')
    asyncio.run(assembly.aclose(close_source=True))


def test_wave62_recipe_catalog_is_json_serializable_and_matches_runtime_registry():
    entries = recipe_catalog_entries()
    assert {item['key'] for item in entries} == set(RECIPE_KEYS)
    assert all(item['surfaces'] and item['panel_count'] >= len(item['surfaces']) for item in entries)
    assert all(item['interaction_count'] > 0 and item['avoid_when'] for item in entries)
    json.dumps(entries)


@pytest.mark.parametrize('key', RECIPE_KEYS)
def test_wave62_factory_generates_importable_executable_recipe_starters(tmp_path: Path, key: str):
    root = tmp_path / key
    created = create_application(root, name=get_semiconductor_recipe(key).application_name, recipe=key)
    assert created.recipe == key and created.template == 'analysis-workspace'
    assert f"recipe = '{key}'" in (root/'nicegui_base.toml').read_text(encoding='utf-8')
    assert (root/'services/data_source.py').exists()
    preflight = run_agent_preflight(root)
    assert preflight.passed, preflight.issues
    home = _load_home(root, key)
    assert home._RECIPE.key == key and callable(home.build_page)
    assembly = asyncio.run(home.prepare_analysis())
    assert assembly.compatibility.compatible and assembly.surfaces
    asyncio.run(assembly.aclose(close_source=True))


def test_wave62_source_application_gate_executes_recipe_build_page_and_generated_tests(tmp_path: Path):
    root = tmp_path/'spc'
    create_application(root, name='SPC Monitor', recipe='spc-monitor')
    report = run_application_gate(root)
    assert report.passed, report.to_dict()
    assert {check.name for check in report.checks} == {'manifest','agent-preflight','dependency-pin','python-compile','entrypoint','build-page','tests'}


def test_wave62_recipe_factory_rejects_non_analysis_template_to_prevent_parallel_layout_system(tmp_path: Path):
    with pytest.raises(ValueError, match='analysis-workspace'):
        create_application(tmp_path/'bad', name='Bad Recipe', template='dashboard', recipe='spc-monitor')


def test_wave62_agent_context_recommends_recipe_and_one_command_factory():
    pack = build_agent_context('compare chambers after PM')
    assert pack.starter_template == 'analysis-workspace'
    assert pack.starter_recipe == 'pm-effect-analysis'
    rendered = render_agent_context(pack)
    assert '--recipe pm-effect-analysis' in rendered
    assert pack.to_dict()['starter_recipe'] == 'pm-effect-analysis'


def test_wave62_recipe_interactions_reference_only_existing_panels_and_share_selection_contracts():
    for recipe in SEMICONDUCTOR_RECIPE_REGISTRY.values():
        panel_ids = {panel.panel_id for panel in recipe.panels}
        for interaction in recipe.interactions:
            assert interaction.source_panel in panel_ids
            assert set(interaction.target_panels) <= panel_ids
            assert interaction.selection_kinds
            assert interaction.crossfilter




def test_wave62_packaged_catalog_and_agent_registry_publish_all_recipes():
    from nicegui_base.ai import FRAMEWORK_REGISTRY_COUNTS, load_framework_catalog
    from nicegui_base.ai.scaffold import GUIDE_NAMES
    catalog = load_framework_catalog()
    entries = catalog['registries']['semiconductor_recipes']
    assert {entry['_registry_key'] for entry in entries} == set(RECIPE_KEYS)
    assert catalog['registry_counts']['semiconductor_recipes'] == len(RECIPE_KEYS)
    assert FRAMEWORK_REGISTRY_COUNTS['semiconductor_recipes'] == len(RECIPE_KEYS)
    assert 'SEMICONDUCTOR_APPLICATION_RECIPES.md' in GUIDE_NAMES

def test_wave62_recipe_factory_adds_no_numerical_or_provider_dependency():
    requirements = [
        line.strip()
        for line in Path(__file__).resolve().parents[1].joinpath('requirements.txt').read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ]
    assert requirements == ['nicegui==3.15.0']
