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
from .semiconductor_orchestrator import PromotionDecisionStatus
from .semiconductor_promotion import PromotionCandidateStatus
from .semiconductor_release_audit import (
    ReleaseAuditClosure,
    ReleaseAuditStatus,
    read_release_audit_closure,
    release_audit_closure_from_dict,
)
from .semiconductor_execution import verify_stable_promotion_candidate_archive


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _resolve_artifact_path(artifact: TargetEvidenceArtifact, base_dir: str | Path | None) -> Path:
    path = Path(artifact.path)
    if path.is_absolute() or base_dir is None:
        return path
    return Path(base_dir) / path




def _target_evidence_artifact_from_dict(payload: Mapping[str, Any]) -> TargetEvidenceArtifact:
    return TargetEvidenceArtifact(
        str(payload['key']), str(payload['path']), str(payload['sha256']),
        int(payload['size_bytes']), str(payload.get('description', '')),
    )

def _safe_manifest_artifact_path(base: Path, value: str) -> Path:
    raw = Path(value)
    candidate = raw.resolve() if raw.is_absolute() else (base / raw).resolve()
    root = base.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f'stable release acceptance artifact path escapes acceptance base directory: {value!r}') from exc
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


class StableReleaseEvidenceAcceptanceStatus(str, Enum):
    ACCEPTED = 'accepted'
    PENDING = 'pending'
    BLOCKED = 'blocked'


class StablePromotionClosureStatus(str, Enum):
    CLOSED = 'closed'
    PENDING = 'pending'
    BLOCKED = 'blocked'


class ReleaseAuditArchiveStatus(str, Enum):
    VERIFIED = 'verified'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class ReleaseAuditArchiveFinding:
    code: str
    status: ReleaseAuditArchiveStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('release audit archive finding code and message must not be empty')
        object.__setattr__(self, 'status', ReleaseAuditArchiveStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class ReleaseAuditArchiveVerification:
    path: str
    sha256: str | None
    status: ReleaseAuditArchiveStatus
    audit_id: str | None = None
    candidate_id: str | None = None
    entries: tuple[str, ...] = ()
    findings: tuple[ReleaseAuditArchiveFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.sha256 is not None and len(self.sha256) != 64:
            raise ValueError('release audit archive sha256 must be 64 hex characters when present')
        object.__setattr__(self, 'status', ReleaseAuditArchiveStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def verified(self) -> bool:
        return self.status is ReleaseAuditArchiveStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': self.path, 'sha256': self.sha256, 'status': self.status.value, 'verified': self.verified,
            'audit_id': self.audit_id, 'candidate_id': self.candidate_id, 'entries': self.entries,
            'findings': [item.to_dict() for item in self.findings],
        }


def _blocked_archive(path: str | Path, code: str, message: str, remediation: str, *, sha256: str | None = None, entries: Sequence[str] = ()) -> ReleaseAuditArchiveVerification:
    return ReleaseAuditArchiveVerification(
        str(path), sha256, ReleaseAuditArchiveStatus.BLOCKED, entries=tuple(entries),
        findings=(ReleaseAuditArchiveFinding(code, ReleaseAuditArchiveStatus.BLOCKED, message, remediation),),
    )


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


def verify_release_audit_archive(
    path: str | Path,
    *,
    expected_audit: ReleaseAuditClosure | None = None,
) -> ReleaseAuditArchiveVerification:
    target = Path(path)
    if not target.is_file():
        return _blocked_archive(target, 'audit_archive_missing', 'The Wave 69 release-audit archive is unavailable.', 'Restore the exact immutable release-audit ZIP before stable release evidence acceptance.')
    data = target.read_bytes()
    archive_sha = hashlib.sha256(data).hexdigest()
    try:
        with zipfile.ZipFile(target) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if len(names) != len(set(names)):
                return _blocked_archive(target, 'audit_archive_duplicate_entry', 'The release-audit ZIP contains duplicate archive entries.', 'Recreate the audit package from the canonical Wave 69 packager.', sha256=archive_sha, entries=names)
            for name in names:
                pure = PurePosixPath(name)
                if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                    return _blocked_archive(target, 'audit_archive_unsafe_entry', f'The release-audit ZIP contains unsafe entry {name!r}.', 'Reject the archive and recreate it with the canonical Wave 69 packager.', sha256=archive_sha, entries=names)
            required = {'release-audit.json', 'handoff.json', 'execution-adapter-qualification.json', 'candidate/stable-promotion-candidate.zip', 'MANIFEST.sha256'}
            missing = sorted(required - set(names))
            if missing:
                return _blocked_archive(target, 'audit_archive_required_entry_missing', f'The release-audit ZIP is missing required entries: {missing}.', 'Recreate the complete self-contained Wave 69 audit package.', sha256=archive_sha, entries=names)
            try:
                expected_hashes = _parse_manifest(archive.read('MANIFEST.sha256'))
            except (UnicodeDecodeError, ValueError) as exc:
                return _blocked_archive(target, 'audit_archive_manifest_invalid', f'The release-audit manifest is invalid: {exc}', 'Recreate the audit package; do not repair manifest bytes manually.', sha256=archive_sha, entries=names)
            payload_names = set(names) - {'MANIFEST.sha256'}
            if set(expected_hashes) != payload_names:
                return _blocked_archive(target, 'audit_archive_manifest_incomplete', 'MANIFEST.sha256 does not cover exactly every non-manifest archive entry.', 'Recreate the audit package with complete deterministic hashing.', sha256=archive_sha, entries=names)
            for name, expected_sha in expected_hashes.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected_sha:
                    return _blocked_archive(target, 'audit_archive_hash_mismatch', f'Archive entry {name!r} does not match MANIFEST.sha256.', 'Reject changed audit bytes and restore/recreate the immutable audit package.', sha256=archive_sha, entries=names)
            try:
                audit_payload = json.loads(archive.read('release-audit.json').decode('utf-8'))
                if not isinstance(audit_payload, Mapping):
                    raise TypeError('release-audit.json must contain an object')
                audit = release_audit_closure_from_dict(audit_payload)
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                return _blocked_archive(target, 'audit_archive_payload_invalid', f'release-audit.json cannot be verified: {exc}', 'Recreate the audit package from a canonical Wave 69 ReleaseAuditClosure.', sha256=archive_sha, entries=names)
            if expected_audit is not None and audit.audit_id != expected_audit.audit_id:
                return _blocked_archive(target, 'audit_archive_identity_mismatch', 'The audit archive contains a different audit identity than the supplied closure.', 'Use the exact archive created for this release-audit closure.', sha256=archive_sha, entries=names)
            if audit.status is ReleaseAuditStatus.BLOCKED:
                return _blocked_archive(target, 'audit_archive_contains_blocked_audit', 'The release-audit archive contains a BLOCKED audit closure.', 'Resolve the Wave 69 audit blockers before final evidence acceptance.', sha256=archive_sha, entries=names)

            candidate_bytes = archive.read('candidate/stable-promotion-candidate.zip')
            if hashlib.sha256(candidate_bytes).hexdigest() != audit.handoff.candidate_archive.sha256:
                return _blocked_archive(target, 'audit_archive_candidate_hash_mismatch', 'Embedded candidate ZIP no longer matches the handoff-bound candidate archive SHA-256.', 'Restore the exact candidate archive and recreate the release-audit package.', sha256=archive_sha, entries=names)
            with tempfile.TemporaryDirectory(prefix='nicegui-base-wave70-audit-') as temp_dir:
                candidate_path = Path(temp_dir) / 'candidate.zip'
                candidate_path.write_bytes(candidate_bytes)
                candidate_verification = verify_stable_promotion_candidate_archive(candidate_path, expected_candidate=audit.handoff.candidate)
            if not candidate_verification.verified:
                return _blocked_archive(target, 'audit_archive_candidate_reverification_failed', 'Embedded candidate archive failed independent candidate verification.', 'Recreate the release-audit package from a verified Wave 67 candidate archive.', sha256=archive_sha, entries=names)

            # Independently bind every qualification and operation artifact in the self-contained package.
            qualification = audit.execution_adapter_qualification
            for artifact in qualification.artifacts:
                entry = f'adapter-evidence/{_safe_entry_component(artifact.key)}/{_safe_entry_component(Path(artifact.path).name)}'
                if entry not in payload_names:
                    return _blocked_archive(target, 'audit_archive_adapter_evidence_missing', f'Qualified adapter evidence {artifact.key!r} is missing from the audit archive.', 'Recreate the self-contained audit package with all qualified adapter evidence.', sha256=archive_sha, entries=names)
                blob = archive.read(entry)
                if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
                    return _blocked_archive(target, 'audit_archive_adapter_evidence_mismatch', f'Qualified adapter evidence {artifact.key!r} does not match its recorded hash/size.', 'Reject changed adapter evidence and recreate the audit package.', sha256=archive_sha, entries=names)
            for record in audit.operation_records:
                base = f'operations/{_safe_entry_component(record.recipe_key)}/{_safe_entry_component(record.kind.value)}'
                record_entry = f'{base}/record.json'
                if record_entry not in payload_names:
                    return _blocked_archive(target, 'audit_archive_operation_record_missing', f'Operation record is missing for {record.recipe_key}/{record.kind.value}.', 'Recreate the self-contained audit package.', sha256=archive_sha, entries=names)
                for item in record.evidence:
                    artifact = item.artifact
                    entry = (
                        f'{base}/evidence/{_safe_entry_component(item.step_key)}/'
                        f'{_safe_entry_component(item.evidence_key)}/{_safe_entry_component(Path(artifact.path).name)}'
                    )
                    if entry not in payload_names:
                        return _blocked_archive(target, 'audit_archive_operation_evidence_missing', f'Operation evidence {record.recipe_key}/{item.step_key}/{item.evidence_key} is missing.', 'Recreate the self-contained audit package with all bound operation evidence.', sha256=archive_sha, entries=names)
                    blob = archive.read(entry)
                    if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
                        return _blocked_archive(target, 'audit_archive_operation_evidence_mismatch', f'Operation evidence {record.recipe_key}/{item.step_key}/{item.evidence_key} does not match its recorded hash/size.', 'Reject changed operation evidence and recreate the audit package.', sha256=archive_sha, entries=names)
            return ReleaseAuditArchiveVerification(
                str(target), archive_sha, ReleaseAuditArchiveStatus.VERIFIED, audit.audit_id,
                audit.handoff.candidate.candidate_id, tuple(sorted(names)), (),
            )
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        return _blocked_archive(target, 'audit_archive_invalid', f'The release-audit ZIP cannot be read safely: {exc}', 'Restore or recreate the canonical Wave 69 release-audit package.', sha256=archive_sha)


@dataclass(frozen=True, slots=True)
class StableReleaseEvidenceAcceptanceFinding:
    code: str
    status: StableReleaseEvidenceAcceptanceStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('stable release evidence acceptance finding code and message must not be empty')
        object.__setattr__(self, 'status', StableReleaseEvidenceAcceptanceStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class StableReleaseEvidenceAcceptance:
    acceptance_id: str
    audit_id: str
    candidate_id: str
    audit_archive_sha256: str
    requested_status: StableReleaseEvidenceAcceptanceStatus
    artifacts: tuple[TargetEvidenceArtifact, ...]
    framework_version: str = FRAMEWORK_VERSION
    nicegui_required: str = NICEGUI_VERSION
    observed_framework_version: str | None = None
    observed_nicegui_version: str | None = None
    acceptance_authority: str | None = None
    approval_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    captured_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if any(len(value) != 64 for value in (self.acceptance_id, self.audit_id, self.candidate_id, self.audit_archive_sha256)):
            raise ValueError('stable release evidence acceptance requires sha256 acceptance/audit/candidate/archive identifiers')
        object.__setattr__(self, 'requested_status', StableReleaseEvidenceAcceptanceStatus(self.requested_status))
        artifacts = tuple(self.artifacts)
        if len({item.key for item in artifacts}) != len(artifacts):
            raise ValueError('stable release evidence acceptance contains duplicate artifact keys')
        object.__setattr__(self, 'artifacts', artifacts)
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'acceptance_id': self.acceptance_id, 'audit_id': self.audit_id,
            'candidate_id': self.candidate_id, 'audit_archive_sha256': self.audit_archive_sha256,
            'requested_status': self.requested_status.value, 'artifacts': [item.to_dict() for item in self.artifacts],
            'framework_version': self.framework_version, 'nicegui_required': self.nicegui_required,
            'observed_framework_version': self.observed_framework_version, 'observed_nicegui_version': self.observed_nicegui_version,
            'acceptance_authority': self.acceptance_authority, 'approval_reference': self.approval_reference,
            'metadata': dict(self.metadata), 'captured_at': self.captured_at,
            'external_authority_is_metadata_only': True,
            'acceptance_does_not_mutate_canonical_promotion_truth': True,
        }


def _acceptance_identity_payload(
    audit_id: str,
    candidate_id: str,
    audit_archive_sha256: str,
    requested_status: StableReleaseEvidenceAcceptanceStatus,
    artifacts: Sequence[TargetEvidenceArtifact],
    *,
    framework_version: str,
    nicegui_required: str,
    observed_framework_version: str | None,
    observed_nicegui_version: str | None,
    acceptance_authority: str | None,
    approval_reference: str | None,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'audit_id': audit_id, 'candidate_id': candidate_id, 'audit_archive_sha256': audit_archive_sha256,
        'requested_status': requested_status.value, 'artifacts': [item.to_dict() for item in artifacts],
        'framework_version': framework_version, 'nicegui_required': nicegui_required,
        'observed_framework_version': observed_framework_version, 'observed_nicegui_version': observed_nicegui_version,
        'acceptance_authority': acceptance_authority, 'approval_reference': approval_reference, 'metadata': dict(metadata),
    }


def build_stable_release_evidence_acceptance(
    audit: ReleaseAuditClosure,
    audit_archive_path: str | Path,
    *,
    requested_status: StableReleaseEvidenceAcceptanceStatus | str = StableReleaseEvidenceAcceptanceStatus.PENDING,
    artifacts: Sequence[TargetEvidenceArtifact] = (),
    observed_framework_version: str | None = None,
    observed_nicegui_version: str | None = None,
    acceptance_authority: str | None = None,
    approval_reference: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> StableReleaseEvidenceAcceptance:
    archive = Path(audit_archive_path)
    if not archive.is_file():
        raise FileNotFoundError(archive)
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    status = StableReleaseEvidenceAcceptanceStatus(requested_status)
    values = dict(metadata or {})
    payload = _acceptance_identity_payload(
        audit.audit_id, audit.handoff.candidate.candidate_id, archive_sha, status, tuple(artifacts),
        framework_version=FRAMEWORK_VERSION, nicegui_required=NICEGUI_VERSION,
        observed_framework_version=observed_framework_version, observed_nicegui_version=observed_nicegui_version,
        acceptance_authority=acceptance_authority, approval_reference=approval_reference, metadata=values,
    )
    return StableReleaseEvidenceAcceptance(
        _canonical_digest(payload), audit.audit_id, audit.handoff.candidate.candidate_id, archive_sha, status, tuple(artifacts),
        FRAMEWORK_VERSION, NICEGUI_VERSION, observed_framework_version, observed_nicegui_version,
        acceptance_authority, approval_reference, values,
    )


def stable_release_evidence_acceptance_from_dict(payload: Mapping[str, Any]) -> StableReleaseEvidenceAcceptance:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported stable release evidence acceptance schema {payload.get("schema_version")!r}')
    artifacts = tuple(_target_evidence_artifact_from_dict(item) for item in payload.get('artifacts', ()) if isinstance(item, Mapping))
    acceptance = StableReleaseEvidenceAcceptance(
        str(payload['acceptance_id']), str(payload['audit_id']), str(payload['candidate_id']), str(payload['audit_archive_sha256']),
        StableReleaseEvidenceAcceptanceStatus(str(payload['requested_status'])), artifacts,
        str(payload.get('framework_version') or FRAMEWORK_VERSION), str(payload.get('nicegui_required') or NICEGUI_VERSION),
        None if payload.get('observed_framework_version') is None else str(payload.get('observed_framework_version')),
        None if payload.get('observed_nicegui_version') is None else str(payload.get('observed_nicegui_version')),
        None if payload.get('acceptance_authority') is None else str(payload.get('acceptance_authority')),
        None if payload.get('approval_reference') is None else str(payload.get('approval_reference')),
        dict(payload.get('metadata') or {}), str(payload.get('captured_at') or _utc_now()),
    )
    expected = _canonical_digest(_acceptance_identity_payload(
        acceptance.audit_id, acceptance.candidate_id, acceptance.audit_archive_sha256, acceptance.requested_status, acceptance.artifacts,
        framework_version=acceptance.framework_version, nicegui_required=acceptance.nicegui_required,
        observed_framework_version=acceptance.observed_framework_version, observed_nicegui_version=acceptance.observed_nicegui_version,
        acceptance_authority=acceptance.acceptance_authority, approval_reference=acceptance.approval_reference, metadata=acceptance.metadata,
    ))
    if acceptance.acceptance_id != expected:
        raise ValueError('stable release evidence acceptance id does not match persisted content')
    return acceptance


def write_stable_release_evidence_acceptance(path: str | Path, acceptance: StableReleaseEvidenceAcceptance) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(acceptance.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_stable_release_evidence_acceptance(path: str | Path) -> StableReleaseEvidenceAcceptance:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('stable release evidence acceptance JSON must contain an object')
    return stable_release_evidence_acceptance_from_dict(payload)


def load_stable_release_evidence_acceptance_manifest(
    path: str | Path,
    audit: ReleaseAuditClosure,
    audit_archive_path: str | Path,
    *,
    artifact_base_dir: str | Path | None = None,
) -> StableReleaseEvidenceAcceptance:
    manifest = Path(path)
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('stable release evidence acceptance manifest must contain an object')
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported stable release evidence acceptance manifest schema {payload.get("schema_version")!r}')
    archive = Path(audit_archive_path)
    if not archive.is_file():
        raise FileNotFoundError(archive)
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    expected_values = {
        'audit_id': audit.audit_id,
        'candidate_id': audit.handoff.candidate.candidate_id,
        'audit_archive_sha256': archive_sha,
    }
    for key, expected in expected_values.items():
        supplied = payload.get(key)
        if supplied is not None and str(supplied) != expected:
            raise ValueError(f'stable release acceptance manifest {key} does not match supplied audit/archive')
    base = Path(artifact_base_dir).resolve() if artifact_base_dir is not None else manifest.parent.resolve()
    artifacts: list[TargetEvidenceArtifact] = []
    for spec in payload.get('artifacts', ()):
        if not isinstance(spec, Mapping):
            raise TypeError('stable release acceptance artifact must be an object')
        value = str(spec.get('path') or '')
        if not value:
            raise ValueError('stable release acceptance artifact path must not be empty')
        source = _safe_manifest_artifact_path(base, value)
        if source.is_file():
            artifact = capture_target_evidence_artifact(
                source, key=str(spec.get('key') or source.stem),
                description=str(spec.get('description') or 'stable release evidence acceptance artifact'),
            )
            expected_sha = spec.get('sha256')
            if expected_sha is not None and str(expected_sha) != artifact.sha256:
                metadata = dict(payload.get('metadata') or {})
                metadata.setdefault('manifest_artifact_sha256_mismatches', {})[artifact.key] = str(expected_sha)
                payload = dict(payload)
                payload['metadata'] = metadata
            artifacts.append(artifact)
        else:
            # Missing evidence is represented as no captured artifact; requested ACCEPTED therefore stays PENDING.
            metadata = dict(payload.get('metadata') or {})
            metadata.setdefault('missing_requested_artifact_paths', []).append(value)
            payload = dict(payload)
            payload['metadata'] = metadata
    return build_stable_release_evidence_acceptance(
        audit, archive,
        requested_status=str(payload.get('status') or payload.get('requested_status') or 'pending'),
        artifacts=artifacts,
        observed_framework_version=None if payload.get('framework_version') is None else str(payload.get('framework_version')),
        observed_nicegui_version=None if payload.get('nicegui_version') is None else str(payload.get('nicegui_version')),
        acceptance_authority=None if payload.get('acceptance_authority') is None else str(payload.get('acceptance_authority')),
        approval_reference=None if payload.get('approval_reference') is None else str(payload.get('approval_reference')),
        metadata=dict(payload.get('metadata') or {}),
    )


@dataclass(frozen=True, slots=True)
class StableReleaseEvidenceAcceptanceVerification:
    acceptance_id: str
    status: StableReleaseEvidenceAcceptanceStatus
    findings: tuple[StableReleaseEvidenceAcceptanceFinding, ...] = ()

    def __post_init__(self) -> None:
        if len(self.acceptance_id) != 64:
            raise ValueError('stable release evidence acceptance verification requires sha256 id')
        object.__setattr__(self, 'status', StableReleaseEvidenceAcceptanceStatus(self.status))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def accepted(self) -> bool:
        return self.status is StableReleaseEvidenceAcceptanceStatus.ACCEPTED

    @property
    def blocked(self) -> bool:
        return self.status is StableReleaseEvidenceAcceptanceStatus.BLOCKED

    def to_dict(self) -> dict[str, Any]:
        return {'acceptance_id': self.acceptance_id, 'status': self.status.value, 'accepted': self.accepted, 'findings': [item.to_dict() for item in self.findings]}


def verify_stable_release_evidence_acceptance(
    acceptance: StableReleaseEvidenceAcceptance,
    *,
    audit: ReleaseAuditClosure,
    audit_archive_path: str | Path,
    base_dir: str | Path | None = None,
) -> StableReleaseEvidenceAcceptanceVerification:
    findings: list[StableReleaseEvidenceAcceptanceFinding] = []
    if acceptance.framework_version != FRAMEWORK_VERSION or acceptance.nicegui_required != NICEGUI_VERSION:
        findings.append(StableReleaseEvidenceAcceptanceFinding('release_identity_mismatch', StableReleaseEvidenceAcceptanceStatus.BLOCKED, 'Persisted acceptance release identity does not match the current NiceGUI Base release authority.', 'Regenerate acceptance from the current framework and exact required NiceGUI runtime.'))
    if acceptance.audit_id != audit.audit_id or acceptance.candidate_id != audit.handoff.candidate.candidate_id:
        findings.append(StableReleaseEvidenceAcceptanceFinding('acceptance_subject_mismatch', StableReleaseEvidenceAcceptanceStatus.BLOCKED, 'Acceptance is bound to a different audit or candidate.', 'Import acceptance created for this exact release-audit/candidate identity.'))
    archive = Path(audit_archive_path)
    if not archive.is_file():
        findings.append(StableReleaseEvidenceAcceptanceFinding('audit_archive_unavailable', StableReleaseEvidenceAcceptanceStatus.BLOCKED, 'The accepted release-audit archive is unavailable.', 'Restore the exact archive accepted by the external release authority.'))
    else:
        observed_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        if observed_sha != acceptance.audit_archive_sha256:
            findings.append(StableReleaseEvidenceAcceptanceFinding('audit_archive_hash_mismatch', StableReleaseEvidenceAcceptanceStatus.BLOCKED, 'The release-audit ZIP differs from the exact archive bound to acceptance.', 'Use the immutable archive that the acceptance authority reviewed.'))
    if acceptance.requested_status is StableReleaseEvidenceAcceptanceStatus.BLOCKED:
        findings.append(StableReleaseEvidenceAcceptanceFinding('external_acceptance_blocked', StableReleaseEvidenceAcceptanceStatus.BLOCKED, 'The external release-evidence acceptance explicitly reports BLOCKED.', 'Resolve the external release authority blocker and import a fresh acceptance record.'))
    elif acceptance.requested_status is StableReleaseEvidenceAcceptanceStatus.PENDING:
        findings.append(StableReleaseEvidenceAcceptanceFinding('external_acceptance_pending', StableReleaseEvidenceAcceptanceStatus.PENDING, 'The external release-evidence acceptance is still PENDING.', 'Complete the external evidence acceptance process and import current traceable evidence.'))
    else:
        if not acceptance.acceptance_authority or not acceptance.approval_reference:
            findings.append(StableReleaseEvidenceAcceptanceFinding('acceptance_authority_untraced', StableReleaseEvidenceAcceptanceStatus.PENDING, 'Requested ACCEPTED lacks an external acceptance authority and approval reference.', 'Capture the approved external authority/reference; the framework does not infer them.'))
        if acceptance.observed_framework_version is None or acceptance.observed_nicegui_version is None:
            findings.append(StableReleaseEvidenceAcceptanceFinding('acceptance_execution_identity_missing', StableReleaseEvidenceAcceptanceStatus.PENDING, 'Requested ACCEPTED lacks observed framework or exact NiceGUI identity.', f'Record framework {FRAMEWORK_VERSION} and exact nicegui=={NICEGUI_VERSION} reviewed by the acceptance authority.'))
        else:
            if acceptance.observed_framework_version != FRAMEWORK_VERSION:
                findings.append(StableReleaseEvidenceAcceptanceFinding('framework_identity_mismatch', StableReleaseEvidenceAcceptanceStatus.BLOCKED, f'Acceptance observed framework {acceptance.observed_framework_version!r}, expected {FRAMEWORK_VERSION!r}.', 'Repeat acceptance against the current framework release.'))
            if acceptance.observed_nicegui_version != NICEGUI_VERSION:
                findings.append(StableReleaseEvidenceAcceptanceFinding('nicegui_identity_mismatch', StableReleaseEvidenceAcceptanceStatus.BLOCKED, f'Acceptance observed NiceGUI {acceptance.observed_nicegui_version!r}, expected exact {NICEGUI_VERSION!r}.', f'Repeat acceptance against exact nicegui=={NICEGUI_VERSION}.'))
        if not acceptance.artifacts:
            findings.append(StableReleaseEvidenceAcceptanceFinding('acceptance_artifacts_missing', StableReleaseEvidenceAcceptanceStatus.PENDING, 'Requested ACCEPTED has no captured acceptance artifact bytes.', 'Attach the immutable external approval/acceptance record before final closure.'))
    for artifact in acceptance.artifacts:
        source = _resolve_artifact_path(artifact, base_dir)
        if not source.is_file():
            findings.append(StableReleaseEvidenceAcceptanceFinding('acceptance_artifact_unavailable', StableReleaseEvidenceAcceptanceStatus.BLOCKED, f'Acceptance artifact {artifact.key!r} is unavailable at {source}.', 'Restore the exact accepted artifact bytes or recapture acceptance.'))
            continue
        blob = source.read_bytes()
        if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
            findings.append(StableReleaseEvidenceAcceptanceFinding('acceptance_artifact_hash_mismatch', StableReleaseEvidenceAcceptanceStatus.BLOCKED, f'Acceptance artifact {artifact.key!r} changed after capture.', 'Reject changed evidence and import a fresh externally accepted artifact.'))
    mismatches = acceptance.metadata.get('manifest_artifact_sha256_mismatches')
    if isinstance(mismatches, Mapping) and mismatches:
        findings.append(StableReleaseEvidenceAcceptanceFinding('manifest_artifact_hash_mismatch', StableReleaseEvidenceAcceptanceStatus.BLOCKED, 'Acceptance manifest expected SHA-256 values do not match captured artifact bytes.', 'Resolve the external manifest/artifact mismatch before acceptance.'))
    missing_paths = acceptance.metadata.get('missing_requested_artifact_paths')
    if isinstance(missing_paths, Sequence) and not isinstance(missing_paths, (str, bytes)) and missing_paths:
        findings.append(StableReleaseEvidenceAcceptanceFinding('requested_acceptance_artifact_missing', StableReleaseEvidenceAcceptanceStatus.PENDING, 'One or more requested acceptance artifact paths were not available at import time.', 'Provide the referenced external acceptance artifacts and rebuild the acceptance record.'))
    status = StableReleaseEvidenceAcceptanceStatus.ACCEPTED
    if any(item.status is StableReleaseEvidenceAcceptanceStatus.BLOCKED for item in findings):
        status = StableReleaseEvidenceAcceptanceStatus.BLOCKED
    elif any(item.status is StableReleaseEvidenceAcceptanceStatus.PENDING for item in findings):
        status = StableReleaseEvidenceAcceptanceStatus.PENDING
    return StableReleaseEvidenceAcceptanceVerification(acceptance.acceptance_id, status, tuple(findings))


@runtime_checkable
class StableReleaseEvidenceAcceptanceAdapter(Protocol):
    key: str
    def load(self, path: str | Path, audit: ReleaseAuditClosure, audit_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> StableReleaseEvidenceAcceptance: ...


@dataclass(frozen=True, slots=True)
class JsonStableReleaseEvidenceAcceptanceAdapter:
    key: str = 'json-manifest'
    def load(self, path: str | Path, audit: ReleaseAuditClosure, audit_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> StableReleaseEvidenceAcceptance:
        return load_stable_release_evidence_acceptance_manifest(path, audit, audit_archive_path, artifact_base_dir=artifact_base_dir)


STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS: Mapping[str, StableReleaseEvidenceAcceptanceAdapter] = MappingProxyType({'json-manifest': JsonStableReleaseEvidenceAcceptanceAdapter()})


@dataclass(frozen=True, slots=True)
class StablePromotionClosurePolicy:
    key: str = 'stable'
    target_version: str = '3.0.0'
    require_verified_audit_archive: bool = True
    require_closed_release_audit: bool = True
    require_ready_candidate: bool = True
    require_promotable_decision: bool = True
    require_accepted_release_evidence: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.target_version.strip():
            raise ValueError('stable promotion closure policy key and target version must not be empty')

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key, 'target_version': self.target_version,
            'require_verified_audit_archive': self.require_verified_audit_archive,
            'require_closed_release_audit': self.require_closed_release_audit,
            'require_ready_candidate': self.require_ready_candidate,
            'require_promotable_decision': self.require_promotable_decision,
            'require_accepted_release_evidence': self.require_accepted_release_evidence,
        }


STABLE_PROMOTION_CLOSURE_POLICY = StablePromotionClosurePolicy()
STABLE_PROMOTION_CLOSURE_POLICIES: Mapping[str, StablePromotionClosurePolicy] = MappingProxyType({'stable': STABLE_PROMOTION_CLOSURE_POLICY})


@dataclass(frozen=True, slots=True)
class StablePromotionClosureFinding:
    code: str
    status: StablePromotionClosureStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('stable promotion closure finding code and message must not be empty')
        object.__setattr__(self, 'status', StablePromotionClosureStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class StableReleasePromotionClosure:
    closure_id: str
    release_audit: ReleaseAuditClosure
    audit_archive: TargetEvidenceArtifact
    evidence_acceptance: StableReleaseEvidenceAcceptance
    policy: StablePromotionClosurePolicy = STABLE_PROMOTION_CLOSURE_POLICY
    findings: tuple[StablePromotionClosureFinding, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.closure_id) != 64:
            raise ValueError('stable release promotion closure requires sha256 id')
        object.__setattr__(self, 'findings', tuple(self.findings))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def status(self) -> StablePromotionClosureStatus:
        if any(item.status is StablePromotionClosureStatus.BLOCKED for item in self.findings):
            return StablePromotionClosureStatus.BLOCKED
        if any(item.status is StablePromotionClosureStatus.PENDING for item in self.findings):
            return StablePromotionClosureStatus.PENDING
        return StablePromotionClosureStatus.CLOSED

    @property
    def closed(self) -> bool:
        return self.status is StablePromotionClosureStatus.CLOSED

    @property
    def next_actions(self) -> tuple[str, ...]:
        actions = tuple(dict.fromkeys(item.remediation for item in self.findings if item.remediation.strip()))
        if actions:
            return actions
        return ('Retain the immutable closure package with the external release authority record; publication/deployment remains outside the generic framework.',)

    def to_dict(self) -> dict[str, Any]:
        candidate = self.release_audit.handoff.candidate
        return {
            'schema_version': 1, 'closure_id': self.closure_id, 'status': self.status.value, 'closed': self.closed,
            'target_version': self.policy.target_version, 'release_audit': self.release_audit.to_dict(),
            'audit_archive': self.audit_archive.to_dict(), 'evidence_acceptance': self.evidence_acceptance.to_dict(),
            'policy': self.policy.to_dict(), 'findings': [item.to_dict() for item in self.findings],
            'metadata': dict(self.metadata), 'generated_at': self.generated_at, 'next_actions': self.next_actions,
            'candidate_status': candidate.status.value, 'canonical_promotion_decision': candidate.evidence.decision.status.value,
            'affects_candidate_status': False, 'affects_target_gate_status': False,
            'deployment_performed_by_framework': False, 'stable_release_published_by_framework': False,
            'external_authority_is_interpreted_by_framework': False,
            'closure_records_verified_evidence_acceptance_only': True,
        }


def _closure_identity_payload(
    audit: ReleaseAuditClosure,
    audit_archive: TargetEvidenceArtifact,
    acceptance: StableReleaseEvidenceAcceptance,
    policy: StablePromotionClosurePolicy,
    findings: Sequence[StablePromotionClosureFinding],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'audit_id': audit.audit_id, 'candidate_id': audit.handoff.candidate.candidate_id,
        'audit_archive': audit_archive.to_dict(), 'acceptance_id': acceptance.acceptance_id,
        'policy': policy.to_dict(), 'findings': [item.to_dict() for item in findings], 'metadata': dict(metadata),
    }


def _promotion_closure_findings(
    audit: ReleaseAuditClosure,
    audit_archive: TargetEvidenceArtifact,
    acceptance: StableReleaseEvidenceAcceptance,
    policy: StablePromotionClosurePolicy,
    *,
    artifact_base_dir: str | Path | None = None,
) -> tuple[StablePromotionClosureFinding, ...]:
    findings: list[StablePromotionClosureFinding] = []
    archive_path = _resolve_artifact_path(audit_archive, artifact_base_dir)
    archive_verification = verify_release_audit_archive(archive_path, expected_audit=audit)
    if policy.require_verified_audit_archive and not archive_verification.verified:
        findings.append(StablePromotionClosureFinding('release_audit_archive_not_verified', StablePromotionClosureStatus.BLOCKED, 'The immutable Wave 69 release-audit package does not independently verify.', 'Restore the exact self-contained verified release-audit ZIP before closure.'))
    if archive_path.is_file():
        blob = archive_path.read_bytes()
        if len(blob) != audit_archive.size_bytes or hashlib.sha256(blob).hexdigest() != audit_archive.sha256:
            findings.append(StablePromotionClosureFinding('release_audit_archive_artifact_mismatch', StablePromotionClosureStatus.BLOCKED, 'The closure-bound release-audit artifact changed after capture.', 'Use the exact immutable audit archive captured for this closure.'))
    candidate = audit.handoff.candidate
    if candidate.target_version != policy.target_version:
        findings.append(StablePromotionClosureFinding('target_version_mismatch', StablePromotionClosureStatus.BLOCKED, f'Candidate targets {candidate.target_version!r}, closure policy targets {policy.target_version!r}.', 'Use the matching stable release-channel policy/candidate.'))
    if policy.require_closed_release_audit:
        if audit.status is ReleaseAuditStatus.BLOCKED:
            findings.append(StablePromotionClosureFinding('release_audit_blocked', StablePromotionClosureStatus.BLOCKED, 'The canonical Wave 69 release audit is BLOCKED.', 'Resolve release-audit blockers before final closure.'))
        elif audit.status is not ReleaseAuditStatus.CLOSED:
            findings.append(StablePromotionClosureFinding('release_audit_not_closed', StablePromotionClosureStatus.PENDING, 'The canonical Wave 69 release audit is not CLOSED.', 'Complete the required handoff/adapter/operation evidence first.'))
    if policy.require_ready_candidate:
        if candidate.status is PromotionCandidateStatus.BLOCKED:
            findings.append(StablePromotionClosureFinding('candidate_blocked', StablePromotionClosureStatus.BLOCKED, 'The canonical Wave 67 stable-promotion candidate is BLOCKED.', 'Resolve canonical candidate blockers; final closure cannot override them.'))
        elif candidate.status is not PromotionCandidateStatus.READY:
            findings.append(StablePromotionClosureFinding('candidate_not_ready', StablePromotionClosureStatus.PENDING, 'The canonical Wave 67 stable-promotion candidate is not READY.', 'Complete canonical target evidence and rehearsals before closure.'))
    decision = candidate.evidence.decision
    if policy.require_promotable_decision:
        if decision.status is PromotionDecisionStatus.BLOCKED:
            findings.append(StablePromotionClosureFinding('promotion_decision_blocked', StablePromotionClosureStatus.BLOCKED, 'The canonical Wave 66 stable-promotion decision is BLOCKED.', 'Resolve canonical promotion findings; Wave 70 cannot override them.'))
        elif decision.status is not PromotionDecisionStatus.PROMOTABLE:
            findings.append(StablePromotionClosureFinding('promotion_decision_not_promotable', StablePromotionClosureStatus.PENDING, 'The canonical Wave 66 stable-promotion decision is not PROMOTABLE.', 'Complete the canonical target/provider/runtime/browser/human evidence first.'))
    acceptance_verification = verify_stable_release_evidence_acceptance(
        acceptance, audit=audit, audit_archive_path=archive_path, base_dir=artifact_base_dir,
    )
    if policy.require_accepted_release_evidence:
        if acceptance_verification.status is StableReleaseEvidenceAcceptanceStatus.BLOCKED:
            findings.append(StablePromotionClosureFinding('release_evidence_acceptance_blocked', StablePromotionClosureStatus.BLOCKED, 'External stable-release evidence acceptance is BLOCKED.', 'Resolve acceptance evidence/identity failures and import a fresh acceptance record.'))
        elif acceptance_verification.status is not StableReleaseEvidenceAcceptanceStatus.ACCEPTED:
            findings.append(StablePromotionClosureFinding('release_evidence_not_accepted', StablePromotionClosureStatus.PENDING, 'External stable-release evidence is not yet artifact-backed ACCEPTED.', 'Complete external evidence acceptance and attach current immutable acceptance artifacts.'))
    return tuple(findings)


def build_stable_release_promotion_closure(
    audit: ReleaseAuditClosure,
    audit_archive_path: str | Path,
    evidence_acceptance: StableReleaseEvidenceAcceptance,
    *,
    policy: StablePromotionClosurePolicy = STABLE_PROMOTION_CLOSURE_POLICY,
    artifact_base_dir: str | Path | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> StableReleasePromotionClosure:
    archive_path = Path(audit_archive_path)
    if not archive_path.is_file():
        # Capture a synthetic identity is unsafe; closure requires the actual bound archive bytes.
        raise FileNotFoundError(archive_path)
    archive_artifact = capture_target_evidence_artifact(archive_path, key='release-audit-package', description='immutable Wave 69 release-audit package')
    findings = _promotion_closure_findings(audit, archive_artifact, evidence_acceptance, policy, artifact_base_dir=artifact_base_dir)
    values = dict(metadata or {})
    payload = _closure_identity_payload(audit, archive_artifact, evidence_acceptance, policy, findings, values)
    return StableReleasePromotionClosure(_canonical_digest(payload), audit, archive_artifact, evidence_acceptance, policy, findings, values)


def stable_release_promotion_closure_from_dict(payload: Mapping[str, Any]) -> StableReleasePromotionClosure:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported stable release promotion closure schema {payload.get("schema_version")!r}')
    audit_payload = payload.get('release_audit')
    archive_payload = payload.get('audit_archive')
    acceptance_payload = payload.get('evidence_acceptance')
    policy_payload = payload.get('policy') or {}
    if not isinstance(audit_payload, Mapping) or not isinstance(archive_payload, Mapping) or not isinstance(acceptance_payload, Mapping):
        raise TypeError('stable release promotion closure requires release_audit, audit_archive and evidence_acceptance objects')
    audit = release_audit_closure_from_dict(audit_payload)
    archive = _target_evidence_artifact_from_dict(archive_payload)
    acceptance = stable_release_evidence_acceptance_from_dict(acceptance_payload)
    policy = StablePromotionClosurePolicy(
        str(policy_payload.get('key', 'stable')), str(policy_payload.get('target_version', '3.0.0')),
        bool(policy_payload.get('require_verified_audit_archive', True)), bool(policy_payload.get('require_closed_release_audit', True)),
        bool(policy_payload.get('require_ready_candidate', True)), bool(policy_payload.get('require_promotable_decision', True)),
        bool(policy_payload.get('require_accepted_release_evidence', True)),
    )
    findings = tuple(
        StablePromotionClosureFinding(str(item['code']), StablePromotionClosureStatus(str(item['status'])), str(item['message']), str(item.get('remediation', '')))
        for item in payload.get('findings', ()) if isinstance(item, Mapping)
    )
    closure = StableReleasePromotionClosure(
        str(payload['closure_id']), audit, archive, acceptance, policy, findings,
        dict(payload.get('metadata') or {}), str(payload.get('generated_at') or _utc_now()),
    )
    expected = _canonical_digest(_closure_identity_payload(audit, archive, acceptance, policy, findings, closure.metadata))
    if closure.closure_id != expected:
        raise ValueError('stable release promotion closure id does not match persisted content')
    if payload.get('status') is not None and str(payload.get('status')) != closure.status.value:
        raise ValueError('stable release promotion closure status does not match persisted content')
    return closure


def write_stable_release_promotion_closure(path: str | Path, closure: StableReleasePromotionClosure) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(closure.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_stable_release_promotion_closure(path: str | Path) -> StableReleasePromotionClosure:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('stable release promotion closure JSON must contain an object')
    return stable_release_promotion_closure_from_dict(payload)


@dataclass(frozen=True, slots=True)
class StablePromotionClosurePackage:
    path: str
    sha256: str
    closure_id: str
    status: StablePromotionClosureStatus
    entries: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or len(self.closure_id) != 64:
            raise ValueError('stable promotion closure package requires sha256 package/closure identifiers')
        object.__setattr__(self, 'status', StablePromotionClosureStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))

    def to_dict(self) -> dict[str, Any]:
        return {'path': self.path, 'sha256': self.sha256, 'closure_id': self.closure_id, 'status': self.status.value, 'entries': self.entries}


def package_stable_release_promotion_closure(
    path: str | Path,
    closure: StableReleasePromotionClosure,
    *,
    artifact_base_dir: str | Path | None = None,
) -> StablePromotionClosurePackage:
    audit_archive_path = _resolve_artifact_path(closure.audit_archive, artifact_base_dir)
    refreshed = build_stable_release_promotion_closure(
        closure.release_audit, audit_archive_path, closure.evidence_acceptance,
        policy=closure.policy, artifact_base_dir=artifact_base_dir, metadata=closure.metadata,
    )
    if refreshed.status is StablePromotionClosureStatus.BLOCKED:
        raise ValueError('stable promotion closure package cannot be created from BLOCKED or changed evidence')
    if refreshed.closure_id != closure.closure_id:
        raise ValueError('stable promotion closure identity changed during package verification')
    entries: dict[str, bytes] = {
        'promotion-closure.json': _json_bytes(refreshed.to_dict()),
        'release-evidence-acceptance.json': _json_bytes(refreshed.evidence_acceptance.to_dict()),
        'release-audit/release-audit.zip': audit_archive_path.read_bytes(),
    }
    for artifact in refreshed.evidence_acceptance.artifacts:
        source = _resolve_artifact_path(artifact, artifact_base_dir)
        if not source.is_file():
            continue
        blob = source.read_bytes()
        if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
            raise ValueError(f'stable release acceptance artifact changed: {artifact.key}')
        entries[f'acceptance-evidence/{_safe_entry_component(artifact.key)}/{_safe_entry_component(source.name)}'] = blob
    manifest = ''.join(f'{hashlib.sha256(entries[name]).hexdigest()}  {name}\n' for name in sorted(entries))
    entries['MANIFEST.sha256'] = manifest.encode('utf-8')
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w') as archive:
        for name in sorted(entries):
            pure = PurePosixPath(name)
            if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                raise ValueError(f'unsafe stable promotion closure archive entry {name!r}')
            archive.writestr(_zip_info(name), entries[name])
    return StablePromotionClosurePackage(str(target), hashlib.sha256(target.read_bytes()).hexdigest(), closure.closure_id, closure.status, tuple(sorted(entries)))


__all__ = [
    'JsonStableReleaseEvidenceAcceptanceAdapter','ReleaseAuditArchiveFinding','ReleaseAuditArchiveStatus','ReleaseAuditArchiveVerification',
    'STABLE_PROMOTION_CLOSURE_POLICIES','STABLE_PROMOTION_CLOSURE_POLICY','STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS',
    'StablePromotionClosureFinding','StablePromotionClosurePackage','StablePromotionClosurePolicy','StablePromotionClosureStatus',
    'StableReleaseEvidenceAcceptance','StableReleaseEvidenceAcceptanceAdapter','StableReleaseEvidenceAcceptanceFinding',
    'StableReleaseEvidenceAcceptanceStatus','StableReleaseEvidenceAcceptanceVerification','StableReleasePromotionClosure',
    'build_stable_release_evidence_acceptance','build_stable_release_promotion_closure','load_stable_release_evidence_acceptance_manifest',
    'package_stable_release_promotion_closure','read_stable_release_evidence_acceptance','read_stable_release_promotion_closure',
    'stable_release_evidence_acceptance_from_dict','stable_release_promotion_closure_from_dict','verify_release_audit_archive',
    'verify_stable_release_evidence_acceptance','write_stable_release_evidence_acceptance','write_stable_release_promotion_closure',
]
