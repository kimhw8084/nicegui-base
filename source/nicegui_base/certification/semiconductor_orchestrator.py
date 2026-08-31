from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from nicegui_base.semiconductor.operational_readiness import OperationalReadinessState, SemiconductorOperationalReadiness
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

from .semiconductor_evidence import SemiconductorTargetEvidenceBundle, TargetEvidenceArtifact, target_evidence_bundle_from_dict, target_evidence_bundle_to_dict
from .semiconductor_runtime import TargetGateStatus


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('evidence timestamp must include timezone information')
    return parsed.astimezone(timezone.utc)


class EvidenceFreshnessStatus(str, Enum):
    CURRENT = 'current'
    STALE = 'stale'
    FUTURE = 'future'
    INVALID = 'invalid'


class ArtifactIntegrityStatus(str, Enum):
    VERIFIED = 'verified'
    MISSING = 'missing'
    HASH_MISMATCH = 'hash_mismatch'
    INVALID = 'invalid'


class PromotionDecisionStatus(str, Enum):
    PROMOTABLE = 'promotable'
    PENDING = 'pending'
    BLOCKED = 'blocked'


class PromotionFindingSeverity(str, Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


_EXTERNAL_GATE_KEYS = ('installed_nicegui', 'server_websocket', 'supported_browser', 'human_visual_baseline')


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessPolicy:
    max_age_hours: float = 168.0
    max_future_skew_minutes: float = 5.0
    require_artifact_integrity: bool = True
    require_external_gate_traceability: bool = True
    external_gate_keys: tuple[str, ...] = _EXTERNAL_GATE_KEYS

    def __post_init__(self) -> None:
        if self.max_age_hours <= 0 or self.max_future_skew_minutes < 0:
            raise ValueError('evidence freshness limits must be positive/non-negative')
        object.__setattr__(self, 'external_gate_keys', tuple(self.external_gate_keys))


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessAssessment:
    recipe_key: str
    status: EvidenceFreshnessStatus
    captured_at: str
    age_hours: float | None
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {'recipe_key': self.recipe_key, 'status': self.status.value, 'captured_at': self.captured_at, 'age_hours': self.age_hours, 'detail': self.detail}


@dataclass(frozen=True, slots=True)
class ArtifactIntegrityFinding:
    key: str
    path: str
    status: ArtifactIntegrityStatus
    detail: str
    expected_sha256: str
    observed_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key, 'path': self.path, 'status': self.status.value, 'detail': self.detail,
            'expected_sha256': self.expected_sha256, 'observed_sha256': self.observed_sha256,
        }


@dataclass(frozen=True, slots=True)
class EvidenceTraceabilityReport:
    recipe_key: str
    freshness: EvidenceFreshnessAssessment
    artifacts: tuple[ArtifactIntegrityFinding, ...]
    untraced_pass_gates: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'artifacts', tuple(self.artifacts))
        object.__setattr__(self, 'untraced_pass_gates', tuple(self.untraced_pass_gates))

    @property
    def corrupt(self) -> bool:
        return self.freshness.status in {EvidenceFreshnessStatus.FUTURE, EvidenceFreshnessStatus.INVALID} or any(item.status in {ArtifactIntegrityStatus.HASH_MISMATCH, ArtifactIntegrityStatus.INVALID} for item in self.artifacts)

    @property
    def pending(self) -> bool:
        return self.freshness.status is EvidenceFreshnessStatus.STALE or any(item.status is ArtifactIntegrityStatus.MISSING for item in self.artifacts) or bool(self.untraced_pass_gates)

    @property
    def valid_for_promotion(self) -> bool:
        return not self.corrupt and not self.pending and self.freshness.status is EvidenceFreshnessStatus.CURRENT

    def to_dict(self) -> dict[str, Any]:
        return {
            'recipe_key': self.recipe_key,
            'valid_for_promotion': self.valid_for_promotion,
            'corrupt': self.corrupt,
            'pending': self.pending,
            'freshness': self.freshness.to_dict(),
            'artifacts': [item.to_dict() for item in self.artifacts],
            'untraced_pass_gates': self.untraced_pass_gates,
        }


@dataclass(frozen=True, slots=True)
class ProviderQualificationPack:
    provider: str
    bundles: tuple[SemiconductorTargetEvidenceBundle, ...]
    traceability: tuple[EvidenceTraceabilityReport, ...]
    qualification_id: str
    source_keys: tuple[str, ...]
    superseded_bundles: int = 0
    generated_at: str = field(default_factory=lambda: _utc_now().replace(microsecond=0).isoformat().replace('+00:00', 'Z'))

    def __post_init__(self) -> None:
        if not self.provider.strip() or len(self.qualification_id) != 64:
            raise ValueError('provider qualification pack requires provider and sha256 qualification_id')
        object.__setattr__(self, 'bundles', tuple(self.bundles))
        object.__setattr__(self, 'traceability', tuple(self.traceability))
        object.__setattr__(self, 'source_keys', tuple(self.source_keys))
        if len(self.bundles) != len(self.traceability):
            raise ValueError('qualification bundles and traceability reports must align')

    @property
    def recipe_keys(self) -> tuple[str, ...]:
        return tuple(item.recipe_key for item in self.bundles)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1,
            'provider': self.provider,
            'qualification_id': self.qualification_id,
            'generated_at': self.generated_at,
            'source_keys': self.source_keys,
            'superseded_bundles': self.superseded_bundles,
            'recipe_keys': self.recipe_keys,
            'bundles': [target_evidence_bundle_to_dict(item) for item in self.bundles],
            'traceability': [item.to_dict() for item in self.traceability],
        }


@dataclass(frozen=True, slots=True)
class PromotionFinding:
    code: str
    severity: PromotionFindingSeverity
    message: str
    remediation: str = ''
    recipe_key: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('promotion finding code and message must not be empty')
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'severity': self.severity.value, 'message': self.message, 'remediation': self.remediation, 'recipe_key': self.recipe_key, 'metadata': dict(self.metadata)}


@dataclass(frozen=True, slots=True)
class PromotionPolicy:
    key: str = 'stable'
    require_all_target_gates: bool = True
    require_traceable_current_evidence: bool = True
    require_operational_release_ready: bool = True
    require_consistent_environment: bool = True
    require_framework_version_match: bool = True
    require_runtime_version_match: bool = True
    required_recipe_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError('promotion policy key must not be empty')
        object.__setattr__(self, 'required_recipe_keys', tuple(self.required_recipe_keys))


@dataclass(frozen=True, slots=True)
class SemiconductorPromotionDecision:
    status: PromotionDecisionStatus
    policy_key: str
    provider: str
    qualification_id: str
    recipe_keys: tuple[str, ...]
    findings: tuple[PromotionFinding, ...]
    generated_at: str = field(default_factory=lambda: _utc_now().replace(microsecond=0).isoformat().replace('+00:00', 'Z'))

    def __post_init__(self) -> None:
        object.__setattr__(self, 'recipe_keys', tuple(self.recipe_keys))
        object.__setattr__(self, 'findings', tuple(self.findings))

    @property
    def promotable(self) -> bool:
        return self.status is PromotionDecisionStatus.PROMOTABLE

    @property
    def blocked(self) -> bool:
        return self.status is PromotionDecisionStatus.BLOCKED

    @property
    def pending(self) -> bool:
        return self.status is PromotionDecisionStatus.PENDING

    @property
    def next_actions(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.remediation for item in self.findings if item.remediation))

    def to_dict(self) -> dict[str, Any]:
        return {
            'status': self.status.value,
            'promotable': self.promotable,
            'policy_key': self.policy_key,
            'provider': self.provider,
            'qualification_id': self.qualification_id,
            'recipe_keys': self.recipe_keys,
            'generated_at': self.generated_at,
            'findings': [item.to_dict() for item in self.findings],
            'next_actions': self.next_actions,
        }


def assess_evidence_freshness(bundle: SemiconductorTargetEvidenceBundle, *, policy: EvidenceFreshnessPolicy = EvidenceFreshnessPolicy(), now: datetime | None = None) -> EvidenceFreshnessAssessment:
    current = (now or _utc_now()).astimezone(timezone.utc)
    try:
        captured = _parse_utc(bundle.captured_at)
    except (TypeError, ValueError) as exc:
        return EvidenceFreshnessAssessment(bundle.recipe_key, EvidenceFreshnessStatus.INVALID, bundle.captured_at, None, f'Invalid evidence timestamp: {exc}')
    age_hours = (current - captured).total_seconds() / 3600.0
    if age_hours < -(policy.max_future_skew_minutes / 60.0):
        return EvidenceFreshnessAssessment(bundle.recipe_key, EvidenceFreshnessStatus.FUTURE, bundle.captured_at, age_hours, 'Evidence capture time is materially in the future relative to the qualification clock.')
    if age_hours > policy.max_age_hours:
        return EvidenceFreshnessAssessment(bundle.recipe_key, EvidenceFreshnessStatus.STALE, bundle.captured_at, age_hours, f'Evidence age exceeds {policy.max_age_hours:g} hours.')
    return EvidenceFreshnessAssessment(bundle.recipe_key, EvidenceFreshnessStatus.CURRENT, bundle.captured_at, max(0.0, age_hours), 'Evidence is within the configured freshness window.')


def _resolve_artifact_path(artifact: TargetEvidenceArtifact, base_dir: str | Path | None) -> Path:
    path = Path(artifact.path)
    if not path.is_absolute() and base_dir is not None:
        path = Path(base_dir) / path
    return path


def verify_target_evidence_artifacts(bundle: SemiconductorTargetEvidenceBundle, *, base_dir: str | Path | None = None) -> tuple[ArtifactIntegrityFinding, ...]:
    findings: list[ArtifactIntegrityFinding] = []
    for artifact in bundle.artifacts:
        path = _resolve_artifact_path(artifact, base_dir)
        if not path.exists() or not path.is_file():
            findings.append(ArtifactIntegrityFinding(artifact.key, str(path), ArtifactIntegrityStatus.MISSING, 'Evidence artifact is not available at the recorded path.', artifact.sha256))
            continue
        try:
            observed = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            findings.append(ArtifactIntegrityFinding(artifact.key, str(path), ArtifactIntegrityStatus.INVALID, f'Unable to read evidence artifact: {exc}', artifact.sha256))
            continue
        status = ArtifactIntegrityStatus.VERIFIED if observed == artifact.sha256 else ArtifactIntegrityStatus.HASH_MISMATCH
        detail = 'Artifact hash matches the evidence bundle.' if status is ArtifactIntegrityStatus.VERIFIED else 'Artifact hash does not match the evidence bundle.'
        findings.append(ArtifactIntegrityFinding(artifact.key, str(path), status, detail, artifact.sha256, observed))
    return tuple(findings)


def _artifact_gate_keys(bundle: SemiconductorTargetEvidenceBundle) -> Mapping[str, tuple[str, ...]]:
    raw = bundle.metadata.get('gate_artifacts', {})
    if not isinstance(raw, Mapping):
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for key, value in raw.items():
        if isinstance(value, str):
            out[str(key)] = (value,)
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
            out[str(key)] = tuple(str(item) for item in value)
    return out


def _gate_is_traced(gate_key: str, bundle: SemiconductorTargetEvidenceBundle) -> bool:
    artifact_keys = {item.key for item in bundle.artifacts}
    mapped = _artifact_gate_keys(bundle).get(gate_key, ())
    if any(item in artifact_keys for item in mapped):
        return True
    return any(key == gate_key or key.startswith(f'{gate_key}:') or key.startswith(f'{gate_key}-') for key in artifact_keys)


def assess_target_evidence_traceability(bundle: SemiconductorTargetEvidenceBundle, *, policy: EvidenceFreshnessPolicy = EvidenceFreshnessPolicy(), base_dir: str | Path | None = None, now: datetime | None = None) -> EvidenceTraceabilityReport:
    freshness = assess_evidence_freshness(bundle, policy=policy, now=now)
    artifacts = verify_target_evidence_artifacts(bundle, base_dir=base_dir) if policy.require_artifact_integrity else ()
    untraced: list[str] = []
    if policy.require_external_gate_traceability:
        for gate in bundle.certification.gates:
            if gate.key in policy.external_gate_keys and gate.status is TargetGateStatus.PASS and not _gate_is_traced(gate.key, bundle):
                untraced.append(gate.key)
    return EvidenceTraceabilityReport(bundle.recipe_key, freshness, tuple(artifacts), tuple(untraced))


def _provider_from_bundle(bundle: SemiconductorTargetEvidenceBundle) -> str | None:
    for payload in (bundle.adapter_conformance, bundle.performance, bundle.benchmark):
        if isinstance(payload, Mapping) and payload.get('provider'):
            return str(payload['provider'])
    return None


def _source_from_bundle(bundle: SemiconductorTargetEvidenceBundle) -> str | None:
    for payload in (bundle.adapter_conformance, bundle.performance, bundle.benchmark):
        if isinstance(payload, Mapping) and payload.get('source_key'):
            return str(payload['source_key'])
    return None


SEMICONDUCTOR_PROMOTION_POLICIES: Mapping[str, PromotionPolicy] = MappingProxyType({'stable': PromotionPolicy()})
TARGET_EVIDENCE_FRESHNESS_POLICIES: Mapping[str, EvidenceFreshnessPolicy] = MappingProxyType({'stable': EvidenceFreshnessPolicy()})


def _timestamp_sort_key(value: str) -> datetime:
    try:
        return _parse_utc(value)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def build_provider_qualification_pack(
    bundles: Sequence[SemiconductorTargetEvidenceBundle], *, provider: str | None = None,
    freshness_policy: EvidenceFreshnessPolicy = EvidenceFreshnessPolicy(), base_dir: str | Path | None = None,
    now: datetime | None = None,
) -> ProviderQualificationPack:
    if not bundles:
        raise ValueError('provider qualification pack requires at least one target evidence bundle')
    latest: dict[str, SemiconductorTargetEvidenceBundle] = {}
    superseded = 0
    for bundle in bundles:
        previous = latest.get(bundle.recipe_key)
        if previous is None or _timestamp_sort_key(bundle.captured_at) >= _timestamp_sort_key(previous.captured_at):
            if previous is not None:
                superseded += 1
            latest[bundle.recipe_key] = bundle
        else:
            superseded += 1
    ordered = tuple(latest[key] for key in sorted(latest))
    observed_providers = {value for value in (_provider_from_bundle(item) for item in ordered) if value}
    if provider is None:
        if len(observed_providers) != 1:
            raise ValueError(f'provider qualification requires one explicit provider; observed {sorted(observed_providers)!r}')
        provider = next(iter(observed_providers))
    elif any(value != provider for value in observed_providers):
        raise ValueError(f'provider qualification evidence does not all belong to provider {provider!r}')
    traces = tuple(assess_target_evidence_traceability(item, policy=freshness_policy, base_dir=base_dir, now=now) for item in ordered)
    source_keys = tuple(sorted({value for value in (_source_from_bundle(item) for item in ordered) if value}))
    canonical = json.dumps({
        'provider': provider,
        'bundles': [{'recipe_key': item.recipe_key, 'captured_at': item.captured_at, 'gates': [(gate.key, gate.status.value) for gate in item.certification.gates], 'artifacts': [(a.key, a.sha256) for a in item.artifacts]} for item in ordered],
    }, sort_keys=True, separators=(',', ':')).encode('utf-8')
    qualification_id = hashlib.sha256(canonical).hexdigest()
    return ProviderQualificationPack(provider, ordered, traces, qualification_id, source_keys, superseded)


def build_semiconductor_promotion_decision(
    qualification: ProviderQualificationPack, *,
    operational_readiness: Mapping[str, SemiconductorOperationalReadiness] | None = None,
    policy: PromotionPolicy = PromotionPolicy(),
) -> SemiconductorPromotionDecision:
    findings: list[PromotionFinding] = []
    by_recipe = {item.recipe_key: item for item in qualification.bundles}
    if policy.required_recipe_keys:
        missing = tuple(key for key in policy.required_recipe_keys if key not in by_recipe)
        for key in missing:
            findings.append(PromotionFinding('missing_recipe_evidence', PromotionFindingSeverity.WARNING, f'Required recipe evidence is missing for {key}.', 'Capture a current target-evidence bundle for the required recipe.', key))
    if policy.require_consistent_environment:
        environments = {(item.environment.python_version, item.environment.nicegui_version) for item in qualification.bundles}
        if len(environments) > 1:
            findings.append(PromotionFinding('target_environment_mismatch', PromotionFindingSeverity.ERROR, 'Qualification bundles were captured against inconsistent Python/NiceGUI target environments.', 'Recapture qualification evidence against one approved target runtime version family.', metadata={'environments': tuple(sorted((str(a), str(b)) for a,b in environments))}))
    for bundle, trace in zip(qualification.bundles, qualification.traceability):
        if policy.require_framework_version_match:
            framework_version = bundle.metadata.get('framework_version')
            if framework_version is None:
                findings.append(PromotionFinding(
                    'framework_version_evidence_pending', PromotionFindingSeverity.WARNING,
                    'Target evidence does not identify the framework release that produced it.',
                    'Recapture target evidence with the current framework before stable promotion.',
                    bundle.recipe_key,
                    {'required_framework_version': FRAMEWORK_VERSION},
                ))
            elif str(framework_version) != FRAMEWORK_VERSION:
                findings.append(PromotionFinding(
                    'framework_version_mismatch', PromotionFindingSeverity.ERROR,
                    f'Target evidence was captured with framework {framework_version}, not the current {FRAMEWORK_VERSION}.',
                    'Recapture target evidence using the current framework release.',
                    bundle.recipe_key,
                    {'observed_framework_version': str(framework_version), 'required_framework_version': FRAMEWORK_VERSION},
                ))
        if policy.require_runtime_version_match:
            required_nicegui = bundle.metadata.get('nicegui_required')
            if required_nicegui is None:
                findings.append(PromotionFinding(
                    'runtime_contract_evidence_pending', PromotionFindingSeverity.WARNING,
                    'Target evidence does not identify the NiceGUI runtime contract that produced it.',
                    'Recapture target evidence with the current framework runtime contract before stable promotion.',
                    bundle.recipe_key,
                    {'required_nicegui_version': NICEGUI_VERSION},
                ))
            elif str(required_nicegui) != NICEGUI_VERSION:
                findings.append(PromotionFinding(
                    'runtime_contract_mismatch', PromotionFindingSeverity.ERROR,
                    f'Target evidence requires NiceGUI {required_nicegui}, not the current {NICEGUI_VERSION}.',
                    'Recapture target evidence using the current framework runtime contract.',
                    bundle.recipe_key,
                    {'observed_nicegui_required': str(required_nicegui), 'required_nicegui_version': NICEGUI_VERSION},
                ))
            installed_gate = next((gate for gate in bundle.certification.gates if gate.key == 'installed_nicegui'), None)
            if installed_gate is not None and installed_gate.status is TargetGateStatus.PASS and bundle.environment.nicegui_version != NICEGUI_VERSION:
                findings.append(PromotionFinding(
                    'installed_nicegui_version_mismatch', PromotionFindingSeverity.ERROR,
                    f'Installed NiceGUI evidence reports {bundle.environment.nicegui_version!r}, not required {NICEGUI_VERSION}.',
                    'Re-run installed NiceGUI certification against the exact framework-required runtime version.',
                    bundle.recipe_key,
                    {'observed_nicegui_version': bundle.environment.nicegui_version, 'required_nicegui_version': NICEGUI_VERSION},
                ))
        if policy.require_all_target_gates:
            for gate in bundle.certification.failed:
                findings.append(PromotionFinding('target_gate_failed', PromotionFindingSeverity.ERROR, f'Target gate {gate.label} failed.', f'Resolve and recapture target gate: {gate.label}.', bundle.recipe_key, {'gate': gate.key}))
            for gate in bundle.certification.pending:
                findings.append(PromotionFinding('target_gate_pending', PromotionFindingSeverity.WARNING, f'Target gate {gate.label} is pending.', f'Complete target gate: {gate.label}.', bundle.recipe_key, {'gate': gate.key}))
        if policy.require_traceable_current_evidence:
            if trace.corrupt:
                findings.append(PromotionFinding('evidence_integrity_failed', PromotionFindingSeverity.ERROR, 'Evidence traceability/integrity is invalid.', 'Recapture the affected evidence and verify hashes/timestamps.', bundle.recipe_key))
            elif trace.pending:
                findings.append(PromotionFinding('evidence_traceability_pending', PromotionFindingSeverity.WARNING, 'Evidence is stale, missing, or not linked to required passed gates.', 'Refresh evidence and attach/hash artifacts for passed external gates.', bundle.recipe_key, {'untraced_pass_gates': trace.untraced_pass_gates}))
        if policy.require_operational_release_ready:
            report = operational_readiness.get(bundle.recipe_key) if operational_readiness is not None else None
            if report is None:
                findings.append(PromotionFinding('operational_readiness_pending', PromotionFindingSeverity.WARNING, 'Operational readiness evidence is not attached.', 'Assess operational readiness and attach the report before promotion.', bundle.recipe_key))
            elif report.provider != qualification.provider or (_source_from_bundle(bundle) is not None and report.source_key != _source_from_bundle(bundle)):
                findings.append(PromotionFinding('operational_evidence_mismatch', PromotionFindingSeverity.ERROR, 'Operational readiness evidence does not match the qualified provider/source.', 'Reassess operational readiness against the same provider/source represented in target evidence.', bundle.recipe_key, {'operational_provider': report.provider, 'operational_source': report.source_key, 'qualified_provider': qualification.provider, 'qualified_source': _source_from_bundle(bundle)}))
            elif report.state is OperationalReadinessState.BLOCKED:
                findings.append(PromotionFinding('operational_readiness_blocked', PromotionFindingSeverity.ERROR, 'Operational readiness is blocked.', 'Resolve blocking operational readiness checks.', bundle.recipe_key))
            elif not report.ready_for_release:
                findings.append(PromotionFinding('operational_readiness_pending', PromotionFindingSeverity.WARNING, f'Operational readiness is {report.state.value}.', 'Complete pending/degraded operational readiness checks.', bundle.recipe_key))
    if any(item.severity is PromotionFindingSeverity.ERROR for item in findings):
        status = PromotionDecisionStatus.BLOCKED
    elif findings:
        status = PromotionDecisionStatus.PENDING
    else:
        status = PromotionDecisionStatus.PROMOTABLE
        findings.append(PromotionFinding('stable_promotion_ready', PromotionFindingSeverity.INFO, 'All required target, traceability and operational readiness gates are satisfied.'))
    return SemiconductorPromotionDecision(status, policy.key, qualification.provider, qualification.qualification_id, qualification.recipe_keys, tuple(findings))


def provider_qualification_pack_to_dict(pack: ProviderQualificationPack) -> dict[str, Any]:
    return pack.to_dict()


def provider_qualification_pack_from_dict(payload: Mapping[str, Any]) -> ProviderQualificationPack:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported provider qualification pack schema {payload.get("schema_version")!r}')
    bundles_payload = payload.get('bundles')
    if not isinstance(bundles_payload, list):
        raise TypeError('provider qualification pack bundles must be a list')
    bundles = tuple(target_evidence_bundle_from_dict(item) for item in bundles_payload)
    pack = build_provider_qualification_pack(bundles, provider=str(payload['provider']), freshness_policy=EvidenceFreshnessPolicy(require_artifact_integrity=False, require_external_gate_traceability=False))
    if str(payload.get('qualification_id')) != pack.qualification_id:
        raise ValueError('provider qualification pack qualification_id does not match its evidence payload')
    trace_payload = payload.get('traceability')
    traces = pack.traceability
    if isinstance(trace_payload, list):
        parsed: list[EvidenceTraceabilityReport] = []
        for item in trace_payload:
            fresh = item.get('freshness', {})
            freshness = EvidenceFreshnessAssessment(
                str(item.get('recipe_key', fresh.get('recipe_key',''))), EvidenceFreshnessStatus(str(fresh['status'])),
                str(fresh.get('captured_at','')), None if fresh.get('age_hours') is None else float(fresh['age_hours']), str(fresh.get('detail','')),
            )
            artifacts = tuple(ArtifactIntegrityFinding(
                str(a['key']), str(a['path']), ArtifactIntegrityStatus(str(a['status'])), str(a.get('detail','')),
                str(a['expected_sha256']), None if a.get('observed_sha256') is None else str(a['observed_sha256']),
            ) for a in item.get('artifacts', ()))
            parsed.append(EvidenceTraceabilityReport(str(item['recipe_key']), freshness, artifacts, tuple(item.get('untraced_pass_gates', ()))))
        if len(parsed) == len(bundles):
            traces = tuple(parsed)
    return ProviderQualificationPack(pack.provider, pack.bundles, traces, pack.qualification_id, tuple(payload.get('source_keys', pack.source_keys)), int(payload.get('superseded_bundles', 0)), str(payload.get('generated_at') or pack.generated_at))


def write_provider_qualification_pack(path: str | Path, pack: ProviderQualificationPack) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(pack.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_provider_qualification_pack(path: str | Path) -> ProviderQualificationPack:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('provider qualification JSON must contain an object')
    return provider_qualification_pack_from_dict(payload)


__all__ = [
    'ArtifactIntegrityFinding','ArtifactIntegrityStatus','EvidenceFreshnessAssessment','EvidenceFreshnessPolicy','EvidenceFreshnessStatus',
    'EvidenceTraceabilityReport','PromotionDecisionStatus','PromotionFinding','PromotionFindingSeverity','PromotionPolicy',
    'ProviderQualificationPack','SEMICONDUCTOR_PROMOTION_POLICIES','TARGET_EVIDENCE_FRESHNESS_POLICIES','SemiconductorPromotionDecision','assess_evidence_freshness','assess_target_evidence_traceability',
    'build_provider_qualification_pack','build_semiconductor_promotion_decision','provider_qualification_pack_from_dict',
    'provider_qualification_pack_to_dict','read_provider_qualification_pack','verify_target_evidence_artifacts','write_provider_qualification_pack',
]
