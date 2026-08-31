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

from nicegui_base.semiconductor.operational_readiness import SEMICONDUCTOR_OPERATIONAL_RUNBOOKS
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

from .semiconductor_evidence import (
    SemiconductorTargetEvidenceBundle,
    TargetEnvironmentFingerprint,
    TargetEvidenceArtifact,
    capture_target_evidence_artifact,
    read_semiconductor_target_evidence,
    target_evidence_bundle_from_dict,
    write_semiconductor_target_evidence,
)
from .semiconductor_promotion import (
    PromotionCandidateStatus,
    PromotionRehearsalKind,
    StablePromotionCandidate,
    build_promotion_rehearsal,
    promotion_candidate_from_dict,
    read_promotion_candidate,
)
from .semiconductor_runtime import SemiconductorTargetRuntimeCertification, TargetGateStatus, TargetRuntimeGate


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
    if raw.is_absolute():
        candidate = raw.resolve()
    else:
        candidate = (base / raw).resolve()
    root = base.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f'target execution artifact path escapes intake base directory: {value!r}') from exc
    return candidate


def _safe_zip_names(names: Sequence[str]) -> tuple[str, ...]:
    problems: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            problems.append(f'duplicate archive entry: {name}')
        seen.add(name)
        if not name or '\\' in name:
            problems.append(f'unsafe archive entry: {name!r}')
            continue
        pure = PurePosixPath(name)
        if pure.is_absolute() or any(part in {'', '.', '..'} for part in pure.parts):
            problems.append(f'unsafe archive entry: {name!r}')
    return tuple(dict.fromkeys(problems))


TARGET_EXECUTION_GATE_KEYS: tuple[str, ...] = (
    'installed_nicegui',
    'server_websocket',
    'supported_browser',
    'human_visual_baseline',
)


class TargetExecutionIntakeStatus(str, Enum):
    VERIFIED = 'verified'
    PENDING = 'pending'
    BLOCKED = 'blocked'


class PromotionHandoffStatus(str, Enum):
    READY = 'ready'
    PENDING = 'pending'
    BLOCKED = 'blocked'


class PromotionOperationStatus(str, Enum):
    PASS = 'pass'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class TargetExecutionObservation:
    gate_key: str
    status: TargetGateStatus
    evidence: str
    artifact: TargetEvidenceArtifact | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.gate_key not in TARGET_EXECUTION_GATE_KEYS:
            raise ValueError(f'unsupported target execution gate {self.gate_key!r}')
        object.__setattr__(self, 'status', TargetGateStatus(self.status))
        if not self.evidence.strip():
            raise ValueError('target execution observation evidence must not be empty')
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'gate_key': self.gate_key,
            'status': self.status.value,
            'evidence': self.evidence,
            'artifact': None if self.artifact is None else self.artifact.to_dict(),
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class TargetExecutionIntakeFinding:
    code: str
    status: TargetExecutionIntakeStatus
    message: str
    gate_key: str | None = None
    remediation: str = ''

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('target execution intake finding code and message must not be empty')
        object.__setattr__(self, 'status', TargetExecutionIntakeStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {
            'code': self.code,
            'status': self.status.value,
            'message': self.message,
            'gate_key': self.gate_key,
            'remediation': self.remediation,
        }


@dataclass(frozen=True, slots=True)
class TargetExecutionIntake:
    intake_id: str
    recipe_key: str
    provider: str
    source_key: str
    environment: TargetEnvironmentFingerprint
    observations: tuple[TargetExecutionObservation, ...]
    framework_version: str = FRAMEWORK_VERSION
    nicegui_required: str = NICEGUI_VERSION
    observed_framework_version: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    captured_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.intake_id) != 64 or not all(item.strip() for item in (self.recipe_key, self.provider, self.source_key)):
            raise ValueError('target execution intake requires sha256 id, recipe, provider and source')
        object.__setattr__(self, 'observations', tuple(self.observations))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))
        keys = [item.gate_key for item in self.observations]
        if len(keys) != len(set(keys)):
            raise ValueError('target execution intake contains duplicate gate observations')
        artifact_keys = [item.artifact.key for item in self.observations if item.artifact is not None]
        if len(artifact_keys) != len(set(artifact_keys)):
            raise ValueError('target execution intake contains duplicate artifact keys')

    @property
    def artifacts(self) -> tuple[TargetEvidenceArtifact, ...]:
        return tuple(item.artifact for item in self.observations if item.artifact is not None)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1,
            'intake_id': self.intake_id,
            'recipe_key': self.recipe_key,
            'provider': self.provider,
            'source_key': self.source_key,
            'framework_version': self.framework_version,
            'nicegui_required': self.nicegui_required,
            'observed_framework_version': self.observed_framework_version,
            'captured_at': self.captured_at,
            'environment': self.environment.to_dict(),
            'observations': [item.to_dict() for item in self.observations],
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class TargetExecutionIntakeVerification:
    intake_id: str
    status: TargetExecutionIntakeStatus
    findings: tuple[TargetExecutionIntakeFinding, ...] = ()

    def __post_init__(self) -> None:
        if len(self.intake_id) != 64:
            raise ValueError('target execution verification requires sha256 intake id')
        object.__setattr__(self, 'status', TargetExecutionIntakeStatus(self.status))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def verified(self) -> bool:
        return self.status is TargetExecutionIntakeStatus.VERIFIED

    @property
    def blocked(self) -> bool:
        return self.status is TargetExecutionIntakeStatus.BLOCKED

    def gate_status(self, gate_key: str) -> TargetExecutionIntakeStatus:
        related = tuple(item for item in self.findings if item.gate_key == gate_key)
        if any(item.status is TargetExecutionIntakeStatus.BLOCKED for item in related):
            return TargetExecutionIntakeStatus.BLOCKED
        if any(item.status is TargetExecutionIntakeStatus.PENDING for item in related):
            return TargetExecutionIntakeStatus.PENDING
        return TargetExecutionIntakeStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            'intake_id': self.intake_id,
            'status': self.status.value,
            'verified': self.verified,
            'findings': [item.to_dict() for item in self.findings],
        }


def _target_execution_intake_payload(
    recipe_key: str,
    provider: str,
    source_key: str,
    environment: TargetEnvironmentFingerprint,
    observations: Sequence[TargetExecutionObservation],
    *,
    framework_version: str,
    nicegui_required: str,
    observed_framework_version: str | None,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'recipe_key': recipe_key,
        'provider': provider,
        'source_key': source_key,
        'framework_version': framework_version,
        'nicegui_required': nicegui_required,
        'observed_framework_version': observed_framework_version,
        'environment': environment.to_dict(),
        'observations': [item.to_dict() for item in sorted(observations, key=lambda item: item.gate_key)],
        'metadata': dict(metadata),
    }


def build_target_execution_intake(
    recipe_key: str,
    *,
    provider: str,
    source_key: str,
    observations: Sequence[TargetExecutionObservation],
    environment: TargetEnvironmentFingerprint,
    observed_framework_version: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> TargetExecutionIntake:
    values = tuple(observations)
    payload = _target_execution_intake_payload(
        recipe_key,
        provider,
        source_key,
        environment,
        values,
        framework_version=FRAMEWORK_VERSION,
        nicegui_required=NICEGUI_VERSION,
        observed_framework_version=observed_framework_version,
        metadata=metadata or {},
    )
    return TargetExecutionIntake(
        _canonical_digest(payload),
        recipe_key,
        provider,
        source_key,
        environment,
        tuple(sorted(values, key=lambda item: item.gate_key)),
        FRAMEWORK_VERSION,
        NICEGUI_VERSION,
        observed_framework_version,
        metadata or {},
    )


def target_execution_intake_from_dict(payload: Mapping[str, Any]) -> TargetExecutionIntake:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported target execution intake schema {payload.get("schema_version")!r}')
    environment_payload = payload.get('environment')
    observations_payload = payload.get('observations')
    if not isinstance(environment_payload, Mapping) or not isinstance(observations_payload, list):
        raise TypeError('target execution intake requires environment object and observations list')
    environment = TargetEnvironmentFingerprint(
        str(environment_payload.get('python_version', '')),
        str(environment_payload.get('platform', '')),
        environment_payload.get('nicegui_version'),
        str(environment_payload.get('executable', '')),
        environment_payload.get('metadata', {}),
    )
    observations: list[TargetExecutionObservation] = []
    for item in observations_payload:
        if not isinstance(item, Mapping):
            raise TypeError('target execution observation must be an object')
        artifact_payload = item.get('artifact')
        artifact = None
        if artifact_payload is not None:
            if not isinstance(artifact_payload, Mapping):
                raise TypeError('target execution observation artifact must be an object')
            artifact = TargetEvidenceArtifact(
                str(artifact_payload['key']),
                str(artifact_payload['path']),
                str(artifact_payload['sha256']),
                int(artifact_payload['size_bytes']),
                str(artifact_payload.get('description', '')),
            )
        observations.append(TargetExecutionObservation(
            str(item['gate_key']),
            TargetGateStatus(str(item['status'])),
            str(item['evidence']),
            artifact,
            item.get('metadata', {}),
        ))
    intake = TargetExecutionIntake(
        str(payload['intake_id']),
        str(payload['recipe_key']),
        str(payload['provider']),
        str(payload['source_key']),
        environment,
        tuple(observations),
        str(payload.get('framework_version', '')),
        str(payload.get('nicegui_required', '')),
        None if payload.get('observed_framework_version') is None else str(payload.get('observed_framework_version')),
        payload.get('metadata', {}),
        str(payload.get('captured_at') or _utc_now()),
    )
    expected = _canonical_digest(_target_execution_intake_payload(
        intake.recipe_key,
        intake.provider,
        intake.source_key,
        intake.environment,
        intake.observations,
        framework_version=intake.framework_version,
        nicegui_required=intake.nicegui_required,
        observed_framework_version=intake.observed_framework_version,
        metadata=intake.metadata,
    ))
    if intake.intake_id != expected:
        raise ValueError('target execution intake id does not match persisted content')
    return intake


def write_target_execution_intake(path: str | Path, intake: TargetExecutionIntake) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(intake.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_target_execution_intake(path: str | Path) -> TargetExecutionIntake:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('target execution intake JSON must contain an object')
    return target_execution_intake_from_dict(payload)


def load_target_execution_intake_manifest(path: str | Path, *, artifact_base_dir: str | Path | None = None) -> TargetExecutionIntake:
    manifest = Path(path)
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('target execution intake manifest must contain an object')
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported target execution intake manifest schema {payload.get("schema_version")!r}')
    gates = payload.get('gates')
    environment_payload = payload.get('environment')
    if not isinstance(gates, list) or not isinstance(environment_payload, Mapping):
        raise TypeError('target execution intake manifest requires gates list and environment object')
    environment = TargetEnvironmentFingerprint(
        str(environment_payload.get('python_version', '')),
        str(environment_payload.get('platform', '')),
        environment_payload.get('nicegui_version'),
        str(environment_payload.get('executable', '')),
        environment_payload.get('metadata', {}),
    )
    base = Path(artifact_base_dir).resolve() if artifact_base_dir is not None else manifest.parent.resolve()
    observations: list[TargetExecutionObservation] = []
    for gate in gates:
        if not isinstance(gate, Mapping):
            raise TypeError('target execution intake gate must be an object')
        gate_key = str(gate['key'])
        status = TargetGateStatus(str(gate['status']))
        evidence = str(gate.get('evidence') or f'Target execution manifest reported {status.value}.')
        metadata = dict(gate.get('metadata', {}))
        artifact_spec = gate.get('artifact')
        artifact: TargetEvidenceArtifact | None = None
        if artifact_spec is not None:
            if isinstance(artifact_spec, str):
                artifact_path_value = artifact_spec
                artifact_key = gate_key
                description = f'{gate_key} target execution evidence'
                expected_sha = None
            elif isinstance(artifact_spec, Mapping):
                artifact_path_value = str(artifact_spec.get('path', ''))
                artifact_key = str(artifact_spec.get('key') or gate_key)
                description = str(artifact_spec.get('description') or f'{gate_key} target execution evidence')
                expected_sha = artifact_spec.get('sha256')
            else:
                raise TypeError('target execution intake artifact must be a path string or object')
            if not artifact_path_value:
                raise ValueError('target execution intake artifact path must not be empty')
            artifact_path = _safe_manifest_artifact_path(base, artifact_path_value)
            metadata['requested_artifact_path'] = artifact_path_value
            if expected_sha is not None:
                metadata['expected_sha256'] = str(expected_sha)
            if artifact_path.is_file():
                artifact = capture_target_evidence_artifact(artifact_path, key=artifact_key, description=description)
        observations.append(TargetExecutionObservation(gate_key, status, evidence, artifact, metadata))
    return build_target_execution_intake(
        str(payload['recipe_key']),
        provider=str(payload['provider']),
        source_key=str(payload['source_key']),
        observations=observations,
        environment=environment,
        observed_framework_version=None if payload.get('framework_version') is None else str(payload.get('framework_version')),
        metadata=payload.get('metadata', {}),
    )


def verify_target_execution_intake(
    intake: TargetExecutionIntake, *, base_dir: str | Path | None = None,
) -> TargetExecutionIntakeVerification:
    findings: list[TargetExecutionIntakeFinding] = []
    if intake.framework_version != FRAMEWORK_VERSION or intake.nicegui_required != NICEGUI_VERSION:
        findings.append(TargetExecutionIntakeFinding(
            'release_identity_mismatch', TargetExecutionIntakeStatus.BLOCKED,
            'Persisted intake release identity does not match the current NiceGUI Base release authority.',
            remediation='Regenerate the intake with the current framework and exact required NiceGUI runtime.',
        ))
    if intake.observed_framework_version is None:
        if any(item.status is TargetGateStatus.PASS for item in intake.observations):
            findings.append(TargetExecutionIntakeFinding(
                'framework_identity_missing', TargetExecutionIntakeStatus.PENDING,
                'Target execution PASS observations do not identify the framework version actually executed.',
                remediation='Capture the target framework version in the execution manifest.',
            ))
    elif intake.observed_framework_version != FRAMEWORK_VERSION:
        findings.append(TargetExecutionIntakeFinding(
            'framework_identity_mismatch', TargetExecutionIntakeStatus.BLOCKED,
            f'Target execution observed framework {intake.observed_framework_version!r}, expected {FRAMEWORK_VERSION!r}.',
            remediation='Execute the current framework source before importing PASS evidence.',
        ))
    for observation in intake.observations:
        if observation.gate_key == 'installed_nicegui' and observation.status is TargetGateStatus.PASS:
            observed_nicegui = intake.environment.nicegui_version
            if observed_nicegui is None:
                findings.append(TargetExecutionIntakeFinding(
                    'nicegui_identity_missing', TargetExecutionIntakeStatus.PENDING,
                    'Installed NiceGUI PASS lacks an observed target NiceGUI version.', observation.gate_key,
                    f'Execute and record exact nicegui=={NICEGUI_VERSION}.',
                ))
            elif observed_nicegui != NICEGUI_VERSION:
                findings.append(TargetExecutionIntakeFinding(
                    'nicegui_identity_mismatch', TargetExecutionIntakeStatus.BLOCKED,
                    f'Installed NiceGUI PASS observed {observed_nicegui!r}, expected exact {NICEGUI_VERSION!r}.', observation.gate_key,
                    f'Run the target gate against exact nicegui=={NICEGUI_VERSION}.',
                ))
        artifact = observation.artifact
        if artifact is None:
            if observation.status is not TargetGateStatus.PENDING:
                findings.append(TargetExecutionIntakeFinding(
                    'execution_artifact_missing', TargetExecutionIntakeStatus.PENDING,
                    f'{observation.gate_key} {observation.status.value.upper()} has no captured artifact bytes.', observation.gate_key,
                    'Attach a current target-execution artifact before relying on this observation for release evidence.',
                ))
            continue
        source = _resolve_artifact_path(artifact, base_dir)
        if not source.is_file():
            findings.append(TargetExecutionIntakeFinding(
                'execution_artifact_unavailable', TargetExecutionIntakeStatus.BLOCKED,
                f'Captured artifact for {observation.gate_key} is unavailable at {source}.', observation.gate_key,
                'Restore the exact captured artifact or recapture the target execution.',
            ))
            continue
        data = source.read_bytes()
        observed_sha = hashlib.sha256(data).hexdigest()
        if len(data) != artifact.size_bytes or observed_sha != artifact.sha256:
            findings.append(TargetExecutionIntakeFinding(
                'execution_artifact_hash_mismatch', TargetExecutionIntakeStatus.BLOCKED,
                f'Captured artifact for {observation.gate_key} no longer matches its recorded SHA-256/size.', observation.gate_key,
                'Do not use changed artifact bytes; recapture the target execution.',
            ))
        expected_sha = observation.metadata.get('expected_sha256')
        if expected_sha is not None and str(expected_sha) != artifact.sha256:
            findings.append(TargetExecutionIntakeFinding(
                'manifest_artifact_hash_mismatch', TargetExecutionIntakeStatus.BLOCKED,
                f'Manifest expected SHA-256 for {observation.gate_key} does not match captured artifact bytes.', observation.gate_key,
                'Resolve the manifest/artifact mismatch before evidence assimilation.',
            ))
    status = TargetExecutionIntakeStatus.VERIFIED
    if any(item.status is TargetExecutionIntakeStatus.BLOCKED for item in findings):
        status = TargetExecutionIntakeStatus.BLOCKED
    elif any(item.status is TargetExecutionIntakeStatus.PENDING for item in findings) or any(item.status is TargetGateStatus.PENDING for item in intake.observations):
        status = TargetExecutionIntakeStatus.PENDING
    return TargetExecutionIntakeVerification(intake.intake_id, status, tuple(findings))


def _bundle_provider_source(bundle: SemiconductorTargetEvidenceBundle) -> tuple[str | None, str | None]:
    for value in (bundle.adapter_conformance, bundle.performance, bundle.benchmark, bundle.metadata):
        if not isinstance(value, Mapping):
            continue
        provider = value.get('provider')
        source = value.get('source_key')
        if provider or source:
            return (None if provider is None else str(provider), None if source is None else str(source))
    return None, None


def apply_target_execution_intake(
    bundle: SemiconductorTargetEvidenceBundle,
    intake: TargetExecutionIntake,
    *,
    base_dir: str | Path | None = None,
) -> SemiconductorTargetEvidenceBundle:
    if bundle.recipe_key != intake.recipe_key:
        raise ValueError('target execution intake recipe does not match evidence bundle')
    provider, source = _bundle_provider_source(bundle)
    if provider is not None and provider != intake.provider:
        raise ValueError('target execution intake provider does not match evidence bundle')
    if source is not None and source != intake.source_key:
        raise ValueError('target execution intake source does not match evidence bundle')
    verification = verify_target_execution_intake(intake, base_dir=base_dir)
    if verification.blocked:
        raise ValueError('target execution intake is BLOCKED; resolve integrity/identity findings before assimilation')
    observation_map = {item.gate_key: item for item in intake.observations}
    existing = {item.key: item for item in bundle.certification.gates}
    gates: list[TargetRuntimeGate] = []
    for gate in bundle.certification.gates:
        observation = observation_map.get(gate.key)
        if observation is None:
            gates.append(gate)
            continue
        status = observation.status
        if status is TargetGateStatus.PASS and verification.gate_status(gate.key) is not TargetExecutionIntakeStatus.VERIFIED:
            status = TargetGateStatus.PENDING
        metadata = dict(gate.metadata)
        metadata.update(observation.metadata)
        metadata['target_execution_intake_id'] = intake.intake_id
        if observation.artifact is not None:
            metadata['artifact_key'] = observation.artifact.key
            metadata['artifact_sha256'] = observation.artifact.sha256
        evidence = observation.evidence
        if observation.status is TargetGateStatus.PASS and status is TargetGateStatus.PENDING:
            evidence = f'{observation.evidence} PASS was not accepted because required traceability/identity evidence is still pending.'
        gates.append(TargetRuntimeGate(gate.key, gate.label, status, evidence, metadata))
    for key in observation_map:
        if key not in existing:
            raise ValueError(f'evidence bundle does not contain target gate {key!r}')
    artifacts_by_key = {item.key: item for item in bundle.artifacts}
    for artifact in intake.artifacts:
        previous = artifacts_by_key.get(artifact.key)
        if previous is not None and previous.sha256 != artifact.sha256:
            raise ValueError(f'target execution artifact key {artifact.key!r} conflicts with existing evidence artifact')
        artifacts_by_key[artifact.key] = artifact
    metadata = dict(bundle.metadata)
    gate_artifacts_raw = metadata.get('gate_artifacts', {})
    gate_artifacts = dict(gate_artifacts_raw) if isinstance(gate_artifacts_raw, Mapping) else {}
    for observation in intake.observations:
        if observation.artifact is not None:
            current = gate_artifacts.get(observation.gate_key, ())
            if isinstance(current, str):
                values = [current]
            elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
                values = [str(item) for item in current]
            else:
                values = []
            if observation.artifact.key not in values:
                values.append(observation.artifact.key)
            gate_artifacts[observation.gate_key] = tuple(values)
    metadata['gate_artifacts'] = gate_artifacts
    metadata['framework_version'] = FRAMEWORK_VERSION
    metadata['nicegui_required'] = NICEGUI_VERSION
    metadata['target_execution_intake_id'] = intake.intake_id
    metadata['target_execution_intake_status'] = verification.status.value
    return SemiconductorTargetEvidenceBundle(
        bundle.recipe_key,
        SemiconductorTargetRuntimeCertification(bundle.recipe_key, tuple(gates)),
        intake.environment,
        tuple(sorted(artifacts_by_key.values(), key=lambda item: item.key)),
        bundle.benchmark,
        bundle.adapter_conformance,
        bundle.performance,
        metadata,
        _utc_now(),
        1,
    )


@runtime_checkable
class TargetExecutionIntakeAdapter(Protocol):
    key: str

    def load(self, manifest_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> TargetExecutionIntake: ...


@dataclass(frozen=True, slots=True)
class JsonTargetExecutionIntakeAdapter:
    key: str = 'json-manifest'

    def load(self, manifest_path: str | Path, *, artifact_base_dir: str | Path | None = None) -> TargetExecutionIntake:
        return load_target_execution_intake_manifest(manifest_path, artifact_base_dir=artifact_base_dir)


TARGET_EXECUTION_INTAKE_ADAPTERS: Mapping[str, TargetExecutionIntakeAdapter] = MappingProxyType({
    'json-manifest': JsonTargetExecutionIntakeAdapter(),
})


@dataclass(frozen=True, slots=True)
class PromotionCandidateArchiveVerification:
    path: str
    sha256: str
    candidate_id: str | None
    entries: tuple[str, ...]
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.sha256) != 64:
            raise ValueError('candidate archive verification requires sha256')
        if self.candidate_id is not None and len(self.candidate_id) != 64:
            raise ValueError('candidate archive verification candidate id must be sha256')
        object.__setattr__(self, 'entries', tuple(self.entries))
        object.__setattr__(self, 'errors', tuple(self.errors))

    @property
    def verified(self) -> bool:
        return not self.errors and self.candidate_id is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': self.path,
            'sha256': self.sha256,
            'candidate_id': self.candidate_id,
            'entries': self.entries,
            'verified': self.verified,
            'errors': self.errors,
        }


def verify_stable_promotion_candidate_archive(
    path: str | Path, *, expected_candidate: StablePromotionCandidate | None = None,
) -> PromotionCandidateArchiveVerification:
    source = Path(path)
    if not source.is_file():
        digest = hashlib.sha256(str(source).encode('utf-8')).hexdigest()
        return PromotionCandidateArchiveVerification(str(source), digest, None, (), ('candidate archive is unavailable',))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    errors: list[str] = []
    candidate_id: str | None = None
    entries: tuple[str, ...] = ()
    try:
        with zipfile.ZipFile(source, 'r') as archive:
            names = tuple(info.filename for info in archive.infolist())
            entries = tuple(sorted(names))
            errors.extend(_safe_zip_names(names))
            if 'candidate.json' not in names:
                errors.append('candidate archive is missing candidate.json')
            if 'MANIFEST.sha256' not in names:
                errors.append('candidate archive is missing MANIFEST.sha256')
            if 'MANIFEST.sha256' in names:
                expected: dict[str, str] = {}
                try:
                    manifest_text = archive.read('MANIFEST.sha256').decode('utf-8')
                    for line in manifest_text.splitlines():
                        if not line.strip():
                            continue
                        sha, name = line.split('  ', 1)
                        if not re.fullmatch(r'[0-9a-f]{64}', sha):
                            raise ValueError('invalid manifest SHA-256')
                        if name in expected:
                            raise ValueError('duplicate manifest entry')
                        expected[name] = sha
                    actual_names = {name for name in names if name != 'MANIFEST.sha256'}
                    if set(expected) != actual_names:
                        errors.append('candidate archive manifest entry set does not match archive contents')
                    for name, sha in expected.items():
                        if name in names and hashlib.sha256(archive.read(name)).hexdigest() != sha:
                            errors.append(f'candidate archive manifest hash mismatch: {name}')
                except Exception as exc:
                    errors.append(f'candidate archive manifest is invalid: {exc}')
            if 'candidate.json' in names:
                try:
                    payload = json.loads(archive.read('candidate.json').decode('utf-8'))
                    if not isinstance(payload, Mapping):
                        raise TypeError('candidate.json must contain an object')
                    candidate = promotion_candidate_from_dict(payload)
                    candidate_id = candidate.candidate_id
                    if expected_candidate is not None and candidate.candidate_id != expected_candidate.candidate_id:
                        errors.append('candidate archive candidate id does not match expected candidate')
                except Exception as exc:
                    errors.append(f'candidate archive candidate.json is invalid: {exc}')
    except zipfile.BadZipFile:
        errors.append('candidate archive is not a valid ZIP file')
    return PromotionCandidateArchiveVerification(str(source), digest, candidate_id, entries, tuple(dict.fromkeys(errors)))


@dataclass(frozen=True, slots=True)
class StablePromotionOperationalHandoff:
    handoff_id: str
    candidate: StablePromotionCandidate
    candidate_archive: PromotionCandidateArchiveVerification
    adapter_key: str = 'file-package'
    change_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.handoff_id) != 64 or not self.adapter_key.strip():
            raise ValueError('promotion operational handoff requires sha256 id and adapter key')
        if self.candidate_archive.candidate_id is not None and self.candidate_archive.candidate_id != self.candidate.candidate_id:
            raise ValueError('promotion operational handoff candidate/archive mismatch')
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def status(self) -> PromotionHandoffStatus:
        if self.candidate.status is PromotionCandidateStatus.BLOCKED or not self.candidate_archive.verified:
            return PromotionHandoffStatus.BLOCKED
        if self.candidate.status is not PromotionCandidateStatus.READY:
            return PromotionHandoffStatus.PENDING
        return PromotionHandoffStatus.READY

    @property
    def ready_for_company_handoff(self) -> bool:
        return self.status is PromotionHandoffStatus.READY

    @property
    def next_actions(self) -> tuple[str, ...]:
        if not self.candidate_archive.verified:
            return ('Regenerate or restore the exact verified Wave 67 candidate package before operational handoff.',)
        if self.candidate.status is PromotionCandidateStatus.BLOCKED:
            return self.candidate.next_actions or ('Resolve blocked stable-promotion candidate findings before handoff.',)
        if self.candidate.status is PromotionCandidateStatus.PENDING:
            return self.candidate.next_actions or ('Complete the remaining stable-promotion candidate evidence/rehearsal gaps.',)
        return ('Execute through the approved company deployment/change path, then capture a bound promotion operation record.',)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1,
            'handoff_id': self.handoff_id,
            'status': self.status.value,
            'ready_for_company_handoff': self.ready_for_company_handoff,
            'adapter_key': self.adapter_key,
            'change_reference': self.change_reference,
            'generated_at': self.generated_at,
            'candidate': self.candidate.to_dict(),
            'candidate_archive': self.candidate_archive.to_dict(),
            'metadata': dict(self.metadata),
            'next_actions': self.next_actions,
            'affects_candidate_status': False,
            'affects_target_gate_status': False,
        }


def _handoff_identity_payload(
    candidate: StablePromotionCandidate,
    archive: PromotionCandidateArchiveVerification,
    adapter_key: str,
    change_reference: str | None,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'candidate_id': candidate.candidate_id,
        'candidate_archive_sha256': archive.sha256,
        'adapter_key': adapter_key,
        'change_reference': change_reference,
        'metadata': dict(metadata),
    }


def build_stable_promotion_operational_handoff(
    candidate: StablePromotionCandidate,
    candidate_package_path: str | Path,
    *,
    adapter_key: str = 'file-package',
    change_reference: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> StablePromotionOperationalHandoff:
    archive = verify_stable_promotion_candidate_archive(candidate_package_path, expected_candidate=candidate)
    payload = _handoff_identity_payload(candidate, archive, adapter_key, change_reference, metadata or {})
    return StablePromotionOperationalHandoff(
        _canonical_digest(payload), candidate, archive, adapter_key, change_reference, metadata or {},
    )


def promotion_operational_handoff_from_dict(payload: Mapping[str, Any]) -> StablePromotionOperationalHandoff:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported promotion operational handoff schema {payload.get("schema_version")!r}')
    candidate_payload = payload.get('candidate')
    archive_payload = payload.get('candidate_archive')
    if not isinstance(candidate_payload, Mapping) or not isinstance(archive_payload, Mapping):
        raise TypeError('promotion operational handoff requires candidate and candidate_archive objects')
    candidate = promotion_candidate_from_dict(candidate_payload)
    archive = PromotionCandidateArchiveVerification(
        str(archive_payload.get('path', '')),
        str(archive_payload['sha256']),
        None if archive_payload.get('candidate_id') is None else str(archive_payload.get('candidate_id')),
        tuple(str(item) for item in archive_payload.get('entries', ())),
        tuple(str(item) for item in archive_payload.get('errors', ())),
    )
    handoff = StablePromotionOperationalHandoff(
        str(payload['handoff_id']),
        candidate,
        archive,
        str(payload.get('adapter_key') or 'file-package'),
        None if payload.get('change_reference') is None else str(payload.get('change_reference')),
        payload.get('metadata', {}),
        str(payload.get('generated_at') or _utc_now()),
    )
    expected = _canonical_digest(_handoff_identity_payload(handoff.candidate, handoff.candidate_archive, handoff.adapter_key, handoff.change_reference, handoff.metadata))
    if handoff.handoff_id != expected:
        raise ValueError('promotion operational handoff id does not match persisted content')
    persisted_status = payload.get('status')
    if persisted_status is not None and str(persisted_status) != handoff.status.value:
        raise ValueError('promotion operational handoff status does not match persisted content')
    return handoff


def write_promotion_operational_handoff(path: str | Path, handoff: StablePromotionOperationalHandoff) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(handoff.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_promotion_operational_handoff(path: str | Path, *, reverify_archive: bool = True) -> StablePromotionOperationalHandoff:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('promotion operational handoff JSON must contain an object')
    handoff = promotion_operational_handoff_from_dict(payload)
    if not reverify_archive:
        return handoff
    current = verify_stable_promotion_candidate_archive(handoff.candidate_archive.path, expected_candidate=handoff.candidate)
    if current.sha256 == handoff.candidate_archive.sha256 and current.errors == handoff.candidate_archive.errors:
        return handoff
    # Preserve the original handoff identity; the live archive mismatch must be visible as a blocked snapshot.
    errors = tuple(dict.fromkeys((*current.errors, 'candidate archive bytes changed after handoff creation'))) if current.sha256 != handoff.candidate_archive.sha256 else current.errors
    current = PromotionCandidateArchiveVerification(current.path, current.sha256, current.candidate_id, current.entries, errors)
    return StablePromotionOperationalHandoff(
        handoff.handoff_id, handoff.candidate, current, handoff.adapter_key, handoff.change_reference, handoff.metadata, handoff.generated_at,
    )


@dataclass(frozen=True, slots=True)
class PromotionOperationalHandoffPackage:
    path: str
    sha256: str
    handoff_id: str
    status: PromotionHandoffStatus
    entries: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or len(self.handoff_id) != 64:
            raise ValueError('promotion operational handoff package requires sha256 identifiers')
        object.__setattr__(self, 'status', PromotionHandoffStatus(self.status))
        object.__setattr__(self, 'entries', tuple(self.entries))

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': self.path,
            'sha256': self.sha256,
            'handoff_id': self.handoff_id,
            'status': self.status.value,
            'entries': self.entries,
        }


def _operation_template(recipe_key: str, kind: PromotionRehearsalKind, handoff_id: str) -> dict[str, Any]:
    plan = build_promotion_rehearsal(recipe_key, kind)
    runbook = SEMICONDUCTOR_OPERATIONAL_RUNBOOKS[recipe_key]
    by_step = {item.key: item for item in runbook.steps}
    return {
        'schema_version': 1,
        'handoff_id': handoff_id,
        'recipe_key': recipe_key,
        'kind': kind.value,
        'required_step_keys': plan.required_step_keys,
        'completed_step_keys': (),
        'failed_step_keys': (),
        'required_evidence': {step: by_step[step].evidence_to_capture for step in plan.required_step_keys},
        'evidence': (),
        'notes': (),
        'status': PromotionOperationStatus.PENDING.value,
        'affects_candidate_status': False,
        'affects_target_gate_status': False,
    }


def package_promotion_operational_handoff(path: str | Path, handoff: StablePromotionOperationalHandoff) -> PromotionOperationalHandoffPackage:
    current = verify_stable_promotion_candidate_archive(handoff.candidate_archive.path, expected_candidate=handoff.candidate)
    if not current.verified or current.sha256 != handoff.candidate_archive.sha256:
        raise ValueError('cannot package operational handoff because the bound candidate archive is unavailable or changed')
    target = Path(path)
    if target.suffix.lower() != '.zip':
        target = target.with_suffix('.zip')
    target.parent.mkdir(parents=True, exist_ok=True)
    entries: dict[str, bytes] = {}
    payload = handoff.to_dict()
    payload['candidate_archive'] = dict(payload['candidate_archive'])
    payload['candidate_archive']['path'] = 'candidate/stable-promotion-candidate.zip'
    entries['handoff.json'] = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')
    entries['candidate/stable-promotion-candidate.zip'] = Path(handoff.candidate_archive.path).read_bytes()
    for recipe in handoff.candidate.evidence.recipe_keys:
        for kind in PromotionRehearsalKind:
            template = _operation_template(recipe, kind, handoff.handoff_id)
            entries[f'operations/{recipe}/{kind.value}.template.json'] = (json.dumps(template, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')
    readme = (
        '# NiceGUI Base stable-promotion operational handoff\n\n'
        f'- Handoff: `{handoff.handoff_id}`\n'
        f'- Candidate: `{handoff.candidate.candidate_id}`\n'
        f'- Handoff status: `{handoff.status.value}`\n\n'
        'This package is an operational handoff envelope, not an automated deployment. Use only an approved company deployment/change path. '
        'Operation records and handoff packaging never upgrade target gates or the bound candidate status.\n'
    )
    entries['README.md'] = readme.encode('utf-8')
    manifest = '\n'.join(f'{hashlib.sha256(entries[name]).hexdigest()}  {name}' for name in sorted(entries)) + '\n'
    entries['MANIFEST.sha256'] = manifest.encode('utf-8')
    fixed_time = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=fixed_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, entries[name])
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return PromotionOperationalHandoffPackage(str(target), digest, handoff.handoff_id, handoff.status, tuple(sorted(entries)))


@runtime_checkable
class PromotionOperationalHandoffAdapter(Protocol):
    key: str

    def prepare(
        self,
        candidate: StablePromotionCandidate,
        candidate_package_path: str | Path,
        *,
        change_reference: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> StablePromotionOperationalHandoff: ...


@dataclass(frozen=True, slots=True)
class FilePromotionOperationalHandoffAdapter:
    key: str = 'file-package'

    def prepare(
        self,
        candidate: StablePromotionCandidate,
        candidate_package_path: str | Path,
        *,
        change_reference: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> StablePromotionOperationalHandoff:
        return build_stable_promotion_operational_handoff(
            candidate, candidate_package_path, adapter_key=self.key, change_reference=change_reference, metadata=metadata,
        )


PROMOTION_OPERATIONAL_HANDOFF_ADAPTERS: Mapping[str, PromotionOperationalHandoffAdapter] = MappingProxyType({
    'file-package': FilePromotionOperationalHandoffAdapter(),
})


@dataclass(frozen=True, slots=True)
class PromotionOperationEvidence:
    step_key: str
    evidence_key: str
    artifact: TargetEvidenceArtifact

    def __post_init__(self) -> None:
        if not self.step_key.strip() or not self.evidence_key.strip():
            raise ValueError('promotion operation evidence step/evidence keys must not be empty')

    def to_dict(self) -> dict[str, Any]:
        return {'step_key': self.step_key, 'evidence_key': self.evidence_key, 'artifact': self.artifact.to_dict()}


def capture_promotion_operation_evidence(
    path: str | Path,
    *,
    recipe_key: str,
    step_key: str,
    evidence_key: str,
    artifact_key: str | None = None,
    description: str = '',
) -> PromotionOperationEvidence:
    runbook = SEMICONDUCTOR_OPERATIONAL_RUNBOOKS.get(recipe_key)
    if runbook is None:
        raise KeyError(f'unknown semiconductor recipe {recipe_key!r}')
    steps = {item.key: item for item in runbook.steps}
    if step_key not in steps:
        raise ValueError(f'unknown runbook step {step_key!r} for recipe {recipe_key!r}')
    if evidence_key not in steps[step_key].evidence_to_capture:
        raise ValueError(f'evidence key {evidence_key!r} is not required by runbook step {step_key!r}')
    key = artifact_key or f'{step_key}:{evidence_key}'
    artifact = capture_target_evidence_artifact(path, key=key, description=description or f'{recipe_key} {step_key} {evidence_key}')
    return PromotionOperationEvidence(step_key, evidence_key, artifact)


@dataclass(frozen=True, slots=True)
class PromotionOperationRecord:
    operation_id: str
    handoff_id: str
    recipe_key: str
    kind: PromotionRehearsalKind
    required_step_keys: tuple[str, ...]
    completed_step_keys: tuple[str, ...] = ()
    failed_step_keys: tuple[str, ...] = ()
    evidence: tuple[PromotionOperationEvidence, ...] = ()
    notes: tuple[str, ...] = ()
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.operation_id) != 64 or len(self.handoff_id) != 64 or not self.recipe_key.strip():
            raise ValueError('promotion operation record requires sha256 operation/handoff ids and recipe')
        object.__setattr__(self, 'kind', PromotionRehearsalKind(self.kind))
        object.__setattr__(self, 'required_step_keys', tuple(self.required_step_keys))
        object.__setattr__(self, 'completed_step_keys', tuple(dict.fromkeys(self.completed_step_keys)))
        object.__setattr__(self, 'failed_step_keys', tuple(dict.fromkeys(self.failed_step_keys)))
        object.__setattr__(self, 'evidence', tuple(self.evidence))
        object.__setattr__(self, 'notes', tuple(self.notes))
        plan = build_promotion_rehearsal(self.recipe_key, self.kind)
        if self.required_step_keys != plan.required_step_keys:
            raise ValueError('promotion operation required steps must match the canonical Wave 67 rehearsal/runbook authority')
        allowed = set(self.required_step_keys)
        if not set(self.completed_step_keys).issubset(allowed) or not set(self.failed_step_keys).issubset(allowed):
            raise ValueError('promotion operation completed/failed steps must belong to required steps')
        if set(self.completed_step_keys) & set(self.failed_step_keys):
            raise ValueError('promotion operation step cannot be both completed and failed')
        runbook = SEMICONDUCTOR_OPERATIONAL_RUNBOOKS[self.recipe_key]
        steps = {item.key: item for item in runbook.steps}
        pairs: set[tuple[str, str]] = set()
        artifact_keys: set[str] = set()
        for item in self.evidence:
            if item.step_key not in allowed or item.evidence_key not in steps[item.step_key].evidence_to_capture:
                raise ValueError('promotion operation evidence must bind to canonical evidence requirements for a required step')
            pair = (item.step_key, item.evidence_key)
            if pair in pairs:
                raise ValueError('promotion operation contains duplicate step/evidence entries')
            pairs.add(pair)
            if item.artifact.key in artifact_keys:
                raise ValueError('promotion operation contains duplicate artifact keys')
            artifact_keys.add(item.artifact.key)

    @property
    def required_evidence(self) -> Mapping[str, tuple[str, ...]]:
        runbook = SEMICONDUCTOR_OPERATIONAL_RUNBOOKS[self.recipe_key]
        steps = {item.key: item for item in runbook.steps}
        return MappingProxyType({key: steps[key].evidence_to_capture for key in self.required_step_keys})

    @property
    def missing_evidence(self) -> tuple[str, ...]:
        captured = {(item.step_key, item.evidence_key) for item in self.evidence}
        return tuple(
            f'{step}:{evidence_key}'
            for step in self.required_step_keys
            for evidence_key in self.required_evidence[step]
            if (step, evidence_key) not in captured
        )

    @property
    def status(self) -> PromotionOperationStatus:
        if self.failed_step_keys:
            return PromotionOperationStatus.BLOCKED
        if not set(self.required_step_keys).issubset(self.completed_step_keys):
            return PromotionOperationStatus.PENDING
        if self.missing_evidence:
            return PromotionOperationStatus.PENDING
        return PromotionOperationStatus.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1,
            'operation_id': self.operation_id,
            'handoff_id': self.handoff_id,
            'recipe_key': self.recipe_key,
            'kind': self.kind.value,
            'status': self.status.value,
            'required_step_keys': self.required_step_keys,
            'completed_step_keys': self.completed_step_keys,
            'failed_step_keys': self.failed_step_keys,
            'required_evidence': {key: value for key, value in self.required_evidence.items()},
            'missing_evidence': self.missing_evidence,
            'evidence': [item.to_dict() for item in self.evidence],
            'notes': self.notes,
            'generated_at': self.generated_at,
            'affects_candidate_status': False,
            'affects_target_gate_status': False,
        }


def _operation_identity_payload(
    handoff_id: str,
    recipe_key: str,
    kind: PromotionRehearsalKind,
    required_step_keys: Sequence[str],
    completed_step_keys: Sequence[str],
    failed_step_keys: Sequence[str],
    evidence: Sequence[PromotionOperationEvidence],
    notes: Sequence[str],
) -> dict[str, Any]:
    return {
        'handoff_id': handoff_id,
        'recipe_key': recipe_key,
        'kind': kind.value,
        'required_step_keys': tuple(required_step_keys),
        'completed_step_keys': tuple(sorted(dict.fromkeys(completed_step_keys))),
        'failed_step_keys': tuple(sorted(dict.fromkeys(failed_step_keys))),
        'evidence': [item.to_dict() for item in sorted(evidence, key=lambda item: (item.step_key, item.evidence_key, item.artifact.key))],
        'notes': tuple(notes),
    }


def build_promotion_operation_record(
    handoff: StablePromotionOperationalHandoff,
    recipe_key: str,
    kind: PromotionRehearsalKind | str,
    *,
    completed_step_keys: Sequence[str] = (),
    failed_step_keys: Sequence[str] = (),
    evidence: Sequence[PromotionOperationEvidence] = (),
    notes: Sequence[str] = (),
) -> PromotionOperationRecord:
    if recipe_key not in handoff.candidate.evidence.recipe_keys:
        raise ValueError('promotion operation recipe is not present in the bound stable-promotion candidate')
    resolved_kind = PromotionRehearsalKind(kind)
    required = build_promotion_rehearsal(recipe_key, resolved_kind).required_step_keys
    payload = _operation_identity_payload(handoff.handoff_id, recipe_key, resolved_kind, required, completed_step_keys, failed_step_keys, evidence, notes)
    return PromotionOperationRecord(
        _canonical_digest(payload), handoff.handoff_id, recipe_key, resolved_kind, required,
        tuple(sorted(dict.fromkeys(completed_step_keys))), tuple(sorted(dict.fromkeys(failed_step_keys))),
        tuple(sorted(evidence, key=lambda item: (item.step_key, item.evidence_key, item.artifact.key))), tuple(notes),
    )


def promotion_operation_record_from_dict(payload: Mapping[str, Any]) -> PromotionOperationRecord:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported promotion operation record schema {payload.get("schema_version")!r}')
    evidence_payload = payload.get('evidence', ())
    if not isinstance(evidence_payload, list):
        raise TypeError('promotion operation evidence must be a list')
    evidence: list[PromotionOperationEvidence] = []
    for item in evidence_payload:
        if not isinstance(item, Mapping) or not isinstance(item.get('artifact'), Mapping):
            raise TypeError('promotion operation evidence entries require artifact objects')
        artifact_payload = item['artifact']
        artifact = TargetEvidenceArtifact(
            str(artifact_payload['key']), str(artifact_payload['path']), str(artifact_payload['sha256']),
            int(artifact_payload['size_bytes']), str(artifact_payload.get('description', '')),
        )
        evidence.append(PromotionOperationEvidence(str(item['step_key']), str(item['evidence_key']), artifact))
    record = PromotionOperationRecord(
        str(payload['operation_id']),
        str(payload['handoff_id']),
        str(payload['recipe_key']),
        PromotionRehearsalKind(str(payload['kind'])),
        tuple(str(item) for item in payload.get('required_step_keys', ())),
        tuple(str(item) for item in payload.get('completed_step_keys', ())),
        tuple(str(item) for item in payload.get('failed_step_keys', ())),
        tuple(evidence),
        tuple(str(item) for item in payload.get('notes', ())),
        str(payload.get('generated_at') or _utc_now()),
    )
    expected = _canonical_digest(_operation_identity_payload(
        record.handoff_id, record.recipe_key, record.kind, record.required_step_keys,
        record.completed_step_keys, record.failed_step_keys, record.evidence, record.notes,
    ))
    if record.operation_id != expected:
        raise ValueError('promotion operation id does not match persisted content')
    if payload.get('status') is not None and str(payload.get('status')) != record.status.value:
        raise ValueError('promotion operation status does not match persisted content')
    return record


def write_promotion_operation_record(path: str | Path, record: PromotionOperationRecord) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_promotion_operation_record(path: str | Path) -> PromotionOperationRecord:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('promotion operation record JSON must contain an object')
    return promotion_operation_record_from_dict(payload)


@dataclass(frozen=True, slots=True)
class PromotionOperationVerification:
    operation_id: str
    status: PromotionOperationStatus
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.operation_id) != 64:
            raise ValueError('promotion operation verification requires sha256 operation id')
        object.__setattr__(self, 'status', PromotionOperationStatus(self.status))
        object.__setattr__(self, 'errors', tuple(self.errors))

    @property
    def verified(self) -> bool:
        return self.status is PromotionOperationStatus.PASS and not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {'operation_id': self.operation_id, 'status': self.status.value, 'verified': self.verified, 'errors': self.errors}


def verify_promotion_operation_record(
    record: PromotionOperationRecord, *, base_dir: str | Path | None = None,
) -> PromotionOperationVerification:
    errors: list[str] = []
    for item in record.evidence:
        path = _resolve_artifact_path(item.artifact, base_dir)
        if not path.is_file():
            errors.append(f'operation evidence unavailable: {item.step_key}:{item.evidence_key}')
            continue
        data = path.read_bytes()
        if len(data) != item.artifact.size_bytes or hashlib.sha256(data).hexdigest() != item.artifact.sha256:
            errors.append(f'operation evidence hash mismatch: {item.step_key}:{item.evidence_key}')
    if errors:
        return PromotionOperationVerification(record.operation_id, PromotionOperationStatus.BLOCKED, tuple(errors))
    return PromotionOperationVerification(record.operation_id, record.status, ())


__all__ = [
    'FilePromotionOperationalHandoffAdapter','JsonTargetExecutionIntakeAdapter','PROMOTION_OPERATIONAL_HANDOFF_ADAPTERS',
    'PromotionCandidateArchiveVerification','PromotionHandoffStatus','PromotionOperationEvidence','PromotionOperationRecord',
    'PromotionOperationStatus','PromotionOperationVerification','PromotionOperationalHandoffAdapter','PromotionOperationalHandoffPackage',
    'StablePromotionOperationalHandoff','TARGET_EXECUTION_GATE_KEYS','TARGET_EXECUTION_INTAKE_ADAPTERS','TargetExecutionIntake',
    'TargetExecutionIntakeAdapter','TargetExecutionIntakeFinding','TargetExecutionIntakeStatus','TargetExecutionIntakeVerification',
    'TargetExecutionObservation','apply_target_execution_intake','build_promotion_operation_record',
    'build_stable_promotion_operational_handoff','build_target_execution_intake','capture_promotion_operation_evidence',
    'load_target_execution_intake_manifest','package_promotion_operational_handoff','promotion_operation_record_from_dict',
    'promotion_operational_handoff_from_dict','read_promotion_operation_record','read_promotion_operational_handoff',
    'read_target_execution_intake','target_execution_intake_from_dict','verify_promotion_operation_record',
    'verify_stable_promotion_candidate_archive','verify_target_execution_intake','write_promotion_operation_record',
    'write_promotion_operational_handoff','write_target_execution_intake',
]
