from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import test_phase72_v300a8_post_release_stability_rollback_readiness as w72

from nicegui_base import (
    FRAMEWORK_VERSION, NICEGUI_VERSION,
    INCIDENT_ROLLBACK_AUDIT_POLICIES, INCIDENT_ROLLBACK_AUDIT_POLICY,
    SUSTAINED_OPERATIONS_ACCEPTANCE_POLICIES, SUSTAINED_OPERATIONS_ACCEPTANCE_POLICY,
    SUSTAINED_OPERATIONS_EVIDENCE_ACCEPTANCE_ADAPTERS,
    IncidentRollbackAuditPolicy, IncidentRollbackAuditStatus,
    StableRollbackReadinessArchiveStatus, SustainedOperationsAcceptancePolicy,
    SustainedOperationsAcceptanceStatus,
    build_incident_rollback_audit_closure, build_sustained_operations_evidence_acceptance,
    capture_target_evidence_artifact, incident_rollback_audit_closure_from_dict,
    load_incident_rollback_audit_manifest, load_sustained_operations_evidence_acceptance_manifest,
    package_incident_rollback_audit_closure, package_stable_rollback_readiness_verification,
    read_incident_rollback_audit_closure, read_sustained_operations_evidence_acceptance,
    sustained_operations_evidence_acceptance_from_dict, verify_stable_rollback_readiness_archive,
    verify_sustained_operations_evidence_acceptance, write_incident_rollback_audit_closure,
    write_stable_rollback_readiness_verification, write_sustained_operations_evidence_acceptance,
)
from nicegui_base.certification.semiconductor_operations_cli import (
    incident_rollback_audit_close_main, sustained_operations_accept_main,
)


def _wave72(tmp_path: Path):
    post, post_package = w72._post(tmp_path)
    stability = w72._stability(tmp_path, post, post_package)
    readiness = w72._rollback(tmp_path, post, post_package, stability)
    assert readiness.ready
    package = package_stable_rollback_readiness_verification(tmp_path / 'rollback-readiness.zip', readiness)
    write_stable_rollback_readiness_verification(tmp_path / 'rollback-readiness.json', readiness)
    return readiness, package


def _acceptance_artifacts(tmp_path: Path):
    values=[]
    for key in SUSTAINED_OPERATIONS_ACCEPTANCE_POLICY.required_artifact_keys:
        p=tmp_path/f'{key}.json'; p.write_text(json.dumps({'key':key,'ok':True})+'\n')
        values.append(capture_target_evidence_artifact(p,key=key))
    return tuple(values)


def _acceptance(tmp_path: Path, readiness, package, *, status='accepted', artifacts=True, authority=True, framework=FRAMEWORK_VERSION, nicegui=NICEGUI_VERSION):
    return build_sustained_operations_evidence_acceptance(
        readiness, package.path, requested_status=status,
        artifacts=_acceptance_artifacts(tmp_path) if artifacts else (),
        observed_framework_version=framework, observed_nicegui_version=nicegui,
        acceptance_authority='approved-operations-review' if authority else None,
        acceptance_reference='OPS-73' if authority else None,
    )


def _audit_artifacts(tmp_path: Path):
    values=[]
    for key in INCIDENT_ROLLBACK_AUDIT_POLICY.required_artifact_keys:
        p=tmp_path/f'{key}.json'; p.write_text(json.dumps({'key':key,'closed':True})+'\n')
        values.append(capture_target_evidence_artifact(p,key=key))
    return tuple(values)


def _closure(tmp_path: Path, readiness, package, acceptance, *, status='closed', artifacts=True, authority=True, policy=INCIDENT_ROLLBACK_AUDIT_POLICY):
    return build_incident_rollback_audit_closure(
        readiness, package.path, acceptance, audit_artifacts=_audit_artifacts(tmp_path) if artifacts else (),
        requested_status=status, audit_authority='approved-operations-audit' if authority else None,
        audit_reference='AUDIT-73' if authority else None, policy=policy,
    )


def _rewrite_zip(src: Path, dst: Path, mutate):
    with zipfile.ZipFile(src) as z:
        entries={i.filename:z.read(i.filename) for i in z.infolist()}
    mutate(entries)
    with zipfile.ZipFile(dst,'w') as z:
        for name,blob in entries.items(): z.writestr(name,blob)
    return dst


def _acceptance_manifest(tmp_path: Path, readiness, *, status='accepted', artifacts=True, authority=True, framework=FRAMEWORK_VERSION, nicegui=NICEGUI_VERSION):
    rows=[]
    if artifacts:
        for a in _acceptance_artifacts(tmp_path): rows.append({'key':a.key,'path':Path(a.path).name})
    payload={'schema_version':1,'status':status,'readiness_id':readiness.readiness_id,'stability_id':readiness.stability_evidence.stability_id,
        'target_version':readiness.policy.target_version,'framework_version':framework,'nicegui_version':nicegui,
        'acceptance_authority':'approved-operations-review' if authority else None,'acceptance_reference':'OPS-73' if authority else None,'artifacts':rows}
    p=tmp_path/'sustained-operations-manifest.json';p.write_text(json.dumps(payload,indent=2)+'\n');return p


def _audit_manifest(tmp_path: Path, readiness, acceptance, *, status='closed', artifacts=True, authority=True):
    rows=[]
    if artifacts:
        for a in _audit_artifacts(tmp_path): rows.append({'key':a.key,'path':Path(a.path).name})
    payload={'schema_version':1,'status':status,'readiness_id':readiness.readiness_id,'stability_id':readiness.stability_evidence.stability_id,
        'sustained_operations_acceptance_id':acceptance.acceptance_id,'target_version':readiness.policy.target_version,
        'audit_authority':'approved-operations-audit' if authority else None,'audit_reference':'AUDIT-73' if authority else None,'artifacts':rows}
    p=tmp_path/'incident-rollback-audit-manifest.json';p.write_text(json.dumps(payload,indent=2)+'\n');return p


def test_wave73_registries_are_bounded():
    assert set(SUSTAINED_OPERATIONS_EVIDENCE_ACCEPTANCE_ADAPTERS)=={'json-manifest'}
    assert set(SUSTAINED_OPERATIONS_ACCEPTANCE_POLICIES)=={'stable'}
    assert set(INCIDENT_ROLLBACK_AUDIT_POLICIES)=={'stable'}


def test_wave73_readiness_archive_verifies(tmp_path: Path):
    readiness,package=_wave72(tmp_path)
    report=verify_stable_rollback_readiness_archive(package.path,expected_readiness=readiness)
    assert report.verified and report.status is StableRollbackReadinessArchiveStatus.VERIFIED
    assert report.readiness_id==readiness.readiness_id


def test_wave73_readiness_archive_missing_blocks(tmp_path: Path):
    report=verify_stable_rollback_readiness_archive(tmp_path/'missing.zip')
    assert report.status is StableRollbackReadinessArchiveStatus.BLOCKED


def test_wave73_readiness_archive_wrong_subject_blocks(tmp_path: Path):
    readiness1,package1=_wave72(tmp_path/'a'); readiness2,_=_wave72(tmp_path/'b')
    report=verify_stable_rollback_readiness_archive(package1.path,expected_readiness=readiness2)
    assert any(x.code=='rollback_readiness_archive_identity_mismatch' for x in report.findings)


def test_wave73_readiness_archive_hash_tamper_blocks(tmp_path: Path):
    readiness,package=_wave72(tmp_path)
    bad=_rewrite_zip(Path(package.path),tmp_path/'bad.zip',lambda e:e.__setitem__('post-release-stability-evidence.json',e['post-release-stability-evidence.json']+b'x'))
    assert not verify_stable_rollback_readiness_archive(bad,expected_readiness=readiness).verified


def test_wave73_readiness_archive_manifest_coverage_blocks(tmp_path: Path):
    readiness,package=_wave72(tmp_path)
    def mutate(e): e['extra.json']=b'{}\n'
    bad=_rewrite_zip(Path(package.path),tmp_path/'extra.zip',mutate)
    report=verify_stable_rollback_readiness_archive(bad,expected_readiness=readiness)
    assert any(x.code=='rollback_readiness_archive_manifest_incomplete' for x in report.findings)


def test_wave73_readiness_archive_duplicate_blocks(tmp_path: Path):
    readiness,package=_wave72(tmp_path); dst=tmp_path/'dup.zip'
    with zipfile.ZipFile(package.path) as src, zipfile.ZipFile(dst,'w') as out:
        for i in src.infolist(): out.writestr(i.filename,src.read(i.filename))
        out.writestr('rollback-readiness-verification.json',b'{}')
    assert any(x.code=='rollback_readiness_archive_duplicate_entry' for x in verify_stable_rollback_readiness_archive(dst,expected_readiness=readiness).findings)


def test_wave73_readiness_archive_unsafe_path_blocks(tmp_path: Path):
    readiness,package=_wave72(tmp_path); dst=tmp_path/'unsafe.zip'
    with zipfile.ZipFile(package.path) as src, zipfile.ZipFile(dst,'w') as out:
        for i in src.infolist(): out.writestr(i.filename,src.read(i.filename))
        out.writestr('../escape',b'x')
    assert any(x.code=='rollback_readiness_archive_unsafe_entry' for x in verify_stable_rollback_readiness_archive(dst,expected_readiness=readiness).findings)


def test_wave73_acceptance_complete_is_accepted(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package)
    report=verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path)
    assert report.accepted and report.status is SustainedOperationsAcceptanceStatus.ACCEPTED
    assert acceptance.to_dict()['monitoring_performed_by_framework'] is False


@pytest.mark.parametrize('status,expected',[('pending',SustainedOperationsAcceptanceStatus.PENDING),('blocked',SustainedOperationsAcceptanceStatus.BLOCKED)])
def test_wave73_acceptance_requested_state_propagates(tmp_path: Path,status,expected):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package,status=status)
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path).status is expected


def test_wave73_acceptance_missing_artifacts_pending(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package,artifacts=False)
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path).status is SustainedOperationsAcceptanceStatus.PENDING


def test_wave73_acceptance_missing_authority_pending(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package,authority=False)
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path).status is SustainedOperationsAcceptanceStatus.PENDING


def test_wave73_acceptance_missing_identity_pending(tmp_path: Path):
    readiness,package=_wave72(tmp_path)
    acceptance=_acceptance(tmp_path,readiness,package,framework=None,nicegui=None)
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path).status is SustainedOperationsAcceptanceStatus.PENDING


@pytest.mark.parametrize('framework,nicegui', [('0.0.0',NICEGUI_VERSION),(FRAMEWORK_VERSION,'3.14.0')])
def test_wave73_acceptance_identity_mismatch_blocks(tmp_path: Path,framework,nicegui):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package,framework=framework,nicegui=nicegui)
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path).status is SustainedOperationsAcceptanceStatus.BLOCKED


def test_wave73_changed_acceptance_artifact_blocks(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package);Path(acceptance.artifacts[0].path).write_text('changed\n')
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path).status is SustainedOperationsAcceptanceStatus.BLOCKED


def test_wave73_changed_readiness_archive_blocks_acceptance(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package);Path(package.path).write_bytes(Path(package.path).read_bytes()+b'x')
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path).status is SustainedOperationsAcceptanceStatus.BLOCKED


def test_wave73_acceptance_subject_mismatch_blocks(tmp_path: Path):
    readiness1,package1=_wave72(tmp_path/'a'); acceptance=_acceptance(tmp_path/'a',readiness1,package1)
    readiness2,package2=_wave72(tmp_path/'b')
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness2,package2.path).status is SustainedOperationsAcceptanceStatus.BLOCKED


def test_wave73_acceptance_policy_target_mismatch_blocks(tmp_path: Path):
    readiness,package=_wave72(tmp_path); policy=SustainedOperationsAcceptancePolicy(target_version='9.9.9')
    acceptance=build_sustained_operations_evidence_acceptance(readiness,package.path,requested_status='accepted',artifacts=_acceptance_artifacts(tmp_path),observed_framework_version=FRAMEWORK_VERSION,observed_nicegui_version=NICEGUI_VERSION,acceptance_authority='a',acceptance_reference='r',policy=policy)
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path).status is SustainedOperationsAcceptanceStatus.BLOCKED


def test_wave73_acceptance_round_trip(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package)
    p=write_sustained_operations_evidence_acceptance(tmp_path/'acceptance.json',acceptance)
    assert read_sustained_operations_evidence_acceptance(p).acceptance_id==acceptance.acceptance_id


def test_wave73_acceptance_tamper_detected(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package);payload=acceptance.to_dict();payload['acceptance_reference']='changed'
    with pytest.raises(ValueError,match='id does not match'): sustained_operations_evidence_acceptance_from_dict(payload)


def test_wave73_acceptance_manifest_loads(tmp_path: Path):
    readiness,package=_wave72(tmp_path); manifest=_acceptance_manifest(tmp_path,readiness)
    acceptance=load_sustained_operations_evidence_acceptance_manifest(manifest,readiness,package.path)
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path).accepted


def test_wave73_acceptance_manifest_subject_mismatch_rejected(tmp_path: Path):
    readiness,package=_wave72(tmp_path); manifest=_acceptance_manifest(tmp_path,readiness);payload=json.loads(manifest.read_text());payload['readiness_id']='0'*64;manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='readiness_id'): load_sustained_operations_evidence_acceptance_manifest(manifest,readiness,package.path)


def test_wave73_acceptance_manifest_path_escape_rejected(tmp_path: Path):
    readiness,package=_wave72(tmp_path); outside=tmp_path.parent/'outside.json';outside.write_text('{}')
    manifest=_acceptance_manifest(tmp_path,readiness);payload=json.loads(manifest.read_text());payload['artifacts']=[{'key':'x','path':'../outside.json'}];manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='escapes'): load_sustained_operations_evidence_acceptance_manifest(manifest,readiness,package.path)


def test_wave73_acceptance_manifest_expected_hash_mismatch_blocks(tmp_path: Path):
    readiness,package=_wave72(tmp_path); manifest=_acceptance_manifest(tmp_path,readiness);payload=json.loads(manifest.read_text());payload['artifacts'][0]['sha256']='0'*64;manifest.write_text(json.dumps(payload))
    acceptance=load_sustained_operations_evidence_acceptance_manifest(manifest,readiness,package.path)
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path).status is SustainedOperationsAcceptanceStatus.BLOCKED


def test_wave73_acceptance_manifest_missing_file_stays_pending(tmp_path: Path):
    readiness,package=_wave72(tmp_path); manifest=_acceptance_manifest(tmp_path,readiness);payload=json.loads(manifest.read_text());payload['artifacts'].append({'key':'extra','path':'missing.json'});manifest.write_text(json.dumps(payload))
    acceptance=load_sustained_operations_evidence_acceptance_manifest(manifest,readiness,package.path)
    assert verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path).status is SustainedOperationsAcceptanceStatus.PENDING


def test_wave73_audit_complete_closes(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package); closure=_closure(tmp_path,readiness,package,acceptance)
    assert closure.closed and closure.status is IncidentRollbackAuditStatus.CLOSED
    data=closure.to_dict(); assert data['rollback_performed_by_framework'] is False and data['audit_closure_is_not_operational_execution'] is True


@pytest.mark.parametrize('status,expected',[('pending',IncidentRollbackAuditStatus.PENDING),('blocked',IncidentRollbackAuditStatus.BLOCKED)])
def test_wave73_audit_requested_state_propagates(tmp_path: Path,status,expected):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package); closure=_closure(tmp_path,readiness,package,acceptance,status=status)
    assert closure.status is expected


def test_wave73_audit_missing_artifacts_pending(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package); closure=_closure(tmp_path,readiness,package,acceptance,artifacts=False)
    assert closure.status is IncidentRollbackAuditStatus.PENDING


def test_wave73_audit_missing_authority_pending(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package); closure=_closure(tmp_path,readiness,package,acceptance,authority=False)
    assert closure.status is IncidentRollbackAuditStatus.PENDING


def test_wave73_audit_pending_acceptance_stays_pending(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package,status='pending'); closure=_closure(tmp_path,readiness,package,acceptance)
    assert closure.status is IncidentRollbackAuditStatus.PENDING


def test_wave73_audit_blocked_acceptance_blocks(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package,status='blocked'); closure=_closure(tmp_path,readiness,package,acceptance)
    assert closure.status is IncidentRollbackAuditStatus.BLOCKED


def test_wave73_changed_audit_artifact_blocks_rebuild(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package); closure=_closure(tmp_path,readiness,package,acceptance);Path(closure.audit_artifacts[0].path).write_text('changed\n')
    rebuilt=build_incident_rollback_audit_closure(readiness,package.path,acceptance,audit_artifacts=closure.audit_artifacts,requested_status='closed',audit_authority='approved-operations-audit',audit_reference='AUDIT-73')
    assert rebuilt.status is IncidentRollbackAuditStatus.BLOCKED


def test_wave73_audit_policy_target_mismatch_blocks(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package);policy=IncidentRollbackAuditPolicy(target_version='9.9.9')
    closure=_closure(tmp_path,readiness,package,acceptance,policy=policy)
    assert closure.status is IncidentRollbackAuditStatus.BLOCKED


def test_wave73_audit_round_trip(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package);closure=_closure(tmp_path,readiness,package,acceptance)
    p=write_incident_rollback_audit_closure(tmp_path/'audit.json',closure); assert read_incident_rollback_audit_closure(p).audit_id==closure.audit_id


def test_wave73_audit_tamper_detected(tmp_path: Path):
    readiness,package=_wave72(tmp_path); acceptance=_acceptance(tmp_path,readiness,package);closure=_closure(tmp_path,readiness,package,acceptance);payload=closure.to_dict();payload['audit_reference']='changed'
    with pytest.raises(ValueError,match='id does not match'): incident_rollback_audit_closure_from_dict(payload)


def test_wave73_audit_manifest_loads_closed(tmp_path: Path):
    readiness,package=_wave72(tmp_path);acceptance=_acceptance(tmp_path,readiness,package);manifest=_audit_manifest(tmp_path,readiness,acceptance)
    closure=load_incident_rollback_audit_manifest(manifest,readiness,package.path,acceptance)
    assert closure.closed


def test_wave73_audit_manifest_subject_mismatch_rejected(tmp_path: Path):
    readiness,package=_wave72(tmp_path);acceptance=_acceptance(tmp_path,readiness,package);manifest=_audit_manifest(tmp_path,readiness,acceptance);payload=json.loads(manifest.read_text());payload['sustained_operations_acceptance_id']='0'*64;manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='sustained_operations_acceptance_id'): load_incident_rollback_audit_manifest(manifest,readiness,package.path,acceptance)


def test_wave73_audit_manifest_path_escape_rejected(tmp_path: Path):
    readiness,package=_wave72(tmp_path);acceptance=_acceptance(tmp_path,readiness,package);outside=tmp_path.parent/'outside.json';outside.write_text('{}');manifest=_audit_manifest(tmp_path,readiness,acceptance);payload=json.loads(manifest.read_text());payload['artifacts']=[{'key':'x','path':'../outside.json'}];manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='escapes'): load_incident_rollback_audit_manifest(manifest,readiness,package.path,acceptance)


def test_wave73_audit_manifest_expected_hash_mismatch_blocks(tmp_path: Path):
    readiness,package=_wave72(tmp_path);acceptance=_acceptance(tmp_path,readiness,package);manifest=_audit_manifest(tmp_path,readiness,acceptance);payload=json.loads(manifest.read_text());payload['artifacts'][0]['sha256']='0'*64;manifest.write_text(json.dumps(payload))
    assert load_incident_rollback_audit_manifest(manifest,readiness,package.path,acceptance).status is IncidentRollbackAuditStatus.BLOCKED


def test_wave73_audit_manifest_missing_file_stays_pending_and_packages(tmp_path: Path):
    readiness,package=_wave72(tmp_path);acceptance=_acceptance(tmp_path,readiness,package);manifest=_audit_manifest(tmp_path,readiness,acceptance);payload=json.loads(manifest.read_text());payload['artifacts'].append({'key':'extra','path':'missing.json'});manifest.write_text(json.dumps(payload))
    closure=load_incident_rollback_audit_manifest(manifest,readiness,package.path,acceptance); assert closure.status is IncidentRollbackAuditStatus.PENDING
    pkg=package_incident_rollback_audit_closure(tmp_path/'gap.zip',closure); assert pkg.status is IncidentRollbackAuditStatus.PENDING


def test_wave73_audit_package_is_deterministic(tmp_path: Path):
    readiness,package=_wave72(tmp_path);acceptance=_acceptance(tmp_path,readiness,package);closure=_closure(tmp_path,readiness,package,acceptance)
    p1=package_incident_rollback_audit_closure(tmp_path/'a.zip',closure);p2=package_incident_rollback_audit_closure(tmp_path/'b.zip',closure)
    assert p1.sha256==p2.sha256 and Path(p1.path).read_bytes()==Path(p2.path).read_bytes()


def test_wave73_audit_package_is_self_contained(tmp_path: Path):
    readiness,package=_wave72(tmp_path);acceptance=_acceptance(tmp_path,readiness,package);closure=_closure(tmp_path,readiness,package,acceptance);pkg=package_incident_rollback_audit_closure(tmp_path/'audit.zip',closure)
    with zipfile.ZipFile(pkg.path) as z:
        names=set(z.namelist()); assert {'incident-rollback-audit-closure.json','sustained-operations-acceptance.json','wave72/rollback-readiness.zip','MANIFEST.sha256'}<=names


def test_wave73_changed_evidence_refuses_package(tmp_path: Path):
    readiness,package=_wave72(tmp_path);acceptance=_acceptance(tmp_path,readiness,package);closure=_closure(tmp_path,readiness,package,acceptance);Path(acceptance.artifacts[0].path).write_text('changed\n')
    with pytest.raises(ValueError): package_incident_rollback_audit_closure(tmp_path/'bad.zip',closure)


def test_wave73_blocked_closure_refuses_package(tmp_path: Path):
    readiness,package=_wave72(tmp_path);acceptance=_acceptance(tmp_path,readiness,package,status='blocked');closure=_closure(tmp_path,readiness,package,acceptance)
    with pytest.raises(ValueError,match='BLOCKED'): package_incident_rollback_audit_closure(tmp_path/'bad.zip',closure)


def test_wave73_acceptance_cli_pending_without_real_evidence(tmp_path: Path,capsys):
    readiness,package=_wave72(tmp_path);manifest=_acceptance_manifest(tmp_path,readiness,status='accepted',artifacts=False)
    rc=sustained_operations_accept_main([str(tmp_path/'rollback-readiness.json'),package.path,str(manifest),'--format','json'])
    assert rc==0 and json.loads(capsys.readouterr().out)['status']=='pending'


def test_wave73_acceptance_cli_writes_record(tmp_path: Path,capsys):
    readiness,package=_wave72(tmp_path);manifest=_acceptance_manifest(tmp_path,readiness);out=tmp_path/'acceptance.json'
    rc=sustained_operations_accept_main([str(tmp_path/'rollback-readiness.json'),package.path,str(manifest),'--output',str(out),'--format','json'])
    assert rc==0 and out.is_file() and json.loads(capsys.readouterr().out)['status']=='accepted'


def test_wave73_audit_cli_writes_package(tmp_path: Path,capsys):
    readiness,package=_wave72(tmp_path);acceptance=_acceptance(tmp_path,readiness,package);ap=write_sustained_operations_evidence_acceptance(tmp_path/'acceptance.json',acceptance);manifest=_audit_manifest(tmp_path,readiness,acceptance);out=tmp_path/'audit.json';pkg=tmp_path/'audit.zip'
    rc=incident_rollback_audit_close_main([str(tmp_path/'rollback-readiness.json'),package.path,str(ap),str(manifest),'--output',str(out),'--package',str(pkg),'--format','json'])
    payload=json.loads(capsys.readouterr().out); assert rc==0 and payload['status']=='closed' and out.is_file() and pkg.is_file()


def test_wave73_top_level_cli_routes_commands():
    root=Path(__file__).resolve().parents[1]
    for command in ('sustained-operations-accept','incident-rollback-audit-close'):
        result=subprocess.run([sys.executable,'-m','nicegui_base.cli',command,'--help'],cwd=root,text=True,capture_output=True)
        assert result.returncode==0 and command in result.stdout


def test_wave73_acceptance_does_not_mutate_readiness(tmp_path: Path):
    readiness,package=_wave72(tmp_path);before=readiness.to_dict();acceptance=_acceptance(tmp_path,readiness,package);verify_sustained_operations_evidence_acceptance(acceptance,readiness,package.path)
    assert readiness.to_dict()==before


def test_wave73_audit_closure_does_not_mutate_upstream_truth(tmp_path: Path):
    readiness,package=_wave72(tmp_path);before=readiness.to_dict();acceptance=_acceptance(tmp_path,readiness,package);closure=_closure(tmp_path,readiness,package,acceptance)
    assert closure.closed and readiness.to_dict()==before and closure.to_dict()['affects_wave66_to_wave72_truth'] is False


def test_wave73_policy_validation_rejects_empty_keys():
    with pytest.raises(ValueError): SustainedOperationsAcceptancePolicy(required_artifact_keys=())
    with pytest.raises(ValueError): IncidentRollbackAuditPolicy(required_artifact_keys=())


def test_wave73_archive_sha_is_actual_file_hash(tmp_path: Path):
    readiness,package=_wave72(tmp_path);report=verify_stable_rollback_readiness_archive(package.path,expected_readiness=readiness)
    assert report.sha256==hashlib.sha256(Path(package.path).read_bytes()).hexdigest()


def test_wave73_generated_semiconductor_starter_includes_operations_helpers(tmp_path: Path):
    from nicegui_base.ai.project import create_application
    app=create_application(tmp_path/'app',name='Wave73 Starter',recipe='spc-monitor')
    source=(app.root/'services/release_evidence.py').read_text()
    assert 'def accept_sustained_operations' in source
    assert 'def close_incident_rollback_audit' in source
    assert 'verify_stable_rollback_readiness_archive' in source
    compile(source,str(app.root/'services/release_evidence.py'),'exec')


def test_wave73_ui_panels_are_public():
    import nicegui_base
    assert hasattr(nicegui_base,'SemiconductorSustainedOperationsAcceptancePanel')
    assert hasattr(nicegui_base,'SemiconductorIncidentRollbackAuditClosurePanel')


def test_wave73_source_evidence_declares_operations_boundary(tmp_path: Path):
    from nicegui_base.certification.mac_coverage import coverage_summary
    from nicegui_base.governance.source_evidence import _sync_packaged_certification_manifest
    root=Path(__file__).resolve().parents[1]
    source=root/'nicegui_base/certification/certification_manifest.json'
    target=tmp_path/'nicegui_base/certification/certification_manifest.json';target.parent.mkdir(parents=True);target.write_text(source.read_text())
    _sync_packaged_certification_manifest(tmp_path,test_count=1,coverage=coverage_summary())
    payload=json.loads(target.read_text())
    assert payload['phase'] >= 73
    phase=payload['phase_73_v300a8_enterprise_sustained_operations_incident_rollback_audit_closure']
    assert phase['incident_rollback_audit_closure_is_documentary_evidence_only'] is True
    assert phase['company_incident_response']=='NOT PERFORMED BY GENERIC FRAMEWORK'
    assert phase['company_rollback_execution']=='NOT PERFORMED BY GENERIC FRAMEWORK'


def test_wave73_main_cli_routes_acceptance_command(tmp_path: Path,monkeypatch,capsys):
    from nicegui_base.cli import main
    readiness,package=_wave72(tmp_path);manifest=_acceptance_manifest(tmp_path,readiness);out=tmp_path/'acceptance-main.json'
    monkeypatch.setattr('sys.argv',['nicegui-base','sustained-operations-accept',str(tmp_path/'rollback-readiness.json'),package.path,str(manifest),'--output',str(out),'--format','json'])
    assert main()==0 and out.is_file();capsys.readouterr()


def test_wave73_main_cli_routes_audit_command(tmp_path: Path,monkeypatch,capsys):
    from nicegui_base.cli import main
    readiness,package=_wave72(tmp_path);acceptance=_acceptance(tmp_path,readiness,package);ap=write_sustained_operations_evidence_acceptance(tmp_path/'acceptance-main.json',acceptance);manifest=_audit_manifest(tmp_path,readiness,acceptance);out=tmp_path/'audit-main.json';pkg=tmp_path/'audit-main.zip'
    monkeypatch.setattr('sys.argv',['nicegui-base','incident-rollback-audit-close',str(tmp_path/'rollback-readiness.json'),package.path,str(ap),str(manifest),'--output',str(out),'--package',str(pkg),'--format','json'])
    assert main()==0 and out.is_file() and pkg.is_file();capsys.readouterr()
