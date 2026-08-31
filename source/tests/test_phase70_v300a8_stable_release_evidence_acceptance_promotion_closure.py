from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nicegui_base import (
    FRAMEWORK_VERSION, NICEGUI_VERSION,
    JsonStableReleaseEvidenceAcceptanceAdapter,
    OperationalReadinessCheck, OperationalReadinessState,
    PromotionCandidateStatus, PromotionRehearsalKind,
    ReleaseAuditArchiveStatus, ReleaseAuditStatus,
    SEMICONDUCTOR_OPERATIONAL_RUNBOOKS,
    STABLE_PROMOTION_CLOSURE_POLICIES, STABLE_PROMOTION_CLOSURE_POLICY,
    STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS,
    SemiconductorOperationalReadiness, SemiconductorTargetEvidenceBundle, SemiconductorTargetRuntimeCertification,
    StablePromotionClosurePolicy, StablePromotionClosureStatus,
    StableReleaseEvidenceAcceptanceStatus,
    TargetEnvironmentFingerprint, TargetGateStatus, TargetRuntimeGate,
    assimilate_enterprise_target_evidence, build_promotion_operation_record, build_promotion_rehearsal,
    build_release_audit_closure, build_stable_promotion_candidate, build_stable_promotion_operational_handoff,
    build_stable_release_evidence_acceptance, build_stable_release_promotion_closure,
    capture_promotion_operation_evidence, capture_target_evidence_artifact,
    load_promotion_execution_adapter_qualification_manifest, load_stable_release_evidence_acceptance_manifest,
    package_release_audit_closure, package_stable_promotion_candidate, package_stable_release_promotion_closure,
    read_stable_release_evidence_acceptance, read_stable_release_promotion_closure,
    stable_release_evidence_acceptance_from_dict, stable_release_promotion_closure_from_dict,
    verify_release_audit_archive, verify_stable_release_evidence_acceptance,
    write_release_audit_closure, write_stable_release_evidence_acceptance, write_stable_release_promotion_closure,
)
from nicegui_base.certification.semiconductor_release_acceptance_cli import promotion_close_main, release_evidence_accept_main


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
    return build_stable_promotion_operational_handoff(candidate,package.path,change_reference='CHG-wave70-fixture')


def _adapter_manifest(tmp_path: Path):
    p=tmp_path/'adapter-qualification.json';p.write_text('{"qualified":true}\n')
    payload={
        'schema_version':1,'adapter_key':'company-release','adapter_version':'1.2.3','status':'qualified',
        'supported_operations':[item.value for item in PromotionRehearsalKind],
        'framework_version':FRAMEWORK_VERSION,'nicegui_version':NICEGUI_VERSION,
        'qualification_authority':'approved-company-process','approval_reference':'APR-69',
        'artifacts':[{'key':'qualification-run','path':p.name}],
    }
    path=tmp_path/'adapter-manifest.json';path.write_text(json.dumps(payload,indent=2)+'\n');return path


def _qualification(tmp_path: Path):
    return load_promotion_execution_adapter_qualification_manifest(_adapter_manifest(tmp_path))


def _operation(tmp_path: Path, handoff):
    kind=PromotionRehearsalKind.PROMOTION
    plan=build_promotion_rehearsal('spc-monitor',kind)
    runbook=SEMICONDUCTOR_OPERATIONAL_RUNBOOKS['spc-monitor']; steps={s.key:s for s in runbook.steps}
    evidence=[]
    for step in plan.required_step_keys:
        for evidence_key in steps[step].evidence_to_capture:
            p=tmp_path/f'promotion-{step}-{evidence_key}.json';p.write_text(json.dumps({'step':step,'evidence':evidence_key})+'\n')
            evidence.append(capture_promotion_operation_evidence(p,recipe_key='spc-monitor',step_key=step,evidence_key=evidence_key))
    return build_promotion_operation_record(handoff,'spc-monitor',kind,completed_step_keys=plan.required_step_keys,evidence=evidence)


def _closed_audit(tmp_path: Path):
    handoff=_handoff(tmp_path); qualification=_qualification(tmp_path); operation=_operation(tmp_path,handoff)
    audit=build_release_audit_closure(handoff,qualification,(operation,))
    assert audit.status is ReleaseAuditStatus.CLOSED
    package=package_release_audit_closure(tmp_path/'release-audit.zip',audit)
    return audit,package


def _acceptance_manifest(tmp_path: Path, audit, package, *, status='accepted', framework=FRAMEWORK_VERSION, nicegui=NICEGUI_VERSION, artifact=True, authority=True):
    artifacts=[]
    if artifact:
        p=tmp_path/'external-release-acceptance.json';p.write_text(json.dumps({'accepted':status=='accepted'})+'\n')
        artifacts=[{'key':'release-approval','path':p.name}]
    payload={
        'schema_version':1,'status':status,'audit_id':audit.audit_id,'candidate_id':audit.handoff.candidate.candidate_id,
        'audit_archive_sha256':package.sha256,'framework_version':framework,'nicegui_version':nicegui,
        'acceptance_authority':'approved-company-release-board' if authority else None,
        'approval_reference':'REL-70' if authority else None,'artifacts':artifacts,
    }
    path=tmp_path/'acceptance-manifest.json';path.write_text(json.dumps(payload,indent=2)+'\n');return path


def _acceptance(tmp_path: Path, audit, package, **kwargs):
    return load_stable_release_evidence_acceptance_manifest(_acceptance_manifest(tmp_path,audit,package,**kwargs),audit,package.path)


def test_wave70_registry_is_bounded_provider_neutral():
    assert set(STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS)=={'json-manifest'}
    assert isinstance(STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS['json-manifest'],JsonStableReleaseEvidenceAcceptanceAdapter)


def test_wave70_stable_closure_policy_registered():
    assert STABLE_PROMOTION_CLOSURE_POLICIES['stable'] is STABLE_PROMOTION_CLOSURE_POLICY
    assert STABLE_PROMOTION_CLOSURE_POLICY.target_version=='3.0.0'


def test_wave70_audit_archive_independently_verifies(tmp_path: Path):
    audit,package=_closed_audit(tmp_path)
    report=verify_release_audit_archive(package.path,expected_audit=audit)
    assert report.status is ReleaseAuditArchiveStatus.VERIFIED and report.verified
    assert report.audit_id==audit.audit_id and report.candidate_id==audit.handoff.candidate.candidate_id


def test_wave70_audit_archive_missing_blocks(tmp_path: Path):
    report=verify_release_audit_archive(tmp_path/'missing.zip')
    assert not report.verified and report.findings[0].code=='audit_archive_missing'


def test_wave70_audit_archive_changed_entry_blocks(tmp_path: Path):
    audit,package=_closed_audit(tmp_path)
    with zipfile.ZipFile(package.path,'a') as z:z.writestr('release-audit.json',b'changed')
    report=verify_release_audit_archive(package.path,expected_audit=audit)
    assert not report.verified


def test_wave70_audit_archive_duplicate_entry_blocks(tmp_path: Path):
    audit,package=_closed_audit(tmp_path)
    with zipfile.ZipFile(package.path,'a') as z:z.writestr('handoff.json',b'duplicate')
    report=verify_release_audit_archive(package.path,expected_audit=audit)
    assert any(f.code=='audit_archive_duplicate_entry' for f in report.findings)


def test_wave70_audit_archive_missing_manifest_blocks(tmp_path: Path):
    audit,package=_closed_audit(tmp_path)
    out=tmp_path/'no-manifest.zip'
    with zipfile.ZipFile(package.path) as src, zipfile.ZipFile(out,'w') as dst:
        for name in src.namelist():
            if name!='MANIFEST.sha256': dst.writestr(name,src.read(name))
    assert not verify_release_audit_archive(out,expected_audit=audit).verified


def test_wave70_audit_archive_wrong_expected_audit_blocks(tmp_path: Path):
    audit,package=_closed_audit(tmp_path/'a'); audit2,_=_closed_audit(tmp_path/'b')
    report=verify_release_audit_archive(package.path,expected_audit=audit2)
    assert any(f.code=='audit_archive_identity_mismatch' for f in report.findings)


def test_wave70_acceptance_manifest_hash_binds_artifact_bytes(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); acceptance=_acceptance(tmp_path,audit,package)
    assert len(acceptance.artifacts)==1 and len(acceptance.artifacts[0].sha256)==64


def test_wave70_requested_accepted_with_artifact_and_identity_verifies(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); acceptance=_acceptance(tmp_path,audit,package)
    report=verify_stable_release_evidence_acceptance(acceptance,audit=audit,audit_archive_path=package.path)
    assert report.accepted


def test_wave70_requested_accepted_without_artifact_stays_pending(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); acceptance=_acceptance(tmp_path,audit,package,artifact=False)
    report=verify_stable_release_evidence_acceptance(acceptance,audit=audit,audit_archive_path=package.path)
    assert report.status is StableReleaseEvidenceAcceptanceStatus.PENDING
    assert any(f.code=='acceptance_artifacts_missing' for f in report.findings)


def test_wave70_requested_accepted_without_authority_stays_pending(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); acceptance=_acceptance(tmp_path,audit,package,authority=False)
    report=verify_stable_release_evidence_acceptance(acceptance,audit=audit,audit_archive_path=package.path)
    assert report.status is StableReleaseEvidenceAcceptanceStatus.PENDING


@pytest.mark.parametrize('field,value,code',[('framework','old','framework_identity_mismatch'),('nicegui','3.14.0','nicegui_identity_mismatch')])
def test_wave70_acceptance_identity_mismatch_blocks(tmp_path: Path,field,value,code):
    audit,package=_closed_audit(tmp_path); acceptance=_acceptance(tmp_path,audit,package,**{field:value})
    report=verify_stable_release_evidence_acceptance(acceptance,audit=audit,audit_archive_path=package.path)
    assert report.blocked and any(f.code==code for f in report.findings)


def test_wave70_external_pending_stays_pending(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); acceptance=_acceptance(tmp_path,audit,package,status='pending')
    assert verify_stable_release_evidence_acceptance(acceptance,audit=audit,audit_archive_path=package.path).status is StableReleaseEvidenceAcceptanceStatus.PENDING


def test_wave70_external_blocked_stays_blocked(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); acceptance=_acceptance(tmp_path,audit,package,status='blocked')
    assert verify_stable_release_evidence_acceptance(acceptance,audit=audit,audit_archive_path=package.path).blocked


def test_wave70_changed_acceptance_artifact_blocks(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); acceptance=_acceptance(tmp_path,audit,package)
    Path(acceptance.artifacts[0].path).write_text('changed\n')
    assert verify_stable_release_evidence_acceptance(acceptance,audit=audit,audit_archive_path=package.path).blocked


def test_wave70_changed_audit_archive_after_acceptance_blocks(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); acceptance=_acceptance(tmp_path,audit,package)
    Path(package.path).write_bytes(Path(package.path).read_bytes()+b'changed')
    report=verify_stable_release_evidence_acceptance(acceptance,audit=audit,audit_archive_path=package.path)
    assert report.blocked and any(f.code=='audit_archive_hash_mismatch' for f in report.findings)


def test_wave70_acceptance_id_deterministic_ignoring_capture_time(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); p=tmp_path/'approval.json';p.write_text('{}'); art=capture_target_evidence_artifact(p,key='approval')
    kwargs=dict(requested_status='accepted',artifacts=(art,),observed_framework_version=FRAMEWORK_VERSION,observed_nicegui_version=NICEGUI_VERSION,acceptance_authority='board',approval_reference='R1')
    a=build_stable_release_evidence_acceptance(audit,package.path,**kwargs);b=build_stable_release_evidence_acceptance(audit,package.path,**kwargs)
    assert a.acceptance_id==b.acceptance_id


def test_wave70_acceptance_roundtrip_and_tamper_detection(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package)
    assert stable_release_evidence_acceptance_from_dict(a.to_dict()).acceptance_id==a.acceptance_id
    payload=a.to_dict();payload['approval_reference']='tampered'
    with pytest.raises(ValueError,match='id does not match'):
        stable_release_evidence_acceptance_from_dict(payload)


def test_wave70_acceptance_file_roundtrip(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package)
    path=write_stable_release_evidence_acceptance(tmp_path/'acceptance.json',a)
    assert read_stable_release_evidence_acceptance(path).acceptance_id==a.acceptance_id


def test_wave70_manifest_rejects_artifact_escape(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); outside=tmp_path.parent/'outside-wave70.json';outside.write_text('{}')
    path=_acceptance_manifest(tmp_path,audit,package); payload=json.loads(path.read_text());payload['artifacts']=[{'key':'x','path':'../outside-wave70.json'}];path.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='escapes acceptance base'):
        load_stable_release_evidence_acceptance_manifest(path,audit,package.path)


def test_wave70_manifest_subject_mismatch_rejected(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); path=_acceptance_manifest(tmp_path,audit,package); payload=json.loads(path.read_text());payload['audit_id']='0'*64;path.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='audit_id'):
        load_stable_release_evidence_acceptance_manifest(path,audit,package.path)


def test_wave70_manifest_expected_artifact_sha_mismatch_blocks(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); path=_acceptance_manifest(tmp_path,audit,package); payload=json.loads(path.read_text());payload['artifacts'][0]['sha256']='0'*64;path.write_text(json.dumps(payload))
    a=load_stable_release_evidence_acceptance_manifest(path,audit,package.path)
    report=verify_stable_release_evidence_acceptance(a,audit=audit,audit_archive_path=package.path)
    assert report.blocked and any(f.code=='manifest_artifact_hash_mismatch' for f in report.findings)


def test_wave70_missing_manifest_artifact_keeps_requested_accept_pending(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); path=_acceptance_manifest(tmp_path,audit,package); payload=json.loads(path.read_text());payload['artifacts']=[{'key':'approval','path':'missing.json'}];path.write_text(json.dumps(payload))
    a=load_stable_release_evidence_acceptance_manifest(path,audit,package.path)
    report=verify_stable_release_evidence_acceptance(a,audit=audit,audit_archive_path=package.path)
    assert report.status is StableReleaseEvidenceAcceptanceStatus.PENDING


def test_wave70_closure_closes_only_with_verified_audit_and_accepted_evidence(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package)
    closure=build_stable_release_promotion_closure(audit,package.path,a)
    assert closure.status is StablePromotionClosureStatus.CLOSED and closure.closed


def test_wave70_closure_pending_acceptance_stays_pending(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package,status='pending')
    closure=build_stable_release_promotion_closure(audit,package.path,a)
    assert closure.status is StablePromotionClosureStatus.PENDING


def test_wave70_closure_blocked_acceptance_blocks(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package,status='blocked')
    assert build_stable_release_promotion_closure(audit,package.path,a).status is StablePromotionClosureStatus.BLOCKED


def test_wave70_closure_changed_audit_archive_blocks(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package)
    with zipfile.ZipFile(package.path,'a') as z:z.writestr('tamper.txt','x')
    closure=build_stable_release_promotion_closure(audit,package.path,a)
    assert closure.status is StablePromotionClosureStatus.BLOCKED


def test_wave70_closed_closure_does_not_mutate_or_publish(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package); closure=build_stable_release_promotion_closure(audit,package.path,a)
    payload=closure.to_dict()
    assert payload['affects_candidate_status'] is False
    assert payload['affects_target_gate_status'] is False
    assert payload['deployment_performed_by_framework'] is False
    assert payload['stable_release_published_by_framework'] is False
    assert payload['closure_records_verified_evidence_acceptance_only'] is True


def test_wave70_closure_id_is_deterministic(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package)
    c1=build_stable_release_promotion_closure(audit,package.path,a,metadata={'x':1});c2=build_stable_release_promotion_closure(audit,package.path,a,metadata={'x':1})
    assert c1.closure_id==c2.closure_id


def test_wave70_closure_roundtrip_and_tamper_detection(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package); c=build_stable_release_promotion_closure(audit,package.path,a)
    assert stable_release_promotion_closure_from_dict(c.to_dict()).closure_id==c.closure_id
    payload=c.to_dict();payload['metadata']['tamper']=1
    with pytest.raises(ValueError,match='id does not match'):
        stable_release_promotion_closure_from_dict(payload)


def test_wave70_closure_file_roundtrip(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package); c=build_stable_release_promotion_closure(audit,package.path,a)
    path=write_stable_release_promotion_closure(tmp_path/'closure.json',c)
    assert read_stable_release_promotion_closure(path).closure_id==c.closure_id


def test_wave70_custom_policy_target_version_mismatch_blocks(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package); policy=StablePromotionClosurePolicy(target_version='9.9.9')
    c=build_stable_release_promotion_closure(audit,package.path,a,policy=policy)
    assert c.status is StablePromotionClosureStatus.BLOCKED


def test_wave70_closure_package_is_deterministic_and_self_contained(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package); c=build_stable_release_promotion_closure(audit,package.path,a)
    p1=package_stable_release_promotion_closure(tmp_path/'c1.zip',c);p2=package_stable_release_promotion_closure(tmp_path/'c2.zip',c)
    assert p1.sha256==p2.sha256
    with zipfile.ZipFile(p1.path) as z:
        names=set(z.namelist())
        assert {'promotion-closure.json','release-evidence-acceptance.json','release-audit/release-audit.zip','MANIFEST.sha256'}<=names
        assert any(name.startswith('acceptance-evidence/') for name in names)


def test_wave70_closure_package_manifest_verifies(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package); c=build_stable_release_promotion_closure(audit,package.path,a)
    p=package_stable_release_promotion_closure(tmp_path/'closure.zip',c)
    with zipfile.ZipFile(p.path) as z:
        expected={name:sha for sha,name in (line.split('  ',1) for line in z.read('MANIFEST.sha256').decode().splitlines())}
        assert set(expected)==set(z.namelist())-{'MANIFEST.sha256'}
        assert all(hashlib.sha256(z.read(name)).hexdigest()==sha for name,sha in expected.items())


def test_wave70_pending_closure_can_package_for_gap_handoff(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package,status='pending'); c=build_stable_release_promotion_closure(audit,package.path,a)
    p=package_stable_release_promotion_closure(tmp_path/'pending.zip',c)
    assert Path(p.path).is_file() and p.status is StablePromotionClosureStatus.PENDING


def test_wave70_blocked_closure_refuses_packaging(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package,status='blocked'); c=build_stable_release_promotion_closure(audit,package.path,a)
    with pytest.raises(ValueError,match='BLOCKED'):
        package_stable_release_promotion_closure(tmp_path/'blocked.zip',c)


def test_wave70_changed_acceptance_artifact_refuses_packaging(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package); c=build_stable_release_promotion_closure(audit,package.path,a)
    Path(a.artifacts[0].path).write_text('changed\n')
    with pytest.raises(ValueError,match='BLOCKED'):
        package_stable_release_promotion_closure(tmp_path/'bad.zip',c)


def test_wave70_closed_next_action_is_retention_not_deploy_claim(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package); c=build_stable_release_promotion_closure(audit,package.path,a)
    assert c.closed and 'Retain' in c.next_actions[0] and 'publication' in c.next_actions[0]


def test_wave70_acceptance_cli_outputs_normalized_acceptance(tmp_path: Path,monkeypatch,capsys):
    audit,package=_closed_audit(tmp_path); audit_path=write_release_audit_closure(tmp_path/'audit.json',audit); manifest=_acceptance_manifest(tmp_path,audit,package); out=tmp_path/'acceptance.json'
    monkeypatch.setattr('sys.argv',['nicegui-base release-evidence-accept',str(audit_path),package.path,str(manifest),'--output',str(out),'--format','json'])
    assert release_evidence_accept_main()==0 and out.is_file()
    payload=json.loads(capsys.readouterr().out); assert payload['verification']['status']=='accepted'


def test_wave70_promotion_close_cli_builds_package(tmp_path: Path,monkeypatch,capsys):
    audit,package=_closed_audit(tmp_path); audit_path=write_release_audit_closure(tmp_path/'audit.json',audit); a=_acceptance(tmp_path,audit,package); acceptance_path=write_stable_release_evidence_acceptance(tmp_path/'acceptance.json',a); out=tmp_path/'closure.json'; z=tmp_path/'closure.zip'
    monkeypatch.setattr('sys.argv',['nicegui-base promotion-close',str(audit_path),package.path,str(acceptance_path),'--output',str(out),'--package',str(z),'--format','json'])
    assert promotion_close_main()==0 and out.is_file() and z.is_file()
    payload=json.loads(capsys.readouterr().out); assert payload['closure']['status']=='closed'


def test_wave70_root_public_api_exports_new_contracts():
    import nicegui_base
    for name in ('StableReleaseEvidenceAcceptance','StableReleasePromotionClosure','verify_release_audit_archive','package_stable_release_promotion_closure','SemiconductorStablePromotionClosurePanel'):
        assert hasattr(nicegui_base,name),name


def test_wave70_generated_semiconductor_starter_includes_acceptance_and_closure_helpers(tmp_path: Path):
    from nicegui_base.ai.project import create_application
    app=create_application(tmp_path/'app',name='Wave70 Starter',recipe='spc-monitor')
    source=(app.root/'services/release_evidence.py').read_text()
    assert 'def accept_stable_release_evidence' in source
    assert 'def close_stable_promotion_evidence' in source
    assert 'verify_release_audit_archive' in source
    compile(source,str(app.root/'services/release_evidence.py'),'exec')


def test_wave70_acceptance_cli_pending_returns_two(tmp_path: Path,capsys):
    audit,package=_closed_audit(tmp_path); audit_path=write_release_audit_closure(tmp_path/'audit.json',audit); manifest=_acceptance_manifest(tmp_path,audit,package,status='pending')
    rc=release_evidence_accept_main(['nicegui-base release-evidence-accept',str(audit_path),package.path,str(manifest),'--format','json'])
    assert rc==2 and json.loads(capsys.readouterr().out)['verification']['status']=='pending'


def test_wave70_acceptance_cli_blocked_returns_one(tmp_path: Path,capsys):
    audit,package=_closed_audit(tmp_path); audit_path=write_release_audit_closure(tmp_path/'audit.json',audit); manifest=_acceptance_manifest(tmp_path,audit,package,status='blocked')
    rc=release_evidence_accept_main(['nicegui-base release-evidence-accept',str(audit_path),package.path,str(manifest),'--format','json'])
    assert rc==1 and json.loads(capsys.readouterr().out)['verification']['status']=='blocked'


def test_wave70_promotion_close_pending_returns_two(tmp_path: Path,capsys):
    audit,package=_closed_audit(tmp_path); audit_path=write_release_audit_closure(tmp_path/'audit.json',audit); a=_acceptance(tmp_path,audit,package,status='pending'); ap=write_stable_release_evidence_acceptance(tmp_path/'a.json',a)
    rc=promotion_close_main(['nicegui-base promotion-close',str(audit_path),package.path,str(ap),'--format','json'])
    assert rc==2 and json.loads(capsys.readouterr().out)['closure']['status']=='pending'


def test_wave70_promotion_close_blocked_returns_one(tmp_path: Path,capsys):
    audit,package=_closed_audit(tmp_path); audit_path=write_release_audit_closure(tmp_path/'audit.json',audit); a=_acceptance(tmp_path,audit,package,status='blocked'); ap=write_stable_release_evidence_acceptance(tmp_path/'a.json',a)
    rc=promotion_close_main(['nicegui-base promotion-close',str(audit_path),package.path,str(ap),'--format','json'])
    assert rc==1 and json.loads(capsys.readouterr().out)['closure']['status']=='blocked'


def test_wave70_acceptance_bound_to_other_audit_blocks(tmp_path: Path):
    audit1,package1=_closed_audit(tmp_path/'a'); audit2,_=_closed_audit(tmp_path/'b'); a=_acceptance(tmp_path/'a',audit1,package1)
    report=verify_stable_release_evidence_acceptance(a,audit=audit2,audit_archive_path=package1.path)
    assert report.blocked and any(f.code=='acceptance_subject_mismatch' for f in report.findings)


def test_wave70_closure_requires_actual_audit_archive_bytes(tmp_path: Path):
    audit,package=_closed_audit(tmp_path); a=_acceptance(tmp_path,audit,package); Path(package.path).unlink()
    with pytest.raises(FileNotFoundError):
        build_stable_release_promotion_closure(audit,package.path,a)


def test_wave70_audit_archive_invalid_zip_blocks(tmp_path: Path):
    path=tmp_path/'bad.zip';path.write_bytes(b'not-a-zip')
    report=verify_release_audit_archive(path)
    assert not report.verified and any(f.code=='audit_archive_invalid' for f in report.findings)


def test_wave70_main_cli_routes_new_commands(tmp_path: Path,monkeypatch,capsys):
    from nicegui_base.cli import main
    audit,package=_closed_audit(tmp_path); audit_path=write_release_audit_closure(tmp_path/'audit.json',audit); manifest=_acceptance_manifest(tmp_path,audit,package); out=tmp_path/'a.json'
    monkeypatch.setattr('sys.argv',['nicegui-base','release-evidence-accept',str(audit_path),package.path,str(manifest),'--output',str(out),'--format','json'])
    assert main()==0 and out.is_file()
    assert json.loads(capsys.readouterr().out)['verification']['status']=='accepted'


def test_wave70_source_evidence_declares_wave69_and_wave70_without_release_or_deployment_claims(tmp_path: Path):
    from nicegui_base.certification.mac_coverage import coverage_summary
    from nicegui_base.governance.source_evidence import _sync_packaged_certification_manifest

    root = Path(__file__).resolve().parents[1]
    source = root / 'nicegui_base/certification/certification_manifest.json'
    target = tmp_path / 'nicegui_base/certification/certification_manifest.json'
    target.parent.mkdir(parents=True)
    target.write_text(source.read_text(encoding='utf-8'), encoding='utf-8')

    _sync_packaged_certification_manifest(tmp_path, test_count=1219, coverage=coverage_summary())
    payload = json.loads(target.read_text(encoding='utf-8'))
    assert payload['phase'] >= 70
    phase69 = payload['phase_69_v300a8_enterprise_promotion_execution_adapter_qualification_release_audit_closure']
    phase70 = payload['phase_70_v300a8_enterprise_stable_release_evidence_acceptance_promotion_closure']
    assert phase69['release_audit_closed_means_evidence_completeness_only'] is True
    assert phase69['company_deployment_execution'] == 'NOT PERFORMED BY GENERIC FRAMEWORK'
    assert phase70['stable_closure_is_documentary_evidence_closure_only'] is True
    assert phase70['stable_closure_never_deploys_or_publishes_stable_release'] is True
    assert phase70['target_runtime_browser_company_human_gates'] == 'PENDING FOR CURRENT SOURCE'
    assert phase70['stable_3_0_0_publication'] == 'NOT PERFORMED BY GENERIC FRAMEWORK'
