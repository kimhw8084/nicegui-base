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
from .semiconductor_publication import (
    PostPromotionVerificationStatus,
    StablePostPromotionVerification,
    StableReleasePublicationStatus,
    read_stable_post_promotion_verification,
    stable_post_promotion_verification_from_dict,
    stable_release_publication_evidence_from_dict,
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
        raise ValueError(f'post-release stability artifact path escapes manifest base directory: {value!r}') from exc
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
    artifacts: Sequence[TargetEvidenceArtifact],
    *,
    base_dir: str | Path | None,
    missing_status: Enum,
    blocked_status: Enum,
    finding_type,
    missing_code: str,
    absent_code: str,
    changed_code: str,
    required_keys: Sequence[str],
    subject: str,
):
    findings = []
    artifact_keys = {item.key for item in artifacts}
    for key in required_keys:
        if key not in artifact_keys:
            findings.append(finding_type(
                missing_code, missing_status, f'Required {subject} artifact {key!r} is missing.',
                f'Capture and attach {key!r} evidence from the actual company target.',
            ))
    for artifact in artifacts:
        source = _resolve_artifact_path(artifact, base_dir)
        if not source.is_file():
            findings.append(finding_type(
                absent_code, blocked_status, f'{subject.title()} artifact {artifact.key!r} is unavailable.',
                f'Restore the exact captured {subject} artifact bytes.',
            ))
            continue
        blob = source.read_bytes()
        if len(blob) != artifact.size_bytes or hashlib.sha256(blob).hexdigest() != artifact.sha256:
            findings.append(finding_type(
                changed_code, blocked_status, f'{subject.title()} artifact {artifact.key!r} changed after capture.',
                f'Reject changed {subject} evidence and recapture it from the actual company target.',
            ))
    return findings


class StablePostPromotionArchiveStatus(str, Enum):
    VERIFIED = 'verified'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class StablePostPromotionArchiveFinding:
    code: str
    status: StablePostPromotionArchiveStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('post-promotion archive finding code and message must not be empty')
        object.__setattr__(self, 'status', StablePostPromotionArchiveStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class StablePostPromotionArchiveVerification:
    path: str
    sha256: str | None
    status: StablePostPromotionArchiveStatus
    verification_id: str | None = None
    publication_id: str | None = None
    closure_id: str | None = None
    entries: tuple[str, ...] = ()
    findings: tuple[StablePostPromotionArchiveFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.sha256 is not None and len(self.sha256) != 64:
            raise ValueError('post-promotion archive sha256 must be 64 hex characters when present')
        object.__setattr__(self, 'status', StablePostPromotionArchiveStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def verified(self) -> bool:
        return self.status is StablePostPromotionArchiveStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': self.path, 'sha256': self.sha256, 'status': self.status.value, 'verified': self.verified,
            'verification_id': self.verification_id, 'publication_id': self.publication_id, 'closure_id': self.closure_id,
            'entries': self.entries, 'findings': [item.to_dict() for item in self.findings],
        }


def _blocked_post_archive(path: str | Path, code: str, message: str, remediation: str, *, sha256: str | None = None, entries: Sequence[str] = ()) -> StablePostPromotionArchiveVerification:
    return StablePostPromotionArchiveVerification(
        str(path), sha256, StablePostPromotionArchiveStatus.BLOCKED, entries=tuple(entries),
        findings=(StablePostPromotionArchiveFinding(code, StablePostPromotionArchiveStatus.BLOCKED, message, remediation),),
    )


def verify_stable_post_promotion_archive(
    path: str | Path,
    *,
    expected_verification: StablePostPromotionVerification | None = None,
) -> StablePostPromotionArchiveVerification:
    target = Path(path)
    if not target.is_file():
        return _blocked_post_archive(target, 'post_promotion_archive_missing', 'The Wave 71 post-promotion verification archive is unavailable.', 'Restore the exact immutable Wave 71 post-promotion ZIP before stability evidence intake.')
    data = target.read_bytes()
    archive_sha = hashlib.sha256(data).hexdigest()
    try:
        with zipfile.ZipFile(target) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if len(names) != len(set(names)):
                return _blocked_post_archive(target, 'post_promotion_archive_duplicate_entry', 'The post-promotion ZIP contains duplicate entries.', 'Recreate the package with the canonical Wave 71 packager.', sha256=archive_sha, entries=names)
            for name in names:
                pure = PurePosixPath(name)
                if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                    return _blocked_post_archive(target, 'post_promotion_archive_unsafe_entry', f'The post-promotion ZIP contains unsafe entry {name!r}.', 'Reject the archive and recreate it with the canonical Wave 71 packager.', sha256=archive_sha, entries=names)
            required = {'post-promotion-verification.json', 'publication-evidence.json', 'closure/stable-promotion-closure.zip', 'MANIFEST.sha256'}
            missing = sorted(required - set(names))
            if missing:
                return _blocked_post_archive(target, 'post_promotion_archive_required_entry_missing', f'The post-promotion ZIP is missing required entries: {missing}.', 'Recreate the complete self-contained Wave 71 post-promotion package.', sha256=archive_sha, entries=names)
            expected_hashes = _parse_manifest(archive.read('MANIFEST.sha256'))
            payload_names = set(names) - {'MANIFEST.sha256'}
            if set(expected_hashes) != payload_names:
                return _blocked_post_archive(target, 'post_promotion_archive_manifest_incomplete', 'MANIFEST.sha256 does not cover exactly every non-manifest archive entry.', 'Recreate the package with complete deterministic hashing.', sha256=archive_sha, entries=names)
            for name, expected_sha in expected_hashes.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected_sha:
                    return _blocked_post_archive(target, 'post_promotion_archive_hash_mismatch', f'Archive entry {name!r} does not match MANIFEST.sha256.', 'Reject changed post-promotion bytes and restore/recreate the immutable package.', sha256=archive_sha, entries=names)
            payload = json.loads(archive.read('post-promotion-verification.json').decode('utf-8'))
            if not isinstance(payload, Mapping):
                raise TypeError('post-promotion-verification.json must contain an object')
            verification = stable_post_promotion_verification_from_dict(payload)
            if expected_verification is not None and verification.verification_id != expected_verification.verification_id:
                return _blocked_post_archive(target, 'post_promotion_archive_identity_mismatch', 'The post-promotion archive contains a different verification identity than supplied.', 'Use the exact Wave 71 archive created for this verification.', sha256=archive_sha, entries=names)
            publication_payload = json.loads(archive.read('publication-evidence.json').decode('utf-8'))
            if not isinstance(publication_payload, Mapping):
                raise TypeError('publication-evidence.json must contain an object')
            publication = stable_release_publication_evidence_from_dict(publication_payload)
            if publication.publication_id != verification.publication.publication_id:
                return _blocked_post_archive(target, 'post_promotion_archive_publication_mismatch', 'The separately embedded publication evidence does not match the post-promotion verification.', 'Recreate the canonical self-contained Wave 71 package.', sha256=archive_sha, entries=names)
            closure_bytes = archive.read('closure/stable-promotion-closure.zip')
            if hashlib.sha256(closure_bytes).hexdigest() != verification.closure_archive.sha256 or len(closure_bytes) != verification.closure_archive.size_bytes:
                return _blocked_post_archive(target, 'post_promotion_archive_closure_mismatch', 'The embedded Wave 70 closure ZIP does not match the verification artifact binding.', 'Restore the exact Wave 70 closure package and recreate the Wave 71 package.', sha256=archive_sha, entries=names)
            return StablePostPromotionArchiveVerification(
                str(target), archive_sha, StablePostPromotionArchiveStatus.VERIFIED,
                verification.verification_id, verification.publication.publication_id, verification.closure.closure_id,
                tuple(sorted(names)), (),
            )
    except (OSError, zipfile.BadZipFile, RuntimeError, KeyError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return _blocked_post_archive(target, 'post_promotion_archive_invalid', f'The post-promotion ZIP cannot be read safely: {exc}', 'Restore or recreate the canonical Wave 71 post-promotion package.', sha256=archive_sha)


class PostReleaseStabilityStatus(str, Enum):
    STABLE = 'stable'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class PostReleaseStabilityPolicy:
    key: str = 'stable'
    target_version: str = '3.0.0'
    required_artifact_keys: tuple[str, ...] = ('production-health-window', 'incident-summary')
    require_verified_post_promotion: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.target_version.strip() or not self.required_artifact_keys:
            raise ValueError('post-release stability policy requires key, target version and artifact keys')
        object.__setattr__(self, 'required_artifact_keys', tuple(dict.fromkeys(str(item).strip() for item in self.required_artifact_keys if str(item).strip())))

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key, 'target_version': self.target_version,
            'required_artifact_keys': self.required_artifact_keys,
            'require_verified_post_promotion': self.require_verified_post_promotion,
        }


POST_RELEASE_STABILITY_POLICY = PostReleaseStabilityPolicy()
POST_RELEASE_STABILITY_POLICIES: Mapping[str, PostReleaseStabilityPolicy] = MappingProxyType({'stable': POST_RELEASE_STABILITY_POLICY})


@dataclass(frozen=True, slots=True)
class PostReleaseStabilityFinding:
    code: str
    status: PostReleaseStabilityStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('post-release stability finding code and message must not be empty')
        object.__setattr__(self, 'status', PostReleaseStabilityStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class PostReleaseStabilityEvidence:
    stability_id: str
    post_verification_id: str
    publication_id: str
    post_promotion_archive_sha256: str
    target_version: str
    requested_status: PostReleaseStabilityStatus
    artifacts: tuple[TargetEvidenceArtifact, ...]
    policy: PostReleaseStabilityPolicy = POST_RELEASE_STABILITY_POLICY
    framework_version: str = FRAMEWORK_VERSION
    nicegui_required: str = NICEGUI_VERSION
    observed_framework_version: str | None = None
    observed_nicegui_version: str | None = None
    stability_authority: str | None = None
    stability_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    captured_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if any(len(value) != 64 for value in (self.stability_id, self.post_verification_id, self.publication_id, self.post_promotion_archive_sha256)):
            raise ValueError('post-release stability requires sha256 stability/post/publication/archive identifiers')
        object.__setattr__(self, 'requested_status', PostReleaseStabilityStatus(self.requested_status))
        artifacts = tuple(self.artifacts)
        if len({item.key for item in artifacts}) != len(artifacts):
            raise ValueError('post-release stability contains duplicate artifact keys')
        object.__setattr__(self, 'artifacts', artifacts)
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'stability_id': self.stability_id, 'post_verification_id': self.post_verification_id,
            'publication_id': self.publication_id, 'post_promotion_archive_sha256': self.post_promotion_archive_sha256,
            'target_version': self.target_version, 'requested_status': self.requested_status.value,
            'artifacts': [item.to_dict() for item in self.artifacts], 'policy': self.policy.to_dict(),
            'framework_version': self.framework_version, 'nicegui_required': self.nicegui_required,
            'observed_framework_version': self.observed_framework_version, 'observed_nicegui_version': self.observed_nicegui_version,
            'stability_authority': self.stability_authority, 'stability_reference': self.stability_reference,
            'metadata': dict(self.metadata), 'captured_at': self.captured_at,
            'monitoring_performed_by_framework': False, 'incident_response_performed_by_framework': False,
            'rollback_performed_by_framework': False, 'records_external_artifacts_only': True,
            'does_not_mutate_publication_or_promotion_truth': True,
        }


def _stability_identity_payload(
    post_verification_id: str, publication_id: str, post_promotion_archive_sha256: str, target_version: str,
    requested_status: PostReleaseStabilityStatus, artifacts: Sequence[TargetEvidenceArtifact], policy: PostReleaseStabilityPolicy, *,
    framework_version: str, nicegui_required: str, observed_framework_version: str | None,
    observed_nicegui_version: str | None, stability_authority: str | None, stability_reference: str | None,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'post_verification_id': post_verification_id, 'publication_id': publication_id,
        'post_promotion_archive_sha256': post_promotion_archive_sha256, 'target_version': target_version,
        'requested_status': requested_status.value, 'artifacts': [item.to_dict() for item in artifacts], 'policy': policy.to_dict(),
        'framework_version': framework_version, 'nicegui_required': nicegui_required,
        'observed_framework_version': observed_framework_version, 'observed_nicegui_version': observed_nicegui_version,
        'stability_authority': stability_authority, 'stability_reference': stability_reference, 'metadata': dict(metadata),
    }


def build_post_release_stability_evidence(
    post_verification: StablePostPromotionVerification,
    post_promotion_archive_path: str | Path,
    *,
    requested_status: PostReleaseStabilityStatus | str = PostReleaseStabilityStatus.PENDING,
    artifacts: Sequence[TargetEvidenceArtifact] = (),
    observed_framework_version: str | None = None,
    observed_nicegui_version: str | None = None,
    stability_authority: str | None = None,
    stability_reference: str | None = None,
    policy: PostReleaseStabilityPolicy = POST_RELEASE_STABILITY_POLICY,
    metadata: Mapping[str, Any] | None = None,
) -> PostReleaseStabilityEvidence:
    archive = Path(post_promotion_archive_path)
    if not archive.is_file():
        raise FileNotFoundError(archive)
    status = PostReleaseStabilityStatus(requested_status)
    values = dict(metadata or {})
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    payload = _stability_identity_payload(
        post_verification.verification_id, post_verification.publication.publication_id, archive_sha, post_verification.policy.target_version,
        status, tuple(artifacts), policy, framework_version=FRAMEWORK_VERSION, nicegui_required=NICEGUI_VERSION,
        observed_framework_version=observed_framework_version, observed_nicegui_version=observed_nicegui_version,
        stability_authority=stability_authority, stability_reference=stability_reference, metadata=values,
    )
    return PostReleaseStabilityEvidence(
        _canonical_digest(payload), post_verification.verification_id, post_verification.publication.publication_id,
        archive_sha, post_verification.policy.target_version, status, tuple(artifacts), policy, FRAMEWORK_VERSION, NICEGUI_VERSION,
        observed_framework_version, observed_nicegui_version, stability_authority, stability_reference, values,
    )


def post_release_stability_evidence_from_dict(payload: Mapping[str, Any]) -> PostReleaseStabilityEvidence:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported post-release stability evidence schema {payload.get("schema_version")!r}')
    policy_payload = payload.get('policy') or {}
    policy = PostReleaseStabilityPolicy(
        str(policy_payload.get('key', 'stable')), str(policy_payload.get('target_version', '3.0.0')),
        tuple(str(item) for item in policy_payload.get('required_artifact_keys', ('production-health-window', 'incident-summary'))),
        bool(policy_payload.get('require_verified_post_promotion', True)),
    )
    evidence = PostReleaseStabilityEvidence(
        str(payload['stability_id']), str(payload['post_verification_id']), str(payload['publication_id']),
        str(payload['post_promotion_archive_sha256']), str(payload['target_version']),
        PostReleaseStabilityStatus(str(payload['requested_status'])),
        tuple(_target_artifact_from_dict(item) for item in payload.get('artifacts', ()) if isinstance(item, Mapping)), policy,
        str(payload.get('framework_version') or FRAMEWORK_VERSION), str(payload.get('nicegui_required') or NICEGUI_VERSION),
        None if payload.get('observed_framework_version') is None else str(payload.get('observed_framework_version')),
        None if payload.get('observed_nicegui_version') is None else str(payload.get('observed_nicegui_version')),
        None if payload.get('stability_authority') is None else str(payload.get('stability_authority')),
        None if payload.get('stability_reference') is None else str(payload.get('stability_reference')),
        dict(payload.get('metadata') or {}), str(payload.get('captured_at') or _utc_now()),
    )
    expected = _canonical_digest(_stability_identity_payload(
        evidence.post_verification_id, evidence.publication_id, evidence.post_promotion_archive_sha256, evidence.target_version,
        evidence.requested_status, evidence.artifacts, evidence.policy, framework_version=evidence.framework_version,
        nicegui_required=evidence.nicegui_required, observed_framework_version=evidence.observed_framework_version,
        observed_nicegui_version=evidence.observed_nicegui_version, stability_authority=evidence.stability_authority,
        stability_reference=evidence.stability_reference, metadata=evidence.metadata,
    ))
    if evidence.stability_id != expected:
        raise ValueError('post-release stability id does not match persisted content')
    return evidence


def write_post_release_stability_evidence(path: str | Path, evidence: PostReleaseStabilityEvidence) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_post_release_stability_evidence(path: str | Path) -> PostReleaseStabilityEvidence:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('post-release stability JSON must contain an object')
    return post_release_stability_evidence_from_dict(payload)


@dataclass(frozen=True, slots=True)
class PostReleaseStabilityVerification:
    stability_id: str
    status: PostReleaseStabilityStatus
    findings: tuple[PostReleaseStabilityFinding, ...]

    def __post_init__(self) -> None:
        if len(self.stability_id) != 64:
            raise ValueError('post-release stability verification requires sha256 stability id')
        object.__setattr__(self, 'status', PostReleaseStabilityStatus(self.status))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def stable(self) -> bool:
        return self.status is PostReleaseStabilityStatus.STABLE

    def to_dict(self) -> dict[str, Any]:
        return {'stability_id': self.stability_id, 'status': self.status.value, 'stable': self.stable, 'findings': [item.to_dict() for item in self.findings]}


def verify_post_release_stability_evidence(
    evidence: PostReleaseStabilityEvidence,
    *,
    post_verification: StablePostPromotionVerification,
    post_promotion_archive_path: str | Path,
    base_dir: str | Path | None = None,
) -> PostReleaseStabilityVerification:
    findings: list[PostReleaseStabilityFinding] = []
    archive_verification = verify_stable_post_promotion_archive(post_promotion_archive_path, expected_verification=post_verification)
    if not archive_verification.verified:
        findings.append(PostReleaseStabilityFinding('post_promotion_archive_not_verified', PostReleaseStabilityStatus.BLOCKED, 'The immutable Wave 71 post-promotion archive does not verify.', 'Restore the exact Wave 71 post-promotion ZIP.'))
    actual_sha = hashlib.sha256(Path(post_promotion_archive_path).read_bytes()).hexdigest() if Path(post_promotion_archive_path).is_file() else None
    if actual_sha is not None and evidence.post_promotion_archive_sha256 != actual_sha:
        findings.append(PostReleaseStabilityFinding('stability_archive_hash_mismatch', PostReleaseStabilityStatus.BLOCKED, 'The stability record is bound to a different Wave 71 archive hash.', 'Use the exact post-promotion archive captured by this stability record.'))
    if evidence.post_verification_id != post_verification.verification_id or evidence.publication_id != post_verification.publication.publication_id:
        findings.append(PostReleaseStabilityFinding('stability_subject_identity_mismatch', PostReleaseStabilityStatus.BLOCKED, 'The stability record does not match the supplied post-promotion/publication identity.', 'Use evidence captured for the exact Wave 71 verification chain.'))
    if evidence.target_version != post_verification.policy.target_version or evidence.policy.target_version != evidence.target_version:
        findings.append(PostReleaseStabilityFinding('stability_target_version_mismatch', PostReleaseStabilityStatus.BLOCKED, 'The stability target version does not match the verified release target.', 'Use a stability policy matching the exact published target.'))
    if evidence.framework_version != FRAMEWORK_VERSION or evidence.nicegui_required != NICEGUI_VERSION:
        findings.append(PostReleaseStabilityFinding('stability_framework_contract_mismatch', PostReleaseStabilityStatus.BLOCKED, 'The stability record framework/NiceGUI contract does not match current NiceGUI Base.', 'Recreate the record with the current framework contract.'))
    if evidence.observed_framework_version is not None and evidence.observed_framework_version != FRAMEWORK_VERSION:
        findings.append(PostReleaseStabilityFinding('stability_observed_framework_mismatch', PostReleaseStabilityStatus.BLOCKED, 'Observed production framework version does not match current NiceGUI Base.', 'Verify the actual released framework build.'))
    if evidence.observed_nicegui_version is not None and evidence.observed_nicegui_version != NICEGUI_VERSION:
        findings.append(PostReleaseStabilityFinding('stability_observed_nicegui_mismatch', PostReleaseStabilityStatus.BLOCKED, 'Observed production NiceGUI version does not match the exact required version.', f'Verify the production target on NiceGUI {NICEGUI_VERSION}.'))
    if evidence.policy.require_verified_post_promotion and post_verification.status is not PostPromotionVerificationStatus.VERIFIED:
        status = PostReleaseStabilityStatus.BLOCKED if post_verification.status is PostPromotionVerificationStatus.BLOCKED else PostReleaseStabilityStatus.PENDING
        findings.append(PostReleaseStabilityFinding('post_promotion_not_verified', status, 'Wave 71 post-promotion verification is not VERIFIED.', 'Complete the canonical Wave 71 verification before asserting stable production evidence.'))
    findings.extend(_artifact_findings(
        evidence.artifacts, base_dir=base_dir, missing_status=PostReleaseStabilityStatus.PENDING,
        blocked_status=PostReleaseStabilityStatus.BLOCKED, finding_type=PostReleaseStabilityFinding,
        missing_code='stability_required_artifact_missing', absent_code='stability_artifact_missing', changed_code='stability_artifact_hash_mismatch',
        required_keys=evidence.policy.required_artifact_keys, subject='post-release stability',
    ))
    if evidence.requested_status is PostReleaseStabilityStatus.BLOCKED:
        findings.append(PostReleaseStabilityFinding('stability_explicitly_blocked', PostReleaseStabilityStatus.BLOCKED, 'External production stability evidence explicitly reports BLOCKED.', 'Resolve the external production-health issue and capture fresh evidence.'))
    elif evidence.requested_status is PostReleaseStabilityStatus.PENDING:
        findings.append(PostReleaseStabilityFinding('stability_requested_pending', PostReleaseStabilityStatus.PENDING, 'Post-release stability remains PENDING.', 'Complete the external production-health/incident review and attach the resulting artifacts.'))
    else:
        if evidence.observed_framework_version is None or evidence.observed_nicegui_version is None:
            findings.append(PostReleaseStabilityFinding('stability_observed_identity_missing', PostReleaseStabilityStatus.PENDING, 'Requested STABLE lacks complete observed framework/NiceGUI identity.', 'Capture both observed versions from the actual production target.'))
        if not evidence.stability_authority or not evidence.stability_reference:
            findings.append(PostReleaseStabilityFinding('stability_authority_reference_missing', PostReleaseStabilityStatus.PENDING, 'Requested STABLE lacks traceable external authority/reference metadata.', 'Attach the production stability authority and immutable evidence reference.'))
    status = PostReleaseStabilityStatus.STABLE
    if any(item.status is PostReleaseStabilityStatus.BLOCKED for item in findings):
        status = PostReleaseStabilityStatus.BLOCKED
    elif any(item.status is PostReleaseStabilityStatus.PENDING for item in findings):
        status = PostReleaseStabilityStatus.PENDING
    return PostReleaseStabilityVerification(evidence.stability_id, status, tuple(findings))


def load_post_release_stability_manifest(
    path: str | Path,
    post_verification: StablePostPromotionVerification,
    post_promotion_archive_path: str | Path,
    *,
    artifact_base_dir: str | Path | None = None,
    policy: PostReleaseStabilityPolicy = POST_RELEASE_STABILITY_POLICY,
) -> PostReleaseStabilityEvidence:
    manifest = Path(path)
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('post-release stability manifest must contain an object')
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported post-release stability manifest schema {payload.get("schema_version")!r}')
    expected_values = {
        'post_verification_id': post_verification.verification_id,
        'publication_id': post_verification.publication.publication_id,
        'target_version': post_verification.policy.target_version,
    }
    for key, expected in expected_values.items():
        supplied = payload.get(key)
        if supplied is not None and str(supplied) != expected:
            raise ValueError(f'post-release stability manifest {key} does not match supplied Wave 71 verification')
    base = Path(artifact_base_dir) if artifact_base_dir is not None else manifest.parent
    artifacts: list[TargetEvidenceArtifact] = []
    for item in payload.get('artifacts', ()):
        if not isinstance(item, Mapping) or not str(item.get('key', '')).strip() or not str(item.get('path', '')).strip():
            raise ValueError('post-release stability manifest artifacts require non-empty key/path')
        source = _safe_manifest_artifact_path(base, str(item['path']))
        if not source.is_file():
            raise FileNotFoundError(source)
        artifacts.append(capture_target_evidence_artifact(source, key=str(item['key']), description=str(item.get('description', ''))))
    return build_post_release_stability_evidence(
        post_verification, post_promotion_archive_path, requested_status=str(payload.get('status', 'pending')), artifacts=tuple(artifacts),
        observed_framework_version=None if payload.get('framework_version') is None else str(payload.get('framework_version')),
        observed_nicegui_version=None if payload.get('nicegui_version') is None else str(payload.get('nicegui_version')),
        stability_authority=None if payload.get('stability_authority') is None else str(payload.get('stability_authority')),
        stability_reference=None if payload.get('stability_reference') is None else str(payload.get('stability_reference')),
        policy=policy, metadata=dict(payload.get('metadata') or {}),
    )


@runtime_checkable
class PostReleaseStabilityEvidenceAdapter(Protocol):
    def load(self, path: str | Path, post_verification: StablePostPromotionVerification, post_promotion_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> PostReleaseStabilityEvidence: ...


class JsonPostReleaseStabilityEvidenceAdapter:
    def load(self, path: str | Path, post_verification: StablePostPromotionVerification, post_promotion_archive_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> PostReleaseStabilityEvidence:
        return load_post_release_stability_manifest(path, post_verification, post_promotion_archive_path, artifact_base_dir=artifact_base_dir)


POST_RELEASE_STABILITY_EVIDENCE_ADAPTERS: Mapping[str, PostReleaseStabilityEvidenceAdapter] = MappingProxyType({'json-manifest': JsonPostReleaseStabilityEvidenceAdapter()})


class RollbackReadinessStatus(str, Enum):
    READY = 'ready'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class RollbackReadinessPolicy:
    key: str = 'stable'
    target_version: str = '3.0.0'
    required_artifact_keys: tuple[str, ...] = ('rollback-plan-validation', 'rollback-artifact-integrity', 'rollback-rehearsal')
    require_stable_post_release_evidence: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.target_version.strip() or not self.required_artifact_keys:
            raise ValueError('rollback readiness policy requires key, target version and artifact keys')
        object.__setattr__(self, 'required_artifact_keys', tuple(dict.fromkeys(str(item).strip() for item in self.required_artifact_keys if str(item).strip())))

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key, 'target_version': self.target_version, 'required_artifact_keys': self.required_artifact_keys,
            'require_stable_post_release_evidence': self.require_stable_post_release_evidence,
        }


ROLLBACK_READINESS_POLICY = RollbackReadinessPolicy()
ROLLBACK_READINESS_POLICIES: Mapping[str, RollbackReadinessPolicy] = MappingProxyType({'stable': ROLLBACK_READINESS_POLICY})


@dataclass(frozen=True, slots=True)
class RollbackReadinessFinding:
    code: str
    status: RollbackReadinessStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('rollback readiness finding code and message must not be empty')
        object.__setattr__(self, 'status', RollbackReadinessStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'status': self.status.value, 'message': self.message, 'remediation': self.remediation}


@dataclass(frozen=True, slots=True)
class StableRollbackReadinessVerification:
    readiness_id: str
    post_verification: StablePostPromotionVerification
    post_promotion_archive: TargetEvidenceArtifact
    stability_evidence: PostReleaseStabilityEvidence
    rollback_artifacts: tuple[TargetEvidenceArtifact, ...]
    rollback_execution_artifacts: tuple[TargetEvidenceArtifact, ...]
    policy: RollbackReadinessPolicy
    requested_status: RollbackReadinessStatus
    findings: tuple[RollbackReadinessFinding, ...]
    readiness_authority: str | None = None
    readiness_reference: str | None = None
    rollback_execution_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.readiness_id) != 64:
            raise ValueError('rollback readiness id must be sha256')
        object.__setattr__(self, 'rollback_artifacts', tuple(self.rollback_artifacts))
        object.__setattr__(self, 'rollback_execution_artifacts', tuple(self.rollback_execution_artifacts))
        object.__setattr__(self, 'requested_status', RollbackReadinessStatus(self.requested_status))
        object.__setattr__(self, 'findings', tuple(self.findings))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def status(self) -> RollbackReadinessStatus:
        if any(item.status is RollbackReadinessStatus.BLOCKED for item in self.findings):
            return RollbackReadinessStatus.BLOCKED
        if any(item.status is RollbackReadinessStatus.PENDING for item in self.findings):
            return RollbackReadinessStatus.PENDING
        return RollbackReadinessStatus.READY

    @property
    def ready(self) -> bool:
        return self.status is RollbackReadinessStatus.READY

    @property
    def next_actions(self) -> tuple[str, ...]:
        actions = tuple(dict.fromkeys(item.remediation for item in self.findings if item.remediation.strip()))
        if actions:
            return actions
        return ('Retain the verified rollback-readiness dossier with the exact Wave 71 post-promotion package; actual monitoring, incident response and rollback remain external operations.',)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'readiness_id': self.readiness_id, 'status': self.status.value, 'ready': self.ready,
            'post_verification': self.post_verification.to_dict(), 'post_promotion_archive': self.post_promotion_archive.to_dict(),
            'stability_evidence': self.stability_evidence.to_dict(),
            'rollback_artifacts': [item.to_dict() for item in self.rollback_artifacts],
            'rollback_execution_artifacts': [item.to_dict() for item in self.rollback_execution_artifacts],
            'policy': self.policy.to_dict(), 'requested_status': self.requested_status.value,
            'findings': [item.to_dict() for item in self.findings], 'readiness_authority': self.readiness_authority,
            'readiness_reference': self.readiness_reference, 'rollback_execution_reference': self.rollback_execution_reference,
            'metadata': dict(self.metadata), 'generated_at': self.generated_at, 'next_actions': self.next_actions,
            'monitoring_performed_by_framework': False, 'incident_response_performed_by_framework': False,
            'rollback_performed_by_framework': False, 'rollback_execution_artifacts_are_external_evidence_only': True,
            'affects_publication_status': False, 'affects_post_promotion_status': False, 'affects_canonical_promotion_truth': False,
        }


def _rollback_identity_payload(
    post_verification: StablePostPromotionVerification, post_promotion_archive: TargetEvidenceArtifact,
    stability_evidence: PostReleaseStabilityEvidence, rollback_artifacts: Sequence[TargetEvidenceArtifact],
    rollback_execution_artifacts: Sequence[TargetEvidenceArtifact], policy: RollbackReadinessPolicy,
    requested_status: RollbackReadinessStatus, findings: Sequence[RollbackReadinessFinding], *,
    readiness_authority: str | None, readiness_reference: str | None, rollback_execution_reference: str | None,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'post_verification_id': post_verification.verification_id, 'post_promotion_archive': post_promotion_archive.to_dict(),
        'stability_id': stability_evidence.stability_id, 'rollback_artifacts': [item.to_dict() for item in rollback_artifacts],
        'rollback_execution_artifacts': [item.to_dict() for item in rollback_execution_artifacts], 'policy': policy.to_dict(),
        'requested_status': requested_status.value, 'findings': [item.to_dict() for item in findings],
        'readiness_authority': readiness_authority, 'readiness_reference': readiness_reference,
        'rollback_execution_reference': rollback_execution_reference, 'metadata': dict(metadata),
    }


def _rollback_readiness_findings(
    post_verification: StablePostPromotionVerification, post_promotion_archive_path: Path,
    stability_evidence: PostReleaseStabilityEvidence, rollback_artifacts: Sequence[TargetEvidenceArtifact],
    rollback_execution_artifacts: Sequence[TargetEvidenceArtifact], policy: RollbackReadinessPolicy,
    requested_status: RollbackReadinessStatus, *, readiness_authority: str | None, readiness_reference: str | None,
    artifact_base_dir: str | Path | None,
) -> tuple[RollbackReadinessFinding, ...]:
    findings: list[RollbackReadinessFinding] = []
    archive_verification = verify_stable_post_promotion_archive(post_promotion_archive_path, expected_verification=post_verification)
    if not archive_verification.verified:
        findings.append(RollbackReadinessFinding('rollback_post_archive_not_verified', RollbackReadinessStatus.BLOCKED, 'The immutable Wave 71 post-promotion package does not independently verify.', 'Restore the exact verified Wave 71 package.'))
    stability_verification = verify_post_release_stability_evidence(
        stability_evidence, post_verification=post_verification, post_promotion_archive_path=post_promotion_archive_path, base_dir=artifact_base_dir,
    )
    if policy.require_stable_post_release_evidence:
        if stability_verification.status is PostReleaseStabilityStatus.BLOCKED:
            findings.append(RollbackReadinessFinding('rollback_stability_blocked', RollbackReadinessStatus.BLOCKED, 'Post-release stability evidence is BLOCKED.', 'Resolve production-health evidence integrity/identity failures first.'))
        elif stability_verification.status is not PostReleaseStabilityStatus.STABLE:
            findings.append(RollbackReadinessFinding('rollback_stability_not_stable', RollbackReadinessStatus.PENDING, 'Post-release stability evidence is not yet STABLE.', 'Complete the external production stability evidence intake first.'))
    if policy.target_version != post_verification.policy.target_version:
        findings.append(RollbackReadinessFinding('rollback_target_version_mismatch', RollbackReadinessStatus.BLOCKED, 'Rollback-readiness policy target does not match the published release target.', 'Use the matching rollback-readiness policy.'))
    findings.extend(_artifact_findings(
        rollback_artifacts, base_dir=artifact_base_dir, missing_status=RollbackReadinessStatus.PENDING,
        blocked_status=RollbackReadinessStatus.BLOCKED, finding_type=RollbackReadinessFinding,
        missing_code='rollback_required_artifact_missing', absent_code='rollback_artifact_missing', changed_code='rollback_artifact_hash_mismatch',
        required_keys=policy.required_artifact_keys, subject='rollback readiness',
    ))
    findings.extend(_artifact_findings(
        rollback_execution_artifacts, base_dir=artifact_base_dir, missing_status=RollbackReadinessStatus.PENDING,
        blocked_status=RollbackReadinessStatus.BLOCKED, finding_type=RollbackReadinessFinding,
        missing_code='rollback_execution_required_artifact_missing', absent_code='rollback_execution_artifact_missing', changed_code='rollback_execution_artifact_hash_mismatch',
        required_keys=(), subject='rollback execution',
    ))
    if requested_status is RollbackReadinessStatus.BLOCKED:
        findings.append(RollbackReadinessFinding('rollback_readiness_explicitly_blocked', RollbackReadinessStatus.BLOCKED, 'External rollback readiness explicitly reports BLOCKED.', 'Resolve the external rollback-readiness failure and capture fresh evidence.'))
    elif requested_status is RollbackReadinessStatus.PENDING:
        findings.append(RollbackReadinessFinding('rollback_readiness_requested_pending', RollbackReadinessStatus.PENDING, 'Rollback readiness remains PENDING.', 'Complete the external rollback validation/rehearsal and attach the resulting artifacts.'))
    elif not readiness_authority or not readiness_reference:
        findings.append(RollbackReadinessFinding('rollback_readiness_authority_reference_missing', RollbackReadinessStatus.PENDING, 'Requested READY lacks traceable external authority/reference metadata.', 'Attach the rollback-readiness authority and immutable reference.'))
    return tuple(findings)


def build_stable_rollback_readiness_verification(
    post_verification: StablePostPromotionVerification,
    post_promotion_archive_path: str | Path,
    stability_evidence: PostReleaseStabilityEvidence,
    *,
    rollback_artifacts: Sequence[TargetEvidenceArtifact] = (),
    rollback_execution_artifacts: Sequence[TargetEvidenceArtifact] = (),
    requested_status: RollbackReadinessStatus | str = RollbackReadinessStatus.PENDING,
    readiness_authority: str | None = None,
    readiness_reference: str | None = None,
    rollback_execution_reference: str | None = None,
    policy: RollbackReadinessPolicy = ROLLBACK_READINESS_POLICY,
    artifact_base_dir: str | Path | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> StableRollbackReadinessVerification:
    archive_path = Path(post_promotion_archive_path)
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    archive_artifact = capture_target_evidence_artifact(archive_path, key='post-promotion-verification-package', description='immutable Wave 71 post-promotion verification package')
    status = RollbackReadinessStatus(requested_status)
    values = dict(metadata or {})
    findings = _rollback_readiness_findings(
        post_verification, archive_path, stability_evidence, tuple(rollback_artifacts), tuple(rollback_execution_artifacts), policy, status,
        readiness_authority=readiness_authority, readiness_reference=readiness_reference, artifact_base_dir=artifact_base_dir,
    )
    payload = _rollback_identity_payload(
        post_verification, archive_artifact, stability_evidence, tuple(rollback_artifacts), tuple(rollback_execution_artifacts),
        policy, status, findings, readiness_authority=readiness_authority, readiness_reference=readiness_reference,
        rollback_execution_reference=rollback_execution_reference, metadata=values,
    )
    return StableRollbackReadinessVerification(
        _canonical_digest(payload), post_verification, archive_artifact, stability_evidence, tuple(rollback_artifacts),
        tuple(rollback_execution_artifacts), policy, status, findings, readiness_authority, readiness_reference,
        rollback_execution_reference, values,
    )


def stable_rollback_readiness_verification_from_dict(payload: Mapping[str, Any]) -> StableRollbackReadinessVerification:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported rollback readiness verification schema {payload.get("schema_version")!r}')
    post_payload = payload.get('post_verification'); archive_payload = payload.get('post_promotion_archive'); stability_payload = payload.get('stability_evidence')
    if not isinstance(post_payload, Mapping) or not isinstance(archive_payload, Mapping) or not isinstance(stability_payload, Mapping):
        raise TypeError('rollback readiness requires post_verification, post_promotion_archive and stability_evidence objects')
    post = stable_post_promotion_verification_from_dict(post_payload)
    archive = _target_artifact_from_dict(archive_payload)
    stability = post_release_stability_evidence_from_dict(stability_payload)
    policy_payload = payload.get('policy') or {}
    policy = RollbackReadinessPolicy(
        str(policy_payload.get('key', 'stable')), str(policy_payload.get('target_version', '3.0.0')),
        tuple(str(item) for item in policy_payload.get('required_artifact_keys', ('rollback-plan-validation', 'rollback-artifact-integrity', 'rollback-rehearsal'))),
        bool(policy_payload.get('require_stable_post_release_evidence', True)),
    )
    findings = tuple(
        RollbackReadinessFinding(str(item['code']), RollbackReadinessStatus(str(item['status'])), str(item['message']), str(item.get('remediation', '')))
        for item in payload.get('findings', ()) if isinstance(item, Mapping)
    )
    obj = StableRollbackReadinessVerification(
        str(payload['readiness_id']), post, archive, stability,
        tuple(_target_artifact_from_dict(item) for item in payload.get('rollback_artifacts', ()) if isinstance(item, Mapping)),
        tuple(_target_artifact_from_dict(item) for item in payload.get('rollback_execution_artifacts', ()) if isinstance(item, Mapping)),
        policy, RollbackReadinessStatus(str(payload.get('requested_status', 'pending'))), findings,
        None if payload.get('readiness_authority') is None else str(payload.get('readiness_authority')),
        None if payload.get('readiness_reference') is None else str(payload.get('readiness_reference')),
        None if payload.get('rollback_execution_reference') is None else str(payload.get('rollback_execution_reference')),
        dict(payload.get('metadata') or {}), str(payload.get('generated_at') or _utc_now()),
    )
    expected = _canonical_digest(_rollback_identity_payload(
        obj.post_verification, obj.post_promotion_archive, obj.stability_evidence, obj.rollback_artifacts,
        obj.rollback_execution_artifacts, obj.policy, obj.requested_status, obj.findings,
        readiness_authority=obj.readiness_authority, readiness_reference=obj.readiness_reference,
        rollback_execution_reference=obj.rollback_execution_reference, metadata=obj.metadata,
    ))
    if obj.readiness_id != expected:
        raise ValueError('rollback readiness id does not match persisted content')
    if payload.get('status') is not None and str(payload['status']) != obj.status.value:
        raise ValueError('rollback readiness status does not match persisted content')
    return obj


def write_stable_rollback_readiness_verification(path: str | Path, verification: StableRollbackReadinessVerification) -> Path:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(verification.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_stable_rollback_readiness_verification(path: str | Path) -> StableRollbackReadinessVerification:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('rollback readiness JSON must contain an object')
    return stable_rollback_readiness_verification_from_dict(payload)


def load_stable_rollback_readiness_manifest(
    path: str | Path,
    post_verification: StablePostPromotionVerification,
    post_promotion_archive_path: str | Path,
    stability_evidence: PostReleaseStabilityEvidence,
    *,
    artifact_base_dir: str | Path | None = None,
    policy: RollbackReadinessPolicy = ROLLBACK_READINESS_POLICY,
) -> StableRollbackReadinessVerification:
    manifest = Path(path)
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('rollback readiness manifest must contain an object')
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported rollback readiness manifest schema {payload.get("schema_version")!r}')
    expected_values = {
        'post_verification_id': post_verification.verification_id,
        'stability_id': stability_evidence.stability_id,
        'target_version': post_verification.policy.target_version,
    }
    for key, expected in expected_values.items():
        supplied = payload.get(key)
        if supplied is not None and str(supplied) != expected:
            raise ValueError(f'rollback readiness manifest {key} does not match supplied Wave 71/stability evidence')
    base = Path(artifact_base_dir) if artifact_base_dir is not None else manifest.parent

    def load_artifacts(items, label: str) -> tuple[TargetEvidenceArtifact, ...]:
        values: list[TargetEvidenceArtifact] = []
        for item in items:
            if not isinstance(item, Mapping) or not str(item.get('key', '')).strip() or not str(item.get('path', '')).strip():
                raise ValueError(f'rollback readiness {label} require non-empty key/path')
            source = _safe_manifest_artifact_path(base, str(item['path']))
            if not source.is_file():
                raise FileNotFoundError(source)
            values.append(capture_target_evidence_artifact(source, key=str(item['key']), description=str(item.get('description', ''))))
        return tuple(values)

    rollback_artifacts = load_artifacts(payload.get('artifacts', ()), 'artifacts')
    execution_artifacts = load_artifacts(payload.get('rollback_execution_artifacts', ()), 'rollback_execution_artifacts')
    return build_stable_rollback_readiness_verification(
        post_verification, post_promotion_archive_path, stability_evidence, rollback_artifacts=rollback_artifacts,
        rollback_execution_artifacts=execution_artifacts, requested_status=str(payload.get('status', 'pending')),
        readiness_authority=None if payload.get('readiness_authority') is None else str(payload.get('readiness_authority')),
        readiness_reference=None if payload.get('readiness_reference') is None else str(payload.get('readiness_reference')),
        rollback_execution_reference=None if payload.get('rollback_execution_reference') is None else str(payload.get('rollback_execution_reference')),
        policy=policy, artifact_base_dir=artifact_base_dir, metadata=dict(payload.get('metadata') or {}),
    )


@dataclass(frozen=True, slots=True)
class StableRollbackReadinessPackage:
    path: str
    sha256: str
    readiness_id: str
    status: RollbackReadinessStatus
    entries: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or len(self.readiness_id) != 64:
            raise ValueError('rollback readiness package requires sha256 package/readiness identifiers')
        object.__setattr__(self, 'status', RollbackReadinessStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))

    def to_dict(self) -> dict[str, Any]:
        return {'path': self.path, 'sha256': self.sha256, 'readiness_id': self.readiness_id, 'status': self.status.value, 'entries': self.entries}


def package_stable_rollback_readiness_verification(
    path: str | Path,
    verification: StableRollbackReadinessVerification,
    *,
    artifact_base_dir: str | Path | None = None,
) -> StableRollbackReadinessPackage:
    archive_path = _resolve_artifact_path(verification.post_promotion_archive, artifact_base_dir)
    refreshed = build_stable_rollback_readiness_verification(
        verification.post_verification, archive_path, verification.stability_evidence,
        rollback_artifacts=verification.rollback_artifacts, rollback_execution_artifacts=verification.rollback_execution_artifacts,
        requested_status=verification.requested_status, readiness_authority=verification.readiness_authority,
        readiness_reference=verification.readiness_reference, rollback_execution_reference=verification.rollback_execution_reference,
        policy=verification.policy, artifact_base_dir=artifact_base_dir, metadata=verification.metadata,
    )
    if refreshed.status is RollbackReadinessStatus.BLOCKED:
        raise ValueError('rollback readiness package cannot be created from BLOCKED or changed evidence')
    if refreshed.readiness_id != verification.readiness_id:
        raise ValueError('rollback readiness identity changed during package verification')
    entries: dict[str, bytes] = {
        'rollback-readiness-verification.json': _json_bytes(refreshed.to_dict()),
        'post-release-stability-evidence.json': _json_bytes(refreshed.stability_evidence.to_dict()),
        'post-promotion/post-promotion-verification.zip': archive_path.read_bytes(),
    }
    groups = (
        ('stability-evidence', refreshed.stability_evidence.artifacts),
        ('rollback-readiness-evidence', refreshed.rollback_artifacts),
        ('rollback-execution-evidence', refreshed.rollback_execution_artifacts),
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
                raise ValueError(f'unsafe rollback-readiness archive entry {name!r}')
            archive.writestr(_zip_info(name), entries[name])
    return StableRollbackReadinessPackage(str(target), hashlib.sha256(target.read_bytes()).hexdigest(), verification.readiness_id, verification.status, tuple(sorted(entries)))


__all__ = [
    'JsonPostReleaseStabilityEvidenceAdapter','POST_RELEASE_STABILITY_EVIDENCE_ADAPTERS','POST_RELEASE_STABILITY_POLICIES','POST_RELEASE_STABILITY_POLICY',
    'PostReleaseStabilityEvidence','PostReleaseStabilityEvidenceAdapter','PostReleaseStabilityFinding','PostReleaseStabilityPolicy',
    'PostReleaseStabilityStatus','PostReleaseStabilityVerification','ROLLBACK_READINESS_POLICIES','ROLLBACK_READINESS_POLICY',
    'RollbackReadinessFinding','RollbackReadinessPolicy','RollbackReadinessStatus','StablePostPromotionArchiveFinding',
    'StablePostPromotionArchiveStatus','StablePostPromotionArchiveVerification','StableRollbackReadinessPackage',
    'StableRollbackReadinessVerification','build_post_release_stability_evidence','build_stable_rollback_readiness_verification',
    'load_post_release_stability_manifest','load_stable_rollback_readiness_manifest','package_stable_rollback_readiness_verification',
    'post_release_stability_evidence_from_dict','read_post_release_stability_evidence','read_stable_rollback_readiness_verification',
    'stable_rollback_readiness_verification_from_dict','verify_post_release_stability_evidence','verify_stable_post_promotion_archive',
    'write_post_release_stability_evidence','write_stable_rollback_readiness_verification',
]
