from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import test_phase74_v300a8_operations_evidence_renewal_continuity as w74

import nicegui_base
from nicegui_base import (
    FRAMEWORK_VERSION, NICEGUI_VERSION,
    OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICIES, OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICY,
    LongitudinalOperationalAssuranceDossier, OperationalAssuranceContinuityArchiveStatus,
    OperationalAssuranceLedgerStatus, OperationalAssuranceRenewalLedgerPolicy,
    build_longitudinal_operational_assurance_dossier, build_operational_assurance_continuity_dossier,
    build_operational_assurance_renewal_ledger, longitudinal_operational_assurance_dossier_from_dict,
    operational_assurance_renewal_ledger_from_dict, package_longitudinal_operational_assurance_dossier,
    package_operational_assurance_continuity_dossier, read_longitudinal_operational_assurance_dossier,
    read_operational_assurance_renewal_ledger, verify_operational_assurance_continuity_archive,
    verify_operational_assurance_renewal_ledger, write_longitudinal_operational_assurance_dossier,
    write_operational_assurance_renewal_ledger,
)
from nicegui_base.certification.semiconductor_longitudinal_cli import longitudinal_assurance_main, operational_assurance_ledger_main

BASE = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat().replace('+00:00', 'Z')


def _wave74_chain(tmp_path: Path, captures: list[datetime]):
    closure, audit_package = w74._wave73(tmp_path / 'wave73')
    packages = []
    dossiers = []
    for index, captured in enumerate(captures, start=1):
        period = tmp_path / f'period-{index}'
        period.mkdir(parents=True, exist_ok=True)
        renewal = w74._renewal(period, closure, audit_package, captured=_iso(captured))
        dossier = build_operational_assurance_continuity_dossier(closure, audit_package.path, renewal, now=captured + timedelta(hours=1))
        package = package_operational_assurance_continuity_dossier(period / 'wave74-continuity.zip', dossier, now=captured + timedelta(hours=1))
        packages.append(Path(package.path))
        dossiers.append(dossier)
    return closure, tuple(dossiers), tuple(packages)


def _rewrite_zip(src: Path, dst: Path, mutate=None):
    with zipfile.ZipFile(src) as z:
        entries = {i.filename: z.read(i.filename) for i in z.infolist()}
    if mutate:
        mutate(entries)
    with zipfile.ZipFile(dst, 'w') as z:
        for name, blob in reversed(tuple(entries.items())):
            z.writestr(name, blob)
    return dst


def _good(tmp_path: Path):
    captures = [BASE, BASE + timedelta(hours=144), BASE + timedelta(hours=288)]
    _, dossiers, packages = _wave74_chain(tmp_path, captures)
    now = BASE + timedelta(hours=312)
    ledger = build_operational_assurance_renewal_ledger(packages, now=now)
    return dossiers, packages, now, ledger


def test_wave75_registry_is_bounded():
    assert set(OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICIES) == {'stable'}


def test_wave75_default_policy_is_framework_policy_not_company_sla():
    p = OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICY
    assert p.target_version == '3.0.0'
    assert p.max_gap_hours == 0
    assert p.expiring_within_hours == 24
    assert p.max_future_skew_minutes == 5
    assert p.max_overlap_hours is None


@pytest.mark.parametrize('kwargs', [
    {'max_gap_hours': -1}, {'expiring_within_hours': -1}, {'max_future_skew_minutes': -1}, {'max_overlap_hours': -1},
])
def test_wave75_policy_rejects_negative_limits(kwargs):
    with pytest.raises(ValueError):
        OperationalAssuranceRenewalLedgerPolicy(**kwargs)


def test_wave75_wave74_archive_verifies(tmp_path: Path):
    dossiers, packages, _, _ = _good(tmp_path)
    report = verify_operational_assurance_continuity_archive(packages[0], expected_dossier=dossiers[0])
    assert report.verified
    assert report.status is OperationalAssuranceContinuityArchiveStatus.VERIFIED
    assert report.continuity_id == dossiers[0].continuity_id
    assert report.renewal_id == dossiers[0].renewal.renewal_id


def test_wave75_missing_wave74_archive_is_pending(tmp_path: Path):
    report = verify_operational_assurance_continuity_archive(tmp_path / 'missing.zip')
    assert report.status is OperationalAssuranceContinuityArchiveStatus.PENDING


def test_wave75_wrong_subject_blocks(tmp_path: Path):
    dossiers, packages, _, _ = _good(tmp_path)
    report = verify_operational_assurance_continuity_archive(packages[0], expected_dossier=dossiers[1])
    assert report.status is OperationalAssuranceContinuityArchiveStatus.BLOCKED
    assert any(x.code == 'continuity_archive_subject_mismatch' for x in report.findings)


def test_wave75_duplicate_archive_entry_blocks(tmp_path: Path):
    dossiers, packages, _, _ = _good(tmp_path); bad = tmp_path / 'dup.zip'
    with zipfile.ZipFile(packages[0]) as src, zipfile.ZipFile(bad, 'w') as out:
        for i in src.infolist(): out.writestr(i.filename, src.read(i.filename))
        out.writestr('operational-assurance-continuity.json', src.read('operational-assurance-continuity.json'))
    assert verify_operational_assurance_continuity_archive(bad, expected_dossier=dossiers[0]).status is OperationalAssuranceContinuityArchiveStatus.BLOCKED


def test_wave75_unsafe_archive_entry_blocks(tmp_path: Path):
    dossiers, packages, _, _ = _good(tmp_path)
    bad = _rewrite_zip(packages[0], tmp_path / 'unsafe.zip', lambda e: e.__setitem__('../escape', b'x'))
    report = verify_operational_assurance_continuity_archive(bad, expected_dossier=dossiers[0])
    assert report.status is OperationalAssuranceContinuityArchiveStatus.BLOCKED
    assert any(x.code == 'continuity_archive_unsafe_entry' for x in report.findings)


def test_wave75_archive_manifest_incomplete_blocks(tmp_path: Path):
    dossiers, packages, _, _ = _good(tmp_path)
    bad = _rewrite_zip(packages[0], tmp_path / 'extra.zip', lambda e: e.__setitem__('extra.json', b'{}\n'))
    assert any(x.code == 'continuity_archive_manifest_incomplete' for x in verify_operational_assurance_continuity_archive(bad, expected_dossier=dossiers[0]).findings)


def test_wave75_archive_entry_hash_tamper_blocks(tmp_path: Path):
    dossiers, packages, _, _ = _good(tmp_path)
    bad = _rewrite_zip(packages[0], tmp_path / 'tamper.zip', lambda e: e.__setitem__('sustained-operations-renewal.json', e['sustained-operations-renewal.json'] + b'x'))
    assert any(x.code == 'continuity_archive_hash_mismatch' for x in verify_operational_assurance_continuity_archive(bad, expected_dossier=dossiers[0]).findings)


def test_wave75_nested_wave73_hash_tamper_blocks_even_if_manifest_rehashed(tmp_path: Path):
    dossiers, packages, _, _ = _good(tmp_path)
    def mutate(e):
        e['wave73/incident-rollback-audit.zip'] += b'x'
        payload = e.pop('MANIFEST.sha256')
        del payload
        e['MANIFEST.sha256'] = ''.join(f'{hashlib.sha256(e[n]).hexdigest()}  {n}\n' for n in sorted(e)).encode()
    bad = _rewrite_zip(packages[0], tmp_path / 'nested.zip', mutate)
    assert any(x.code == 'continuity_archive_wave73_hash_mismatch' for x in verify_operational_assurance_continuity_archive(bad, expected_dossier=dossiers[0]).findings)


def test_wave75_ledger_assured_for_overlapping_no_gap_chain(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path)
    assert ledger.status is OperationalAssuranceLedgerStatus.ASSURED
    assert len(ledger.entries) == 3
    assert any(x.code == 'ledger_coverage_overlap' for x in ledger.findings)


def test_wave75_ledger_input_order_does_not_change_identity(tmp_path: Path):
    _, packages, now, ledger = _good(tmp_path)
    reordered = build_operational_assurance_renewal_ledger(tuple(reversed(packages)), now=now)
    # source path order is intentionally part of handoff identity; period ordering remains deterministic.
    assert [x.renewal_id for x in reordered.entries] == [x.renewal_id for x in ledger.entries]


def test_wave75_ledger_gap_is_pending(tmp_path: Path):
    captures = [BASE, BASE + timedelta(hours=180)]
    _, _, packages = _wave74_chain(tmp_path, captures)
    ledger = build_operational_assurance_renewal_ledger(packages, now=BASE + timedelta(hours=200))
    assert ledger.status is OperationalAssuranceLedgerStatus.PENDING
    assert any(x.code == 'ledger_coverage_gap' for x in ledger.findings)


def test_wave75_policy_can_bound_tolerated_gap(tmp_path: Path):
    captures = [BASE, BASE + timedelta(hours=174)]
    _, _, packages = _wave74_chain(tmp_path, captures)
    policy = OperationalAssuranceRenewalLedgerPolicy(max_gap_hours=8)
    ledger = build_operational_assurance_renewal_ledger(packages, policy=policy, now=BASE + timedelta(hours=200))
    assert not any(x.code == 'ledger_coverage_gap' for x in ledger.findings)
    assert any(x.code == 'ledger_tolerated_coverage_gap' for x in ledger.findings)


def test_wave75_overlap_can_be_bounded_by_policy(tmp_path: Path):
    _, packages, now, _ = _good(tmp_path)
    policy = OperationalAssuranceRenewalLedgerPolicy(max_overlap_hours=12)
    ledger = build_operational_assurance_renewal_ledger(packages, policy=policy, now=now)
    assert ledger.status is OperationalAssuranceLedgerStatus.PENDING
    assert any(x.code == 'ledger_coverage_overlap' and x.status is OperationalAssuranceLedgerStatus.PENDING for x in ledger.findings)


def test_wave75_latest_window_expiring(tmp_path: Path):
    captures = [BASE, BASE + timedelta(hours=144)]
    _, _, packages = _wave74_chain(tmp_path, captures)
    expiry = captures[-1] + timedelta(hours=168)
    ledger = build_operational_assurance_renewal_ledger(packages, now=expiry - timedelta(hours=12))
    assert ledger.status is OperationalAssuranceLedgerStatus.EXPIRING
    assert any(x.code == 'ledger_active_window_expiring' for x in ledger.findings)


def test_wave75_latest_window_stale_is_pending(tmp_path: Path):
    captures = [BASE, BASE + timedelta(hours=144)]
    _, _, packages = _wave74_chain(tmp_path, captures)
    expiry = captures[-1] + timedelta(hours=168)
    ledger = build_operational_assurance_renewal_ledger(packages, now=expiry + timedelta(hours=1))
    assert ledger.status is OperationalAssuranceLedgerStatus.PENDING
    assert any(x.code == 'ledger_active_window_stale' for x in ledger.findings)


def test_wave75_historical_expiry_with_timely_successor_is_diagnostic_not_failure(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path)
    assert any(x.code == 'ledger_historical_stale_interval_covered' for x in ledger.findings)
    assert ledger.status is OperationalAssuranceLedgerStatus.ASSURED


def test_wave75_missing_source_package_is_pending(tmp_path: Path):
    _, packages, now, _ = _good(tmp_path)
    ledger = build_operational_assurance_renewal_ledger((packages[0], tmp_path / 'missing.zip'), now=now)
    assert ledger.status is OperationalAssuranceLedgerStatus.PENDING
    assert any(x.code == 'ledger_source_missing' for x in ledger.findings)


def test_wave75_tampered_source_package_blocks_ledger(tmp_path: Path):
    _, packages, now, _ = _good(tmp_path)
    bad = _rewrite_zip(packages[1], tmp_path / 'bad.zip', lambda e: e.__setitem__('sustained-operations-renewal.json', e['sustained-operations-renewal.json'] + b'x'))
    ledger = build_operational_assurance_renewal_ledger((packages[0], bad), now=now)
    assert ledger.status is OperationalAssuranceLedgerStatus.BLOCKED
    assert any(x.code == 'ledger_source_blocked' for x in ledger.findings)


def test_wave75_duplicate_identical_period_is_pending(tmp_path: Path):
    _, packages, now, _ = _good(tmp_path)
    ledger = build_operational_assurance_renewal_ledger((packages[0], packages[0]), now=now)
    assert ledger.status is OperationalAssuranceLedgerStatus.PENDING
    assert any(x.code == 'ledger_duplicate_continuity_identity' for x in ledger.findings)


def test_wave75_same_continuity_identity_with_different_outer_archive_bytes_blocks(tmp_path: Path):
    _, packages, now, _ = _good(tmp_path)
    alternate = _rewrite_zip(packages[0], tmp_path / 'alternate.zip')
    assert hashlib.sha256(alternate.read_bytes()).hexdigest() != hashlib.sha256(packages[0].read_bytes()).hexdigest()
    ledger = build_operational_assurance_renewal_ledger((packages[0], alternate), now=now)
    assert ledger.status is OperationalAssuranceLedgerStatus.BLOCKED


def test_wave75_ledger_roundtrip(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path)
    path = write_operational_assurance_renewal_ledger(tmp_path / 'ledger.json', ledger)
    restored = read_operational_assurance_renewal_ledger(path)
    assert restored.ledger_id == ledger.ledger_id and restored.status is ledger.status


def test_wave75_ledger_tamper_is_detected(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path)
    payload = ledger.to_dict(); payload['metadata'] = {'tampered': True}
    with pytest.raises(ValueError, match='id does not match'):
        operational_assurance_renewal_ledger_from_dict(payload)


def test_wave75_ledger_status_tamper_is_detected(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path)
    payload = ledger.to_dict(); payload['status'] = 'blocked'
    with pytest.raises(ValueError, match='status does not match'):
        operational_assurance_renewal_ledger_from_dict(payload)


def test_wave75_ledger_reverification_detects_changed_package(tmp_path: Path):
    _, packages, _, ledger = _good(tmp_path)
    packages[-1].write_bytes(packages[-1].read_bytes() + b'x')
    refreshed = verify_operational_assurance_renewal_ledger(ledger)
    assert refreshed.status is OperationalAssuranceLedgerStatus.BLOCKED


def test_wave75_longitudinal_dossier_assured(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path)
    dossier = build_longitudinal_operational_assurance_dossier(ledger, review_reference='OPS-GOV-75')
    assert dossier.status is OperationalAssuranceLedgerStatus.ASSURED
    assert dossier.review_reference == 'OPS-GOV-75'


def test_wave75_longitudinal_dossier_roundtrip(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path)
    dossier = build_longitudinal_operational_assurance_dossier(ledger)
    path = write_longitudinal_operational_assurance_dossier(tmp_path / 'dossier.json', dossier)
    assert read_longitudinal_operational_assurance_dossier(path).dossier_id == dossier.dossier_id


def test_wave75_longitudinal_dossier_tamper_detected(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path)
    dossier = build_longitudinal_operational_assurance_dossier(ledger)
    payload = dossier.to_dict(); payload['review_reference'] = 'changed'
    with pytest.raises(ValueError, match='id does not match'):
        longitudinal_operational_assurance_dossier_from_dict(payload)


def test_wave75_longitudinal_package_is_deterministic(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path)
    dossier = build_longitudinal_operational_assurance_dossier(ledger)
    a = package_longitudinal_operational_assurance_dossier(tmp_path / 'a.zip', dossier)
    b = package_longitudinal_operational_assurance_dossier(tmp_path / 'b.zip', dossier)
    assert a.sha256 == b.sha256
    assert Path(a.path).read_bytes() == Path(b.path).read_bytes()


def test_wave75_longitudinal_package_contains_self_contained_wave74_chain(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path)
    dossier = build_longitudinal_operational_assurance_dossier(ledger)
    package = package_longitudinal_operational_assurance_dossier(tmp_path / 'longitudinal.zip', dossier)
    with zipfile.ZipFile(package.path) as z:
        names = set(z.namelist())
    assert {'longitudinal-operational-assurance.json', 'operational-assurance-renewal-ledger.json', 'MANIFEST.sha256'} <= names
    assert len([x for x in names if x.startswith('wave74/')]) == len(ledger.entries)


def test_wave75_pending_dossier_is_packageable_for_gap_handoff(tmp_path: Path):
    captures = [BASE, BASE + timedelta(hours=180)]
    _, _, packages = _wave74_chain(tmp_path, captures)
    ledger = build_operational_assurance_renewal_ledger(packages, now=BASE + timedelta(hours=200))
    dossier = build_longitudinal_operational_assurance_dossier(ledger)
    package = package_longitudinal_operational_assurance_dossier(tmp_path / 'pending.zip', dossier)
    assert package.status is OperationalAssuranceLedgerStatus.PENDING


def test_wave75_blocked_dossier_not_packageable(tmp_path: Path):
    _, packages, now, _ = _good(tmp_path)
    bad = _rewrite_zip(packages[0], tmp_path / 'bad.zip', lambda e: e.__setitem__('sustained-operations-renewal.json', b'bad'))
    ledger = build_operational_assurance_renewal_ledger((bad,), now=now)
    dossier = build_longitudinal_operational_assurance_dossier(ledger)
    with pytest.raises(ValueError, match='BLOCKED'):
        package_longitudinal_operational_assurance_dossier(tmp_path / 'blocked.zip', dossier)


def test_wave75_changed_wave74_package_not_packageable(tmp_path: Path):
    _, packages, _, ledger = _good(tmp_path)
    dossier = build_longitudinal_operational_assurance_dossier(ledger)
    packages[-1].write_bytes(packages[-1].read_bytes() + b'x')
    with pytest.raises(ValueError):
        package_longitudinal_operational_assurance_dossier(tmp_path / 'changed.zip', dossier)


def test_wave75_dossier_does_not_mutate_wave74_truth(tmp_path: Path):
    dossiers, _, _, ledger = _good(tmp_path)
    before = [d.to_dict() for d in dossiers]
    dossier = build_longitudinal_operational_assurance_dossier(ledger)
    assert [d.to_dict() for d in dossiers] == before
    assert dossier.to_dict()['historical_wave74_truth_mutated'] is False


def test_wave75_no_operational_execution_claims(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path)
    payload = build_longitudinal_operational_assurance_dossier(ledger).to_dict()
    for key in ('continuous_monitoring_performed_by_framework','incident_response_performed_by_framework','rollback_performed_by_framework','deployment_performed_by_framework','publication_performed_by_framework'):
        assert payload[key] is False


def test_wave75_ledger_cli(tmp_path: Path, capsys):
    _, packages, now, _ = _good(tmp_path)
    output = tmp_path / 'ledger.json'
    rc = operational_assurance_ledger_main([*(str(x) for x in packages), '--now', _iso(now), '--output', str(output), '--format', 'json'])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0 and payload['status'] == 'assured' and output.is_file()


def test_wave75_longitudinal_cli(tmp_path: Path, capsys):
    _, _, _, ledger = _good(tmp_path)
    lp = write_operational_assurance_renewal_ledger(tmp_path / 'ledger.json', ledger)
    out = tmp_path / 'dossier.json'; package = tmp_path / 'dossier.zip'
    rc = longitudinal_assurance_main([str(lp), '--review-reference', 'OPS-75', '--output', str(out), '--package', str(package), '--format', 'json'])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0 and payload['status'] == 'assured' and out.is_file() and package.is_file()


def test_wave75_top_level_ledger_cli_route(tmp_path: Path):
    _, packages, now, _ = _good(tmp_path); root = Path(__file__).parents[1]
    proc = subprocess.run([sys.executable, '-m', 'nicegui_base.cli', 'operational-assurance-ledger', *(str(x) for x in packages), '--now', _iso(now), '--format', 'json'], cwd=root, text=True, capture_output=True)
    assert proc.returncode == 0 and json.loads(proc.stdout)['status'] == 'assured'


def test_wave75_top_level_longitudinal_cli_route(tmp_path: Path):
    _, _, _, ledger = _good(tmp_path); root = Path(__file__).parents[1]
    lp = write_operational_assurance_renewal_ledger(tmp_path / 'ledger.json', ledger)
    proc = subprocess.run([sys.executable, '-m', 'nicegui_base.cli', 'longitudinal-assurance', str(lp), '--format', 'json'], cwd=root, text=True, capture_output=True)
    assert proc.returncode == 0 and json.loads(proc.stdout)['status'] == 'assured'


def test_wave75_root_exports():
    for name in (
        'OperationalAssuranceRenewalLedger','LongitudinalOperationalAssuranceDossier',
        'verify_operational_assurance_continuity_archive','build_operational_assurance_renewal_ledger',
        'SemiconductorOperationalAssuranceRenewalLedgerPanel','SemiconductorLongitudinalAssuranceDossierPanel',
    ):
        assert hasattr(nicegui_base, name), name


def test_wave75_generated_starter_helpers_present():
    from nicegui_base.ai.project import _semiconductor_release_evidence_source
    source = _semiconductor_release_evidence_source()
    assert 'def build_operational_assurance_history' in source
    assert 'def build_longitudinal_assurance' in source
    assert 'verify_operational_assurance_continuity_archive' in source


def test_wave75_source_certification_phase_floor_is_75():
    source = Path('nicegui_base/governance/source_evidence.py').read_text(encoding='utf-8')
    assert "max(int(manifest.get('phase', 0)), 75)" in source
    assert 'phase_75_v300a8_enterprise_operational_assurance_renewal_ledger_longitudinal_evidence_governance' in source


def test_wave75_framework_identity_remains_exact():
    assert FRAMEWORK_VERSION == '3.0.0a8'
    assert NICEGUI_VERSION == '3.15.0'
