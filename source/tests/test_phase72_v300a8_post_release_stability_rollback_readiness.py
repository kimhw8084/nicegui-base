from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nicegui_base import (
    FRAMEWORK_VERSION, NICEGUI_VERSION,
    JsonPostReleaseStabilityEvidenceAdapter, OperationalReadinessCheck, OperationalReadinessState,
    POST_PROMOTION_VERIFICATION_POLICY, POST_RELEASE_STABILITY_EVIDENCE_ADAPTERS, POST_RELEASE_STABILITY_POLICIES,
    POST_RELEASE_STABILITY_POLICY, ROLLBACK_READINESS_POLICIES, ROLLBACK_READINESS_POLICY,
    PostReleaseStabilityPolicy, PostReleaseStabilityStatus, PromotionCandidateStatus, PromotionRehearsalKind,
    ReleaseAuditStatus, RollbackReadinessPolicy, RollbackReadinessStatus, SEMICONDUCTOR_OPERATIONAL_RUNBOOKS,
    SemiconductorOperationalReadiness, SemiconductorTargetEvidenceBundle, SemiconductorTargetRuntimeCertification,
    StablePostPromotionArchiveStatus, TargetEnvironmentFingerprint, TargetGateStatus, TargetRuntimeGate,
    assimilate_enterprise_target_evidence, build_post_release_stability_evidence, build_promotion_operation_record,
    build_promotion_rehearsal, build_release_audit_closure, build_stable_post_promotion_verification,
    build_stable_promotion_candidate, build_stable_promotion_operational_handoff, build_stable_release_promotion_closure,
    build_stable_rollback_readiness_verification, capture_promotion_operation_evidence, capture_target_evidence_artifact,
    load_promotion_execution_adapter_qualification_manifest, load_post_release_stability_manifest,
    load_stable_post_promotion_verification_manifest, load_stable_release_evidence_acceptance_manifest,
    load_stable_release_publication_evidence_manifest, load_stable_rollback_readiness_manifest,
    package_release_audit_closure, package_stable_post_promotion_verification, package_stable_promotion_candidate,
    package_stable_release_promotion_closure, package_stable_rollback_readiness_verification,
    post_release_stability_evidence_from_dict, read_post_release_stability_evidence,
    read_stable_rollback_readiness_verification, stable_rollback_readiness_verification_from_dict,
    verify_post_release_stability_evidence, verify_stable_post_promotion_archive,
    write_post_release_stability_evidence, write_stable_rollback_readiness_verification,
)
from nicegui_base.certification.semiconductor_stability_cli import post_release_stability_intake_main, rollback_readiness_verify_main


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
    return build_stable_promotion_operational_handoff(candidate,package.path,change_reference='CHG-wave72-fixture')


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
    closure=build_stable_release_promotion_closure(audit,audit_package.path,acceptance); assert closure.closed
    closure_package=package_stable_release_promotion_closure(tmp_path/'promotion-closure.zip',closure)
    return closure,closure_package


def _publication_manifest(tmp_path: Path, closure, package):
    p=tmp_path/'stable-publication-receipt.json';p.write_text('{"published":true}\n')
    payload={'schema_version':1,'status':'published','closure_id':closure.closure_id,
        'candidate_id':closure.release_audit.handoff.candidate.candidate_id,'closure_archive_sha256':package.sha256,
        'target_version':closure.policy.target_version,'framework_version':FRAMEWORK_VERSION,'nicegui_version':NICEGUI_VERSION,
        'publication_authority':'approved-company-release-service','publication_reference':'PUB-71','deployment_reference':'DEP-71',
        'artifacts':[{'key':'stable-publication-record','path':p.name}]}
    path=tmp_path/'publication-manifest.json';path.write_text(json.dumps(payload,indent=2)+'\n');return path


def _post(tmp_path: Path, *, reference='POST-71'):
    closure,package=_closed_wave70(tmp_path)
    publication=load_stable_release_publication_evidence_manifest(_publication_manifest(tmp_path,closure,package),closure,package.path)
    rows=[]
    for key in POST_PROMOTION_VERIFICATION_POLICY.required_artifact_keys:
        p=tmp_path/f'{key}.json';p.write_text(json.dumps({'key':key,'ok':True})+'\n');rows.append({'key':key,'path':p.name})
    manifest=tmp_path/'post-manifest.json';manifest.write_text(json.dumps({
        'schema_version':1,'status':'verified','closure_id':closure.closure_id,'publication_id':publication.publication_id,
        'target_version':closure.policy.target_version,'framework_version':FRAMEWORK_VERSION,'nicegui_version':NICEGUI_VERSION,
        'verification_authority':'approved-post-release-process','verification_reference':reference,'artifacts':rows,
    },indent=2)+'\n')
    post=load_stable_post_promotion_verification_manifest(manifest,closure,package.path,publication)
    post_package=package_stable_post_promotion_verification(tmp_path/f'post-{reference}.zip',post)
    return post,post_package


def _stability_manifest(tmp_path: Path, post, package, *, status='stable', framework=FRAMEWORK_VERSION, nicegui=NICEGUI_VERSION, artifacts=True, authority=True):
    rows=[]
    if artifacts:
        for key in POST_RELEASE_STABILITY_POLICY.required_artifact_keys:
            p=tmp_path/f'{key}.json';p.write_text(json.dumps({'key':key,'ok':True})+'\n');rows.append({'key':key,'path':p.name})
    payload={'schema_version':1,'status':status,'post_verification_id':post.verification_id,'publication_id':post.publication.publication_id,
        'target_version':post.policy.target_version,'framework_version':framework,'nicegui_version':nicegui,
        'stability_authority':'approved-production-health-process' if authority else None,
        'stability_reference':'STAB-72' if authority else None,'artifacts':rows}
    path=tmp_path/'stability-manifest.json';path.write_text(json.dumps(payload,indent=2)+'\n');return path


def _stability(tmp_path: Path, post, package, **kwargs):
    return load_post_release_stability_manifest(_stability_manifest(tmp_path,post,package,**kwargs),post,package.path)


def _rollback_manifest(tmp_path: Path, post, stability, *, status='ready', artifacts=True, authority=True, execution=False):
    rows=[]
    if artifacts:
        for key in ROLLBACK_READINESS_POLICY.required_artifact_keys:
            p=tmp_path/f'{key}.json';p.write_text(json.dumps({'key':key,'ok':True})+'\n');rows.append({'key':key,'path':p.name})
    execution_rows=[]
    if execution:
        p=tmp_path/'rollback-execution-record.json';p.write_text('{"external_rollback_executed":true}\n')
        execution_rows=[{'key':'rollback-execution-record','path':p.name}]
    payload={'schema_version':1,'status':status,'post_verification_id':post.verification_id,'stability_id':stability.stability_id,
        'target_version':post.policy.target_version,'readiness_authority':'approved-change-management' if authority else None,
        'readiness_reference':'RB-READY-72' if authority else None,
        'rollback_execution_reference':'RB-EXEC-72' if execution else None,'artifacts':rows,'rollback_execution_artifacts':execution_rows}
    path=tmp_path/'rollback-manifest.json';path.write_text(json.dumps(payload,indent=2)+'\n');return path


def _rollback(tmp_path: Path, post, package, stability, **kwargs):
    return load_stable_rollback_readiness_manifest(_rollback_manifest(tmp_path,post,stability,**kwargs),post,package.path,stability)


def test_wave72_registry_bounded_provider_neutral():
    assert set(POST_RELEASE_STABILITY_EVIDENCE_ADAPTERS)=={'json-manifest'}
    assert isinstance(POST_RELEASE_STABILITY_EVIDENCE_ADAPTERS['json-manifest'],JsonPostReleaseStabilityEvidenceAdapter)


def test_wave72_policies_registered():
    assert POST_RELEASE_STABILITY_POLICIES['stable'] is POST_RELEASE_STABILITY_POLICY
    assert ROLLBACK_READINESS_POLICIES['stable'] is ROLLBACK_READINESS_POLICY
    assert POST_RELEASE_STABILITY_POLICY.target_version==ROLLBACK_READINESS_POLICY.target_version=='3.0.0'


def test_wave72_post_archive_independently_verifies(tmp_path: Path):
    post,package=_post(tmp_path)
    report=verify_stable_post_promotion_archive(package.path,expected_verification=post)
    assert report.verified and report.status is StablePostPromotionArchiveStatus.VERIFIED
    assert report.verification_id==post.verification_id


def test_wave72_post_archive_missing_blocks(tmp_path: Path):
    report=verify_stable_post_promotion_archive(tmp_path/'missing.zip')
    assert not report.verified and report.findings[0].code=='post_promotion_archive_missing'


def test_wave72_post_archive_invalid_blocks(tmp_path: Path):
    path=tmp_path/'bad.zip';path.write_bytes(b'bad')
    assert verify_stable_post_promotion_archive(path).status is StablePostPromotionArchiveStatus.BLOCKED


def test_wave72_post_archive_duplicate_blocks(tmp_path: Path):
    post,package=_post(tmp_path)
    with zipfile.ZipFile(package.path,'a') as z:z.writestr('post-promotion-verification.json',b'changed')
    assert any(f.code=='post_promotion_archive_duplicate_entry' for f in verify_stable_post_promotion_archive(package.path,expected_verification=post).findings)


def test_wave72_post_archive_extra_entry_blocks_manifest_coverage(tmp_path: Path):
    post,package=_post(tmp_path)
    with zipfile.ZipFile(package.path,'a') as z:z.writestr('extra.txt',b'x')
    assert not verify_stable_post_promotion_archive(package.path,expected_verification=post).verified


def test_wave72_post_archive_wrong_subject_blocks(tmp_path: Path):
    post1,package1=_post(tmp_path/'a',reference='POST-A')
    post2,_=_post(tmp_path/'b',reference='POST-B')
    report=verify_stable_post_promotion_archive(package1.path,expected_verification=post2)
    assert any(f.code=='post_promotion_archive_identity_mismatch' for f in report.findings)


def test_wave72_stable_evidence_verifies_when_traceable(tmp_path: Path):
    post,package=_post(tmp_path); evidence=_stability(tmp_path,post,package)
    report=verify_post_release_stability_evidence(evidence,post_verification=post,post_promotion_archive_path=package.path)
    assert report.stable and report.status is PostReleaseStabilityStatus.STABLE
    assert evidence.to_dict()['monitoring_performed_by_framework'] is False


def test_wave72_requested_stable_without_artifacts_stays_pending(tmp_path: Path):
    post,package=_post(tmp_path); evidence=_stability(tmp_path,post,package,artifacts=False)
    report=verify_post_release_stability_evidence(evidence,post_verification=post,post_promotion_archive_path=package.path)
    assert report.status is PostReleaseStabilityStatus.PENDING


def test_wave72_requested_stable_without_authority_stays_pending(tmp_path: Path):
    post,package=_post(tmp_path); evidence=_stability(tmp_path,post,package,authority=False)
    assert verify_post_release_stability_evidence(evidence,post_verification=post,post_promotion_archive_path=package.path).status is PostReleaseStabilityStatus.PENDING


def test_wave72_requested_stable_without_identity_stays_pending(tmp_path: Path):
    post,package=_post(tmp_path); manifest=_stability_manifest(tmp_path,post,package); payload=json.loads(manifest.read_text());payload.pop('framework_version');payload.pop('nicegui_version');manifest.write_text(json.dumps(payload))
    evidence=load_post_release_stability_manifest(manifest,post,package.path)
    assert verify_post_release_stability_evidence(evidence,post_verification=post,post_promotion_archive_path=package.path).status is PostReleaseStabilityStatus.PENDING


@pytest.mark.parametrize(('framework','nicegui'), [('0.0.0',NICEGUI_VERSION),(FRAMEWORK_VERSION,'3.14.0')])
def test_wave72_observed_identity_mismatch_blocks(tmp_path: Path, framework: str, nicegui: str):
    post,package=_post(tmp_path); evidence=_stability(tmp_path,post,package,framework=framework,nicegui=nicegui)
    assert verify_post_release_stability_evidence(evidence,post_verification=post,post_promotion_archive_path=package.path).status is PostReleaseStabilityStatus.BLOCKED


@pytest.mark.parametrize(('requested','expected'), [('pending',PostReleaseStabilityStatus.PENDING),('blocked',PostReleaseStabilityStatus.BLOCKED)])
def test_wave72_explicit_stability_state_propagates(tmp_path: Path, requested: str, expected: PostReleaseStabilityStatus):
    post,package=_post(tmp_path); evidence=_stability(tmp_path,post,package,status=requested)
    assert verify_post_release_stability_evidence(evidence,post_verification=post,post_promotion_archive_path=package.path).status is expected


def test_wave72_changed_stability_artifact_blocks(tmp_path: Path):
    post,package=_post(tmp_path); evidence=_stability(tmp_path,post,package);Path(evidence.artifacts[0].path).write_text('changed\n')
    assert verify_post_release_stability_evidence(evidence,post_verification=post,post_promotion_archive_path=package.path).status is PostReleaseStabilityStatus.BLOCKED


def test_wave72_changed_post_archive_blocks_stability(tmp_path: Path):
    post,package=_post(tmp_path); evidence=_stability(tmp_path,post,package);Path(package.path).write_bytes(Path(package.path).read_bytes()+b'x')
    assert verify_post_release_stability_evidence(evidence,post_verification=post,post_promotion_archive_path=package.path).status is PostReleaseStabilityStatus.BLOCKED


def test_wave72_stability_subject_mismatch_blocks(tmp_path: Path):
    post1,package1=_post(tmp_path/'a',reference='POST-A'); evidence=_stability(tmp_path/'a',post1,package1)
    post2,package2=_post(tmp_path/'b',reference='POST-B')
    assert verify_post_release_stability_evidence(evidence,post_verification=post2,post_promotion_archive_path=package2.path).status is PostReleaseStabilityStatus.BLOCKED


def test_wave72_stability_policy_target_mismatch_blocks(tmp_path: Path):
    post,package=_post(tmp_path); policy=PostReleaseStabilityPolicy(target_version='9.9.9')
    evidence=build_post_release_stability_evidence(post,package.path,requested_status='stable',artifacts=(),observed_framework_version=FRAMEWORK_VERSION,observed_nicegui_version=NICEGUI_VERSION,stability_authority='a',stability_reference='r',policy=policy)
    assert verify_post_release_stability_evidence(evidence,post_verification=post,post_promotion_archive_path=package.path).status is PostReleaseStabilityStatus.BLOCKED


def test_wave72_stability_round_trip_identity(tmp_path: Path):
    post,package=_post(tmp_path); evidence=_stability(tmp_path,post,package); path=write_post_release_stability_evidence(tmp_path/'stability.json',evidence)
    assert read_post_release_stability_evidence(path).stability_id==evidence.stability_id


def test_wave72_stability_tamper_detected(tmp_path: Path):
    post,package=_post(tmp_path); evidence=_stability(tmp_path,post,package);payload=evidence.to_dict();payload['stability_reference']='CHANGED'
    with pytest.raises(ValueError,match='id does not match'):
        post_release_stability_evidence_from_dict(payload)


def test_wave72_stability_manifest_subject_mismatch_rejected(tmp_path: Path):
    post,package=_post(tmp_path); manifest=_stability_manifest(tmp_path,post,package);payload=json.loads(manifest.read_text());payload['post_verification_id']='0'*64;manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='post_verification_id'):
        load_post_release_stability_manifest(manifest,post,package.path)


def test_wave72_stability_manifest_path_escape_rejected(tmp_path: Path):
    post,package=_post(tmp_path); outside=tmp_path.parent/'outside.json';outside.write_text('{}')
    manifest=_stability_manifest(tmp_path,post,package);payload=json.loads(manifest.read_text());payload['artifacts']=[{'key':'x','path':'../outside.json'}];manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='escapes'):
        load_post_release_stability_manifest(manifest,post,package.path)


def test_wave72_rollback_complete_is_ready(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability)
    assert rollback.ready and rollback.status is RollbackReadinessStatus.READY
    assert rollback.to_dict()['rollback_performed_by_framework'] is False


def test_wave72_rollback_missing_artifacts_pending(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability,artifacts=False)
    assert rollback.status is RollbackReadinessStatus.PENDING


def test_wave72_rollback_missing_authority_pending(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability,authority=False)
    assert rollback.status is RollbackReadinessStatus.PENDING


@pytest.mark.parametrize(('requested','expected'), [('pending',RollbackReadinessStatus.PENDING),('blocked',RollbackReadinessStatus.BLOCKED)])
def test_wave72_explicit_rollback_state_propagates(tmp_path: Path, requested: str, expected: RollbackReadinessStatus):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability,status=requested)
    assert rollback.status is expected


def test_wave72_rollback_stability_blocked_propagates(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package,status='blocked'); rollback=_rollback(tmp_path,post,package,stability)
    assert rollback.status is RollbackReadinessStatus.BLOCKED


def test_wave72_rollback_stability_pending_propagates(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package,status='pending'); rollback=_rollback(tmp_path,post,package,stability)
    assert rollback.status is RollbackReadinessStatus.PENDING


def test_wave72_changed_rollback_artifact_blocks(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability);Path(rollback.rollback_artifacts[0].path).write_text('changed\n')
    refreshed=build_stable_rollback_readiness_verification(post,package.path,stability,rollback_artifacts=rollback.rollback_artifacts,requested_status='ready',readiness_authority='approved-change-management',readiness_reference='RB-READY-72')
    assert refreshed.status is RollbackReadinessStatus.BLOCKED


def test_wave72_changed_rollback_execution_artifact_blocks(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability,execution=True);Path(rollback.rollback_execution_artifacts[0].path).write_text('changed\n')
    refreshed=build_stable_rollback_readiness_verification(post,package.path,stability,rollback_artifacts=rollback.rollback_artifacts,rollback_execution_artifacts=rollback.rollback_execution_artifacts,requested_status='ready',readiness_authority='approved-change-management',readiness_reference='RB-READY-72',rollback_execution_reference='RB-EXEC-72')
    assert refreshed.status is RollbackReadinessStatus.BLOCKED


def test_wave72_rollback_policy_target_mismatch_blocks(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); policy=RollbackReadinessPolicy(target_version='9.9.9')
    rollback=build_stable_rollback_readiness_verification(post,package.path,stability,requested_status='ready',readiness_authority='a',readiness_reference='r',policy=policy)
    assert rollback.status is RollbackReadinessStatus.BLOCKED


def test_wave72_rollback_round_trip_identity(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability);path=write_stable_rollback_readiness_verification(tmp_path/'rollback.json',rollback)
    assert read_stable_rollback_readiness_verification(path).readiness_id==rollback.readiness_id


def test_wave72_rollback_tamper_detected(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability);payload=rollback.to_dict();payload['readiness_reference']='changed'
    with pytest.raises(ValueError,match='id does not match'):
        stable_rollback_readiness_verification_from_dict(payload)


def test_wave72_rollback_manifest_subject_mismatch_rejected(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package);manifest=_rollback_manifest(tmp_path,post,stability);payload=json.loads(manifest.read_text());payload['stability_id']='0'*64;manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='stability_id'):
        load_stable_rollback_readiness_manifest(manifest,post,package.path,stability)


def test_wave72_rollback_manifest_path_escape_rejected(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package);outside=tmp_path.parent/'outside-rb.json';outside.write_text('{}');manifest=_rollback_manifest(tmp_path,post,stability);payload=json.loads(manifest.read_text());payload['artifacts']=[{'key':'x','path':'../outside-rb.json'}];manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='escapes'):
        load_stable_rollback_readiness_manifest(manifest,post,package.path,stability)


def test_wave72_rollback_package_deterministic(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability)
    p1=package_stable_rollback_readiness_verification(tmp_path/'rb1.zip',rollback);p2=package_stable_rollback_readiness_verification(tmp_path/'rb2.zip',rollback)
    assert p1.sha256==p2.sha256


def test_wave72_rollback_package_manifest_verifies(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability);p=package_stable_rollback_readiness_verification(tmp_path/'rb.zip',rollback)
    with zipfile.ZipFile(p.path) as z:
        expected={name:sha for sha,name in (line.split('  ',1) for line in z.read('MANIFEST.sha256').decode().splitlines())}
        assert set(expected)==set(z.namelist())-{'MANIFEST.sha256'}
        assert all(hashlib.sha256(z.read(name)).hexdigest()==sha for name,sha in expected.items())


def test_wave72_pending_rollback_can_package_for_gap_handoff(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability,status='pending')
    assert Path(package_stable_rollback_readiness_verification(tmp_path/'pending-rb.zip',rollback).path).is_file()


def test_wave72_blocked_rollback_refuses_packaging(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability,status='blocked')
    with pytest.raises(ValueError,match='BLOCKED'):
        package_stable_rollback_readiness_verification(tmp_path/'blocked-rb.zip',rollback)


def test_wave72_changed_rollback_artifact_refuses_packaging(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability);Path(rollback.rollback_artifacts[0].path).write_text('changed\n')
    with pytest.raises(ValueError,match='BLOCKED'):
        package_stable_rollback_readiness_verification(tmp_path/'bad-rb.zip',rollback)


def test_wave72_external_rollback_execution_evidence_is_packaged_not_executed(tmp_path: Path):
    post,package=_post(tmp_path); stability=_stability(tmp_path,post,package); rollback=_rollback(tmp_path,post,package,stability,execution=True);p=package_stable_rollback_readiness_verification(tmp_path/'rb-exec.zip',rollback)
    assert rollback.to_dict()['rollback_execution_artifacts_are_external_evidence_only'] is True
    with zipfile.ZipFile(p.path) as z: assert any(name.startswith('rollback-execution-evidence/') for name in z.namelist())


def test_wave72_stability_cli_stable_zero(tmp_path: Path,capsys):
    post,package=_post(tmp_path);pp=tmp_path/'post.json';pp.write_text(json.dumps(post.to_dict())) ;manifest=_stability_manifest(tmp_path,post,package);out=tmp_path/'stability.json'
    rc=post_release_stability_intake_main(['nicegui-base post-release-stability-intake',str(pp),package.path,str(manifest),'--output',str(out),'--format','json'])
    assert rc==0 and out.is_file() and json.loads(capsys.readouterr().out)['verification']['status']=='stable'


def test_wave72_stability_cli_pending_two(tmp_path: Path,capsys):
    post,package=_post(tmp_path);pp=tmp_path/'post.json';pp.write_text(json.dumps(post.to_dict()));manifest=_stability_manifest(tmp_path,post,package,status='pending')
    assert post_release_stability_intake_main(['nicegui-base post-release-stability-intake',str(pp),package.path,str(manifest),'--format','json'])==2
    capsys.readouterr()


def test_wave72_stability_cli_blocked_one(tmp_path: Path,capsys):
    post,package=_post(tmp_path);pp=tmp_path/'post.json';pp.write_text(json.dumps(post.to_dict()));manifest=_stability_manifest(tmp_path,post,package,status='blocked')
    assert post_release_stability_intake_main(['nicegui-base post-release-stability-intake',str(pp),package.path,str(manifest),'--format','json'])==1
    capsys.readouterr()


def test_wave72_rollback_cli_ready_zero_and_package(tmp_path: Path,capsys):
    post,package=_post(tmp_path);pp=tmp_path/'post.json';pp.write_text(json.dumps(post.to_dict()));stability=_stability(tmp_path,post,package);sp=write_post_release_stability_evidence(tmp_path/'stability.json',stability);manifest=_rollback_manifest(tmp_path,post,stability);out=tmp_path/'rollback.json';z=tmp_path/'rollback.zip'
    rc=rollback_readiness_verify_main(['nicegui-base rollback-readiness-verify',str(pp),package.path,str(sp),str(manifest),'--output',str(out),'--package',str(z),'--format','json'])
    assert rc==0 and out.is_file() and z.is_file() and json.loads(capsys.readouterr().out)['verification']['status']=='ready'


def test_wave72_rollback_cli_pending_two(tmp_path: Path,capsys):
    post,package=_post(tmp_path);pp=tmp_path/'post.json';pp.write_text(json.dumps(post.to_dict()));stability=_stability(tmp_path,post,package);sp=write_post_release_stability_evidence(tmp_path/'stability.json',stability);manifest=_rollback_manifest(tmp_path,post,stability,status='pending')
    assert rollback_readiness_verify_main(['nicegui-base rollback-readiness-verify',str(pp),package.path,str(sp),str(manifest),'--format','json'])==2
    capsys.readouterr()


def test_wave72_root_public_api_exports_new_contracts():
    import nicegui_base
    for name in ('PostReleaseStabilityEvidence','StableRollbackReadinessVerification','verify_stable_post_promotion_archive','package_stable_rollback_readiness_verification'):
        assert hasattr(nicegui_base,name),name


def test_wave72_main_cli_routes_stability_command(tmp_path: Path,monkeypatch,capsys):
    from nicegui_base.cli import main
    post,package=_post(tmp_path);pp=tmp_path/'post-main.json';pp.write_text(json.dumps(post.to_dict()));manifest=_stability_manifest(tmp_path,post,package);out=tmp_path/'stability-main.json'
    monkeypatch.setattr('sys.argv',['nicegui-base','post-release-stability-intake',str(pp),package.path,str(manifest),'--output',str(out),'--format','json'])
    assert main()==0 and out.is_file();capsys.readouterr()


def test_wave72_main_cli_routes_rollback_command(tmp_path: Path,monkeypatch,capsys):
    from nicegui_base.cli import main
    post,package=_post(tmp_path);pp=tmp_path/'post-main.json';pp.write_text(json.dumps(post.to_dict()));stability=_stability(tmp_path,post,package);sp=write_post_release_stability_evidence(tmp_path/'stability-main.json',stability);manifest=_rollback_manifest(tmp_path,post,stability);out=tmp_path/'rollback-main.json'
    monkeypatch.setattr('sys.argv',['nicegui-base','rollback-readiness-verify',str(pp),package.path,str(sp),str(manifest),'--output',str(out),'--format','json'])
    assert main()==0 and out.is_file();capsys.readouterr()


def test_wave72_generated_semiconductor_starter_includes_stability_helpers(tmp_path: Path):
    from nicegui_base.ai.project import create_application
    app=create_application(tmp_path/'app',name='Wave72 Starter',recipe='spc-monitor')
    source=(app.root/'services/release_evidence.py').read_text()
    assert 'def intake_post_release_stability' in source
    assert 'def verify_rollback_readiness' in source
    assert 'verify_stable_post_promotion_archive' in source
    compile(source,str(app.root/'services/release_evidence.py'),'exec')


def test_wave72_ui_panels_are_public():
    import nicegui_base
    assert hasattr(nicegui_base,'SemiconductorPostReleaseStabilityPanel')
    assert hasattr(nicegui_base,'SemiconductorRollbackReadinessPanel')


def test_wave72_source_evidence_declares_stability_rollback_boundary(tmp_path: Path):
    from nicegui_base.certification.mac_coverage import coverage_summary
    from nicegui_base.governance.source_evidence import _sync_packaged_certification_manifest
    root=Path(__file__).resolve().parents[1]
    source=root/'nicegui_base/certification/certification_manifest.json'
    target=tmp_path/'nicegui_base/certification/certification_manifest.json';target.parent.mkdir(parents=True);target.write_text(source.read_text())
    _sync_packaged_certification_manifest(tmp_path,test_count=1,coverage=coverage_summary())
    payload=json.loads(target.read_text())
    assert payload['phase'] >= 72
    phase72=payload['phase_72_v300a8_enterprise_post_release_stability_rollback_readiness_verification']
    assert phase72['rollback_execution_artifacts_are_external_evidence_only'] is True
    assert phase72['continuous_production_monitoring']=='NOT PERFORMED BY GENERIC FRAMEWORK'
    assert phase72['company_incident_response']=='NOT PERFORMED BY GENERIC FRAMEWORK'
    assert phase72['company_rollback_execution']=='NOT PERFORMED BY GENERIC FRAMEWORK'
