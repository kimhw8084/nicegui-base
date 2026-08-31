from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import test_phase73_v300a8_sustained_operations_incident_rollback_audit as w73

import nicegui_base
from nicegui_base import (
    FRAMEWORK_VERSION, NICEGUI_VERSION,
    OPERATIONAL_ASSURANCE_CONTINUITY_POLICIES, OPERATIONAL_ASSURANCE_CONTINUITY_POLICY,
    SUSTAINED_OPERATIONS_EVIDENCE_RENEWAL_ADAPTERS, SUSTAINED_OPERATIONS_RENEWAL_POLICIES,
    SUSTAINED_OPERATIONS_RENEWAL_POLICY, IncidentRollbackAuditArchiveStatus,
    OperationalAssuranceContinuityPolicy, OperationalAssuranceContinuityStatus, OperationsEvidenceFreshness,
    SustainedOperationsRenewalPolicy, SustainedOperationsRenewalStatus,
    assess_sustained_operations_evidence_freshness, build_operational_assurance_continuity_dossier,
    build_sustained_operations_evidence_renewal, capture_target_evidence_artifact,
    load_sustained_operations_evidence_renewal_manifest, operational_assurance_continuity_dossier_from_dict,
    package_incident_rollback_audit_closure, package_operational_assurance_continuity_dossier,
    read_operational_assurance_continuity_dossier, read_sustained_operations_evidence_renewal,
    sustained_operations_evidence_renewal_from_dict, verify_incident_rollback_audit_archive,
    verify_sustained_operations_evidence_renewal, write_incident_rollback_audit_closure,
    write_operational_assurance_continuity_dossier, write_sustained_operations_evidence_renewal,
)
from nicegui_base.certification.semiconductor_continuity_cli import operational_assurance_continuity_main, operations_evidence_renew_main

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
NOW_ISO = '2026-08-30T12:00:00Z'


def _wave73(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    readiness, readiness_package = w73._wave72(tmp_path)
    acceptance = w73._acceptance(tmp_path, readiness, readiness_package)
    closure = w73._closure(tmp_path, readiness, readiness_package, acceptance)
    assert closure.closed
    package = package_incident_rollback_audit_closure(tmp_path / 'wave73-audit.zip', closure)
    write_incident_rollback_audit_closure(tmp_path / 'wave73-audit.json', closure)
    return closure, package


def _renewal_artifacts(tmp_path: Path):
    values=[]
    for key in SUSTAINED_OPERATIONS_RENEWAL_POLICY.required_artifact_keys:
        p=tmp_path/f'{key}.json'; p.write_text(json.dumps({'key':key,'renewed':True})+'\n')
        values.append(capture_target_evidence_artifact(p,key=key))
    return tuple(values)


def _renewal(tmp_path: Path, closure, package, *, status='renewed', captured=NOW_ISO, artifacts=True, authority=True, framework=FRAMEWORK_VERSION, nicegui=NICEGUI_VERSION, policy=SUSTAINED_OPERATIONS_RENEWAL_POLICY):
    return build_sustained_operations_evidence_renewal(
        closure, package.path, requested_status=status, evidence_captured_at=captured,
        artifacts=_renewal_artifacts(tmp_path) if artifacts else (), observed_framework_version=framework,
        observed_nicegui_version=nicegui, renewal_authority='approved-operations-renewal' if authority else None,
        renewal_reference='RENEW-74' if authority else None, policy=policy,
    )


def _renewal_manifest(tmp_path: Path, closure, *, status='renewed', captured=NOW_ISO, artifacts=True, authority=True, framework=FRAMEWORK_VERSION, nicegui=NICEGUI_VERSION):
    rows=[]
    if artifacts:
        for a in _renewal_artifacts(tmp_path): rows.append({'key':a.key,'path':Path(a.path).name})
    payload={'schema_version':1,'status':status,'audit_id':closure.audit_id,'acceptance_id':closure.sustained_operations_acceptance.acceptance_id,
        'target_version':closure.policy.target_version,'evidence_captured_at':captured,'observed_framework_version':framework,
        'observed_nicegui_version':nicegui,'renewal_authority':'approved-operations-renewal' if authority else None,
        'renewal_reference':'RENEW-74' if authority else None,'artifacts':rows}
    p=tmp_path/'renewal-manifest.json'; p.write_text(json.dumps(payload,indent=2)+'\n'); return p


def _rewrite_zip(src: Path, dst: Path, mutate):
    with zipfile.ZipFile(src) as z: entries={i.filename:z.read(i.filename) for i in z.infolist()}
    mutate(entries)
    with zipfile.ZipFile(dst,'w') as z:
        for name,blob in entries.items(): z.writestr(name,blob)
    return dst


def test_wave74_registries_are_bounded():
    assert set(SUSTAINED_OPERATIONS_EVIDENCE_RENEWAL_ADAPTERS)=={'json-manifest'}
    assert set(SUSTAINED_OPERATIONS_RENEWAL_POLICIES)=={'stable'}
    assert set(OPERATIONAL_ASSURANCE_CONTINUITY_POLICIES)=={'stable'}


def test_wave74_default_policy_is_configurable_not_company_claim():
    p=SUSTAINED_OPERATIONS_RENEWAL_POLICY
    assert p.max_age_hours==168 and p.expiring_within_hours==24 and p.max_future_skew_minutes==5
    assert p.target_version=='3.0.0'


@pytest.mark.parametrize(('offset','expected'),[(0,OperationsEvidenceFreshness.CURRENT),(145,OperationsEvidenceFreshness.EXPIRING),(169,OperationsEvidenceFreshness.EXPIRED)])
def test_wave74_freshness_windows(offset,expected):
    captured=(NOW-timedelta(hours=offset)).isoformat().replace('+00:00','Z')
    assert assess_sustained_operations_evidence_freshness(captured,now=NOW).status is expected


def test_wave74_freshness_missing():
    assert assess_sustained_operations_evidence_freshness(None,now=NOW).status is OperationsEvidenceFreshness.MISSING


def test_wave74_freshness_invalid_is_contradictory():
    assert assess_sustained_operations_evidence_freshness('not-a-time',now=NOW).status is OperationsEvidenceFreshness.CONTRADICTORY


def test_wave74_freshness_future_is_contradictory():
    captured=(NOW+timedelta(minutes=6)).isoformat().replace('+00:00','Z')
    assert assess_sustained_operations_evidence_freshness(captured,now=NOW).status is OperationsEvidenceFreshness.CONTRADICTORY


def test_wave74_expiring_threshold_validation():
    with pytest.raises(ValueError): SustainedOperationsRenewalPolicy(max_age_hours=24,expiring_within_hours=25)


def test_wave74_archive_verifies(tmp_path: Path):
    closure,package=_wave73(tmp_path)
    report=verify_incident_rollback_audit_archive(package.path,expected_closure=closure)
    assert report.verified and report.status is IncidentRollbackAuditArchiveStatus.VERIFIED
    assert report.audit_id==closure.audit_id


def test_wave74_archive_missing_blocks(tmp_path: Path):
    assert verify_incident_rollback_audit_archive(tmp_path/'missing.zip').status is IncidentRollbackAuditArchiveStatus.BLOCKED


def test_wave74_archive_wrong_subject_blocks(tmp_path: Path):
    closure1,package1=_wave73(tmp_path/'a'); closure2,_=_wave73(tmp_path/'b')
    report=verify_incident_rollback_audit_archive(package1.path,expected_closure=closure2)
    assert any(x.code=='incident_rollback_audit_archive_subject_mismatch' for x in report.findings)


def test_wave74_archive_hash_tamper_blocks(tmp_path: Path):
    closure,package=_wave73(tmp_path)
    bad=_rewrite_zip(Path(package.path),tmp_path/'bad.zip',lambda e:e.__setitem__('sustained-operations-acceptance.json',e['sustained-operations-acceptance.json']+b'x'))
    assert not verify_incident_rollback_audit_archive(bad,expected_closure=closure).verified


def test_wave74_archive_manifest_coverage_blocks(tmp_path: Path):
    closure,package=_wave73(tmp_path)
    bad=_rewrite_zip(Path(package.path),tmp_path/'extra.zip',lambda e:e.__setitem__('extra.json',b'{}\n'))
    assert any(x.code=='incident_rollback_audit_archive_manifest_incomplete' for x in verify_incident_rollback_audit_archive(bad,expected_closure=closure).findings)


def test_wave74_archive_duplicate_blocks(tmp_path: Path):
    closure,package=_wave73(tmp_path); dst=tmp_path/'dup.zip'
    with zipfile.ZipFile(package.path) as src, zipfile.ZipFile(dst,'w') as out:
        for i in src.infolist(): out.writestr(i.filename,src.read(i.filename))
        out.writestr('incident-rollback-audit-closure.json',src.read('incident-rollback-audit-closure.json'))
    assert any(x.code=='incident_rollback_audit_archive_duplicate_entry' for x in verify_incident_rollback_audit_archive(dst,expected_closure=closure).findings)


def test_wave74_archive_unsafe_path_blocks(tmp_path: Path):
    closure,package=_wave73(tmp_path)
    bad=_rewrite_zip(Path(package.path),tmp_path/'unsafe.zip',lambda e:e.__setitem__('../escape',b'x'))
    assert any(x.code=='incident_rollback_audit_archive_unsafe_entry' for x in verify_incident_rollback_audit_archive(bad,expected_closure=closure).findings)


def test_wave74_archive_nested_wave72_hash_blocks(tmp_path: Path):
    closure,package=_wave73(tmp_path)
    def mutate(e):
        e['wave72/rollback-readiness.zip']+=b'x'
        lines=[]
        for name,blob in e.items():
            if name!='MANIFEST.sha256':
                import hashlib; lines.append(f'{hashlib.sha256(blob).hexdigest()}  {name}\n')
        e['MANIFEST.sha256']=''.join(sorted(lines)).encode()
    bad=_rewrite_zip(Path(package.path),tmp_path/'nested.zip',mutate)
    assert any(x.code=='incident_rollback_audit_archive_wave72_hash_mismatch' for x in verify_incident_rollback_audit_archive(bad,expected_closure=closure).findings)


def test_wave74_build_and_verify_renewed(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package)
    report=verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW)
    assert report.renewed and report.freshness.status is OperationsEvidenceFreshness.CURRENT


@pytest.mark.parametrize(('status','expected'),[('pending',SustainedOperationsRenewalStatus.PENDING),('blocked',SustainedOperationsRenewalStatus.BLOCKED)])
def test_wave74_requested_status_propagates(tmp_path: Path,status,expected):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package,status=status)
    assert verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW).status is expected


def test_wave74_renewed_without_artifacts_stays_pending(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package,artifacts=False)
    assert verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW).status is SustainedOperationsRenewalStatus.PENDING


def test_wave74_renewed_without_authority_stays_pending(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package,authority=False)
    assert verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW).status is SustainedOperationsRenewalStatus.PENDING


def test_wave74_renewed_without_timestamp_stays_pending(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package,captured=None)
    report=verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW)
    assert report.status is SustainedOperationsRenewalStatus.PENDING and report.freshness.status is OperationsEvidenceFreshness.MISSING


def test_wave74_expired_renewal_stays_pending(tmp_path: Path):
    closure,package=_wave73(tmp_path); captured=(NOW-timedelta(hours=200)).isoformat().replace('+00:00','Z'); renewal=_renewal(tmp_path,closure,package,captured=captured)
    report=verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW)
    assert report.status is SustainedOperationsRenewalStatus.PENDING and report.freshness.status is OperationsEvidenceFreshness.EXPIRED


def test_wave74_expiring_renewal_remains_renewed(tmp_path: Path):
    closure,package=_wave73(tmp_path); captured=(NOW-timedelta(hours=150)).isoformat().replace('+00:00','Z'); renewal=_renewal(tmp_path,closure,package,captured=captured)
    report=verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW)
    assert report.status is SustainedOperationsRenewalStatus.RENEWED and report.freshness.status is OperationsEvidenceFreshness.EXPIRING


def test_wave74_future_timestamp_blocks(tmp_path: Path):
    closure,package=_wave73(tmp_path); captured=(NOW+timedelta(hours=1)).isoformat().replace('+00:00','Z'); renewal=_renewal(tmp_path,closure,package,captured=captured)
    assert verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW).status is SustainedOperationsRenewalStatus.BLOCKED


@pytest.mark.parametrize('field,value',[('framework','0.0.0'),('nicegui','0.0.0')])
def test_wave74_identity_mismatch_blocks(tmp_path: Path,field,value):
    closure,package=_wave73(tmp_path); kwargs={field:value}; renewal=_renewal(tmp_path,closure,package,**kwargs)
    assert verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW).status is SustainedOperationsRenewalStatus.BLOCKED


def test_wave74_changed_artifact_blocks(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package); Path(renewal.artifacts[0].path).write_text('changed')
    assert verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW).status is SustainedOperationsRenewalStatus.BLOCKED


def test_wave74_changed_audit_archive_blocks(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package); Path(package.path).write_bytes(Path(package.path).read_bytes()+b'x')
    assert verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW).status is SustainedOperationsRenewalStatus.BLOCKED


def test_wave74_renewal_roundtrip(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package); p=write_sustained_operations_evidence_renewal(tmp_path/'renewal.json',renewal)
    assert read_sustained_operations_evidence_renewal(p).renewal_id==renewal.renewal_id


def test_wave74_renewal_tamper_rejected(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package); payload=renewal.to_dict();payload['renewal_reference']='changed'
    with pytest.raises(ValueError,match='id does not match'): sustained_operations_evidence_renewal_from_dict(payload)


def test_wave74_manifest_loads_and_verifies(tmp_path: Path):
    closure,package=_wave73(tmp_path); manifest=_renewal_manifest(tmp_path,closure); renewal=load_sustained_operations_evidence_renewal_manifest(manifest,closure,package.path)
    assert verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW).renewed


def test_wave74_manifest_subject_mismatch_rejected(tmp_path: Path):
    closure,package=_wave73(tmp_path); manifest=_renewal_manifest(tmp_path,closure); payload=json.loads(manifest.read_text());payload['audit_id']='0'*64;manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='audit_id'): load_sustained_operations_evidence_renewal_manifest(manifest,closure,package.path)


def test_wave74_manifest_escape_rejected(tmp_path: Path):
    closure,package=_wave73(tmp_path); manifest=_renewal_manifest(tmp_path,closure);payload=json.loads(manifest.read_text());payload['artifacts'][0]['path']='../escape';manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='escapes'): load_sustained_operations_evidence_renewal_manifest(manifest,closure,package.path)


def test_wave74_manifest_expected_hash_mismatch_blocks(tmp_path: Path):
    closure,package=_wave73(tmp_path); manifest=_renewal_manifest(tmp_path,closure);payload=json.loads(manifest.read_text());payload['artifacts'][0]['sha256']='0'*64;manifest.write_text(json.dumps(payload))
    renewal=load_sustained_operations_evidence_renewal_manifest(manifest,closure,package.path)
    assert verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW).status is SustainedOperationsRenewalStatus.BLOCKED


def test_wave74_manifest_missing_requested_file_pending(tmp_path: Path):
    closure,package=_wave73(tmp_path); manifest=_renewal_manifest(tmp_path,closure);payload=json.loads(manifest.read_text());payload['artifacts'][0]['path']='missing.json';manifest.write_text(json.dumps(payload))
    renewal=load_sustained_operations_evidence_renewal_manifest(manifest,closure,package.path)
    assert verify_sustained_operations_evidence_renewal(renewal,closure,package.path,now=NOW).status is SustainedOperationsRenewalStatus.PENDING


def test_wave74_continuity_assured(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package); dossier=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW)
    assert dossier.status is OperationalAssuranceContinuityStatus.ASSURED


def test_wave74_continuity_expiring(tmp_path: Path):
    closure,package=_wave73(tmp_path); captured=(NOW-timedelta(hours=150)).isoformat().replace('+00:00','Z'); renewal=_renewal(tmp_path,closure,package,captured=captured); dossier=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW)
    assert dossier.status is OperationalAssuranceContinuityStatus.EXPIRING


def test_wave74_continuity_expired_pending(tmp_path: Path):
    closure,package=_wave73(tmp_path); captured=(NOW-timedelta(hours=200)).isoformat().replace('+00:00','Z'); renewal=_renewal(tmp_path,closure,package,captured=captured); dossier=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW)
    assert dossier.status is OperationalAssuranceContinuityStatus.PENDING


def test_wave74_continuity_contradictory_blocked(tmp_path: Path):
    closure,package=_wave73(tmp_path); captured=(NOW+timedelta(hours=2)).isoformat().replace('+00:00','Z'); renewal=_renewal(tmp_path,closure,package,captured=captured); dossier=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW)
    assert dossier.status is OperationalAssuranceContinuityStatus.BLOCKED


def test_wave74_continuity_policy_target_mismatch_blocks(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package); policy=OperationalAssuranceContinuityPolicy(target_version='9.9.9')
    assert build_operational_assurance_continuity_dossier(closure,package.path,renewal,policy=policy,now=NOW).status is OperationalAssuranceContinuityStatus.BLOCKED


def test_wave74_continuity_roundtrip_and_tamper(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package); dossier=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW)
    p=write_operational_assurance_continuity_dossier(tmp_path/'continuity.json',dossier); assert read_operational_assurance_continuity_dossier(p).continuity_id==dossier.continuity_id
    payload=dossier.to_dict();payload['metadata']={'tampered':True}
    with pytest.raises(ValueError,match='id does not match'): operational_assurance_continuity_dossier_from_dict(payload)


def test_wave74_continuity_package_is_deterministic(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package); dossier=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW)
    a=package_operational_assurance_continuity_dossier(tmp_path/'a.zip',dossier,now=NOW);b=package_operational_assurance_continuity_dossier(tmp_path/'b.zip',dossier,now=NOW)
    assert a.sha256==b.sha256 and Path(a.path).read_bytes()==Path(b.path).read_bytes()


def test_wave74_pending_continuity_is_packageable_for_gap_handoff(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package,status='pending',artifacts=False,captured=None); dossier=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW)
    pkg=package_operational_assurance_continuity_dossier(tmp_path/'gap.zip',dossier,now=NOW); assert pkg.status is OperationalAssuranceContinuityStatus.PENDING


def test_wave74_blocked_continuity_not_packageable(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package,framework='wrong'); dossier=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW)
    with pytest.raises(ValueError,match='BLOCKED'): package_operational_assurance_continuity_dossier(tmp_path/'bad.zip',dossier,now=NOW)


def test_wave74_changed_artifact_not_packageable(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package); dossier=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW);Path(renewal.artifacts[0].path).write_text('changed')
    with pytest.raises(ValueError): package_operational_assurance_continuity_dossier(tmp_path/'bad.zip',dossier,now=NOW)


def test_wave74_package_contains_self_contained_chain(tmp_path: Path):
    closure,package=_wave73(tmp_path); renewal=_renewal(tmp_path,closure,package); dossier=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW);pkg=package_operational_assurance_continuity_dossier(tmp_path/'continuity.zip',dossier,now=NOW)
    with zipfile.ZipFile(pkg.path) as z:
        names=set(z.namelist()); assert {'operational-assurance-continuity.json','sustained-operations-renewal.json','wave73/incident-rollback-audit.zip','MANIFEST.sha256'}<=names


def test_wave74_renew_cli(tmp_path: Path,capsys):
    closure,package=_wave73(tmp_path);manifest=_renewal_manifest(tmp_path,closure);out=tmp_path/'renewal.json'
    rc=operations_evidence_renew_main([str(tmp_path/'wave73-audit.json'),package.path,str(manifest),'--now',NOW_ISO,'--output',str(out),'--format','json'])
    payload=json.loads(capsys.readouterr().out); assert rc==0 and payload['status']=='renewed' and out.is_file()


def test_wave74_continuity_cli(tmp_path: Path,capsys):
    closure,package=_wave73(tmp_path);renewal=_renewal(tmp_path,closure,package);rp=write_sustained_operations_evidence_renewal(tmp_path/'renewal.json',renewal);out=tmp_path/'continuity.json';pkg=tmp_path/'continuity.zip'
    rc=operational_assurance_continuity_main([str(tmp_path/'wave73-audit.json'),package.path,str(rp),'--now',NOW_ISO,'--output',str(out),'--package',str(pkg),'--format','json'])
    payload=json.loads(capsys.readouterr().out); assert rc==0 and payload['status']=='assured' and out.is_file() and pkg.is_file()


def test_wave74_top_level_cli_routes(tmp_path: Path):
    closure,package=_wave73(tmp_path);manifest=_renewal_manifest(tmp_path,closure);root=Path(__file__).parents[1]
    proc=subprocess.run([sys.executable,'-m','nicegui_base.cli','operations-evidence-renew',str(tmp_path/'wave73-audit.json'),package.path,str(manifest),'--now',NOW_ISO,'--format','json'],cwd=root,text=True,capture_output=True)
    assert proc.returncode==0 and json.loads(proc.stdout)['status']=='renewed'


def test_wave74_root_exports():
    for name in ('SustainedOperationsEvidenceRenewal','OperationalAssuranceContinuityDossier','verify_incident_rollback_audit_archive','SemiconductorSustainedOperationsRenewalPanel','SemiconductorOperationalAssuranceContinuityPanel'):
        assert hasattr(nicegui_base,name),name


def test_wave74_generated_starter_helpers_present():
    from nicegui_base.ai.project import _semiconductor_release_evidence_source
    source=_semiconductor_release_evidence_source()
    assert 'def renew_sustained_operations' in source
    assert 'def build_operational_assurance_continuity' in source
    assert 'verify_incident_rollback_audit_archive' in source


def test_wave74_states_do_not_mutate_wave73_truth(tmp_path: Path):
    closure,package=_wave73(tmp_path);before=closure.to_dict();renewal=_renewal(tmp_path,closure,package);dossier=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW)
    assert closure.to_dict()==before and dossier.to_dict()['historical_wave73_truth_mutated'] is False
    assert dossier.to_dict()['monitoring_performed_by_framework'] is False


def test_wave74_no_operational_execution_claims(tmp_path: Path):
    closure,package=_wave73(tmp_path);renewal=_renewal(tmp_path,closure,package);d=build_operational_assurance_continuity_dossier(closure,package.path,renewal,now=NOW).to_dict()
    for key in ('monitoring_performed_by_framework','incident_response_performed_by_framework','rollback_performed_by_framework','deployment_performed_by_framework','publication_performed_by_framework'):
        assert d[key] is False


def test_wave74_source_certification_phase_floor_is_74():
    source=Path('nicegui_base/governance/source_evidence.py').read_text(encoding='utf-8')
    assert "max(int(manifest.get('phase', 0)), 74)" in source
