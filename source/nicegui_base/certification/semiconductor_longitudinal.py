from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

from .semiconductor_continuity import (
    OperationalAssuranceContinuityDossier,
    OperationalAssuranceContinuityStatus,
    SustainedOperationsEvidenceRenewal,
    operational_assurance_continuity_dossier_from_dict,
    sustained_operations_evidence_renewal_from_dict,
    verify_incident_rollback_audit_archive,
)
from .semiconductor_evidence import TargetEvidenceArtifact, capture_target_evidence_artifact


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _parse_time(value: str) -> datetime:
    text = value.strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _moment(now: datetime | str | None) -> datetime:
    if isinstance(now, str):
        return _parse_time(now)
    if isinstance(now, datetime):
        return now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    info.date_time = (1980, 1, 1, 0, 0, 0)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def _parse_manifest(raw: bytes) -> dict[str, str]:
    expected: dict[str, str] = {}
    for line in raw.decode('utf-8').splitlines():
        if not line.strip():
            continue
        sha, sep, name = line.partition('  ')
        if not sep or len(sha) != 64 or not name:
            raise ValueError(f'invalid MANIFEST.sha256 line: {line!r}')
        if name in expected:
            raise ValueError(f'duplicate MANIFEST.sha256 entry: {name!r}')
        expected[name] = sha
    return expected


class OperationalAssuranceContinuityArchiveStatus(str, Enum):
    VERIFIED = 'verified'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class OperationalAssuranceContinuityArchiveFinding:
    code: str
    status: OperationalAssuranceContinuityArchiveStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('continuity archive finding code and message must not be empty')
        object.__setattr__(self, 'status', OperationalAssuranceContinuityArchiveStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class OperationalAssuranceContinuityArchiveVerification:
    path: str
    sha256: str | None
    status: OperationalAssuranceContinuityArchiveStatus
    continuity_id: str | None = None
    renewal_id: str | None = None
    audit_id: str | None = None
    acceptance_id: str | None = None
    target_version: str | None = None
    framework_version: str | None = None
    nicegui_required: str | None = None
    evidence_captured_at: str | None = None
    coverage_expires_at: str | None = None
    continuity_status: str | None = None
    entries: tuple[str, ...] = ()
    findings: tuple[OperationalAssuranceContinuityArchiveFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.sha256 is not None and (len(self.sha256) != 64 or any(ch not in '0123456789abcdef' for ch in self.sha256.lower())):
            raise ValueError('continuity archive sha256 must be 64 hex characters when present')
        object.__setattr__(self, 'status', OperationalAssuranceContinuityArchiveStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def verified(self) -> bool:
        return self.status is OperationalAssuranceContinuityArchiveStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': self.path, 'sha256': self.sha256, 'status': self.status.value, 'verified': self.verified,
            'continuity_id': self.continuity_id, 'renewal_id': self.renewal_id, 'audit_id': self.audit_id,
            'acceptance_id': self.acceptance_id, 'target_version': self.target_version,
            'framework_version': self.framework_version, 'nicegui_required': self.nicegui_required,
            'evidence_captured_at': self.evidence_captured_at, 'coverage_expires_at': self.coverage_expires_at,
            'continuity_status': self.continuity_status, 'entries': self.entries,
            'findings': [item.to_dict() for item in self.findings],
        }


def _archive_result(path: str | Path, status: OperationalAssuranceContinuityArchiveStatus, code: str, message: str, remediation: str, *, sha256: str | None = None, entries: Sequence[str] = ()) -> OperationalAssuranceContinuityArchiveVerification:
    return OperationalAssuranceContinuityArchiveVerification(
        str(path), sha256, status, entries=tuple(entries),
        findings=(OperationalAssuranceContinuityArchiveFinding(code, status, message, remediation),),
    )


def verify_operational_assurance_continuity_archive(
    path: str | Path, *, expected_dossier: OperationalAssuranceContinuityDossier | None = None,
) -> OperationalAssuranceContinuityArchiveVerification:
    target = Path(path)
    if not target.is_file():
        return _archive_result(
            target, OperationalAssuranceContinuityArchiveStatus.PENDING,
            'continuity_archive_missing', 'The Wave 74 operational-assurance continuity ZIP is unavailable.',
            'Provide the exact immutable Wave 74 continuity package for this renewal period.',
        )
    data = target.read_bytes()
    archive_sha = hashlib.sha256(data).hexdigest()
    try:
        with zipfile.ZipFile(target) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if len(names) != len(set(names)):
                return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_duplicate_entry', 'The Wave 74 ZIP contains duplicate entries.', 'Reject it and recreate the canonical Wave 74 package.', sha256=archive_sha, entries=names)
            for name in names:
                pure = PurePosixPath(name)
                if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                    return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_unsafe_entry', f'The Wave 74 ZIP contains unsafe entry {name!r}.', 'Reject the archive and recreate it with the canonical packager.', sha256=archive_sha, entries=names)
            required = {'operational-assurance-continuity.json', 'sustained-operations-renewal.json', 'wave73/incident-rollback-audit.zip', 'MANIFEST.sha256'}
            missing = sorted(required - set(names))
            if missing:
                return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_required_entry_missing', f'The Wave 74 ZIP is missing required entries: {missing}.', 'Recreate the complete self-contained Wave 74 package.', sha256=archive_sha, entries=names)
            expected_hashes = _parse_manifest(archive.read('MANIFEST.sha256'))
            payload_names = set(names) - {'MANIFEST.sha256'}
            if set(expected_hashes) != payload_names:
                return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_manifest_incomplete', 'MANIFEST.sha256 does not cover exactly every non-manifest entry.', 'Recreate the Wave 74 package with complete deterministic hashing.', sha256=archive_sha, entries=names)
            for name, expected_sha in expected_hashes.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected_sha:
                    return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_hash_mismatch', f'Wave 74 archive entry {name!r} does not match MANIFEST.sha256.', 'Reject the changed archive and restore the exact Wave 74 package.', sha256=archive_sha, entries=names)
            dossier_payload = json.loads(archive.read('operational-assurance-continuity.json'))
            renewal_payload = json.loads(archive.read('sustained-operations-renewal.json'))
            if not isinstance(dossier_payload, Mapping) or not isinstance(renewal_payload, Mapping):
                return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_payload_invalid', 'Wave 74 continuity/renewal entries must contain JSON objects.', 'Recreate the canonical Wave 74 package.', sha256=archive_sha, entries=names)
            dossier = operational_assurance_continuity_dossier_from_dict(dossier_payload)
            renewal = sustained_operations_evidence_renewal_from_dict(renewal_payload)
            if dossier.renewal.renewal_id != renewal.renewal_id:
                return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_renewal_identity_mismatch', 'The embedded renewal identity does not match the continuity dossier.', 'Reject the contradictory Wave 74 package.', sha256=archive_sha, entries=names)
            if expected_dossier is not None and dossier.continuity_id != expected_dossier.continuity_id:
                return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_subject_mismatch', 'The Wave 74 package belongs to a different continuity dossier.', 'Provide the exact package for the expected continuity identity.', sha256=archive_sha, entries=names)
            embedded_wave73 = archive.read('wave73/incident-rollback-audit.zip')
            if len(embedded_wave73) != dossier.audit_archive.size_bytes or hashlib.sha256(embedded_wave73).hexdigest() != dossier.audit_archive.sha256:
                return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_wave73_hash_mismatch', 'The nested Wave 73 audit ZIP does not match the dossier artifact identity.', 'Reject the changed nested chain and restore the canonical Wave 74 package.', sha256=archive_sha, entries=names)
            with tempfile.NamedTemporaryFile(suffix='.zip') as tmp:
                tmp.write(embedded_wave73); tmp.flush()
                nested = verify_incident_rollback_audit_archive(tmp.name, expected_closure=dossier.closure)
            if not nested.verified:
                return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_wave73_reverification_failed', 'The nested Wave 73 audit package failed independent reverification.', 'Restore the exact verified Wave 73 package and recreate Wave 74.', sha256=archive_sha, entries=names)
            if renewal.framework_version != FRAMEWORK_VERSION or renewal.nicegui_required != NICEGUI_VERSION:
                return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_runtime_identity_mismatch', 'Wave 74 renewal framework/NiceGUI identity does not match this framework.', 'Use evidence captured for this exact framework and required NiceGUI runtime.', sha256=archive_sha, entries=names)
            if renewal.target_version != dossier.policy.target_version or renewal.target_version != dossier.closure.policy.target_version:
                return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_target_identity_mismatch', 'Wave 74 target-release identity is contradictory.', 'Use a single exact target-release identity across the renewal chain.', sha256=archive_sha, entries=names)
            expires_at = None
            if renewal.evidence_captured_at:
                try:
                    expires_at = _iso(_parse_time(renewal.evidence_captured_at) + timedelta(hours=renewal.policy.max_age_hours))
                except Exception:
                    return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_capture_time_invalid', 'Wave 74 renewal capture time is invalid.', 'Recreate renewal evidence with an authoritative capture timestamp.', sha256=archive_sha, entries=names)
            return OperationalAssuranceContinuityArchiveVerification(
                str(target), archive_sha, OperationalAssuranceContinuityArchiveStatus.VERIFIED,
                dossier.continuity_id, renewal.renewal_id, dossier.closure.audit_id,
                dossier.closure.sustained_operations_acceptance.acceptance_id, renewal.target_version,
                renewal.framework_version, renewal.nicegui_required, renewal.evidence_captured_at, expires_at,
                dossier.status.value, tuple(names), (),
            )
    except (OSError, zipfile.BadZipFile, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return _archive_result(target, OperationalAssuranceContinuityArchiveStatus.BLOCKED, 'continuity_archive_invalid', f'The Wave 74 continuity package cannot be verified: {exc}', 'Reject the invalid archive and recreate it with the canonical Wave 74 packager.', sha256=archive_sha)


class OperationalAssuranceLedgerStatus(str, Enum):
    ASSURED = 'assured'
    EXPIRING = 'expiring'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class OperationalAssuranceRenewalLedgerPolicy:
    key: str = 'stable'
    target_version: str = '3.0.0'
    max_gap_hours: float = 0.0
    expiring_within_hours: float = 24.0
    max_future_skew_minutes: float = 5.0
    max_overlap_hours: float | None = None
    require_verified_wave74_packages: bool = True
    require_unique_renewal_ids: bool = True
    require_unique_continuity_ids: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.target_version.strip():
            raise ValueError('renewal ledger policy requires key and target version')
        if self.max_gap_hours < 0 or self.expiring_within_hours < 0 or self.max_future_skew_minutes < 0:
            raise ValueError('renewal ledger policy time limits must be non-negative')
        if self.max_overlap_hours is not None and self.max_overlap_hours < 0:
            raise ValueError('renewal ledger max_overlap_hours must be non-negative when configured')

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key, 'target_version': self.target_version, 'max_gap_hours': self.max_gap_hours,
            'expiring_within_hours': self.expiring_within_hours, 'max_future_skew_minutes': self.max_future_skew_minutes,
            'max_overlap_hours': self.max_overlap_hours, 'require_verified_wave74_packages': self.require_verified_wave74_packages,
            'require_unique_renewal_ids': self.require_unique_renewal_ids, 'require_unique_continuity_ids': self.require_unique_continuity_ids,
        }


OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICY = OperationalAssuranceRenewalLedgerPolicy()
OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICIES: Mapping[str, OperationalAssuranceRenewalLedgerPolicy] = MappingProxyType({'stable': OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICY})


@dataclass(frozen=True, slots=True)
class OperationalAssuranceRenewalLedgerFinding:
    code: str
    status: OperationalAssuranceLedgerStatus
    message: str
    remediation: str = ''
    related_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('renewal ledger finding code and message must not be empty')
        object.__setattr__(self, 'status', OperationalAssuranceLedgerStatus(self.status))
        object.__setattr__(self, 'related_ids', tuple(self.related_ids))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation, 'related_ids': self.related_ids}


@dataclass(frozen=True, slots=True)
class OperationalAssuranceRenewalLedgerEntry:
    entry_id: str
    package: TargetEvidenceArtifact
    continuity_id: str
    renewal_id: str
    audit_id: str
    acceptance_id: str
    target_version: str
    framework_version: str
    nicegui_required: str
    evidence_captured_at: str
    coverage_expires_at: str
    continuity_status: OperationalAssuranceContinuityStatus

    def __post_init__(self) -> None:
        if any(len(value) != 64 for value in (self.entry_id, self.continuity_id, self.renewal_id, self.audit_id, self.acceptance_id, self.package.sha256)):
            raise ValueError('renewal ledger entry requires sha256-bound identities')
        object.__setattr__(self, 'continuity_status', OperationalAssuranceContinuityStatus(self.continuity_status))

    def to_dict(self) -> dict[str, Any]:
        return {
            'entry_id': self.entry_id, 'package': self.package.to_dict(), 'continuity_id': self.continuity_id,
            'renewal_id': self.renewal_id, 'audit_id': self.audit_id, 'acceptance_id': self.acceptance_id,
            'target_version': self.target_version, 'framework_version': self.framework_version,
            'nicegui_required': self.nicegui_required, 'evidence_captured_at': self.evidence_captured_at,
            'coverage_expires_at': self.coverage_expires_at, 'continuity_status': self.continuity_status.value,
        }


def _entry_identity_payload(verification: OperationalAssuranceContinuityArchiveVerification, artifact: TargetEvidenceArtifact) -> dict[str, Any]:
    return {
        'package': artifact.to_dict(), 'continuity_id': verification.continuity_id, 'renewal_id': verification.renewal_id,
        'audit_id': verification.audit_id, 'acceptance_id': verification.acceptance_id, 'target_version': verification.target_version,
        'framework_version': verification.framework_version, 'nicegui_required': verification.nicegui_required,
        'evidence_captured_at': verification.evidence_captured_at, 'coverage_expires_at': verification.coverage_expires_at,
        'continuity_status': verification.continuity_status,
    }


def _entry_from_verification(verification: OperationalAssuranceContinuityArchiveVerification) -> OperationalAssuranceRenewalLedgerEntry:
    if not verification.verified or verification.sha256 is None:
        raise ValueError('only verified Wave 74 continuity archives can become ledger entries')
    required = (
        verification.continuity_id, verification.renewal_id, verification.audit_id, verification.acceptance_id,
        verification.target_version, verification.framework_version, verification.nicegui_required,
        verification.evidence_captured_at, verification.coverage_expires_at, verification.continuity_status,
    )
    if any(value is None for value in required):
        raise ValueError('verified Wave 74 archive is missing ledger identity fields')
    artifact = capture_target_evidence_artifact(verification.path, key='wave74-operational-assurance-continuity-package', description='immutable Wave 74 operational-assurance continuity package')
    payload = _entry_identity_payload(verification, artifact)
    return OperationalAssuranceRenewalLedgerEntry(
        _canonical_digest(payload), artifact, str(verification.continuity_id), str(verification.renewal_id), str(verification.audit_id),
        str(verification.acceptance_id), str(verification.target_version), str(verification.framework_version), str(verification.nicegui_required),
        str(verification.evidence_captured_at), str(verification.coverage_expires_at), OperationalAssuranceContinuityStatus(str(verification.continuity_status)),
    )


@dataclass(frozen=True, slots=True)
class OperationalAssuranceRenewalLedger:
    ledger_id: str
    entries: tuple[OperationalAssuranceRenewalLedgerEntry, ...]
    source_paths: tuple[str, ...]
    policy: OperationalAssuranceRenewalLedgerPolicy
    findings: tuple[OperationalAssuranceRenewalLedgerFinding, ...]
    assessed_at: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.ledger_id) != 64:
            raise ValueError('renewal ledger requires sha256 id')
        object.__setattr__(self, 'entries', tuple(self.entries))
        object.__setattr__(self, 'source_paths', tuple(self.source_paths))
        object.__setattr__(self, 'findings', tuple(self.findings))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def status(self) -> OperationalAssuranceLedgerStatus:
        if any(item.status is OperationalAssuranceLedgerStatus.BLOCKED for item in self.findings):
            return OperationalAssuranceLedgerStatus.BLOCKED
        if any(item.status is OperationalAssuranceLedgerStatus.PENDING for item in self.findings):
            return OperationalAssuranceLedgerStatus.PENDING
        if any(item.status is OperationalAssuranceLedgerStatus.EXPIRING for item in self.findings):
            return OperationalAssuranceLedgerStatus.EXPIRING
        return OperationalAssuranceLedgerStatus.ASSURED

    @property
    def next_actions(self) -> tuple[str, ...]:
        actions = tuple(dict.fromkeys(item.remediation for item in self.findings if item.remediation))
        return actions or ('Retain the immutable Wave 74 renewal packages and renew external evidence before the active coverage window expires.',)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'ledger_id': self.ledger_id, 'status': self.status.value,
            'entries': [item.to_dict() for item in self.entries], 'source_paths': self.source_paths,
            'policy': self.policy.to_dict(), 'findings': [item.to_dict() for item in self.findings],
            'assessed_at': self.assessed_at, 'metadata': dict(self.metadata), 'next_actions': self.next_actions,
            'historical_wave74_truth_mutated': False, 'continuous_monitoring_performed_by_framework': False,
            'incident_response_performed_by_framework': False, 'rollback_performed_by_framework': False,
            'deployment_performed_by_framework': False, 'publication_performed_by_framework': False,
            'records_external_artifacts_only': True,
        }


def _ledger_identity_payload(entries: Sequence[OperationalAssuranceRenewalLedgerEntry], source_paths: Sequence[str], policy: OperationalAssuranceRenewalLedgerPolicy, findings: Sequence[OperationalAssuranceRenewalLedgerFinding], assessed_at: str, metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {
        'entries': [item.to_dict() for item in entries], 'source_paths': tuple(source_paths), 'policy': policy.to_dict(),
        'findings': [item.to_dict() for item in findings], 'assessed_at': assessed_at, 'metadata': dict(metadata),
    }


def build_operational_assurance_renewal_ledger(
    continuity_packages: Sequence[str | Path], *, policy: OperationalAssuranceRenewalLedgerPolicy = OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICY,
    now: datetime | str | None = None, metadata: Mapping[str, Any] | None = None,
) -> OperationalAssuranceRenewalLedger:
    moment = _moment(now)
    assessed_at = _iso(moment)
    source_paths = tuple(str(Path(item)) for item in continuity_packages)
    findings: list[OperationalAssuranceRenewalLedgerFinding] = []
    entries: list[OperationalAssuranceRenewalLedgerEntry] = []
    for raw in continuity_packages:
        verification = verify_operational_assurance_continuity_archive(raw)
        if verification.status is OperationalAssuranceContinuityArchiveStatus.PENDING:
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_source_missing', OperationalAssuranceLedgerStatus.PENDING, f'Wave 74 renewal package is missing: {raw}.', 'Supply the missing immutable Wave 74 continuity package.'))
            continue
        if verification.status is OperationalAssuranceContinuityArchiveStatus.BLOCKED:
            message = verification.findings[0].message if verification.findings else f'Wave 74 renewal package is blocked: {raw}.'
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_source_blocked', OperationalAssuranceLedgerStatus.BLOCKED, message, 'Replace the corrupt, unsafe, tampered, or identity-mismatched Wave 74 package.'))
            continue
        entry = _entry_from_verification(verification)
        entries.append(entry)

    entries.sort(key=lambda item: (_parse_time(item.evidence_captured_at), item.renewal_id, item.package.sha256))
    if not entries:
        findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_no_verified_periods', OperationalAssuranceLedgerStatus.PENDING, 'No verified Wave 74 renewal period is available for longitudinal assurance.', 'Provide at least one verified Wave 74 operational-assurance continuity package.'))

    continuity_seen: dict[str, str] = {}
    renewal_seen: dict[str, str] = {}
    capture_seen: dict[str, str] = {}
    for entry in entries:
        if entry.target_version != policy.target_version:
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_target_identity_drift', OperationalAssuranceLedgerStatus.BLOCKED, f'Renewal {entry.renewal_id[:12]} targets {entry.target_version}, expected {policy.target_version}.', 'Use one exact target release identity for this ledger.', (entry.renewal_id,)))
        if entry.framework_version != FRAMEWORK_VERSION or entry.nicegui_required != NICEGUI_VERSION:
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_runtime_identity_drift', OperationalAssuranceLedgerStatus.BLOCKED, f'Renewal {entry.renewal_id[:12]} does not match the exact framework/NiceGUI identity.', 'Use renewal packages captured for this framework and exact required NiceGUI runtime.', (entry.renewal_id,)))
        previous_sha = continuity_seen.get(entry.continuity_id)
        if previous_sha is not None:
            status = OperationalAssuranceLedgerStatus.BLOCKED if previous_sha != entry.package.sha256 else OperationalAssuranceLedgerStatus.PENDING
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_duplicate_continuity_identity', status, f'Continuity identity {entry.continuity_id[:12]} appears more than once.', 'Remove duplicate or contradictory continuity packages before longitudinal review.', (entry.continuity_id,)))
        continuity_seen[entry.continuity_id] = entry.package.sha256
        prior_continuity = renewal_seen.get(entry.renewal_id)
        if prior_continuity is not None:
            status = OperationalAssuranceLedgerStatus.BLOCKED if prior_continuity != entry.continuity_id else OperationalAssuranceLedgerStatus.PENDING
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_duplicate_renewal_identity', status, f'Renewal identity {entry.renewal_id[:12]} appears more than once.', 'Remove duplicate or contradictory renewal identities.', (entry.renewal_id,)))
        renewal_seen[entry.renewal_id] = entry.continuity_id
        prior_renewal = capture_seen.get(entry.evidence_captured_at)
        if prior_renewal is not None and prior_renewal != entry.renewal_id:
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_capture_time_contradiction', OperationalAssuranceLedgerStatus.BLOCKED, f'Different renewal identities share the exact capture timestamp {entry.evidence_captured_at}.', 'Resolve the contradictory external renewal history.', (prior_renewal, entry.renewal_id)))
        capture_seen[entry.evidence_captured_at] = entry.renewal_id
        captured = _parse_time(entry.evidence_captured_at)
        if captured - moment > timedelta(minutes=policy.max_future_skew_minutes):
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_future_capture_time', OperationalAssuranceLedgerStatus.BLOCKED, f'Renewal {entry.renewal_id[:12]} appears to come from the future.', 'Resolve the external clock/timestamp contradiction.', (entry.renewal_id,)))
        if entry.continuity_status is OperationalAssuranceContinuityStatus.BLOCKED:
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_blocked_continuity_period', OperationalAssuranceLedgerStatus.BLOCKED, f'Wave 74 continuity period {entry.continuity_id[:12]} is BLOCKED.', 'Replace the blocked period with verified external renewal evidence.', (entry.continuity_id,)))
        elif entry.continuity_status is OperationalAssuranceContinuityStatus.PENDING:
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_pending_continuity_period', OperationalAssuranceLedgerStatus.PENDING, f'Wave 74 continuity period {entry.continuity_id[:12]} is PENDING.', 'Complete the missing renewal evidence for this period.', (entry.continuity_id,)))

    for previous, current in zip(entries, entries[1:]):
        prev_expiry = _parse_time(previous.coverage_expires_at)
        current_start = _parse_time(current.evidence_captured_at)
        delta_hours = (current_start - prev_expiry).total_seconds() / 3600.0
        if delta_hours > policy.max_gap_hours:
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_coverage_gap', OperationalAssuranceLedgerStatus.PENDING, f'Coverage gap of {delta_hours:.2f} hours exists between renewals {previous.renewal_id[:12]} and {current.renewal_id[:12]}.', 'Supply a renewal period that closes the uncovered interval or apply an explicitly approved policy.', (previous.renewal_id, current.renewal_id)))
        elif delta_hours > 0:
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_tolerated_coverage_gap', OperationalAssuranceLedgerStatus.ASSURED, f'Coverage gap of {delta_hours:.2f} hours is inside the configured framework policy.', '', (previous.renewal_id, current.renewal_id)))
        elif delta_hours < 0:
            overlap = abs(delta_hours)
            status = OperationalAssuranceLedgerStatus.PENDING if policy.max_overlap_hours is not None and overlap > policy.max_overlap_hours else OperationalAssuranceLedgerStatus.ASSURED
            remediation = 'Review the overlapping external renewal intervals against the configured governance policy.' if status is OperationalAssuranceLedgerStatus.PENDING else ''
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_coverage_overlap', status, f'Renewal windows overlap by {overlap:.2f} hours.', remediation, (previous.renewal_id, current.renewal_id)))
        if prev_expiry < moment and current_start <= prev_expiry:
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_historical_stale_interval_covered', OperationalAssuranceLedgerStatus.ASSURED, f'Historical renewal {previous.renewal_id[:12]} is expired now but was renewed without an uncovered interval.', '', (previous.renewal_id, current.renewal_id)))

    if entries:
        latest = entries[-1]
        expiry = _parse_time(latest.coverage_expires_at)
        remaining_hours = (expiry - moment).total_seconds() / 3600.0
        if remaining_hours < 0:
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_active_window_stale', OperationalAssuranceLedgerStatus.PENDING, f'The latest renewal coverage expired {-remaining_hours:.2f} hours ago.', 'Capture and verify a fresh external sustained-operations renewal package.', (latest.renewal_id,)))
        elif remaining_hours <= policy.expiring_within_hours:
            findings.append(OperationalAssuranceRenewalLedgerFinding('ledger_active_window_expiring', OperationalAssuranceLedgerStatus.EXPIRING, f'The latest renewal coverage expires in {remaining_hours:.2f} hours.', 'Capture the next external renewal evidence before the active coverage window expires.', (latest.renewal_id,)))
    values = dict(metadata or {})
    payload = _ledger_identity_payload(entries, source_paths, policy, findings, assessed_at, values)
    return OperationalAssuranceRenewalLedger(_canonical_digest(payload), tuple(entries), source_paths, policy, tuple(findings), assessed_at, values)


def _artifact_from_dict(payload: Mapping[str, Any]) -> TargetEvidenceArtifact:
    return TargetEvidenceArtifact(str(payload['key']), str(payload['path']), str(payload['sha256']), int(payload['size_bytes']), str(payload.get('description', '')))


def operational_assurance_renewal_ledger_from_dict(payload: Mapping[str, Any]) -> OperationalAssuranceRenewalLedger:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported operational assurance renewal ledger schema {payload.get("schema_version")!r}')
    policy_payload = payload.get('policy') or {}
    policy = OperationalAssuranceRenewalLedgerPolicy(
        str(policy_payload.get('key', 'stable')), str(policy_payload.get('target_version', '3.0.0')),
        float(policy_payload.get('max_gap_hours', 0.0)), float(policy_payload.get('expiring_within_hours', 24.0)),
        float(policy_payload.get('max_future_skew_minutes', 5.0)),
        None if policy_payload.get('max_overlap_hours') is None else float(policy_payload.get('max_overlap_hours')),
        bool(policy_payload.get('require_verified_wave74_packages', True)), bool(policy_payload.get('require_unique_renewal_ids', True)),
        bool(policy_payload.get('require_unique_continuity_ids', True)),
    )
    entries: list[OperationalAssuranceRenewalLedgerEntry] = []
    for item in payload.get('entries', ()):
        if not isinstance(item, Mapping) or not isinstance(item.get('package'), Mapping):
            raise TypeError('renewal ledger entries must contain package objects')
        entries.append(OperationalAssuranceRenewalLedgerEntry(
            str(item['entry_id']), _artifact_from_dict(item['package']), str(item['continuity_id']), str(item['renewal_id']),
            str(item['audit_id']), str(item['acceptance_id']), str(item['target_version']), str(item['framework_version']),
            str(item['nicegui_required']), str(item['evidence_captured_at']), str(item['coverage_expires_at']),
            OperationalAssuranceContinuityStatus(str(item['continuity_status'])),
        ))
    findings = tuple(
        OperationalAssuranceRenewalLedgerFinding(str(item['code']), OperationalAssuranceLedgerStatus(str(item['status'])), str(item['message']), str(item.get('remediation', '')), tuple(str(v) for v in item.get('related_ids', ())))
        for item in payload.get('findings', ()) if isinstance(item, Mapping)
    )
    obj = OperationalAssuranceRenewalLedger(
        str(payload['ledger_id']), tuple(entries), tuple(str(item) for item in payload.get('source_paths', ())), policy,
        findings, str(payload['assessed_at']), dict(payload.get('metadata') or {}),
    )
    expected = _canonical_digest(_ledger_identity_payload(obj.entries, obj.source_paths, obj.policy, obj.findings, obj.assessed_at, obj.metadata))
    if obj.ledger_id != expected:
        raise ValueError('operational assurance renewal ledger id does not match persisted content')
    if payload.get('status') is not None and str(payload['status']) != obj.status.value:
        raise ValueError('operational assurance renewal ledger status does not match persisted content')
    return obj


def write_operational_assurance_renewal_ledger(path: str | Path, ledger: OperationalAssuranceRenewalLedger) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(ledger.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_operational_assurance_renewal_ledger(path: str | Path) -> OperationalAssuranceRenewalLedger:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('operational assurance renewal ledger JSON must contain an object')
    return operational_assurance_renewal_ledger_from_dict(payload)


def verify_operational_assurance_renewal_ledger(ledger: OperationalAssuranceRenewalLedger, *, now: datetime | str | None = None) -> OperationalAssuranceRenewalLedger:
    refreshed = build_operational_assurance_renewal_ledger(ledger.source_paths, policy=ledger.policy, now=now or ledger.assessed_at, metadata=ledger.metadata)
    expected_by_path = {str(Path(item.package.path)): item.package.sha256 for item in ledger.entries}
    changed = []
    for raw_path, expected_sha in expected_by_path.items():
        path = Path(raw_path)
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
            changed.append(raw_path)
    if not changed:
        return refreshed
    findings = list(refreshed.findings)
    for raw_path in changed:
        findings.append(OperationalAssuranceRenewalLedgerFinding(
            'ledger_bound_package_hash_changed', OperationalAssuranceLedgerStatus.BLOCKED,
            f'A Wave 74 package changed after it was bound into the ledger: {raw_path}.',
            'Restore the exact immutable Wave 74 package or construct a new ledger from newly accepted evidence.',
        ))
    payload = _ledger_identity_payload(refreshed.entries, refreshed.source_paths, refreshed.policy, findings, refreshed.assessed_at, refreshed.metadata)
    return OperationalAssuranceRenewalLedger(_canonical_digest(payload), refreshed.entries, refreshed.source_paths, refreshed.policy, tuple(findings), refreshed.assessed_at, refreshed.metadata)


@dataclass(frozen=True, slots=True)
class LongitudinalOperationalAssuranceDossier:
    dossier_id: str
    ledger: OperationalAssuranceRenewalLedger
    review_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.dossier_id) != 64:
            raise ValueError('longitudinal assurance dossier requires sha256 id')
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def status(self) -> OperationalAssuranceLedgerStatus:
        return self.ledger.status

    @property
    def next_actions(self) -> tuple[str, ...]:
        return self.ledger.next_actions

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'dossier_id': self.dossier_id, 'status': self.status.value, 'ledger': self.ledger.to_dict(),
            'review_reference': self.review_reference, 'metadata': dict(self.metadata), 'generated_at': self.generated_at,
            'next_actions': self.next_actions, 'longitudinal_assurance_is_documentary_evidence_only': True,
            'historical_wave74_truth_mutated': False, 'continuous_monitoring_performed_by_framework': False,
            'incident_response_performed_by_framework': False, 'rollback_performed_by_framework': False,
            'deployment_performed_by_framework': False, 'publication_performed_by_framework': False,
        }


def _dossier_identity_payload(ledger: OperationalAssuranceRenewalLedger, review_reference: str | None, metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {'ledger_id': ledger.ledger_id, 'review_reference': review_reference, 'metadata': dict(metadata)}


def build_longitudinal_operational_assurance_dossier(
    ledger: OperationalAssuranceRenewalLedger, *, now: datetime | str | None = None, review_reference: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> LongitudinalOperationalAssuranceDossier:
    refreshed = verify_operational_assurance_renewal_ledger(ledger, now=now or ledger.assessed_at)
    values = dict(metadata or {})
    payload = _dossier_identity_payload(refreshed, review_reference, values)
    return LongitudinalOperationalAssuranceDossier(_canonical_digest(payload), refreshed, review_reference, values)


def longitudinal_operational_assurance_dossier_from_dict(payload: Mapping[str, Any]) -> LongitudinalOperationalAssuranceDossier:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported longitudinal assurance dossier schema {payload.get("schema_version")!r}')
    ledger_payload = payload.get('ledger')
    if not isinstance(ledger_payload, Mapping):
        raise TypeError('longitudinal assurance dossier requires a ledger object')
    ledger = operational_assurance_renewal_ledger_from_dict(ledger_payload)
    obj = LongitudinalOperationalAssuranceDossier(
        str(payload['dossier_id']), ledger, None if payload.get('review_reference') is None else str(payload.get('review_reference')),
        dict(payload.get('metadata') or {}), str(payload.get('generated_at') or _utc_now()),
    )
    expected = _canonical_digest(_dossier_identity_payload(obj.ledger, obj.review_reference, obj.metadata))
    if obj.dossier_id != expected:
        raise ValueError('longitudinal assurance dossier id does not match persisted content')
    if payload.get('status') is not None and str(payload['status']) != obj.status.value:
        raise ValueError('longitudinal assurance dossier status does not match persisted content')
    return obj


def write_longitudinal_operational_assurance_dossier(path: str | Path, dossier: LongitudinalOperationalAssuranceDossier) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dossier.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_longitudinal_operational_assurance_dossier(path: str | Path) -> LongitudinalOperationalAssuranceDossier:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('longitudinal assurance dossier JSON must contain an object')
    return longitudinal_operational_assurance_dossier_from_dict(payload)


@dataclass(frozen=True, slots=True)
class LongitudinalOperationalAssurancePackage:
    path: str
    sha256: str
    dossier_id: str
    ledger_id: str
    status: OperationalAssuranceLedgerStatus
    entries: tuple[str, ...]

    def __post_init__(self) -> None:
        if any(len(value) != 64 for value in (self.sha256, self.dossier_id, self.ledger_id)):
            raise ValueError('longitudinal assurance package requires sha256 package/dossier/ledger identifiers')
        object.__setattr__(self, 'status', OperationalAssuranceLedgerStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))

    def to_dict(self) -> dict[str, Any]:
        return {'path': self.path, 'sha256': self.sha256, 'dossier_id': self.dossier_id, 'ledger_id': self.ledger_id, 'status': self.status.value, 'entries': self.entries}


def package_longitudinal_operational_assurance_dossier(
    path: str | Path, dossier: LongitudinalOperationalAssuranceDossier, *, now: datetime | str | None = None,
) -> LongitudinalOperationalAssurancePackage:
    refreshed = build_longitudinal_operational_assurance_dossier(
        dossier.ledger, now=now or dossier.ledger.assessed_at, review_reference=dossier.review_reference, metadata=dossier.metadata,
    )
    if refreshed.status is OperationalAssuranceLedgerStatus.BLOCKED:
        raise ValueError('longitudinal assurance package cannot be created from BLOCKED or changed evidence')
    if refreshed.dossier_id != dossier.dossier_id:
        raise ValueError('longitudinal assurance identity changed during package verification')
    entries: dict[str, bytes] = {
        'longitudinal-operational-assurance.json': _json_bytes(refreshed.to_dict()),
        'operational-assurance-renewal-ledger.json': _json_bytes(refreshed.ledger.to_dict()),
    }
    for index, entry in enumerate(refreshed.ledger.entries, start=1):
        source = Path(entry.package.path)
        if not source.is_file():
            raise ValueError(f'Wave 74 continuity package is missing: {source}')
        blob = source.read_bytes()
        if len(blob) != entry.package.size_bytes or hashlib.sha256(blob).hexdigest() != entry.package.sha256:
            raise ValueError(f'Wave 74 continuity package changed: {source}')
        name = f'wave74/{index:04d}-{entry.continuity_id[:16]}.zip'
        entries[name] = blob
    manifest = ''.join(f'{hashlib.sha256(entries[name]).hexdigest()}  {name}\n' for name in sorted(entries))
    entries['MANIFEST.sha256'] = manifest.encode('utf-8')
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w') as archive:
        for name in sorted(entries):
            pure = PurePosixPath(name)
            if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                raise ValueError(f'unsafe longitudinal assurance archive entry {name!r}')
            archive.writestr(_zip_info(name), entries[name])
    return LongitudinalOperationalAssurancePackage(
        str(target), hashlib.sha256(target.read_bytes()).hexdigest(), refreshed.dossier_id, refreshed.ledger.ledger_id,
        refreshed.status, tuple(sorted(entries)),
    )


__all__ = [
    'LongitudinalOperationalAssuranceDossier','LongitudinalOperationalAssurancePackage',
    'OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICIES','OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICY',
    'OperationalAssuranceContinuityArchiveFinding','OperationalAssuranceContinuityArchiveStatus','OperationalAssuranceContinuityArchiveVerification',
    'OperationalAssuranceLedgerStatus','OperationalAssuranceRenewalLedger','OperationalAssuranceRenewalLedgerEntry',
    'OperationalAssuranceRenewalLedgerFinding','OperationalAssuranceRenewalLedgerPolicy',
    'build_longitudinal_operational_assurance_dossier','build_operational_assurance_renewal_ledger',
    'longitudinal_operational_assurance_dossier_from_dict','operational_assurance_renewal_ledger_from_dict',
    'package_longitudinal_operational_assurance_dossier','read_longitudinal_operational_assurance_dossier',
    'read_operational_assurance_renewal_ledger','verify_operational_assurance_continuity_archive',
    'verify_operational_assurance_renewal_ledger','write_longitudinal_operational_assurance_dossier',
    'write_operational_assurance_renewal_ledger',
]
