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
from .semiconductor_stability import (
    PostReleaseStabilityStatus,
    RollbackReadinessStatus,
    StableRollbackReadinessVerification,
    post_release_stability_evidence_from_dict,
    stable_rollback_readiness_verification_from_dict,
    verify_stable_post_promotion_archive,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


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
        raise ValueError(f'Wave 73 artifact path escapes manifest base directory: {value!r}') from exc
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


def _artifact_findings(
    artifacts: Sequence[TargetEvidenceArtifact], *, base_dir: str | Path | None, required_keys: Sequence[str],
    finding_type, pending_status: Enum, blocked_status: Enum, subject: str, prefix: str,
):
    findings = []
    keys = {item.key for item in artifacts}
    for key in required_keys:
        if key not in keys:
            findings.append(finding_type(
                f'{prefix}_required_artifact_missing', pending_status,
                f'Required {subject} artifact {key!r} is missing.',
                f'Capture and attach {key!r} from the authoritative external company process.',
            ))
    for artifact in artifacts:
        source = _resolve_artifact_path(artifact, base_dir)
        if not source.is_file():
            findings.append(finding_type(
                f'{prefix}_artifact_unavailable', blocked_status,
                f'{subject.title()} artifact {artifact.key!r} is unavailable.',
                f'Restore the exact captured {subject} artifact bytes.',
            ))
            continue
        blob = source.read_bytes()
        if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
            findings.append(finding_type(
                f'{prefix}_artifact_hash_mismatch', blocked_status,
                f'{subject.title()} artifact {artifact.key!r} changed after capture.',
                f'Reject changed {subject} evidence and recapture it from the authoritative external process.',
            ))
    return findings


class StableRollbackReadinessArchiveStatus(str, Enum):
    VERIFIED = 'verified'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class StableRollbackReadinessArchiveFinding:
    code: str
    status: StableRollbackReadinessArchiveStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('rollback-readiness archive finding code and message must not be empty')
        object.__setattr__(self, 'status', StableRollbackReadinessArchiveStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class StableRollbackReadinessArchiveVerification:
    path: str
    sha256: str | None
    status: StableRollbackReadinessArchiveStatus
    readiness_id: str | None = None
    stability_id: str | None = None
    post_verification_id: str | None = None
    entries: tuple[str, ...] = ()
    findings: tuple[StableRollbackReadinessArchiveFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.sha256 is not None and (len(self.sha256) != 64 or any(ch not in '0123456789abcdef' for ch in self.sha256.lower())):
            raise ValueError('rollback-readiness archive sha256 must be 64 hex characters when present')
        object.__setattr__(self, 'status', StableRollbackReadinessArchiveStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def verified(self) -> bool:
        return self.status is StableRollbackReadinessArchiveStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': self.path, 'sha256': self.sha256, 'status': self.status.value, 'verified': self.verified,
            'readiness_id': self.readiness_id, 'stability_id': self.stability_id,
            'post_verification_id': self.post_verification_id, 'entries': self.entries,
            'findings': [item.to_dict() for item in self.findings],
        }


def _blocked_readiness_archive(path: str | Path, code: str, message: str, remediation: str, *, sha256: str | None = None, entries: Sequence[str] = ()) -> StableRollbackReadinessArchiveVerification:
    return StableRollbackReadinessArchiveVerification(
        str(path), sha256, StableRollbackReadinessArchiveStatus.BLOCKED, entries=tuple(entries),
        findings=(StableRollbackReadinessArchiveFinding(code, StableRollbackReadinessArchiveStatus.BLOCKED, message, remediation),),
    )


def verify_stable_rollback_readiness_archive(
    path: str | Path, *, expected_readiness: StableRollbackReadinessVerification | None = None,
) -> StableRollbackReadinessArchiveVerification:
    target = Path(path)
    if not target.is_file():
        return _blocked_readiness_archive(
            target, 'rollback_readiness_archive_missing', 'The Wave 72 rollback-readiness archive is unavailable.',
            'Restore the exact immutable Wave 72 rollback-readiness ZIP before sustained-operations acceptance.',
        )
    data = target.read_bytes()
    archive_sha = hashlib.sha256(data).hexdigest()
    try:
        with zipfile.ZipFile(target) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if len(names) != len(set(names)):
                return _blocked_readiness_archive(target, 'rollback_readiness_archive_duplicate_entry', 'The Wave 72 ZIP contains duplicate entries.', 'Recreate it with the canonical Wave 72 packager.', sha256=archive_sha, entries=names)
            for name in names:
                pure = PurePosixPath(name)
                if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                    return _blocked_readiness_archive(target, 'rollback_readiness_archive_unsafe_entry', f'The Wave 72 ZIP contains unsafe entry {name!r}.', 'Reject the archive and recreate it with the canonical packager.', sha256=archive_sha, entries=names)
            required = {
                'rollback-readiness-verification.json', 'post-release-stability-evidence.json',
                'post-promotion/post-promotion-verification.zip', 'MANIFEST.sha256',
            }
            missing = sorted(required - set(names))
            if missing:
                return _blocked_readiness_archive(target, 'rollback_readiness_archive_required_entry_missing', f'The Wave 72 ZIP is missing required entries: {missing}.', 'Recreate the complete self-contained Wave 72 package.', sha256=archive_sha, entries=names)
            expected_hashes = _parse_manifest(archive.read('MANIFEST.sha256'))
            payload_names = set(names) - {'MANIFEST.sha256'}
            if set(expected_hashes) != payload_names:
                return _blocked_readiness_archive(target, 'rollback_readiness_archive_manifest_incomplete', 'MANIFEST.sha256 does not cover exactly every non-manifest archive entry.', 'Recreate the Wave 72 package with complete deterministic hashing.', sha256=archive_sha, entries=names)
            for name, expected_sha in expected_hashes.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected_sha:
                    return _blocked_readiness_archive(target, 'rollback_readiness_archive_hash_mismatch', f'Archive entry {name!r} does not match MANIFEST.sha256.', 'Reject changed bytes and restore/recreate the immutable Wave 72 package.', sha256=archive_sha, entries=names)

            readiness_payload = json.loads(archive.read('rollback-readiness-verification.json').decode('utf-8'))
            if not isinstance(readiness_payload, Mapping):
                raise TypeError('rollback-readiness-verification.json must contain an object')
            readiness = stable_rollback_readiness_verification_from_dict(readiness_payload)
            if expected_readiness is not None and readiness.readiness_id != expected_readiness.readiness_id:
                return _blocked_readiness_archive(target, 'rollback_readiness_archive_identity_mismatch', 'The Wave 72 archive contains a different rollback-readiness identity than supplied.', 'Use the exact Wave 72 archive created for this readiness record.', sha256=archive_sha, entries=names)

            stability_payload = json.loads(archive.read('post-release-stability-evidence.json').decode('utf-8'))
            if not isinstance(stability_payload, Mapping):
                raise TypeError('post-release-stability-evidence.json must contain an object')
            stability = post_release_stability_evidence_from_dict(stability_payload)
            if stability.stability_id != readiness.stability_evidence.stability_id:
                return _blocked_readiness_archive(target, 'rollback_readiness_archive_stability_mismatch', 'The separately embedded stability evidence does not match the rollback-readiness record.', 'Recreate the canonical self-contained Wave 72 package.', sha256=archive_sha, entries=names)

            nested = archive.read('post-promotion/post-promotion-verification.zip')
            if hashlib.sha256(nested).hexdigest() != readiness.post_promotion_archive.sha256:
                return _blocked_readiness_archive(target, 'rollback_readiness_archive_post_promotion_hash_mismatch', 'The nested Wave 71 archive does not match the hash bound to rollback readiness.', 'Restore the exact nested Wave 71 package and rebuild Wave 72.', sha256=archive_sha, entries=names)
            with tempfile.NamedTemporaryFile(suffix='.zip') as handle:
                handle.write(nested); handle.flush()
                nested_verification = verify_stable_post_promotion_archive(handle.name, expected_verification=readiness.post_verification)
            if not nested_verification.verified:
                return _blocked_readiness_archive(target, 'rollback_readiness_archive_nested_post_promotion_invalid', 'The nested Wave 71 post-promotion package does not independently verify.', 'Restore the exact verified Wave 71 package and rebuild Wave 72.', sha256=archive_sha, entries=names)
            return StableRollbackReadinessArchiveVerification(
                str(target), archive_sha, StableRollbackReadinessArchiveStatus.VERIFIED,
                readiness.readiness_id, readiness.stability_evidence.stability_id,
                readiness.post_verification.verification_id, tuple(names), (),
            )
    except Exception as exc:
        return _blocked_readiness_archive(target, 'rollback_readiness_archive_invalid', f'The Wave 72 rollback-readiness ZIP cannot be read safely: {exc}', 'Restore or recreate the canonical Wave 72 package.', sha256=archive_sha)


class SustainedOperationsAcceptanceStatus(str, Enum):
    ACCEPTED = 'accepted'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class SustainedOperationsAcceptancePolicy:
    key: str = 'stable'
    target_version: str = '3.0.0'
    required_artifact_keys: tuple[str, ...] = ('sustained-operations-window', 'incident-audit-summary')
    require_ready_rollback_readiness: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.target_version.strip() or not self.required_artifact_keys:
            raise ValueError('sustained-operations acceptance policy requires key, target version and artifact keys')
        values = tuple(dict.fromkeys(str(item).strip() for item in self.required_artifact_keys if str(item).strip()))
        if not values:
            raise ValueError('sustained-operations acceptance policy requires artifact keys')
        object.__setattr__(self, 'required_artifact_keys', values)

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key, 'target_version': self.target_version,
            'required_artifact_keys': self.required_artifact_keys,
            'require_ready_rollback_readiness': self.require_ready_rollback_readiness,
        }


SUSTAINED_OPERATIONS_ACCEPTANCE_POLICY = SustainedOperationsAcceptancePolicy()
SUSTAINED_OPERATIONS_ACCEPTANCE_POLICIES: Mapping[str, SustainedOperationsAcceptancePolicy] = MappingProxyType({'stable': SUSTAINED_OPERATIONS_ACCEPTANCE_POLICY})


@dataclass(frozen=True, slots=True)
class SustainedOperationsAcceptanceFinding:
    code: str
    status: SustainedOperationsAcceptanceStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('sustained-operations acceptance finding code and message must not be empty')
        object.__setattr__(self, 'status', SustainedOperationsAcceptanceStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class SustainedOperationsEvidenceAcceptance:
    acceptance_id: str
    readiness_id: str
    stability_id: str
    readiness_archive_sha256: str
    target_version: str
    requested_status: SustainedOperationsAcceptanceStatus
    artifacts: tuple[TargetEvidenceArtifact, ...]
    policy: SustainedOperationsAcceptancePolicy = SUSTAINED_OPERATIONS_ACCEPTANCE_POLICY
    framework_version: str = FRAMEWORK_VERSION
    nicegui_required: str = NICEGUI_VERSION
    observed_framework_version: str | None = None
    observed_nicegui_version: str | None = None
    acceptance_authority: str | None = None
    acceptance_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    captured_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if any(len(value) != 64 for value in (self.acceptance_id, self.readiness_id, self.stability_id, self.readiness_archive_sha256)):
            raise ValueError('sustained-operations acceptance requires sha256 acceptance/readiness/stability/archive identifiers')
        object.__setattr__(self, 'requested_status', SustainedOperationsAcceptanceStatus(self.requested_status))
        artifacts = tuple(self.artifacts)
        if len({item.key for item in artifacts}) != len(artifacts):
            raise ValueError('sustained-operations acceptance contains duplicate artifact keys')
        object.__setattr__(self, 'artifacts', artifacts)
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'acceptance_id': self.acceptance_id, 'readiness_id': self.readiness_id,
            'stability_id': self.stability_id, 'readiness_archive_sha256': self.readiness_archive_sha256,
            'target_version': self.target_version, 'requested_status': self.requested_status.value,
            'artifacts': [item.to_dict() for item in self.artifacts], 'policy': self.policy.to_dict(),
            'framework_version': self.framework_version, 'nicegui_required': self.nicegui_required,
            'observed_framework_version': self.observed_framework_version, 'observed_nicegui_version': self.observed_nicegui_version,
            'acceptance_authority': self.acceptance_authority, 'acceptance_reference': self.acceptance_reference,
            'metadata': dict(self.metadata), 'captured_at': self.captured_at,
            'monitoring_performed_by_framework': False, 'incident_response_performed_by_framework': False,
            'rollback_performed_by_framework': False, 'deployment_performed_by_framework': False,
            'publication_performed_by_framework': False, 'records_external_artifacts_only': True,
            'does_not_mutate_wave66_to_wave72_truth': True,
        }


def _acceptance_identity_payload(
    readiness: StableRollbackReadinessVerification, readiness_archive_sha256: str,
    requested_status: SustainedOperationsAcceptanceStatus, artifacts: Sequence[TargetEvidenceArtifact],
    policy: SustainedOperationsAcceptancePolicy, *, observed_framework_version: str | None,
    observed_nicegui_version: str | None, acceptance_authority: str | None,
    acceptance_reference: str | None, metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'readiness_id': readiness.readiness_id, 'stability_id': readiness.stability_evidence.stability_id,
        'readiness_archive_sha256': readiness_archive_sha256, 'target_version': readiness.policy.target_version,
        'requested_status': requested_status.value, 'artifacts': [item.to_dict() for item in artifacts],
        'policy': policy.to_dict(), 'framework_version': FRAMEWORK_VERSION, 'nicegui_required': NICEGUI_VERSION,
        'observed_framework_version': observed_framework_version, 'observed_nicegui_version': observed_nicegui_version,
        'acceptance_authority': acceptance_authority, 'acceptance_reference': acceptance_reference,
        'metadata': dict(metadata),
    }


def build_sustained_operations_evidence_acceptance(
    readiness: StableRollbackReadinessVerification, readiness_archive_path: str | Path, *,
    requested_status: SustainedOperationsAcceptanceStatus | str = SustainedOperationsAcceptanceStatus.PENDING,
    artifacts: Sequence[TargetEvidenceArtifact] = (), observed_framework_version: str | None = None,
    observed_nicegui_version: str | None = None, acceptance_authority: str | None = None,
    acceptance_reference: str | None = None, policy: SustainedOperationsAcceptancePolicy = SUSTAINED_OPERATIONS_ACCEPTANCE_POLICY,
    metadata: Mapping[str, Any] | None = None,
) -> SustainedOperationsEvidenceAcceptance:
    archive = Path(readiness_archive_path)
    if not archive.is_file():
        raise FileNotFoundError(archive)
    status = SustainedOperationsAcceptanceStatus(requested_status)
    values = dict(metadata or {})
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    payload = _acceptance_identity_payload(
        readiness, archive_sha, status, tuple(artifacts), policy,
        observed_framework_version=observed_framework_version, observed_nicegui_version=observed_nicegui_version,
        acceptance_authority=acceptance_authority, acceptance_reference=acceptance_reference, metadata=values,
    )
    return SustainedOperationsEvidenceAcceptance(
        _canonical_digest(payload), readiness.readiness_id, readiness.stability_evidence.stability_id,
        archive_sha, readiness.policy.target_version, status, tuple(artifacts), policy,
        FRAMEWORK_VERSION, NICEGUI_VERSION, observed_framework_version, observed_nicegui_version,
        acceptance_authority, acceptance_reference, values,
    )


def sustained_operations_evidence_acceptance_from_dict(payload: Mapping[str, Any]) -> SustainedOperationsEvidenceAcceptance:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported sustained-operations acceptance schema {payload.get("schema_version")!r}')
    policy_payload = payload.get('policy') or {}
    policy = SustainedOperationsAcceptancePolicy(
        str(policy_payload.get('key', 'stable')), str(policy_payload.get('target_version', '3.0.0')),
        tuple(str(item) for item in policy_payload.get('required_artifact_keys', ('sustained-operations-window', 'incident-audit-summary'))),
        bool(policy_payload.get('require_ready_rollback_readiness', True)),
    )
    obj = SustainedOperationsEvidenceAcceptance(
        str(payload['acceptance_id']), str(payload['readiness_id']), str(payload['stability_id']),
        str(payload['readiness_archive_sha256']), str(payload['target_version']),
        SustainedOperationsAcceptanceStatus(str(payload['requested_status'])),
        tuple(_target_artifact_from_dict(item) for item in payload.get('artifacts', ()) if isinstance(item, Mapping)),
        policy, str(payload.get('framework_version') or FRAMEWORK_VERSION), str(payload.get('nicegui_required') or NICEGUI_VERSION),
        None if payload.get('observed_framework_version') is None else str(payload.get('observed_framework_version')),
        None if payload.get('observed_nicegui_version') is None else str(payload.get('observed_nicegui_version')),
        None if payload.get('acceptance_authority') is None else str(payload.get('acceptance_authority')),
        None if payload.get('acceptance_reference') is None else str(payload.get('acceptance_reference')),
        dict(payload.get('metadata') or {}), str(payload.get('captured_at') or _utc_now()),
    )
    identity_payload = {
        'readiness_id': obj.readiness_id, 'stability_id': obj.stability_id,
        'readiness_archive_sha256': obj.readiness_archive_sha256, 'target_version': obj.target_version,
        'requested_status': obj.requested_status.value, 'artifacts': [item.to_dict() for item in obj.artifacts],
        'policy': obj.policy.to_dict(), 'framework_version': obj.framework_version, 'nicegui_required': obj.nicegui_required,
        'observed_framework_version': obj.observed_framework_version, 'observed_nicegui_version': obj.observed_nicegui_version,
        'acceptance_authority': obj.acceptance_authority, 'acceptance_reference': obj.acceptance_reference,
        'metadata': dict(obj.metadata),
    }
    if obj.acceptance_id != _canonical_digest(identity_payload):
        raise ValueError('sustained-operations acceptance id does not match persisted content')
    return obj


def write_sustained_operations_evidence_acceptance(path: str | Path, acceptance: SustainedOperationsEvidenceAcceptance) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(acceptance.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_sustained_operations_evidence_acceptance(path: str | Path) -> SustainedOperationsEvidenceAcceptance:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('sustained-operations acceptance JSON must contain an object')
    return sustained_operations_evidence_acceptance_from_dict(payload)


@dataclass(frozen=True, slots=True)
class SustainedOperationsAcceptanceVerification:
    acceptance_id: str
    status: SustainedOperationsAcceptanceStatus
    findings: tuple[SustainedOperationsAcceptanceFinding, ...] = ()

    def __post_init__(self) -> None:
        if len(self.acceptance_id) != 64:
            raise ValueError('sustained-operations acceptance verification requires sha256 id')
        object.__setattr__(self, 'status', SustainedOperationsAcceptanceStatus(self.status))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def accepted(self) -> bool:
        return self.status is SustainedOperationsAcceptanceStatus.ACCEPTED

    def to_dict(self) -> dict[str, Any]:
        return {'acceptance_id': self.acceptance_id, 'status': self.status.value, 'accepted': self.accepted, 'findings': [item.to_dict() for item in self.findings]}


def verify_sustained_operations_evidence_acceptance(
    acceptance: SustainedOperationsEvidenceAcceptance, readiness: StableRollbackReadinessVerification,
    readiness_archive_path: str | Path, *, base_dir: str | Path | None = None,
) -> SustainedOperationsAcceptanceVerification:
    findings: list[SustainedOperationsAcceptanceFinding] = []
    archive = verify_stable_rollback_readiness_archive(readiness_archive_path, expected_readiness=readiness)
    if not archive.verified:
        findings.append(SustainedOperationsAcceptanceFinding('readiness_archive_not_verified', SustainedOperationsAcceptanceStatus.BLOCKED, 'The immutable Wave 72 rollback-readiness package does not independently verify.', 'Restore the exact verified Wave 72 package.'))
    elif archive.sha256 != acceptance.readiness_archive_sha256:
        findings.append(SustainedOperationsAcceptanceFinding('readiness_archive_hash_mismatch', SustainedOperationsAcceptanceStatus.BLOCKED, 'The Wave 72 archive differs from the exact bytes bound to sustained-operations acceptance.', 'Use the exact archive reviewed by the external sustained-operations authority.'))
    if acceptance.readiness_id != readiness.readiness_id or acceptance.stability_id != readiness.stability_evidence.stability_id:
        findings.append(SustainedOperationsAcceptanceFinding('acceptance_subject_mismatch', SustainedOperationsAcceptanceStatus.BLOCKED, 'Sustained-operations acceptance is bound to a different Wave 72 readiness/stability identity.', 'Use acceptance created for this exact Wave 72 readiness chain.'))
    if acceptance.framework_version != FRAMEWORK_VERSION or acceptance.nicegui_required != NICEGUI_VERSION:
        findings.append(SustainedOperationsAcceptanceFinding('release_identity_mismatch', SustainedOperationsAcceptanceStatus.BLOCKED, 'Persisted acceptance release identity does not match the current NiceGUI Base authority.', 'Regenerate acceptance from the current framework and exact required NiceGUI runtime.'))
    if acceptance.policy.target_version != readiness.policy.target_version or acceptance.target_version != readiness.policy.target_version:
        findings.append(SustainedOperationsAcceptanceFinding('acceptance_target_version_mismatch', SustainedOperationsAcceptanceStatus.BLOCKED, 'Sustained-operations policy/record target does not match the Wave 72 release target.', 'Use the matching sustained-operations policy.'))
    if acceptance.policy.require_ready_rollback_readiness:
        if readiness.status is RollbackReadinessStatus.BLOCKED:
            findings.append(SustainedOperationsAcceptanceFinding('rollback_readiness_blocked', SustainedOperationsAcceptanceStatus.BLOCKED, 'Wave 72 rollback readiness is BLOCKED.', 'Resolve the canonical Wave 72 rollback-readiness blocker first.'))
        elif readiness.status is not RollbackReadinessStatus.READY:
            findings.append(SustainedOperationsAcceptanceFinding('rollback_readiness_not_ready', SustainedOperationsAcceptanceStatus.PENDING, 'Wave 72 rollback readiness is not READY.', 'Complete the canonical Wave 72 readiness evidence before sustained-operations acceptance.'))
    if readiness.stability_evidence.requested_status is PostReleaseStabilityStatus.BLOCKED:
        findings.append(SustainedOperationsAcceptanceFinding('stability_evidence_blocked', SustainedOperationsAcceptanceStatus.BLOCKED, 'Wave 72 stability evidence is explicitly BLOCKED.', 'Resolve the canonical post-release stability evidence first.'))
    findings.extend(_artifact_findings(
        acceptance.artifacts, base_dir=base_dir, required_keys=acceptance.policy.required_artifact_keys,
        finding_type=SustainedOperationsAcceptanceFinding, pending_status=SustainedOperationsAcceptanceStatus.PENDING,
        blocked_status=SustainedOperationsAcceptanceStatus.BLOCKED, subject='sustained operations acceptance', prefix='sustained_operations',
    ))
    if acceptance.requested_status is SustainedOperationsAcceptanceStatus.BLOCKED:
        findings.append(SustainedOperationsAcceptanceFinding('sustained_operations_explicitly_blocked', SustainedOperationsAcceptanceStatus.BLOCKED, 'External sustained-operations acceptance explicitly reports BLOCKED.', 'Resolve the external sustained-operations blocker and capture fresh evidence.'))
    elif acceptance.requested_status is SustainedOperationsAcceptanceStatus.PENDING:
        findings.append(SustainedOperationsAcceptanceFinding('sustained_operations_requested_pending', SustainedOperationsAcceptanceStatus.PENDING, 'Sustained-operations acceptance remains PENDING.', 'Complete the external sustained-operations evidence review and attach the resulting artifacts.'))
    else:
        if not acceptance.acceptance_authority or not acceptance.acceptance_reference:
            findings.append(SustainedOperationsAcceptanceFinding('sustained_operations_authority_reference_missing', SustainedOperationsAcceptanceStatus.PENDING, 'Requested ACCEPTED lacks a traceable external authority/reference.', 'Attach the external acceptance authority and immutable review reference.'))
        if acceptance.observed_framework_version is None or acceptance.observed_nicegui_version is None:
            findings.append(SustainedOperationsAcceptanceFinding('sustained_operations_execution_identity_missing', SustainedOperationsAcceptanceStatus.PENDING, 'Requested ACCEPTED lacks observed framework or exact NiceGUI identity.', f'Record framework {FRAMEWORK_VERSION} and exact nicegui=={NICEGUI_VERSION} reviewed by the authority.'))
        else:
            if acceptance.observed_framework_version != FRAMEWORK_VERSION:
                findings.append(SustainedOperationsAcceptanceFinding('framework_identity_mismatch', SustainedOperationsAcceptanceStatus.BLOCKED, f'Acceptance observed framework {acceptance.observed_framework_version!r}, expected {FRAMEWORK_VERSION!r}.', 'Repeat acceptance against the current framework release.'))
            if acceptance.observed_nicegui_version != NICEGUI_VERSION:
                findings.append(SustainedOperationsAcceptanceFinding('nicegui_identity_mismatch', SustainedOperationsAcceptanceStatus.BLOCKED, f'Acceptance observed NiceGUI {acceptance.observed_nicegui_version!r}, expected exact {NICEGUI_VERSION!r}.', f'Repeat acceptance against exact nicegui=={NICEGUI_VERSION}.'))
    mismatches = acceptance.metadata.get('manifest_artifact_sha256_mismatches')
    if isinstance(mismatches, Mapping) and mismatches:
        findings.append(SustainedOperationsAcceptanceFinding('manifest_artifact_hash_mismatch', SustainedOperationsAcceptanceStatus.BLOCKED, 'Acceptance manifest SHA-256 expectations do not match captured artifact bytes.', 'Resolve the external manifest/artifact mismatch.'))
    missing_paths = acceptance.metadata.get('missing_requested_artifact_paths')
    if isinstance(missing_paths, Sequence) and not isinstance(missing_paths, (str, bytes)) and missing_paths:
        findings.append(SustainedOperationsAcceptanceFinding('requested_acceptance_artifact_missing', SustainedOperationsAcceptanceStatus.PENDING, 'One or more requested sustained-operations artifact paths were unavailable at import time.', 'Provide the referenced external artifacts and rebuild acceptance.'))
    status = SustainedOperationsAcceptanceStatus.ACCEPTED
    if any(item.status is SustainedOperationsAcceptanceStatus.BLOCKED for item in findings):
        status = SustainedOperationsAcceptanceStatus.BLOCKED
    elif any(item.status is SustainedOperationsAcceptanceStatus.PENDING for item in findings):
        status = SustainedOperationsAcceptanceStatus.PENDING
    return SustainedOperationsAcceptanceVerification(acceptance.acceptance_id, status, tuple(findings))


def load_sustained_operations_evidence_acceptance_manifest(
    path: str | Path, readiness: StableRollbackReadinessVerification, readiness_archive_path: str | Path, *,
    artifact_base_dir: str | Path | None = None,
    policy: SustainedOperationsAcceptancePolicy = SUSTAINED_OPERATIONS_ACCEPTANCE_POLICY,
) -> SustainedOperationsEvidenceAcceptance:
    manifest = Path(path)
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('sustained-operations acceptance manifest must contain an object')
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported sustained-operations acceptance manifest schema {payload.get("schema_version")!r}')
    expected_values = {'readiness_id': readiness.readiness_id, 'stability_id': readiness.stability_evidence.stability_id, 'target_version': readiness.policy.target_version}
    for key, expected in expected_values.items():
        supplied = payload.get(key)
        if supplied is not None and str(supplied) != expected:
            raise ValueError(f'sustained-operations acceptance manifest {key} does not match supplied Wave 72 evidence')
    base = Path(artifact_base_dir) if artifact_base_dir is not None else manifest.parent
    artifacts: list[TargetEvidenceArtifact] = []
    mismatches: dict[str, dict[str, str]] = {}
    missing_paths: list[str] = []
    for item in payload.get('artifacts', ()):
        if not isinstance(item, Mapping) or not str(item.get('key', '')).strip() or not str(item.get('path', '')).strip():
            raise ValueError('sustained-operations acceptance artifacts require non-empty key/path')
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
    return build_sustained_operations_evidence_acceptance(
        readiness, readiness_archive_path,
        requested_status=str(payload.get('status') or payload.get('requested_status') or 'pending'), artifacts=tuple(artifacts),
        observed_framework_version=None if payload.get('framework_version') is None else str(payload.get('framework_version')),
        observed_nicegui_version=None if payload.get('nicegui_version') is None else str(payload.get('nicegui_version')),
        acceptance_authority=None if payload.get('acceptance_authority') is None else str(payload.get('acceptance_authority')),
        acceptance_reference=None if payload.get('acceptance_reference') is None else str(payload.get('acceptance_reference')),
        policy=policy, metadata=metadata,
    )


@runtime_checkable
class SustainedOperationsEvidenceAcceptanceAdapter(Protocol):
    key: str
    def load(self, path: str | Path, readiness: StableRollbackReadinessVerification, readiness_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> SustainedOperationsEvidenceAcceptance: ...


@dataclass(frozen=True, slots=True)
class JsonSustainedOperationsEvidenceAcceptanceAdapter:
    key: str = 'json-manifest'
    def load(self, path: str | Path, readiness: StableRollbackReadinessVerification, readiness_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> SustainedOperationsEvidenceAcceptance:
        return load_sustained_operations_evidence_acceptance_manifest(path, readiness, readiness_archive_path, artifact_base_dir=artifact_base_dir)


SUSTAINED_OPERATIONS_EVIDENCE_ACCEPTANCE_ADAPTERS: Mapping[str, SustainedOperationsEvidenceAcceptanceAdapter] = MappingProxyType({'json-manifest': JsonSustainedOperationsEvidenceAcceptanceAdapter()})


class IncidentRollbackAuditStatus(str, Enum):
    CLOSED = 'closed'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class IncidentRollbackAuditPolicy:
    key: str = 'stable'
    target_version: str = '3.0.0'
    required_artifact_keys: tuple[str, ...] = ('incident-audit-closure', 'rollback-audit-closure')
    require_accepted_sustained_operations: bool = True
    require_ready_rollback_readiness: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.target_version.strip() or not self.required_artifact_keys:
            raise ValueError('incident/rollback audit policy requires key, target version and artifact keys')
        values = tuple(dict.fromkeys(str(item).strip() for item in self.required_artifact_keys if str(item).strip()))
        if not values:
            raise ValueError('incident/rollback audit policy requires artifact keys')
        object.__setattr__(self, 'required_artifact_keys', values)

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key, 'target_version': self.target_version, 'required_artifact_keys': self.required_artifact_keys,
            'require_accepted_sustained_operations': self.require_accepted_sustained_operations,
            'require_ready_rollback_readiness': self.require_ready_rollback_readiness,
        }


INCIDENT_ROLLBACK_AUDIT_POLICY = IncidentRollbackAuditPolicy()
INCIDENT_ROLLBACK_AUDIT_POLICIES: Mapping[str, IncidentRollbackAuditPolicy] = MappingProxyType({'stable': INCIDENT_ROLLBACK_AUDIT_POLICY})


@dataclass(frozen=True, slots=True)
class IncidentRollbackAuditFinding:
    code: str
    status: IncidentRollbackAuditStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('incident/rollback audit finding code and message must not be empty')
        object.__setattr__(self, 'status', IncidentRollbackAuditStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class IncidentRollbackAuditClosure:
    audit_id: str
    readiness: StableRollbackReadinessVerification
    readiness_archive: TargetEvidenceArtifact
    sustained_operations_acceptance: SustainedOperationsEvidenceAcceptance
    audit_artifacts: tuple[TargetEvidenceArtifact, ...]
    policy: IncidentRollbackAuditPolicy = INCIDENT_ROLLBACK_AUDIT_POLICY
    requested_status: IncidentRollbackAuditStatus = IncidentRollbackAuditStatus.PENDING
    findings: tuple[IncidentRollbackAuditFinding, ...] = ()
    audit_authority: str | None = None
    audit_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.audit_id) != 64:
            raise ValueError('incident/rollback audit closure requires sha256 id')
        object.__setattr__(self, 'audit_artifacts', tuple(self.audit_artifacts))
        if len({item.key for item in self.audit_artifacts}) != len(self.audit_artifacts):
            raise ValueError('incident/rollback audit closure contains duplicate artifact keys')
        object.__setattr__(self, 'requested_status', IncidentRollbackAuditStatus(self.requested_status))
        object.__setattr__(self, 'findings', tuple(self.findings))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def status(self) -> IncidentRollbackAuditStatus:
        if any(item.status is IncidentRollbackAuditStatus.BLOCKED for item in self.findings):
            return IncidentRollbackAuditStatus.BLOCKED
        if any(item.status is IncidentRollbackAuditStatus.PENDING for item in self.findings):
            return IncidentRollbackAuditStatus.PENDING
        return IncidentRollbackAuditStatus.CLOSED

    @property
    def closed(self) -> bool:
        return self.status is IncidentRollbackAuditStatus.CLOSED

    @property
    def next_actions(self) -> tuple[str, ...]:
        actions = tuple(dict.fromkeys(item.remediation for item in self.findings if item.remediation.strip()))
        if actions:
            return actions
        return ('Retain the immutable Wave 73 audit package with the external operations record; no monitoring, incident response, rollback, deployment or publication is performed by NiceGUI Base.',)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'audit_id': self.audit_id, 'status': self.status.value, 'closed': self.closed,
            'readiness': self.readiness.to_dict(), 'readiness_archive': self.readiness_archive.to_dict(),
            'sustained_operations_acceptance': self.sustained_operations_acceptance.to_dict(),
            'audit_artifacts': [item.to_dict() for item in self.audit_artifacts], 'policy': self.policy.to_dict(),
            'requested_status': self.requested_status.value, 'findings': [item.to_dict() for item in self.findings],
            'audit_authority': self.audit_authority, 'audit_reference': self.audit_reference,
            'metadata': dict(self.metadata), 'generated_at': self.generated_at, 'next_actions': self.next_actions,
            'monitoring_performed_by_framework': False, 'incident_response_performed_by_framework': False,
            'rollback_performed_by_framework': False, 'deployment_performed_by_framework': False,
            'publication_performed_by_framework': False, 'audit_closure_is_not_operational_execution': True,
            'affects_wave66_to_wave72_truth': False,
        }


def _audit_identity_payload(
    readiness: StableRollbackReadinessVerification, readiness_archive: TargetEvidenceArtifact,
    acceptance: SustainedOperationsEvidenceAcceptance, audit_artifacts: Sequence[TargetEvidenceArtifact],
    policy: IncidentRollbackAuditPolicy, requested_status: IncidentRollbackAuditStatus,
    findings: Sequence[IncidentRollbackAuditFinding], *, audit_authority: str | None, audit_reference: str | None,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'readiness_id': readiness.readiness_id, 'readiness_archive': readiness_archive.to_dict(),
        'sustained_operations_acceptance_id': acceptance.acceptance_id,
        'audit_artifacts': [item.to_dict() for item in audit_artifacts], 'policy': policy.to_dict(),
        'requested_status': requested_status.value, 'findings': [item.to_dict() for item in findings],
        'audit_authority': audit_authority, 'audit_reference': audit_reference, 'metadata': dict(metadata),
    }


def _incident_rollback_audit_findings(
    readiness: StableRollbackReadinessVerification, readiness_archive_path: Path,
    acceptance: SustainedOperationsEvidenceAcceptance, audit_artifacts: Sequence[TargetEvidenceArtifact],
    policy: IncidentRollbackAuditPolicy, requested_status: IncidentRollbackAuditStatus, *,
    audit_authority: str | None, audit_reference: str | None, artifact_base_dir: str | Path | None, metadata: Mapping[str, Any],
) -> tuple[IncidentRollbackAuditFinding, ...]:
    findings: list[IncidentRollbackAuditFinding] = []
    archive = verify_stable_rollback_readiness_archive(readiness_archive_path, expected_readiness=readiness)
    if not archive.verified:
        findings.append(IncidentRollbackAuditFinding('audit_readiness_archive_not_verified', IncidentRollbackAuditStatus.BLOCKED, 'The immutable Wave 72 rollback-readiness package does not independently verify.', 'Restore the exact verified Wave 72 package.'))
    if policy.require_ready_rollback_readiness:
        if readiness.status is RollbackReadinessStatus.BLOCKED:
            findings.append(IncidentRollbackAuditFinding('audit_rollback_readiness_blocked', IncidentRollbackAuditStatus.BLOCKED, 'Wave 72 rollback readiness is BLOCKED.', 'Resolve the canonical Wave 72 readiness blocker first.'))
        elif readiness.status is not RollbackReadinessStatus.READY:
            findings.append(IncidentRollbackAuditFinding('audit_rollback_readiness_not_ready', IncidentRollbackAuditStatus.PENDING, 'Wave 72 rollback readiness is not READY.', 'Complete canonical Wave 72 rollback-readiness evidence first.'))
    acceptance_verification = verify_sustained_operations_evidence_acceptance(acceptance, readiness, readiness_archive_path, base_dir=artifact_base_dir)
    if policy.require_accepted_sustained_operations:
        if acceptance_verification.status is SustainedOperationsAcceptanceStatus.BLOCKED:
            findings.append(IncidentRollbackAuditFinding('sustained_operations_acceptance_blocked', IncidentRollbackAuditStatus.BLOCKED, 'Sustained-operations acceptance is BLOCKED.', 'Resolve the external sustained-operations evidence integrity/identity failure.'))
        elif acceptance_verification.status is not SustainedOperationsAcceptanceStatus.ACCEPTED:
            findings.append(IncidentRollbackAuditFinding('sustained_operations_not_accepted', IncidentRollbackAuditStatus.PENDING, 'Sustained-operations evidence is not yet ACCEPTED.', 'Complete the authoritative sustained-operations acceptance first.'))
    if policy.target_version != readiness.policy.target_version:
        findings.append(IncidentRollbackAuditFinding('audit_target_version_mismatch', IncidentRollbackAuditStatus.BLOCKED, 'Incident/rollback audit policy target does not match the Wave 72 release target.', 'Use the matching audit policy.'))
    findings.extend(_artifact_findings(
        audit_artifacts, base_dir=artifact_base_dir, required_keys=policy.required_artifact_keys,
        finding_type=IncidentRollbackAuditFinding, pending_status=IncidentRollbackAuditStatus.PENDING,
        blocked_status=IncidentRollbackAuditStatus.BLOCKED, subject='incident/rollback audit', prefix='incident_rollback_audit',
    ))
    if requested_status is IncidentRollbackAuditStatus.BLOCKED:
        findings.append(IncidentRollbackAuditFinding('incident_rollback_audit_explicitly_blocked', IncidentRollbackAuditStatus.BLOCKED, 'External incident/rollback audit explicitly reports BLOCKED.', 'Resolve the external audit blocker and capture fresh closure evidence.'))
    elif requested_status is IncidentRollbackAuditStatus.PENDING:
        findings.append(IncidentRollbackAuditFinding('incident_rollback_audit_requested_pending', IncidentRollbackAuditStatus.PENDING, 'Incident/rollback audit remains PENDING.', 'Complete the external audit and attach the resulting closure artifacts.'))
    elif not audit_authority or not audit_reference:
        findings.append(IncidentRollbackAuditFinding('incident_rollback_audit_authority_reference_missing', IncidentRollbackAuditStatus.PENDING, 'Requested CLOSED lacks a traceable external audit authority/reference.', 'Attach the external audit authority and immutable closure reference.'))
    mismatches = metadata.get('manifest_artifact_sha256_mismatches')
    if isinstance(mismatches, Mapping) and mismatches:
        findings.append(IncidentRollbackAuditFinding('audit_manifest_artifact_hash_mismatch', IncidentRollbackAuditStatus.BLOCKED, 'Audit manifest SHA-256 expectations do not match captured artifact bytes.', 'Resolve the external audit manifest/artifact mismatch.'))
    missing_paths = metadata.get('missing_requested_artifact_paths')
    if isinstance(missing_paths, Sequence) and not isinstance(missing_paths, (str, bytes)) and missing_paths:
        findings.append(IncidentRollbackAuditFinding('requested_audit_artifact_missing', IncidentRollbackAuditStatus.PENDING, 'One or more requested incident/rollback audit artifacts were unavailable at import time.', 'Provide the referenced external audit artifacts and rebuild closure.'))
    return tuple(findings)


def build_incident_rollback_audit_closure(
    readiness: StableRollbackReadinessVerification, readiness_archive_path: str | Path,
    sustained_operations_acceptance: SustainedOperationsEvidenceAcceptance, *,
    audit_artifacts: Sequence[TargetEvidenceArtifact] = (),
    requested_status: IncidentRollbackAuditStatus | str = IncidentRollbackAuditStatus.PENDING,
    audit_authority: str | None = None, audit_reference: str | None = None,
    policy: IncidentRollbackAuditPolicy = INCIDENT_ROLLBACK_AUDIT_POLICY,
    artifact_base_dir: str | Path | None = None, metadata: Mapping[str, Any] | None = None,
) -> IncidentRollbackAuditClosure:
    archive_path = Path(readiness_archive_path)
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    archive_artifact = capture_target_evidence_artifact(archive_path, key='rollback-readiness-package', description='immutable Wave 72 rollback-readiness package')
    status = IncidentRollbackAuditStatus(requested_status)
    values = dict(metadata or {})
    findings = _incident_rollback_audit_findings(
        readiness, archive_path, sustained_operations_acceptance, tuple(audit_artifacts), policy, status,
        audit_authority=audit_authority, audit_reference=audit_reference, artifact_base_dir=artifact_base_dir, metadata=values,
    )
    payload = _audit_identity_payload(
        readiness, archive_artifact, sustained_operations_acceptance, tuple(audit_artifacts), policy, status, findings,
        audit_authority=audit_authority, audit_reference=audit_reference, metadata=values,
    )
    return IncidentRollbackAuditClosure(
        _canonical_digest(payload), readiness, archive_artifact, sustained_operations_acceptance, tuple(audit_artifacts),
        policy, status, findings, audit_authority, audit_reference, values,
    )


def incident_rollback_audit_closure_from_dict(payload: Mapping[str, Any]) -> IncidentRollbackAuditClosure:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported incident/rollback audit closure schema {payload.get("schema_version")!r}')
    readiness_payload = payload.get('readiness'); archive_payload = payload.get('readiness_archive'); acceptance_payload = payload.get('sustained_operations_acceptance')
    if not isinstance(readiness_payload, Mapping) or not isinstance(archive_payload, Mapping) or not isinstance(acceptance_payload, Mapping):
        raise TypeError('incident/rollback audit closure requires readiness/archive/acceptance objects')
    readiness = stable_rollback_readiness_verification_from_dict(readiness_payload)
    archive_artifact = _target_artifact_from_dict(archive_payload)
    acceptance = sustained_operations_evidence_acceptance_from_dict(acceptance_payload)
    policy_payload = payload.get('policy') or {}
    policy = IncidentRollbackAuditPolicy(
        str(policy_payload.get('key', 'stable')), str(policy_payload.get('target_version', '3.0.0')),
        tuple(str(item) for item in policy_payload.get('required_artifact_keys', ('incident-audit-closure', 'rollback-audit-closure'))),
        bool(policy_payload.get('require_accepted_sustained_operations', True)), bool(policy_payload.get('require_ready_rollback_readiness', True)),
    )
    findings = tuple(
        IncidentRollbackAuditFinding(str(item['code']), IncidentRollbackAuditStatus(str(item['status'])), str(item['message']), str(item.get('remediation', '')))
        for item in payload.get('findings', ()) if isinstance(item, Mapping)
    )
    obj = IncidentRollbackAuditClosure(
        str(payload['audit_id']), readiness, archive_artifact, acceptance,
        tuple(_target_artifact_from_dict(item) for item in payload.get('audit_artifacts', ()) if isinstance(item, Mapping)),
        policy, IncidentRollbackAuditStatus(str(payload.get('requested_status', 'pending'))), findings,
        None if payload.get('audit_authority') is None else str(payload.get('audit_authority')),
        None if payload.get('audit_reference') is None else str(payload.get('audit_reference')),
        dict(payload.get('metadata') or {}), str(payload.get('generated_at') or _utc_now()),
    )
    expected = _canonical_digest(_audit_identity_payload(
        obj.readiness, obj.readiness_archive, obj.sustained_operations_acceptance, obj.audit_artifacts,
        obj.policy, obj.requested_status, obj.findings, audit_authority=obj.audit_authority,
        audit_reference=obj.audit_reference, metadata=obj.metadata,
    ))
    if obj.audit_id != expected:
        raise ValueError('incident/rollback audit id does not match persisted content')
    if payload.get('status') is not None and str(payload['status']) != obj.status.value:
        raise ValueError('incident/rollback audit status does not match persisted content')
    return obj


def write_incident_rollback_audit_closure(path: str | Path, closure: IncidentRollbackAuditClosure) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(closure.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_incident_rollback_audit_closure(path: str | Path) -> IncidentRollbackAuditClosure:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('incident/rollback audit closure JSON must contain an object')
    return incident_rollback_audit_closure_from_dict(payload)


def load_incident_rollback_audit_manifest(
    path: str | Path, readiness: StableRollbackReadinessVerification, readiness_archive_path: str | Path,
    sustained_operations_acceptance: SustainedOperationsEvidenceAcceptance, *, artifact_base_dir: str | Path | None = None,
    policy: IncidentRollbackAuditPolicy = INCIDENT_ROLLBACK_AUDIT_POLICY,
) -> IncidentRollbackAuditClosure:
    manifest = Path(path)
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('incident/rollback audit manifest must contain an object')
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported incident/rollback audit manifest schema {payload.get("schema_version")!r}')
    expected_values = {
        'readiness_id': readiness.readiness_id, 'stability_id': readiness.stability_evidence.stability_id,
        'sustained_operations_acceptance_id': sustained_operations_acceptance.acceptance_id,
        'target_version': readiness.policy.target_version,
    }
    for key, expected in expected_values.items():
        supplied = payload.get(key)
        if supplied is not None and str(supplied) != expected:
            raise ValueError(f'incident/rollback audit manifest {key} does not match supplied Wave 72/73 evidence')
    base = Path(artifact_base_dir) if artifact_base_dir is not None else manifest.parent
    artifacts: list[TargetEvidenceArtifact] = []
    mismatches: dict[str, dict[str, str]] = {}
    missing_paths: list[str] = []
    for item in payload.get('artifacts', ()):
        if not isinstance(item, Mapping) or not str(item.get('key', '')).strip() or not str(item.get('path', '')).strip():
            raise ValueError('incident/rollback audit artifacts require non-empty key/path')
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
    closure = build_incident_rollback_audit_closure(
        readiness, readiness_archive_path, sustained_operations_acceptance, audit_artifacts=tuple(artifacts),
        requested_status=str(payload.get('status') or payload.get('requested_status') or 'pending'),
        audit_authority=None if payload.get('audit_authority') is None else str(payload.get('audit_authority')),
        audit_reference=None if payload.get('audit_reference') is None else str(payload.get('audit_reference')),
        policy=policy, artifact_base_dir=artifact_base_dir, metadata=metadata,
    )
    return closure


@dataclass(frozen=True, slots=True)
class IncidentRollbackAuditPackage:
    path: str
    sha256: str
    audit_id: str
    status: IncidentRollbackAuditStatus
    entries: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or len(self.audit_id) != 64:
            raise ValueError('incident/rollback audit package requires sha256 package/audit identifiers')
        object.__setattr__(self, 'status', IncidentRollbackAuditStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))

    def to_dict(self) -> dict[str, Any]:
        return {'path': self.path, 'sha256': self.sha256, 'audit_id': self.audit_id, 'status': self.status.value, 'entries': self.entries}


def package_incident_rollback_audit_closure(
    path: str | Path, closure: IncidentRollbackAuditClosure, *, artifact_base_dir: str | Path | None = None,
) -> IncidentRollbackAuditPackage:
    archive_path = _resolve_artifact_path(closure.readiness_archive, artifact_base_dir)
    refreshed = build_incident_rollback_audit_closure(
        closure.readiness, archive_path, closure.sustained_operations_acceptance,
        audit_artifacts=closure.audit_artifacts, requested_status=closure.requested_status,
        audit_authority=closure.audit_authority, audit_reference=closure.audit_reference,
        policy=closure.policy, artifact_base_dir=artifact_base_dir, metadata=closure.metadata,
    )
    if refreshed.status is IncidentRollbackAuditStatus.BLOCKED:
        raise ValueError('incident/rollback audit package cannot be created from BLOCKED or changed evidence')
    if refreshed.audit_id != closure.audit_id:
        raise ValueError('incident/rollback audit identity changed during package verification')
    entries: dict[str, bytes] = {
        'incident-rollback-audit-closure.json': _json_bytes(refreshed.to_dict()),
        'sustained-operations-acceptance.json': _json_bytes(refreshed.sustained_operations_acceptance.to_dict()),
        'wave72/rollback-readiness.zip': archive_path.read_bytes(),
    }
    groups = (
        ('sustained-operations-evidence', refreshed.sustained_operations_acceptance.artifacts),
        ('incident-rollback-audit-evidence', refreshed.audit_artifacts),
    )
    for prefix, artifacts in groups:
        for artifact in artifacts:
            source = _resolve_artifact_path(artifact, artifact_base_dir)
            if not source.is_file():
                continue
            blob = source.read_bytes()
            if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
                raise ValueError(f'{prefix} artifact changed: {artifact.key}')
            entries[f'{prefix}/{_safe_entry_component(artifact.key)}/{_safe_entry_component(source.name)}'] = blob
    manifest = ''.join(f'{hashlib.sha256(entries[name]).hexdigest()}  {name}\n' for name in sorted(entries))
    entries['MANIFEST.sha256'] = manifest.encode('utf-8')
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w') as archive:
        for name in sorted(entries):
            pure = PurePosixPath(name)
            if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                raise ValueError(f'unsafe incident/rollback audit archive entry {name!r}')
            archive.writestr(_zip_info(name), entries[name])
    return IncidentRollbackAuditPackage(str(target), hashlib.sha256(target.read_bytes()).hexdigest(), closure.audit_id, closure.status, tuple(sorted(entries)))


__all__ = [
    'INCIDENT_ROLLBACK_AUDIT_POLICIES','INCIDENT_ROLLBACK_AUDIT_POLICY','IncidentRollbackAuditClosure','IncidentRollbackAuditFinding',
    'IncidentRollbackAuditPackage','IncidentRollbackAuditPolicy','IncidentRollbackAuditStatus','JsonSustainedOperationsEvidenceAcceptanceAdapter',
    'SUSTAINED_OPERATIONS_ACCEPTANCE_POLICIES','SUSTAINED_OPERATIONS_ACCEPTANCE_POLICY','SUSTAINED_OPERATIONS_EVIDENCE_ACCEPTANCE_ADAPTERS',
    'StableRollbackReadinessArchiveFinding','StableRollbackReadinessArchiveStatus','StableRollbackReadinessArchiveVerification',
    'SustainedOperationsAcceptanceFinding','SustainedOperationsAcceptancePolicy','SustainedOperationsAcceptanceStatus',
    'SustainedOperationsAcceptanceVerification','SustainedOperationsEvidenceAcceptance','SustainedOperationsEvidenceAcceptanceAdapter',
    'build_incident_rollback_audit_closure','build_sustained_operations_evidence_acceptance','incident_rollback_audit_closure_from_dict',
    'load_incident_rollback_audit_manifest','load_sustained_operations_evidence_acceptance_manifest','package_incident_rollback_audit_closure',
    'read_incident_rollback_audit_closure','read_sustained_operations_evidence_acceptance','sustained_operations_evidence_acceptance_from_dict',
    'verify_stable_rollback_readiness_archive','verify_sustained_operations_evidence_acceptance','write_incident_rollback_audit_closure',
    'write_sustained_operations_evidence_acceptance',
]
