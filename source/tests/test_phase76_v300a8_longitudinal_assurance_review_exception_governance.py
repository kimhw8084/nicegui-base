from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import test_phase75_v300a8_operational_assurance_renewal_ledger as w75

import nicegui_base
from nicegui_base import (
    FRAMEWORK_VERSION, NICEGUI_VERSION,
    EvidenceExceptionDisposition, EvidenceExceptionGovernanceStatus,
    LONGITUDINAL_ASSURANCE_REVIEW_ADAPTERS, LONGITUDINAL_EVIDENCE_EXCEPTION_POLICIES, LONGITUDINAL_EVIDENCE_EXCEPTION_POLICY,
    LongitudinalAssuranceArchiveStatus, LongitudinalAssuranceReviewStatus,
    LongitudinalEvidenceExceptionDecision, LongitudinalEvidenceExceptionPolicy,
    build_evidence_exception_governance_dossier, build_longitudinal_operational_assurance_dossier,
    evidence_exception_governance_dossier_from_dict, load_longitudinal_assurance_review_manifest,
    longitudinal_assurance_review_record_from_dict, package_evidence_exception_governance_dossier,
    package_longitudinal_operational_assurance_dossier, read_evidence_exception_governance_dossier,
    read_longitudinal_assurance_review_record, verify_longitudinal_operational_assurance_archive,
    write_evidence_exception_governance_dossier, write_longitudinal_assurance_review_record,
)
from nicegui_base.certification.semiconductor_longitudinal_review_cli import evidence_exception_governance_main, longitudinal_assurance_review_main

BASE = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace('+00:00', 'Z')


def _wave75_assured(tmp_path: Path):
    _, _, now, ledger = w75._good(tmp_path / 'history')
    dossier = build_longitudinal_operational_assurance_dossier(ledger, now=now, review_reference='OPS-GOV-75')
    package = package_longitudinal_operational_assurance_dossier(tmp_path / 'wave75-longitudinal.zip', dossier, now=now)
    return dossier, Path(package.path), now


def _wave75_pending_gap(tmp_path: Path):
    captures = [w75.BASE, w75.BASE + timedelta(hours=180)]
    _, _, packages = w75._wave74_chain(tmp_path / 'history', captures)
    now = w75.BASE + timedelta(hours=200)
    ledger = nicegui_base.build_operational_assurance_renewal_ledger(packages, now=now)
    assert ledger.status.value == 'pending'
    dossier = build_longitudinal_operational_assurance_dossier(ledger, now=now, review_reference='OPS-GAP-75')
    package = package_longitudinal_operational_assurance_dossier(tmp_path / 'wave75-gap.zip', dossier, now=now)
    return dossier, Path(package.path), now


def _review_manifest(tmp_path: Path, dossier, now: datetime, *, exceptions=(), **overrides):
    authority = tmp_path / 'review-authority.txt'; authority.write_text('approved external reviewer authority\n', encoding='utf-8')
    payload = {
        'dossier_id': dossier.dossier_id,
        'framework_version': FRAMEWORK_VERSION,
        'nicegui_required': NICEGUI_VERSION,
        'reviewer': 'A. Reviewer',
        'authority': 'Enterprise Reliability Review Board',
        'review_reference': 'ERRB-2026-076',
        'authority_issued_at': _iso(now - timedelta(hours=1)),
        'authority_expires_at': _iso(now + timedelta(hours=72)),
        'authority_revoked': False,
        'artifacts': [{'key':'review-authority','path':authority.name,'description':'external review authority'}],
        'exceptions': list(exceptions),
        'metadata': {'source':'test'},
    }
    payload.update(overrides)
    path = tmp_path / 'review-manifest.json'; path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return path, authority


def _review(tmp_path: Path, *, pending=False, exceptions=(), **overrides):
    dossier, package, now = _wave75_pending_gap(tmp_path) if pending else _wave75_assured(tmp_path)
    manifest, authority = _review_manifest(tmp_path, dossier, now, exceptions=exceptions, **overrides)
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    return dossier, package, now, review, authority, manifest


def _rewrite_zip(src: Path, dst: Path, mutate=None):
    with zipfile.ZipFile(src) as z:
        entries = {i.filename: z.read(i.filename) for i in z.infolist()}
    if mutate: mutate(entries)
    with zipfile.ZipFile(dst, 'w') as z:
        for name, blob in reversed(tuple(entries.items())): z.writestr(name, blob)
    return dst


def test_wave76_registries_are_bounded():
    assert set(LONGITUDINAL_ASSURANCE_REVIEW_ADAPTERS) == {'json-manifest'}
    assert set(LONGITUDINAL_EVIDENCE_EXCEPTION_POLICIES) == {'stable'}


def test_wave76_policy_is_framework_default_not_company_sla():
    p = LONGITUDINAL_EVIDENCE_EXCEPTION_POLICY
    assert p.target_version == '3.0.0' and p.max_exception_hours == 168
    assert p.permit_blocked_evidence_exceptions is False


@pytest.mark.parametrize('hours', [-1, -0.01])
def test_wave76_policy_rejects_negative_exception_bound(hours):
    with pytest.raises(ValueError): LongitudinalEvidenceExceptionPolicy(max_exception_hours=hours)


@pytest.mark.parametrize('disposition', list(EvidenceExceptionDisposition))
def test_wave76_exception_decision_roundtrip_enum(disposition):
    d = LongitudinalEvidenceExceptionDecision('ledger_coverage_gap', disposition, 'bounded external decision')
    assert d.to_dict()['disposition'] == disposition.value


def test_wave76_wave75_archive_verifies(tmp_path: Path):
    dossier, package, _ = _wave75_assured(tmp_path)
    r = verify_longitudinal_operational_assurance_archive(package, expected_dossier=dossier)
    assert r.verified and r.status is LongitudinalAssuranceArchiveStatus.VERIFIED
    assert r.dossier_id == dossier.dossier_id and r.ledger_id == dossier.ledger.ledger_id


def test_wave76_missing_wave75_archive_is_pending(tmp_path: Path):
    r = verify_longitudinal_operational_assurance_archive(tmp_path/'missing.zip')
    assert r.status is LongitudinalAssuranceArchiveStatus.PENDING


def test_wave76_wrong_dossier_subject_blocks(tmp_path: Path):
    dossier, package, _ = _wave75_assured(tmp_path/'a')
    other, _, _ = _wave75_assured(tmp_path/'b')
    r = verify_longitudinal_operational_assurance_archive(package, expected_dossier=other)
    assert r.status is LongitudinalAssuranceArchiveStatus.BLOCKED
    assert any(x.code == 'longitudinal_archive_subject_mismatch' for x in r.findings)


def test_wave76_duplicate_entry_blocks(tmp_path: Path):
    dossier, package, _ = _wave75_assured(tmp_path); bad = tmp_path/'dup.zip'
    with zipfile.ZipFile(package) as src, zipfile.ZipFile(bad,'w') as out:
        for i in src.infolist(): out.writestr(i.filename, src.read(i.filename))
        out.writestr('longitudinal-operational-assurance.json', src.read('longitudinal-operational-assurance.json'))
    assert verify_longitudinal_operational_assurance_archive(bad, expected_dossier=dossier).status is LongitudinalAssuranceArchiveStatus.BLOCKED


def test_wave76_unsafe_entry_blocks(tmp_path: Path):
    dossier, package, _ = _wave75_assured(tmp_path)
    bad = _rewrite_zip(package, tmp_path/'unsafe.zip', lambda e: e.__setitem__('../escape', b'x'))
    assert any(x.code == 'longitudinal_archive_unsafe_entry' for x in verify_longitudinal_operational_assurance_archive(bad, expected_dossier=dossier).findings)


def test_wave76_manifest_incomplete_blocks(tmp_path: Path):
    dossier, package, _ = _wave75_assured(tmp_path)
    bad = _rewrite_zip(package, tmp_path/'extra.zip', lambda e: e.__setitem__('extra.json', b'{}'))
    assert any(x.code == 'longitudinal_archive_manifest_incomplete' for x in verify_longitudinal_operational_assurance_archive(bad, expected_dossier=dossier).findings)


def test_wave76_hash_tamper_blocks(tmp_path: Path):
    dossier, package, _ = _wave75_assured(tmp_path)
    bad = _rewrite_zip(package, tmp_path/'tamper.zip', lambda e: e.__setitem__('operational-assurance-renewal-ledger.json', e['operational-assurance-renewal-ledger.json']+b'x'))
    assert any(x.code == 'longitudinal_archive_hash_mismatch' for x in verify_longitudinal_operational_assurance_archive(bad, expected_dossier=dossier).findings)


def test_wave76_nested_wave74_tamper_blocks_even_if_manifest_rehashed(tmp_path: Path):
    dossier, package, _ = _wave75_assured(tmp_path)
    def mutate(e):
        key = sorted(k for k in e if k.startswith('wave74/'))[0]
        e[key] += b'x'; e.pop('MANIFEST.sha256')
        e['MANIFEST.sha256'] = ''.join(f'{hashlib.sha256(e[n]).hexdigest()}  {n}\n' for n in sorted(e)).encode()
    bad = _rewrite_zip(package, tmp_path/'nested.zip', mutate)
    r = verify_longitudinal_operational_assurance_archive(bad, expected_dossier=dossier)
    assert r.status is LongitudinalAssuranceArchiveStatus.BLOCKED
    assert any(x.code == 'longitudinal_archive_wave74_hash_mismatch' for x in r.findings)


def test_wave76_good_review_is_reviewed(tmp_path: Path):
    _, _, _, review, _, _ = _review(tmp_path)
    assert review.status is LongitudinalAssuranceReviewStatus.REVIEWED
    assert review.to_dict()['synthetic_evidence_pass_created'] is False


def test_wave76_review_is_identity_bound(tmp_path: Path):
    _, _, _, review, _, _ = _review(tmp_path)
    payload = review.to_dict(); payload['review_reference'] = 'changed'
    with pytest.raises(ValueError, match='id does not match'): longitudinal_assurance_review_record_from_dict(payload)


def test_wave76_review_status_tamper_detected(tmp_path: Path):
    _, _, _, review, _, _ = _review(tmp_path)
    payload = review.to_dict(); payload['status'] = 'blocked'
    with pytest.raises(ValueError, match='status does not match'): longitudinal_assurance_review_record_from_dict(payload)


def test_wave76_review_roundtrip(tmp_path: Path):
    _, _, _, review, _, _ = _review(tmp_path)
    path = write_longitudinal_assurance_review_record(tmp_path/'review.json', review)
    assert read_longitudinal_assurance_review_record(path).review_id == review.review_id



def test_wave76_missing_reviewer_authority_reference_is_pending(tmp_path: Path):
    dossier, package, now = _wave75_assured(tmp_path)
    manifest, _ = _review_manifest(tmp_path, dossier, now, reviewer='', authority='', review_reference='')
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert review.status is LongitudinalAssuranceReviewStatus.PENDING
    assert any(x.code == 'review_authority_missing' for x in review.findings)


def test_wave76_expired_authority_is_pending(tmp_path: Path):
    dossier, package, now = _wave75_assured(tmp_path)
    manifest, _ = _review_manifest(tmp_path, dossier, now, authority_expires_at=_iso(now-timedelta(seconds=1)))
    r = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert r.status is LongitudinalAssuranceReviewStatus.PENDING
    assert any(x.code == 'review_authority_expired' for x in r.findings)


def test_wave76_revoked_authority_is_pending(tmp_path: Path):
    _, _, _, review, _, _ = _review(tmp_path, authority_revoked=True)
    assert review.status is LongitudinalAssuranceReviewStatus.PENDING
    assert any(x.code == 'review_authority_revoked' for x in review.findings)


def test_wave76_missing_expiry_is_pending(tmp_path: Path):
    _, _, _, review, _, _ = _review(tmp_path, authority_expires_at=None)
    assert review.status is LongitudinalAssuranceReviewStatus.PENDING


def test_wave76_future_authority_issue_blocks(tmp_path: Path):
    dossier, package, now = _wave75_assured(tmp_path)
    manifest, _ = _review_manifest(tmp_path, dossier, now, authority_issued_at=_iso(now+timedelta(hours=1)))
    r = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert r.status is LongitudinalAssuranceReviewStatus.BLOCKED


def test_wave76_authority_timestamp_contradiction_blocks(tmp_path: Path):
    dossier, package, now = _wave75_assured(tmp_path)
    manifest, _ = _review_manifest(tmp_path, dossier, now, authority_issued_at=_iso(now+timedelta(hours=2)), authority_expires_at=_iso(now+timedelta(hours=1)))
    r = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert r.status is LongitudinalAssuranceReviewStatus.BLOCKED


def test_wave76_missing_authority_artifact_is_pending(tmp_path: Path):
    dossier, package, now = _wave75_assured(tmp_path)
    manifest, authority = _review_manifest(tmp_path, dossier, now)
    authority.unlink()
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert review.status is LongitudinalAssuranceReviewStatus.PENDING
    assert any(x.code == 'review_authority_artifact_missing' for x in review.findings)


def test_wave76_persisted_authority_artifact_tamper_blocks_governance(tmp_path: Path):
    _, _, now, review, authority, _ = _review(tmp_path)
    authority.write_text('changed\n', encoding='utf-8')
    g = build_evidence_exception_governance_dossier(review, now=now)
    assert g.status is EvidenceExceptionGovernanceStatus.BLOCKED
    assert any('artifact' in x.code for x in g.findings)


def test_wave76_manifest_wrong_dossier_rejected(tmp_path: Path):
    dossier, package, now = _wave75_assured(tmp_path)
    manifest, _ = _review_manifest(tmp_path, dossier, now, dossier_id='0'*64)
    with pytest.raises(ValueError, match='dossier_id'): load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)


def test_wave76_manifest_wrong_framework_rejected(tmp_path: Path):
    dossier, package, now = _wave75_assured(tmp_path)
    manifest, _ = _review_manifest(tmp_path, dossier, now, framework_version='other')
    with pytest.raises(ValueError, match='framework_version'): load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)


def test_wave76_manifest_wrong_nicegui_rejected(tmp_path: Path):
    dossier, package, now = _wave75_assured(tmp_path)
    manifest, _ = _review_manifest(tmp_path, dossier, now, nicegui_required='0.0.0')
    with pytest.raises(ValueError, match='nicegui_required'): load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)


def test_wave76_manifest_artifact_escape_rejected(tmp_path: Path):
    dossier, package, now = _wave75_assured(tmp_path)
    manifest, _ = _review_manifest(tmp_path, dossier, now, artifacts=[{'key':'x','path':'../escape'}])
    with pytest.raises(ValueError, match='escapes'): load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)


def _accepted_gap_exception(now):
    return {'finding_code':'ledger_coverage_gap','disposition':'accepted','rationale':'bounded external exception','exception_reference':'EX-76-1','expires_at':_iso(now+timedelta(hours=24))}


def test_wave76_pending_gap_without_exception_stays_pending_governance(tmp_path: Path):
    _, _, now, review, _, _ = _review(tmp_path, pending=True)
    g = build_evidence_exception_governance_dossier(review, now=now)
    assert g.status is EvidenceExceptionGovernanceStatus.PENDING
    assert g.to_dict()['underlying_evidence_status'] == 'pending'


def test_wave76_accepted_bounded_gap_can_be_governed_without_synthetic_pass(tmp_path: Path):
    dossier, package, now = _wave75_pending_gap(tmp_path)
    manifest, _ = _review_manifest(tmp_path, dossier, now, exceptions=[_accepted_gap_exception(now)])
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    g = build_evidence_exception_governance_dossier(review, now=now)
    assert review.status is LongitudinalAssuranceReviewStatus.REVIEWED
    assert g.status is EvidenceExceptionGovernanceStatus.GOVERNED
    assert g.to_dict()['underlying_evidence_status'] == 'pending'
    assert g.to_dict()['accepted_exception_creates_synthetic_pass'] is False


def test_wave76_exception_unknown_subject_blocks(tmp_path: Path):
    dossier, package, now = _wave75_pending_gap(tmp_path)
    exc = _accepted_gap_exception(now); exc['finding_code'] = 'not-a-real-finding'
    manifest, _ = _review_manifest(tmp_path, dossier, now, exceptions=[exc])
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert review.status is LongitudinalAssuranceReviewStatus.BLOCKED


def test_wave76_exception_not_allowed_blocks(tmp_path: Path):
    dossier, package, now = _wave75_pending_gap(tmp_path)
    exc = _accepted_gap_exception(now)
    manifest, _ = _review_manifest(tmp_path, dossier, now, exceptions=[exc])
    policy = LongitudinalEvidenceExceptionPolicy(allowed_finding_codes=())
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now, policy=policy)
    assert review.status is LongitudinalAssuranceReviewStatus.BLOCKED


def test_wave76_exception_missing_reference_is_pending(tmp_path: Path):
    dossier, package, now = _wave75_pending_gap(tmp_path)
    exc = _accepted_gap_exception(now); exc['exception_reference'] = None
    manifest, _ = _review_manifest(tmp_path, dossier, now, exceptions=[exc])
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert review.status is LongitudinalAssuranceReviewStatus.PENDING


def test_wave76_exception_missing_expiry_is_pending(tmp_path: Path):
    dossier, package, now = _wave75_pending_gap(tmp_path)
    exc = _accepted_gap_exception(now); exc['expires_at'] = None
    manifest, _ = _review_manifest(tmp_path, dossier, now, exceptions=[exc])
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert review.status is LongitudinalAssuranceReviewStatus.PENDING


def test_wave76_exception_expired_is_pending(tmp_path: Path):
    dossier, package, now = _wave75_pending_gap(tmp_path)
    exc = _accepted_gap_exception(now); exc['expires_at'] = _iso(now-timedelta(seconds=1))
    manifest, _ = _review_manifest(tmp_path, dossier, now, exceptions=[exc])
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert review.status is LongitudinalAssuranceReviewStatus.PENDING


def test_wave76_exception_exceeding_bound_blocks(tmp_path: Path):
    dossier, package, now = _wave75_pending_gap(tmp_path)
    exc = _accepted_gap_exception(now); exc['expires_at'] = _iso(now+timedelta(hours=200))
    manifest, _ = _review_manifest(tmp_path, dossier, now, exceptions=[exc])
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert review.status is LongitudinalAssuranceReviewStatus.BLOCKED


def test_wave76_unresolved_exception_stays_pending(tmp_path: Path):
    dossier, package, now = _wave75_pending_gap(tmp_path)
    exc = _accepted_gap_exception(now); exc['disposition'] = 'unresolved'
    manifest, _ = _review_manifest(tmp_path, dossier, now, exceptions=[exc])
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert review.status is LongitudinalAssuranceReviewStatus.PENDING


def test_wave76_rejected_exception_stays_pending(tmp_path: Path):
    dossier, package, now = _wave75_pending_gap(tmp_path)
    exc = _accepted_gap_exception(now); exc['disposition'] = 'rejected'
    manifest, _ = _review_manifest(tmp_path, dossier, now, exceptions=[exc])
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert review.status is LongitudinalAssuranceReviewStatus.PENDING


def test_wave76_duplicate_exception_blocks(tmp_path: Path):
    dossier, package, now = _wave75_pending_gap(tmp_path)
    exc = _accepted_gap_exception(now)
    manifest, _ = _review_manifest(tmp_path, dossier, now, exceptions=[exc, dict(exc)])
    review = load_longitudinal_assurance_review_manifest(manifest, dossier, package, now=now)
    assert review.status is LongitudinalAssuranceReviewStatus.BLOCKED


def test_wave76_governance_roundtrip(tmp_path: Path):
    _, _, now, review, _, _ = _review(tmp_path)
    g = build_evidence_exception_governance_dossier(review, now=now)
    path = write_evidence_exception_governance_dossier(tmp_path/'governance.json', g)
    assert read_evidence_exception_governance_dossier(path).governance_id == g.governance_id


def test_wave76_governance_tamper_detected(tmp_path: Path):
    _, _, now, review, _, _ = _review(tmp_path)
    g = build_evidence_exception_governance_dossier(review, now=now)
    payload = g.to_dict(); payload['metadata'] = {'tampered':True}
    with pytest.raises(ValueError, match='id does not match'): evidence_exception_governance_dossier_from_dict(payload)


def test_wave76_governance_status_tamper_detected(tmp_path: Path):
    _, _, now, review, _, _ = _review(tmp_path)
    g = build_evidence_exception_governance_dossier(review, now=now)
    payload = g.to_dict(); payload['status'] = 'blocked'
    with pytest.raises(ValueError, match='status does not match'): evidence_exception_governance_dossier_from_dict(payload)


def test_wave76_bound_wave75_outer_hash_change_blocks_governance(tmp_path: Path):
    _, package, now, review, _, _ = _review(tmp_path)
    package.write_bytes(package.read_bytes()+b'x')
    g = build_evidence_exception_governance_dossier(review, now=now)
    assert g.status is EvidenceExceptionGovernanceStatus.BLOCKED


def test_wave76_package_is_deterministic(tmp_path: Path):
    _, _, now, review, _, _ = _review(tmp_path)
    g = build_evidence_exception_governance_dossier(review, now=now)
    a = package_evidence_exception_governance_dossier(tmp_path/'a.zip', g, now=now)
    b = package_evidence_exception_governance_dossier(tmp_path/'b.zip', g, now=now)
    assert a.sha256 == b.sha256 and a.entries == b.entries


def test_wave76_pending_governance_is_packageable_for_gap_handoff(tmp_path: Path):
    _, _, now, review, _, _ = _review(tmp_path, pending=True)
    g = build_evidence_exception_governance_dossier(review, now=now)
    assert g.status is EvidenceExceptionGovernanceStatus.PENDING
    p = package_evidence_exception_governance_dossier(tmp_path/'pending.zip', g, now=now)
    assert Path(p.path).is_file()


def test_wave76_changed_authority_artifact_refuses_package(tmp_path: Path):
    _, _, now, review, authority, _ = _review(tmp_path)
    g = build_evidence_exception_governance_dossier(review, now=now)
    authority.write_text('changed', encoding='utf-8')
    with pytest.raises(ValueError): package_evidence_exception_governance_dossier(tmp_path/'bad.zip', g, now=now)


def test_wave76_review_cli(tmp_path: Path, capsys):
    dossier, package, now = _wave75_assured(tmp_path)
    dossier_path = nicegui_base.write_longitudinal_operational_assurance_dossier(tmp_path/'dossier.json', dossier)
    manifest, _ = _review_manifest(tmp_path, dossier, now)
    out = tmp_path/'review.json'
    code = longitudinal_assurance_review_main(['nicegui-base longitudinal-assurance-review', str(dossier_path), str(package), str(manifest), '--now', _iso(now), '--output', str(out)])
    assert code == 0 and out.is_file()
    assert json.loads(capsys.readouterr().out)['status'] == 'reviewed'


def test_wave76_governance_cli(tmp_path: Path, capsys):
    _, _, now, review, _, _ = _review(tmp_path)
    review_path = write_longitudinal_assurance_review_record(tmp_path/'review.json', review)
    out = tmp_path/'g.json'; package = tmp_path/'g.zip'
    code = evidence_exception_governance_main(['nicegui-base evidence-exception-governance', str(review_path), '--now', _iso(now), '--output', str(out), '--package', str(package)])
    assert code == 0 and out.is_file() and package.is_file()
    assert json.loads(capsys.readouterr().out)['status'] == 'governed'


def test_wave76_root_exports_present():
    for name in ('LongitudinalAssuranceReviewRecord','EvidenceExceptionGovernanceDossier','verify_longitudinal_operational_assurance_archive','package_evidence_exception_governance_dossier'):
        assert hasattr(nicegui_base, name)


def test_wave76_safety_flags_are_explicit(tmp_path: Path):
    _, _, now, review, _, _ = _review(tmp_path)
    g = build_evidence_exception_governance_dossier(review, now=now).to_dict()
    assert g['underlying_evidence_status_changed'] is False
    assert g['accepted_exception_creates_synthetic_pass'] is False
    assert g['monitoring_performed_by_framework'] is False
    assert g['incident_response_performed_by_framework'] is False
    assert g['rollback_performed_by_framework'] is False
    assert g['deployment_performed_by_framework'] is False
    assert g['publication_performed_by_framework'] is False


def test_wave76_generated_semiconductor_project_contains_review_helpers_and_guide(tmp_path: Path):
    from nicegui_base.ai.project import create_application
    created = create_application(tmp_path / 'generated', name='Wave76Generated', recipe='spc-monitor')
    release_helper = created.root / 'services/release_evidence.py'
    text = release_helper.read_text(encoding='utf-8')
    assert 'def review_longitudinal_assurance(' in text
    assert 'def govern_evidence_exceptions(' in text
    assert (created.root / 'docs/nicegui_base/SEMICONDUCTOR_LONGITUDINAL_ASSURANCE_REVIEW_EXCEPTION_GOVERNANCE.md').is_file()
    install_manifest = json.loads((created.root / '.nicegui_base/install_manifest.json').read_text(encoding='utf-8'))
    assert 'evidence_exception_governance_command' in install_manifest


def test_wave76_main_cli_exposes_review_and_exception_governance_routes():
    import subprocess, sys
    completed = subprocess.run([sys.executable, '-m', 'nicegui_base.cli', '--help'], text=True, capture_output=True, check=False)
    assert completed.returncode == 0
    assert 'longitudinal-assurance-review' in completed.stdout
    assert 'evidence-exception-governance' in completed.stdout


def test_wave76_source_certification_phase_floor_is_76():
    source = Path('nicegui_base/governance/source_evidence.py').read_text(encoding='utf-8')
    assert "max(int(manifest.get('phase', 0)), 76)" in source
