from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from nicegui_base import (
    ArtifactIntegrityStatus,
    EvidenceFreshnessPolicy,
    EvidenceFreshnessStatus,
    FRAMEWORK_VERSION,
    InMemoryDataSource,
    NICEGUI_VERSION,
    OperationalReadinessCheck,
    OperationalReadinessState,
    PromotionDecisionStatus,
    PromotionPolicy,
    SemiconductorOperationalReadiness,
    SemiconductorTargetEvidenceBundle,
    SemiconductorTargetRuntimeCertification,
    TargetEnvironmentFingerprint,
    TargetGateStatus,
    TargetRuntimeGate,
    assess_evidence_freshness,
    assess_semiconductor_operational_readiness,
    assess_target_evidence_traceability,
    build_provider_qualification_pack,
    build_semiconductor_operational_runbook,
    build_semiconductor_promotion_decision,
    capture_target_evidence_artifact,
    create_semiconductor_recipe_runtime,
    provider_qualification_pack_from_dict,
    provider_qualification_pack_to_dict,
    verify_target_evidence_artifacts,
)
from nicegui_base.semiconductor.recipes import SEMICONDUCTOR_RECIPE_REGISTRY


ROWS = (
    {'id':'M1','timestamp':'2026-08-29T08:00:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':-1.0,'y':0.0,'value':10.0,'sensor':'pressure','sensor_value':1.0,'bin':'PASS','count':95.0,'yield_pct':99.1,'category':'PASS','defect_class':'none'},
    {'id':'M2','timestamp':'2026-08-29T08:01:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':0.0,'y':0.0,'value':10.4,'sensor':'pressure','sensor_value':1.2,'bin':'B1','count':3.0,'yield_pct':98.7,'category':'B1','defect_class':'particle'},
)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def make_bundle(tmp_path: Path, *, recipe='spc-monitor', provider='sqlite', source_key='target', captured_at: str | None = None, traced=True, fail_gate: str | None = None, pending_gate: str | None = None):
    gate_defs=(
        ('company_adapter','Approved company adapter conformance'),
        ('fab_scale_pushdown','Representative fab-scale pushdown/performance'),
        ('installed_nicegui','Installed NiceGUI 3.15.0'),
        ('server_websocket','Real server/WebSocket lifecycle'),
        ('supported_browser','Supported corporate browser'),
        ('human_visual_baseline','Human visual baseline'),
        ('provider_benchmark','Governed representative provider benchmark'),
    )
    gates=[]
    for key,label in gate_defs:
        status = TargetGateStatus.FAIL if key==fail_gate else (TargetGateStatus.PENDING if key==pending_gate else TargetGateStatus.PASS)
        gates.append(TargetRuntimeGate(key,label,status,f'{key} evidence'))
    artifacts=[]
    if traced:
        for key in ('installed_nicegui','server_websocket','supported_browser','human_visual_baseline'):
            path=tmp_path/f'{recipe}-{key}.json'; path.write_text(json.dumps({'gate':key,'pass':True})+'\n')
            artifacts.append(capture_target_evidence_artifact(path,key=key,description=f'{key} target evidence'))
    return SemiconductorTargetEvidenceBundle(
        recipe,
        SemiconductorTargetRuntimeCertification(recipe,tuple(gates)),
        TargetEnvironmentFingerprint('3.12.0','test-platform','3.15.0','python'),
        tuple(artifacts),
        {'profile_key':'provider-rc','provider':provider,'source_key':source_key,'passed':True},
        {'provider':provider,'source_key':source_key,'passed':True},
        {'provider':provider,'source_key':source_key,'passed':True},
        {'framework_version': FRAMEWORK_VERSION, 'nicegui_required': NICEGUI_VERSION},
        captured_at or _iso(datetime.now(timezone.utc)),
        1,
    )


def ready_ops(recipe='spc-monitor', provider='sqlite', source_key='target'):
    check=OperationalReadinessCheck('all','All operational gates',OperationalReadinessState.READY,'Operational gates passed.',required_for_run=True,required_for_release=True)
    return SemiconductorOperationalReadiness(recipe,source_key,provider,(check,))


def test_wave66_freshness_current_stale_future_and_timezone_validation(tmp_path: Path):
    now=datetime(2026,8,29,18,0,tzinfo=timezone.utc)
    current=make_bundle(tmp_path,captured_at=_iso(now-timedelta(hours=2)))
    stale=replace(current,captured_at=_iso(now-timedelta(hours=169)))
    future=replace(current,captured_at=_iso(now+timedelta(minutes=10)))
    invalid=replace(current,captured_at='2026-08-29T18:00:00')
    assert assess_evidence_freshness(current,now=now).status is EvidenceFreshnessStatus.CURRENT
    assert assess_evidence_freshness(stale,now=now).status is EvidenceFreshnessStatus.STALE
    assert assess_evidence_freshness(future,now=now).status is EvidenceFreshnessStatus.FUTURE
    assert assess_evidence_freshness(invalid,now=now).status is EvidenceFreshnessStatus.INVALID


def test_wave66_freshness_policy_is_explicit_and_validated():
    assert EvidenceFreshnessPolicy(max_age_hours=24).max_age_hours==24
    with pytest.raises(ValueError): EvidenceFreshnessPolicy(max_age_hours=0)
    with pytest.raises(ValueError): EvidenceFreshnessPolicy(max_future_skew_minutes=-1)


def test_wave66_artifact_integrity_detects_verified_tampered_and_missing(tmp_path: Path):
    bundle=make_bundle(tmp_path)
    assert all(item.status is ArtifactIntegrityStatus.VERIFIED for item in verify_target_evidence_artifacts(bundle))
    Path(bundle.artifacts[0].path).write_text('tampered')
    findings=verify_target_evidence_artifacts(bundle)
    assert findings[0].status is ArtifactIntegrityStatus.HASH_MISMATCH
    Path(bundle.artifacts[1].path).unlink()
    findings=verify_target_evidence_artifacts(bundle)
    assert findings[1].status is ArtifactIntegrityStatus.MISSING


def test_wave66_external_passes_require_traceability_for_stable_promotion(tmp_path: Path):
    bundle=make_bundle(tmp_path,traced=False)
    trace=assess_target_evidence_traceability(bundle)
    assert set(trace.untraced_pass_gates)=={'installed_nicegui','server_websocket','supported_browser','human_visual_baseline'}
    assert trace.pending and not trace.valid_for_promotion


def test_wave66_gate_artifact_mapping_can_trace_external_pass(tmp_path: Path):
    path=tmp_path/'combined.json'; path.write_text('{}')
    artifact=capture_target_evidence_artifact(path,key='target-runtime-evidence')
    bundle=make_bundle(tmp_path,traced=False)
    bundle=replace(bundle,artifacts=(artifact,),metadata={'gate_artifacts':{key:'target-runtime-evidence' for key in ('installed_nicegui','server_websocket','supported_browser','human_visual_baseline')}})
    trace=assess_target_evidence_traceability(bundle)
    assert not trace.untraced_pass_gates and trace.valid_for_promotion


def test_wave66_provider_qualification_pack_is_deterministic_and_order_independent(tmp_path: Path):
    one=make_bundle(tmp_path,recipe='spc-monitor',source_key='s1')
    two=make_bundle(tmp_path,recipe='yield-loss',source_key='s2')
    left=build_provider_qualification_pack((one,two),provider='sqlite')
    right=build_provider_qualification_pack((two,one),provider='sqlite')
    assert left.qualification_id==right.qualification_id
    assert left.recipe_keys==('spc-monitor','yield-loss') and left.source_keys==('s1','s2')


def test_wave66_provider_qualification_rejects_mixed_provider_evidence(tmp_path: Path):
    one=make_bundle(tmp_path,provider='sqlite')
    two=make_bundle(tmp_path,recipe='yield-loss',provider='memory')
    with pytest.raises(ValueError,match='provider'):
        build_provider_qualification_pack((one,two))


def test_wave66_provider_qualification_selects_latest_bundle_per_recipe(tmp_path: Path):
    now=datetime.now(timezone.utc)
    old=make_bundle(tmp_path,captured_at=_iso(now-timedelta(hours=2)))
    newer=make_bundle(tmp_path,captured_at=_iso(now-timedelta(hours=1)))
    pack=build_provider_qualification_pack((old,newer),provider='sqlite')
    assert len(pack.bundles)==1 and pack.bundles[0].captured_at==newer.captured_at and pack.superseded_bundles==1


def test_wave66_provider_qualification_roundtrip_preserves_identity_and_traceability(tmp_path: Path):
    pack=build_provider_qualification_pack((make_bundle(tmp_path),),provider='sqlite')
    payload=provider_qualification_pack_to_dict(pack)
    decoded=provider_qualification_pack_from_dict(payload)
    assert decoded.qualification_id==pack.qualification_id
    assert decoded.traceability[0].valid_for_promotion==pack.traceability[0].valid_for_promotion
    json.dumps(payload)


def test_wave66_qualification_id_detects_payload_tampering(tmp_path: Path):
    pack=build_provider_qualification_pack((make_bundle(tmp_path),),provider='sqlite')
    payload=pack.to_dict(); payload['bundles'][0]['captured_at']='2026-01-01T00:00:00Z'
    with pytest.raises(ValueError,match='qualification_id'):
        provider_qualification_pack_from_dict(payload)


def test_wave66_promotion_is_pending_when_target_gate_is_pending(tmp_path: Path):
    pack=build_provider_qualification_pack((make_bundle(tmp_path,pending_gate='supported_browser'),),provider='sqlite')
    decision=build_semiconductor_promotion_decision(pack,operational_readiness={'spc-monitor':ready_ops()})
    assert decision.status is PromotionDecisionStatus.PENDING
    assert any(item.code=='target_gate_pending' for item in decision.findings)


def test_wave66_promotion_is_blocked_when_target_gate_fails(tmp_path: Path):
    pack=build_provider_qualification_pack((make_bundle(tmp_path,fail_gate='server_websocket'),),provider='sqlite')
    decision=build_semiconductor_promotion_decision(pack,operational_readiness={'spc-monitor':ready_ops()})
    assert decision.blocked
    assert any(item.code=='target_gate_failed' for item in decision.findings)


def test_wave66_stale_evidence_cannot_be_stably_promoted(tmp_path: Path):
    old=_iso(datetime.now(timezone.utc)-timedelta(hours=200))
    pack=build_provider_qualification_pack((make_bundle(tmp_path,captured_at=old),),provider='sqlite')
    decision=build_semiconductor_promotion_decision(pack,operational_readiness={'spc-monitor':ready_ops()})
    assert decision.pending and any(item.code=='evidence_traceability_pending' for item in decision.findings)


def test_wave66_hash_mismatch_blocks_promotion(tmp_path: Path):
    bundle=make_bundle(tmp_path)
    Path(bundle.artifacts[0].path).write_text('tampered')
    pack=build_provider_qualification_pack((bundle,),provider='sqlite')
    decision=build_semiconductor_promotion_decision(pack,operational_readiness={'spc-monitor':ready_ops()})
    assert decision.blocked and any(item.code=='evidence_integrity_failed' for item in decision.findings)


def test_wave66_missing_operational_readiness_is_pending_not_pass(tmp_path: Path):
    pack=build_provider_qualification_pack((make_bundle(tmp_path),),provider='sqlite')
    decision=build_semiconductor_promotion_decision(pack)
    assert decision.pending and any(item.code=='operational_readiness_pending' for item in decision.findings)


def test_wave66_complete_current_traceable_and_operational_evidence_is_promotable(tmp_path: Path):
    pack=build_provider_qualification_pack((make_bundle(tmp_path),),provider='sqlite')
    decision=build_semiconductor_promotion_decision(pack,operational_readiness={'spc-monitor':ready_ops()})
    assert decision.promotable and decision.status is PromotionDecisionStatus.PROMOTABLE
    assert any(item.code=='stable_promotion_ready' for item in decision.findings)
    json.dumps(decision.to_dict())


def test_wave66_legacy_evidence_without_framework_runtime_identity_is_pending(tmp_path: Path):
    bundle=replace(make_bundle(tmp_path),metadata={})
    pack=build_provider_qualification_pack((bundle,),provider='sqlite')
    decision=build_semiconductor_promotion_decision(pack,operational_readiness={'spc-monitor':ready_ops()})
    assert decision.pending
    assert {'framework_version_evidence_pending','runtime_contract_evidence_pending'} <= {item.code for item in decision.findings}


def test_wave66_framework_or_runtime_contract_mismatch_blocks_stable_promotion(tmp_path: Path):
    bundle=make_bundle(tmp_path)
    bad_framework=replace(bundle,metadata={'framework_version':'0.0.0','nicegui_required':NICEGUI_VERSION})
    decision=build_semiconductor_promotion_decision(build_provider_qualification_pack((bad_framework,),provider='sqlite'),operational_readiness={'spc-monitor':ready_ops()})
    assert decision.blocked and any(item.code=='framework_version_mismatch' for item in decision.findings)
    bad_contract=replace(bundle,metadata={'framework_version':FRAMEWORK_VERSION,'nicegui_required':'0.0.0'})
    decision=build_semiconductor_promotion_decision(build_provider_qualification_pack((bad_contract,),provider='sqlite'),operational_readiness={'spc-monitor':ready_ops()})
    assert decision.blocked and any(item.code=='runtime_contract_mismatch' for item in decision.findings)


def test_wave66_installed_nicegui_pass_must_match_exact_required_runtime(tmp_path: Path):
    bundle=make_bundle(tmp_path)
    bad_environment=replace(bundle.environment,nicegui_version='3.14.0')
    bundle=replace(bundle,environment=bad_environment)
    decision=build_semiconductor_promotion_decision(build_provider_qualification_pack((bundle,),provider='sqlite'),operational_readiness={'spc-monitor':ready_ops()})
    assert decision.blocked
    assert any(item.code=='installed_nicegui_version_mismatch' for item in decision.findings)


def test_wave66_required_recipe_policy_keeps_incomplete_qualification_pending(tmp_path: Path):
    pack=build_provider_qualification_pack((make_bundle(tmp_path),),provider='sqlite')
    decision=build_semiconductor_promotion_decision(pack,operational_readiness={'spc-monitor':ready_ops()},policy=PromotionPolicy(required_recipe_keys=('spc-monitor','yield-loss')))
    assert decision.pending
    assert any(item.code=='missing_recipe_evidence' and item.recipe_key=='yield-loss' for item in decision.findings)


def test_wave66_operational_readiness_separates_runnable_from_release_ready():
    source=InMemoryDataSource('ops',ROWS)
    runtime=asyncio.run(create_semiconductor_recipe_runtime('spc-monitor',source))
    runtime.assembly.semiconductor.set('chamber','A')
    probe=asyncio.run(runtime.refresh())
    report=assess_semiconductor_operational_readiness(runtime,runtime_experience=runtime.experience_state(probe))
    assert report.ready_to_run and not report.ready_for_release
    assert report.state is OperationalReadinessState.PENDING
    assert {'provider-conformance','runtime-performance','provider-benchmark'} <= {item.key for item in report.checks if item.state is OperationalReadinessState.PENDING}
    json.dumps(report.to_dict())
    asyncio.run(runtime.aclose()); asyncio.run(source.aclose())


def test_wave66_operational_readiness_blocks_runtime_errors_without_mutating_shared_state():
    source=InMemoryDataSource('ops-block',ROWS)
    runtime=asyncio.run(create_semiconductor_recipe_runtime('spc-monitor',source))
    before=runtime.context.snapshot()
    state=runtime.experience_state()
    blocked=replace(state,status=state.status.BLOCKED,message='forced test error')
    report=assess_semiconductor_operational_readiness(runtime,runtime_experience=blocked)
    assert not report.ready_to_run and next(item for item in report.checks if item.key=='runtime-state').state is OperationalReadinessState.BLOCKED
    assert runtime.context.snapshot()==before
    asyncio.run(runtime.aclose()); asyncio.run(source.aclose())


def test_wave66_runbooks_cover_all_eight_recipes_with_required_operational_paths():
    assert set(SEMICONDUCTOR_RECIPE_REGISTRY)=={
        'spc-monitor','excursion-defense-line','fdc-tool-health','lot-wafer-explorer','yield-loss','pm-effect-analysis','chamber-matching','rca-cockpit'
    }
    for key in SEMICONDUCTOR_RECIPE_REGISTRY:
        runbook=build_semiconductor_operational_runbook(key)
        keys={item.key for item in runbook.steps}
        assert {'startup','stale-data','incident','provider-failure','rollback','release-evidence'} <= keys
        assert len(runbook.steps)==len(keys)==6
        json.dumps(runbook.to_dict())


def test_wave66_runbook_incident_guidance_is_recipe_specific():
    spc=build_semiconductor_operational_runbook('spc-monitor')
    fdc=build_semiconductor_operational_runbook('fdc-tool-health')
    spc_incident=next(item for item in spc.steps if item.key=='incident')
    fdc_incident=next(item for item in fdc.steps if item.key=='incident')
    assert spc_incident.action != fdc_incident.action
    assert 'limit-version' in spc_incident.evidence_to_capture and 'trace-sample' in fdc_incident.evidence_to_capture


def test_wave66_runbooks_and_orchestrator_are_provider_neutral():
    text=(Path(__file__).resolve().parents[1]/'nicegui_base'/'certification'/'semiconductor_orchestrator.py').read_text().casefold()
    text+=(Path(__file__).resolve().parents[1]/'nicegui_base'/'semiconductor'/'operational_readiness.py').read_text().casefold()
    for forbidden in ('kubernetes','snowflake','oracle','windows authentication','nginx'):
        assert forbidden not in text


def test_wave66_external_traceability_policy_can_be_relaxed_without_changing_wave65_bundle_semantics(tmp_path: Path):
    bundle=make_bundle(tmp_path,traced=False)
    assert bundle.promotable
    trace=assess_target_evidence_traceability(bundle,policy=EvidenceFreshnessPolicy(require_external_gate_traceability=False))
    assert not trace.untraced_pass_gates
    # Stable policy remains the stricter opt-in orchestrator; Wave 65 portable bundle semantics are unchanged.


def test_wave66_public_root_exports_new_contracts():
    import nicegui_base
    for name in ('ProviderQualificationPack','SemiconductorPromotionDecision','SemiconductorOperationalReadiness','build_provider_qualification_pack','build_semiconductor_promotion_decision','build_semiconductor_operational_runbook'):
        assert hasattr(nicegui_base,name)


def test_wave66_no_new_mandatory_dependency():
    requirements=[line.strip() for line in Path(__file__).resolve().parents[1].joinpath('requirements.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    assert requirements==['nicegui==3.15.0']


def test_wave66_invalid_timestamp_evidence_is_aggregated_and_blocks_instead_of_crashing(tmp_path: Path):
    bundle=make_bundle(tmp_path)
    bundle=replace(bundle,captured_at='not-a-timestamp')
    pack=build_provider_qualification_pack((bundle,),provider='sqlite')
    assert pack.traceability[0].freshness.status is EvidenceFreshnessStatus.INVALID
    decision=build_semiconductor_promotion_decision(pack,operational_readiness={'spc-monitor':ready_ops()})
    assert decision.blocked


def test_wave66_stable_promotion_rejects_environment_version_mismatch(tmp_path: Path):
    one=make_bundle(tmp_path,recipe='spc-monitor',source_key='s1')
    two=make_bundle(tmp_path,recipe='yield-loss',source_key='s2')
    two=replace(two,environment=TargetEnvironmentFingerprint('3.13.0','test-platform','3.15.0','python'))
    pack=build_provider_qualification_pack((one,two),provider='sqlite')
    ops={'spc-monitor':ready_ops('spc-monitor','sqlite','s1'),'yield-loss':ready_ops('yield-loss','sqlite','s2')}
    decision=build_semiconductor_promotion_decision(pack,operational_readiness=ops)
    assert decision.blocked and any(item.code=='target_environment_mismatch' for item in decision.findings)


def test_wave66_operational_evidence_must_match_qualified_provider_and_source(tmp_path: Path):
    bundle=make_bundle(tmp_path,source_key='qualified')
    pack=build_provider_qualification_pack((bundle,),provider='sqlite')
    decision=build_semiconductor_promotion_decision(pack,operational_readiness={'spc-monitor':ready_ops(source_key='other')})
    assert decision.blocked and any(item.code=='operational_evidence_mismatch' for item in decision.findings)


def test_wave66_machine_registries_cover_stable_policy_and_all_recipe_runbooks():
    from nicegui_base import SEMICONDUCTOR_OPERATIONAL_RUNBOOKS, SEMICONDUCTOR_PROMOTION_POLICIES, TARGET_EVIDENCE_FRESHNESS_POLICIES
    assert set(SEMICONDUCTOR_OPERATIONAL_RUNBOOKS)==set(SEMICONDUCTOR_RECIPE_REGISTRY)
    assert set(SEMICONDUCTOR_PROMOTION_POLICIES)=={'stable'}
    assert set(TARGET_EVIDENCE_FRESHNESS_POLICIES)=={'stable'}


def test_wave66_catalog_and_runtime_registries_are_in_sync():
    from nicegui_base import FRAMEWORK_REGISTRY_COUNTS, load_framework_catalog
    catalog=load_framework_catalog()
    counts=catalog['registry_counts']
    assert counts['semiconductor_operational_runbooks']==FRAMEWORK_REGISTRY_COUNTS['semiconductor_operational_runbooks']==8
    assert counts['semiconductor_promotion_policies']==FRAMEWORK_REGISTRY_COUNTS['semiconductor_promotion_policies']==1
    assert counts['semiconductor_evidence_freshness_policies']==FRAMEWORK_REGISTRY_COUNTS['semiconductor_evidence_freshness_policies']==1
    assert len(catalog['registries']['semiconductor_operational_runbooks'])==8
    assert catalog['registries']['semiconductor_promotion_policies'][0]['key']=='stable'


def test_wave66_agent_context_teaches_target_certification_path():
    from nicegui_base import build_agent_context
    pack=build_agent_context('certify and operationalize a semiconductor SPC monitor for stable target promotion')
    assert pack.starter_recipe=='spc-monitor'
    assert 'examples/phase66_target_certification_orchestrator.py' in pack.golden_examples


def test_wave66_generated_recipe_starter_contains_stable_promotion_helper_and_guide(tmp_path: Path):
    from nicegui_base.ai.project import create_application
    from nicegui_base.ai.gate import run_application_gate
    root=tmp_path/'generated'
    create_application(root,name='Wave66 SPC',recipe='spc-monitor')
    helper=(root/'services'/'release_evidence.py').read_text()
    assert 'evaluate_stable_promotion' in helper
    assert 'build_provider_qualification_pack' in helper
    assert (root/'docs'/'nicegui_base'/'SEMICONDUCTOR_TARGET_CERTIFICATION.md').is_file()
    gate=run_application_gate(root)
    assert gate.passed,gate.to_dict()


def test_wave66_golden_example_executes_pending_not_fake_pass():
    import importlib.util
    path=Path(__file__).resolve().parents[1]/'examples'/'phase66_target_certification_orchestrator.py'
    spec=importlib.util.spec_from_file_location('phase66_example',path); assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    result=asyncio.run(module.build_example())
    assert result['runtime_ready'] and not result['target_promotable'] and result['promotion_status']=='pending'


def test_wave66_construction_manifest_stays_schema6_and_is_additive():
    from nicegui_base import load_ai_manifest
    manifest=load_ai_manifest()
    assert manifest['schema_version']==6
    section=manifest['wave66_semiconductor_target_certification_orchestrator']
    assert 'PENDING' in section['release_rule'] or 'never substitute' in section['release_rule'].lower()


def test_wave66_operational_readiness_json_roundtrip(tmp_path: Path):
    from nicegui_base import read_operational_readiness, write_operational_readiness
    report=ready_ops()
    path=tmp_path/'ops.json'; write_operational_readiness(path,report)
    loaded=read_operational_readiness(path)
    assert loaded.recipe_key==report.recipe_key and loaded.ready_for_release


def test_wave66_target_qualify_cli_can_emit_promotable_decision_only_with_complete_inputs(tmp_path: Path, capsys):
    from nicegui_base import write_operational_readiness, write_semiconductor_target_evidence
    from nicegui_base.certification.semiconductor_target_cli import target_qualify_main
    bundle=make_bundle(tmp_path)
    evidence=tmp_path/'evidence.json'; write_semiconductor_target_evidence(evidence,bundle)
    ops=tmp_path/'ops.json'; write_operational_readiness(ops,ready_ops())
    qualification=tmp_path/'qualification.json'; decision=tmp_path/'decision.json'
    rc=target_qualify_main(['nicegui-base target-qualify',str(evidence),'--provider','sqlite','--operational-readiness',str(ops),'--qualification-output',str(qualification),'--decision-output',str(decision),'--format','json'])
    assert rc==0 and qualification.is_file() and decision.is_file()
    payload=json.loads(decision.read_text())
    assert payload['promotable'] and payload['status']=='promotable'
    capsys.readouterr()


def test_wave66_target_qualify_cli_returns_pending_for_missing_operational_readiness(tmp_path: Path, capsys):
    from nicegui_base import write_semiconductor_target_evidence
    from nicegui_base.certification.semiconductor_target_cli import target_qualify_main
    bundle=make_bundle(tmp_path)
    evidence=tmp_path/'evidence.json'; write_semiconductor_target_evidence(evidence,bundle)
    rc=target_qualify_main(['nicegui-base target-qualify',str(evidence),'--provider','sqlite','--format','json'])
    assert rc==2
    payload=json.loads(capsys.readouterr().out)
    assert payload['decision']['status']=='pending'
