from __future__ import annotations

import hashlib
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

from .semiconductor_evidence import TargetEvidenceArtifact, capture_target_evidence_artifact
from .semiconductor_longitudinal import (
    LongitudinalOperationalAssuranceDossier,
    OperationalAssuranceLedgerStatus,
    longitudinal_operational_assurance_dossier_from_dict,
    operational_assurance_renewal_ledger_from_dict,
    verify_operational_assurance_continuity_archive,
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


def _artifact_from_dict(payload: Mapping[str, Any]) -> TargetEvidenceArtifact:
    return TargetEvidenceArtifact(
        str(payload['key']), str(payload['path']), str(payload['sha256']), int(payload['size_bytes']), str(payload.get('description', '')),
    )


def _resolve_artifact_path(artifact: TargetEvidenceArtifact, base_dir: str | Path | None) -> Path:
    path = Path(artifact.path)
    return path if path.is_absolute() or base_dir is None else Path(base_dir) / path


def _safe_manifest_artifact_path(base: Path, value: str) -> Path:
    raw = Path(value)
    candidate = raw.resolve() if raw.is_absolute() else (base / raw).resolve()
    root = base.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f'Wave 76 artifact path escapes manifest base directory: {value!r}') from exc
    return candidate


def _safe_component(value: str) -> str:
    text = re.sub(r'[^A-Za-z0-9._-]+', '-', value.strip()).strip('.-')
    return text or 'item'


class LongitudinalAssuranceArchiveStatus(str, Enum):
    VERIFIED = 'verified'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class LongitudinalAssuranceArchiveFinding:
    code: str
    status: LongitudinalAssuranceArchiveStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('Wave 75 archive finding code and message must not be empty')
        object.__setattr__(self, 'status', LongitudinalAssuranceArchiveStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class LongitudinalAssuranceArchiveVerification:
    path: str
    sha256: str | None
    status: LongitudinalAssuranceArchiveStatus
    dossier_id: str | None = None
    ledger_id: str | None = None
    target_version: str | None = None
    framework_version: str | None = None
    nicegui_required: str | None = None
    entries: tuple[str, ...] = ()
    findings: tuple[LongitudinalAssuranceArchiveFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.sha256 is not None and (len(self.sha256) != 64 or any(ch not in '0123456789abcdef' for ch in self.sha256.lower())):
            raise ValueError('Wave 75 archive sha256 must be 64 hex characters when present')
        object.__setattr__(self, 'status', LongitudinalAssuranceArchiveStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def verified(self) -> bool:
        return self.status is LongitudinalAssuranceArchiveStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': self.path, 'sha256': self.sha256, 'status': self.status.value, 'verified': self.verified,
            'dossier_id': self.dossier_id, 'ledger_id': self.ledger_id, 'target_version': self.target_version,
            'framework_version': self.framework_version, 'nicegui_required': self.nicegui_required,
            'entries': self.entries, 'findings': [item.to_dict() for item in self.findings],
        }


def _archive_result(path: str | Path, status: LongitudinalAssuranceArchiveStatus, code: str, message: str, remediation: str, *, sha256: str | None = None, entries: Sequence[str] = ()) -> LongitudinalAssuranceArchiveVerification:
    return LongitudinalAssuranceArchiveVerification(
        str(path), sha256, status, entries=tuple(entries),
        findings=(LongitudinalAssuranceArchiveFinding(code, status, message, remediation),),
    )


def verify_longitudinal_operational_assurance_archive(
    path: str | Path, *, expected_dossier: LongitudinalOperationalAssuranceDossier | None = None,
) -> LongitudinalAssuranceArchiveVerification:
    target = Path(path)
    if not target.is_file():
        return _archive_result(target, LongitudinalAssuranceArchiveStatus.PENDING, 'longitudinal_archive_missing', 'The Wave 75 longitudinal assurance ZIP is unavailable.', 'Provide the exact immutable Wave 75 longitudinal assurance package.')
    blob = target.read_bytes(); archive_sha = hashlib.sha256(blob).hexdigest()
    try:
        with zipfile.ZipFile(target) as archive:
            infos = archive.infolist(); names = [item.filename for item in infos]
            if len(names) != len(set(names)):
                return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_duplicate_entry', 'The Wave 75 ZIP contains duplicate entries.', 'Reject it and recreate the canonical Wave 75 package.', sha256=archive_sha, entries=names)
            for name in names:
                pure = PurePosixPath(name)
                if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                    return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_unsafe_entry', f'The Wave 75 ZIP contains unsafe entry {name!r}.', 'Reject the archive and recreate it with the canonical Wave 75 packager.', sha256=archive_sha, entries=names)
            required = {'longitudinal-operational-assurance.json', 'operational-assurance-renewal-ledger.json', 'MANIFEST.sha256'}
            missing = sorted(required - set(names))
            if missing:
                return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_required_entry_missing', f'The Wave 75 ZIP is missing required entries: {missing}.', 'Recreate the complete self-contained Wave 75 package.', sha256=archive_sha, entries=names)
            expected_hashes = _parse_manifest(archive.read('MANIFEST.sha256'))
            payload_names = set(names) - {'MANIFEST.sha256'}
            if set(expected_hashes) != payload_names:
                return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_manifest_incomplete', 'MANIFEST.sha256 does not cover exactly every non-manifest entry.', 'Recreate the Wave 75 package with complete deterministic hashing.', sha256=archive_sha, entries=names)
            for name, expected_sha in expected_hashes.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected_sha:
                    return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_hash_mismatch', f'Wave 75 archive entry {name!r} does not match MANIFEST.sha256.', 'Reject the changed archive and restore the exact Wave 75 package.', sha256=archive_sha, entries=names)
            dossier_payload = json.loads(archive.read('longitudinal-operational-assurance.json'))
            ledger_payload = json.loads(archive.read('operational-assurance-renewal-ledger.json'))
            if not isinstance(dossier_payload, Mapping) or not isinstance(ledger_payload, Mapping):
                return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_payload_invalid', 'Wave 75 dossier and ledger entries must contain JSON objects.', 'Recreate the canonical Wave 75 package.', sha256=archive_sha, entries=names)
            dossier = longitudinal_operational_assurance_dossier_from_dict(dossier_payload)
            ledger = operational_assurance_renewal_ledger_from_dict(ledger_payload)
            if dossier.ledger.ledger_id != ledger.ledger_id:
                return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_ledger_mismatch', 'The embedded dossier and ledger identities do not match.', 'Reject the contradictory Wave 75 package.', sha256=archive_sha, entries=names)
            if expected_dossier is not None and dossier.dossier_id != expected_dossier.dossier_id:
                return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_subject_mismatch', 'The Wave 75 package does not belong to the expected dossier.', 'Use the exact Wave 75 package created for the reviewed dossier.', sha256=archive_sha, entries=names)
            expected_wave74 = [name for name in names if name.startswith('wave74/') and name.endswith('.zip')]
            if len(expected_wave74) != len(ledger.entries):
                return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_wave74_count_mismatch', 'The Wave 75 package does not contain exactly one Wave 74 package for each ledger entry.', 'Recreate the canonical self-contained Wave 75 package.', sha256=archive_sha, entries=names)
            with tempfile.TemporaryDirectory(prefix='nicegui-base-wave76-') as td:
                for name, entry in zip(sorted(expected_wave74), ledger.entries):
                    nested = Path(td) / Path(name).name
                    nested.write_bytes(archive.read(name))
                    nested_sha = hashlib.sha256(nested.read_bytes()).hexdigest()
                    if nested_sha != entry.package.sha256:
                        return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_wave74_hash_mismatch', f'Embedded Wave 74 package {name!r} does not match ledger artifact identity.', 'Reject the contradictory Wave 75 package.', sha256=archive_sha, entries=names)
                    report = verify_operational_assurance_continuity_archive(nested)
                    if not report.verified:
                        return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_nested_wave74_blocked', f'Embedded Wave 74 package {name!r} failed independent verification.', 'Replace the Wave 75 package with one containing the exact verified Wave 74 chain.', sha256=archive_sha, entries=names)
                    if report.continuity_id != entry.continuity_id or report.renewal_id != entry.renewal_id:
                        return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_nested_identity_mismatch', f'Embedded Wave 74 package {name!r} does not match the ledger continuity/renewal identity.', 'Reject the contradictory Wave 75 package.', sha256=archive_sha, entries=names)
            framework_versions = {entry.framework_version for entry in ledger.entries}
            nicegui_versions = {entry.nicegui_required for entry in ledger.entries}
            targets = {entry.target_version for entry in ledger.entries}
            framework = next(iter(framework_versions), FRAMEWORK_VERSION)
            nicegui = next(iter(nicegui_versions), NICEGUI_VERSION)
            target_version = next(iter(targets), ledger.policy.target_version)
            if len(framework_versions) > 1 or len(nicegui_versions) > 1 or len(targets) > 1:
                return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_identity_drift', 'The Wave 75 ledger contains contradictory framework/runtime/target identities.', 'Use one exact release identity for a longitudinal review.', sha256=archive_sha, entries=names)
            if framework != FRAMEWORK_VERSION or nicegui != NICEGUI_VERSION:
                return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_runtime_identity_mismatch', 'The Wave 75 package does not match this framework and exact required NiceGUI runtime.', 'Review evidence captured for this exact framework/runtime identity.', sha256=archive_sha, entries=names)
            return LongitudinalAssuranceArchiveVerification(
                str(target), archive_sha, LongitudinalAssuranceArchiveStatus.VERIFIED, dossier.dossier_id, ledger.ledger_id,
                target_version, framework, nicegui, tuple(names), (),
            )
    except (OSError, zipfile.BadZipFile, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return _archive_result(target, LongitudinalAssuranceArchiveStatus.BLOCKED, 'longitudinal_archive_invalid', f'The Wave 75 package cannot be verified: {exc}', 'Reject the invalid archive and recreate it with the canonical Wave 75 packager.', sha256=archive_sha)


class EvidenceExceptionDisposition(str, Enum):
    ACCEPTED = 'accepted'
    UNRESOLVED = 'unresolved'
    REJECTED = 'rejected'


@dataclass(frozen=True, slots=True)
class LongitudinalEvidenceExceptionPolicy:
    key: str = 'stable'
    target_version: str = '3.0.0'
    allowed_finding_codes: tuple[str, ...] = ('ledger_coverage_gap', 'ledger_active_window_stale', 'ledger_pending_continuity_period', 'ledger_coverage_overlap')
    max_exception_hours: float = 168.0
    require_exception_reference: bool = True
    require_expiry: bool = True
    permit_blocked_evidence_exceptions: bool = False

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.target_version.strip():
            raise ValueError('Wave 76 exception policy requires key and target version')
        if self.max_exception_hours < 0:
            raise ValueError('Wave 76 max_exception_hours must be non-negative')
        object.__setattr__(self, 'allowed_finding_codes', tuple(dict.fromkeys(str(v).strip() for v in self.allowed_finding_codes if str(v).strip())))

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key, 'target_version': self.target_version, 'allowed_finding_codes': self.allowed_finding_codes,
            'max_exception_hours': self.max_exception_hours, 'require_exception_reference': self.require_exception_reference,
            'require_expiry': self.require_expiry, 'permit_blocked_evidence_exceptions': self.permit_blocked_evidence_exceptions,
        }


LONGITUDINAL_EVIDENCE_EXCEPTION_POLICY = LongitudinalEvidenceExceptionPolicy()
LONGITUDINAL_EVIDENCE_EXCEPTION_POLICIES: Mapping[str, LongitudinalEvidenceExceptionPolicy] = MappingProxyType({'stable': LONGITUDINAL_EVIDENCE_EXCEPTION_POLICY})


@dataclass(frozen=True, slots=True)
class LongitudinalEvidenceExceptionDecision:
    finding_code: str
    disposition: EvidenceExceptionDisposition
    rationale: str
    exception_reference: str | None = None
    expires_at: str | None = None

    def __post_init__(self) -> None:
        if not self.finding_code.strip() or not self.rationale.strip():
            raise ValueError('Wave 76 exception decisions require finding code and rationale')
        object.__setattr__(self, 'disposition', EvidenceExceptionDisposition(self.disposition))

    def to_dict(self) -> dict[str, Any]:
        return {
            'finding_code': self.finding_code, 'disposition': self.disposition.value, 'rationale': self.rationale,
            'exception_reference': self.exception_reference, 'expires_at': self.expires_at,
        }


class LongitudinalAssuranceReviewStatus(str, Enum):
    REVIEWED = 'reviewed'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class LongitudinalAssuranceReviewFinding:
    code: str
    status: LongitudinalAssuranceReviewStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('Wave 76 review finding code and message must not be empty')
        object.__setattr__(self, 'status', LongitudinalAssuranceReviewStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class LongitudinalAssuranceReviewRecord:
    review_id: str
    dossier: LongitudinalOperationalAssuranceDossier
    dossier_archive: TargetEvidenceArtifact
    reviewer: str
    authority: str
    review_reference: str
    authority_issued_at: str | None
    authority_expires_at: str | None
    authority_revoked: bool
    artifacts: tuple[TargetEvidenceArtifact, ...]
    exceptions: tuple[LongitudinalEvidenceExceptionDecision, ...]
    policy: LongitudinalEvidenceExceptionPolicy
    findings: tuple[LongitudinalAssuranceReviewFinding, ...]
    framework_version: str = FRAMEWORK_VERSION
    nicegui_required: str = NICEGUI_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)
    reviewed_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.review_id) != 64:
            raise ValueError('Wave 76 review record requires sha256 id')
        object.__setattr__(self, 'artifacts', tuple(self.artifacts)); object.__setattr__(self, 'exceptions', tuple(self.exceptions))
        object.__setattr__(self, 'findings', tuple(self.findings)); object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def status(self) -> LongitudinalAssuranceReviewStatus:
        if any(item.status is LongitudinalAssuranceReviewStatus.BLOCKED for item in self.findings):
            return LongitudinalAssuranceReviewStatus.BLOCKED
        if any(item.status is LongitudinalAssuranceReviewStatus.PENDING for item in self.findings):
            return LongitudinalAssuranceReviewStatus.PENDING
        return LongitudinalAssuranceReviewStatus.REVIEWED

    @property
    def next_actions(self) -> tuple[str, ...]:
        actions = tuple(dict.fromkeys(item.remediation for item in self.findings if item.remediation))
        return actions or ('Retain the exact Wave 75 dossier package and review-authority artifacts; re-review before authority or exception expiry.',)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'review_id': self.review_id, 'status': self.status.value, 'dossier': self.dossier.to_dict(),
            'dossier_archive': self.dossier_archive.to_dict(), 'reviewer': self.reviewer, 'authority': self.authority,
            'review_reference': self.review_reference, 'authority_issued_at': self.authority_issued_at,
            'authority_expires_at': self.authority_expires_at, 'authority_revoked': self.authority_revoked,
            'artifacts': [item.to_dict() for item in self.artifacts], 'exceptions': [item.to_dict() for item in self.exceptions],
            'policy': self.policy.to_dict(), 'findings': [item.to_dict() for item in self.findings],
            'framework_version': self.framework_version, 'nicegui_required': self.nicegui_required,
            'metadata': dict(self.metadata), 'reviewed_at': self.reviewed_at, 'next_actions': self.next_actions,
            'underlying_evidence_status': self.dossier.status.value, 'synthetic_evidence_pass_created': False,
            'historical_wave74_wave75_truth_mutated': False, 'review_is_documentary_only': True,
            'monitoring_performed_by_framework': False, 'incident_response_performed_by_framework': False,
            'rollback_performed_by_framework': False, 'deployment_performed_by_framework': False,
            'publication_performed_by_framework': False,
        }


def _review_identity_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {k: record[k] for k in (
        'dossier_id','dossier_archive','reviewer','authority','review_reference','authority_issued_at','authority_expires_at',
        'authority_revoked','artifacts','exceptions','policy','findings','framework_version','nicegui_required','metadata','reviewed_at',
    )}


def _artifact_findings(artifacts: Sequence[TargetEvidenceArtifact], base_dir: str | Path | None) -> list[LongitudinalAssuranceReviewFinding]:
    findings: list[LongitudinalAssuranceReviewFinding] = []
    for artifact in artifacts:
        path = _resolve_artifact_path(artifact, base_dir)
        if not path.is_file():
            findings.append(LongitudinalAssuranceReviewFinding('review_authority_artifact_missing', LongitudinalAssuranceReviewStatus.PENDING, f'Review authority artifact is missing: {artifact.path}.', 'Provide the exact authoritative review artifact.'))
            continue
        blob = path.read_bytes()
        if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
            findings.append(LongitudinalAssuranceReviewFinding('review_authority_artifact_tampered', LongitudinalAssuranceReviewStatus.BLOCKED, f'Review authority artifact changed: {artifact.path}.', 'Restore the exact artifact or issue a new review record.'))
    return findings


def build_longitudinal_assurance_review_record(
    dossier: LongitudinalOperationalAssuranceDossier, dossier_archive_path: str | Path, *, reviewer: str, authority: str,
    review_reference: str, authority_issued_at: str | None = None, authority_expires_at: str | None = None,
    authority_revoked: bool = False, artifacts: Sequence[TargetEvidenceArtifact] = (),
    exceptions: Sequence[LongitudinalEvidenceExceptionDecision] = (), policy: LongitudinalEvidenceExceptionPolicy = LONGITUDINAL_EVIDENCE_EXCEPTION_POLICY,
    artifact_base_dir: str | Path | None = None, now: datetime | str | None = None, metadata: Mapping[str, Any] | None = None,
) -> LongitudinalAssuranceReviewRecord:
    moment = _moment(now); findings: list[LongitudinalAssuranceReviewFinding] = []
    archive_report = verify_longitudinal_operational_assurance_archive(dossier_archive_path, expected_dossier=dossier)
    archive_path = Path(dossier_archive_path)
    if archive_path.is_file():
        archive_artifact = capture_target_evidence_artifact(archive_path, key='wave75-longitudinal-assurance-package', description='immutable Wave 75 longitudinal assurance package')
    else:
        archive_artifact = TargetEvidenceArtifact('wave75-longitudinal-assurance-package', str(archive_path), '0'*64, 0, 'missing Wave 75 longitudinal assurance package')
    if archive_report.status is LongitudinalAssuranceArchiveStatus.PENDING:
        findings.append(LongitudinalAssuranceReviewFinding('review_wave75_archive_missing', LongitudinalAssuranceReviewStatus.PENDING, 'The reviewed Wave 75 dossier package is unavailable.', 'Provide the exact immutable Wave 75 package before review can complete.'))
    elif archive_report.status is LongitudinalAssuranceArchiveStatus.BLOCKED:
        findings.append(LongitudinalAssuranceReviewFinding('review_wave75_archive_blocked', LongitudinalAssuranceReviewStatus.BLOCKED, 'The reviewed Wave 75 dossier package failed independent verification.', 'Replace the invalid or mismatched Wave 75 package.'))
    if dossier.ledger.policy.target_version != policy.target_version:
        findings.append(LongitudinalAssuranceReviewFinding('review_target_identity_mismatch', LongitudinalAssuranceReviewStatus.BLOCKED, 'The review policy target does not match the Wave 75 target release.', 'Use a review policy bound to the exact target release identity.'))
    if not reviewer.strip() or not authority.strip() or not review_reference.strip():
        findings.append(LongitudinalAssuranceReviewFinding('review_authority_missing', LongitudinalAssuranceReviewStatus.PENDING, 'Reviewer, authority and review reference are all required.', 'Supply an approved external reviewer, authority and traceable review reference.'))
    if authority_revoked:
        findings.append(LongitudinalAssuranceReviewFinding('review_authority_revoked', LongitudinalAssuranceReviewStatus.PENDING, 'The supplied review authority is revoked.', 'Obtain a current non-revoked review authority and issue a new review record.'))
    issued = _parse_time(authority_issued_at) if authority_issued_at else None
    expires = _parse_time(authority_expires_at) if authority_expires_at else None
    if issued and issued > moment:
        findings.append(LongitudinalAssuranceReviewFinding('review_authority_future_issued_at', LongitudinalAssuranceReviewStatus.BLOCKED, 'Review authority appears to have been issued in the future.', 'Resolve the external timestamp/clock contradiction.'))
    if expires is None:
        findings.append(LongitudinalAssuranceReviewFinding('review_authority_expiry_missing', LongitudinalAssuranceReviewStatus.PENDING, 'Review authority expiry is missing.', 'Provide bounded authority validity evidence.'))
    elif expires <= moment:
        findings.append(LongitudinalAssuranceReviewFinding('review_authority_expired', LongitudinalAssuranceReviewStatus.PENDING, 'Review authority is expired.', 'Obtain current review authority and issue a new review record.'))
    elif issued is not None and expires <= issued:
        findings.append(LongitudinalAssuranceReviewFinding('review_authority_time_contradiction', LongitudinalAssuranceReviewStatus.BLOCKED, 'Review authority expiry is not after its issue time.', 'Resolve the contradictory review-authority timestamps.'))
    if not artifacts:
        findings.append(LongitudinalAssuranceReviewFinding('review_authority_artifacts_missing', LongitudinalAssuranceReviewStatus.PENDING, 'No traceable review-authority artifact is supplied.', 'Supply at least one hash-bound external review/authority artifact.'))
    findings.extend(_artifact_findings(tuple(artifacts), artifact_base_dir))
    ledger_by_code = {finding.code: finding for finding in dossier.ledger.findings}
    seen_codes: set[str] = set()
    for exc in exceptions:
        if exc.finding_code in seen_codes:
            findings.append(LongitudinalAssuranceReviewFinding('review_duplicate_exception', LongitudinalAssuranceReviewStatus.BLOCKED, f'Duplicate exception decision exists for {exc.finding_code}.', 'Keep one authoritative exception decision per finding code.'))
            continue
        seen_codes.add(exc.finding_code)
        source = ledger_by_code.get(exc.finding_code)
        if source is None:
            findings.append(LongitudinalAssuranceReviewFinding('review_exception_subject_missing', LongitudinalAssuranceReviewStatus.BLOCKED, f'Exception references unknown ledger finding {exc.finding_code}.', 'Bind exceptions only to findings present in the exact Wave 75 dossier.'))
            continue
        if source.status is OperationalAssuranceLedgerStatus.BLOCKED and not policy.permit_blocked_evidence_exceptions:
            findings.append(LongitudinalAssuranceReviewFinding('review_blocked_evidence_not_exceptionable', LongitudinalAssuranceReviewStatus.BLOCKED, f'Blocked evidence finding {exc.finding_code} cannot be waived.', 'Replace or correct the contradictory/tampered evidence.'))
            continue
        if exc.disposition is EvidenceExceptionDisposition.ACCEPTED:
            if exc.finding_code not in policy.allowed_finding_codes:
                findings.append(LongitudinalAssuranceReviewFinding('review_exception_not_allowed', LongitudinalAssuranceReviewStatus.BLOCKED, f'Finding {exc.finding_code} is outside the bounded exception policy.', 'Use the approved bounded policy or resolve the evidence gap.'))
            if policy.require_exception_reference and not (exc.exception_reference or '').strip():
                findings.append(LongitudinalAssuranceReviewFinding('review_exception_reference_missing', LongitudinalAssuranceReviewStatus.PENDING, f'Accepted exception for {exc.finding_code} lacks a reference.', 'Supply the approved external exception/waiver reference.'))
            if policy.require_expiry and not exc.expires_at:
                findings.append(LongitudinalAssuranceReviewFinding('review_exception_expiry_missing', LongitudinalAssuranceReviewStatus.PENDING, f'Accepted exception for {exc.finding_code} lacks expiry.', 'Bound the exception with an explicit expiry.'))
            if exc.expires_at:
                exc_expiry = _parse_time(exc.expires_at)
                if exc_expiry <= moment:
                    findings.append(LongitudinalAssuranceReviewFinding('review_exception_expired', LongitudinalAssuranceReviewStatus.PENDING, f'Accepted exception for {exc.finding_code} is expired.', 'Renew the exception or resolve the underlying evidence gap.'))
                elif (exc_expiry - moment).total_seconds()/3600 > policy.max_exception_hours:
                    findings.append(LongitudinalAssuranceReviewFinding('review_exception_exceeds_bound', LongitudinalAssuranceReviewStatus.BLOCKED, f'Accepted exception for {exc.finding_code} exceeds the configured bounded duration.', 'Use an approved exception within the configured maximum duration.'))
        elif exc.disposition is EvidenceExceptionDisposition.UNRESOLVED:
            findings.append(LongitudinalAssuranceReviewFinding('review_exception_unresolved', LongitudinalAssuranceReviewStatus.PENDING, f'Exception subject {exc.finding_code} remains unresolved.', 'Resolve the gap or obtain a bounded approved exception.'))
        else:
            findings.append(LongitudinalAssuranceReviewFinding('review_exception_rejected', LongitudinalAssuranceReviewStatus.PENDING, f'Exception for {exc.finding_code} was rejected.', 'Resolve the underlying evidence gap before review closure.'))
    values = dict(metadata or {})
    reviewed_at = _iso(moment)
    payload = {
        'dossier_id': dossier.dossier_id, 'dossier_archive': archive_artifact.to_dict(), 'reviewer': reviewer,
        'authority': authority, 'review_reference': review_reference, 'authority_issued_at': authority_issued_at,
        'authority_expires_at': authority_expires_at, 'authority_revoked': bool(authority_revoked),
        'artifacts': [item.to_dict() for item in artifacts], 'exceptions': [item.to_dict() for item in exceptions],
        'policy': policy.to_dict(), 'findings': [item.to_dict() for item in findings], 'framework_version': FRAMEWORK_VERSION,
        'nicegui_required': NICEGUI_VERSION, 'metadata': values, 'reviewed_at': reviewed_at,
    }
    return LongitudinalAssuranceReviewRecord(
        _canonical_digest(payload), dossier, archive_artifact, reviewer, authority, review_reference, authority_issued_at,
        authority_expires_at, bool(authority_revoked), tuple(artifacts), tuple(exceptions), policy, tuple(findings),
        FRAMEWORK_VERSION, NICEGUI_VERSION, values, reviewed_at,
    )


def longitudinal_assurance_review_record_from_dict(payload: Mapping[str, Any]) -> LongitudinalAssuranceReviewRecord:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported Wave 76 review schema {payload.get("schema_version")!r}')
    dossier_payload = payload.get('dossier'); archive_payload = payload.get('dossier_archive'); policy_payload = payload.get('policy')
    if not isinstance(dossier_payload, Mapping) or not isinstance(archive_payload, Mapping) or not isinstance(policy_payload, Mapping):
        raise TypeError('Wave 76 review requires dossier, dossier_archive and policy objects')
    dossier = longitudinal_operational_assurance_dossier_from_dict(dossier_payload)
    policy = LongitudinalEvidenceExceptionPolicy(
        key=str(policy_payload.get('key', 'stable')), target_version=str(policy_payload.get('target_version', '3.0.0')),
        allowed_finding_codes=tuple(str(v) for v in policy_payload.get('allowed_finding_codes', ())),
        max_exception_hours=float(policy_payload.get('max_exception_hours', 168.0)),
        require_exception_reference=bool(policy_payload.get('require_exception_reference', True)),
        require_expiry=bool(policy_payload.get('require_expiry', True)),
        permit_blocked_evidence_exceptions=bool(policy_payload.get('permit_blocked_evidence_exceptions', False)),
    )
    exceptions = tuple(LongitudinalEvidenceExceptionDecision(
        str(item['finding_code']), EvidenceExceptionDisposition(str(item['disposition'])), str(item['rationale']),
        None if item.get('exception_reference') is None else str(item.get('exception_reference')),
        None if item.get('expires_at') is None else str(item.get('expires_at')),
    ) for item in payload.get('exceptions', ()))
    findings = tuple(LongitudinalAssuranceReviewFinding(str(item['code']), LongitudinalAssuranceReviewStatus(str(item['status'])), str(item['message']), str(item.get('remediation', ''))) for item in payload.get('findings', ()))
    obj = LongitudinalAssuranceReviewRecord(
        str(payload['review_id']), dossier, _artifact_from_dict(archive_payload), str(payload['reviewer']), str(payload['authority']),
        str(payload['review_reference']), None if payload.get('authority_issued_at') is None else str(payload.get('authority_issued_at')),
        None if payload.get('authority_expires_at') is None else str(payload.get('authority_expires_at')), bool(payload.get('authority_revoked', False)),
        tuple(_artifact_from_dict(item) for item in payload.get('artifacts', ())), exceptions, policy, findings,
        str(payload.get('framework_version', FRAMEWORK_VERSION)), str(payload.get('nicegui_required', NICEGUI_VERSION)),
        dict(payload.get('metadata') or {}), str(payload.get('reviewed_at') or _utc_now()),
    )
    identity = {
        'dossier_id': obj.dossier.dossier_id, 'dossier_archive': obj.dossier_archive.to_dict(), 'reviewer': obj.reviewer,
        'authority': obj.authority, 'review_reference': obj.review_reference, 'authority_issued_at': obj.authority_issued_at,
        'authority_expires_at': obj.authority_expires_at, 'authority_revoked': obj.authority_revoked,
        'artifacts': [item.to_dict() for item in obj.artifacts], 'exceptions': [item.to_dict() for item in obj.exceptions],
        'policy': obj.policy.to_dict(), 'findings': [item.to_dict() for item in obj.findings], 'framework_version': obj.framework_version,
        'nicegui_required': obj.nicegui_required, 'metadata': dict(obj.metadata), 'reviewed_at': obj.reviewed_at,
    }
    if obj.review_id != _canonical_digest(identity):
        raise ValueError('Wave 76 review id does not match persisted content')
    if payload.get('status') is not None and str(payload['status']) != obj.status.value:
        raise ValueError('Wave 76 review status does not match persisted content')
    return obj


def write_longitudinal_assurance_review_record(path: str | Path, record: LongitudinalAssuranceReviewRecord) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)+'\n', encoding='utf-8')
    return target


def read_longitudinal_assurance_review_record(path: str | Path) -> LongitudinalAssuranceReviewRecord:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('Wave 76 review JSON must contain an object')
    return longitudinal_assurance_review_record_from_dict(payload)


def load_longitudinal_assurance_review_manifest(
    path: str | Path, dossier: LongitudinalOperationalAssuranceDossier, dossier_archive_path: str | Path, *,
    artifact_base_dir: str | Path | None = None, now: datetime | str | None = None,
    policy: LongitudinalEvidenceExceptionPolicy = LONGITUDINAL_EVIDENCE_EXCEPTION_POLICY,
) -> LongitudinalAssuranceReviewRecord:
    manifest_path = Path(path); payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('Wave 76 review manifest must contain an object')
    if payload.get('dossier_id') is not None and str(payload['dossier_id']) != dossier.dossier_id:
        raise ValueError('Wave 76 review manifest dossier_id does not match the reviewed dossier')
    if payload.get('framework_version') is not None and str(payload['framework_version']) != FRAMEWORK_VERSION:
        raise ValueError('Wave 76 review manifest framework_version does not match current framework')
    if payload.get('nicegui_required') is not None and str(payload['nicegui_required']) != NICEGUI_VERSION:
        raise ValueError('Wave 76 review manifest nicegui_required does not match exact required runtime')
    base = Path(artifact_base_dir) if artifact_base_dir is not None else manifest_path.parent
    artifacts: list[TargetEvidenceArtifact] = []
    for item in payload.get('artifacts', ()):
        if not isinstance(item, Mapping):
            raise TypeError('Wave 76 review artifact entries must be objects')
        raw_path = str(item['path']); resolved = _safe_manifest_artifact_path(base, raw_path)
        expected_sha = item.get('sha256'); expected_size = item.get('size_bytes')
        if expected_sha is None or expected_size is None:
            if resolved.is_file():
                artifact = capture_target_evidence_artifact(resolved, key=str(item.get('key', 'review-authority')), description=str(item.get('description', 'external review authority evidence')))
            else:
                artifact = TargetEvidenceArtifact(str(item.get('key', 'review-authority')), str(resolved), '0'*64, 0, str(item.get('description', 'external review authority evidence')))
        else:
            artifact = TargetEvidenceArtifact(str(item.get('key', 'review-authority')), str(resolved), str(expected_sha), int(expected_size), str(item.get('description', 'external review authority evidence')))
        artifacts.append(artifact)
    exceptions = tuple(LongitudinalEvidenceExceptionDecision(
        str(item['finding_code']), EvidenceExceptionDisposition(str(item.get('disposition', 'unresolved'))), str(item.get('rationale', 'External review decision')),
        None if item.get('exception_reference') is None else str(item.get('exception_reference')),
        None if item.get('expires_at') is None else str(item.get('expires_at')),
    ) for item in payload.get('exceptions', ()))
    return build_longitudinal_assurance_review_record(
        dossier, dossier_archive_path, reviewer=str(payload.get('reviewer', '')), authority=str(payload.get('authority', '')),
        review_reference=str(payload.get('review_reference', '')), authority_issued_at=None if payload.get('authority_issued_at') is None else str(payload.get('authority_issued_at')),
        authority_expires_at=None if payload.get('authority_expires_at') is None else str(payload.get('authority_expires_at')),
        authority_revoked=bool(payload.get('authority_revoked', False)), artifacts=artifacts, exceptions=exceptions, policy=policy,
        artifact_base_dir=None, now=now, metadata=dict(payload.get('metadata') or {}),
    )


@runtime_checkable
class LongitudinalAssuranceReviewAdapter(Protocol):
    def load(self, path: str | Path, dossier: LongitudinalOperationalAssuranceDossier, dossier_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None, now: datetime | str | None = None) -> LongitudinalAssuranceReviewRecord: ...


@dataclass(frozen=True, slots=True)
class JsonLongitudinalAssuranceReviewAdapter:
    key: str = 'json-manifest'

    def load(self, path: str | Path, dossier: LongitudinalOperationalAssuranceDossier, dossier_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None, now: datetime | str | None = None) -> LongitudinalAssuranceReviewRecord:
        return load_longitudinal_assurance_review_manifest(path, dossier, dossier_archive_path, artifact_base_dir=artifact_base_dir, now=now)


LONGITUDINAL_ASSURANCE_REVIEW_ADAPTERS: Mapping[str, LongitudinalAssuranceReviewAdapter] = MappingProxyType({'json-manifest': JsonLongitudinalAssuranceReviewAdapter()})


class EvidenceExceptionGovernanceStatus(str, Enum):
    GOVERNED = 'governed'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class EvidenceExceptionGovernanceFinding:
    code: str
    status: EvidenceExceptionGovernanceStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('Wave 76 governance finding code and message must not be empty')
        object.__setattr__(self, 'status', EvidenceExceptionGovernanceStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class EvidenceExceptionGovernanceDossier:
    governance_id: str
    review: LongitudinalAssuranceReviewRecord
    findings: tuple[EvidenceExceptionGovernanceFinding, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.governance_id) != 64:
            raise ValueError('Wave 76 governance dossier requires sha256 id')
        object.__setattr__(self, 'findings', tuple(self.findings)); object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def status(self) -> EvidenceExceptionGovernanceStatus:
        if any(item.status is EvidenceExceptionGovernanceStatus.BLOCKED for item in self.findings):
            return EvidenceExceptionGovernanceStatus.BLOCKED
        if any(item.status is EvidenceExceptionGovernanceStatus.PENDING for item in self.findings):
            return EvidenceExceptionGovernanceStatus.PENDING
        return EvidenceExceptionGovernanceStatus.GOVERNED

    @property
    def next_actions(self) -> tuple[str, ...]:
        actions = tuple(dict.fromkeys(item.remediation for item in self.findings if item.remediation))
        return actions or ('Retain the exact Wave 75 package, review record, authority artifacts and bounded exception references until their external validity ends.',)

    def to_dict(self) -> dict[str, Any]:
        accepted = tuple(item.finding_code for item in self.review.exceptions if item.disposition is EvidenceExceptionDisposition.ACCEPTED)
        return {
            'schema_version': 1, 'governance_id': self.governance_id, 'status': self.status.value, 'review': self.review.to_dict(),
            'findings': [item.to_dict() for item in self.findings], 'metadata': dict(self.metadata), 'generated_at': self.generated_at,
            'next_actions': self.next_actions, 'accepted_exception_finding_codes': accepted,
            'underlying_evidence_status': self.review.dossier.status.value, 'underlying_evidence_status_changed': False,
            'accepted_exception_creates_synthetic_pass': False, 'historical_wave74_wave75_truth_mutated': False,
            'governance_is_documentary_only': True, 'monitoring_performed_by_framework': False,
            'incident_response_performed_by_framework': False, 'rollback_performed_by_framework': False,
            'deployment_performed_by_framework': False, 'publication_performed_by_framework': False,
        }


def _governance_identity_payload(review: LongitudinalAssuranceReviewRecord, findings: Sequence[EvidenceExceptionGovernanceFinding], metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {'review_id': review.review_id, 'findings': [item.to_dict() for item in findings], 'metadata': dict(metadata)}


def build_evidence_exception_governance_dossier(
    review: LongitudinalAssuranceReviewRecord, *, now: datetime | str | None = None, artifact_base_dir: str | Path | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceExceptionGovernanceDossier:
    moment = _moment(now or review.reviewed_at); findings: list[EvidenceExceptionGovernanceFinding] = []
    archive = verify_longitudinal_operational_assurance_archive(review.dossier_archive.path, expected_dossier=review.dossier)
    if archive.status is LongitudinalAssuranceArchiveStatus.PENDING:
        findings.append(EvidenceExceptionGovernanceFinding('governance_wave75_archive_missing', EvidenceExceptionGovernanceStatus.PENDING, 'The bound Wave 75 package is missing.', 'Restore the exact package before governance can remain current.'))
    elif archive.status is LongitudinalAssuranceArchiveStatus.BLOCKED or archive.sha256 != review.dossier_archive.sha256:
        findings.append(EvidenceExceptionGovernanceFinding('governance_wave75_archive_changed', EvidenceExceptionGovernanceStatus.BLOCKED, 'The bound Wave 75 package is changed, unsafe, invalid or identity-mismatched.', 'Restore the exact immutable Wave 75 package or issue a new review against new evidence.'))
    if review.framework_version != FRAMEWORK_VERSION or review.nicegui_required != NICEGUI_VERSION:
        findings.append(EvidenceExceptionGovernanceFinding('governance_runtime_identity_mismatch', EvidenceExceptionGovernanceStatus.BLOCKED, 'The persisted review does not match this framework and exact NiceGUI identity.', 'Use a review bound to this exact framework/runtime identity.'))
    if review.authority_revoked:
        findings.append(EvidenceExceptionGovernanceFinding('governance_authority_revoked', EvidenceExceptionGovernanceStatus.PENDING, 'Review authority is revoked.', 'Obtain current authority and issue a new review.'))
    if review.authority_expires_at is None or _parse_time(review.authority_expires_at) <= moment:
        findings.append(EvidenceExceptionGovernanceFinding('governance_authority_not_current', EvidenceExceptionGovernanceStatus.PENDING, 'Review authority is missing or expired.', 'Renew the external review authority.'))
    for f in _artifact_findings(review.artifacts, artifact_base_dir):
        findings.append(EvidenceExceptionGovernanceFinding(
            'governance_'+f.code, EvidenceExceptionGovernanceStatus.BLOCKED if f.status is LongitudinalAssuranceReviewStatus.BLOCKED else EvidenceExceptionGovernanceStatus.PENDING,
            f.message, f.remediation,
        ))
    if review.status is LongitudinalAssuranceReviewStatus.BLOCKED:
        findings.append(EvidenceExceptionGovernanceFinding('governance_review_blocked', EvidenceExceptionGovernanceStatus.BLOCKED, 'The Wave 76 review record is BLOCKED.', 'Resolve contradictory/tampered review evidence and issue a new record.'))
    elif review.status is LongitudinalAssuranceReviewStatus.PENDING:
        findings.append(EvidenceExceptionGovernanceFinding('governance_review_pending', EvidenceExceptionGovernanceStatus.PENDING, 'The review record still has unresolved authority or exception obligations.', 'Complete the missing review authority/evidence/exception requirements.'))
    accepted = {e.finding_code: e for e in review.exceptions if e.disposition is EvidenceExceptionDisposition.ACCEPTED}
    for source in review.dossier.ledger.findings:
        if source.status is OperationalAssuranceLedgerStatus.BLOCKED:
            findings.append(EvidenceExceptionGovernanceFinding('governance_blocked_underlying_evidence', EvidenceExceptionGovernanceStatus.BLOCKED, f'Underlying Wave 75 evidence remains BLOCKED: {source.code}.', 'Correct the contradictory/tampered evidence; blocked evidence cannot become synthetic PASS.'))
        elif source.status is OperationalAssuranceLedgerStatus.PENDING:
            exc = accepted.get(source.code)
            if exc is None:
                findings.append(EvidenceExceptionGovernanceFinding('governance_unresolved_evidence_gap', EvidenceExceptionGovernanceStatus.PENDING, f'Underlying evidence gap remains unresolved: {source.code}.', 'Resolve the evidence gap or attach an approved bounded exception.'))
            elif exc.expires_at is None or _parse_time(exc.expires_at) <= moment:
                findings.append(EvidenceExceptionGovernanceFinding('governance_exception_not_current', EvidenceExceptionGovernanceStatus.PENDING, f'Accepted exception for {source.code} is missing expiry or expired.', 'Renew the bounded exception or resolve the underlying evidence gap.'))
    values = dict(metadata or {})
    payload = _governance_identity_payload(review, findings, values)
    return EvidenceExceptionGovernanceDossier(_canonical_digest(payload), review, tuple(findings), values, _iso(moment))


def evidence_exception_governance_dossier_from_dict(payload: Mapping[str, Any]) -> EvidenceExceptionGovernanceDossier:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported Wave 76 governance schema {payload.get("schema_version")!r}')
    review_payload = payload.get('review')
    if not isinstance(review_payload, Mapping):
        raise TypeError('Wave 76 governance dossier requires a review object')
    review = longitudinal_assurance_review_record_from_dict(review_payload)
    findings = tuple(EvidenceExceptionGovernanceFinding(str(item['code']), EvidenceExceptionGovernanceStatus(str(item['status'])), str(item['message']), str(item.get('remediation', ''))) for item in payload.get('findings', ()))
    obj = EvidenceExceptionGovernanceDossier(str(payload['governance_id']), review, findings, dict(payload.get('metadata') or {}), str(payload.get('generated_at') or _utc_now()))
    if obj.governance_id != _canonical_digest(_governance_identity_payload(obj.review, obj.findings, obj.metadata)):
        raise ValueError('Wave 76 governance id does not match persisted content')
    if payload.get('status') is not None and str(payload['status']) != obj.status.value:
        raise ValueError('Wave 76 governance status does not match persisted content')
    return obj


def write_evidence_exception_governance_dossier(path: str | Path, dossier: EvidenceExceptionGovernanceDossier) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dossier.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)+'\n', encoding='utf-8')
    return target


def read_evidence_exception_governance_dossier(path: str | Path) -> EvidenceExceptionGovernanceDossier:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('Wave 76 governance JSON must contain an object')
    return evidence_exception_governance_dossier_from_dict(payload)


@dataclass(frozen=True, slots=True)
class EvidenceExceptionGovernancePackage:
    path: str
    sha256: str
    governance_id: str
    review_id: str
    dossier_id: str
    status: EvidenceExceptionGovernanceStatus
    entries: tuple[str, ...]

    def __post_init__(self) -> None:
        if any(len(v) != 64 for v in (self.sha256, self.governance_id, self.review_id, self.dossier_id)):
            raise ValueError('Wave 76 package requires sha256-bound identities')
        object.__setattr__(self, 'status', EvidenceExceptionGovernanceStatus(self.status)); object.__setattr__(self, 'entries', tuple(self.entries))

    def to_dict(self) -> dict[str, Any]:
        return {'path': self.path, 'sha256': self.sha256, 'governance_id': self.governance_id, 'review_id': self.review_id, 'dossier_id': self.dossier_id, 'status': self.status.value, 'entries': self.entries}


def package_evidence_exception_governance_dossier(
    path: str | Path, dossier: EvidenceExceptionGovernanceDossier, *, artifact_base_dir: str | Path | None = None, now: datetime | str | None = None,
) -> EvidenceExceptionGovernancePackage:
    refreshed = build_evidence_exception_governance_dossier(dossier.review, artifact_base_dir=artifact_base_dir, now=now or dossier.generated_at, metadata=dossier.metadata)
    if refreshed.status is EvidenceExceptionGovernanceStatus.BLOCKED:
        raise ValueError('Wave 76 governance package cannot be created from BLOCKED or changed evidence')
    if refreshed.governance_id != dossier.governance_id:
        raise ValueError('Wave 76 governance identity changed during package verification')
    archive = Path(refreshed.review.dossier_archive.path)
    if not archive.is_file():
        raise ValueError('Wave 75 longitudinal package is missing')
    archive_blob = archive.read_bytes()
    if hashlib.sha256(archive_blob).hexdigest() != refreshed.review.dossier_archive.sha256:
        raise ValueError('Wave 75 longitudinal package changed after review binding')
    entries: dict[str, bytes] = {
        'evidence-exception-governance.json': _json_bytes(refreshed.to_dict()),
        'longitudinal-assurance-review.json': _json_bytes(refreshed.review.to_dict()),
        'wave75/longitudinal-assurance.zip': archive_blob,
    }
    for index, artifact in enumerate(refreshed.review.artifacts, start=1):
        source = _resolve_artifact_path(artifact, artifact_base_dir)
        if not source.is_file():
            continue
        blob = source.read_bytes()
        if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
            raise ValueError(f'Wave 76 review artifact changed: {artifact.path}')
        entries[f'review-artifacts/{index:04d}-{_safe_component(artifact.key)}-{_safe_component(source.name)}'] = blob
    manifest = ''.join(f'{hashlib.sha256(entries[name]).hexdigest()}  {name}\n' for name in sorted(entries))
    entries['MANIFEST.sha256'] = manifest.encode('utf-8')
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w') as out:
        for name in sorted(entries):
            pure = PurePosixPath(name)
            if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                raise ValueError(f'unsafe Wave 76 package entry {name!r}')
            out.writestr(_zip_info(name), entries[name])
    return EvidenceExceptionGovernancePackage(
        str(target), hashlib.sha256(target.read_bytes()).hexdigest(), refreshed.governance_id, refreshed.review.review_id,
        refreshed.review.dossier.dossier_id, refreshed.status, tuple(sorted(entries)),
    )


__all__ = [
    'EvidenceExceptionDisposition','EvidenceExceptionGovernanceDossier','EvidenceExceptionGovernanceFinding','EvidenceExceptionGovernancePackage','EvidenceExceptionGovernanceStatus',
    'JsonLongitudinalAssuranceReviewAdapter','LONGITUDINAL_ASSURANCE_REVIEW_ADAPTERS','LONGITUDINAL_EVIDENCE_EXCEPTION_POLICIES','LONGITUDINAL_EVIDENCE_EXCEPTION_POLICY',
    'LongitudinalAssuranceArchiveFinding','LongitudinalAssuranceArchiveStatus','LongitudinalAssuranceArchiveVerification',
    'LongitudinalAssuranceReviewAdapter','LongitudinalAssuranceReviewFinding','LongitudinalAssuranceReviewRecord','LongitudinalAssuranceReviewStatus',
    'LongitudinalEvidenceExceptionDecision','LongitudinalEvidenceExceptionPolicy',
    'build_evidence_exception_governance_dossier','build_longitudinal_assurance_review_record','evidence_exception_governance_dossier_from_dict',
    'load_longitudinal_assurance_review_manifest','longitudinal_assurance_review_record_from_dict','package_evidence_exception_governance_dossier',
    'read_evidence_exception_governance_dossier','read_longitudinal_assurance_review_record','verify_longitudinal_operational_assurance_archive',
    'write_evidence_exception_governance_dossier','write_longitudinal_assurance_review_record',
]
