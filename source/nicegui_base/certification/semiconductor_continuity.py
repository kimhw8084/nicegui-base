from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

from .semiconductor_evidence import TargetEvidenceArtifact, capture_target_evidence_artifact
from .semiconductor_operations import (
    IncidentRollbackAuditClosure,
    IncidentRollbackAuditStatus,
    SustainedOperationsAcceptanceStatus,
    incident_rollback_audit_closure_from_dict,
    sustained_operations_evidence_acceptance_from_dict,
)


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


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _target_artifact_from_dict(payload: Mapping[str, Any]) -> TargetEvidenceArtifact:
    return TargetEvidenceArtifact(
        str(payload['key']), str(payload['path']), str(payload['sha256']), int(payload['size_bytes']), str(payload.get('description', '')),
    )


def _resolve_artifact_path(artifact: TargetEvidenceArtifact, base_dir: str | Path | None) -> Path:
    path = Path(artifact.path)
    if path.is_absolute() or base_dir is None:
        return path
    return Path(base_dir) / path


def _safe_manifest_artifact_path(base: Path, value: str) -> Path:
    raw = Path(value)
    candidate = raw.resolve() if raw.is_absolute() else (base / raw).resolve()
    root = base.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f'Wave 74 artifact path escapes manifest base directory: {value!r}') from exc
    return candidate


def _safe_entry_component(value: str) -> str:
    text = re.sub(r'[^A-Za-z0-9._-]+', '-', value.strip()).strip('.-')
    return text or 'item'


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    info.date_time = (1980, 1, 1, 0, 0, 0)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


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


def _embedded_artifact_present(archive: zipfile.ZipFile, names: Sequence[str], prefix: str, artifact: TargetEvidenceArtifact) -> bool:
    expected_prefix = prefix.rstrip('/') + '/'
    for name in names:
        if not name.startswith(expected_prefix):
            continue
        blob = archive.read(name)
        if len(blob) == artifact.size_bytes and hashlib.sha256(blob).hexdigest() == artifact.sha256:
            return True
    return False


class IncidentRollbackAuditArchiveStatus(str, Enum):
    VERIFIED = 'verified'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class IncidentRollbackAuditArchiveFinding:
    code: str
    status: IncidentRollbackAuditArchiveStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('Wave 73 audit archive finding code and message must not be empty')
        object.__setattr__(self, 'status', IncidentRollbackAuditArchiveStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class IncidentRollbackAuditArchiveVerification:
    path: str
    sha256: str | None
    status: IncidentRollbackAuditArchiveStatus
    audit_id: str | None = None
    acceptance_id: str | None = None
    readiness_id: str | None = None
    entries: tuple[str, ...] = ()
    findings: tuple[IncidentRollbackAuditArchiveFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.sha256 is not None and (len(self.sha256) != 64 or any(ch not in '0123456789abcdef' for ch in self.sha256.lower())):
            raise ValueError('Wave 73 audit archive sha256 must be 64 hex characters when present')
        object.__setattr__(self, 'status', IncidentRollbackAuditArchiveStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def verified(self) -> bool:
        return self.status is IncidentRollbackAuditArchiveStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': self.path, 'sha256': self.sha256, 'status': self.status.value, 'verified': self.verified,
            'audit_id': self.audit_id, 'acceptance_id': self.acceptance_id, 'readiness_id': self.readiness_id,
            'entries': self.entries, 'findings': [item.to_dict() for item in self.findings],
        }


def _blocked_audit_archive(path: str | Path, code: str, message: str, remediation: str, *, sha256: str | None = None, entries: Sequence[str] = ()) -> IncidentRollbackAuditArchiveVerification:
    return IncidentRollbackAuditArchiveVerification(
        str(path), sha256, IncidentRollbackAuditArchiveStatus.BLOCKED, entries=tuple(entries),
        findings=(IncidentRollbackAuditArchiveFinding(code, IncidentRollbackAuditArchiveStatus.BLOCKED, message, remediation),),
    )


def verify_incident_rollback_audit_archive(
    path: str | Path, *, expected_closure: IncidentRollbackAuditClosure | None = None,
) -> IncidentRollbackAuditArchiveVerification:
    target = Path(path)
    if not target.is_file():
        return _blocked_audit_archive(
            target, 'incident_rollback_audit_archive_missing', 'The Wave 73 incident/rollback audit archive is unavailable.',
            'Restore the exact immutable Wave 73 audit ZIP before renewal or continuity verification.',
        )
    data = target.read_bytes()
    archive_sha = hashlib.sha256(data).hexdigest()
    try:
        with zipfile.ZipFile(target) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if len(names) != len(set(names)):
                return _blocked_audit_archive(target, 'incident_rollback_audit_archive_duplicate_entry', 'The Wave 73 ZIP contains duplicate entries.', 'Recreate it with the canonical Wave 73 packager.', sha256=archive_sha, entries=names)
            for name in names:
                pure = PurePosixPath(name)
                if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                    return _blocked_audit_archive(target, 'incident_rollback_audit_archive_unsafe_entry', f'The Wave 73 ZIP contains unsafe entry {name!r}.', 'Reject the archive and recreate it with the canonical packager.', sha256=archive_sha, entries=names)
            required = {
                'incident-rollback-audit-closure.json', 'sustained-operations-acceptance.json',
                'wave72/rollback-readiness.zip', 'MANIFEST.sha256',
            }
            missing = sorted(required - set(names))
            if missing:
                return _blocked_audit_archive(target, 'incident_rollback_audit_archive_required_entry_missing', f'The Wave 73 ZIP is missing required entries: {missing}.', 'Recreate the complete self-contained Wave 73 package.', sha256=archive_sha, entries=names)
            expected_hashes = _parse_manifest(archive.read('MANIFEST.sha256'))
            payload_names = set(names) - {'MANIFEST.sha256'}
            if set(expected_hashes) != payload_names:
                return _blocked_audit_archive(target, 'incident_rollback_audit_archive_manifest_incomplete', 'MANIFEST.sha256 does not cover exactly every non-manifest archive entry.', 'Recreate the Wave 73 package with complete deterministic hashing.', sha256=archive_sha, entries=names)
            for name, expected_sha in expected_hashes.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected_sha:
                    return _blocked_audit_archive(target, 'incident_rollback_audit_archive_hash_mismatch', f'Wave 73 archive entry {name!r} does not match MANIFEST.sha256.', 'Reject the changed archive and restore the exact Wave 73 package.', sha256=archive_sha, entries=names)
            closure_payload = json.loads(archive.read('incident-rollback-audit-closure.json'))
            acceptance_payload = json.loads(archive.read('sustained-operations-acceptance.json'))
            if not isinstance(closure_payload, Mapping) or not isinstance(acceptance_payload, Mapping):
                return _blocked_audit_archive(target, 'incident_rollback_audit_archive_payload_invalid', 'Wave 73 closure/acceptance entries must contain JSON objects.', 'Recreate the canonical Wave 73 package.', sha256=archive_sha, entries=names)
            closure = incident_rollback_audit_closure_from_dict(closure_payload)
            acceptance = sustained_operations_evidence_acceptance_from_dict(acceptance_payload)
            if closure.sustained_operations_acceptance.acceptance_id != acceptance.acceptance_id:
                return _blocked_audit_archive(target, 'incident_rollback_audit_archive_acceptance_mismatch', 'The separately embedded Wave 73 acceptance does not match the acceptance bound into the audit closure.', 'Reject the archive and recreate it from one canonical evidence chain.', sha256=archive_sha, entries=names)
            if closure.readiness_archive.sha256 != hashlib.sha256(archive.read('wave72/rollback-readiness.zip')).hexdigest():
                return _blocked_audit_archive(target, 'incident_rollback_audit_archive_wave72_hash_mismatch', 'The nested Wave 72 ZIP differs from the exact rollback-readiness package bound into Wave 73.', 'Restore the exact nested Wave 72 package and rebuild Wave 73.', sha256=archive_sha, entries=names)
            for artifact in acceptance.artifacts:
                if not _embedded_artifact_present(archive, names, 'sustained-operations-evidence', artifact):
                    return _blocked_audit_archive(target, 'incident_rollback_audit_archive_acceptance_artifact_missing', f'Wave 73 acceptance artifact {artifact.key!r} is not represented by matching bytes in the ZIP.', 'Rebuild Wave 73 with every accepted sustained-operations artifact.', sha256=archive_sha, entries=names)
            for artifact in closure.audit_artifacts:
                if not _embedded_artifact_present(archive, names, 'incident-rollback-audit-evidence', artifact):
                    return _blocked_audit_archive(target, 'incident_rollback_audit_archive_audit_artifact_missing', f'Wave 73 audit artifact {artifact.key!r} is not represented by matching bytes in the ZIP.', 'Rebuild Wave 73 with every incident/rollback audit artifact.', sha256=archive_sha, entries=names)
            if expected_closure is not None and closure.audit_id != expected_closure.audit_id:
                return _blocked_audit_archive(target, 'incident_rollback_audit_archive_subject_mismatch', 'The Wave 73 ZIP is bound to a different incident/rollback audit closure.', 'Use the exact Wave 73 archive created for the supplied closure.', sha256=archive_sha, entries=names)
            return IncidentRollbackAuditArchiveVerification(
                str(target), archive_sha, IncidentRollbackAuditArchiveStatus.VERIFIED,
                closure.audit_id, acceptance.acceptance_id, closure.readiness.readiness_id, tuple(names), (),
            )
    except Exception as exc:
        return _blocked_audit_archive(target, 'incident_rollback_audit_archive_invalid', f'The Wave 73 incident/rollback audit ZIP cannot be read safely: {exc}', 'Restore or recreate the canonical Wave 73 package.', sha256=archive_sha)


class OperationsEvidenceFreshness(str, Enum):
    CURRENT = 'current'
    EXPIRING = 'expiring'
    EXPIRED = 'expired'
    MISSING = 'missing'
    CONTRADICTORY = 'contradictory'


@dataclass(frozen=True, slots=True)
class SustainedOperationsRenewalPolicy:
    key: str = 'stable'
    target_version: str = '3.0.0'
    max_age_hours: float = 168.0
    expiring_within_hours: float = 24.0
    max_future_skew_minutes: float = 5.0
    required_artifact_keys: tuple[str, ...] = ('sustained-operations-renewal', 'incident-audit-renewal')
    require_wave73_accepted: bool = True
    require_wave73_audit_closed: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.target_version.strip():
            raise ValueError('sustained-operations renewal policy requires key and target version')
        if self.max_age_hours <= 0 or self.expiring_within_hours < 0 or self.expiring_within_hours > self.max_age_hours or self.max_future_skew_minutes < 0:
            raise ValueError('invalid sustained-operations renewal freshness limits')
        values = tuple(dict.fromkeys(str(item).strip() for item in self.required_artifact_keys if str(item).strip()))
        if not values:
            raise ValueError('sustained-operations renewal policy requires artifact keys')
        object.__setattr__(self, 'required_artifact_keys', values)

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key, 'target_version': self.target_version, 'max_age_hours': self.max_age_hours,
            'expiring_within_hours': self.expiring_within_hours, 'max_future_skew_minutes': self.max_future_skew_minutes,
            'required_artifact_keys': self.required_artifact_keys, 'require_wave73_accepted': self.require_wave73_accepted,
            'require_wave73_audit_closed': self.require_wave73_audit_closed,
        }


SUSTAINED_OPERATIONS_RENEWAL_POLICY = SustainedOperationsRenewalPolicy()
SUSTAINED_OPERATIONS_RENEWAL_POLICIES: Mapping[str, SustainedOperationsRenewalPolicy] = MappingProxyType({'stable': SUSTAINED_OPERATIONS_RENEWAL_POLICY})


@dataclass(frozen=True, slots=True)
class OperationsEvidenceFreshnessAssessment:
    status: OperationsEvidenceFreshness
    evidence_captured_at: str | None
    assessed_at: str
    age_hours: float | None
    expires_at: str | None
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'status', OperationsEvidenceFreshness(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {
            'status': self.status.value, 'evidence_captured_at': self.evidence_captured_at, 'assessed_at': self.assessed_at,
            'age_hours': self.age_hours, 'expires_at': self.expires_at, 'message': self.message,
        }


def assess_sustained_operations_evidence_freshness(
    evidence_captured_at: str | None, *, policy: SustainedOperationsRenewalPolicy = SUSTAINED_OPERATIONS_RENEWAL_POLICY,
    now: datetime | str | None = None,
) -> OperationsEvidenceFreshnessAssessment:
    moment = _parse_time(now) if isinstance(now, str) else (now.astimezone(timezone.utc) if isinstance(now, datetime) and now.tzinfo else (now.replace(tzinfo=timezone.utc) if isinstance(now, datetime) else datetime.now(timezone.utc)))
    assessed_at = moment.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    if evidence_captured_at is None or not str(evidence_captured_at).strip():
        return OperationsEvidenceFreshnessAssessment(OperationsEvidenceFreshness.MISSING, None, assessed_at, None, None, 'External renewal evidence has no authoritative capture timestamp.')
    try:
        captured = _parse_time(str(evidence_captured_at))
    except Exception:
        return OperationsEvidenceFreshnessAssessment(OperationsEvidenceFreshness.CONTRADICTORY, str(evidence_captured_at), assessed_at, None, None, 'External renewal evidence capture timestamp is invalid.')
    age_hours = (moment - captured).total_seconds() / 3600.0
    expires = captured.timestamp() + policy.max_age_hours * 3600.0
    expires_at = datetime.fromtimestamp(expires, tz=timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    if age_hours < -(policy.max_future_skew_minutes / 60.0):
        return OperationsEvidenceFreshnessAssessment(OperationsEvidenceFreshness.CONTRADICTORY, str(evidence_captured_at), assessed_at, age_hours, expires_at, 'External renewal evidence appears to come from the future beyond the allowed clock skew.')
    if age_hours > policy.max_age_hours:
        return OperationsEvidenceFreshnessAssessment(OperationsEvidenceFreshness.EXPIRED, str(evidence_captured_at), assessed_at, max(0.0, age_hours), expires_at, 'External renewal evidence is older than the configured renewal window.')
    if age_hours >= policy.max_age_hours - policy.expiring_within_hours:
        return OperationsEvidenceFreshnessAssessment(OperationsEvidenceFreshness.EXPIRING, str(evidence_captured_at), assessed_at, max(0.0, age_hours), expires_at, 'External renewal evidence is still valid but is inside the configured renewal warning window.')
    return OperationsEvidenceFreshnessAssessment(OperationsEvidenceFreshness.CURRENT, str(evidence_captured_at), assessed_at, max(0.0, age_hours), expires_at, 'External renewal evidence is within the configured renewal window.')


class SustainedOperationsRenewalStatus(str, Enum):
    RENEWED = 'renewed'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class SustainedOperationsRenewalFinding:
    code: str
    status: SustainedOperationsRenewalStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('sustained-operations renewal finding code and message must not be empty')
        object.__setattr__(self, 'status', SustainedOperationsRenewalStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class SustainedOperationsEvidenceRenewal:
    renewal_id: str
    audit_id: str
    acceptance_id: str
    audit_archive_sha256: str
    target_version: str
    requested_status: SustainedOperationsRenewalStatus
    evidence_captured_at: str | None
    artifacts: tuple[TargetEvidenceArtifact, ...]
    policy: SustainedOperationsRenewalPolicy = SUSTAINED_OPERATIONS_RENEWAL_POLICY
    framework_version: str = FRAMEWORK_VERSION
    nicegui_required: str = NICEGUI_VERSION
    observed_framework_version: str | None = None
    observed_nicegui_version: str | None = None
    renewal_authority: str | None = None
    renewal_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if any(len(value) != 64 for value in (self.renewal_id, self.audit_id, self.acceptance_id, self.audit_archive_sha256)):
            raise ValueError('sustained-operations renewal requires sha256 renewal/audit/acceptance/archive identifiers')
        object.__setattr__(self, 'requested_status', SustainedOperationsRenewalStatus(self.requested_status))
        artifacts = tuple(self.artifacts)
        if len({item.key for item in artifacts}) != len(artifacts):
            raise ValueError('sustained-operations renewal contains duplicate artifact keys')
        object.__setattr__(self, 'artifacts', artifacts)
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'renewal_id': self.renewal_id, 'audit_id': self.audit_id, 'acceptance_id': self.acceptance_id,
            'audit_archive_sha256': self.audit_archive_sha256, 'target_version': self.target_version,
            'requested_status': self.requested_status.value, 'evidence_captured_at': self.evidence_captured_at,
            'artifacts': [item.to_dict() for item in self.artifacts], 'policy': self.policy.to_dict(),
            'framework_version': self.framework_version, 'nicegui_required': self.nicegui_required,
            'observed_framework_version': self.observed_framework_version, 'observed_nicegui_version': self.observed_nicegui_version,
            'renewal_authority': self.renewal_authority, 'renewal_reference': self.renewal_reference,
            'metadata': dict(self.metadata), 'created_at': self.created_at,
            'historical_wave73_acceptance_mutated': False, 'historical_wave73_audit_mutated': False,
            'monitoring_performed_by_framework': False, 'incident_response_performed_by_framework': False,
            'rollback_performed_by_framework': False, 'deployment_performed_by_framework': False,
            'publication_performed_by_framework': False, 'records_external_artifacts_only': True,
        }


def _renewal_identity_payload(
    closure: IncidentRollbackAuditClosure, audit_archive_sha256: str, requested_status: SustainedOperationsRenewalStatus,
    evidence_captured_at: str | None, artifacts: Sequence[TargetEvidenceArtifact], policy: SustainedOperationsRenewalPolicy, *,
    observed_framework_version: str | None, observed_nicegui_version: str | None,
    renewal_authority: str | None, renewal_reference: str | None, metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'audit_id': closure.audit_id, 'acceptance_id': closure.sustained_operations_acceptance.acceptance_id,
        'audit_archive_sha256': audit_archive_sha256, 'target_version': closure.policy.target_version,
        'requested_status': requested_status.value, 'evidence_captured_at': evidence_captured_at,
        'artifacts': [item.to_dict() for item in artifacts], 'policy': policy.to_dict(),
        'framework_version': FRAMEWORK_VERSION, 'nicegui_required': NICEGUI_VERSION,
        'observed_framework_version': observed_framework_version, 'observed_nicegui_version': observed_nicegui_version,
        'renewal_authority': renewal_authority, 'renewal_reference': renewal_reference, 'metadata': dict(metadata),
    }


def build_sustained_operations_evidence_renewal(
    closure: IncidentRollbackAuditClosure, audit_archive_path: str | Path, *,
    requested_status: SustainedOperationsRenewalStatus | str = SustainedOperationsRenewalStatus.PENDING,
    evidence_captured_at: str | None = None, artifacts: Sequence[TargetEvidenceArtifact] = (),
    observed_framework_version: str | None = None, observed_nicegui_version: str | None = None,
    renewal_authority: str | None = None, renewal_reference: str | None = None,
    policy: SustainedOperationsRenewalPolicy = SUSTAINED_OPERATIONS_RENEWAL_POLICY,
    metadata: Mapping[str, Any] | None = None,
) -> SustainedOperationsEvidenceRenewal:
    archive = Path(audit_archive_path)
    if not archive.is_file():
        raise FileNotFoundError(archive)
    status = SustainedOperationsRenewalStatus(requested_status)
    values = dict(metadata or {})
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    payload = _renewal_identity_payload(
        closure, archive_sha, status, evidence_captured_at, tuple(artifacts), policy,
        observed_framework_version=observed_framework_version, observed_nicegui_version=observed_nicegui_version,
        renewal_authority=renewal_authority, renewal_reference=renewal_reference, metadata=values,
    )
    return SustainedOperationsEvidenceRenewal(
        _canonical_digest(payload), closure.audit_id, closure.sustained_operations_acceptance.acceptance_id,
        archive_sha, closure.policy.target_version, status, evidence_captured_at, tuple(artifacts), policy,
        FRAMEWORK_VERSION, NICEGUI_VERSION, observed_framework_version, observed_nicegui_version,
        renewal_authority, renewal_reference, values,
    )


def sustained_operations_evidence_renewal_from_dict(payload: Mapping[str, Any]) -> SustainedOperationsEvidenceRenewal:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported sustained-operations renewal schema {payload.get("schema_version")!r}')
    policy_payload = payload.get('policy') or {}
    policy = SustainedOperationsRenewalPolicy(
        str(policy_payload.get('key', 'stable')), str(policy_payload.get('target_version', '3.0.0')),
        float(policy_payload.get('max_age_hours', 168.0)), float(policy_payload.get('expiring_within_hours', 24.0)),
        float(policy_payload.get('max_future_skew_minutes', 5.0)),
        tuple(str(item) for item in policy_payload.get('required_artifact_keys', ('sustained-operations-renewal', 'incident-audit-renewal'))),
        bool(policy_payload.get('require_wave73_accepted', True)), bool(policy_payload.get('require_wave73_audit_closed', True)),
    )
    obj = SustainedOperationsEvidenceRenewal(
        str(payload['renewal_id']), str(payload['audit_id']), str(payload['acceptance_id']), str(payload['audit_archive_sha256']),
        str(payload['target_version']), SustainedOperationsRenewalStatus(str(payload.get('requested_status', 'pending'))),
        None if payload.get('evidence_captured_at') is None else str(payload.get('evidence_captured_at')),
        tuple(_target_artifact_from_dict(item) for item in payload.get('artifacts', ()) if isinstance(item, Mapping)),
        policy, str(payload.get('framework_version') or FRAMEWORK_VERSION), str(payload.get('nicegui_required') or NICEGUI_VERSION),
        None if payload.get('observed_framework_version') is None else str(payload.get('observed_framework_version')),
        None if payload.get('observed_nicegui_version') is None else str(payload.get('observed_nicegui_version')),
        None if payload.get('renewal_authority') is None else str(payload.get('renewal_authority')),
        None if payload.get('renewal_reference') is None else str(payload.get('renewal_reference')),
        dict(payload.get('metadata') or {}), str(payload.get('created_at') or _utc_now()),
    )
    identity = {
        'audit_id': obj.audit_id, 'acceptance_id': obj.acceptance_id, 'audit_archive_sha256': obj.audit_archive_sha256,
        'target_version': obj.target_version, 'requested_status': obj.requested_status.value,
        'evidence_captured_at': obj.evidence_captured_at, 'artifacts': [item.to_dict() for item in obj.artifacts],
        'policy': obj.policy.to_dict(), 'framework_version': obj.framework_version, 'nicegui_required': obj.nicegui_required,
        'observed_framework_version': obj.observed_framework_version, 'observed_nicegui_version': obj.observed_nicegui_version,
        'renewal_authority': obj.renewal_authority, 'renewal_reference': obj.renewal_reference, 'metadata': dict(obj.metadata),
    }
    if obj.renewal_id != _canonical_digest(identity):
        raise ValueError('sustained-operations renewal id does not match persisted content')
    return obj


def write_sustained_operations_evidence_renewal(path: str | Path, renewal: SustainedOperationsEvidenceRenewal) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(renewal.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_sustained_operations_evidence_renewal(path: str | Path) -> SustainedOperationsEvidenceRenewal:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('sustained-operations renewal JSON must contain an object')
    return sustained_operations_evidence_renewal_from_dict(payload)


@dataclass(frozen=True, slots=True)
class SustainedOperationsRenewalVerification:
    renewal_id: str
    status: SustainedOperationsRenewalStatus
    freshness: OperationsEvidenceFreshnessAssessment
    findings: tuple[SustainedOperationsRenewalFinding, ...] = ()

    def __post_init__(self) -> None:
        if len(self.renewal_id) != 64:
            raise ValueError('sustained-operations renewal verification requires sha256 id')
        object.__setattr__(self, 'status', SustainedOperationsRenewalStatus(self.status))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def renewed(self) -> bool:
        return self.status is SustainedOperationsRenewalStatus.RENEWED

    def to_dict(self) -> dict[str, Any]:
        return {'renewal_id': self.renewal_id, 'status': self.status.value, 'renewed': self.renewed, 'freshness': self.freshness.to_dict(), 'findings': [item.to_dict() for item in self.findings]}


def _artifact_findings(renewal: SustainedOperationsEvidenceRenewal, base_dir: str | Path | None) -> list[SustainedOperationsRenewalFinding]:
    findings: list[SustainedOperationsRenewalFinding] = []
    keys = {item.key for item in renewal.artifacts}
    for key in renewal.policy.required_artifact_keys:
        if key not in keys:
            findings.append(SustainedOperationsRenewalFinding('renewal_required_artifact_missing', SustainedOperationsRenewalStatus.PENDING, f'Required renewal artifact {key!r} is missing.', f'Capture and attach {key!r} from the authoritative external operations process.'))
    for artifact in renewal.artifacts:
        source = _resolve_artifact_path(artifact, base_dir)
        if not source.is_file():
            findings.append(SustainedOperationsRenewalFinding('renewal_artifact_unavailable', SustainedOperationsRenewalStatus.BLOCKED, f'Renewal artifact {artifact.key!r} is unavailable.', 'Restore the exact captured external renewal artifact bytes.'))
            continue
        blob = source.read_bytes()
        if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
            findings.append(SustainedOperationsRenewalFinding('renewal_artifact_hash_mismatch', SustainedOperationsRenewalStatus.BLOCKED, f'Renewal artifact {artifact.key!r} changed after capture.', 'Reject changed evidence and recapture it from the authoritative external process.'))
    return findings


def verify_sustained_operations_evidence_renewal(
    renewal: SustainedOperationsEvidenceRenewal, closure: IncidentRollbackAuditClosure, audit_archive_path: str | Path, *,
    base_dir: str | Path | None = None, now: datetime | str | None = None,
) -> SustainedOperationsRenewalVerification:
    findings: list[SustainedOperationsRenewalFinding] = []
    archive = verify_incident_rollback_audit_archive(audit_archive_path, expected_closure=closure)
    if not archive.verified:
        findings.append(SustainedOperationsRenewalFinding('wave73_audit_archive_not_verified', SustainedOperationsRenewalStatus.BLOCKED, 'The immutable Wave 73 audit package does not independently verify.', 'Restore the exact verified Wave 73 audit package.'))
    elif archive.sha256 != renewal.audit_archive_sha256:
        findings.append(SustainedOperationsRenewalFinding('wave73_audit_archive_hash_mismatch', SustainedOperationsRenewalStatus.BLOCKED, 'The Wave 73 archive differs from the exact bytes bound to renewal.', 'Use the exact Wave 73 archive reviewed by the renewal authority.'))
    if renewal.audit_id != closure.audit_id or renewal.acceptance_id != closure.sustained_operations_acceptance.acceptance_id:
        findings.append(SustainedOperationsRenewalFinding('renewal_subject_mismatch', SustainedOperationsRenewalStatus.BLOCKED, 'Renewal is bound to a different Wave 73 audit/acceptance identity.', 'Use renewal evidence created for this exact Wave 73 chain.'))
    if renewal.framework_version != FRAMEWORK_VERSION or renewal.nicegui_required != NICEGUI_VERSION:
        findings.append(SustainedOperationsRenewalFinding('renewal_release_identity_mismatch', SustainedOperationsRenewalStatus.BLOCKED, 'Persisted renewal release identity does not match the current NiceGUI Base authority.', 'Regenerate renewal from the current framework and exact required NiceGUI runtime.'))
    if renewal.policy.target_version != closure.policy.target_version or renewal.target_version != closure.policy.target_version:
        findings.append(SustainedOperationsRenewalFinding('renewal_target_version_mismatch', SustainedOperationsRenewalStatus.BLOCKED, 'Renewal policy/record target does not match the Wave 73 release target.', 'Use the matching renewal policy.'))
    if renewal.policy.require_wave73_accepted:
        status = closure.sustained_operations_acceptance.requested_status
        if status is SustainedOperationsAcceptanceStatus.BLOCKED:
            findings.append(SustainedOperationsRenewalFinding('wave73_acceptance_blocked', SustainedOperationsRenewalStatus.BLOCKED, 'Historical Wave 73 sustained-operations acceptance is explicitly BLOCKED.', 'Resolve the canonical Wave 73 evidence chain rather than overriding it with renewal.'))
        elif status is not SustainedOperationsAcceptanceStatus.ACCEPTED:
            findings.append(SustainedOperationsRenewalFinding('wave73_acceptance_not_accepted', SustainedOperationsRenewalStatus.PENDING, 'Historical Wave 73 sustained-operations acceptance is not ACCEPTED.', 'Complete the canonical Wave 73 acceptance before renewal.'))
    if renewal.policy.require_wave73_audit_closed:
        if closure.status is IncidentRollbackAuditStatus.BLOCKED:
            findings.append(SustainedOperationsRenewalFinding('wave73_audit_blocked', SustainedOperationsRenewalStatus.BLOCKED, 'Historical Wave 73 incident/rollback audit is BLOCKED.', 'Resolve the canonical Wave 73 audit blocker first.'))
        elif closure.status is not IncidentRollbackAuditStatus.CLOSED:
            findings.append(SustainedOperationsRenewalFinding('wave73_audit_not_closed', SustainedOperationsRenewalStatus.PENDING, 'Historical Wave 73 incident/rollback audit is not CLOSED.', 'Complete the canonical Wave 73 documentary audit first.'))
    findings.extend(_artifact_findings(renewal, base_dir))
    freshness = assess_sustained_operations_evidence_freshness(renewal.evidence_captured_at, policy=renewal.policy, now=now)
    if freshness.status is OperationsEvidenceFreshness.MISSING:
        findings.append(SustainedOperationsRenewalFinding('renewal_freshness_missing', SustainedOperationsRenewalStatus.PENDING, freshness.message, 'Record the authoritative external evidence capture timestamp.'))
    elif freshness.status is OperationsEvidenceFreshness.EXPIRED:
        findings.append(SustainedOperationsRenewalFinding('renewal_evidence_expired', SustainedOperationsRenewalStatus.PENDING, freshness.message, 'Capture a fresh external sustained-operations renewal evidence set.'))
    elif freshness.status is OperationsEvidenceFreshness.CONTRADICTORY:
        findings.append(SustainedOperationsRenewalFinding('renewal_freshness_contradictory', SustainedOperationsRenewalStatus.BLOCKED, freshness.message, 'Resolve the timestamp/clock contradiction and recapture or correct the authoritative evidence record.'))
    if renewal.requested_status is SustainedOperationsRenewalStatus.BLOCKED:
        findings.append(SustainedOperationsRenewalFinding('renewal_explicitly_blocked', SustainedOperationsRenewalStatus.BLOCKED, 'External renewal explicitly reports BLOCKED.', 'Resolve the external renewal blocker and capture fresh evidence.'))
    elif renewal.requested_status is SustainedOperationsRenewalStatus.PENDING:
        findings.append(SustainedOperationsRenewalFinding('renewal_requested_pending', SustainedOperationsRenewalStatus.PENDING, 'Sustained-operations renewal remains PENDING.', 'Complete the external renewal review and attach the resulting artifacts.'))
    else:
        if not renewal.renewal_authority or not renewal.renewal_reference:
            findings.append(SustainedOperationsRenewalFinding('renewal_authority_reference_missing', SustainedOperationsRenewalStatus.PENDING, 'Requested RENEWED lacks a traceable external renewal authority/reference.', 'Attach the external renewal authority and immutable review reference.'))
        if renewal.observed_framework_version is None or renewal.observed_nicegui_version is None:
            findings.append(SustainedOperationsRenewalFinding('renewal_execution_identity_missing', SustainedOperationsRenewalStatus.PENDING, 'Requested RENEWED lacks observed framework or exact NiceGUI identity.', f'Record framework {FRAMEWORK_VERSION} and exact nicegui=={NICEGUI_VERSION} reviewed by the renewal authority.'))
        else:
            if renewal.observed_framework_version != FRAMEWORK_VERSION:
                findings.append(SustainedOperationsRenewalFinding('renewal_framework_identity_mismatch', SustainedOperationsRenewalStatus.BLOCKED, f'Renewal observed framework {renewal.observed_framework_version!r}, expected {FRAMEWORK_VERSION!r}.', 'Repeat renewal against the current framework release.'))
            if renewal.observed_nicegui_version != NICEGUI_VERSION:
                findings.append(SustainedOperationsRenewalFinding('renewal_nicegui_identity_mismatch', SustainedOperationsRenewalStatus.BLOCKED, f'Renewal observed NiceGUI {renewal.observed_nicegui_version!r}, expected exact {NICEGUI_VERSION!r}.', f'Repeat renewal against exact nicegui=={NICEGUI_VERSION}.'))
    mismatches = renewal.metadata.get('manifest_artifact_sha256_mismatches')
    if isinstance(mismatches, Mapping) and mismatches:
        findings.append(SustainedOperationsRenewalFinding('renewal_manifest_artifact_hash_mismatch', SustainedOperationsRenewalStatus.BLOCKED, 'Renewal manifest SHA-256 expectations do not match captured artifact bytes.', 'Resolve the external renewal manifest/artifact mismatch.'))
    missing_paths = renewal.metadata.get('missing_requested_artifact_paths')
    if isinstance(missing_paths, Sequence) and not isinstance(missing_paths, (str, bytes)) and missing_paths:
        findings.append(SustainedOperationsRenewalFinding('requested_renewal_artifact_missing', SustainedOperationsRenewalStatus.PENDING, 'One or more requested renewal artifact paths were unavailable at import time.', 'Provide the referenced external renewal artifacts and rebuild renewal.'))
    status = SustainedOperationsRenewalStatus.RENEWED
    if any(item.status is SustainedOperationsRenewalStatus.BLOCKED for item in findings):
        status = SustainedOperationsRenewalStatus.BLOCKED
    elif any(item.status is SustainedOperationsRenewalStatus.PENDING for item in findings):
        status = SustainedOperationsRenewalStatus.PENDING
    return SustainedOperationsRenewalVerification(renewal.renewal_id, status, freshness, tuple(findings))


def load_sustained_operations_evidence_renewal_manifest(
    path: str | Path, closure: IncidentRollbackAuditClosure, audit_archive_path: str | Path, *,
    artifact_base_dir: str | Path | None = None, policy: SustainedOperationsRenewalPolicy = SUSTAINED_OPERATIONS_RENEWAL_POLICY,
) -> SustainedOperationsEvidenceRenewal:
    manifest = Path(path)
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('sustained-operations renewal manifest must contain an object')
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported sustained-operations renewal manifest schema {payload.get("schema_version")!r}')
    expected_values = {
        'audit_id': closure.audit_id, 'acceptance_id': closure.sustained_operations_acceptance.acceptance_id,
        'target_version': closure.policy.target_version,
    }
    for key, expected in expected_values.items():
        supplied = payload.get(key)
        if supplied is not None and str(supplied) != expected:
            raise ValueError(f'sustained-operations renewal manifest {key} does not match supplied Wave 73 evidence')
    base = Path(artifact_base_dir) if artifact_base_dir is not None else manifest.parent
    artifacts: list[TargetEvidenceArtifact] = []
    mismatches: dict[str, dict[str, str]] = {}
    missing_paths: list[str] = []
    for item in payload.get('artifacts', ()):
        if not isinstance(item, Mapping) or not str(item.get('key', '')).strip() or not str(item.get('path', '')).strip():
            raise ValueError('sustained-operations renewal artifacts require non-empty key/path')
        source = _safe_manifest_artifact_path(base, str(item['path']))
        if not source.is_file():
            missing_paths.append(str(item['path']))
            continue
        artifact = capture_target_evidence_artifact(source, key=str(item['key']), description=str(item.get('description', '')))
        expected_sha = item.get('sha256')
        if expected_sha is not None and str(expected_sha) != artifact.sha256:
            mismatches[artifact.key] = {'expected': str(expected_sha), 'observed': artifact.sha256}
        artifacts.append(artifact)
    metadata = dict(payload.get('metadata') or {})
    if mismatches:
        metadata['manifest_artifact_sha256_mismatches'] = mismatches
    if missing_paths:
        metadata['missing_requested_artifact_paths'] = missing_paths
    return build_sustained_operations_evidence_renewal(
        closure, audit_archive_path, requested_status=str(payload.get('status') or payload.get('requested_status') or 'pending'),
        evidence_captured_at=None if payload.get('evidence_captured_at') is None else str(payload.get('evidence_captured_at')),
        artifacts=tuple(artifacts), observed_framework_version=None if payload.get('observed_framework_version') is None else str(payload.get('observed_framework_version')),
        observed_nicegui_version=None if payload.get('observed_nicegui_version') is None else str(payload.get('observed_nicegui_version')),
        renewal_authority=None if payload.get('renewal_authority') is None else str(payload.get('renewal_authority')),
        renewal_reference=None if payload.get('renewal_reference') is None else str(payload.get('renewal_reference')),
        policy=policy, metadata=metadata,
    )


@runtime_checkable
class SustainedOperationsEvidenceRenewalAdapter(Protocol):
    def load(self, path: str | Path, closure: IncidentRollbackAuditClosure, audit_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> SustainedOperationsEvidenceRenewal: ...


@dataclass(frozen=True, slots=True)
class JsonSustainedOperationsEvidenceRenewalAdapter:
    key: str = 'json-manifest'

    def load(self, path: str | Path, closure: IncidentRollbackAuditClosure, audit_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> SustainedOperationsEvidenceRenewal:
        return load_sustained_operations_evidence_renewal_manifest(path, closure, audit_archive_path, artifact_base_dir=artifact_base_dir)


SUSTAINED_OPERATIONS_EVIDENCE_RENEWAL_ADAPTERS: Mapping[str, SustainedOperationsEvidenceRenewalAdapter] = MappingProxyType({'json-manifest': JsonSustainedOperationsEvidenceRenewalAdapter()})


class OperationalAssuranceContinuityStatus(str, Enum):
    ASSURED = 'assured'
    EXPIRING = 'expiring'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class OperationalAssuranceContinuityPolicy:
    key: str = 'stable'
    target_version: str = '3.0.0'
    require_verified_wave73_archive: bool = True
    require_renewed_evidence: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.target_version.strip():
            raise ValueError('operational assurance continuity policy requires key and target version')

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key, 'target_version': self.target_version,
            'require_verified_wave73_archive': self.require_verified_wave73_archive,
            'require_renewed_evidence': self.require_renewed_evidence,
        }


OPERATIONAL_ASSURANCE_CONTINUITY_POLICY = OperationalAssuranceContinuityPolicy()
OPERATIONAL_ASSURANCE_CONTINUITY_POLICIES: Mapping[str, OperationalAssuranceContinuityPolicy] = MappingProxyType({'stable': OPERATIONAL_ASSURANCE_CONTINUITY_POLICY})


@dataclass(frozen=True, slots=True)
class OperationalAssuranceContinuityFinding:
    code: str
    status: OperationalAssuranceContinuityStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('operational assurance continuity finding code and message must not be empty')
        object.__setattr__(self, 'status', OperationalAssuranceContinuityStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class OperationalAssuranceContinuityDossier:
    continuity_id: str
    closure: IncidentRollbackAuditClosure
    audit_archive: TargetEvidenceArtifact
    renewal: SustainedOperationsEvidenceRenewal
    renewal_verification: SustainedOperationsRenewalVerification
    policy: OperationalAssuranceContinuityPolicy
    findings: tuple[OperationalAssuranceContinuityFinding, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.continuity_id) != 64:
            raise ValueError('operational assurance continuity dossier requires sha256 id')
        object.__setattr__(self, 'findings', tuple(self.findings))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def status(self) -> OperationalAssuranceContinuityStatus:
        if any(item.status is OperationalAssuranceContinuityStatus.BLOCKED for item in self.findings):
            return OperationalAssuranceContinuityStatus.BLOCKED
        if any(item.status is OperationalAssuranceContinuityStatus.PENDING for item in self.findings):
            return OperationalAssuranceContinuityStatus.PENDING
        if any(item.status is OperationalAssuranceContinuityStatus.EXPIRING for item in self.findings):
            return OperationalAssuranceContinuityStatus.EXPIRING
        return OperationalAssuranceContinuityStatus.ASSURED

    @property
    def next_actions(self) -> tuple[str, ...]:
        actions = tuple(dict.fromkeys(item.remediation for item in self.findings if item.remediation))
        if actions:
            return actions
        return ('Retain the immutable Wave 73 audit package and current renewal dossier; NiceGUI Base performs no monitoring, incident response, rollback, deployment or publication.',)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'continuity_id': self.continuity_id, 'status': self.status.value,
            'closure': self.closure.to_dict(), 'audit_archive': self.audit_archive.to_dict(), 'renewal': self.renewal.to_dict(),
            'renewal_verification': self.renewal_verification.to_dict(), 'policy': self.policy.to_dict(),
            'findings': [item.to_dict() for item in self.findings], 'metadata': dict(self.metadata),
            'generated_at': self.generated_at, 'next_actions': self.next_actions,
            'continuity_is_documentary_evidence_only': True, 'historical_wave73_truth_mutated': False,
            'monitoring_performed_by_framework': False, 'incident_response_performed_by_framework': False,
            'rollback_performed_by_framework': False, 'deployment_performed_by_framework': False,
            'publication_performed_by_framework': False,
        }


def _continuity_identity_payload(
    closure: IncidentRollbackAuditClosure, audit_archive: TargetEvidenceArtifact,
    renewal: SustainedOperationsEvidenceRenewal, renewal_verification: SustainedOperationsRenewalVerification,
    policy: OperationalAssuranceContinuityPolicy, findings: Sequence[OperationalAssuranceContinuityFinding],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'audit_id': closure.audit_id, 'audit_archive': audit_archive.to_dict(), 'renewal_id': renewal.renewal_id,
        'renewal_verification': renewal_verification.to_dict(), 'policy': policy.to_dict(),
        'findings': [item.to_dict() for item in findings], 'metadata': dict(metadata),
    }


def build_operational_assurance_continuity_dossier(
    closure: IncidentRollbackAuditClosure, audit_archive_path: str | Path, renewal: SustainedOperationsEvidenceRenewal, *,
    policy: OperationalAssuranceContinuityPolicy = OPERATIONAL_ASSURANCE_CONTINUITY_POLICY,
    artifact_base_dir: str | Path | None = None, now: datetime | str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> OperationalAssuranceContinuityDossier:
    archive_path = Path(audit_archive_path)
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    archive_artifact = capture_target_evidence_artifact(archive_path, key='wave73-incident-rollback-audit-package', description='immutable Wave 73 incident/rollback audit package')
    verification = verify_sustained_operations_evidence_renewal(renewal, closure, archive_path, base_dir=artifact_base_dir, now=now)
    findings: list[OperationalAssuranceContinuityFinding] = []
    archive = verify_incident_rollback_audit_archive(archive_path, expected_closure=closure)
    if policy.require_verified_wave73_archive and not archive.verified:
        findings.append(OperationalAssuranceContinuityFinding('continuity_wave73_archive_blocked', OperationalAssuranceContinuityStatus.BLOCKED, 'The immutable Wave 73 audit package does not independently verify.', 'Restore the exact verified Wave 73 audit package.'))
    if policy.target_version != closure.policy.target_version:
        findings.append(OperationalAssuranceContinuityFinding('continuity_target_version_mismatch', OperationalAssuranceContinuityStatus.BLOCKED, 'Continuity policy target does not match the Wave 73 release target.', 'Use the matching continuity policy.'))
    if policy.require_renewed_evidence:
        if verification.status is SustainedOperationsRenewalStatus.BLOCKED:
            findings.append(OperationalAssuranceContinuityFinding('continuity_renewal_blocked', OperationalAssuranceContinuityStatus.BLOCKED, 'Sustained-operations renewal is BLOCKED.', 'Resolve renewal evidence integrity/identity contradictions.'))
        elif verification.status is not SustainedOperationsRenewalStatus.RENEWED:
            findings.append(OperationalAssuranceContinuityFinding('continuity_renewal_pending', OperationalAssuranceContinuityStatus.PENDING, 'Sustained-operations renewal is not RENEWED.', 'Complete the external renewal evidence intake.'))
    freshness = verification.freshness.status
    if freshness is OperationsEvidenceFreshness.EXPIRING and verification.status is SustainedOperationsRenewalStatus.RENEWED:
        findings.append(OperationalAssuranceContinuityFinding('continuity_evidence_expiring', OperationalAssuranceContinuityStatus.EXPIRING, 'Renewal evidence remains valid but is inside the configured expiry warning window.', 'Schedule the next external evidence renewal before the current window expires.'))
    elif freshness in {OperationsEvidenceFreshness.EXPIRED, OperationsEvidenceFreshness.MISSING}:
        findings.append(OperationalAssuranceContinuityFinding('continuity_evidence_not_current', OperationalAssuranceContinuityStatus.PENDING, 'Operational assurance continuity lacks current external renewal evidence.', 'Capture and accept a fresh external renewal evidence set.'))
    elif freshness is OperationsEvidenceFreshness.CONTRADICTORY:
        findings.append(OperationalAssuranceContinuityFinding('continuity_freshness_contradictory', OperationalAssuranceContinuityStatus.BLOCKED, 'Operational assurance freshness evidence is contradictory.', 'Resolve the external timestamp/clock contradiction before continuity can be assured.'))
    values = dict(metadata or {})
    payload = _continuity_identity_payload(closure, archive_artifact, renewal, verification, policy, tuple(findings), values)
    return OperationalAssuranceContinuityDossier(_canonical_digest(payload), closure, archive_artifact, renewal, verification, policy, tuple(findings), values)


def operational_assurance_continuity_dossier_from_dict(payload: Mapping[str, Any]) -> OperationalAssuranceContinuityDossier:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported operational assurance continuity schema {payload.get("schema_version")!r}')
    closure_payload = payload.get('closure'); archive_payload = payload.get('audit_archive'); renewal_payload = payload.get('renewal')
    verification_payload = payload.get('renewal_verification')
    if not isinstance(closure_payload, Mapping) or not isinstance(archive_payload, Mapping) or not isinstance(renewal_payload, Mapping) or not isinstance(verification_payload, Mapping):
        raise TypeError('operational assurance continuity requires closure/archive/renewal/verification objects')
    closure = incident_rollback_audit_closure_from_dict(closure_payload)
    archive_artifact = _target_artifact_from_dict(archive_payload)
    renewal = sustained_operations_evidence_renewal_from_dict(renewal_payload)
    freshness_payload = verification_payload.get('freshness') or {}
    freshness = OperationsEvidenceFreshnessAssessment(
        OperationsEvidenceFreshness(str(freshness_payload['status'])),
        None if freshness_payload.get('evidence_captured_at') is None else str(freshness_payload.get('evidence_captured_at')),
        str(freshness_payload.get('assessed_at') or _utc_now()),
        None if freshness_payload.get('age_hours') is None else float(freshness_payload.get('age_hours')),
        None if freshness_payload.get('expires_at') is None else str(freshness_payload.get('expires_at')),
        str(freshness_payload.get('message') or ''),
    )
    renewal_findings = tuple(
        SustainedOperationsRenewalFinding(str(item['code']), SustainedOperationsRenewalStatus(str(item['status'])), str(item['message']), str(item.get('remediation', '')))
        for item in verification_payload.get('findings', ()) if isinstance(item, Mapping)
    )
    renewal_verification = SustainedOperationsRenewalVerification(str(verification_payload['renewal_id']), SustainedOperationsRenewalStatus(str(verification_payload['status'])), freshness, renewal_findings)
    policy_payload = payload.get('policy') or {}
    policy = OperationalAssuranceContinuityPolicy(
        str(policy_payload.get('key', 'stable')), str(policy_payload.get('target_version', '3.0.0')),
        bool(policy_payload.get('require_verified_wave73_archive', True)), bool(policy_payload.get('require_renewed_evidence', True)),
    )
    findings = tuple(
        OperationalAssuranceContinuityFinding(str(item['code']), OperationalAssuranceContinuityStatus(str(item['status'])), str(item['message']), str(item.get('remediation', '')))
        for item in payload.get('findings', ()) if isinstance(item, Mapping)
    )
    obj = OperationalAssuranceContinuityDossier(
        str(payload['continuity_id']), closure, archive_artifact, renewal, renewal_verification, policy, findings,
        dict(payload.get('metadata') or {}), str(payload.get('generated_at') or _utc_now()),
    )
    expected = _canonical_digest(_continuity_identity_payload(obj.closure, obj.audit_archive, obj.renewal, obj.renewal_verification, obj.policy, obj.findings, obj.metadata))
    if obj.continuity_id != expected:
        raise ValueError('operational assurance continuity id does not match persisted content')
    if payload.get('status') is not None and str(payload['status']) != obj.status.value:
        raise ValueError('operational assurance continuity status does not match persisted content')
    return obj


def write_operational_assurance_continuity_dossier(path: str | Path, dossier: OperationalAssuranceContinuityDossier) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dossier.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_operational_assurance_continuity_dossier(path: str | Path) -> OperationalAssuranceContinuityDossier:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('operational assurance continuity JSON must contain an object')
    return operational_assurance_continuity_dossier_from_dict(payload)


@dataclass(frozen=True, slots=True)
class OperationalAssuranceContinuityPackage:
    path: str
    sha256: str
    continuity_id: str
    status: OperationalAssuranceContinuityStatus
    entries: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or len(self.continuity_id) != 64:
            raise ValueError('operational assurance continuity package requires sha256 package/dossier identifiers')
        object.__setattr__(self, 'status', OperationalAssuranceContinuityStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))

    def to_dict(self) -> dict[str, Any]:
        return {'path': self.path, 'sha256': self.sha256, 'continuity_id': self.continuity_id, 'status': self.status.value, 'entries': self.entries}


def package_operational_assurance_continuity_dossier(
    path: str | Path, dossier: OperationalAssuranceContinuityDossier, *, artifact_base_dir: str | Path | None = None,
    now: datetime | str | None = None,
) -> OperationalAssuranceContinuityPackage:
    archive_path = _resolve_artifact_path(dossier.audit_archive, artifact_base_dir)
    refreshed = build_operational_assurance_continuity_dossier(
        dossier.closure, archive_path, dossier.renewal, policy=dossier.policy,
        artifact_base_dir=artifact_base_dir, now=now or dossier.renewal_verification.freshness.assessed_at,
        metadata=dossier.metadata,
    )
    if refreshed.status is OperationalAssuranceContinuityStatus.BLOCKED:
        raise ValueError('operational assurance continuity package cannot be created from BLOCKED or changed evidence')
    if refreshed.continuity_id != dossier.continuity_id:
        raise ValueError('operational assurance continuity identity changed during package verification')
    entries: dict[str, bytes] = {
        'operational-assurance-continuity.json': _json_bytes(refreshed.to_dict()),
        'sustained-operations-renewal.json': _json_bytes(refreshed.renewal.to_dict()),
        'wave73/incident-rollback-audit.zip': archive_path.read_bytes(),
    }
    for artifact in refreshed.renewal.artifacts:
        source = _resolve_artifact_path(artifact, artifact_base_dir)
        if not source.is_file():
            continue
        blob = source.read_bytes()
        if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
            raise ValueError(f'renewal artifact changed: {artifact.key}')
        entries[f'renewal-evidence/{_safe_entry_component(artifact.key)}/{_safe_entry_component(source.name)}'] = blob
    manifest = ''.join(f'{hashlib.sha256(entries[name]).hexdigest()}  {name}\n' for name in sorted(entries))
    entries['MANIFEST.sha256'] = manifest.encode('utf-8')
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w') as archive:
        for name in sorted(entries):
            pure = PurePosixPath(name)
            if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                raise ValueError(f'unsafe operational assurance continuity archive entry {name!r}')
            archive.writestr(_zip_info(name), entries[name])
    return OperationalAssuranceContinuityPackage(str(target), hashlib.sha256(target.read_bytes()).hexdigest(), dossier.continuity_id, dossier.status, tuple(sorted(entries)))


__all__ = [
    'IncidentRollbackAuditArchiveFinding','IncidentRollbackAuditArchiveStatus','IncidentRollbackAuditArchiveVerification',
    'JsonSustainedOperationsEvidenceRenewalAdapter','OPERATIONAL_ASSURANCE_CONTINUITY_POLICIES','OPERATIONAL_ASSURANCE_CONTINUITY_POLICY',
    'OperationalAssuranceContinuityDossier','OperationalAssuranceContinuityFinding','OperationalAssuranceContinuityPackage',
    'OperationalAssuranceContinuityPolicy','OperationalAssuranceContinuityStatus','OperationsEvidenceFreshness',
    'OperationsEvidenceFreshnessAssessment','SUSTAINED_OPERATIONS_EVIDENCE_RENEWAL_ADAPTERS','SUSTAINED_OPERATIONS_RENEWAL_POLICIES',
    'SUSTAINED_OPERATIONS_RENEWAL_POLICY','SustainedOperationsEvidenceRenewal','SustainedOperationsEvidenceRenewalAdapter',
    'SustainedOperationsRenewalFinding','SustainedOperationsRenewalPolicy','SustainedOperationsRenewalStatus','SustainedOperationsRenewalVerification',
    'assess_sustained_operations_evidence_freshness','build_operational_assurance_continuity_dossier',
    'build_sustained_operations_evidence_renewal','load_sustained_operations_evidence_renewal_manifest',
    'operational_assurance_continuity_dossier_from_dict','package_operational_assurance_continuity_dossier',
    'read_operational_assurance_continuity_dossier','read_sustained_operations_evidence_renewal',
    'sustained_operations_evidence_renewal_from_dict','verify_incident_rollback_audit_archive',
    'verify_sustained_operations_evidence_renewal','write_operational_assurance_continuity_dossier',
    'write_sustained_operations_evidence_renewal',
]
