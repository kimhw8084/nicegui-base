from __future__ import annotations

import asyncio
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

from nicegui_base import (
    AdaptedSemiconductorSource,
    DataSchema,
    FieldRole,
    FieldType,
    InMemoryDataSource,
    OperationalSeverity,
    PopulationDefinition,
    ProviderAdapterManifest,
    ProviderConformanceFixture,
    ProviderConformanceSuiteReport,
    SEMICONDUCTOR_BENCHMARK_PROFILES,
    SEMICONDUCTOR_RECIPE_REGISTRY,
    RECIPE_OPERATIONAL_GUARDRAILS,
    SemanticField,
    SemiconductorProviderAdapterBase,
    SetupStepStatus,
    TargetGateStatus,
    build_semiconductor_target_evidence_bundle,
    capture_target_evidence_artifact,
    create_semiconductor_recipe_runtime,
    deserialize_semiconductor_target_evidence,
    get_recipe_operational_guardrails,
    load_provider_fixtures,
    load_semiconductor_adapter,
    provider_adapter_template_source,
    provider_fixture_template,
    provider_report_guidance,
    read_semiconductor_target_evidence,
    run_provider_conformance_suite,
    run_semiconductor_adapter_conformance,
    run_semiconductor_runtime_benchmark,
    serialize_semiconductor_target_evidence,
    write_semiconductor_target_evidence,
)
from nicegui_base.ai.gate import run_application_gate
from nicegui_base.ai.project import create_application
from nicegui_base.data_sources import SQLiteDataSource
from nicegui_base.semiconductor.provider_cli import provider_check_main, provider_init_main


ROWS = (
    {'id':'M1','timestamp':'2026-08-29T08:00:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':-1.0,'y':0.0,'value':10.0,'sensor':'pressure','sensor_value':1.0,'bin':'PASS','count':95.0,'yield_pct':99.1,'category':'PASS','defect_class':'none'},
    {'id':'M2','timestamp':'2026-08-29T08:01:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':0.0,'y':0.0,'value':10.4,'sensor':'pressure','sensor_value':1.2,'bin':'B1','count':3.0,'yield_pct':98.7,'category':'B1','defect_class':'particle'},
    {'id':'M3','timestamp':'2026-08-29T08:02:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'B','lot':'L2','wafer':'W02','x':1.0,'y':0.0,'value':9.9,'sensor':'pressure','sensor_value':1.1,'bin':'B2','count':2.0,'yield_pct':99.0,'category':'B2','defect_class':'scratch'},
)


def memory_source(key='wave65'):
    return InMemoryDataSource(key, ROWS)


class FixtureProvider(SemiconductorProviderAdapterBase):
    manifest = ProviderAdapterManifest('fixture-provider','Fixture Provider', supported_recipes=('spc-monitor','yield-loss'))
    def __init__(self):
        self.opened = []
    async def build_source(self, recipe):
        source = memory_source(f'fixture-{recipe.key}')
        self.opened.append(source)
        return source


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
    ), key='measurements', revision='wave65-benchmark-v1')


def large_sqlite(path: Path, rows: int = 12_000) -> SQLiteDataSource:
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE measurements (id TEXT, timestamp TEXT, product TEXT, route TEXT, operation TEXT, tool TEXT, chamber TEXT, lot TEXT, wafer TEXT, value REAL)')
        connection.executemany(
            'INSERT INTO measurements VALUES (?,?,?,?,?,?,?,?,?,?)',
            ((f'M{i}',f'2026-08-29T08:{i%60:02d}:00',f'P{i%4}',f'R{i%2}',f'OP{i%8}',f'T{i%12}',chr(65+i%4),f'L{i//25}',f'W{i%25:02d}',10.0+(i%17)/100.0) for i in range(rows)),
        )
        connection.execute('CREATE INDEX idx_wave65_context ON measurements(product,operation,tool,chamber)')
        connection.commit()
    return SQLiteDataSource('wave65-large', str(path), 'measurements', schema=sqlite_schema())


def load_home(root: Path, name='wave65_generated'):
    spec=importlib.util.spec_from_file_location(name, root/'pages'/'home.py'); assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); old=list(sys.path)
    try:
        for loaded in tuple(sys.modules):
            if loaded == 'recipe_config' or loaded == 'services' or loaded.startswith('services.'):
                sys.modules.pop(loaded,None)
        sys.path.insert(0,str(root)); spec.loader.exec_module(module)
    finally:
        sys.path[:]=old
    return module


def test_wave65_provider_manifest_is_governed_and_recipe_aware():
    manifest=ProviderAdapterManifest('approved-db','Approved DB','2',('spc-monitor',),metadata={'owner':'data'})
    assert manifest.supports('spc-monitor') and not manifest.supports('yield-loss')
    assert manifest.to_dict()['metadata']['owner']=='data'
    with pytest.raises(KeyError): ProviderAdapterManifest('bad','Bad',supported_recipes=('not-a-recipe',))
    with pytest.raises(ValueError): ProviderAdapterManifest('Bad Key','Bad')


def test_wave65_provider_base_returns_existing_datasource_authority_and_owns_it():
    adapter=FixtureProvider()
    adapted=asyncio.run(adapter.open(SEMICONDUCTOR_RECIPE_REGISTRY['spc-monitor']))
    assert isinstance(adapted, AdaptedSemiconductorSource)
    assert adapted.owns_source and adapted.source.provider == 'memory'
    assert adapted.metadata['provider_adapter']=='fixture-provider'
    asyncio.run(adapted.source.aclose())


def test_wave65_provider_base_rejects_undeclared_recipe():
    adapter=FixtureProvider()
    with pytest.raises(ValueError,match='does not declare support'):
        asyncio.run(adapter.open(SEMICONDUCTOR_RECIPE_REGISTRY['fdc-tool-health']))


def test_wave65_conformance_fixture_suite_closes_owned_sources_and_serializes():
    adapter=FixtureProvider()
    fixtures=(ProviderConformanceFixture('spc-dev','spc-monitor','development'), ProviderConformanceFixture('yield-dev','yield-loss','development'))
    suite=asyncio.run(run_provider_conformance_suite(adapter,fixtures))
    assert isinstance(suite,ProviderConformanceSuiteReport) and suite.passed
    assert all(source.closed for source in adapter.opened)
    json.dumps(suite.to_dict())


def test_wave65_provider_diagnostics_include_actionable_remediation():
    s=memory_source('prod-fail')
    report=asyncio.run(run_semiconductor_adapter_conformance('spc-monitor',s))
    guidance=provider_report_guidance(report)
    filter_item=next(item for item in guidance if item.code=='missing_filter_pushdown')
    assert 'backend' in filter_item.remediation.lower()
    assert filter_item.severity.value=='error'
    asyncio.run(s.aclose())


def test_wave65_provider_fixture_json_roundtrip(tmp_path: Path):
    payload=provider_fixture_template(recipes=('spc-monitor','yield-loss'),profile_key='development')
    path=tmp_path/'fixtures.json'; path.write_text(json.dumps(payload))
    fixtures=load_provider_fixtures(path)
    assert [item.recipe_key for item in fixtures]==['spc-monitor','yield-loss']
    assert all(item.profile_key=='development' for item in fixtures)


def test_wave65_provider_adapter_template_is_compilable_and_never_embeds_vendor_assumptions():
    source=provider_adapter_template_source(key='company-provider')
    compile(source,'data_adapter.py','exec')
    assert 'SemiconductorProviderAdapterBase' in source and 'build_source' in source
    for forbidden in ('kubernetes','snowflake','oracle','windows authentication'):
        assert forbidden not in source.casefold()


def test_wave65_provider_init_cli_writes_sdk_starter_and_fixture(tmp_path: Path):
    root=tmp_path/'provider'
    rc=provider_init_main(['nicegui-base provider-init',str(root),'--key','fab-provider','--recipe','yield-loss','--profile','development'])
    assert rc==0
    assert 'SemiconductorProviderAdapterBase' in (root/'data_adapter.py').read_text()
    fixtures=json.loads((root/'provider_fixtures.json').read_text())['fixtures']
    assert [item['recipe_key'] for item in fixtures]==['yield-loss']


def test_wave65_load_adapter_and_provider_check_cli_from_local_module(tmp_path: Path, capsys):
    mod=tmp_path/'local_provider.py'
    mod.write_text('''from nicegui_base import InMemoryDataSource, ProviderAdapterManifest, SemiconductorProviderAdapterBase\nclass Adapter(SemiconductorProviderAdapterBase):\n    manifest=ProviderAdapterManifest("local-provider","Local Provider",supported_recipes=("spc-monitor",))\n    async def build_source(self,recipe):\n        return InMemoryDataSource("local",({"value":1.0},{"value":2.0}))\n''')
    old=list(sys.path); sys.path.insert(0,str(tmp_path))
    try:
        adapter=load_semiconductor_adapter('local_provider:Adapter')
        assert adapter.key=='local-provider'
        out=tmp_path/'report.json'
        rc=provider_check_main(['nicegui-base provider-check','local_provider:Adapter','--recipe','spc-monitor','--profile','development','--format','json','--output',str(out)])
        assert rc==0 and json.loads(out.read_text())['passed']
    finally:
        sys.path[:]=old; sys.modules.pop('local_provider',None)


def test_wave65_development_benchmark_is_bounded_and_does_not_claim_representative_scale():
    s=memory_source('benchmark-dev'); runtime=asyncio.run(create_semiconductor_recipe_runtime('spc-monitor',s))
    report=asyncio.run(run_semiconductor_runtime_benchmark(runtime,profile='development-smoke'))
    assert report.passed and report.iterations==1
    assert all(item.max_rows_returned <= 3 for item in report.operation_summaries)
    assert SEMICONDUCTOR_BENCHMARK_PROFILES['development-smoke'].require_representative_scale is False
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave65_provider_rc_benchmark_rejects_small_or_nonpushdown_fixture():
    s=memory_source('benchmark-small'); runtime=asyncio.run(create_semiconductor_recipe_runtime('spc-monitor',s))
    report=asyncio.run(runtime.benchmark(profile='provider-rc'))
    codes={item.code for item in report.errors}
    assert 'benchmark_scale_not_representative' in codes
    assert any('pushdown' in code for code in codes)
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave65_provider_rc_benchmark_passes_large_sqlite_with_observed_pushdown(tmp_path: Path):
    s=large_sqlite(tmp_path/'fab.db'); runtime=asyncio.run(create_semiconductor_recipe_runtime('spc-monitor',s))
    report=asyncio.run(runtime.benchmark(profile='provider-rc'))
    assert report.passed, report.to_dict()
    assert report.operation_summaries and all(item.pushdown_rate==1.0 for item in report.operation_summaries)
    assert max(item.max_filtered_total for item in report.operation_summaries) >= 12_000
    json.dumps(report.to_dict())
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave65_operational_guardrails_cover_every_recipe():
    assert set(RECIPE_OPERATIONAL_GUARDRAILS)==set(SEMICONDUCTOR_RECIPE_REGISTRY)
    assert all(get_recipe_operational_guardrails(key) for key in SEMICONDUCTOR_RECIPE_REGISTRY)


def test_wave65_spc_configuration_review_is_runnable_but_not_release_ready_without_evidence():
    s=memory_source('review-spc'); runtime=asyncio.run(create_semiconductor_recipe_runtime('spc-monitor',s))
    review=runtime.configuration_review()
    assert review.safe_to_run and not review.safe_to_promote
    assert any(item.guardrail_key.endswith('provider-conformance') and item.severity is OperationalSeverity.WARNING for item in review.warnings)
    json.dumps(review.to_dict())
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave65_excursion_guardrails_block_until_affected_and_control_populations_exist():
    s=memory_source('review-excursion'); runtime=asyncio.run(create_semiconductor_recipe_runtime('excursion-defense-line',s))
    review=runtime.configuration_review()
    assert not review.safe_to_run
    codes={item.guardrail_key for item in review.blocking}
    assert {'excursion-defense-line:affected','excursion-defense-line:control'} <= codes
    runtime.context.set_affected(PopulationDefinition('affected')); runtime.context.set_control(PopulationDefinition('control'))
    assert runtime.configuration_review().safe_to_run
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave65_setup_workflow_distinguishes_runnable_from_release_ready():
    s=memory_source('setup'); runtime=asyncio.run(create_semiconductor_recipe_runtime('spc-monitor',s))
    workflow=asyncio.run(runtime.prepare_setup_workflow())
    assert workflow.ready_to_run and not workflow.ready_for_release
    assert workflow.steps[-1].status is SetupStepStatus.PENDING
    assert {'conformance','benchmark','target-certification'} <= {item.key for item in workflow.steps if item.status is SetupStepStatus.PENDING}
    json.dumps(workflow.to_dict())
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave65_setup_workflow_blocks_incompatible_operational_population_even_when_bindings_are_ready():
    s=memory_source('setup-rca'); runtime=asyncio.run(create_semiconductor_recipe_runtime('rca-cockpit',s))
    workflow=asyncio.run(runtime.prepare_setup_workflow())
    assert not workflow.ready_to_run and workflow.blocked
    config=next(item for item in workflow.steps if item.key=='configuration')
    assert config.status is SetupStepStatus.BLOCKED
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave65_target_evidence_bundle_keeps_benchmark_and_external_gates_pending_by_default(tmp_path: Path):
    s=memory_source('evidence-pending'); runtime=asyncio.run(create_semiconductor_recipe_runtime('spc-monitor',s))
    bundle=build_semiconductor_target_evidence_bundle('spc-monitor')
    assert not bundle.promotable
    pending={item.key for item in bundle.certification.pending}
    assert 'provider_benchmark' in pending and 'supported_browser' in pending and 'company_adapter' in pending
    assert bundle.metadata['framework_version'] and bundle.metadata['nicegui_required']=='3.15.0'
    encoded=serialize_semiconductor_target_evidence(bundle)
    decoded=deserialize_semiconductor_target_evidence(encoded)
    assert decoded.recipe_key=='spc-monitor' and not decoded.promotable
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave65_target_evidence_artifact_hash_and_file_roundtrip(tmp_path: Path):
    artifact_file=tmp_path/'browser.json'; artifact_file.write_text('{"pass":true}\n')
    artifact=capture_target_evidence_artifact(artifact_file,key='browser-smoke',description='target browser result')
    bundle=build_semiconductor_target_evidence_bundle('spc-monitor',artifacts=(artifact,))
    output=tmp_path/'evidence.json'; write_semiconductor_target_evidence(output,bundle)
    loaded=read_semiconductor_target_evidence(output)
    assert loaded.artifacts[0].sha256==artifact.sha256 and loaded.artifacts[0].size_bytes==artifact_file.stat().st_size


def test_wave65_full_target_evidence_can_become_promotable_only_with_real_reports_and_explicit_external_passes(tmp_path: Path):
    s=large_sqlite(tmp_path/'cert.db'); conformance=asyncio.run(run_semiconductor_adapter_conformance('spc-monitor',s))
    runtime=asyncio.run(create_semiconductor_recipe_runtime('spc-monitor',s))
    performance=asyncio.run(runtime.performance_report())
    benchmark=asyncio.run(runtime.benchmark(profile='provider-rc'))
    assert conformance.passed and performance.passed and benchmark.passed
    bundle=build_semiconductor_target_evidence_bundle(
        'spc-monitor',adapter_conformance=conformance,performance=performance,benchmark=benchmark,
        installed_nicegui_pass=True,server_websocket_pass=True,browser_pass=True,human_visual_baseline_pass=True,
    )
    assert bundle.promotable and not bundle.certification.pending and not bundle.certification.failed
    assert next(item for item in bundle.certification.gates if item.key=='provider_benchmark').status is TargetGateStatus.PASS
    asyncio.run(runtime.aclose()); asyncio.run(s.aclose())


def test_wave65_generated_recipe_starter_contains_guided_setup_provider_fixture_and_release_evidence(tmp_path: Path):
    root=tmp_path/'generated'; create_application(root,name='SPC RC',recipe='spc-monitor',recipe_variant='spc-monitor-fast-response')
    assert (root/'services'/'provider_fixtures.json').exists()
    assert 'SemiconductorProviderAdapterBase' in (root/'services'/'data_adapter.py').read_text()
    assert 'build_semiconductor_target_evidence_bundle' in (root/'services'/'release_evidence.py').read_text()
    assert 'BENCHMARK_PROFILE' in (root/'recipe_config.py').read_text()
    home=load_home(root)
    runtime,workflow=asyncio.run(home.prepare_guided_setup())
    assert workflow.ready_to_run and not workflow.ready_for_release
    asyncio.run(runtime.aclose())
    gate=run_application_gate(root)
    assert gate.passed,gate.to_dict()


def test_wave65_generated_guided_setup_can_attach_development_conformance_and_benchmark(tmp_path: Path):
    root=tmp_path/'generated2'; create_application(root,name='SPC Setup',recipe='spc-monitor')
    home=load_home(root,'wave65_generated2')
    runtime,workflow=asyncio.run(home.prepare_guided_setup(include_conformance=True,include_benchmark=True))
    assert next(item for item in workflow.steps if item.key=='conformance').status is SetupStepStatus.COMPLETE
    assert next(item for item in workflow.steps if item.key=='benchmark').status is SetupStepStatus.COMPLETE
    assert not workflow.ready_for_release
    asyncio.run(runtime.aclose())


def test_wave65_no_new_mandatory_dependency():
    requirements=[line.strip() for line in Path(__file__).resolve().parents[1].joinpath('requirements.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    assert requirements==['nicegui==3.15.0']


def test_wave65_machine_catalog_publishes_provider_benchmark_guardrail_and_recipe_guidance():
    root=Path(__file__).resolve().parents[1]
    catalog=json.loads(root.joinpath('FRAMEWORK_CATALOG.json').read_text())
    registries=catalog['registries']
    assert len(registries['semiconductor_provider_profiles'])==2
    assert len(registries['semiconductor_benchmark_profiles'])==2
    assert len(registries['semiconductor_operational_guardrails'])==sum(len(items) for items in RECIPE_OPERATIONAL_GUARDRAILS.values())
    assert catalog['registry_counts']['semiconductor_operational_guardrails']==26
    assert all(item['provider_sdk'] and item['guided_setup'] and item['provider_benchmark'] and item['target_evidence'] for item in registries['semiconductor_recipes'])


def test_wave65_construction_manifest_and_agent_guide_are_additive_without_schema_break():
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads(root.joinpath('AI_CONSTRUCTION_MANIFEST.json').read_text())
    assert manifest['schema_version']==6
    assert manifest['wave65_semiconductor_provider_sdk_rc']['provider_profiles']=='registries.semiconductor_provider_profiles'
    from nicegui_base.ai.scaffold import GUIDE_NAMES
    assert 'SEMICONDUCTOR_PROVIDER_SDK_RC.md' in GUIDE_NAMES
    assert root.joinpath('nicegui_base/ai/guides/SEMICONDUCTOR_PROVIDER_SDK_RC.md').is_file()


def test_wave65_golden_provider_sdk_release_candidate_example_executes():
    root=Path(__file__).resolve().parents[1]
    path=root/'examples'/'phase65_provider_sdk_release_candidate.py'
    spec=importlib.util.spec_from_file_location('wave65_provider_sdk_example',path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    result=asyncio.run(module.main())
    assert result['provider_suite_passed'] and result['runtime_ready_to_run']
    assert not result['runtime_release_ready'] and not result['target_promotable']
    assert 'supported_browser' in result['pending_target_gates']


def test_wave65_source_evidence_declares_phase65_without_target_pass_claims(tmp_path: Path):
    from nicegui_base.governance.source_evidence import _sync_packaged_certification_manifest
    from nicegui_base.certification.mac_coverage import coverage_summary
    source=Path(__file__).resolve().parents[1]/'nicegui_base/certification/certification_manifest.json'
    target_root=tmp_path
    target=target_root/'nicegui_base/certification/certification_manifest.json'; target.parent.mkdir(parents=True)
    target.write_text(source.read_text())
    _sync_packaged_certification_manifest(target_root,test_count=999,coverage=coverage_summary())
    payload=json.loads(target.read_text())
    assert payload['phase']>=65
    phase=payload['phase_65_v300a8_semiconductor_provider_sdk_onboarding_rc']
    assert phase['provider_sdk_reuses_wave59_datasource'] is True
    assert phase['target_runtime_browser_human_gates']=='PENDING FOR CURRENT SOURCE'
