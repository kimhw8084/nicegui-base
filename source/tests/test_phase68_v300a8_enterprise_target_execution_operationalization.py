from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nicegui_base import (
    FRAMEWORK_VERSION,
    NICEGUI_VERSION,
    FilePromotionOperationalHandoffAdapter,
    JsonTargetExecutionIntakeAdapter,
    OperationalReadinessCheck,
    OperationalReadinessState,
    PROMOTION_OPERATIONAL_HANDOFF_ADAPTERS,
    PromotionCandidateStatus,
    PromotionHandoffStatus,
    PromotionOperationStatus,
    PromotionRehearsalKind,
    SEMICONDUCTOR_OPERATIONAL_RUNBOOKS,
    TARGET_EXECUTION_GATE_KEYS,
    TARGET_EXECUTION_INTAKE_ADAPTERS,
    SemiconductorOperationalReadiness,
    SemiconductorTargetEvidenceBundle,
    SemiconductorTargetRuntimeCertification,
    TargetEnvironmentFingerprint,
    TargetExecutionIntakeStatus,
    TargetExecutionObservation,
    TargetGateStatus,
    TargetRuntimeGate,
    apply_target_execution_intake,
    assimilate_enterprise_target_evidence,
    build_promotion_operation_record,
    build_promotion_rehearsal,
    build_stable_promotion_candidate,
    build_stable_promotion_operational_handoff,
    build_target_execution_intake,
    capture_promotion_operation_evidence,
    capture_target_evidence_artifact,
    load_target_execution_intake_manifest,
    package_promotion_operational_handoff,
    package_stable_promotion_candidate,
    promotion_operation_record_from_dict,
    promotion_operational_handoff_from_dict,
    read_promotion_operation_record,
    read_promotion_operational_handoff,
    read_target_execution_intake,
    target_execution_intake_from_dict,
    verify_promotion_operation_record,
    verify_stable_promotion_candidate_archive,
    verify_target_execution_intake,
    write_promotion_operation_record,
    write_promotion_operational_handoff,
    write_target_execution_intake,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _pending_bundle(tmp_path: Path, *, recipe='spc-monitor', provider='sqlite', source_key='target'):
    gates=(
        TargetRuntimeGate('company_adapter','Approved company adapter conformance',TargetGateStatus.PASS,'provider evidence',{'provider':provider,'source_key':source_key}),
        TargetRuntimeGate('fab_scale_pushdown','Representative fab-scale pushdown/performance',TargetGateStatus.PASS,'performance evidence',{'provider':provider,'source_key':source_key}),
        TargetRuntimeGate('installed_nicegui','Installed NiceGUI 3.15.0',TargetGateStatus.PENDING,'pending'),
        TargetRuntimeGate('server_websocket','Real server/WebSocket lifecycle',TargetGateStatus.PENDING,'pending'),
        TargetRuntimeGate('supported_browser','Supported corporate browser',TargetGateStatus.PENDING,'pending'),
        TargetRuntimeGate('human_visual_baseline','Human visual baseline',TargetGateStatus.PENDING,'pending'),
        TargetRuntimeGate('provider_benchmark','Governed representative provider benchmark',TargetGateStatus.PASS,'benchmark evidence',{'provider':provider,'source_key':source_key}),
    )
    return SemiconductorTargetEvidenceBundle(
        recipe,
        SemiconductorTargetRuntimeCertification(recipe,gates),
        TargetEnvironmentFingerprint('3.12.0','build-env',None,'python'),
        (),
        {'profile_key':'provider-rc','provider':provider,'source_key':source_key,'passed':True},
        {'provider':provider,'source_key':source_key,'passed':True},
        {'provider':provider,'source_key':source_key,'passed':True},
        {'framework_version':FRAMEWORK_VERSION,'nicegui_required':NICEGUI_VERSION,'provider':provider,'source_key':source_key},
        _iso_now(),1,
    )


def _manifest(tmp_path: Path, *, gates=None, framework=FRAMEWORK_VERSION, nicegui=NICEGUI_VERSION, provider='sqlite', source_key='target') -> Path:
    gates = gates if gates is not None else [
        {'key':key,'status':'pass','evidence':f'{key} executed','artifact':f'{key}.json'} for key in TARGET_EXECUTION_GATE_KEYS
    ]
    for gate in gates:
        artifact=gate.get('artifact')
        if isinstance(artifact,str):
            path=tmp_path/artifact
            if not path.exists(): path.write_text(json.dumps({'gate':gate['key'],'status':gate['status']})+'\n')
        elif isinstance(artifact,dict) and artifact.get('path'):
            path=tmp_path/artifact['path']
            if not path.exists(): path.write_text(json.dumps({'gate':gate['key'],'status':gate['status']})+'\n')
    payload={
        'schema_version':1,'recipe_key':'spc-monitor','provider':provider,'source_key':source_key,
        'framework_version':framework,
        'environment':{'python_version':'3.12.0','platform':'enterprise-test','nicegui_version':nicegui,'executable':'python','metadata':{}},
        'gates':gates,'metadata':{'site':'fixture'},
    }
    path=tmp_path/'intake_manifest.json'; path.write_text(json.dumps(payload,indent=2)+'\n'); return path


def _ready_ops(recipe='spc-monitor',provider='sqlite',source_key='target'):
    check=OperationalReadinessCheck('all','All operational gates',OperationalReadinessState.READY,'Operational gates passed.',required_for_run=True,required_for_release=True)
    return SemiconductorOperationalReadiness(recipe,source_key,provider,(check,))


def _complete_rehearsals(recipe='spc-monitor'):
    reports=[]
    for kind in PromotionRehearsalKind:
        plan=build_promotion_rehearsal(recipe,kind)
        reports.append(build_promotion_rehearsal(recipe,kind,completed_step_keys=plan.required_step_keys))
    return tuple(reports)


def _candidate(tmp_path: Path, *, pending=False, blocked=False):
    bundle=_pending_bundle(tmp_path)
    gates=[]
    artifacts=[]
    for gate in bundle.certification.gates:
        if gate.key in TARGET_EXECUTION_GATE_KEYS:
            status=TargetGateStatus.PENDING if pending and gate.key=='supported_browser' else (TargetGateStatus.FAIL if blocked and gate.key=='server_websocket' else TargetGateStatus.PASS)
            path=tmp_path/f'candidate-{gate.key}.json'; path.write_text(json.dumps({'gate':gate.key,'status':status.value})+'\n')
            artifact=capture_target_evidence_artifact(path,key=gate.key)
            artifacts.append(artifact)
            gates.append(TargetRuntimeGate(gate.key,gate.label,status,'target evidence'))
        else:
            gates.append(gate)
    ready=SemiconductorTargetEvidenceBundle(
        bundle.recipe_key,SemiconductorTargetRuntimeCertification(bundle.recipe_key,tuple(gates)),
        TargetEnvironmentFingerprint('3.12.0','enterprise-test',NICEGUI_VERSION,'python'),tuple(artifacts),
        bundle.benchmark,bundle.adapter_conformance,bundle.performance,
        {'framework_version':FRAMEWORK_VERSION,'nicegui_required':NICEGUI_VERSION,'provider':'sqlite','source_key':'target'},_iso_now(),1,
    )
    evidence=assimilate_enterprise_target_evidence((ready,),operational_readiness=(_ready_ops(),),provider='sqlite',required_recipe_keys=('spc-monitor',))
    rehearsals=_complete_rehearsals() if not pending else ()
    return build_stable_promotion_candidate(evidence,rehearsals=rehearsals)


def _candidate_package(tmp_path: Path, candidate):
    return package_stable_promotion_candidate(tmp_path/'candidate.zip',candidate,artifact_base_dir=tmp_path)


def _handoff(tmp_path: Path, *, pending=False, blocked=False):
    candidate=_candidate(tmp_path,pending=pending,blocked=blocked)
    package=_candidate_package(tmp_path,candidate)
    return build_stable_promotion_operational_handoff(candidate,package.path)


def _complete_operation_evidence(tmp_path: Path, handoff, kind='promotion'):
    plan=build_promotion_rehearsal('spc-monitor',kind)
    runbook=SEMICONDUCTOR_OPERATIONAL_RUNBOOKS['spc-monitor']
    steps={s.key:s for s in runbook.steps}
    evidence=[]
    for step in plan.required_step_keys:
        for evidence_key in steps[step].evidence_to_capture:
            p=tmp_path/f'{step}-{evidence_key}.json'; p.write_text(json.dumps({'step':step,'evidence':evidence_key})+'\n')
            evidence.append(capture_promotion_operation_evidence(p,recipe_key='spc-monitor',step_key=step,evidence_key=evidence_key))
    return tuple(evidence)


def test_wave68_manifest_adapter_loads_and_hashes_actual_artifact_bytes(tmp_path: Path):
    intake=load_target_execution_intake_manifest(_manifest(tmp_path))
    assert intake.recipe_key=='spc-monitor'
    assert len(intake.artifacts)==4
    assert all(len(item.sha256)==64 for item in intake.artifacts)
    assert verify_target_execution_intake(intake).verified


def test_wave68_manifest_rejects_artifact_path_escape(tmp_path: Path):
    outside=tmp_path.parent/'outside.json'; outside.write_text('{}')
    path=_manifest(tmp_path,gates=[{'key':'supported_browser','status':'pass','artifact':'../outside.json'}])
    with pytest.raises(ValueError,match='escapes intake base'):
        load_target_execution_intake_manifest(path)


def test_wave68_missing_pass_artifact_stays_pending(tmp_path: Path):
    path=_manifest(tmp_path,gates=[{'key':'supported_browser','status':'pass','artifact':'missing.json'}])
    (tmp_path/'missing.json').unlink()
    intake=load_target_execution_intake_manifest(path)
    verification=verify_target_execution_intake(intake)
    assert verification.status is TargetExecutionIntakeStatus.PENDING
    assert any(item.code=='execution_artifact_missing' for item in verification.findings)


def test_wave68_changed_captured_artifact_blocks_intake(tmp_path: Path):
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,gates=[{'key':'supported_browser','status':'pass','artifact':'browser.json'}]))
    Path(intake.artifacts[0].path).write_text('changed\n')
    verification=verify_target_execution_intake(intake)
    assert verification.blocked
    assert any(item.code=='execution_artifact_hash_mismatch' for item in verification.findings)


def test_wave68_wrong_installed_nicegui_blocks_pass_intake(tmp_path: Path):
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,nicegui='3.14.0',gates=[{'key':'installed_nicegui','status':'pass','artifact':'runtime.json'}]))
    assert verify_target_execution_intake(intake).blocked


def test_wave68_missing_installed_nicegui_identity_keeps_pass_pending(tmp_path: Path):
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,nicegui=None,gates=[{'key':'installed_nicegui','status':'pass','artifact':'runtime.json'}]))
    assert verify_target_execution_intake(intake).status is TargetExecutionIntakeStatus.PENDING


def test_wave68_wrong_framework_identity_blocks_pass_intake(tmp_path: Path):
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,framework='2.0.0',gates=[{'key':'supported_browser','status':'pass','artifact':'browser.json'}]))
    assert verify_target_execution_intake(intake).blocked


def test_wave68_missing_framework_identity_keeps_pass_pending(tmp_path: Path):
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,framework=None,gates=[{'key':'supported_browser','status':'pass','artifact':'browser.json'}]))
    assert verify_target_execution_intake(intake).status is TargetExecutionIntakeStatus.PENDING


def test_wave68_intake_id_is_deterministic_across_observation_order(tmp_path: Path):
    env=TargetEnvironmentFingerprint('3.12','target',NICEGUI_VERSION,'python')
    obs=[]
    for key in ('supported_browser','server_websocket'):
        p=tmp_path/f'{key}.json';p.write_text('{}')
        obs.append(TargetExecutionObservation(key,TargetGateStatus.PASS,key,capture_target_evidence_artifact(p,key=key)))
    a=build_target_execution_intake('spc-monitor',provider='sqlite',source_key='target',observations=obs,environment=env,observed_framework_version=FRAMEWORK_VERSION)
    b=build_target_execution_intake('spc-monitor',provider='sqlite',source_key='target',observations=reversed(obs),environment=env,observed_framework_version=FRAMEWORK_VERSION)
    assert a.intake_id==b.intake_id


def test_wave68_duplicate_gate_observation_rejected(tmp_path: Path):
    env=TargetEnvironmentFingerprint('3.12','target',NICEGUI_VERSION,'python')
    obs=TargetExecutionObservation('supported_browser',TargetGateStatus.PENDING,'pending')
    with pytest.raises(ValueError,match='duplicate gate'):
        build_target_execution_intake('spc-monitor',provider='sqlite',source_key='target',observations=(obs,obs),environment=env)


def test_wave68_unknown_gate_observation_rejected():
    with pytest.raises(ValueError,match='unsupported target execution gate'):
        TargetExecutionObservation('provider_benchmark',TargetGateStatus.PASS,'not external')


def test_wave68_apply_verified_intake_updates_only_external_gate(tmp_path: Path):
    bundle=_pending_bundle(tmp_path)
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,gates=[{'key':'supported_browser','status':'pass','artifact':'browser.json'}]))
    merged=apply_target_execution_intake(bundle,intake)
    gates={g.key:g for g in merged.certification.gates}
    assert gates['supported_browser'].status is TargetGateStatus.PASS
    assert gates['company_adapter'].status is TargetGateStatus.PASS
    assert gates['installed_nicegui'].status is TargetGateStatus.PENDING


def test_wave68_apply_untraced_requested_pass_remains_pending(tmp_path: Path):
    bundle=_pending_bundle(tmp_path)
    path=_manifest(tmp_path,gates=[{'key':'supported_browser','status':'pass','artifact':'missing.json'}]); (tmp_path/'missing.json').unlink()
    merged=apply_target_execution_intake(bundle,load_target_execution_intake_manifest(path))
    gate={g.key:g for g in merged.certification.gates}['supported_browser']
    assert gate.status is TargetGateStatus.PENDING
    assert 'not accepted' in gate.evidence


def test_wave68_apply_fail_is_conservative_even_without_artifact(tmp_path: Path):
    bundle=_pending_bundle(tmp_path)
    path=_manifest(tmp_path,gates=[{'key':'server_websocket','status':'fail','evidence':'server failed'}])
    merged=apply_target_execution_intake(bundle,load_target_execution_intake_manifest(path))
    assert {g.key:g.status for g in merged.certification.gates}['server_websocket'] is TargetGateStatus.FAIL


def test_wave68_apply_rejects_provider_mismatch(tmp_path: Path):
    bundle=_pending_bundle(tmp_path)
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,provider='other',gates=[{'key':'supported_browser','status':'pending'}]))
    with pytest.raises(ValueError,match='provider'):
        apply_target_execution_intake(bundle,intake)


def test_wave68_apply_rejects_source_mismatch(tmp_path: Path):
    bundle=_pending_bundle(tmp_path)
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,source_key='other',gates=[{'key':'supported_browser','status':'pending'}]))
    with pytest.raises(ValueError,match='source'):
        apply_target_execution_intake(bundle,intake)


def test_wave68_apply_rejects_blocked_intake(tmp_path: Path):
    bundle=_pending_bundle(tmp_path)
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,framework='wrong',gates=[{'key':'supported_browser','status':'pass','artifact':'browser.json'}]))
    with pytest.raises(ValueError,match='BLOCKED'):
        apply_target_execution_intake(bundle,intake)


def test_wave68_apply_merges_artifacts_and_gate_traceability(tmp_path: Path):
    bundle=_pending_bundle(tmp_path)
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,gates=[{'key':'supported_browser','status':'pass','artifact':{'path':'browser.json','key':'browser-proof'}}]))
    merged=apply_target_execution_intake(bundle,intake)
    assert any(a.key=='browser-proof' for a in merged.artifacts)
    assert 'browser-proof' in merged.metadata['gate_artifacts']['supported_browser']
    assert merged.metadata['target_execution_intake_id']==intake.intake_id


def test_wave68_intake_roundtrip_and_tamper_detection(tmp_path: Path):
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,gates=[{'key':'supported_browser','status':'pass','artifact':'browser.json'}]))
    restored=target_execution_intake_from_dict(intake.to_dict())
    assert restored.intake_id==intake.intake_id
    payload=intake.to_dict(); payload['source_key']='tampered'
    with pytest.raises(ValueError,match='id does not match'):
        target_execution_intake_from_dict(payload)


def test_wave68_intake_file_roundtrip(tmp_path: Path):
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,gates=[{'key':'supported_browser','status':'pass','artifact':'browser.json'}]))
    path=write_target_execution_intake(tmp_path/'intake.json',intake)
    assert read_target_execution_intake(path).intake_id==intake.intake_id


def test_wave68_manifest_expected_sha_mismatch_blocks(tmp_path: Path):
    intake=load_target_execution_intake_manifest(_manifest(tmp_path,gates=[{'key':'supported_browser','status':'pass','artifact':{'path':'browser.json','sha256':'0'*64}}]))
    assert verify_target_execution_intake(intake).blocked


def test_wave68_adapter_registries_are_bounded_provider_neutral_defaults():
    assert set(TARGET_EXECUTION_INTAKE_ADAPTERS)=={'json-manifest'}
    assert isinstance(TARGET_EXECUTION_INTAKE_ADAPTERS['json-manifest'],JsonTargetExecutionIntakeAdapter)
    assert set(PROMOTION_OPERATIONAL_HANDOFF_ADAPTERS)=={'file-package'}
    assert isinstance(PROMOTION_OPERATIONAL_HANDOFF_ADAPTERS['file-package'],FilePromotionOperationalHandoffAdapter)


def test_wave68_candidate_archive_verification_accepts_wave67_package(tmp_path: Path):
    candidate=_candidate(tmp_path); package=_candidate_package(tmp_path,candidate)
    verification=verify_stable_promotion_candidate_archive(package.path,expected_candidate=candidate)
    assert verification.verified
    assert verification.sha256==package.sha256


def test_wave68_candidate_archive_manifest_tamper_is_blocked(tmp_path: Path):
    candidate=_candidate(tmp_path); package=_candidate_package(tmp_path,candidate)
    bad=tmp_path/'bad.zip'
    with zipfile.ZipFile(package.path) as src, zipfile.ZipFile(bad,'w') as dst:
        for info in src.infolist():
            data=src.read(info.filename)
            if info.filename=='candidate.json': data += b'\n'
            dst.writestr(info.filename,data)
    verification=verify_stable_promotion_candidate_archive(bad,expected_candidate=candidate)
    assert not verification.verified
    assert any('hash mismatch' in error for error in verification.errors)


def test_wave68_candidate_archive_unsafe_path_is_blocked(tmp_path: Path):
    path=tmp_path/'unsafe.zip'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('../escape','x'); z.writestr('candidate.json','{}'); z.writestr('MANIFEST.sha256','')
    assert not verify_stable_promotion_candidate_archive(path).verified


def test_wave68_candidate_archive_expected_candidate_mismatch_is_blocked(tmp_path: Path):
    candidate=_candidate(tmp_path); package=_candidate_package(tmp_path,candidate)
    other_dir=tmp_path/'other';other_dir.mkdir(); other=_candidate(other_dir,pending=True)
    verification=verify_stable_promotion_candidate_archive(package.path,expected_candidate=other)
    assert not verification.verified
    assert any('does not match expected' in error for error in verification.errors)


def test_wave68_ready_candidate_plus_verified_archive_is_handoff_ready(tmp_path: Path):
    handoff=_handoff(tmp_path)
    assert handoff.status is PromotionHandoffStatus.READY
    assert handoff.ready_for_company_handoff
    assert handoff.candidate.status is PromotionCandidateStatus.READY


def test_wave68_pending_candidate_stays_handoff_pending(tmp_path: Path):
    handoff=_handoff(tmp_path,pending=True)
    assert handoff.status is PromotionHandoffStatus.PENDING
    assert not handoff.ready_for_company_handoff


def test_wave68_blocked_candidate_stays_handoff_blocked(tmp_path: Path):
    handoff=_handoff(tmp_path,blocked=True)
    assert handoff.status is PromotionHandoffStatus.BLOCKED


def test_wave68_handoff_id_is_path_independent_for_same_archive_bytes(tmp_path: Path):
    candidate=_candidate(tmp_path); package=_candidate_package(tmp_path,candidate)
    copy=tmp_path/'copy.zip'; copy.write_bytes(Path(package.path).read_bytes())
    a=build_stable_promotion_operational_handoff(candidate,package.path,change_reference='CHG-1')
    b=build_stable_promotion_operational_handoff(candidate,copy,change_reference='CHG-1')
    assert a.handoff_id==b.handoff_id


def test_wave68_handoff_roundtrip_and_tamper_detection(tmp_path: Path):
    handoff=_handoff(tmp_path)
    assert promotion_operational_handoff_from_dict(handoff.to_dict()).handoff_id==handoff.handoff_id
    payload=handoff.to_dict();payload['change_reference']='tampered'
    with pytest.raises(ValueError,match='id does not match'):
        promotion_operational_handoff_from_dict(payload)


def test_wave68_handoff_file_roundtrip_reverifies_archive(tmp_path: Path):
    handoff=_handoff(tmp_path); path=write_promotion_operational_handoff(tmp_path/'handoff.json',handoff)
    assert read_promotion_operational_handoff(path).status is PromotionHandoffStatus.READY
    Path(handoff.candidate_archive.path).write_bytes(b'changed')
    assert read_promotion_operational_handoff(path).status is PromotionHandoffStatus.BLOCKED


def test_wave68_handoff_package_is_deterministic_and_contains_bound_candidate(tmp_path: Path):
    handoff=_handoff(tmp_path)
    a=package_promotion_operational_handoff(tmp_path/'handoff-a.zip',handoff)
    b=package_promotion_operational_handoff(tmp_path/'handoff-b.zip',handoff)
    assert a.sha256==b.sha256
    with zipfile.ZipFile(a.path) as z:
        assert z.read('candidate/stable-promotion-candidate.zip')==Path(handoff.candidate_archive.path).read_bytes()
        assert 'operations/spc-monitor/promotion.template.json' in z.namelist()


def test_wave68_handoff_packaging_refuses_changed_candidate_archive(tmp_path: Path):
    handoff=_handoff(tmp_path); Path(handoff.candidate_archive.path).write_bytes(b'changed')
    with pytest.raises(ValueError,match='unavailable or changed'):
        package_promotion_operational_handoff(tmp_path/'handoff.zip',handoff)


def test_wave68_operation_evidence_must_match_canonical_runbook(tmp_path: Path):
    p=tmp_path/'proof.json';p.write_text('{}')
    evidence=capture_promotion_operation_evidence(p,recipe_key='spc-monitor',step_key='startup',evidence_key='runtime-probe')
    assert evidence.step_key=='startup'
    with pytest.raises(ValueError,match='not required'):
        capture_promotion_operation_evidence(p,recipe_key='spc-monitor',step_key='startup',evidence_key='invented')


def test_wave68_operation_record_pending_until_required_steps_complete(tmp_path: Path):
    handoff=_handoff(tmp_path)
    record=build_promotion_operation_record(handoff,'spc-monitor','promotion')
    assert record.status is PromotionOperationStatus.PENDING
    assert record.to_dict()['affects_candidate_status'] is False
    assert record.to_dict()['affects_target_gate_status'] is False


def test_wave68_operation_record_pending_until_required_evidence_captured(tmp_path: Path):
    handoff=_handoff(tmp_path); plan=build_promotion_rehearsal('spc-monitor','promotion')
    record=build_promotion_operation_record(handoff,'spc-monitor','promotion',completed_step_keys=plan.required_step_keys)
    assert record.status is PromotionOperationStatus.PENDING
    assert record.missing_evidence


def test_wave68_complete_operation_record_passes_structural_and_hash_verification(tmp_path: Path):
    handoff=_handoff(tmp_path); plan=build_promotion_rehearsal('spc-monitor','promotion')
    evidence=_complete_operation_evidence(tmp_path,handoff)
    record=build_promotion_operation_record(handoff,'spc-monitor','promotion',completed_step_keys=plan.required_step_keys,evidence=evidence)
    assert record.status is PromotionOperationStatus.PASS
    assert verify_promotion_operation_record(record).verified


def test_wave68_failed_operation_step_blocks_record(tmp_path: Path):
    handoff=_handoff(tmp_path); plan=build_promotion_rehearsal('spc-monitor','promotion')
    record=build_promotion_operation_record(handoff,'spc-monitor','promotion',failed_step_keys=(plan.required_step_keys[0],))
    assert record.status is PromotionOperationStatus.BLOCKED


def test_wave68_changed_operation_evidence_blocks_verification(tmp_path: Path):
    handoff=_handoff(tmp_path); plan=build_promotion_rehearsal('spc-monitor','promotion')
    evidence=_complete_operation_evidence(tmp_path,handoff)
    record=build_promotion_operation_record(handoff,'spc-monitor','promotion',completed_step_keys=plan.required_step_keys,evidence=evidence)
    Path(evidence[0].artifact.path).write_text('changed')
    assert verify_promotion_operation_record(record).status is PromotionOperationStatus.BLOCKED


def test_wave68_operation_record_binds_handoff_and_does_not_change_candidate(tmp_path: Path):
    handoff=_handoff(tmp_path); before=handoff.candidate.candidate_id
    record=build_promotion_operation_record(handoff,'spc-monitor','incident')
    assert record.handoff_id==handoff.handoff_id
    assert handoff.candidate.candidate_id==before
    assert handoff.candidate.status is PromotionCandidateStatus.READY


def test_wave68_operation_record_rejects_recipe_outside_candidate(tmp_path: Path):
    handoff=_handoff(tmp_path)
    with pytest.raises(ValueError,match='not present'):
        build_promotion_operation_record(handoff,'yield-loss','promotion')


def test_wave68_operation_record_roundtrip_and_tamper_detection(tmp_path: Path):
    handoff=_handoff(tmp_path); record=build_promotion_operation_record(handoff,'spc-monitor','promotion')
    assert promotion_operation_record_from_dict(record.to_dict()).operation_id==record.operation_id
    payload=record.to_dict(); payload['notes']=['tampered']
    with pytest.raises(ValueError,match='operation id'):
        promotion_operation_record_from_dict(payload)


def test_wave68_operation_record_file_roundtrip(tmp_path: Path):
    handoff=_handoff(tmp_path); record=build_promotion_operation_record(handoff,'spc-monitor','promotion')
    path=write_promotion_operation_record(tmp_path/'operation.json',record)
    assert read_promotion_operation_record(path).operation_id==record.operation_id


def test_wave68_no_new_mandatory_dependency():
    pyproject=Path(__file__).parents[1]/'pyproject.toml'
    text=pyproject.read_text()
    project_deps=text.split('dependencies = [',1)[1].split(']',1)[0]
    assert 'nicegui==3.15.0' in project_deps
    assert 'requests' not in project_deps and 'pydantic' not in project_deps


def test_wave68_public_root_exports_execution_and_handoff_contracts():
    import nicegui_base
    for name in (
        'TargetExecutionIntake','apply_target_execution_intake','verify_target_execution_intake',
        'StablePromotionOperationalHandoff','build_stable_promotion_operational_handoff','package_promotion_operational_handoff',
        'PromotionOperationRecord','capture_promotion_operation_evidence','verify_promotion_operation_record',
    ):
        assert hasattr(nicegui_base,name), name


def test_wave68_target_intake_cli_merges_verified_execution_without_overclaim(tmp_path: Path,capsys):
    from nicegui_base.certification.semiconductor_evidence import write_semiconductor_target_evidence
    from nicegui_base.certification.semiconductor_execution_cli import target_intake_main
    evidence_path=write_semiconductor_target_evidence(tmp_path/'base-evidence.json',_pending_bundle(tmp_path))
    output=tmp_path/'merged.json'; intake_output=tmp_path/'intake.json'
    code=target_intake_main(['nicegui-base target-intake',str(evidence_path),str(_manifest(tmp_path)),'--output',str(output),'--intake-output',str(intake_output),'--format','json'])
    payload=json.loads(capsys.readouterr().out)
    assert code==0
    assert payload['verification']['status']=='verified'
    assert output.is_file() and intake_output.is_file()
    assert payload['merged_evidence']['promotable'] is True


def test_wave68_target_intake_cli_refuses_blocked_identity_mismatch(tmp_path: Path,capsys):
    from nicegui_base.certification.semiconductor_evidence import write_semiconductor_target_evidence
    from nicegui_base.certification.semiconductor_execution_cli import target_intake_main
    evidence_path=write_semiconductor_target_evidence(tmp_path/'base-evidence.json',_pending_bundle(tmp_path))
    output=tmp_path/'merged.json'
    manifest=_manifest(tmp_path,framework='wrong',gates=[{'key':'supported_browser','status':'pass','artifact':'browser.json'}])
    code=target_intake_main(['nicegui-base target-intake',str(evidence_path),str(manifest),'--output',str(output),'--format','json'])
    payload=json.loads(capsys.readouterr().out)
    assert code==1
    assert payload['verification']['status']=='blocked'
    assert payload['merged_evidence'] is None
    assert not output.exists()


def test_wave68_promotion_handoff_cli_ready_but_never_claims_deployment(tmp_path: Path,capsys):
    from nicegui_base.certification.semiconductor_execution_cli import promotion_handoff_main
    from nicegui_base.certification.semiconductor_promotion import write_promotion_candidate
    candidate=_candidate(tmp_path); package=_candidate_package(tmp_path,candidate)
    candidate_path=write_promotion_candidate(tmp_path/'candidate.json',candidate)
    output=tmp_path/'handoff.json'; handoff_package=tmp_path/'handoff.zip'
    code=promotion_handoff_main(['nicegui-base promotion-handoff',str(candidate_path),package.path,'--output',str(output),'--package',str(handoff_package),'--format','json'])
    payload=json.loads(capsys.readouterr().out)
    assert code==0
    assert payload['handoff']['status']=='ready'
    assert payload['handoff']['affects_candidate_status'] is False
    assert output.is_file() and handoff_package.is_file()


def test_wave68_promotion_operation_cli_pending_does_not_mutate_promotion_truth(tmp_path: Path,capsys):
    from nicegui_base.certification.semiconductor_execution_cli import promotion_operation_main
    handoff=_handoff(tmp_path); path=write_promotion_operational_handoff(tmp_path/'handoff.json',handoff)
    output=tmp_path/'operation.json'
    code=promotion_operation_main(['nicegui-base promotion-operation',str(path),'spc-monitor','promotion','--output',str(output),'--format','json'])
    payload=json.loads(capsys.readouterr().out)
    assert code==2
    assert payload['record']['status']=='pending'
    assert payload['record']['affects_candidate_status'] is False
    assert payload['record']['affects_target_gate_status'] is False


def test_wave68_top_level_cli_dispatch_contains_execution_operational_commands():
    text=(Path(__file__).parents[1]/'nicegui_base'/'cli.py').read_text()
    for command in ('target-intake','promotion-handoff','promotion-operation'):
        assert command in text


def test_wave68_generated_recipe_starter_contains_execution_intake_and_handoff_helpers(tmp_path: Path):
    from nicegui_base.ai.project import create_application
    app=create_application(tmp_path/'generated',name='Wave68 Fixture',template='analysis-workspace',recipe='spc-monitor')
    source=(app.root/'services'/'release_evidence.py').read_text()
    for name in ('assimilate_target_execution','prepare_operational_handoff','record_operational_execution'):
        assert f'def {name}' in source
    compile(source,str(app.root/'services'/'release_evidence.py'),'exec')


def test_wave68_ui_exports_intake_and_handoff_panels_without_rendering():
    import nicegui_base
    assert hasattr(nicegui_base,'SemiconductorTargetExecutionIntakePanel')
    assert hasattr(nicegui_base,'SemiconductorPromotionOperationalHandoffPanel')


def test_wave68_handoff_package_operation_templates_never_claim_execution(tmp_path: Path):
    package=package_promotion_operational_handoff(tmp_path/'handoff.zip',_handoff(tmp_path))
    with zipfile.ZipFile(package.path) as z:
        template=json.loads(z.read('operations/spc-monitor/promotion.template.json'))
    assert template['status']=='pending'
    assert template['completed_step_keys']==[]
    assert template['affects_candidate_status'] is False
    assert template['affects_target_gate_status'] is False
