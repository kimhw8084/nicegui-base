from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from nicegui_base.semiconductor.benchmarking import SemiconductorBenchmarkReport
from nicegui_base.semiconductor.conformance import AdapterConformanceReport
from nicegui_base.semiconductor.runtime_experience import RuntimePerformanceReport
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

from .semiconductor_runtime import SemiconductorTargetRuntimeCertification, TargetGateStatus, TargetRuntimeGate, build_semiconductor_target_runtime_certification


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


@dataclass(frozen=True, slots=True)
class TargetEvidenceArtifact:
    key: str
    path: str
    sha256: str
    size_bytes: int
    description: str = ''

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.path.strip() or len(self.sha256) != 64 or self.size_bytes < 0:
            raise ValueError('invalid target evidence artifact')

    def to_dict(self) -> dict[str, Any]:
        return {'key': self.key, 'path': self.path, 'sha256': self.sha256, 'size_bytes': self.size_bytes, 'description': self.description}


@dataclass(frozen=True, slots=True)
class TargetEnvironmentFingerprint:
    python_version: str
    platform: str
    nicegui_version: str | None
    executable: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'python_version': self.python_version,
            'platform': self.platform,
            'nicegui_version': self.nicegui_version,
            'executable': self.executable,
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class SemiconductorTargetEvidenceBundle:
    recipe_key: str
    certification: SemiconductorTargetRuntimeCertification
    environment: TargetEnvironmentFingerprint
    artifacts: tuple[TargetEvidenceArtifact, ...] = ()
    benchmark: Mapping[str, Any] | None = None
    adapter_conformance: Mapping[str, Any] | None = None
    performance: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    captured_at: str = field(default_factory=_utc_now)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError('unsupported semiconductor target evidence bundle schema')
        if self.certification.recipe_key != self.recipe_key:
            raise ValueError('target evidence certification recipe mismatch')
        object.__setattr__(self, 'artifacts', tuple(self.artifacts))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))
        for name in ('benchmark','adapter_conformance','performance'):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, MappingProxyType(dict(value)))

    @property
    def promotable(self) -> bool:
        return self.certification.promotable

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'recipe_key': self.recipe_key,
            'captured_at': self.captured_at,
            'promotable': self.promotable,
            'environment': self.environment.to_dict(),
            'certification': self.certification.to_dict(),
            'artifacts': [item.to_dict() for item in self.artifacts],
            'adapter_conformance': dict(self.adapter_conformance) if self.adapter_conformance is not None else None,
            'performance': dict(self.performance) if self.performance is not None else None,
            'benchmark': dict(self.benchmark) if self.benchmark is not None else None,
            'metadata': dict(self.metadata),
        }


def capture_target_environment_fingerprint(*, metadata: Mapping[str, Any] | None = None) -> TargetEnvironmentFingerprint:
    try:
        nicegui_version = importlib.metadata.version('nicegui')
    except importlib.metadata.PackageNotFoundError:
        nicegui_version = None
    return TargetEnvironmentFingerprint(
        platform.python_version(),
        platform.platform(),
        nicegui_version,
        sys.executable,
        metadata or {},
    )


def capture_target_evidence_artifact(path: str | Path, *, key: str, description: str = '') -> TargetEvidenceArtifact:
    item = Path(path)
    if not item.is_file():
        raise FileNotFoundError(item)
    digest = hashlib.sha256(item.read_bytes()).hexdigest()
    return TargetEvidenceArtifact(key, str(item), digest, item.stat().st_size, description)


def build_semiconductor_target_evidence_bundle(
    recipe_key: str,
    *,
    adapter_conformance: AdapterConformanceReport | None = None,
    performance: RuntimePerformanceReport | None = None,
    benchmark: SemiconductorBenchmarkReport | None = None,
    installed_nicegui_pass: bool | None = None,
    server_websocket_pass: bool | None = None,
    browser_pass: bool | None = None,
    human_visual_baseline_pass: bool | None = None,
    artifacts: tuple[TargetEvidenceArtifact, ...] = (),
    environment: TargetEnvironmentFingerprint | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> SemiconductorTargetEvidenceBundle:
    certification = build_semiconductor_target_runtime_certification(
        recipe_key,
        adapter_conformance=adapter_conformance,
        performance=performance,
        installed_nicegui_pass=installed_nicegui_pass,
        server_websocket_pass=server_websocket_pass,
        browser_pass=browser_pass,
        human_visual_baseline_pass=human_visual_baseline_pass,
    )
    if benchmark is not None:
        gate = TargetRuntimeGate(
            'provider_benchmark',
            'Governed representative provider benchmark',
            TargetGateStatus.PASS if benchmark.passed else TargetGateStatus.FAIL,
            f'Benchmark profile {benchmark.profile_key} supplied.',
            {'source_key': benchmark.source_key, 'provider': benchmark.provider, 'errors': tuple(item.code for item in benchmark.errors)},
        )
        certification = SemiconductorTargetRuntimeCertification(certification.recipe_key, (*certification.gates, gate))
    else:
        certification = SemiconductorTargetRuntimeCertification(certification.recipe_key, (*certification.gates, TargetRuntimeGate(
            'provider_benchmark',
            'Governed representative provider benchmark',
            TargetGateStatus.PENDING,
            'No governed representative provider benchmark report was supplied.',
        )))
    evidence_metadata = dict(metadata or {})
    # These identifiers describe the framework/runtime contract that produced
    # the evidence.  Callers may add metadata, but must not spoof the release
    # authority recorded by the framework itself.
    evidence_metadata['framework_version'] = FRAMEWORK_VERSION
    evidence_metadata['nicegui_required'] = NICEGUI_VERSION
    return SemiconductorTargetEvidenceBundle(
        recipe_key,
        certification,
        environment or capture_target_environment_fingerprint(),
        artifacts,
        benchmark.to_dict() if benchmark is not None else None,
        adapter_conformance.to_dict() if adapter_conformance is not None else None,
        performance.to_dict() if performance is not None else None,
        evidence_metadata,
    )


def target_evidence_bundle_to_dict(bundle: SemiconductorTargetEvidenceBundle) -> dict[str, Any]:
    return bundle.to_dict()


def target_evidence_bundle_from_dict(payload: Mapping[str, Any]) -> SemiconductorTargetEvidenceBundle:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported target evidence schema {payload.get("schema_version")!r}')
    env_payload = payload.get('environment')
    cert_payload = payload.get('certification')
    if not isinstance(env_payload, Mapping) or not isinstance(cert_payload, Mapping):
        raise TypeError('target evidence requires environment and certification objects')
    environment = TargetEnvironmentFingerprint(
        str(env_payload.get('python_version','')),
        str(env_payload.get('platform','')),
        env_payload.get('nicegui_version'),
        str(env_payload.get('executable','')),
        env_payload.get('metadata',{}),
    )
    gates_payload = cert_payload.get('gates')
    if not isinstance(gates_payload, list):
        raise TypeError('target evidence certification gates must be a list')
    gates = tuple(TargetRuntimeGate(
        str(item['key']), str(item['label']), TargetGateStatus(str(item['status'])), str(item['evidence']), item.get('metadata',{})
    ) for item in gates_payload)
    certification = SemiconductorTargetRuntimeCertification(str(cert_payload['recipe_key']), gates)
    artifacts = tuple(TargetEvidenceArtifact(
        str(item['key']), str(item['path']), str(item['sha256']), int(item['size_bytes']), str(item.get('description',''))
    ) for item in payload.get('artifacts', ()))
    return SemiconductorTargetEvidenceBundle(
        str(payload['recipe_key']), certification, environment, artifacts,
        payload.get('benchmark'), payload.get('adapter_conformance'), payload.get('performance'),
        payload.get('metadata',{}), str(payload.get('captured_at') or _utc_now()), 1,
    )


def serialize_semiconductor_target_evidence(bundle: SemiconductorTargetEvidenceBundle, *, indent: int | None = 2) -> str:
    return json.dumps(bundle.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False)


def deserialize_semiconductor_target_evidence(value: str) -> SemiconductorTargetEvidenceBundle:
    payload = json.loads(value)
    if not isinstance(payload, Mapping):
        raise TypeError('target evidence JSON must contain an object')
    return target_evidence_bundle_from_dict(payload)


def write_semiconductor_target_evidence(path: str | Path, bundle: SemiconductorTargetEvidenceBundle) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(serialize_semiconductor_target_evidence(bundle) + '\n', encoding='utf-8')
    return target


def read_semiconductor_target_evidence(path: str | Path) -> SemiconductorTargetEvidenceBundle:
    return deserialize_semiconductor_target_evidence(Path(path).read_text(encoding='utf-8'))


__all__ = [
    'SemiconductorTargetEvidenceBundle','TargetEnvironmentFingerprint','TargetEvidenceArtifact',
    'build_semiconductor_target_evidence_bundle','capture_target_environment_fingerprint','capture_target_evidence_artifact',
    'deserialize_semiconductor_target_evidence','read_semiconductor_target_evidence','serialize_semiconductor_target_evidence',
    'target_evidence_bundle_from_dict','target_evidence_bundle_to_dict','write_semiconductor_target_evidence',
]
