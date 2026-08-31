from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nicegui_base import (
    FRAMEWORK_VERSION, NICEGUI_VERSION,
    JsonStableReleasePublicationEvidenceAdapter,
    OperationalReadinessCheck, OperationalReadinessState,
    POST_PROMOTION_VERIFICATION_POLICIES, POST_PROMOTION_VERIFICATION_POLICY,
    PostPromotionVerificationStatus, PromotionCandidateStatus, PromotionRehearsalKind,
    ReleaseAuditStatus, SEMICONDUCTOR_OPERATIONAL_RUNBOOKS,
    STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS,
    SemiconductorOperationalReadiness, SemiconductorTargetEvidenceBundle, SemiconductorTargetRuntimeCertification,
    StablePromotionClosureArchiveStatus, StableReleasePublicationStatus,
    TargetEnvironmentFingerprint, TargetGateStatus, TargetRuntimeGate,
    assimilate_enterprise_target_evidence, build_promotion_operation_record, build_promotion_rehearsal,
    build_release_audit_closure, build_stable_post_promotion_verification, build_stable_promotion_candidate,
    build_stable_promotion_operational_handoff, build_stable_release_promotion_closure,
    capture_promotion_operation_evidence, capture_target_evidence_artifact,
    load_promotion_execution_adapter_qualification_manifest, load_stable_post_promotion_verification_manifest,
    load_stable_release_evidence_acceptance_manifest, load_stable_release_publication_evidence_manifest,
    package_release_audit_closure, package_stable_post_promotion_verification, package_stable_promotion_candidate,
    package_stable_release_promotion_closure, read_stable_post_promotion_verification,
    read_stable_release_publication_evidence, stable_post_promotion_verification_from_dict,
    stable_release_publication_evidence_from_dict, verify_stable_promotion_closure_archive,
    verify_stable_release_publication_evidence, write_stable_post_promotion_verification,
    write_stable_release_promotion_closure, write_stable_release_publication_evidence,
)
from nicegui_base.certification.semiconductor_publication_cli import post_promotion_verify_main, release_publication_intake_main


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _ready_bundle(tmp_path: Path, recipe='spc-monitor', provider='sqlite', source_key='target'):
    tmp_path.mkdir(parents=True, exist_ok=True)
    gates=[]; artifacts=[]
    for key,label in (
        ('company_adapter','Approved company adapter conformance'),('fab_scale_pushdown','Representative fab-scale pushdown/performance'),
        ('installed_nicegui','Installed NiceGUI 3.15.0'),('server_websocket','Real server/WebSocket lifecycle'),
        ('supported_browser','Supported corporate browser'),('human_visual_baseline','Human visual baseline'),
        ('provider_benchmark','Governed representative provider benchmark'),
    ):
        gates.append(TargetRuntimeGate(key,label,TargetGateStatus.PASS,'verified fixture',{'provider':provider,'source_key':source_key}))
        if key in {'installed_nicegui','server_websocket','supported_browser','human_visual_baseline'}:
            p=tmp_path/f'{key}.json'; p.write_text(json.dumps({'key':key})+'\n')
            artifacts.append(capture_target_evidence_artifact(p,key=key))
    return SemiconductorTargetEvidenceBundle(
        recipe, SemiconductorTargetRuntimeCertification(recipe,tuple(gates)),
        TargetEnvironmentFingerprint('3.12.0','enterprise-test',NICEGUI_VERSION,'python'), tuple(artifacts),
        {'profile_key':'provider-rc','provider':provider,'source_key':source_key,'passed':True},
        {'provider':provider,'source_key':source_key,'passed':True}, {'provider':provider,'source_key':source_key,'passed':True},
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
    return build_stable_promotion_operational_handoff(candidate,package.path,change_reference='CHG-wave71-fixture')


def _qualification(tmp_path: Path):
    p=tmp_path/'adapter-qualification.json';p.write_text('{"qualified":true}\n')
    payload={'schema_version':1,'adapter_key':'company-release','adapter_version':'1.2.3','status':'qualified',
        'supported_operations':[item.value for item in PromotionRehearsalKind],'framework_version':FRAMEWORK_VERSION,'nicegui_version':NICEGUI_VERSION,
        'qualification_authority':'approved-company-process','approval_reference':'APR-69','artifacts':[{'key':'qualification-run','path':p.name}]}
    path=tmp_path/'adapter-manifest.json';path.write_text(json.dumps(payload,indent=2)+'\n')
    return load_promotion_execution_adapter_qualification_manifest(path)


def _operation(tmp_path: Path, handoff):
    kind=PromotionRehearsalKind.PROMOTION; plan=build_promotion_rehearsal('spc-monitor',kind)
    runbook=SEMICONDUCTOR_OPERATIONAL_RUNBOOKS['spc-monitor']; steps={s.key:s for s in runbook.steps}; evidence=[]
    for step in plan.required_step_keys:
        for evidence_key in steps[step].evidence_to_capture:
            p=tmp_path/f'promotion-{step}-{evidence_key}.json';p.write_text(json.dumps({'step':step,'evidence':evidence_key})+'\n')
            evidence.append(capture_promotion_operation_evidence(p,recipe_key='spc-monitor',step_key=step,evidence_key=evidence_key))
    return build_promotion_operation_record(handoff,'spc-monitor',kind,completed_step_keys=plan.required_step_keys,evidence=evidence)


def _closed_wave70(tmp_path: Path):
    tmp_path.mkdir(parents=True,exist_ok=True)
    handoff=_handoff(tmp_path); q=_qualification(tmp_path); op=_operation(tmp_path,handoff)
    audit=build_release_audit_closure(handoff,q,(op,)); assert audit.status is ReleaseAuditStatus.CLOSED
    audit_package=package_release_audit_closure(tmp_path/'release-audit.zip',audit)
    approval=tmp_path/'release-acceptance.json';approval.write_text('{"accepted":true}\n')
    manifest=tmp_path/'acceptance-manifest.json';manifest.write_text(json.dumps({
        'schema_version':1,'status':'accepted','audit_id':audit.audit_id,'candidate_id':audit.handoff.candidate.candidate_id,
        'audit_archive_sha256':audit_package.sha256,'framework_version':FRAMEWORK_VERSION,'nicegui_version':NICEGUI_VERSION,
        'acceptance_authority':'approved-company-release-board','approval_reference':'REL-70','artifacts':[{'key':'release-approval','path':approval.name}],
    },indent=2)+'\n')
    acceptance=load_stable_release_evidence_acceptance_manifest(manifest,audit,audit_package.path)
    closure=build_stable_release_promotion_closure(audit,audit_package.path,acceptance)
    assert closure.closed
    closure_package=package_stable_release_promotion_closure(tmp_path/'promotion-closure.zip',closure)
    return closure,closure_package


def _publication_manifest(tmp_path: Path, closure, package, *, status='published', framework=FRAMEWORK_VERSION, nicegui=NICEGUI_VERSION, artifacts=True, authority=True):
    rows=[]
    if artifacts:
        p=tmp_path/'stable-publication-receipt.json';p.write_text(json.dumps({'published':status=='published'})+'\n')
        rows=[{'key':'stable-publication-record','path':p.name}]
    payload={'schema_version':1,'status':status,'closure_id':closure.closure_id,
        'candidate_id':closure.release_audit.handoff.candidate.candidate_id,'closure_archive_sha256':package.sha256,
        'target_version':closure.policy.target_version,'framework_version':framework,'nicegui_version':nicegui,
        'publication_authority':'approved-company-release-service' if authority else None,
        'publication_reference':'PUB-71' if authority else None,'deployment_reference':'DEP-71' if authority else None,'artifacts':rows}
    path=tmp_path/'publication-manifest.json';path.write_text(json.dumps(payload,indent=2)+'\n');return path


def _publication(tmp_path: Path, closure, package, **kwargs):
    return load_stable_release_publication_evidence_manifest(_publication_manifest(tmp_path,closure,package,**kwargs),closure,package.path)


def _post_manifest(tmp_path: Path, closure, publication, *, status='verified', framework=FRAMEWORK_VERSION, nicegui=NICEGUI_VERSION, artifacts=True, authority=True):
    rows=[]
    if artifacts:
        for key in POST_PROMOTION_VERIFICATION_POLICY.required_artifact_keys:
            p=tmp_path/f'{key}.json';p.write_text(json.dumps({'key':key,'ok':True})+'\n');rows.append({'key':key,'path':p.name})
    payload={'schema_version':1,'status':status,'closure_id':closure.closure_id,'publication_id':publication.publication_id,
        'target_version':closure.policy.target_version,'framework_version':framework,'nicegui_version':nicegui,
        'verification_authority':'approved-post-release-process' if authority else None,
        'verification_reference':'POST-71' if authority else None,'artifacts':rows}
    path=tmp_path/'post-manifest.json';path.write_text(json.dumps(payload,indent=2)+'\n');return path


def _post(tmp_path: Path, closure, package, publication, **kwargs):
    return load_stable_post_promotion_verification_manifest(_post_manifest(tmp_path,closure,publication,**kwargs),closure,package.path,publication)


def test_wave71_registry_bounded_provider_neutral():
    assert set(STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS)=={'json-manifest'}
    assert isinstance(STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS['json-manifest'],JsonStableReleasePublicationEvidenceAdapter)


def test_wave71_post_policy_registered():
    assert POST_PROMOTION_VERIFICATION_POLICIES['stable'] is POST_PROMOTION_VERIFICATION_POLICY
    assert POST_PROMOTION_VERIFICATION_POLICY.target_version=='3.0.0'


def test_wave71_closure_archive_independently_verifies(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path)
    report=verify_stable_promotion_closure_archive(package.path,expected_closure=closure)
    assert report.status is StablePromotionClosureArchiveStatus.VERIFIED and report.verified
    assert report.closure_id==closure.closure_id


def test_wave71_closure_archive_missing_blocks(tmp_path: Path):
    report=verify_stable_promotion_closure_archive(tmp_path/'missing.zip')
    assert not report.verified and report.findings[0].code=='closure_archive_missing'


def test_wave71_closure_archive_duplicate_blocks(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path)
    with zipfile.ZipFile(package.path,'a') as z:z.writestr('promotion-closure.json',b'changed')
    assert any(f.code=='closure_archive_duplicate_entry' for f in verify_stable_promotion_closure_archive(package.path,expected_closure=closure).findings)


def test_wave71_closure_archive_changed_hash_blocks(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path)
    with zipfile.ZipFile(package.path,'a') as z:z.writestr('extra.txt',b'x')
    report=verify_stable_promotion_closure_archive(package.path,expected_closure=closure)
    assert not report.verified


def test_wave71_invalid_zip_blocks(tmp_path: Path):
    path=tmp_path/'bad.zip';path.write_bytes(b'bad')
    assert any(f.code=='closure_archive_invalid' for f in verify_stable_promotion_closure_archive(path).findings)


def test_wave71_published_evidence_verifies_when_traceable(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); evidence=_publication(tmp_path,closure,package)
    report=verify_stable_release_publication_evidence(evidence,closure=closure,closure_archive_path=package.path)
    assert report.published and report.status is StableReleasePublicationStatus.PUBLISHED


def test_wave71_requested_published_without_artifact_stays_pending(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); evidence=_publication(tmp_path,closure,package,artifacts=False)
    report=verify_stable_release_publication_evidence(evidence,closure=closure,closure_archive_path=package.path)
    assert report.status is StableReleasePublicationStatus.PENDING
    assert any(f.code=='publication_artifacts_missing' for f in report.findings)


def test_wave71_requested_published_without_authority_stays_pending(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); evidence=_publication(tmp_path,closure,package,authority=False)
    report=verify_stable_release_publication_evidence(evidence,closure=closure,closure_archive_path=package.path)
    assert report.status is StableReleasePublicationStatus.PENDING


def test_wave71_requested_published_without_identity_stays_pending(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); manifest=_publication_manifest(tmp_path,closure,package)
    payload=json.loads(manifest.read_text());payload.pop('framework_version');payload.pop('nicegui_version');manifest.write_text(json.dumps(payload))
    evidence=load_stable_release_publication_evidence_manifest(manifest,closure,package.path)
    assert verify_stable_release_publication_evidence(evidence,closure=closure,closure_archive_path=package.path).status is StableReleasePublicationStatus.PENDING


def test_wave71_framework_mismatch_blocks(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); evidence=_publication(tmp_path,closure,package,framework='0.0.0')
    report=verify_stable_release_publication_evidence(evidence,closure=closure,closure_archive_path=package.path)
    assert report.blocked and any(f.code=='publication_framework_mismatch' for f in report.findings)


def test_wave71_nicegui_mismatch_blocks(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); evidence=_publication(tmp_path,closure,package,nicegui='3.14.0')
    assert verify_stable_release_publication_evidence(evidence,closure=closure,closure_archive_path=package.path).blocked


def test_wave71_explicit_blocked_propagates(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); evidence=_publication(tmp_path,closure,package,status='blocked')
    assert verify_stable_release_publication_evidence(evidence,closure=closure,closure_archive_path=package.path).status is StableReleasePublicationStatus.BLOCKED


def test_wave71_explicit_pending_propagates(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); evidence=_publication(tmp_path,closure,package,status='pending')
    assert verify_stable_release_publication_evidence(evidence,closure=closure,closure_archive_path=package.path).status is StableReleasePublicationStatus.PENDING


def test_wave71_changed_publication_artifact_blocks(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); evidence=_publication(tmp_path,closure,package)
    Path(evidence.artifacts[0].path).write_text('changed\n')
    assert verify_stable_release_publication_evidence(evidence,closure=closure,closure_archive_path=package.path).blocked


def test_wave71_changed_closure_archive_blocks_publication(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); evidence=_publication(tmp_path,closure,package)
    Path(package.path).write_bytes(Path(package.path).read_bytes()+b'x')
    assert verify_stable_release_publication_evidence(evidence,closure=closure,closure_archive_path=package.path).blocked


def test_wave71_publication_round_trip_identity(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); evidence=_publication(tmp_path,closure,package); path=write_stable_release_publication_evidence(tmp_path/'publication.json',evidence)
    assert read_stable_release_publication_evidence(path).publication_id==evidence.publication_id


def test_wave71_publication_tamper_detected(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); evidence=_publication(tmp_path,closure,package); payload=evidence.to_dict();payload['publication_reference']='CHANGED'
    with pytest.raises(ValueError,match='id does not match'):
        stable_release_publication_evidence_from_dict(payload)


def test_wave71_manifest_subject_mismatch_rejected(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); manifest=_publication_manifest(tmp_path,closure,package);payload=json.loads(manifest.read_text());payload['closure_id']='0'*64;manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='closure_id'):
        load_stable_release_publication_evidence_manifest(manifest,closure,package.path)


def test_wave71_manifest_path_escape_rejected(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); outside=tmp_path.parent/'outside.json';outside.write_text('{}')
    manifest=_publication_manifest(tmp_path,closure,package);payload=json.loads(manifest.read_text());payload['artifacts']=[{'key':'x','path':'../outside.json'}];manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='escapes'):
        load_stable_release_publication_evidence_manifest(manifest,closure,package.path)


def test_wave71_post_verification_complete_is_verified(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication)
    assert post.verified and post.status is PostPromotionVerificationStatus.VERIFIED
    assert post.to_dict()['publication_performed_by_framework'] is False


def test_wave71_post_verification_missing_required_artifact_pending(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication,artifacts=False)
    assert post.status is PostPromotionVerificationStatus.PENDING
    assert any(f.code=='post_release_required_artifact_missing' for f in post.findings)


def test_wave71_post_verification_pending_request_pending(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication,status='pending')
    assert post.status is PostPromotionVerificationStatus.PENDING


def test_wave71_post_verification_blocked_request_blocked(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication,status='blocked')
    assert post.status is PostPromotionVerificationStatus.BLOCKED


def test_wave71_post_verification_requires_published_publication(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package,status='pending'); post=_post(tmp_path,closure,package,publication)
    assert post.status is PostPromotionVerificationStatus.PENDING


def test_wave71_post_verification_publication_blocked_blocks(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package,status='blocked'); post=_post(tmp_path,closure,package,publication)
    assert post.status is PostPromotionVerificationStatus.BLOCKED


def test_wave71_post_verification_identity_missing_pending(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); manifest=_post_manifest(tmp_path,closure,publication);payload=json.loads(manifest.read_text());payload.pop('framework_version');payload.pop('nicegui_version');manifest.write_text(json.dumps(payload))
    post=load_stable_post_promotion_verification_manifest(manifest,closure,package.path,publication)
    assert post.status is PostPromotionVerificationStatus.PENDING


def test_wave71_post_verification_authority_missing_pending(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication,authority=False)
    assert post.status is PostPromotionVerificationStatus.PENDING


def test_wave71_post_framework_mismatch_blocks(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication,framework='0.0.0')
    assert post.status is PostPromotionVerificationStatus.BLOCKED


def test_wave71_post_nicegui_mismatch_blocks(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication,nicegui='3.14.0')
    assert post.status is PostPromotionVerificationStatus.BLOCKED


def test_wave71_post_round_trip_identity(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication); path=write_stable_post_promotion_verification(tmp_path/'post.json',post)
    assert read_stable_post_promotion_verification(path).verification_id==post.verification_id


def test_wave71_post_tamper_detected(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication);payload=post.to_dict();payload['verification_reference']='changed'
    with pytest.raises(ValueError,match='id does not match'):
        stable_post_promotion_verification_from_dict(payload)


def test_wave71_post_manifest_subject_mismatch_rejected(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); manifest=_post_manifest(tmp_path,closure,publication);payload=json.loads(manifest.read_text());payload['publication_id']='0'*64;manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='publication_id'):
        load_stable_post_promotion_verification_manifest(manifest,closure,package.path,publication)


def test_wave71_post_package_deterministic(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication)
    p1=package_stable_post_promotion_verification(tmp_path/'p1.zip',post);p2=package_stable_post_promotion_verification(tmp_path/'p2.zip',post)
    assert p1.sha256==p2.sha256


def test_wave71_post_package_manifest_verifies(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication); p=package_stable_post_promotion_verification(tmp_path/'post.zip',post)
    with zipfile.ZipFile(p.path) as z:
        expected={name:sha for sha,name in (line.split('  ',1) for line in z.read('MANIFEST.sha256').decode().splitlines())}
        assert set(expected)==set(z.namelist())-{'MANIFEST.sha256'}
        assert all(hashlib.sha256(z.read(name)).hexdigest()==sha for name,sha in expected.items())


def test_wave71_pending_post_can_package_for_gap_handoff(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication,status='pending')
    assert Path(package_stable_post_promotion_verification(tmp_path/'pending.zip',post).path).is_file()


def test_wave71_blocked_post_refuses_packaging(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication,status='blocked')
    with pytest.raises(ValueError,match='BLOCKED'):
        package_stable_post_promotion_verification(tmp_path/'blocked.zip',post)


def test_wave71_changed_post_artifact_refuses_packaging(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path); publication=_publication(tmp_path,closure,package); post=_post(tmp_path,closure,package,publication);Path(post.artifacts[0].path).write_text('changed\n')
    with pytest.raises(ValueError,match='BLOCKED'):
        package_stable_post_promotion_verification(tmp_path/'bad.zip',post)


def test_wave71_publication_cli_published_zero(tmp_path: Path,capsys):
    closure,package=_closed_wave70(tmp_path);cp=write_stable_release_promotion_closure(tmp_path/'closure.json',closure);manifest=_publication_manifest(tmp_path,closure,package);out=tmp_path/'publication.json'
    rc=release_publication_intake_main(['nicegui-base release-publication-intake',str(cp),package.path,str(manifest),'--output',str(out),'--format','json'])
    assert rc==0 and out.is_file() and json.loads(capsys.readouterr().out)['verification']['status']=='published'


def test_wave71_publication_cli_pending_two(tmp_path: Path,capsys):
    closure,package=_closed_wave70(tmp_path);cp=write_stable_release_promotion_closure(tmp_path/'closure.json',closure);manifest=_publication_manifest(tmp_path,closure,package,status='pending')
    assert release_publication_intake_main(['nicegui-base release-publication-intake',str(cp),package.path,str(manifest),'--format','json'])==2
    capsys.readouterr()


def test_wave71_publication_cli_blocked_one(tmp_path: Path,capsys):
    closure,package=_closed_wave70(tmp_path);cp=write_stable_release_promotion_closure(tmp_path/'closure.json',closure);manifest=_publication_manifest(tmp_path,closure,package,status='blocked')
    assert release_publication_intake_main(['nicegui-base release-publication-intake',str(cp),package.path,str(manifest),'--format','json'])==1
    capsys.readouterr()


def test_wave71_post_cli_verified_zero_and_package(tmp_path: Path,capsys):
    closure,package=_closed_wave70(tmp_path);cp=write_stable_release_promotion_closure(tmp_path/'closure.json',closure);publication=_publication(tmp_path,closure,package);pp=write_stable_release_publication_evidence(tmp_path/'publication.json',publication);manifest=_post_manifest(tmp_path,closure,publication);out=tmp_path/'post.json';z=tmp_path/'post.zip'
    rc=post_promotion_verify_main(['nicegui-base post-promotion-verify',str(cp),package.path,str(pp),str(manifest),'--output',str(out),'--package',str(z),'--format','json'])
    assert rc==0 and out.is_file() and z.is_file() and json.loads(capsys.readouterr().out)['verification']['status']=='verified'


def test_wave71_post_cli_pending_two(tmp_path: Path,capsys):
    closure,package=_closed_wave70(tmp_path);cp=write_stable_release_promotion_closure(tmp_path/'closure.json',closure);publication=_publication(tmp_path,closure,package);pp=write_stable_release_publication_evidence(tmp_path/'publication.json',publication);manifest=_post_manifest(tmp_path,closure,publication,status='pending')
    assert post_promotion_verify_main(['nicegui-base post-promotion-verify',str(cp),package.path,str(pp),str(manifest),'--format','json'])==2
    capsys.readouterr()


def test_wave71_root_public_api_exports_new_contracts():
    import nicegui_base
    for name in ('StableReleasePublicationEvidence','StablePostPromotionVerification','verify_stable_promotion_closure_archive','package_stable_post_promotion_verification'):
        assert hasattr(nicegui_base,name),name


def test_wave71_main_cli_routes_publication_command(tmp_path: Path,monkeypatch,capsys):
    from nicegui_base.cli import main
    closure,package=_closed_wave70(tmp_path);cp=write_stable_release_promotion_closure(tmp_path/'closure.json',closure);manifest=_publication_manifest(tmp_path,closure,package);out=tmp_path/'publication.json'
    monkeypatch.setattr('sys.argv',['nicegui-base','release-publication-intake',str(cp),package.path,str(manifest),'--output',str(out),'--format','json'])
    assert main()==0 and out.is_file();capsys.readouterr()


def test_wave71_verified_post_next_action_is_retention_not_monitoring_claim(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path);publication=_publication(tmp_path,closure,package);post=_post(tmp_path,closure,package,publication)
    assert post.verified and 'Retain' in post.next_actions[0] and 'external' in post.next_actions[0]


def test_wave71_generated_semiconductor_starter_includes_publication_helpers(tmp_path: Path):
    from nicegui_base.ai.project import create_application
    app=create_application(tmp_path/'app',name='Wave71 Starter',recipe='spc-monitor')
    source=(app.root/'services/release_evidence.py').read_text()
    assert 'def intake_stable_release_publication' in source
    assert 'def verify_post_promotion_release' in source
    assert 'verify_stable_promotion_closure_archive' in source
    compile(source,str(app.root/'services/release_evidence.py'),'exec')


def test_wave71_ui_panels_are_public():
    import nicegui_base
    assert hasattr(nicegui_base,'SemiconductorStableReleasePublicationPanel')
    assert hasattr(nicegui_base,'SemiconductorPostPromotionVerificationPanel')


def test_wave71_source_evidence_declares_publication_boundary(tmp_path: Path):
    from nicegui_base.certification.mac_coverage import coverage_summary
    from nicegui_base.governance.source_evidence import _sync_packaged_certification_manifest
    root=Path(__file__).resolve().parents[1]
    source=root/'nicegui_base/certification/certification_manifest.json'
    target=tmp_path/'nicegui_base/certification/certification_manifest.json';target.parent.mkdir(parents=True);target.write_text(source.read_text())
    _sync_packaged_certification_manifest(tmp_path,test_count=1,coverage=coverage_summary())
    payload=json.loads(target.read_text())
    assert payload['phase'] >= 71
    phase71=payload['phase_71_v300a8_enterprise_release_publication_evidence_post_promotion_verification']
    assert phase71['post_promotion_verification_is_evidence_verification_only'] is True
    assert phase71['stable_3_0_0_publication']=='NOT PERFORMED BY GENERIC FRAMEWORK'
    assert phase71['continuous_post_release_monitoring']=='NOT PERFORMED BY GENERIC FRAMEWORK'


def test_wave71_closure_archive_recomputed_manifest_cannot_hide_tampered_acceptance(tmp_path: Path):
    closure,package=_closed_wave70(tmp_path)
    target=Path(package.path)
    with zipfile.ZipFile(target) as src:
        entries={name:src.read(name) for name in src.namelist() if name!='MANIFEST.sha256'}
    payload=json.loads(entries['release-evidence-acceptance.json'].decode())
    payload['approval_reference']='TAMPERED'
    entries['release-evidence-acceptance.json']=(json.dumps(payload,sort_keys=True)+'\n').encode()
    manifest=''.join(f'{hashlib.sha256(entries[name]).hexdigest()}  {name}\n' for name in sorted(entries)).encode()
    with zipfile.ZipFile(target,'w') as out:
        for name in sorted(entries): out.writestr(name,entries[name])
        out.writestr('MANIFEST.sha256',manifest)
    report=verify_stable_promotion_closure_archive(target,expected_closure=closure)
    assert not report.verified and any(f.code=='closure_archive_acceptance_invalid' for f in report.findings)
