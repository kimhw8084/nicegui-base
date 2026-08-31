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
    JsonPromotionExecutionAdapterQualificationAdapter,
    OperationalReadinessCheck,
    OperationalReadinessState,
    PROMOTION_EXECUTION_ADAPTER_QUALIFICATION_ADAPTERS,
    PromotionCandidateStatus,
    PromotionExecutionAdapterQualificationStatus,
    PromotionRehearsalKind,
    RELEASE_AUDIT_POLICIES,
    ReleaseAuditPolicy,
    ReleaseAuditStatus,
    SEMICONDUCTOR_OPERATIONAL_RUNBOOKS,
    STABLE_RELEASE_AUDIT_POLICY,
    SemiconductorOperationalReadiness,
    SemiconductorTargetEvidenceBundle,
    SemiconductorTargetRuntimeCertification,
    TargetEnvironmentFingerprint,
    TargetGateStatus,
    TargetRuntimeGate,
    assimilate_enterprise_target_evidence,
    build_promotion_execution_adapter_qualification,
    build_promotion_operation_record,
    build_promotion_rehearsal,
    build_release_audit_closure,
    build_stable_promotion_candidate,
    build_stable_promotion_operational_handoff,
    capture_promotion_operation_evidence,
    capture_target_evidence_artifact,
    load_promotion_execution_adapter_qualification_manifest,
    package_release_audit_closure,
    package_stable_promotion_candidate,
    promotion_execution_adapter_qualification_from_dict,
    read_promotion_execution_adapter_qualification,
    read_release_audit_closure,
    release_audit_closure_from_dict,
    verify_promotion_execution_adapter_qualification,
    write_promotion_execution_adapter_qualification,
    write_release_audit_closure,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _ready_bundle(tmp_path: Path, recipe='spc-monitor', provider='sqlite', source_key='target'):
    tmp_path.mkdir(parents=True, exist_ok=True)
    gates=[]; artifacts=[]
    for key,label in (
        ('company_adapter','Approved company adapter conformance'),
        ('fab_scale_pushdown','Representative fab-scale pushdown/performance'),
        ('installed_nicegui','Installed NiceGUI 3.15.0'),
        ('server_websocket','Real server/WebSocket lifecycle'),
        ('supported_browser','Supported corporate browser'),
        ('human_visual_baseline','Human visual baseline'),
        ('provider_benchmark','Governed representative provider benchmark'),
    ):
        gates.append(TargetRuntimeGate(key,label,TargetGateStatus.PASS,'verified fixture',{'provider':provider,'source_key':source_key}))
        if key in {'installed_nicegui','server_websocket','supported_browser','human_visual_baseline'}:
            p=tmp_path/f'{key}.json';p.write_text(json.dumps({'key':key})+'\n')
            artifacts.append(capture_target_evidence_artifact(p,key=key))
    return SemiconductorTargetEvidenceBundle(
        recipe, SemiconductorTargetRuntimeCertification(recipe,tuple(gates)),
        TargetEnvironmentFingerprint('3.12.0','enterprise-test',NICEGUI_VERSION,'python'), tuple(artifacts),
        {'profile_key':'provider-rc','provider':provider,'source_key':source_key,'passed':True},
        {'provider':provider,'source_key':source_key,'passed':True},
        {'provider':provider,'source_key':source_key,'passed':True},
        {'framework_version':FRAMEWORK_VERSION,'nicegui_required':NICEGUI_VERSION,'provider':provider,'source_key':source_key,
         'gate_artifacts': {a.key:(a.key,) for a in artifacts}}, _iso_now(),1,
    )


def _ready_ops(recipe='spc-monitor',provider='sqlite',source_key='target'):
    check=OperationalReadinessCheck('all','All operational gates',OperationalReadinessState.READY,'Operational gates passed.',required_for_run=True,required_for_release=True)
    return SemiconductorOperationalReadiness(recipe,source_key,provider,(check,))


def _candidate(tmp_path: Path):
    bundle=_ready_bundle(tmp_path)
    evidence=assimilate_enterprise_target_evidence((bundle,),operational_readiness=(_ready_ops(),),provider='sqlite',required_recipe_keys=('spc-monitor',),base_dir=tmp_path)
    rehearsals=[]
    for kind in PromotionRehearsalKind:
        plan=build_promotion_rehearsal('spc-monitor',kind)
        rehearsals.append(build_promotion_rehearsal('spc-monitor',kind,completed_step_keys=plan.required_step_keys))
    candidate=build_stable_promotion_candidate(evidence,rehearsals=tuple(rehearsals))
    assert candidate.status is PromotionCandidateStatus.READY
    return candidate


def _handoff(tmp_path: Path):
    candidate=_candidate(tmp_path)
    package=package_stable_promotion_candidate(tmp_path/'candidate.zip',candidate,artifact_base_dir=tmp_path)
    return build_stable_promotion_operational_handoff(candidate,package.path,change_reference='CHG-fixture')


def _adapter_manifest(tmp_path: Path, *, status='qualified', framework=FRAMEWORK_VERSION, nicegui=NICEGUI_VERSION, operations=None, artifact=True):
    tmp_path.mkdir(parents=True, exist_ok=True)
    operations=operations if operations is not None else [item.value for item in PromotionRehearsalKind]
    artifacts=[]
    if artifact:
        p=tmp_path/'adapter-qualification.json';p.write_text(json.dumps({'result':status})+'\n')
        artifacts=[{'key':'qualification-run','path':p.name}]
    payload={
        'schema_version':1,'adapter_key':'company-release','adapter_version':'1.2.3','status':status,
        'supported_operations':operations,'framework_version':framework,'nicegui_version':nicegui,
        'qualification_authority':'approved-company-process','approval_reference':'APR-42',
        'artifacts':artifacts,'metadata':{'environment':'fixture'},
    }
    path=tmp_path/'adapter-manifest.json';path.write_text(json.dumps(payload,indent=2)+'\n');return path


def _qualification(tmp_path: Path, **kwargs):
    return load_promotion_execution_adapter_qualification_manifest(_adapter_manifest(tmp_path,**kwargs))


def _operation(tmp_path: Path, handoff, kind='promotion', *, complete=True, fail=False):
    kind=PromotionRehearsalKind(kind)
    plan=build_promotion_rehearsal('spc-monitor',kind)
    runbook=SEMICONDUCTOR_OPERATIONAL_RUNBOOKS['spc-monitor']; steps={s.key:s for s in runbook.steps}
    evidence=[]
    completed=plan.required_step_keys if complete else plan.required_step_keys[:-1]
    if fail:
        completed=tuple(item for item in completed if item != plan.required_step_keys[0])
    for step in completed:
        for evidence_key in steps[step].evidence_to_capture:
            p=tmp_path/f'{kind.value}-{step}-{evidence_key}.json';p.write_text(json.dumps({'step':step,'evidence':evidence_key})+'\n')
            evidence.append(capture_promotion_operation_evidence(p,recipe_key='spc-monitor',step_key=step,evidence_key=evidence_key))
    return build_promotion_operation_record(
        handoff,'spc-monitor',kind,completed_step_keys=completed,
        failed_step_keys=(plan.required_step_keys[0],) if fail else (),evidence=evidence,
    )


def test_wave69_default_registry_is_bounded_provider_neutral():
    assert set(PROMOTION_EXECUTION_ADAPTER_QUALIFICATION_ADAPTERS)=={'json-manifest'}
    assert isinstance(PROMOTION_EXECUTION_ADAPTER_QUALIFICATION_ADAPTERS['json-manifest'],JsonPromotionExecutionAdapterQualificationAdapter)


def test_wave69_stable_release_audit_policy_is_registered():
    assert RELEASE_AUDIT_POLICIES['stable'] is STABLE_RELEASE_AUDIT_POLICY
    assert STABLE_RELEASE_AUDIT_POLICY.required_operation_kinds==(PromotionRehearsalKind.PROMOTION,)


def test_wave69_manifest_hashes_actual_adapter_qualification_bytes(tmp_path: Path):
    q=_qualification(tmp_path)
    assert len(q.artifacts)==1 and len(q.artifacts[0].sha256)==64
    assert verify_promotion_execution_adapter_qualification(q).qualified


def test_wave69_manifest_rejects_artifact_escape(tmp_path: Path):
    outside=tmp_path.parent/'outside.json';outside.write_text('{}')
    payload=json.loads(_adapter_manifest(tmp_path).read_text());payload['artifacts']=[{'key':'x','path':'../outside.json'}]
    path=tmp_path/'bad.json';path.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='escapes qualification base'):
        load_promotion_execution_adapter_qualification_manifest(path)


def test_wave69_requested_qualified_without_artifact_stays_pending(tmp_path: Path):
    q=_qualification(tmp_path,artifact=False)
    v=verify_promotion_execution_adapter_qualification(q)
    assert v.status is PromotionExecutionAdapterQualificationStatus.PENDING
    assert any(f.code=='qualification_artifacts_missing' for f in v.findings)


def test_wave69_explicit_external_failure_blocks(tmp_path: Path):
    q=_qualification(tmp_path,status='blocked')
    assert verify_promotion_execution_adapter_qualification(q).blocked


def test_wave69_external_pending_stays_pending(tmp_path: Path):
    q=_qualification(tmp_path,status='pending')
    assert verify_promotion_execution_adapter_qualification(q).status is PromotionExecutionAdapterQualificationStatus.PENDING


@pytest.mark.parametrize('field,value,code',[
    ('framework','old-framework','framework_identity_mismatch'),
    ('nicegui','3.14.0','nicegui_identity_mismatch'),
])
def test_wave69_identity_mismatch_blocks(tmp_path: Path,field,value,code):
    q=_qualification(tmp_path,**{field:value})
    v=verify_promotion_execution_adapter_qualification(q)
    assert v.blocked and any(f.code==code for f in v.findings)


@pytest.mark.parametrize('missing_kind',[item.value for item in PromotionRehearsalKind])
def test_wave69_missing_required_operation_capability_stays_pending(tmp_path: Path,missing_kind):
    operations=[item.value for item in PromotionRehearsalKind if item.value!=missing_kind]
    q=_qualification(tmp_path,operations=operations)
    v=verify_promotion_execution_adapter_qualification(q)
    assert v.status is PromotionExecutionAdapterQualificationStatus.PENDING
    assert any(f.code=='required_operations_missing' for f in v.findings)


def test_wave69_changed_qualification_artifact_blocks(tmp_path: Path):
    q=_qualification(tmp_path);Path(q.artifacts[0].path).write_text('changed\n')
    assert verify_promotion_execution_adapter_qualification(q).blocked


def test_wave69_missing_captured_qualification_artifact_from_requested_pass_is_pending(tmp_path: Path):
    q=_qualification(tmp_path);Path(q.artifacts[0].path).unlink()
    assert verify_promotion_execution_adapter_qualification(q).status is PromotionExecutionAdapterQualificationStatus.PENDING


def test_wave69_builder_is_deterministic_ignoring_capture_time(tmp_path: Path):
    p=tmp_path/'q.json';p.write_text('{}');a=capture_target_evidence_artifact(p,key='q')
    kwargs=dict(requested_status='qualified',supported_operations=tuple(PromotionRehearsalKind),artifacts=(a,),observed_framework_version=FRAMEWORK_VERSION,observed_nicegui_version=NICEGUI_VERSION)
    a1=build_promotion_execution_adapter_qualification('x','1',**kwargs);a2=build_promotion_execution_adapter_qualification('x','1',**kwargs)
    assert a1.qualification_id==a2.qualification_id


def test_wave69_qualification_roundtrip_and_tamper_detection(tmp_path: Path):
    q=_qualification(tmp_path)
    assert promotion_execution_adapter_qualification_from_dict(q.to_dict()).qualification_id==q.qualification_id
    payload=q.to_dict();payload['adapter_version']='tampered'
    with pytest.raises(ValueError,match='id does not match'):
        promotion_execution_adapter_qualification_from_dict(payload)


def test_wave69_qualification_file_roundtrip(tmp_path: Path):
    q=_qualification(tmp_path);p=write_promotion_execution_adapter_qualification(tmp_path/'qualification.json',q)
    assert read_promotion_execution_adapter_qualification(p).qualification_id==q.qualification_id


def test_wave69_approval_reference_is_metadata_not_auto_qualification(tmp_path: Path):
    q=_qualification(tmp_path,status='pending')
    assert q.approval_reference=='APR-42'
    assert not verify_promotion_execution_adapter_qualification(q).qualified


def test_wave69_release_audit_closes_with_ready_handoff_qualified_adapter_and_complete_promotion(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h)
    audit=build_release_audit_closure(h,q,(r,))
    assert audit.status is ReleaseAuditStatus.CLOSED and audit.closed


def test_wave69_release_audit_missing_promotion_record_is_pending(tmp_path: Path):
    audit=build_release_audit_closure(_handoff(tmp_path),_qualification(tmp_path),())
    assert audit.status is ReleaseAuditStatus.PENDING
    assert any(f.code=='required_operation_missing' for f in audit.findings)


def test_wave69_release_audit_incomplete_promotion_record_is_pending(tmp_path: Path):
    h=_handoff(tmp_path);audit=build_release_audit_closure(h,_qualification(tmp_path),(_operation(tmp_path,h,complete=False),))
    assert audit.status is ReleaseAuditStatus.PENDING
    assert any(f.code=='operation_record_incomplete' for f in audit.findings)


def test_wave69_release_audit_failed_operation_is_blocked(tmp_path: Path):
    h=_handoff(tmp_path);audit=build_release_audit_closure(h,_qualification(tmp_path),(_operation(tmp_path,h,fail=True),))
    assert audit.status is ReleaseAuditStatus.BLOCKED


def test_wave69_release_audit_pending_adapter_is_pending(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path,status='pending');r=_operation(tmp_path,h)
    audit=build_release_audit_closure(h,q,(r,))
    assert audit.status is ReleaseAuditStatus.PENDING
    assert any(f.code=='execution_adapter_not_qualified' for f in audit.findings)


def test_wave69_release_audit_blocked_adapter_is_blocked(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path,status='blocked');r=_operation(tmp_path,h)
    assert build_release_audit_closure(h,q,(r,)).status is ReleaseAuditStatus.BLOCKED


def test_wave69_release_audit_changed_candidate_archive_blocks(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h)
    Path(h.candidate_archive.path).write_bytes(b'changed')
    audit=build_release_audit_closure(h,q,(r,))
    assert audit.status is ReleaseAuditStatus.BLOCKED
    assert any(f.code=='candidate_archive_reverification_failed' for f in audit.findings)


def test_wave69_release_audit_changed_operation_evidence_blocks(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h)
    Path(r.evidence[0].artifact.path).write_text('changed\n')
    assert build_release_audit_closure(h,q,(r,)).status is ReleaseAuditStatus.BLOCKED


def test_wave69_release_audit_operation_bound_to_other_handoff_blocks(tmp_path: Path):
    h1=_handoff(tmp_path/'a');h2=_handoff(tmp_path/'b');q=_qualification(tmp_path/'a');r=_operation(tmp_path/'b',h2)
    audit=build_release_audit_closure(h1,q,(r,))
    assert audit.status is ReleaseAuditStatus.BLOCKED
    assert any(f.code=='operation_handoff_mismatch' for f in audit.findings)


def test_wave69_audit_id_is_deterministic_for_same_inputs(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h)
    a=build_release_audit_closure(h,q,(r,),metadata={'x':1});b=build_release_audit_closure(h,q,(r,),metadata={'x':1})
    assert a.audit_id==b.audit_id


def test_wave69_audit_roundtrip_and_tamper_detection(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h);audit=build_release_audit_closure(h,q,(r,))
    assert release_audit_closure_from_dict(audit.to_dict()).audit_id==audit.audit_id
    payload=audit.to_dict();payload['metadata']['tamper']=True
    with pytest.raises(ValueError,match='id does not match'):
        release_audit_closure_from_dict(payload)


def test_wave69_audit_file_roundtrip(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h);audit=build_release_audit_closure(h,q,(r,))
    p=write_release_audit_closure(tmp_path/'audit.json',audit)
    assert read_release_audit_closure(p).audit_id==audit.audit_id


def test_wave69_audit_package_is_deterministic_and_self_contained(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h);audit=build_release_audit_closure(h,q,(r,))
    a=package_release_audit_closure(tmp_path/'a.zip',audit);b=package_release_audit_closure(tmp_path/'b.zip',audit)
    assert a.sha256==b.sha256
    with zipfile.ZipFile(a.path) as z:
        names=set(z.namelist())
        assert {'release-audit.json','handoff.json','execution-adapter-qualification.json','candidate/stable-promotion-candidate.zip','MANIFEST.sha256'} <= names
        assert any(name.startswith('adapter-evidence/') for name in names)
        assert any(name.startswith('operations/spc-monitor/promotion/evidence/') for name in names)


def test_wave69_audit_package_manifest_verifies_every_other_entry(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h);audit=build_release_audit_closure(h,q,(r,))
    p=package_release_audit_closure(tmp_path/'audit.zip',audit)
    with zipfile.ZipFile(p.path) as z:
        expected={name:sha for sha,name in (line.split('  ',1) for line in z.read('MANIFEST.sha256').decode().splitlines())}
        assert set(expected)==set(z.namelist())-{'MANIFEST.sha256'}
        assert all(hashlib.sha256(z.read(name)).hexdigest()==sha for name,sha in expected.items())


def test_wave69_audit_packaging_refuses_changed_candidate_archive(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h);audit=build_release_audit_closure(h,q,(r,))
    Path(h.candidate_archive.path).write_bytes(b'changed')
    with pytest.raises(ValueError,match='BLOCKED'):
        package_release_audit_closure(tmp_path/'audit.zip',audit)


def test_wave69_audit_packaging_refuses_changed_adapter_artifact(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h);audit=build_release_audit_closure(h,q,(r,))
    Path(q.artifacts[0].path).write_text('changed\n')
    with pytest.raises(ValueError,match='BLOCKED'):
        package_release_audit_closure(tmp_path/'audit.zip',audit)


def test_wave69_audit_packaging_refuses_changed_operation_artifact(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h);audit=build_release_audit_closure(h,q,(r,))
    Path(r.evidence[0].artifact.path).write_text('changed\n')
    with pytest.raises(ValueError,match='BLOCKED'):
        package_release_audit_closure(tmp_path/'audit.zip',audit)


def test_wave69_custom_policy_can_require_rollback_record(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);promotion=_operation(tmp_path,h)
    policy=ReleaseAuditPolicy(required_operation_kinds=(PromotionRehearsalKind.PROMOTION,PromotionRehearsalKind.ROLLBACK))
    pending=build_release_audit_closure(h,q,(promotion,),policy=policy)
    assert pending.status is ReleaseAuditStatus.PENDING
    rollback=_operation(tmp_path,h,'rollback')
    assert build_release_audit_closure(h,q,(promotion,rollback),policy=policy).closed


def test_wave69_closed_audit_explicitly_does_not_mutate_promotion_truth(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h);audit=build_release_audit_closure(h,q,(r,))
    data=audit.to_dict()
    assert data['affects_candidate_status'] is False
    assert data['affects_target_gate_status'] is False
    assert data['deployment_performed_by_framework'] is False
    assert data['audit_closure_is_not_promotion_approval'] is True


def test_wave69_audit_next_action_when_closed_is_retention_not_deployment_claim(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h);audit=build_release_audit_closure(h,q,(r,))
    assert audit.closed and 'Retain' in audit.next_actions[0]


def test_wave69_qualification_manifest_expected_sha_mismatch_blocks(tmp_path: Path):
    path=_adapter_manifest(tmp_path);payload=json.loads(path.read_text());payload['artifacts'][0]['sha256']='0'*64;path.write_text(json.dumps(payload))
    assert verify_promotion_execution_adapter_qualification(load_promotion_execution_adapter_qualification_manifest(path)).blocked


def test_wave69_qualification_required_operation_override_can_be_narrower(tmp_path: Path):
    q=_qualification(tmp_path,operations=['promotion'])
    v=verify_promotion_execution_adapter_qualification(q,required_operations=('promotion',))
    assert v.qualified


def test_wave69_pending_audit_can_be_packaged_for_gap_handoff(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);audit=build_release_audit_closure(h,q,())
    assert audit.status is ReleaseAuditStatus.PENDING
    package=package_release_audit_closure(tmp_path/'pending-audit.zip',audit)
    assert Path(package.path).is_file()


def test_wave69_release_audit_status_serializes_closed(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h);audit=build_release_audit_closure(h,q,(r,))
    assert audit.to_dict()['status']=='closed'


def test_wave69_adapter_qualification_status_serializes_qualified(tmp_path: Path):
    q=_qualification(tmp_path);v=verify_promotion_execution_adapter_qualification(q)
    assert q.to_dict()['requested_status']=='qualified' and v.to_dict()['status']=='qualified'


def test_wave69_external_qualification_authority_is_preserved_but_not_interpreted(tmp_path: Path):
    q=_qualification(tmp_path)
    assert q.qualification_authority=='approved-company-process'
    assert q.to_dict()['approval_reference_is_metadata_only'] is True


def test_wave69_audit_operation_optional_incident_record_must_still_verify_if_supplied(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);promotion=_operation(tmp_path,h);incident=_operation(tmp_path,h,'incident')
    Path(incident.evidence[0].artifact.path).write_text('changed\n')
    audit=build_release_audit_closure(h,q,(promotion,incident))
    assert audit.status is ReleaseAuditStatus.BLOCKED


def test_wave69_audit_optional_complete_incident_record_does_not_prevent_closure(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);promotion=_operation(tmp_path,h);incident=_operation(tmp_path,h,'incident')
    assert build_release_audit_closure(h,q,(promotion,incident)).closed


def test_wave69_policy_duplicate_operation_kind_rejected():
    with pytest.raises(ValueError,match='duplicate'):
        ReleaseAuditPolicy(required_operation_kinds=('promotion','promotion'))


def test_wave69_qualification_duplicate_supported_operation_rejected(tmp_path: Path):
    p=tmp_path/'q.json';p.write_text('{}');a=capture_target_evidence_artifact(p,key='q')
    with pytest.raises(ValueError,match='duplicate'):
        build_promotion_execution_adapter_qualification('x','1',requested_status='qualified',supported_operations=('promotion','promotion'),artifacts=(a,),observed_framework_version=FRAMEWORK_VERSION,observed_nicegui_version=NICEGUI_VERSION)


def test_wave69_qualification_duplicate_artifact_key_rejected(tmp_path: Path):
    p=tmp_path/'q.json';p.write_text('{}');a=capture_target_evidence_artifact(p,key='q')
    with pytest.raises(ValueError,match='duplicate artifact'):
        build_promotion_execution_adapter_qualification('x','1',requested_status='qualified',supported_operations=tuple(PromotionRehearsalKind),artifacts=(a,a),observed_framework_version=FRAMEWORK_VERSION,observed_nicegui_version=NICEGUI_VERSION)

@pytest.mark.parametrize('missing_field',['framework_version','nicegui_version'])
def test_wave69_requested_qualified_missing_release_identity_stays_pending(tmp_path: Path, missing_field):
    path=_adapter_manifest(tmp_path);payload=json.loads(path.read_text());payload.pop(missing_field);path.write_text(json.dumps(payload))
    q=load_promotion_execution_adapter_qualification_manifest(path)
    assert verify_promotion_execution_adapter_qualification(q).status is PromotionExecutionAdapterQualificationStatus.PENDING


def test_wave69_duplicate_operation_records_are_blocked_diagnostics(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h)
    audit=build_release_audit_closure(h,q,(r,r))
    assert audit.status is ReleaseAuditStatus.BLOCKED
    assert any(f.code=='duplicate_operation_record' for f in audit.findings)


def test_wave69_persisted_audit_finding_tamper_is_detected(tmp_path: Path):
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h);audit=build_release_audit_closure(h,q,(r,))
    payload=audit.to_dict();payload['findings']=[{'code':'fake','status':'pending','message':'tampered','remediation':'x','recipe_key':None,'operation_kind':None}]
    payload['status']='pending'
    with pytest.raises(ValueError,match='id does not match'):
        release_audit_closure_from_dict(payload)


def test_wave69_execution_adapter_qualify_cli_writes_normalized_qualification(tmp_path: Path, capsys):
    from nicegui_base.certification.semiconductor_release_audit_cli import execution_adapter_qualify_main
    manifest=_adapter_manifest(tmp_path);out=tmp_path/'normalized.json'
    rc=execution_adapter_qualify_main([str(manifest),'--output',str(out),'--format','json'])
    assert rc==0 and out.is_file()
    assert json.loads(capsys.readouterr().out)['verification']['status']=='qualified'


def test_wave69_release_audit_cli_closes_and_packages(tmp_path: Path, capsys):
    from nicegui_base.certification.semiconductor_release_audit_cli import release_audit_main
    h=_handoff(tmp_path);q=_qualification(tmp_path);r=_operation(tmp_path,h)
    hp=tmp_path/'handoff.json';hp.write_text(json.dumps(h.to_dict(),indent=2)+'\n')
    qp=write_promotion_execution_adapter_qualification(tmp_path/'qualification.json',q)
    rp=tmp_path/'operation.json';rp.write_text(json.dumps(r.to_dict(),indent=2)+'\n')
    out=tmp_path/'audit.json';pkg=tmp_path/'audit.zip'
    rc=release_audit_main([str(hp),str(qp),str(rp),'--output',str(out),'--package',str(pkg),'--format','json'])
    payload=json.loads(capsys.readouterr().out)
    assert rc==0 and payload['audit']['status']=='closed' and out.is_file() and pkg.is_file()


def test_wave69_generated_semiconductor_starter_includes_adapter_qualification_and_audit_helpers(tmp_path: Path):
    from nicegui_base.ai.project import create_application
    app=create_application(tmp_path/'app',name='Wave69 Starter',recipe='spc-monitor')
    source=(app.root/'services/release_evidence.py').read_text()
    assert 'def qualify_promotion_execution_adapter' in source
    assert 'def close_release_audit' in source
    compile(source,str(app.root/'services/release_evidence.py'),'exec')
