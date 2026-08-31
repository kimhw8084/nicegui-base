from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from nicegui_base import (
    AdaptedSemiconductorSource, AnalysisContext, AnalysisStatus, DataSchema, FieldRole, FieldType,
    InMemoryDataSource, PanelLayoutOverride, RecipeCustomization, RecipeRuntimePolicy, RuntimeReadiness,
    SelectionKind, SemanticField, SmartBindingPolicy, SEMICONDUCTOR_RECIPE_REGISTRY,
    SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY, binding_candidates, create_semiconductor_recipe_runtime,
    get_semiconductor_recipe_variant, onboard_recipe_source, recipe_variant_catalog_entries,
    resolve_recipe_configuration, smart_binding_decisions, variants_for_recipe,
)
from nicegui_base.ai.gate import run_application_gate
from nicegui_base.ai.project import create_application


ROWS = (
    {'id':'M1','timestamp':'2026-08-29T08:00:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':-1.0,'y':0.0,'value':10.0,'sensor':'pressure','sensor_value':1.0,'bin':'PASS','count':95.0,'yield_pct':99.1,'category':'PASS','defect_class':'none'},
    {'id':'M2','timestamp':'2026-08-29T08:01:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':0.0,'y':0.0,'value':10.4,'sensor':'pressure','sensor_value':1.2,'bin':'B1','count':3.0,'yield_pct':98.7,'category':'B1','defect_class':'particle'},
    {'id':'M3','timestamp':'2026-08-29T08:02:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'B','lot':'L2','wafer':'W02','x':1.0,'y':0.0,'value':9.9,'sensor':'pressure','sensor_value':1.1,'bin':'B2','count':2.0,'yield_pct':99.0,'category':'B2','defect_class':'scratch'},
)


def source(key='semiconductor'):
    return InMemoryDataSource(key, ROWS)


def load_home(root: Path, name='wave63'):
    spec = importlib.util.spec_from_file_location(name, root/'pages'/'home.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    old = list(sys.path)
    try:
        for loaded in tuple(sys.modules):
            if loaded == 'recipe_config' or loaded == 'services' or loaded.startswith('services.'):
                sys.modules.pop(loaded, None)
        sys.path.insert(0, str(root)); spec.loader.exec_module(module)
    finally:
        sys.path[:] = old
    return module


def test_wave63_has_one_governed_focused_variant_per_complete_recipe():
    assert len(SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY) == 8
    assert {item.recipe_key for item in SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY.values()} == set(SEMICONDUCTOR_RECIPE_REGISTRY)
    assert all(len(variants_for_recipe(key)) == 1 for key in SEMICONDUCTOR_RECIPE_REGISTRY)
    json.dumps(recipe_variant_catalog_entries())


@pytest.mark.parametrize('variant_key', tuple(SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY))
def test_wave63_variants_are_additive_composition_not_new_runtime_authorities(variant_key: str):
    variant = get_semiconductor_recipe_variant(variant_key)
    config = resolve_recipe_configuration(variant.recipe_key, variant=variant)
    base = SEMICONDUCTOR_RECIPE_REGISTRY[variant.recipe_key]
    assert config.recipe.key == base.key
    assert set(config.recipe.surface_keys) <= set(base.surface_keys)
    assert set(item.key for item in config.recipe.filters) == set(item.key for item in base.filters)
    assert config.variant_key == variant.key
    assert all(item.source_panel in {p.panel_id for p in config.recipe.panels} for item in config.recipe.interactions)


def test_wave63_customization_can_hide_reorder_resize_pin_and_seed_filters_without_forking_recipe():
    custom = RecipeCustomization(
        hidden_panels=('wafer',), panel_order=('records','control'),
        panel_layout={'control': PanelLayoutOverride(columns=12, rows=6)},
        pinned_filters=('product','chamber'), initial_filters={'product':'P1'},
        metadata={'owner':'process-engineering'},
    )
    config = resolve_recipe_configuration('spc-monitor', customization=custom)
    assert config.recipe.key == 'spc-monitor'
    assert config.recipe.panels[0].panel_id == 'records'
    assert 'wafer' not in {item.panel_id for item in config.recipe.panels}
    assert next(item for item in config.recipe.panels if item.panel_id == 'control').preferred_columns == 12
    assert {item.key for item in config.recipe.filters if item.pinned} >= {'product','chamber'}
    assert config.initial_filters == {'product':'P1'}
    assert config.metadata['owner'] == 'process-engineering'


@pytest.mark.parametrize('kwargs', [
    {'hidden_panels':('missing',)}, {'pinned_filters':('missing',)}, {'field_overrides':{'missing':'x'}},
    {'initial_filters':{'missing':'x'}},
])
def test_wave63_customization_fails_explicitly_on_unknown_recipe_contracts(kwargs):
    with pytest.raises(KeyError):
        resolve_recipe_configuration('spc-monitor', customization=RecipeCustomization(**kwargs))


def test_wave63_binding_candidates_explain_exact_normalized_role_and_name_matches():
    schema = DataSchema((
        SemanticField('criticalDimension', type=FieldType.FLOAT, role=FieldRole.ATTRIBUTE),
        SemanticField('process_value', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT),
        SemanticField('measured_at', type=FieldType.DATETIME, role=FieldRole.TIMESTAMP),
    ))
    recipe = SEMICONDUCTOR_RECIPE_REGISTRY['spc-monitor']
    measurement = next(item for item in recipe.field_requirements if item.key == 'measurement')
    ranked = binding_candidates(measurement, schema)
    assert ranked
    assert any(item.source_field == 'process_value' and item.method.value == 'semantic_role' for item in ranked)
    time_req = next(item for item in recipe.field_requirements if item.key == 'time')
    assert binding_candidates(time_req, schema)[0].source_field == 'measured_at'


def test_wave63_smart_binding_refuses_ambiguous_semantic_role_guess():
    schema = DataSchema((
        SemanticField('metric_a', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT),
        SemanticField('metric_b', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT),
    ))
    decisions = smart_binding_decisions('spc-monitor', schema)
    decision = decisions['measurement']
    assert decision.ambiguous and not decision.auto_bound and decision.source_field is None
    assert {item.source_field for item in decision.alternatives[:2]} == {'metric_a','metric_b'}


def test_wave63_explicit_override_wins_over_smart_binding_and_is_auditable():
    schema = DataSchema((
        SemanticField('metric_a', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT),
        SemanticField('metric_b', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT),
    ))
    decision = smart_binding_decisions('spc-monitor', schema, field_overrides={'measurement':'metric_b'})['measurement']
    assert decision.source_field == 'metric_b' and decision.auto_bound and decision.method.value == 'override'


def test_wave63_onboarding_report_is_serializable_and_warns_about_non_pushdown_fixture():
    s = source('onboard')
    report = asyncio.run(onboard_recipe_source('spc-monitor', s))
    assert report.ready
    assert report.compatibility.bindings['measurement'] == 'value'
    assert any('filter pushdown' in warning for warning in report.warnings)
    assert any('pagination pushdown' in warning for warning in report.warnings)
    json.dumps(report.to_dict())
    asyncio.run(s.aclose())


class Adapter:
    key = 'approved-company-adapter'
    def __init__(self): self.opened = False
    async def open(self, recipe):
        self.opened = True
        return AdaptedSemiconductorSource(source('adapted'), {'measurement':'value'} if recipe.key == 'spc-monitor' else {}, {'provider_contract':'test'}, True)


def test_wave63_provider_adapter_hook_returns_datasource_without_leaking_provider_logic_into_runtime():
    adapter = Adapter()
    runtime = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', adapter))
    assert adapter.opened
    assert runtime.source.provider == 'memory'
    assert runtime.adapter_metadata['provider_contract'] == 'test'
    assert runtime.onboarding.adapter_metadata['provider_contract'] == 'test'
    asyncio.run(runtime.aclose())
    assert runtime.source.closed


@pytest.mark.parametrize('recipe_key', tuple(SEMICONDUCTOR_RECIPE_REGISTRY))
def test_wave63_all_eight_apps_run_shared_runtime_probe_records_filters_and_selection(recipe_key: str):
    s = source(recipe_key)
    runtime = asyncio.run(create_semiconductor_recipe_runtime(recipe_key, s))
    probe = asyncio.run(runtime.refresh())
    assert probe.readiness is RuntimeReadiness.READY
    assert probe.rows_available == len(ROWS)
    assert probe.panel_states and all(state is AnalysisStatus.READY for state in probe.panel_states.values())
    records = asyncio.run(runtime.records(limit=2))
    assert len(records.rows) == 2 and records.filtered_total == 3
    runtime.select(SelectionKind.ENTITY, 'chamber:A', {'chamber':'A'})
    assert runtime.selections.by_kind(SelectionKind.ENTITY)
    if 'product' in runtime.assembly.compatibility.available_filters:
        assert 'P1' in asyncio.run(runtime.filter_options('product'))
    asyncio.run(runtime.aclose())
    assert not s.closed  # caller-owned DataSource remains caller-owned
    asyncio.run(s.aclose())


def test_wave63_runtime_context_mutation_marks_panels_stale_until_refresh():
    s = source('stale')
    runtime = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', s))
    asyncio.run(runtime.refresh())
    runtime.set_manufacturing_filter('chamber','A')
    assert all(surface.controller.state.status is AnalysisStatus.STALE for surface in runtime.assembly.surfaces.values())
    probe = asyncio.run(runtime.refresh())
    assert probe.rows_available == 2 and all(state is AnalysisStatus.READY for state in probe.panel_states.values())
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave63_runtime_empty_context_uses_standard_empty_state_not_plausible_values():
    s = source('empty')
    runtime = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', s))
    runtime.set_manufacturing_filter('chamber','DOES_NOT_EXIST')
    probe = asyncio.run(runtime.refresh())
    assert probe.readiness is RuntimeReadiness.DEGRADED and probe.rows_available == 0
    assert all(state is AnalysisStatus.EMPTY for state in probe.panel_states.values())
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave63_runtime_records_are_bounded_and_respect_shared_context():
    s = source('records')
    runtime = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', s, policy=RecipeRuntimePolicy(record_page_size=1)))
    runtime.set_manufacturing_filter('chamber','A')
    result = asyncio.run(runtime.records())
    assert len(result.rows) == 1 and result.filtered_total == 2
    with pytest.raises(ValueError): asyncio.run(runtime.records(limit=10001))
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave63_runtime_applies_governed_initial_filters_and_rejects_unavailable_initial_filter():
    s = source('initial')
    custom = RecipeCustomization(initial_filters={'product':'P1','chamber':'A'})
    runtime = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', s, customization=custom))
    assert runtime.assembly.semiconductor.get('product') == 'P1'
    assert runtime.assembly.semiconductor.get('chamber') == 'A'
    assert asyncio.run(runtime.refresh()).rows_available == 2
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())
    small = InMemoryDataSource('small', ({'value':1.0},))
    with pytest.raises(KeyError, match='initial manufacturing filters unavailable'):
        asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', small, customization=RecipeCustomization(initial_filters={'product':'P1'}), policy=RecipeRuntimePolicy(strict_bindings=False)))
    asyncio.run(small.aclose())


def test_wave63_generated_variant_app_contains_adapter_config_and_shared_runtime(tmp_path: Path):
    root = tmp_path/'spc'
    created = create_application(root, name='SPC Runtime', recipe='spc-monitor', recipe_variant='spc-monitor-fast-response')
    assert created.recipe_variant == 'spc-monitor-fast-response'
    assert (root/'services'/'data_adapter.py').exists() and (root/'recipe_config.py').exists()
    assert "recipe_variant = 'spc-monitor-fast-response'" in (root/'nicegui_base.toml').read_text()
    home = load_home(root)
    assert home._CONFIGURATION.variant_key == 'spc-monitor-fast-response'
    runtime = asyncio.run(home.prepare_runtime())
    assert runtime.context is home._CONTEXT and runtime.selections is home._SELECTIONS
    assert asyncio.run(runtime.refresh()).readiness is RuntimeReadiness.READY
    asyncio.run(runtime.aclose())


def test_wave63_factory_rejects_variant_recipe_mismatch_and_variant_without_recipe(tmp_path: Path):
    with pytest.raises(ValueError, match='belongs to'):
        create_application(tmp_path/'bad1', name='Bad One', recipe='spc-monitor', recipe_variant='pm-recovery')
    with pytest.raises(ValueError, match='requires a semiconductor recipe'):
        create_application(tmp_path/'bad2', name='Bad Two', recipe_variant='spc-monitor-fast-response')


def test_wave63_generated_app_passes_existing_application_gate(tmp_path: Path):
    root = tmp_path/'pm'
    create_application(root, name='PM Runtime', recipe='pm-effect-analysis', recipe_variant='pm-recovery')
    report = run_application_gate(root)
    assert report.passed, report.to_dict()



def test_wave63_agent_context_recommends_recipe_variant_and_factory_command():
    from nicegui_base.ai.context import build_agent_context, render_agent_context
    pack = build_agent_context('compare chambers after PM')
    assert pack.starter_recipe == 'pm-effect-analysis'
    assert pack.starter_recipe_variant == 'pm-recovery'
    rendered = render_agent_context(pack)
    assert '--recipe pm-effect-analysis --variant pm-recovery' in rendered
    assert pack.to_dict()['starter_recipe_variant'] == 'pm-recovery'


def test_wave63_framework_catalog_and_registry_publish_variants_and_runtime_guide():
    from nicegui_base.ai import FRAMEWORK_REGISTRY_COUNTS, load_framework_catalog
    from nicegui_base.ai.scaffold import GUIDE_NAMES
    catalog = load_framework_catalog()
    assert catalog['registry_counts']['semiconductor_recipe_variants'] == 8
    assert FRAMEWORK_REGISTRY_COUNTS['semiconductor_recipe_variants'] == 8
    assert {item['_registry_key'] for item in catalog['registries']['semiconductor_recipe_variants']} == set(SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY)
    assert all(item['variants'] for item in catalog['registries']['semiconductor_recipes'])
    assert 'SEMICONDUCTOR_RUNTIME_ONBOARDING.md' in GUIDE_NAMES


def test_wave63_resolver_keeps_wave62_behavior_by_default_but_can_disable_implicit_resolution():
    from nicegui_base import resolve_recipe_source
    schema = DataSchema((SemanticField('metric_a', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT),))
    assert resolve_recipe_source('spc-monitor', schema).bindings['measurement'] == 'metric_a'
    safe = resolve_recipe_source('spc-monitor', schema, semantic_role_fallback=False, resolve_unoverridden=False)
    assert 'measurement' in safe.missing_required

def test_wave63_no_new_mandatory_dependency():
    requirements = [line.strip() for line in Path(__file__).resolve().parents[1].joinpath('requirements.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    assert requirements == ['nicegui==3.15.0']
