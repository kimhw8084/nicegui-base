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
from .semiconductor_release_acceptance import (
    StablePromotionClosureStatus,
    StableReleasePromotionClosure,
    stable_release_evidence_acceptance_from_dict,
    stable_release_promotion_closure_from_dict,
    verify_release_audit_archive,
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
        raise ValueError(f'release publication artifact path escapes manifest base directory: {value!r}') from exc
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


class StablePromotionClosureArchiveStatus(str, Enum):
    VERIFIED = 'verified'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class StablePromotionClosureArchiveFinding:
    code: str
    status: StablePromotionClosureArchiveStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('stable promotion closure archive finding code and message must not be empty')
        object.__setattr__(self, 'status', StablePromotionClosureArchiveStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class StablePromotionClosureArchiveVerification:
    path: str
    sha256: str | None
    status: StablePromotionClosureArchiveStatus
    closure_id: str | None = None
    candidate_id: str | None = None
    entries: tuple[str, ...] = ()
    findings: tuple[StablePromotionClosureArchiveFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.sha256 is not None and len(self.sha256) != 64:
            raise ValueError('stable promotion closure archive sha256 must be 64 hex characters when present')
        object.__setattr__(self, 'status', StablePromotionClosureArchiveStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def verified(self) -> bool:
        return self.status is StablePromotionClosureArchiveStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': self.path, 'sha256': self.sha256, 'status': self.status.value, 'verified': self.verified,
            'closure_id': self.closure_id, 'candidate_id': self.candidate_id, 'entries': self.entries,
            'findings': [item.to_dict() for item in self.findings],
        }


def _blocked_closure_archive(path: str | Path, code: str, message: str, remediation: str, *, sha256: str | None = None, entries: Sequence[str] = ()) -> StablePromotionClosureArchiveVerification:
    return StablePromotionClosureArchiveVerification(
        str(path), sha256, StablePromotionClosureArchiveStatus.BLOCKED, entries=tuple(entries),
        findings=(StablePromotionClosureArchiveFinding(code, StablePromotionClosureArchiveStatus.BLOCKED, message, remediation),),
    )


def verify_stable_promotion_closure_archive(
    path: str | Path,
    *,
    expected_closure: StableReleasePromotionClosure | None = None,
) -> StablePromotionClosureArchiveVerification:
    target = Path(path)
    if not target.is_file():
        return _blocked_closure_archive(target, 'closure_archive_missing', 'The Wave 70 stable-promotion closure archive is unavailable.', 'Restore the exact immutable Wave 70 closure ZIP before publication evidence intake.')
    data = target.read_bytes()
    archive_sha = hashlib.sha256(data).hexdigest()
    try:
        with zipfile.ZipFile(target) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if len(names) != len(set(names)):
                return _blocked_closure_archive(target, 'closure_archive_duplicate_entry', 'The stable-promotion closure ZIP contains duplicate entries.', 'Recreate the closure package with the canonical Wave 70 packager.', sha256=archive_sha, entries=names)
            for name in names:
                pure = PurePosixPath(name)
                if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                    return _blocked_closure_archive(target, 'closure_archive_unsafe_entry', f'The closure ZIP contains unsafe entry {name!r}.', 'Reject the archive and recreate it with the canonical Wave 70 packager.', sha256=archive_sha, entries=names)
            required = {'promotion-closure.json', 'release-evidence-acceptance.json', 'release-audit/release-audit.zip', 'MANIFEST.sha256'}
            missing = sorted(required - set(names))
            if missing:
                return _blocked_closure_archive(target, 'closure_archive_required_entry_missing', f'The closure ZIP is missing required entries: {missing}.', 'Recreate the complete self-contained Wave 70 closure package.', sha256=archive_sha, entries=names)
            try:
                expected_hashes = _parse_manifest(archive.read('MANIFEST.sha256'))
            except (UnicodeDecodeError, ValueError) as exc:
                return _blocked_closure_archive(target, 'closure_archive_manifest_invalid', f'The closure manifest is invalid: {exc}', 'Recreate the closure package; do not repair manifest bytes manually.', sha256=archive_sha, entries=names)
            payload_names = set(names) - {'MANIFEST.sha256'}
            if set(expected_hashes) != payload_names:
                return _blocked_closure_archive(target, 'closure_archive_manifest_incomplete', 'MANIFEST.sha256 does not cover exactly every non-manifest archive entry.', 'Recreate the closure package with complete deterministic hashing.', sha256=archive_sha, entries=names)
            for name, expected_sha in expected_hashes.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected_sha:
                    return _blocked_closure_archive(target, 'closure_archive_hash_mismatch', f'Archive entry {name!r} does not match MANIFEST.sha256.', 'Reject changed closure bytes and restore/recreate the immutable package.', sha256=archive_sha, entries=names)
            try:
                payload = json.loads(archive.read('promotion-closure.json').decode('utf-8'))
                if not isinstance(payload, Mapping):
                    raise TypeError('promotion-closure.json must contain an object')
                closure = stable_release_promotion_closure_from_dict(payload)
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                return _blocked_closure_archive(target, 'closure_archive_payload_invalid', f'promotion-closure.json cannot be verified: {exc}', 'Recreate the closure package from a canonical Wave 70 closure.', sha256=archive_sha, entries=names)
            if expected_closure is not None and closure.closure_id != expected_closure.closure_id:
                return _blocked_closure_archive(target, 'closure_archive_identity_mismatch', 'The closure archive contains a different closure identity than supplied.', 'Use the exact archive created for this Wave 70 closure.', sha256=archive_sha, entries=names)
            try:
                embedded_acceptance_payload = json.loads(archive.read('release-evidence-acceptance.json').decode('utf-8'))
                if not isinstance(embedded_acceptance_payload, Mapping):
                    raise TypeError('release-evidence-acceptance.json must contain an object')
                embedded_acceptance = stable_release_evidence_acceptance_from_dict(embedded_acceptance_payload)
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                return _blocked_closure_archive(target, 'closure_archive_acceptance_invalid', f'Embedded release evidence acceptance cannot be identity-verified: {exc}', 'Recreate the closure package from the canonical Wave 70 acceptance record.', sha256=archive_sha, entries=names)
            if embedded_acceptance.acceptance_id != closure.evidence_acceptance.acceptance_id:
                return _blocked_closure_archive(target, 'closure_archive_acceptance_identity_mismatch', 'Embedded acceptance does not match the closure acceptance identity.', 'Recreate the closure package from the canonical acceptance and closure.', sha256=archive_sha, entries=names)
            audit_bytes = archive.read('release-audit/release-audit.zip')
            if hashlib.sha256(audit_bytes).hexdigest() != closure.audit_archive.sha256:
                return _blocked_closure_archive(target, 'closure_archive_audit_hash_mismatch', 'Embedded release-audit ZIP no longer matches the closure-bound audit SHA-256.', 'Restore the exact audit archive and recreate the Wave 70 closure package.', sha256=archive_sha, entries=names)
            with tempfile.TemporaryDirectory(prefix='nicegui-base-wave71-closure-') as temp:
                audit_path = Path(temp) / 'release-audit.zip'
                audit_path.write_bytes(audit_bytes)
                audit_verification = verify_release_audit_archive(audit_path, expected_audit=closure.release_audit)
                if not audit_verification.verified:
                    return _blocked_closure_archive(target, 'closure_archive_audit_reverification_failed', 'Embedded release-audit archive failed independent Wave 70 reverification.', 'Recreate the closure package from an independently verified Wave 69 audit archive.', sha256=archive_sha, entries=names)
            return StablePromotionClosureArchiveVerification(
                str(target), archive_sha, StablePromotionClosureArchiveStatus.VERIFIED,
                closure.closure_id, closure.release_audit.handoff.candidate.candidate_id, tuple(sorted(names)), (),
            )
    except (OSError, zipfile.BadZipFile, RuntimeError, KeyError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return _blocked_closure_archive(target, 'closure_archive_invalid', f'The closure ZIP cannot be read safely: {exc}', 'Restore or recreate the canonical Wave 70 closure package.', sha256=archive_sha)


class StableReleasePublicationStatus(str, Enum):
    PUBLISHED = 'published'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class StableReleasePublicationFinding:
    code: str
    status: StableReleasePublicationStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('stable release publication finding code and message must not be empty')
        object.__setattr__(self, 'status', StableReleasePublicationStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class StableReleasePublicationEvidence:
    publication_id: str
    closure_id: str
    candidate_id: str
    closure_archive_sha256: str
    target_version: str
    requested_status: StableReleasePublicationStatus
    artifacts: tuple[TargetEvidenceArtifact, ...]
    framework_version: str = FRAMEWORK_VERSION
    nicegui_required: str = NICEGUI_VERSION
    observed_framework_version: str | None = None
    observed_nicegui_version: str | None = None
    publication_authority: str | None = None
    publication_reference: str | None = None
    deployment_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    captured_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if any(len(value) != 64 for value in (self.publication_id, self.closure_id, self.candidate_id, self.closure_archive_sha256)):
            raise ValueError('stable release publication requires sha256 publication/closure/candidate/archive identifiers')
        if not self.target_version.strip():
            raise ValueError('stable release publication target_version must not be empty')
        object.__setattr__(self, 'requested_status', StableReleasePublicationStatus(self.requested_status))
        artifacts = tuple(self.artifacts)
        if len({item.key for item in artifacts}) != len(artifacts):
            raise ValueError('stable release publication contains duplicate artifact keys')
        object.__setattr__(self, 'artifacts', artifacts)
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'publication_id': self.publication_id, 'closure_id': self.closure_id,
            'candidate_id': self.candidate_id, 'closure_archive_sha256': self.closure_archive_sha256,
            'target_version': self.target_version, 'requested_status': self.requested_status.value,
            'artifacts': [item.to_dict() for item in self.artifacts], 'framework_version': self.framework_version,
            'nicegui_required': self.nicegui_required, 'observed_framework_version': self.observed_framework_version,
            'observed_nicegui_version': self.observed_nicegui_version, 'publication_authority': self.publication_authority,
            'publication_reference': self.publication_reference, 'deployment_reference': self.deployment_reference,
            'metadata': dict(self.metadata), 'captured_at': self.captured_at,
            'publication_performed_by_framework': False, 'deployment_performed_by_framework': False,
            'external_authority_is_metadata_only': True, 'publication_does_not_mutate_canonical_promotion_truth': True,
        }


def _publication_identity_payload(
    closure_id: str, candidate_id: str, closure_archive_sha256: str, target_version: str,
    requested_status: StableReleasePublicationStatus, artifacts: Sequence[TargetEvidenceArtifact], *,
    framework_version: str, nicegui_required: str, observed_framework_version: str | None,
    observed_nicegui_version: str | None, publication_authority: str | None, publication_reference: str | None,
    deployment_reference: str | None, metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'closure_id': closure_id, 'candidate_id': candidate_id, 'closure_archive_sha256': closure_archive_sha256,
        'target_version': target_version, 'requested_status': requested_status.value,
        'artifacts': [item.to_dict() for item in artifacts], 'framework_version': framework_version,
        'nicegui_required': nicegui_required, 'observed_framework_version': observed_framework_version,
        'observed_nicegui_version': observed_nicegui_version, 'publication_authority': publication_authority,
        'publication_reference': publication_reference, 'deployment_reference': deployment_reference, 'metadata': dict(metadata),
    }


def build_stable_release_publication_evidence(
    closure: StableReleasePromotionClosure,
    closure_archive_path: str | Path,
    *,
    requested_status: StableReleasePublicationStatus | str = StableReleasePublicationStatus.PENDING,
    artifacts: Sequence[TargetEvidenceArtifact] = (),
    observed_framework_version: str | None = None,
    observed_nicegui_version: str | None = None,
    publication_authority: str | None = None,
    publication_reference: str | None = None,
    deployment_reference: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> StableReleasePublicationEvidence:
    archive = Path(closure_archive_path)
    if not archive.is_file():
        raise FileNotFoundError(archive)
    status = StableReleasePublicationStatus(requested_status)
    values = dict(metadata or {})
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    candidate = closure.release_audit.handoff.candidate
    payload = _publication_identity_payload(
        closure.closure_id, candidate.candidate_id, archive_sha, closure.policy.target_version, status, tuple(artifacts),
        framework_version=FRAMEWORK_VERSION, nicegui_required=NICEGUI_VERSION,
        observed_framework_version=observed_framework_version, observed_nicegui_version=observed_nicegui_version,
        publication_authority=publication_authority, publication_reference=publication_reference,
        deployment_reference=deployment_reference, metadata=values,
    )
    return StableReleasePublicationEvidence(
        _canonical_digest(payload), closure.closure_id, candidate.candidate_id, archive_sha, closure.policy.target_version,
        status, tuple(artifacts), FRAMEWORK_VERSION, NICEGUI_VERSION, observed_framework_version, observed_nicegui_version,
        publication_authority, publication_reference, deployment_reference, values,
    )


def stable_release_publication_evidence_from_dict(payload: Mapping[str, Any]) -> StableReleasePublicationEvidence:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported stable release publication evidence schema {payload.get("schema_version")!r}')
    evidence = StableReleasePublicationEvidence(
        str(payload['publication_id']), str(payload['closure_id']), str(payload['candidate_id']), str(payload['closure_archive_sha256']),
        str(payload['target_version']), StableReleasePublicationStatus(str(payload['requested_status'])),
        tuple(_target_artifact_from_dict(item) for item in payload.get('artifacts', ()) if isinstance(item, Mapping)),
        str(payload.get('framework_version') or FRAMEWORK_VERSION), str(payload.get('nicegui_required') or NICEGUI_VERSION),
        None if payload.get('observed_framework_version') is None else str(payload.get('observed_framework_version')),
        None if payload.get('observed_nicegui_version') is None else str(payload.get('observed_nicegui_version')),
        None if payload.get('publication_authority') is None else str(payload.get('publication_authority')),
        None if payload.get('publication_reference') is None else str(payload.get('publication_reference')),
        None if payload.get('deployment_reference') is None else str(payload.get('deployment_reference')),
        dict(payload.get('metadata') or {}), str(payload.get('captured_at') or _utc_now()),
    )
    expected = _canonical_digest(_publication_identity_payload(
        evidence.closure_id, evidence.candidate_id, evidence.closure_archive_sha256, evidence.target_version,
        evidence.requested_status, evidence.artifacts, framework_version=evidence.framework_version,
        nicegui_required=evidence.nicegui_required, observed_framework_version=evidence.observed_framework_version,
        observed_nicegui_version=evidence.observed_nicegui_version, publication_authority=evidence.publication_authority,
        publication_reference=evidence.publication_reference, deployment_reference=evidence.deployment_reference, metadata=evidence.metadata,
    ))
    if evidence.publication_id != expected:
        raise ValueError('stable release publication id does not match persisted content')
    return evidence


def write_stable_release_publication_evidence(path: str | Path, evidence: StableReleasePublicationEvidence) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_stable_release_publication_evidence(path: str | Path) -> StableReleasePublicationEvidence:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('stable release publication evidence JSON must contain an object')
    return stable_release_publication_evidence_from_dict(payload)


def load_stable_release_publication_evidence_manifest(
    path: str | Path,
    closure: StableReleasePromotionClosure,
    closure_archive_path: str | Path,
    *, artifact_base_dir: str | Path | None = None,
) -> StableReleasePublicationEvidence:
    manifest = Path(path)
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('stable release publication manifest must contain an object')
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported stable release publication manifest schema {payload.get("schema_version")!r}')
    archive = Path(closure_archive_path)
    if not archive.is_file():
        raise FileNotFoundError(archive)
    candidate = closure.release_audit.handoff.candidate
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    expected_values = {
        'closure_id': closure.closure_id, 'candidate_id': candidate.candidate_id,
        'closure_archive_sha256': archive_sha, 'target_version': closure.policy.target_version,
    }
    for key, expected in expected_values.items():
        supplied = payload.get(key)
        if supplied is not None and str(supplied) != expected:
            raise ValueError(f'stable release publication manifest {key} does not match supplied closure/archive')
    base = Path(artifact_base_dir) if artifact_base_dir is not None else manifest.parent
    artifacts: list[TargetEvidenceArtifact] = []
    for item in payload.get('artifacts', ()):
        if not isinstance(item, Mapping) or not str(item.get('key', '')).strip() or not str(item.get('path', '')).strip():
            raise ValueError('publication manifest artifacts require non-empty key/path')
        source = _safe_manifest_artifact_path(base, str(item['path']))
        if not source.is_file():
            raise FileNotFoundError(source)
        artifacts.append(capture_target_evidence_artifact(source, key=str(item['key']), description=str(item.get('description', ''))))
    return build_stable_release_publication_evidence(
        closure, archive, requested_status=str(payload.get('status', 'pending')), artifacts=tuple(artifacts),
        observed_framework_version=None if payload.get('framework_version') is None else str(payload.get('framework_version')),
        observed_nicegui_version=None if payload.get('nicegui_version') is None else str(payload.get('nicegui_version')),
        publication_authority=None if payload.get('publication_authority') is None else str(payload.get('publication_authority')),
        publication_reference=None if payload.get('publication_reference') is None else str(payload.get('publication_reference')),
        deployment_reference=None if payload.get('deployment_reference') is None else str(payload.get('deployment_reference')),
        metadata=dict(payload.get('metadata') or {}),
    )


@dataclass(frozen=True, slots=True)
class StableReleasePublicationVerification:
    publication_id: str
    status: StableReleasePublicationStatus
    findings: tuple[StableReleasePublicationFinding, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'status', StableReleasePublicationStatus(self.status))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def published(self) -> bool:
        return self.status is StableReleasePublicationStatus.PUBLISHED

    @property
    def blocked(self) -> bool:
        return self.status is StableReleasePublicationStatus.BLOCKED

    def to_dict(self) -> dict[str, Any]:
        return {'publication_id': self.publication_id, 'status': self.status.value, 'published': self.published, 'blocked': self.blocked, 'findings': [item.to_dict() for item in self.findings]}


def verify_stable_release_publication_evidence(
    evidence: StableReleasePublicationEvidence,
    *, closure: StableReleasePromotionClosure,
    closure_archive_path: str | Path,
    base_dir: str | Path | None = None,
) -> StableReleasePublicationVerification:
    findings: list[StableReleasePublicationFinding] = []
    candidate = closure.release_audit.handoff.candidate
    if evidence.closure_id != closure.closure_id or evidence.candidate_id != candidate.candidate_id or evidence.target_version != closure.policy.target_version:
        findings.append(StableReleasePublicationFinding('publication_subject_mismatch', StableReleasePublicationStatus.BLOCKED, 'Publication evidence is bound to a different closure, candidate or target version.', 'Import publication evidence for this exact Wave 70 closure identity.'))
    archive_path = Path(closure_archive_path)
    if not archive_path.is_file():
        findings.append(StableReleasePublicationFinding('closure_archive_unavailable', StableReleasePublicationStatus.BLOCKED, 'The closure archive bound to publication evidence is unavailable.', 'Restore the exact Wave 70 closure archive.'))
    else:
        archive_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        if archive_sha != evidence.closure_archive_sha256:
            findings.append(StableReleasePublicationFinding('closure_archive_hash_mismatch', StableReleasePublicationStatus.BLOCKED, 'The Wave 70 closure ZIP differs from the archive bound to publication evidence.', 'Use the exact immutable closure archive reviewed for publication.'))
        archive_verification = verify_stable_promotion_closure_archive(archive_path, expected_closure=closure)
        if not archive_verification.verified:
            findings.append(StableReleasePublicationFinding('closure_archive_not_verified', StableReleasePublicationStatus.BLOCKED, 'The Wave 70 closure archive failed independent verification.', 'Restore/recreate the verified closure package before accepting publication evidence.'))
    if closure.status is StablePromotionClosureStatus.BLOCKED:
        findings.append(StableReleasePublicationFinding('canonical_closure_blocked', StableReleasePublicationStatus.BLOCKED, 'The canonical Wave 70 documentary closure is BLOCKED.', 'Resolve canonical closure blockers before stable publication evidence can verify.'))
    elif closure.status is not StablePromotionClosureStatus.CLOSED:
        findings.append(StableReleasePublicationFinding('canonical_closure_not_closed', StableReleasePublicationStatus.PENDING, 'The canonical Wave 70 documentary closure is not CLOSED.', 'Complete the canonical evidence chain before stable publication evidence can verify.'))
    if evidence.framework_version != FRAMEWORK_VERSION or evidence.nicegui_required != NICEGUI_VERSION:
        findings.append(StableReleasePublicationFinding('publication_contract_identity_mismatch', StableReleasePublicationStatus.BLOCKED, 'Publication evidence was constructed for a different framework or required NiceGUI contract.', 'Regenerate publication evidence against the current framework and exact NiceGUI requirement.'))
    if evidence.observed_framework_version is not None and evidence.observed_framework_version != FRAMEWORK_VERSION:
        findings.append(StableReleasePublicationFinding('publication_framework_mismatch', StableReleasePublicationStatus.BLOCKED, 'Observed publication framework version does not match current NiceGUI Base.', 'Publish/verify the exact framework build bound to the closure.'))
    if evidence.observed_nicegui_version is not None and evidence.observed_nicegui_version != NICEGUI_VERSION:
        findings.append(StableReleasePublicationFinding('publication_nicegui_mismatch', StableReleasePublicationStatus.BLOCKED, 'Observed publication NiceGUI version does not match the exact required version.', f'Capture evidence from NiceGUI {NICEGUI_VERSION}.'))
    for artifact in evidence.artifacts:
        source = _resolve_artifact_path(artifact, base_dir)
        if not source.is_file():
            findings.append(StableReleasePublicationFinding('publication_artifact_missing', StableReleasePublicationStatus.BLOCKED, f'Publication artifact {artifact.key!r} is unavailable.', 'Restore the exact immutable publication artifact bytes.'))
            continue
        blob = source.read_bytes()
        if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
            findings.append(StableReleasePublicationFinding('publication_artifact_hash_mismatch', StableReleasePublicationStatus.BLOCKED, f'Publication artifact {artifact.key!r} changed after capture.', 'Reject changed bytes and recapture authoritative publication evidence.'))
    if evidence.requested_status is StableReleasePublicationStatus.BLOCKED:
        findings.append(StableReleasePublicationFinding('publication_explicitly_blocked', StableReleasePublicationStatus.BLOCKED, 'External publication evidence explicitly reports BLOCKED.', 'Resolve the external publication failure and capture a new evidence record.'))
    elif evidence.requested_status is StableReleasePublicationStatus.PENDING:
        findings.append(StableReleasePublicationFinding('publication_requested_pending', StableReleasePublicationStatus.PENDING, 'External stable publication remains PENDING.', 'Attach authoritative publication evidence after the external release process completes.'))
    else:
        if evidence.observed_framework_version is None or evidence.observed_nicegui_version is None:
            findings.append(StableReleasePublicationFinding('publication_identity_missing', StableReleasePublicationStatus.PENDING, 'Requested PUBLISHED lacks complete observed framework/NiceGUI identity.', 'Capture both observed framework and exact NiceGUI versions from the published target.'))
        if not evidence.publication_authority or not evidence.publication_reference:
            findings.append(StableReleasePublicationFinding('publication_authority_reference_missing', StableReleasePublicationStatus.PENDING, 'Requested PUBLISHED lacks traceable authority/reference metadata.', 'Attach the authoritative external publication authority and immutable reference.'))
        if not evidence.artifacts:
            findings.append(StableReleasePublicationFinding('publication_artifacts_missing', StableReleasePublicationStatus.PENDING, 'Requested PUBLISHED has no traceable publication artifact bytes.', 'Attach immutable publication/deployment evidence artifacts.'))
    status = StableReleasePublicationStatus.PUBLISHED
    if any(item.status is StableReleasePublicationStatus.BLOCKED for item in findings):
        status = StableReleasePublicationStatus.BLOCKED
    elif any(item.status is StableReleasePublicationStatus.PENDING for item in findings):
        status = StableReleasePublicationStatus.PENDING
    return StableReleasePublicationVerification(evidence.publication_id, status, tuple(findings))


@runtime_checkable
class StableReleasePublicationEvidenceAdapter(Protocol):
    def load(self, path: str | Path, closure: StableReleasePromotionClosure, closure_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> StableReleasePublicationEvidence: ...


class JsonStableReleasePublicationEvidenceAdapter:
    def load(self, path: str | Path, closure: StableReleasePromotionClosure, closure_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> StableReleasePublicationEvidence:
        return load_stable_release_publication_evidence_manifest(path, closure, closure_archive_path, artifact_base_dir=artifact_base_dir)


STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS: Mapping[str, StableReleasePublicationEvidenceAdapter] = MappingProxyType({'json-manifest': JsonStableReleasePublicationEvidenceAdapter()})


class PostPromotionVerificationStatus(str, Enum):
    VERIFIED = 'verified'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class PostPromotionVerificationPolicy:
    key: str = 'stable'
    target_version: str = '3.0.0'
    required_artifact_keys: tuple[str, ...] = ('publication-integrity', 'post-release-runtime-smoke')
    require_closed_closure: bool = True
    require_published_evidence: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.target_version.strip() or not self.required_artifact_keys:
            raise ValueError('post-promotion verification policy requires key, target version and artifact keys')
        object.__setattr__(self, 'required_artifact_keys', tuple(dict.fromkeys(str(item).strip() for item in self.required_artifact_keys if str(item).strip())))

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key, 'target_version': self.target_version, 'required_artifact_keys': self.required_artifact_keys,
            'require_closed_closure': self.require_closed_closure, 'require_published_evidence': self.require_published_evidence,
        }


POST_PROMOTION_VERIFICATION_POLICY = PostPromotionVerificationPolicy()
POST_PROMOTION_VERIFICATION_POLICIES: Mapping[str, PostPromotionVerificationPolicy] = MappingProxyType({'stable': POST_PROMOTION_VERIFICATION_POLICY})


@dataclass(frozen=True, slots=True)
class PostPromotionVerificationFinding:
    code: str
    status: PostPromotionVerificationStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('post-promotion verification finding code and message must not be empty')
        object.__setattr__(self, 'status', PostPromotionVerificationStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class StablePostPromotionVerification:
    verification_id: str
    closure: StableReleasePromotionClosure
    closure_archive: TargetEvidenceArtifact
    publication: StableReleasePublicationEvidence
    artifacts: tuple[TargetEvidenceArtifact, ...]
    policy: PostPromotionVerificationPolicy
    requested_status: PostPromotionVerificationStatus
    findings: tuple[PostPromotionVerificationFinding, ...]
    observed_framework_version: str | None = None
    observed_nicegui_version: str | None = None
    verification_authority: str | None = None
    verification_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.verification_id) != 64:
            raise ValueError('post-promotion verification id must be sha256')
        object.__setattr__(self, 'artifacts', tuple(self.artifacts))
        object.__setattr__(self, 'requested_status', PostPromotionVerificationStatus(self.requested_status))
        object.__setattr__(self, 'findings', tuple(self.findings))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def status(self) -> PostPromotionVerificationStatus:
        if any(item.status is PostPromotionVerificationStatus.BLOCKED for item in self.findings):
            return PostPromotionVerificationStatus.BLOCKED
        if any(item.status is PostPromotionVerificationStatus.PENDING for item in self.findings):
            return PostPromotionVerificationStatus.PENDING
        return PostPromotionVerificationStatus.VERIFIED

    @property
    def verified(self) -> bool:
        return self.status is PostPromotionVerificationStatus.VERIFIED

    @property
    def next_actions(self) -> tuple[str, ...]:
        actions = tuple(dict.fromkeys(item.remediation for item in self.findings if item.remediation.strip()))
        if actions:
            return actions
        return ('Retain the verified publication/post-release dossier with the immutable Wave 70 closure; ongoing production monitoring remains an external operational responsibility.',)

    def to_dict(self) -> dict[str, Any]:
        candidate = self.closure.release_audit.handoff.candidate
        return {
            'schema_version': 1, 'verification_id': self.verification_id, 'status': self.status.value, 'verified': self.verified,
            'closure': self.closure.to_dict(), 'closure_archive': self.closure_archive.to_dict(), 'publication': self.publication.to_dict(),
            'artifacts': [item.to_dict() for item in self.artifacts], 'policy': self.policy.to_dict(),
            'requested_status': self.requested_status.value, 'findings': [item.to_dict() for item in self.findings],
            'observed_framework_version': self.observed_framework_version, 'observed_nicegui_version': self.observed_nicegui_version,
            'verification_authority': self.verification_authority, 'verification_reference': self.verification_reference,
            'metadata': dict(self.metadata), 'generated_at': self.generated_at, 'next_actions': self.next_actions,
            'candidate_status': candidate.status.value, 'canonical_promotion_decision': candidate.evidence.decision.status.value,
            'affects_candidate_status': False, 'affects_target_gate_status': False,
            'deployment_performed_by_framework': False, 'publication_performed_by_framework': False,
            'post_release_monitoring_performed_by_framework': False,
            'verification_records_external_artifacts_only': True,
        }


def _post_verification_identity_payload(
    closure: StableReleasePromotionClosure, closure_archive: TargetEvidenceArtifact, publication: StableReleasePublicationEvidence,
    artifacts: Sequence[TargetEvidenceArtifact], policy: PostPromotionVerificationPolicy, requested_status: PostPromotionVerificationStatus,
    findings: Sequence[PostPromotionVerificationFinding], *, observed_framework_version: str | None,
    observed_nicegui_version: str | None, verification_authority: str | None, verification_reference: str | None,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'closure_id': closure.closure_id, 'closure_archive': closure_archive.to_dict(), 'publication_id': publication.publication_id,
        'artifacts': [item.to_dict() for item in artifacts], 'policy': policy.to_dict(), 'requested_status': requested_status.value,
        'findings': [item.to_dict() for item in findings], 'observed_framework_version': observed_framework_version,
        'observed_nicegui_version': observed_nicegui_version, 'verification_authority': verification_authority,
        'verification_reference': verification_reference, 'metadata': dict(metadata),
    }


def _post_promotion_findings(
    closure: StableReleasePromotionClosure, closure_archive_path: Path, publication: StableReleasePublicationEvidence,
    artifacts: Sequence[TargetEvidenceArtifact], policy: PostPromotionVerificationPolicy, requested_status: PostPromotionVerificationStatus, *,
    observed_framework_version: str | None, observed_nicegui_version: str | None,
    verification_authority: str | None, verification_reference: str | None, artifact_base_dir: str | Path | None,
) -> tuple[PostPromotionVerificationFinding, ...]:
    findings: list[PostPromotionVerificationFinding] = []
    closure_verification = verify_stable_promotion_closure_archive(closure_archive_path, expected_closure=closure)
    if not closure_verification.verified:
        findings.append(PostPromotionVerificationFinding('closure_archive_not_verified', PostPromotionVerificationStatus.BLOCKED, 'The immutable Wave 70 closure package does not independently verify.', 'Restore the exact verified Wave 70 closure ZIP.'))
    if policy.require_closed_closure:
        if closure.status is StablePromotionClosureStatus.BLOCKED:
            findings.append(PostPromotionVerificationFinding('closure_blocked', PostPromotionVerificationStatus.BLOCKED, 'The canonical Wave 70 closure is BLOCKED.', 'Resolve canonical closure blockers before post-promotion verification.'))
        elif closure.status is not StablePromotionClosureStatus.CLOSED:
            findings.append(PostPromotionVerificationFinding('closure_not_closed', PostPromotionVerificationStatus.PENDING, 'The canonical Wave 70 closure is not CLOSED.', 'Complete the canonical documentary evidence closure first.'))
    publication_verification = verify_stable_release_publication_evidence(publication, closure=closure, closure_archive_path=closure_archive_path, base_dir=artifact_base_dir)
    if policy.require_published_evidence:
        if publication_verification.status is StableReleasePublicationStatus.BLOCKED:
            findings.append(PostPromotionVerificationFinding('publication_blocked', PostPromotionVerificationStatus.BLOCKED, 'Stable release publication evidence is BLOCKED.', 'Resolve publication evidence integrity/identity failures and import a fresh record.'))
        elif publication_verification.status is not StableReleasePublicationStatus.PUBLISHED:
            findings.append(PostPromotionVerificationFinding('publication_not_verified', PostPromotionVerificationStatus.PENDING, 'Stable release publication is not yet artifact-backed PUBLISHED.', 'Attach authoritative publication evidence before post-promotion verification.'))
    if policy.target_version != closure.policy.target_version:
        findings.append(PostPromotionVerificationFinding('target_version_mismatch', PostPromotionVerificationStatus.BLOCKED, 'Post-promotion policy target does not match the Wave 70 closure target.', 'Use the matching stable post-promotion policy.'))
    if observed_framework_version is not None and observed_framework_version != FRAMEWORK_VERSION:
        findings.append(PostPromotionVerificationFinding('post_release_framework_mismatch', PostPromotionVerificationStatus.BLOCKED, 'Observed post-release framework version does not match current NiceGUI Base.', 'Verify the exact released framework build.'))
    if observed_nicegui_version is not None and observed_nicegui_version != NICEGUI_VERSION:
        findings.append(PostPromotionVerificationFinding('post_release_nicegui_mismatch', PostPromotionVerificationStatus.BLOCKED, 'Observed post-release NiceGUI version does not match the exact required version.', f'Verify the released target on NiceGUI {NICEGUI_VERSION}.'))
    artifact_keys = {item.key for item in artifacts}
    for key in policy.required_artifact_keys:
        if key not in artifact_keys:
            findings.append(PostPromotionVerificationFinding('post_release_required_artifact_missing', PostPromotionVerificationStatus.PENDING, f'Required post-release artifact {key!r} is missing.', f'Capture and attach {key!r} evidence from the actual published target.'))
    for artifact in artifacts:
        source = _resolve_artifact_path(artifact, artifact_base_dir)
        if not source.is_file():
            findings.append(PostPromotionVerificationFinding('post_release_artifact_missing', PostPromotionVerificationStatus.BLOCKED, f'Post-release artifact {artifact.key!r} is unavailable.', 'Restore the exact captured post-release artifact bytes.'))
            continue
        blob = source.read_bytes()
        if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
            findings.append(PostPromotionVerificationFinding('post_release_artifact_hash_mismatch', PostPromotionVerificationStatus.BLOCKED, f'Post-release artifact {artifact.key!r} changed after capture.', 'Reject changed evidence and recapture from the published target.'))
    if requested_status is PostPromotionVerificationStatus.BLOCKED:
        findings.append(PostPromotionVerificationFinding('post_release_explicitly_blocked', PostPromotionVerificationStatus.BLOCKED, 'External post-promotion verification explicitly reports BLOCKED.', 'Resolve the external post-release failure and capture new evidence.'))
    elif requested_status is PostPromotionVerificationStatus.PENDING:
        findings.append(PostPromotionVerificationFinding('post_release_requested_pending', PostPromotionVerificationStatus.PENDING, 'Post-promotion verification remains PENDING.', 'Complete the external post-release checks and attach the resulting artifacts.'))
    else:
        if observed_framework_version is None or observed_nicegui_version is None:
            findings.append(PostPromotionVerificationFinding('post_release_identity_missing', PostPromotionVerificationStatus.PENDING, 'Requested VERIFIED lacks complete observed framework/NiceGUI identity.', 'Capture both observed versions from the actual published target.'))
        if not verification_authority or not verification_reference:
            findings.append(PostPromotionVerificationFinding('post_release_authority_reference_missing', PostPromotionVerificationStatus.PENDING, 'Requested VERIFIED lacks traceable verification authority/reference metadata.', 'Attach the external post-release verification authority and immutable reference.'))
    return tuple(findings)


def build_stable_post_promotion_verification(
    closure: StableReleasePromotionClosure,
    closure_archive_path: str | Path,
    publication: StableReleasePublicationEvidence,
    *,
    artifacts: Sequence[TargetEvidenceArtifact] = (),
    requested_status: PostPromotionVerificationStatus | str = PostPromotionVerificationStatus.PENDING,
    observed_framework_version: str | None = None,
    observed_nicegui_version: str | None = None,
    verification_authority: str | None = None,
    verification_reference: str | None = None,
    policy: PostPromotionVerificationPolicy = POST_PROMOTION_VERIFICATION_POLICY,
    artifact_base_dir: str | Path | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> StablePostPromotionVerification:
    archive_path = Path(closure_archive_path)
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    archive_artifact = capture_target_evidence_artifact(archive_path, key='stable-promotion-closure-package', description='immutable Wave 70 stable-promotion closure package')
    status = PostPromotionVerificationStatus(requested_status)
    values = dict(metadata or {})
    findings = _post_promotion_findings(
        closure, archive_path, publication, tuple(artifacts), policy, status,
        observed_framework_version=observed_framework_version, observed_nicegui_version=observed_nicegui_version,
        verification_authority=verification_authority, verification_reference=verification_reference,
        artifact_base_dir=artifact_base_dir,
    )
    payload = _post_verification_identity_payload(
        closure, archive_artifact, publication, tuple(artifacts), policy, status, findings,
        observed_framework_version=observed_framework_version, observed_nicegui_version=observed_nicegui_version,
        verification_authority=verification_authority, verification_reference=verification_reference, metadata=values,
    )
    return StablePostPromotionVerification(
        _canonical_digest(payload), closure, archive_artifact, publication, tuple(artifacts), policy, status, findings,
        observed_framework_version, observed_nicegui_version, verification_authority, verification_reference, values,
    )


def stable_post_promotion_verification_from_dict(payload: Mapping[str, Any]) -> StablePostPromotionVerification:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported post-promotion verification schema {payload.get("schema_version")!r}')
    closure_payload = payload.get('closure'); archive_payload = payload.get('closure_archive'); publication_payload = payload.get('publication')
    if not isinstance(closure_payload, Mapping) or not isinstance(archive_payload, Mapping) or not isinstance(publication_payload, Mapping):
        raise TypeError('post-promotion verification requires closure, closure_archive and publication objects')
    closure = stable_release_promotion_closure_from_dict(closure_payload)
    archive = _target_artifact_from_dict(archive_payload)
    publication = stable_release_publication_evidence_from_dict(publication_payload)
    policy_payload = payload.get('policy') or {}
    policy = PostPromotionVerificationPolicy(
        str(policy_payload.get('key', 'stable')), str(policy_payload.get('target_version', '3.0.0')),
        tuple(str(item) for item in policy_payload.get('required_artifact_keys', ('publication-integrity', 'post-release-runtime-smoke'))),
        bool(policy_payload.get('require_closed_closure', True)), bool(policy_payload.get('require_published_evidence', True)),
    )
    findings = tuple(
        PostPromotionVerificationFinding(str(item['code']), PostPromotionVerificationStatus(str(item['status'])), str(item['message']), str(item.get('remediation', '')))
        for item in payload.get('findings', ()) if isinstance(item, Mapping)
    )
    obj = StablePostPromotionVerification(
        str(payload['verification_id']), closure, archive, publication,
        tuple(_target_artifact_from_dict(item) for item in payload.get('artifacts', ()) if isinstance(item, Mapping)), policy,
        PostPromotionVerificationStatus(str(payload.get('requested_status', 'pending'))), findings,
        None if payload.get('observed_framework_version') is None else str(payload.get('observed_framework_version')),
        None if payload.get('observed_nicegui_version') is None else str(payload.get('observed_nicegui_version')),
        None if payload.get('verification_authority') is None else str(payload.get('verification_authority')),
        None if payload.get('verification_reference') is None else str(payload.get('verification_reference')),
        dict(payload.get('metadata') or {}), str(payload.get('generated_at') or _utc_now()),
    )
    expected = _canonical_digest(_post_verification_identity_payload(
        obj.closure, obj.closure_archive, obj.publication, obj.artifacts, obj.policy, obj.requested_status, obj.findings,
        observed_framework_version=obj.observed_framework_version, observed_nicegui_version=obj.observed_nicegui_version,
        verification_authority=obj.verification_authority, verification_reference=obj.verification_reference, metadata=obj.metadata,
    ))
    if obj.verification_id != expected:
        raise ValueError('post-promotion verification id does not match persisted content')
    if payload.get('status') is not None and str(payload['status']) != obj.status.value:
        raise ValueError('post-promotion verification status does not match persisted content')
    return obj


def write_stable_post_promotion_verification(path: str | Path, verification: StablePostPromotionVerification) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(verification.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_stable_post_promotion_verification(path: str | Path) -> StablePostPromotionVerification:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('post-promotion verification JSON must contain an object')
    return stable_post_promotion_verification_from_dict(payload)


def load_stable_post_promotion_verification_manifest(
    path: str | Path,
    closure: StableReleasePromotionClosure,
    closure_archive_path: str | Path,
    publication: StableReleasePublicationEvidence,
    *, artifact_base_dir: str | Path | None = None,
    policy: PostPromotionVerificationPolicy = POST_PROMOTION_VERIFICATION_POLICY,
) -> StablePostPromotionVerification:
    manifest = Path(path)
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('post-promotion verification manifest must contain an object')
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported post-promotion verification manifest schema {payload.get("schema_version")!r}')
    expected_values = {'closure_id': closure.closure_id, 'publication_id': publication.publication_id, 'target_version': closure.policy.target_version}
    for key, expected in expected_values.items():
        supplied = payload.get(key)
        if supplied is not None and str(supplied) != expected:
            raise ValueError(f'post-promotion verification manifest {key} does not match supplied closure/publication')
    base = Path(artifact_base_dir) if artifact_base_dir is not None else manifest.parent
    artifacts: list[TargetEvidenceArtifact] = []
    for item in payload.get('artifacts', ()):
        if not isinstance(item, Mapping) or not str(item.get('key', '')).strip() or not str(item.get('path', '')).strip():
            raise ValueError('post-promotion manifest artifacts require non-empty key/path')
        source = _safe_manifest_artifact_path(base, str(item['path']))
        if not source.is_file():
            raise FileNotFoundError(source)
        artifacts.append(capture_target_evidence_artifact(source, key=str(item['key']), description=str(item.get('description', ''))))
    return build_stable_post_promotion_verification(
        closure, closure_archive_path, publication, artifacts=tuple(artifacts), requested_status=str(payload.get('status', 'pending')),
        observed_framework_version=None if payload.get('framework_version') is None else str(payload.get('framework_version')),
        observed_nicegui_version=None if payload.get('nicegui_version') is None else str(payload.get('nicegui_version')),
        verification_authority=None if payload.get('verification_authority') is None else str(payload.get('verification_authority')),
        verification_reference=None if payload.get('verification_reference') is None else str(payload.get('verification_reference')),
        policy=policy, artifact_base_dir=artifact_base_dir, metadata=dict(payload.get('metadata') or {}),
    )


@dataclass(frozen=True, slots=True)
class StablePostPromotionVerificationPackage:
    path: str
    sha256: str
    verification_id: str
    status: PostPromotionVerificationStatus
    entries: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or len(self.verification_id) != 64:
            raise ValueError('post-promotion verification package requires sha256 package/verification identifiers')
        object.__setattr__(self, 'status', PostPromotionVerificationStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))

    def to_dict(self) -> dict[str, Any]:
        return {'path': self.path, 'sha256': self.sha256, 'verification_id': self.verification_id, 'status': self.status.value, 'entries': self.entries}


def package_stable_post_promotion_verification(
    path: str | Path,
    verification: StablePostPromotionVerification,
    *, artifact_base_dir: str | Path | None = None,
) -> StablePostPromotionVerificationPackage:
    closure_archive_path = _resolve_artifact_path(verification.closure_archive, artifact_base_dir)
    refreshed = build_stable_post_promotion_verification(
        verification.closure, closure_archive_path, verification.publication, artifacts=verification.artifacts,
        requested_status=verification.requested_status, observed_framework_version=verification.observed_framework_version,
        observed_nicegui_version=verification.observed_nicegui_version, verification_authority=verification.verification_authority,
        verification_reference=verification.verification_reference, policy=verification.policy, artifact_base_dir=artifact_base_dir,
        metadata=verification.metadata,
    )
    if refreshed.status is PostPromotionVerificationStatus.BLOCKED:
        raise ValueError('post-promotion verification package cannot be created from BLOCKED or changed evidence')
    if refreshed.verification_id != verification.verification_id:
        raise ValueError('post-promotion verification identity changed during package verification')
    entries: dict[str, bytes] = {
        'post-promotion-verification.json': _json_bytes(refreshed.to_dict()),
        'publication-evidence.json': _json_bytes(refreshed.publication.to_dict()),
        'closure/stable-promotion-closure.zip': closure_archive_path.read_bytes(),
    }
    for prefix, artifacts in (('publication-evidence', refreshed.publication.artifacts), ('post-release-evidence', refreshed.artifacts)):
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
                raise ValueError(f'unsafe post-promotion verification archive entry {name!r}')
            archive.writestr(_zip_info(name), entries[name])
    return StablePostPromotionVerificationPackage(str(target), hashlib.sha256(target.read_bytes()).hexdigest(), verification.verification_id, verification.status, tuple(sorted(entries)))


__all__ = [
    'JsonStableReleasePublicationEvidenceAdapter','POST_PROMOTION_VERIFICATION_POLICIES','POST_PROMOTION_VERIFICATION_POLICY',
    'PostPromotionVerificationFinding','PostPromotionVerificationPolicy','PostPromotionVerificationStatus',
    'STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS','StablePostPromotionVerification','StablePostPromotionVerificationPackage',
    'StablePromotionClosureArchiveFinding','StablePromotionClosureArchiveStatus','StablePromotionClosureArchiveVerification',
    'StableReleasePublicationEvidence','StableReleasePublicationEvidenceAdapter','StableReleasePublicationFinding',
    'StableReleasePublicationStatus','StableReleasePublicationVerification','build_stable_post_promotion_verification',
    'build_stable_release_publication_evidence','load_stable_post_promotion_verification_manifest',
    'load_stable_release_publication_evidence_manifest','package_stable_post_promotion_verification',
    'read_stable_post_promotion_verification','read_stable_release_publication_evidence',
    'stable_post_promotion_verification_from_dict','stable_release_publication_evidence_from_dict',
    'verify_stable_promotion_closure_archive','verify_stable_release_publication_evidence',
    'write_stable_post_promotion_verification','write_stable_release_publication_evidence',
]
