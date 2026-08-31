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
from .semiconductor_execution import (
    PromotionHandoffStatus,
    PromotionOperationRecord,
    PromotionOperationStatus,
    StablePromotionOperationalHandoff,
    promotion_operation_record_from_dict,
    promotion_operational_handoff_from_dict,
    verify_promotion_operation_record,
    verify_stable_promotion_candidate_archive,
)
from .semiconductor_promotion import PromotionRehearsalKind


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


def _safe_manifest_artifact_path(base: Path, value: str) -> Path:
    raw = Path(value)
    candidate = raw.resolve() if raw.is_absolute() else (base / raw).resolve()
    root = base.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f'execution adapter artifact path escapes qualification base directory: {value!r}') from exc
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


class PromotionExecutionAdapterQualificationStatus(str, Enum):
    QUALIFIED = 'qualified'
    PENDING = 'pending'
    BLOCKED = 'blocked'


class ReleaseAuditStatus(str, Enum):
    CLOSED = 'closed'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class PromotionExecutionAdapterFinding:
    code: str
    status: PromotionExecutionAdapterQualificationStatus
    message: str
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('execution adapter finding code and message must not be empty')
        object.__setattr__(self, 'status', PromotionExecutionAdapterQualificationStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {
            'code': self.code,
            'status': self.status.value,
            'message': self.message,
            'remediation': self.remediation,
        }


@dataclass(frozen=True, slots=True)
class PromotionExecutionAdapterQualification:
    qualification_id: str
    adapter_key: str
    adapter_version: str
    requested_status: PromotionExecutionAdapterQualificationStatus
    supported_operations: tuple[PromotionRehearsalKind, ...]
    artifacts: tuple[TargetEvidenceArtifact, ...]
    framework_version: str = FRAMEWORK_VERSION
    nicegui_required: str = NICEGUI_VERSION
    observed_framework_version: str | None = None
    observed_nicegui_version: str | None = None
    qualification_authority: str | None = None
    approval_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    captured_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.qualification_id) != 64 or not self.adapter_key.strip() or not self.adapter_version.strip():
            raise ValueError('execution adapter qualification requires sha256 id, adapter key and adapter version')
        object.__setattr__(self, 'requested_status', PromotionExecutionAdapterQualificationStatus(self.requested_status))
        operations = tuple(PromotionRehearsalKind(item) for item in self.supported_operations)
        if len(operations) != len(set(operations)):
            raise ValueError('execution adapter qualification contains duplicate supported operations')
        artifacts = tuple(self.artifacts)
        if len({item.key for item in artifacts}) != len(artifacts):
            raise ValueError('execution adapter qualification contains duplicate artifact keys')
        object.__setattr__(self, 'supported_operations', operations)
        object.__setattr__(self, 'artifacts', artifacts)
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1,
            'qualification_id': self.qualification_id,
            'adapter_key': self.adapter_key,
            'adapter_version': self.adapter_version,
            'requested_status': self.requested_status.value,
            'supported_operations': tuple(item.value for item in self.supported_operations),
            'artifacts': [item.to_dict() for item in self.artifacts],
            'framework_version': self.framework_version,
            'nicegui_required': self.nicegui_required,
            'observed_framework_version': self.observed_framework_version,
            'observed_nicegui_version': self.observed_nicegui_version,
            'qualification_authority': self.qualification_authority,
            'approval_reference': self.approval_reference,
            'metadata': dict(self.metadata),
            'captured_at': self.captured_at,
            'approval_reference_is_metadata_only': True,
        }


@dataclass(frozen=True, slots=True)
class PromotionExecutionAdapterQualificationVerification:
    qualification_id: str
    status: PromotionExecutionAdapterQualificationStatus
    findings: tuple[PromotionExecutionAdapterFinding, ...] = ()

    def __post_init__(self) -> None:
        if len(self.qualification_id) != 64:
            raise ValueError('execution adapter qualification verification requires sha256 id')
        object.__setattr__(self, 'status', PromotionExecutionAdapterQualificationStatus(self.status))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def qualified(self) -> bool:
        return self.status is PromotionExecutionAdapterQualificationStatus.QUALIFIED

    @property
    def blocked(self) -> bool:
        return self.status is PromotionExecutionAdapterQualificationStatus.BLOCKED

    def to_dict(self) -> dict[str, Any]:
        return {
            'qualification_id': self.qualification_id,
            'status': self.status.value,
            'qualified': self.qualified,
            'findings': [item.to_dict() for item in self.findings],
        }


def _qualification_identity_payload(
    adapter_key: str,
    adapter_version: str,
    requested_status: PromotionExecutionAdapterQualificationStatus,
    supported_operations: Sequence[PromotionRehearsalKind],
    artifacts: Sequence[TargetEvidenceArtifact],
    *,
    framework_version: str,
    nicegui_required: str,
    observed_framework_version: str | None,
    observed_nicegui_version: str | None,
    qualification_authority: str | None,
    approval_reference: str | None,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'adapter_key': adapter_key,
        'adapter_version': adapter_version,
        'requested_status': requested_status.value,
        'supported_operations': tuple(sorted(item.value for item in supported_operations)),
        'artifacts': [item.to_dict() for item in sorted(artifacts, key=lambda item: item.key)],
        'framework_version': framework_version,
        'nicegui_required': nicegui_required,
        'observed_framework_version': observed_framework_version,
        'observed_nicegui_version': observed_nicegui_version,
        'qualification_authority': qualification_authority,
        'approval_reference': approval_reference,
        'metadata': dict(metadata),
    }


def build_promotion_execution_adapter_qualification(
    adapter_key: str,
    adapter_version: str,
    *,
    requested_status: PromotionExecutionAdapterQualificationStatus | str = PromotionExecutionAdapterQualificationStatus.PENDING,
    supported_operations: Sequence[PromotionRehearsalKind | str] = (),
    artifacts: Sequence[TargetEvidenceArtifact] = (),
    observed_framework_version: str | None = None,
    observed_nicegui_version: str | None = None,
    qualification_authority: str | None = None,
    approval_reference: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> PromotionExecutionAdapterQualification:
    status = PromotionExecutionAdapterQualificationStatus(requested_status)
    operations = tuple(PromotionRehearsalKind(item) for item in supported_operations)
    artifact_values = tuple(artifacts)
    values = dict(metadata or {})
    payload = _qualification_identity_payload(
        adapter_key, adapter_version, status, operations, artifact_values,
        framework_version=FRAMEWORK_VERSION, nicegui_required=NICEGUI_VERSION,
        observed_framework_version=observed_framework_version,
        observed_nicegui_version=observed_nicegui_version,
        qualification_authority=qualification_authority, approval_reference=approval_reference, metadata=values,
    )
    return PromotionExecutionAdapterQualification(
        _canonical_digest(payload), adapter_key, adapter_version, status, operations, artifact_values,
        FRAMEWORK_VERSION, NICEGUI_VERSION, observed_framework_version, observed_nicegui_version,
        qualification_authority, approval_reference, values,
    )


def promotion_execution_adapter_qualification_from_dict(payload: Mapping[str, Any]) -> PromotionExecutionAdapterQualification:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported execution adapter qualification schema {payload.get("schema_version")!r}')
    artifacts_payload = payload.get('artifacts', ())
    if not isinstance(artifacts_payload, list):
        raise TypeError('execution adapter qualification artifacts must be a list')
    artifacts = tuple(
        TargetEvidenceArtifact(
            str(item['key']), str(item['path']), str(item['sha256']), int(item['size_bytes']), str(item.get('description', '')),
        )
        for item in artifacts_payload
        if isinstance(item, Mapping)
    )
    qualification = PromotionExecutionAdapterQualification(
        str(payload['qualification_id']), str(payload['adapter_key']), str(payload['adapter_version']),
        PromotionExecutionAdapterQualificationStatus(str(payload.get('requested_status', 'pending'))),
        tuple(PromotionRehearsalKind(str(item)) for item in payload.get('supported_operations', ())), artifacts,
        str(payload.get('framework_version', FRAMEWORK_VERSION)), str(payload.get('nicegui_required', NICEGUI_VERSION)),
        None if payload.get('observed_framework_version') is None else str(payload.get('observed_framework_version')),
        None if payload.get('observed_nicegui_version') is None else str(payload.get('observed_nicegui_version')),
        None if payload.get('qualification_authority') is None else str(payload.get('qualification_authority')),
        None if payload.get('approval_reference') is None else str(payload.get('approval_reference')),
        dict(payload.get('metadata') or {}), str(payload.get('captured_at') or _utc_now()),
    )
    expected = _canonical_digest(_qualification_identity_payload(
        qualification.adapter_key, qualification.adapter_version, qualification.requested_status,
        qualification.supported_operations, qualification.artifacts,
        framework_version=qualification.framework_version, nicegui_required=qualification.nicegui_required,
        observed_framework_version=qualification.observed_framework_version,
        observed_nicegui_version=qualification.observed_nicegui_version,
        qualification_authority=qualification.qualification_authority,
        approval_reference=qualification.approval_reference, metadata=qualification.metadata,
    ))
    if expected != qualification.qualification_id:
        raise ValueError('execution adapter qualification id does not match persisted content')
    return qualification


def write_promotion_execution_adapter_qualification(path: str | Path, qualification: PromotionExecutionAdapterQualification) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(qualification.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_promotion_execution_adapter_qualification(path: str | Path) -> PromotionExecutionAdapterQualification:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('execution adapter qualification JSON must contain an object')
    return promotion_execution_adapter_qualification_from_dict(payload)


def load_promotion_execution_adapter_qualification_manifest(
    path: str | Path, *, artifact_base_dir: str | Path | None = None,
) -> PromotionExecutionAdapterQualification:
    source = Path(path)
    payload = json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('execution adapter qualification manifest must contain an object')
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported execution adapter qualification manifest schema {payload.get("schema_version")!r}')
    base = Path(artifact_base_dir) if artifact_base_dir is not None else source.parent
    artifacts: list[TargetEvidenceArtifact] = []
    for raw in payload.get('artifacts', ()):
        if not isinstance(raw, Mapping) or not str(raw.get('path', '')).strip():
            raise TypeError('execution adapter qualification artifact entries require path')
        artifact_path = _safe_manifest_artifact_path(base, str(raw['path']))
        key = str(raw.get('key') or artifact_path.stem or 'qualification-artifact')
        expected_sha = None if raw.get('sha256') is None else str(raw.get('sha256'))
        if artifact_path.is_file():
            artifact = capture_target_evidence_artifact(
                artifact_path, key=key, description=str(raw.get('description', 'Execution adapter qualification evidence')),
            )
            if expected_sha is not None and artifact.sha256 != expected_sha:
                artifact = TargetEvidenceArtifact(artifact.key, artifact.path, expected_sha, artifact.size_bytes, artifact.description)
            artifacts.append(artifact)
        else:
            artifacts.append(TargetEvidenceArtifact(key, str(artifact_path), expected_sha or ('0' * 64), int(raw.get('size_bytes', 0)), str(raw.get('description', ''))))
    return build_promotion_execution_adapter_qualification(
        str(payload['adapter_key']), str(payload['adapter_version']),
        requested_status=str(payload.get('status', 'pending')),
        supported_operations=tuple(str(item) for item in payload.get('supported_operations', ())),
        artifacts=tuple(artifacts),
        observed_framework_version=None if payload.get('framework_version') is None else str(payload.get('framework_version')),
        observed_nicegui_version=None if payload.get('nicegui_version') is None else str(payload.get('nicegui_version')),
        qualification_authority=None if payload.get('qualification_authority') is None else str(payload.get('qualification_authority')),
        approval_reference=None if payload.get('approval_reference') is None else str(payload.get('approval_reference')),
        metadata=dict(payload.get('metadata') or {}),
    )


def verify_promotion_execution_adapter_qualification(
    qualification: PromotionExecutionAdapterQualification,
    *,
    base_dir: str | Path | None = None,
    required_operations: Sequence[PromotionRehearsalKind | str] = tuple(PromotionRehearsalKind),
) -> PromotionExecutionAdapterQualificationVerification:
    findings: list[PromotionExecutionAdapterFinding] = []
    required = {PromotionRehearsalKind(item) for item in required_operations}
    supported = set(qualification.supported_operations)

    if qualification.requested_status is PromotionExecutionAdapterQualificationStatus.BLOCKED:
        findings.append(PromotionExecutionAdapterFinding(
            'external_qualification_failed', PromotionExecutionAdapterQualificationStatus.BLOCKED,
            'The external execution-adapter qualification explicitly reported failure.',
            'Resolve the external adapter qualification failure and capture a new qualification artifact set.',
        ))
    elif qualification.requested_status is PromotionExecutionAdapterQualificationStatus.PENDING:
        findings.append(PromotionExecutionAdapterFinding(
            'external_qualification_pending', PromotionExecutionAdapterQualificationStatus.PENDING,
            'The external execution-adapter qualification has not reported PASS.',
            'Complete the approved external qualification process and import its current artifact-backed result.',
        ))

    if qualification.framework_version != FRAMEWORK_VERSION:
        findings.append(PromotionExecutionAdapterFinding(
            'framework_requirement_mismatch', PromotionExecutionAdapterQualificationStatus.BLOCKED,
            f'Qualification requirement identity does not match current framework {FRAMEWORK_VERSION}.',
            'Rebuild the qualification record from the current framework release authority.',
        ))
    elif qualification.observed_framework_version is None:
        findings.append(PromotionExecutionAdapterFinding(
            'framework_identity_missing', PromotionExecutionAdapterQualificationStatus.PENDING,
            'Execution-adapter qualification has no observed current framework identity.',
            'Capture the exact current NiceGUI Base framework version in the approved qualification evidence.',
        ))
    elif qualification.observed_framework_version != FRAMEWORK_VERSION:
        findings.append(PromotionExecutionAdapterFinding(
            'framework_identity_mismatch', PromotionExecutionAdapterQualificationStatus.BLOCKED,
            f'Execution-adapter qualification must bind framework {FRAMEWORK_VERSION}; observed {qualification.observed_framework_version!r}.',
            'Re-run qualification against the exact current NiceGUI Base framework source.',
        ))
    if qualification.nicegui_required != NICEGUI_VERSION:
        findings.append(PromotionExecutionAdapterFinding(
            'nicegui_requirement_mismatch', PromotionExecutionAdapterQualificationStatus.BLOCKED,
            f'Qualification requirement identity does not match exact NiceGUI {NICEGUI_VERSION}.',
            f'Rebuild the qualification record for exact nicegui=={NICEGUI_VERSION}.',
        ))
    elif qualification.observed_nicegui_version is None:
        findings.append(PromotionExecutionAdapterFinding(
            'nicegui_identity_missing', PromotionExecutionAdapterQualificationStatus.PENDING,
            'Execution-adapter qualification has no observed NiceGUI runtime identity.',
            f'Capture exact nicegui=={NICEGUI_VERSION} identity in the approved qualification evidence.',
        ))
    elif qualification.observed_nicegui_version != NICEGUI_VERSION:
        findings.append(PromotionExecutionAdapterFinding(
            'nicegui_identity_mismatch', PromotionExecutionAdapterQualificationStatus.BLOCKED,
            f'Execution-adapter qualification must bind exact NiceGUI {NICEGUI_VERSION}; observed {qualification.observed_nicegui_version!r}.',
            f'Re-run qualification against exact nicegui=={NICEGUI_VERSION}.',
        ))

    missing_operations = tuple(sorted(item.value for item in required - supported))
    if missing_operations:
        findings.append(PromotionExecutionAdapterFinding(
            'required_operations_missing', PromotionExecutionAdapterQualificationStatus.PENDING,
            'Execution adapter does not declare every required operational capability: ' + ', '.join(missing_operations),
            'Qualify the adapter for all required promotion, rollback, incident and evidence-capture operations.',
        ))

    if qualification.requested_status is PromotionExecutionAdapterQualificationStatus.QUALIFIED and not qualification.artifacts:
        findings.append(PromotionExecutionAdapterFinding(
            'qualification_artifacts_missing', PromotionExecutionAdapterQualificationStatus.PENDING,
            'A requested adapter PASS has no traceable qualification artifact bytes.',
            'Attach current external qualification artifacts; an untraced PASS cannot be accepted.',
        ))

    for artifact in qualification.artifacts:
        path = _resolve_artifact_path(artifact, base_dir)
        if not path.is_file():
            status = PromotionExecutionAdapterQualificationStatus.PENDING
            findings.append(PromotionExecutionAdapterFinding(
                'qualification_artifact_unavailable', status,
                f'Execution-adapter qualification artifact is unavailable: {artifact.key}.',
                'Restore the exact captured artifact or produce a new qualification set.',
            ))
            continue
        data = path.read_bytes()
        if len(data) != artifact.size_bytes or hashlib.sha256(data).hexdigest() != artifact.sha256:
            findings.append(PromotionExecutionAdapterFinding(
                'qualification_artifact_hash_mismatch', PromotionExecutionAdapterQualificationStatus.BLOCKED,
                f'Execution-adapter qualification artifact changed after capture: {artifact.key}.',
                'Reject the changed evidence and re-run the approved qualification process.',
            ))

    if any(item.status is PromotionExecutionAdapterQualificationStatus.BLOCKED for item in findings):
        status = PromotionExecutionAdapterQualificationStatus.BLOCKED
    elif findings or qualification.requested_status is not PromotionExecutionAdapterQualificationStatus.QUALIFIED:
        status = PromotionExecutionAdapterQualificationStatus.PENDING
    else:
        status = PromotionExecutionAdapterQualificationStatus.QUALIFIED
    return PromotionExecutionAdapterQualificationVerification(qualification.qualification_id, status, tuple(findings))


@runtime_checkable
class PromotionExecutionAdapterQualificationAdapter(Protocol):
    key: str

    def load(self, manifest_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> PromotionExecutionAdapterQualification: ...


@dataclass(frozen=True, slots=True)
class JsonPromotionExecutionAdapterQualificationAdapter:
    key: str = 'json-manifest'

    def load(self, manifest_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> PromotionExecutionAdapterQualification:
        return load_promotion_execution_adapter_qualification_manifest(manifest_path, artifact_base_dir=artifact_base_dir)


PROMOTION_EXECUTION_ADAPTER_QUALIFICATION_ADAPTERS: Mapping[str, PromotionExecutionAdapterQualificationAdapter] = MappingProxyType({
    'json-manifest': JsonPromotionExecutionAdapterQualificationAdapter(),
})


@dataclass(frozen=True, slots=True)
class ReleaseAuditPolicy:
    key: str = 'stable'
    require_ready_handoff: bool = True
    require_qualified_execution_adapter: bool = True
    require_all_candidate_recipes: bool = True
    required_operation_kinds: tuple[PromotionRehearsalKind, ...] = (PromotionRehearsalKind.PROMOTION,)

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError('release audit policy key must not be empty')
        kinds = tuple(PromotionRehearsalKind(item) for item in self.required_operation_kinds)
        if len(kinds) != len(set(kinds)):
            raise ValueError('release audit policy contains duplicate required operation kinds')
        object.__setattr__(self, 'required_operation_kinds', kinds)

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key,
            'require_ready_handoff': self.require_ready_handoff,
            'require_qualified_execution_adapter': self.require_qualified_execution_adapter,
            'require_all_candidate_recipes': self.require_all_candidate_recipes,
            'required_operation_kinds': tuple(item.value for item in self.required_operation_kinds),
        }


STABLE_RELEASE_AUDIT_POLICY = ReleaseAuditPolicy()
RELEASE_AUDIT_POLICIES: Mapping[str, ReleaseAuditPolicy] = MappingProxyType({'stable': STABLE_RELEASE_AUDIT_POLICY})


@dataclass(frozen=True, slots=True)
class ReleaseAuditFinding:
    code: str
    status: ReleaseAuditStatus
    message: str
    remediation: str = ''
    recipe_key: str | None = None
    operation_kind: PromotionRehearsalKind | None = None

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('release audit finding code and message must not be empty')
        object.__setattr__(self, 'status', ReleaseAuditStatus(self.status))
        if self.operation_kind is not None:
            object.__setattr__(self, 'operation_kind', PromotionRehearsalKind(self.operation_kind))

    def to_dict(self) -> dict[str, Any]:
        return {
            'code': self.code,
            'status': self.status.value,
            'message': self.message,
            'remediation': self.remediation,
            'recipe_key': self.recipe_key,
            'operation_kind': None if self.operation_kind is None else self.operation_kind.value,
        }


@dataclass(frozen=True, slots=True)
class ReleaseAuditClosure:
    audit_id: str
    handoff: StablePromotionOperationalHandoff
    execution_adapter_qualification: PromotionExecutionAdapterQualification
    operation_records: tuple[PromotionOperationRecord, ...]
    policy: ReleaseAuditPolicy = STABLE_RELEASE_AUDIT_POLICY
    findings: tuple[ReleaseAuditFinding, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.audit_id) != 64:
            raise ValueError('release audit closure requires sha256 id')
        records = tuple(self.operation_records)
        object.__setattr__(self, 'operation_records', records)
        object.__setattr__(self, 'findings', tuple(self.findings))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def status(self) -> ReleaseAuditStatus:
        if any(item.status is ReleaseAuditStatus.BLOCKED for item in self.findings):
            return ReleaseAuditStatus.BLOCKED
        if any(item.status is ReleaseAuditStatus.PENDING for item in self.findings):
            return ReleaseAuditStatus.PENDING
        return ReleaseAuditStatus.CLOSED

    @property
    def closed(self) -> bool:
        return self.status is ReleaseAuditStatus.CLOSED

    @property
    def next_actions(self) -> tuple[str, ...]:
        actions = tuple(dict.fromkeys(item.remediation for item in self.findings if item.remediation.strip()))
        if actions:
            return actions
        return ('Retain the immutable audit package with the approved external release record; no framework status is mutated.',)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1,
            'audit_id': self.audit_id,
            'status': self.status.value,
            'closed': self.closed,
            'handoff': self.handoff.to_dict(),
            'execution_adapter_qualification': self.execution_adapter_qualification.to_dict(),
            'operation_records': [item.to_dict() for item in self.operation_records],
            'policy': self.policy.to_dict(),
            'findings': [item.to_dict() for item in self.findings],
            'metadata': dict(self.metadata),
            'generated_at': self.generated_at,
            'next_actions': self.next_actions,
            'affects_candidate_status': False,
            'affects_target_gate_status': False,
            'deployment_performed_by_framework': False,
            'audit_closure_is_not_promotion_approval': True,
        }


def _audit_identity_payload(
    handoff: StablePromotionOperationalHandoff,
    qualification: PromotionExecutionAdapterQualification,
    operation_records: Sequence[PromotionOperationRecord],
    policy: ReleaseAuditPolicy,
    findings: Sequence[ReleaseAuditFinding],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'handoff_id': handoff.handoff_id,
        'candidate_archive_sha256': handoff.candidate_archive.sha256,
        'execution_adapter_qualification_id': qualification.qualification_id,
        'operation_ids': tuple(sorted(item.operation_id for item in operation_records)),
        'policy': policy.to_dict(),
        'findings': [item.to_dict() for item in findings],
        'metadata': dict(metadata),
    }


def _release_audit_findings(
    handoff: StablePromotionOperationalHandoff,
    qualification: PromotionExecutionAdapterQualification,
    operation_records: Sequence[PromotionOperationRecord],
    policy: ReleaseAuditPolicy,
    *,
    artifact_base_dir: str | Path | None = None,
) -> tuple[ReleaseAuditFinding, ...]:
    findings: list[ReleaseAuditFinding] = []

    archive = verify_stable_promotion_candidate_archive(handoff.candidate_archive.path, expected_candidate=handoff.candidate)
    if not archive.verified or archive.sha256 != handoff.candidate_archive.sha256:
        findings.append(ReleaseAuditFinding(
            'candidate_archive_reverification_failed', ReleaseAuditStatus.BLOCKED,
            'The operational handoff candidate archive no longer independently verifies against the bound candidate bytes.',
            'Restore the exact verified candidate archive and rebuild the operational handoff/audit.',
        ))
    if policy.require_ready_handoff:
        if handoff.status is PromotionHandoffStatus.BLOCKED:
            findings.append(ReleaseAuditFinding(
                'handoff_blocked', ReleaseAuditStatus.BLOCKED,
                'The stable-promotion operational handoff is BLOCKED.',
                'Resolve the handoff/candidate archive failure before release audit closure.',
            ))
        elif handoff.status is not PromotionHandoffStatus.READY:
            findings.append(ReleaseAuditFinding(
                'handoff_not_ready', ReleaseAuditStatus.PENDING,
                'The stable-promotion operational handoff is not READY.',
                'Complete the canonical stable-promotion candidate and handoff requirements first.',
            ))

    qualification_verification = verify_promotion_execution_adapter_qualification(
        qualification, base_dir=artifact_base_dir,
    )
    if policy.require_qualified_execution_adapter:
        if qualification_verification.status is PromotionExecutionAdapterQualificationStatus.BLOCKED:
            findings.append(ReleaseAuditFinding(
                'execution_adapter_qualification_blocked', ReleaseAuditStatus.BLOCKED,
                'The external promotion execution adapter qualification is BLOCKED.',
                'Resolve the execution-adapter qualification failures and import a fresh qualification set.',
            ))
        elif qualification_verification.status is not PromotionExecutionAdapterQualificationStatus.QUALIFIED:
            findings.append(ReleaseAuditFinding(
                'execution_adapter_not_qualified', ReleaseAuditStatus.PENDING,
                'The external promotion execution adapter is not yet artifact-backed QUALIFIED.',
                'Complete the approved adapter qualification and import current traceable artifacts.',
            ))

    seen: dict[tuple[str, PromotionRehearsalKind], PromotionOperationRecord] = {}
    for record in operation_records:
        key = (record.recipe_key, record.kind)
        if key in seen:
            findings.append(ReleaseAuditFinding(
                'duplicate_operation_record', ReleaseAuditStatus.BLOCKED,
                f'Duplicate operation records create ambiguous audit truth for {record.recipe_key}/{record.kind.value}.',
                'Keep exactly one canonical record per recipe and operation kind.', record.recipe_key, record.kind,
            ))
            continue
        seen[key] = record
        if record.handoff_id != handoff.handoff_id:
            findings.append(ReleaseAuditFinding(
                'operation_handoff_mismatch', ReleaseAuditStatus.BLOCKED,
                f'Operation record {record.operation_id[:12]} is bound to a different handoff.',
                'Capture operation evidence against this exact handoff.', record.recipe_key, record.kind,
            ))
            continue
        verification = verify_promotion_operation_record(record, base_dir=artifact_base_dir)
        if verification.status is PromotionOperationStatus.BLOCKED:
            findings.append(ReleaseAuditFinding(
                'operation_record_blocked', ReleaseAuditStatus.BLOCKED,
                f'Operational evidence is BLOCKED for {record.recipe_key}/{record.kind.value}.',
                'Restore or recapture the exact operation evidence and rebuild the operation record.', record.recipe_key, record.kind,
            ))
        elif verification.status is not PromotionOperationStatus.PASS:
            findings.append(ReleaseAuditFinding(
                'operation_record_incomplete', ReleaseAuditStatus.PENDING,
                f'Operational evidence is incomplete for {record.recipe_key}/{record.kind.value}.',
                'Complete every required runbook step and evidence item for this operation.', record.recipe_key, record.kind,
            ))

    required_recipes = tuple(handoff.candidate.evidence.recipe_keys) if policy.require_all_candidate_recipes else ()
    for recipe_key in required_recipes:
        for kind in policy.required_operation_kinds:
            if (recipe_key, kind) not in seen:
                findings.append(ReleaseAuditFinding(
                    'required_operation_missing', ReleaseAuditStatus.PENDING,
                    f'Release audit is missing the required {kind.value} operation record for {recipe_key}.',
                    'Capture the approved external operation evidence against the canonical Wave 68 handoff.', recipe_key, kind,
                ))

    return tuple(findings)


def build_release_audit_closure(
    handoff: StablePromotionOperationalHandoff,
    execution_adapter_qualification: PromotionExecutionAdapterQualification,
    operation_records: Sequence[PromotionOperationRecord] = (),
    *,
    policy: ReleaseAuditPolicy = STABLE_RELEASE_AUDIT_POLICY,
    artifact_base_dir: str | Path | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ReleaseAuditClosure:
    records = tuple(operation_records)
    findings = _release_audit_findings(
        handoff, execution_adapter_qualification, records, policy, artifact_base_dir=artifact_base_dir,
    )
    values = dict(metadata or {})
    payload = _audit_identity_payload(handoff, execution_adapter_qualification, records, policy, findings, values)
    return ReleaseAuditClosure(
        _canonical_digest(payload), handoff, execution_adapter_qualification,
        tuple(sorted(records, key=lambda item: (item.recipe_key, item.kind.value, item.operation_id))), policy, findings, values,
    )


def release_audit_closure_from_dict(payload: Mapping[str, Any]) -> ReleaseAuditClosure:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported release audit closure schema {payload.get("schema_version")!r}')
    handoff_payload = payload.get('handoff')
    qualification_payload = payload.get('execution_adapter_qualification')
    records_payload = payload.get('operation_records', ())
    policy_payload = payload.get('policy') or {}
    if not isinstance(handoff_payload, Mapping) or not isinstance(qualification_payload, Mapping) or not isinstance(records_payload, list):
        raise TypeError('release audit closure requires handoff, execution_adapter_qualification and operation_records')
    handoff = promotion_operational_handoff_from_dict(handoff_payload)
    qualification = promotion_execution_adapter_qualification_from_dict(qualification_payload)
    records = tuple(promotion_operation_record_from_dict(item) for item in records_payload if isinstance(item, Mapping))
    policy = ReleaseAuditPolicy(
        str(policy_payload.get('key', 'stable')),
        bool(policy_payload.get('require_ready_handoff', True)),
        bool(policy_payload.get('require_qualified_execution_adapter', True)),
        bool(policy_payload.get('require_all_candidate_recipes', True)),
        tuple(PromotionRehearsalKind(str(item)) for item in policy_payload.get('required_operation_kinds', ('promotion',))),
    )
    findings = tuple(
        ReleaseAuditFinding(
            str(item['code']), ReleaseAuditStatus(str(item['status'])), str(item['message']), str(item.get('remediation', '')),
            None if item.get('recipe_key') is None else str(item.get('recipe_key')),
            None if item.get('operation_kind') is None else PromotionRehearsalKind(str(item.get('operation_kind'))),
        )
        for item in payload.get('findings', ()) if isinstance(item, Mapping)
    )
    closure = ReleaseAuditClosure(
        str(payload['audit_id']), handoff, qualification, records, policy, findings,
        dict(payload.get('metadata') or {}), str(payload.get('generated_at') or _utc_now()),
    )
    expected = _canonical_digest(_audit_identity_payload(handoff, qualification, records, policy, findings, closure.metadata))
    if closure.audit_id != expected:
        raise ValueError('release audit id does not match persisted content')
    if payload.get('status') is not None and str(payload.get('status')) != closure.status.value:
        raise ValueError('release audit status does not match persisted content')
    return closure


def write_release_audit_closure(path: str | Path, closure: ReleaseAuditClosure) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(closure.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_release_audit_closure(path: str | Path) -> ReleaseAuditClosure:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('release audit closure JSON must contain an object')
    return release_audit_closure_from_dict(payload)


@dataclass(frozen=True, slots=True)
class ReleaseAuditPackage:
    path: str
    sha256: str
    audit_id: str
    entries: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or len(self.audit_id) != 64:
            raise ValueError('release audit package requires sha256 values')
        object.__setattr__(self, 'entries', tuple(self.entries))

    def to_dict(self) -> dict[str, Any]:
        return {'path': self.path, 'sha256': self.sha256, 'audit_id': self.audit_id, 'entries': self.entries}


def package_release_audit_closure(
    path: str | Path,
    closure: ReleaseAuditClosure,
    *,
    artifact_base_dir: str | Path | None = None,
) -> ReleaseAuditPackage:
    refreshed = build_release_audit_closure(
        closure.handoff, closure.execution_adapter_qualification, closure.operation_records,
        policy=closure.policy, artifact_base_dir=artifact_base_dir, metadata=closure.metadata,
    )
    if refreshed.status is ReleaseAuditStatus.BLOCKED:
        raise ValueError('release audit package cannot be created from BLOCKED or changed evidence')
    if refreshed.audit_id != closure.audit_id:
        raise ValueError('release audit identity changed during package verification')

    entries: dict[str, bytes] = {
        'release-audit.json': _json_bytes(refreshed.to_dict()),
        'handoff.json': _json_bytes(refreshed.handoff.to_dict()),
        'execution-adapter-qualification.json': _json_bytes(refreshed.execution_adapter_qualification.to_dict()),
    }
    candidate_path = Path(refreshed.handoff.candidate_archive.path)
    candidate_bytes = candidate_path.read_bytes()
    if hashlib.sha256(candidate_bytes).hexdigest() != refreshed.handoff.candidate_archive.sha256:
        raise ValueError('bound candidate archive is unavailable or changed')
    entries['candidate/stable-promotion-candidate.zip'] = candidate_bytes

    for artifact in refreshed.execution_adapter_qualification.artifacts:
        source = _resolve_artifact_path(artifact, artifact_base_dir)
        if not source.is_file():
            continue
        data = source.read_bytes()
        if len(data) != artifact.size_bytes or hashlib.sha256(data).hexdigest() != artifact.sha256:
            raise ValueError(f'execution adapter qualification artifact changed: {artifact.key}')
        name = f'adapter-evidence/{_safe_entry_component(artifact.key)}/{_safe_entry_component(source.name)}'
        entries[name] = data

    for record in refreshed.operation_records:
        base = f'operations/{_safe_entry_component(record.recipe_key)}/{_safe_entry_component(record.kind.value)}'
        entries[f'{base}/record.json'] = _json_bytes(record.to_dict())
        for item in record.evidence:
            source = _resolve_artifact_path(item.artifact, artifact_base_dir)
            if not source.is_file():
                continue
            data = source.read_bytes()
            if len(data) != item.artifact.size_bytes or hashlib.sha256(data).hexdigest() != item.artifact.sha256:
                raise ValueError(f'operation evidence changed: {record.recipe_key}:{item.step_key}:{item.evidence_key}')
            name = (
                f'{base}/evidence/{_safe_entry_component(item.step_key)}/'
                f'{_safe_entry_component(item.evidence_key)}/{_safe_entry_component(source.name)}'
            )
            entries[name] = data

    manifest = ''.join(f'{hashlib.sha256(entries[name]).hexdigest()}  {name}\n' for name in sorted(entries))
    entries['MANIFEST.sha256'] = manifest.encode('utf-8')
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w') as archive:
        for name in sorted(entries):
            pure = PurePosixPath(name)
            if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
                raise ValueError(f'unsafe release audit archive entry {name!r}')
            archive.writestr(_zip_info(name), entries[name])
    return ReleaseAuditPackage(str(target), hashlib.sha256(target.read_bytes()).hexdigest(), closure.audit_id, tuple(sorted(entries)))


__all__ = [
    'JsonPromotionExecutionAdapterQualificationAdapter','PROMOTION_EXECUTION_ADAPTER_QUALIFICATION_ADAPTERS',
    'PromotionExecutionAdapterFinding','PromotionExecutionAdapterQualification','PromotionExecutionAdapterQualificationAdapter',
    'PromotionExecutionAdapterQualificationStatus','PromotionExecutionAdapterQualificationVerification',
    'RELEASE_AUDIT_POLICIES','ReleaseAuditClosure','ReleaseAuditFinding','ReleaseAuditPackage','ReleaseAuditPolicy','ReleaseAuditStatus',
    'STABLE_RELEASE_AUDIT_POLICY','build_promotion_execution_adapter_qualification','build_release_audit_closure',
    'load_promotion_execution_adapter_qualification_manifest','package_release_audit_closure',
    'promotion_execution_adapter_qualification_from_dict','read_promotion_execution_adapter_qualification','read_release_audit_closure',
    'release_audit_closure_from_dict','verify_promotion_execution_adapter_qualification',
    'write_promotion_execution_adapter_qualification','write_release_audit_closure',
]
