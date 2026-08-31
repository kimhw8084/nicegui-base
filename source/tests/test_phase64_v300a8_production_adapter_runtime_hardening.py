from __future__ import annotations

import asyncio
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

from nicegui_base import (
    AdaptedSemiconductorSource, AdapterConformancePolicy, AnalysisStatus, ConformanceSeverity,
    DataSchema, FieldRole, FieldType, InMemoryDataSource, RecipeCustomization, RecipeRuntimePolicy,
    RuntimeExperienceStatus, RuntimePerformancePolicy, SEMICONDUCTOR_RECIPE_REGISTRY,
    SelectionKind, SemanticField, SourceCapabilities, TargetGateStatus,
    assert_semiconductor_adapter_conformance, build_recipe_onboarding_view,
    build_semiconductor_target_runtime_certification, create_semiconductor_recipe_runtime,
    deserialize_recipe_runtime_preset, onboard_recipe_source, probe_semiconductor_runtime_performance,
    recipe_runtime_preset_to_dict, run_semiconductor_adapter_conformance,
    serialize_recipe_runtime_preset,
)
from nicegui_base.ai.gate import run_application_gate
from nicegui_base.ai.project import create_application
from nicegui_base.data_sources import SQLiteDataSource


ROWS = (
    {'id':'M1','timestamp':'2026-08-29T08:00:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':-1.0,'y':0.0,'value':10.0,'sensor':'pressure','sensor_value':1.0,'bin':'PASS','count':95.0,'yield_pct':99.1,'category':'PASS','defect_class':'none'},
    {'id':'M2','timestamp':'2026-08-29T08:01:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':0.0,'y':0.0,'value':10.4,'sensor':'pressure','sensor_value':1.2,'bin':'B1','count':3.0,'yield_pct':98.7,'category':'B1','defect_class':'particle'},
    {'id':'M3','timestamp':'2026-08-29T08:02:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'B','lot':'L2','wafer':'W02','x':1.0,'y':0.0,'value':9.9,'sensor':'pressure','sensor_value':1.1,'bin':'B2','count':2.0,'yield_pct':99.0,'category':'B2','defect_class':'scratch'},
)


def source(key='wave64'):
    return InMemoryDataSource(key, ROWS)


class OwnedFixtureAdapter:
    key = 'fixture-adapter'
    def __init__(self):
        self.source = source('owned-fixture')
    async def open(self, recipe):
        return AdaptedSemiconductorSource(self.source, metadata={'adapter':'fixture'}, owns_source=True)


class LyingPushdownSource(InMemoryDataSource):
    @property
    def capabilities(self):
        return SourceCapabilities(
            filter_pushdown=True, pagination_pushdown=True, projection_pushdown=True,
            distinct_pushdown=True, search_pushdown=True, sort_pushdown=True,
            aggregation_pushdown=True, cancellation=True,
        )


def sqlite_schema() -> DataSchema:
    return DataSchema((
        SemanticField('id', type=FieldType.STRING, role=FieldRole.IDENTIFIER),
        SemanticField('timestamp', type=FieldType.DATETIME, role=FieldRole.TIMESTAMP),
        SemanticField('product', type=FieldType.STRING, role=FieldRole.DIMENSION),
        SemanticField('route', type=FieldType.STRING, role=FieldRole.DIMENSION),
        SemanticField('operation', type=FieldType.STRING, role=FieldRole.DIMENSION),
        SemanticField('tool', type=FieldType.STRING, role=FieldRole.ENTITY),
        SemanticField('chamber', type=FieldType.STRING, role=FieldRole.ENTITY),
        SemanticField('lot', type=FieldType.STRING, role=FieldRole.ENTITY),
        SemanticField('wafer', type=FieldType.STRING, role=FieldRole.ENTITY),
        SemanticField('value', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT),
    ), key='measurements', revision='wave64-synthetic-v1')


def build_large_sqlite(path: Path, rows: int = 25_000) -> SQLiteDataSource:
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE measurements (id TEXT, timestamp TEXT, product TEXT, route TEXT, operation TEXT, tool TEXT, chamber TEXT, lot TEXT, wafer TEXT, value REAL)')
        batch = (
            (f'M{i}', f'2026-08-29T08:{i%60:02d}:00', f'P{i%4}', f'R{i%2}', f'OP{i%8}', f'T{i%12}', chr(65+i%4), f'L{i//25}', f'W{i%25:02d}', 10.0 + (i%17)/100.0)
            for i in range(rows)
        )
        connection.executemany('INSERT INTO measurements VALUES (?,?,?,?,?,?,?,?,?,?)', batch)
        connection.execute('CREATE INDEX idx_measurements_context ON measurements(product, operation, tool, chamber)')
        connection.commit()
    return SQLiteDataSource('large-synthetic', str(path), 'measurements', schema=sqlite_schema())


def load_home(root: Path, name='wave64_generated'):
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


def test_wave64_direct_inmemory_source_fails_production_conformance_without_closing_caller_source():
    s = source('direct')
    report = asyncio.run(run_semiconductor_adapter_conformance('spc-monitor', s))
    assert not report.passed
    assert {'missing_filter_pushdown','missing_pagination_pushdown'} <= {item.code for item in report.errors}
    assert not s.closed and not report.source_closed_after_probe
    with pytest.raises(RuntimeError):
        assert_semiconductor_adapter_conformance(report)
    asyncio.run(s.aclose())


def test_wave64_owned_fixture_adapter_can_use_relaxed_development_policy_and_is_closed_after_probe():
    adapter = OwnedFixtureAdapter()
    report = asyncio.run(run_semiconductor_adapter_conformance(
        'spc-monitor', adapter,
        policy=AdapterConformancePolicy(require_filter_pushdown=False, require_pagination_pushdown=False),
    ))
    assert report.passed
    assert report.source_closed_after_probe and adapter.source.closed
    assert report.observations and max(item.rows_returned for item in report.observations) <= 2
    json.dumps(report.to_dict())


def test_wave64_provider_capability_claims_are_audited_not_trusted():
    s = LyingPushdownSource('liar', ROWS)
    report = asyncio.run(run_semiconductor_adapter_conformance('spc-monitor', s))
    assert not report.passed
    codes = {item.code for item in report.errors}
    assert 'pagination_pushdown_not_observed' in codes
    assert 'filter_pushdown_not_observed' in codes
    assert 'projection_pushdown_not_observed' in codes
    assert 'distinct_pushdown_not_observed' in codes
    asyncio.run(s.aclose())


def test_wave64_onboarding_view_turns_ambiguity_into_explicit_blocking_action():
    schema = DataSchema((
        SemanticField('metric_a', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT),
        SemanticField('metric_b', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT),
    ))
    s = InMemoryDataSource('ambiguous', ({'metric_a':1.0,'metric_b':2.0},), schema=schema)
    report = asyncio.run(onboard_recipe_source('spc-monitor', s))
    view = build_recipe_onboarding_view('spc-monitor', report)
    measurement = next(item for item in view.fields if item.logical_field == 'measurement')
    assert measurement.state.value == 'ambiguous' and measurement.source_field is None
    assert view.unresolved_required == ('measurement',)
    assert any('Choose the source field for measurement' in item for item in view.blocking_actions)
    json.dumps(view.to_dict())
    asyncio.run(s.aclose())


def test_wave64_onboarding_view_rejects_report_for_another_recipe():
    s = source('mismatch')
    report = asyncio.run(onboard_recipe_source('spc-monitor', s))
    with pytest.raises(ValueError, match='onboarding report is for'):
        build_recipe_onboarding_view('yield-loss', report)
    asyncio.run(s.aclose())


@pytest.mark.parametrize('recipe_key', tuple(SEMICONDUCTOR_RECIPE_REGISTRY))
def test_wave64_all_eight_recipes_expose_one_shared_runtime_experience_contract(recipe_key: str):
    s = source(recipe_key)
    runtime = asyncio.run(create_semiconductor_recipe_runtime(recipe_key, s))
    initial = runtime.experience_state()
    assert initial.status in {RuntimeExperienceStatus.READY, RuntimeExperienceStatus.STALE}
    probe = asyncio.run(runtime.refresh())
    ready = runtime.experience_state(probe)
    assert ready.status is RuntimeExperienceStatus.READY
    assert ready.recipe_key == recipe_key and ready.provider == 'memory'
    assert ready.panel_states
    json.dumps(ready.to_dict())
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave64_runtime_experience_standardizes_stale_and_empty_states():
    s = source('states')
    runtime = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', s))
    asyncio.run(runtime.refresh())
    runtime.set_manufacturing_filter('chamber','DOES_NOT_EXIST')
    assert runtime.experience_state().status is RuntimeExperienceStatus.STALE
    probe = asyncio.run(runtime.refresh())
    assert runtime.experience_state(probe).status is RuntimeExperienceStatus.EMPTY
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave64_runtime_preset_roundtrip_reuses_context_selection_and_workspace_snapshots():
    s = source('preset')
    runtime = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', s))
    runtime.set_manufacturing_filter('chamber','A')
    runtime.select(SelectionKind.ENTITY, 'chamber:A', {'chamber':'A'})
    panel_id = next(iter(runtime.assembly.workspace.layout.panels))
    runtime.assembly.workspace.collapse(panel_id, True)
    preset = runtime.capture_preset('Chamber A review', metadata={'owner':'process'})
    encoded = serialize_recipe_runtime_preset(preset)
    decoded = deserialize_recipe_runtime_preset(encoded)
    assert recipe_runtime_preset_to_dict(decoded)['recipe_key'] == 'spc-monitor'

    runtime.set_manufacturing_filter('chamber','B')
    runtime.selections.clear()
    runtime.assembly.workspace.collapse(panel_id, False)
    asyncio.run(runtime.restore_preset(decoded))
    assert runtime.assembly.semiconductor.get('chamber') == 'A'
    assert runtime.selections.by_kind(SelectionKind.ENTITY)[0].selection_id == 'chamber:A'
    assert runtime.assembly.workspace.state(panel_id).collapsed
    assert runtime.context.source_key == s.key
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave64_runtime_preset_rejects_recipe_and_variant_mismatch():
    s1 = source('preset1'); s2 = source('preset2')
    r1 = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', s1, variant='spc-monitor-fast-response'))
    p = r1.capture_preset('focused')
    r2 = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', s2))
    with pytest.raises(ValueError, match='variant'):
        asyncio.run(r2.restore_preset(p))
    r3s = source('preset3')
    r3 = asyncio.run(create_semiconductor_recipe_runtime('yield-loss', r3s))
    with pytest.raises(ValueError, match='recipe'):
        asyncio.run(r3.restore_preset(p, strict_variant=False))
    for runtime in (r1,r2,r3): asyncio.run(runtime.aclose())
    for src in (s1,s2,r3s): asyncio.run(src.aclose())


def test_wave64_large_synthetic_sqlite_adapter_conformance_and_runtime_pushdown(tmp_path: Path):
    s = build_large_sqlite(tmp_path/'fab.db')
    conformance = asyncio.run(run_semiconductor_adapter_conformance('spc-monitor', s))
    assert conformance.passed, conformance.to_dict()
    assert conformance.observations and all(item.rows_returned <= 2 for item in conformance.observations)
    assert all(item.stats.pushdown for item in conformance.observations)

    runtime = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', s))
    runtime.set_manufacturing_filter('product','P1')
    perf = asyncio.run(probe_semiconductor_runtime_performance(runtime, policy=RuntimePerformancePolicy(page_size=3)))
    assert perf.passed, perf.to_dict()
    assert all(item.rows_returned <= 3 for item in perf.observations)
    assert all(item.pushdown and item.rows_scanned is None for item in perf.observations)
    assert max(item.filtered_total for item in perf.observations) >= 6_000
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave64_inmemory_runtime_performance_does_not_get_false_production_pass():
    s = source('perf-memory')
    runtime = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', s))
    report = asyncio.run(runtime.performance_report())
    assert not report.passed
    codes = {item.code for item in report.errors}
    assert {'missing_filter_pushdown','missing_pagination_pushdown','missing_projection_pushdown'} <= codes
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave64_target_runtime_certification_keeps_missing_external_execution_pending(tmp_path: Path):
    s = build_large_sqlite(tmp_path/'cert.db', rows=5_000)
    conformance = asyncio.run(run_semiconductor_adapter_conformance('spc-monitor', s))
    runtime = asyncio.run(create_semiconductor_recipe_runtime('spc-monitor', s))
    performance = asyncio.run(runtime.performance_report())
    cert = build_semiconductor_target_runtime_certification('spc-monitor', adapter_conformance=conformance, performance=performance)
    assert not cert.promotable
    assert {item.key for item in cert.pending} == {'installed_nicegui','server_websocket','supported_browser','human_visual_baseline'}
    assert all(item.status is TargetGateStatus.PENDING for item in cert.pending)
    promoted = build_semiconductor_target_runtime_certification(
        'spc-monitor', adapter_conformance=conformance, performance=performance,
        installed_nicegui_pass=True, server_websocket_pass=True, browser_pass=True, human_visual_baseline_pass=True,
    )
    assert promoted.promotable and not promoted.pending and not promoted.failed
    json.dumps(promoted.to_dict())
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave64_generated_recipe_starter_exposes_runtime_setup_and_adapter_conformance(tmp_path: Path):
    root = tmp_path/'spc'
    create_application(root, name='SPC Production', recipe='spc-monitor', recipe_variant='spc-monitor-fast-response')
    assert 'conformance_report' in (root/'services'/'data_adapter.py').read_text()
    home = load_home(root)
    runtime, onboarding, experience = asyncio.run(home.prepare_runtime_setup())
    assert onboarding.ready and experience.status is RuntimeExperienceStatus.READY
    asyncio.run(runtime.aclose())
    gate = run_application_gate(root)
    assert gate.passed, gate.to_dict()


def test_wave64_no_new_mandatory_dependency():
    requirements = [line.strip() for line in Path(__file__).resolve().parents[1].joinpath('requirements.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    assert requirements == ['nicegui==3.15.0']


def test_wave64_agent_catalog_and_scaffold_publish_production_runtime_contract():
    from nicegui_base.ai import load_framework_catalog
    from nicegui_base.ai.context import build_agent_context
    from nicegui_base.ai.scaffold import GUIDE_NAMES
    catalog = load_framework_catalog()
    entries = catalog['registries']['semiconductor_recipes']
    assert len(entries) == 8
    assert all(item['adapter_conformance'] == 'run_semiconductor_adapter_conformance()' for item in entries)
    assert all('performance_report' in item['runtime_performance'] for item in entries)
    assert 'SEMICONDUCTOR_PRODUCTION_RUNTIME.md' in GUIDE_NAMES
    context = build_agent_context('is chamber B drifting after PM?')
    assert 'examples/phase64_production_adapter_runtime.py' in context.golden_examples


def test_wave64_construction_manifest_keeps_schema_compatible_and_adds_production_contract():
    payload = json.loads(Path(__file__).resolve().parents[1].joinpath('nicegui_base/ai/construction_manifest.json').read_text())
    assert payload['schema_version'] == 6
    wave = payload['wave64_semiconductor_production_hardening']
    assert 'run_semiconductor_adapter_conformance' in wave['adapter_conformance']
    assert 'PENDING' in wave['target_certification']
