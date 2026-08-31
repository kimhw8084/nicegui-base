from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from nicegui_base.semiconductor.operational_readiness import (
    SEMICONDUCTOR_OPERATIONAL_RUNBOOKS,
    OperationalReadinessState,
    SemiconductorOperationalReadiness,
    operational_readiness_from_dict,
)
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

from .semiconductor_evidence import (
    SemiconductorTargetEvidenceBundle,
    TargetEvidenceArtifact,
    read_semiconductor_target_evidence,
    target_evidence_bundle_from_dict,
    target_evidence_bundle_to_dict,
)
from .semiconductor_orchestrator import (
    EvidenceFreshnessPolicy,
    PromotionDecisionStatus,
    PromotionFinding,
    PromotionFindingSeverity,
    PromotionPolicy,
    ProviderQualificationPack,
    SemiconductorPromotionDecision,
    build_provider_qualification_pack,
    build_semiconductor_promotion_decision,
    provider_qualification_pack_from_dict,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _without_generated_at(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result.pop('generated_at', None)
    return result


class PromotionCandidateStatus(str, Enum):
    READY = 'ready'
    PENDING = 'pending'
    BLOCKED = 'blocked'


class PromotionRehearsalKind(str, Enum):
    PROMOTION = 'promotion'
    ROLLBACK = 'rollback'
    INCIDENT = 'incident'
    EVIDENCE_CAPTURE = 'evidence-capture'


class PromotionRehearsalStatus(str, Enum):
    PASS = 'pass'
    PENDING = 'pending'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class ReleaseChannelPolicy:
    key: str = 'stable'
    target_version: str = '3.0.0'
    promotion_policy: PromotionPolicy = field(default_factory=PromotionPolicy)
    required_rehearsal_kinds: tuple[PromotionRehearsalKind, ...] = (
        PromotionRehearsalKind.PROMOTION,
        PromotionRehearsalKind.ROLLBACK,
        PromotionRehearsalKind.INCIDENT,
        PromotionRehearsalKind.EVIDENCE_CAPTURE,
    )

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.target_version.strip():
            raise ValueError('release channel key and target version must not be empty')
        object.__setattr__(self, 'required_rehearsal_kinds', tuple(PromotionRehearsalKind(item) for item in self.required_rehearsal_kinds))


SEMICONDUCTOR_RELEASE_CHANNEL_POLICIES: Mapping[str, ReleaseChannelPolicy] = MappingProxyType({'stable': ReleaseChannelPolicy()})


@dataclass(frozen=True, slots=True)
class PromotionCandidateGap:
    code: str
    severity: PromotionFindingSeverity
    category: str
    message: str
    remediation: str
    recipe_key: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.category.strip() or not self.message.strip():
            raise ValueError('promotion candidate gap code, category and message must not be empty')
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'code': self.code,
            'severity': self.severity.value,
            'category': self.category,
            'message': self.message,
            'remediation': self.remediation,
            'recipe_key': self.recipe_key,
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class EnterpriseTargetEvidenceSet:
    provider: str
    qualification: ProviderQualificationPack
    operational_readiness: tuple[SemiconductorOperationalReadiness, ...]
    decision: SemiconductorPromotionDecision
    evidence_set_id: str
    required_recipe_keys: tuple[str, ...] = ()
    promotion_policy: PromotionPolicy = field(default_factory=PromotionPolicy)
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.provider.strip() or len(self.evidence_set_id) != 64:
            raise ValueError('enterprise evidence set requires provider and sha256 evidence_set_id')
        if self.qualification.provider != self.provider or self.decision.provider != self.provider:
            raise ValueError('enterprise evidence set provider must match qualification and decision')
        if self.decision.qualification_id != self.qualification.qualification_id:
            raise ValueError('enterprise evidence set decision must reference its qualification')
        object.__setattr__(self, 'operational_readiness', tuple(self.operational_readiness))
        object.__setattr__(self, 'required_recipe_keys', tuple(self.required_recipe_keys))
        if self.promotion_policy.key != self.decision.policy_key or tuple(self.promotion_policy.required_recipe_keys) != self.required_recipe_keys:
            raise ValueError('enterprise evidence set promotion policy must match persisted decision/required recipes')
        keys = [item.recipe_key for item in self.operational_readiness]
        if len(keys) != len(set(keys)):
            raise ValueError('enterprise evidence set contains duplicate operational readiness recipes')

    @property
    def recipe_keys(self) -> tuple[str, ...]:
        return self.qualification.recipe_keys

    @property
    def status(self) -> PromotionDecisionStatus:
        return self.decision.status

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1,
            'provider': self.provider,
            'evidence_set_id': self.evidence_set_id,
            'generated_at': self.generated_at,
            'required_recipe_keys': self.required_recipe_keys,
            'promotion_policy': _promotion_policy_to_dict(self.promotion_policy),
            'qualification': self.qualification.to_dict(),
            'operational_readiness': [item.to_dict() for item in self.operational_readiness],
            'decision': self.decision.to_dict(),
        }


_REHEARSAL_STEP_KEYS: Mapping[PromotionRehearsalKind, tuple[str, ...]] = MappingProxyType({
    PromotionRehearsalKind.PROMOTION: ('startup', 'release-evidence', 'rollback'),
    PromotionRehearsalKind.ROLLBACK: ('rollback', 'startup'),
    PromotionRehearsalKind.INCIDENT: ('incident', 'provider-failure', 'release-evidence'),
    PromotionRehearsalKind.EVIDENCE_CAPTURE: ('release-evidence',),
})


@dataclass(frozen=True, slots=True)
class PromotionRehearsalReport:
    recipe_key: str
    kind: PromotionRehearsalKind
    required_step_keys: tuple[str, ...]
    completed_step_keys: tuple[str, ...] = ()
    failed_step_keys: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.recipe_key.strip():
            raise ValueError('rehearsal recipe_key must not be empty')
        object.__setattr__(self, 'kind', PromotionRehearsalKind(self.kind))
        object.__setattr__(self, 'required_step_keys', tuple(self.required_step_keys))
        object.__setattr__(self, 'completed_step_keys', tuple(dict.fromkeys(self.completed_step_keys)))
        object.__setattr__(self, 'failed_step_keys', tuple(dict.fromkeys(self.failed_step_keys)))
        object.__setattr__(self, 'notes', tuple(self.notes))
        allowed = set(self.required_step_keys)
        if not allowed or not set(self.completed_step_keys).issubset(allowed) or not set(self.failed_step_keys).issubset(allowed):
            raise ValueError('rehearsal completion/failure keys must belong to required steps')
        if set(self.completed_step_keys) & set(self.failed_step_keys):
            raise ValueError('a rehearsal step cannot be both completed and failed')

    @property
    def status(self) -> PromotionRehearsalStatus:
        if self.failed_step_keys:
            return PromotionRehearsalStatus.BLOCKED
        if set(self.required_step_keys).issubset(self.completed_step_keys):
            return PromotionRehearsalStatus.PASS
        return PromotionRehearsalStatus.PENDING

    @property
    def remaining_step_keys(self) -> tuple[str, ...]:
        done = set(self.completed_step_keys) | set(self.failed_step_keys)
        return tuple(key for key in self.required_step_keys if key not in done)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1,
            'recipe_key': self.recipe_key,
            'kind': self.kind.value,
            'status': self.status.value,
            'required_step_keys': self.required_step_keys,
            'completed_step_keys': self.completed_step_keys,
            'failed_step_keys': self.failed_step_keys,
            'remaining_step_keys': self.remaining_step_keys,
            'notes': self.notes,
            'generated_at': self.generated_at,
            'affects_target_gate_status': False,
        }


@dataclass(frozen=True, slots=True)
class StablePromotionCandidate:
    candidate_id: str
    channel: str
    target_version: str
    framework_version: str
    nicegui_required: str
    evidence: EnterpriseTargetEvidenceSet
    rehearsals: tuple[PromotionRehearsalReport, ...] = ()
    generated_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if len(self.candidate_id) != 64 or not self.channel.strip() or not self.target_version.strip():
            raise ValueError('stable promotion candidate requires sha256 id, channel and target version')
        if self.framework_version != FRAMEWORK_VERSION or self.nicegui_required != NICEGUI_VERSION:
            raise ValueError('candidate framework/runtime identity must match current release authority')
        object.__setattr__(self, 'rehearsals', tuple(self.rehearsals))
        keys = [(item.recipe_key, item.kind.value) for item in self.rehearsals]
        if len(keys) != len(set(keys)):
            raise ValueError('candidate contains duplicate rehearsal reports')

    @property
    def policy(self) -> ReleaseChannelPolicy:
        try:
            return SEMICONDUCTOR_RELEASE_CHANNEL_POLICIES[self.channel]
        except KeyError as exc:
            raise KeyError(f'unknown release channel {self.channel!r}') from exc

    @property
    def status(self) -> PromotionCandidateStatus:
        if self.evidence.decision.blocked or any(item.status is PromotionRehearsalStatus.BLOCKED for item in self.rehearsals):
            return PromotionCandidateStatus.BLOCKED
        if not self.evidence.decision.promotable:
            return PromotionCandidateStatus.PENDING
        report_map = {(item.recipe_key, item.kind): item for item in self.rehearsals}
        for recipe in self.evidence.recipe_keys:
            for kind in self.policy.required_rehearsal_kinds:
                report = report_map.get((recipe, kind))
                if report is None or report.status is not PromotionRehearsalStatus.PASS:
                    return PromotionCandidateStatus.PENDING
        return PromotionCandidateStatus.READY

    @property
    def release_channel_ready(self) -> bool:
        return self.status is PromotionCandidateStatus.READY

    @property
    def gaps(self) -> tuple[PromotionCandidateGap, ...]:
        return promotion_candidate_gaps(self)

    @property
    def next_actions(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.remediation for item in self.gaps if item.remediation))

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1,
            'candidate_id': self.candidate_id,
            'channel': self.channel,
            'target_version': self.target_version,
            'framework_version': self.framework_version,
            'nicegui_required': self.nicegui_required,
            'status': self.status.value,
            'release_channel_ready': self.release_channel_ready,
            'generated_at': self.generated_at,
            'evidence': self.evidence.to_dict(),
            'rehearsals': [item.to_dict() for item in self.rehearsals],
            'gaps': [item.to_dict() for item in self.gaps],
            'next_actions': self.next_actions,
        }


@dataclass(frozen=True, slots=True)
class PromotionCandidatePackage:
    path: str
    sha256: str
    candidate_id: str
    status: PromotionCandidateStatus
    entries: tuple[str, ...]
    included_artifacts: tuple[str, ...] = ()
    omitted_artifacts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or len(self.candidate_id) != 64:
            raise ValueError('candidate package requires sha256 package/candidate identifiers')
        object.__setattr__(self, 'entries', tuple(self.entries))
        object.__setattr__(self, 'included_artifacts', tuple(self.included_artifacts))
        object.__setattr__(self, 'omitted_artifacts', tuple(self.omitted_artifacts))

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': self.path,
            'sha256': self.sha256,
            'candidate_id': self.candidate_id,
            'status': self.status.value,
            'entries': self.entries,
            'included_artifacts': self.included_artifacts,
            'omitted_artifacts': self.omitted_artifacts,
        }


def _promotion_policy_to_dict(policy: PromotionPolicy) -> dict[str, Any]:
    return {
        'key': policy.key,
        'require_all_target_gates': policy.require_all_target_gates,
        'require_traceable_current_evidence': policy.require_traceable_current_evidence,
        'require_operational_release_ready': policy.require_operational_release_ready,
        'require_consistent_environment': policy.require_consistent_environment,
        'require_framework_version_match': policy.require_framework_version_match,
        'require_runtime_version_match': policy.require_runtime_version_match,
        'required_recipe_keys': policy.required_recipe_keys,
    }


def _promotion_policy_from_dict(payload: Mapping[str, Any]) -> PromotionPolicy:
    return PromotionPolicy(
        key=str(payload.get('key', 'stable')),
        require_all_target_gates=bool(payload.get('require_all_target_gates', True)),
        require_traceable_current_evidence=bool(payload.get('require_traceable_current_evidence', True)),
        require_operational_release_ready=bool(payload.get('require_operational_release_ready', True)),
        require_consistent_environment=bool(payload.get('require_consistent_environment', True)),
        require_framework_version_match=bool(payload.get('require_framework_version_match', True)),
        require_runtime_version_match=bool(payload.get('require_runtime_version_match', True)),
        required_recipe_keys=tuple(payload.get('required_recipe_keys', ())),
    )


def _decision_from_dict(payload: Mapping[str, Any]) -> SemiconductorPromotionDecision:
    findings_payload = payload.get('findings')
    if not isinstance(findings_payload, list):
        raise TypeError('promotion decision findings must be a list')
    findings = tuple(PromotionFinding(
        str(item['code']), PromotionFindingSeverity(str(item['severity'])), str(item['message']),
        str(item.get('remediation', '')), None if item.get('recipe_key') is None else str(item['recipe_key']), item.get('metadata', {}),
    ) for item in findings_payload)
    return SemiconductorPromotionDecision(
        PromotionDecisionStatus(str(payload['status'])), str(payload['policy_key']), str(payload['provider']),
        str(payload['qualification_id']), tuple(payload.get('recipe_keys', ())), findings, str(payload.get('generated_at') or _utc_now()),
    )


def assimilate_enterprise_target_evidence(
    bundles: Sequence[SemiconductorTargetEvidenceBundle], *,
    operational_readiness: Sequence[SemiconductorOperationalReadiness] | Mapping[str, SemiconductorOperationalReadiness] = (),
    provider: str | None = None,
    required_recipe_keys: Sequence[str] = (),
    freshness_policy: EvidenceFreshnessPolicy = EvidenceFreshnessPolicy(),
    promotion_policy: PromotionPolicy | None = None,
    base_dir: str | Path | None = None,
    now: datetime | None = None,
) -> EnterpriseTargetEvidenceSet:
    qualification = build_provider_qualification_pack(bundles, provider=provider, freshness_policy=freshness_policy, base_dir=base_dir, now=now)
    if isinstance(operational_readiness, Mapping):
        operational_map = dict(operational_readiness)
    else:
        operational_map: dict[str, SemiconductorOperationalReadiness] = {}
        for report in operational_readiness:
            if report.recipe_key in operational_map:
                raise ValueError(f'duplicate operational readiness report for recipe {report.recipe_key!r}')
            operational_map[report.recipe_key] = report
    for key, report in operational_map.items():
        if key != report.recipe_key:
            raise ValueError(f'operational readiness mapping key {key!r} does not match report recipe {report.recipe_key!r}')
    required = tuple(dict.fromkeys(str(item) for item in required_recipe_keys))
    policy = promotion_policy or PromotionPolicy(required_recipe_keys=required)
    if promotion_policy is not None and required and tuple(promotion_policy.required_recipe_keys) != required:
        raise ValueError('required_recipe_keys must agree with explicit promotion_policy')
    decision = build_semiconductor_promotion_decision(qualification, operational_readiness=operational_map or None, policy=policy)
    ordered_ops = tuple(operational_map[key] for key in sorted(operational_map))
    canonical = {
        'provider': qualification.provider,
        'qualification_id': qualification.qualification_id,
        'required_recipe_keys': tuple(policy.required_recipe_keys),
        'policy': _promotion_policy_to_dict(policy),
        'operational_readiness': [_without_generated_at(item.to_dict()) for item in ordered_ops],
    }
    evidence_set_id = _canonical_digest(canonical)
    return EnterpriseTargetEvidenceSet(qualification.provider, qualification, ordered_ops, decision, evidence_set_id, tuple(policy.required_recipe_keys), policy)


def load_enterprise_target_evidence(
    evidence_paths: Sequence[str | Path], *,
    operational_readiness_paths: Sequence[str | Path] = (),
    provider: str | None = None,
    required_recipe_keys: Sequence[str] = (),
    freshness_policy: EvidenceFreshnessPolicy = EvidenceFreshnessPolicy(),
    base_dir: str | Path | None = None,
    now: datetime | None = None,
) -> EnterpriseTargetEvidenceSet:
    bundles = tuple(read_semiconductor_target_evidence(path) for path in evidence_paths)
    readiness: list[SemiconductorOperationalReadiness] = []
    for path in operational_readiness_paths:
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(payload, Mapping):
            raise TypeError('operational readiness JSON must contain an object')
        readiness.append(operational_readiness_from_dict(payload))
    return assimilate_enterprise_target_evidence(
        bundles, operational_readiness=readiness, provider=provider, required_recipe_keys=required_recipe_keys,
        freshness_policy=freshness_policy, base_dir=base_dir, now=now,
    )


def enterprise_target_evidence_set_from_dict(payload: Mapping[str, Any]) -> EnterpriseTargetEvidenceSet:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported enterprise target evidence set schema {payload.get("schema_version")!r}')
    qualification_payload = payload.get('qualification')
    decision_payload = payload.get('decision')
    readiness_payload = payload.get('operational_readiness')
    if not isinstance(qualification_payload, Mapping) or not isinstance(decision_payload, Mapping) or not isinstance(readiness_payload, list):
        raise TypeError('enterprise evidence set requires qualification, decision and operational_readiness')
    qualification = provider_qualification_pack_from_dict(qualification_payload)
    readiness = tuple(operational_readiness_from_dict(item) for item in readiness_payload)
    decision = _decision_from_dict(decision_payload)
    required = tuple(payload.get('required_recipe_keys', ()))
    policy_payload = payload.get('promotion_policy')
    policy = _promotion_policy_from_dict(policy_payload) if isinstance(policy_payload, Mapping) else PromotionPolicy(required_recipe_keys=required)
    item = EnterpriseTargetEvidenceSet(
        str(payload['provider']), qualification, readiness, decision, str(payload['evidence_set_id']),
        required, policy, str(payload.get('generated_at') or _utc_now()),
    )
    canonical = {
        'provider': item.qualification.provider,
        'qualification_id': item.qualification.qualification_id,
        'required_recipe_keys': item.required_recipe_keys,
        'policy': _promotion_policy_to_dict(item.promotion_policy),
        'operational_readiness': [_without_generated_at(report.to_dict()) for report in item.operational_readiness],
    }
    if _canonical_digest(canonical) != item.evidence_set_id:
        raise ValueError('enterprise evidence set id does not match persisted evidence payload')
    return item


def write_enterprise_target_evidence_set(path: str | Path, evidence: EnterpriseTargetEvidenceSet) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_enterprise_target_evidence_set(path: str | Path) -> EnterpriseTargetEvidenceSet:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('enterprise evidence set JSON must contain an object')
    return enterprise_target_evidence_set_from_dict(payload)


def build_promotion_rehearsal(
    recipe_key: str, kind: PromotionRehearsalKind | str, *,
    completed_step_keys: Sequence[str] = (), failed_step_keys: Sequence[str] = (), notes: Sequence[str] = (),
) -> PromotionRehearsalReport:
    if recipe_key not in SEMICONDUCTOR_OPERATIONAL_RUNBOOKS:
        raise KeyError(f'unknown semiconductor recipe {recipe_key!r}')
    resolved_kind = PromotionRehearsalKind(kind)
    runbook = SEMICONDUCTOR_OPERATIONAL_RUNBOOKS[recipe_key]
    available = {step.key for step in runbook.steps}
    required = _REHEARSAL_STEP_KEYS[resolved_kind]
    if not set(required).issubset(available):
        raise RuntimeError(f'operational runbook {recipe_key!r} does not support rehearsal {resolved_kind.value!r}')
    return PromotionRehearsalReport(recipe_key, resolved_kind, required, tuple(completed_step_keys), tuple(failed_step_keys), tuple(notes))


def promotion_rehearsal_from_dict(payload: Mapping[str, Any]) -> PromotionRehearsalReport:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported promotion rehearsal schema {payload.get("schema_version")!r}')
    report = PromotionRehearsalReport(
        str(payload['recipe_key']), PromotionRehearsalKind(str(payload['kind'])), tuple(payload.get('required_step_keys', ())),
        tuple(payload.get('completed_step_keys', ())), tuple(payload.get('failed_step_keys', ())), tuple(payload.get('notes', ())),
        str(payload.get('generated_at') or _utc_now()),
    )
    if payload.get('status') is not None and str(payload['status']) != report.status.value:
        raise ValueError('persisted promotion rehearsal status does not match step results')
    return report


def write_promotion_rehearsal(path: str | Path, report: PromotionRehearsalReport) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_promotion_rehearsal(path: str | Path) -> PromotionRehearsalReport:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('promotion rehearsal JSON must contain an object')
    return promotion_rehearsal_from_dict(payload)


def build_stable_promotion_candidate(
    evidence: EnterpriseTargetEvidenceSet, *, rehearsals: Sequence[PromotionRehearsalReport] = (),
    channel: str = 'stable', target_version: str | None = None,
) -> StablePromotionCandidate:
    try:
        policy = SEMICONDUCTOR_RELEASE_CHANNEL_POLICIES[channel]
    except KeyError as exc:
        raise KeyError(f'unknown release channel {channel!r}') from exc
    version = target_version or policy.target_version
    rehearsal_tuple = tuple(sorted(rehearsals, key=lambda item: (item.recipe_key, item.kind.value)))
    allowed_recipes = set(evidence.recipe_keys)
    if any(item.recipe_key not in allowed_recipes for item in rehearsal_tuple):
        raise ValueError('promotion rehearsal recipe must belong to the candidate evidence set')
    canonical = {
        'channel': channel,
        'target_version': version,
        'framework_version': FRAMEWORK_VERSION,
        'nicegui_required': NICEGUI_VERSION,
        'evidence_set_id': evidence.evidence_set_id,
        'rehearsals': [_without_generated_at(item.to_dict()) for item in rehearsal_tuple],
    }
    candidate_id = _canonical_digest(canonical)
    return StablePromotionCandidate(candidate_id, channel, version, FRAMEWORK_VERSION, NICEGUI_VERSION, evidence, rehearsal_tuple)


def with_promotion_rehearsal(candidate: StablePromotionCandidate, report: PromotionRehearsalReport) -> StablePromotionCandidate:
    reports = {(item.recipe_key, item.kind): item for item in candidate.rehearsals}
    reports[(report.recipe_key, report.kind)] = report
    return build_stable_promotion_candidate(candidate.evidence, rehearsals=tuple(reports.values()), channel=candidate.channel, target_version=candidate.target_version)


def promotion_candidate_gaps(candidate: StablePromotionCandidate) -> tuple[PromotionCandidateGap, ...]:
    gaps: list[PromotionCandidateGap] = []
    for finding in candidate.evidence.decision.findings:
        if finding.code == 'stable_promotion_ready':
            continue
        category = 'target-evidence'
        if finding.code.startswith('operational_'):
            category = 'operational-readiness'
        elif 'version' in finding.code or 'runtime_contract' in finding.code:
            category = 'runtime-identity'
        elif 'traceability' in finding.code or 'integrity' in finding.code:
            category = 'traceability'
        gaps.append(PromotionCandidateGap(
            finding.code, finding.severity, category, finding.message, finding.remediation, finding.recipe_key, finding.metadata,
        ))
    reports = {(item.recipe_key, item.kind): item for item in candidate.rehearsals}
    for recipe in candidate.evidence.recipe_keys:
        for kind in candidate.policy.required_rehearsal_kinds:
            report = reports.get((recipe, kind))
            if report is None:
                gaps.append(PromotionCandidateGap(
                    'promotion_rehearsal_missing', PromotionFindingSeverity.WARNING, 'operational-rehearsal',
                    f'{kind.value} rehearsal is not recorded for {recipe}.',
                    f'Rehearse and record the {kind.value} workflow using the canonical operational runbook.', recipe, {'kind': kind.value},
                ))
            elif report.status is PromotionRehearsalStatus.BLOCKED:
                gaps.append(PromotionCandidateGap(
                    'promotion_rehearsal_failed', PromotionFindingSeverity.ERROR, 'operational-rehearsal',
                    f'{kind.value} rehearsal has failed steps for {recipe}.',
                    'Resolve the failed rehearsal steps and record a new rehearsal result; this does not change target gate evidence.',
                    recipe, {'kind': kind.value, 'failed_step_keys': report.failed_step_keys},
                ))
            elif report.status is PromotionRehearsalStatus.PENDING:
                gaps.append(PromotionCandidateGap(
                    'promotion_rehearsal_incomplete', PromotionFindingSeverity.WARNING, 'operational-rehearsal',
                    f'{kind.value} rehearsal is incomplete for {recipe}.',
                    'Complete the remaining canonical runbook rehearsal steps and record the result.',
                    recipe, {'kind': kind.value, 'remaining_step_keys': report.remaining_step_keys},
                ))
    order = {PromotionFindingSeverity.ERROR: 0, PromotionFindingSeverity.WARNING: 1, PromotionFindingSeverity.INFO: 2}
    return tuple(sorted(gaps, key=lambda item: (order[item.severity], item.category, item.recipe_key or '', item.code, item.message)))


def promotion_candidate_from_dict(payload: Mapping[str, Any]) -> StablePromotionCandidate:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported stable promotion candidate schema {payload.get("schema_version")!r}')
    evidence_payload = payload.get('evidence')
    rehearsal_payload = payload.get('rehearsals')
    if not isinstance(evidence_payload, Mapping) or not isinstance(rehearsal_payload, list):
        raise TypeError('promotion candidate requires evidence and rehearsal list')
    evidence = enterprise_target_evidence_set_from_dict(evidence_payload)
    rehearsals = tuple(promotion_rehearsal_from_dict(item) for item in rehearsal_payload)
    rebuilt = build_stable_promotion_candidate(
        evidence, rehearsals=rehearsals, channel=str(payload['channel']), target_version=str(payload['target_version']),
    )
    if str(payload.get('candidate_id')) != rebuilt.candidate_id:
        raise ValueError('promotion candidate id does not match persisted evidence/rehearsal payload')
    if str(payload.get('framework_version')) != FRAMEWORK_VERSION or str(payload.get('nicegui_required')) != NICEGUI_VERSION:
        raise ValueError('promotion candidate framework/runtime identity does not match current release authority')
    return replace(rebuilt, generated_at=str(payload.get('generated_at') or rebuilt.generated_at))


def write_promotion_candidate(path: str | Path, candidate: StablePromotionCandidate) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(candidate.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_promotion_candidate(path: str | Path) -> StablePromotionCandidate:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('promotion candidate JSON must contain an object')
    return promotion_candidate_from_dict(payload)


def _safe_entry_component(value: str) -> str:
    raw = str(value)
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', raw).strip('._') or 'item'
    cleaned = cleaned[:80]
    if cleaned != raw:
        cleaned = f'{cleaned}-{hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]}'
    return cleaned


def _resolve_artifact_path(artifact: TargetEvidenceArtifact, base_dir: str | Path | None) -> Path:
    path = Path(artifact.path)
    if path.is_absolute() or base_dir is None:
        return path
    return Path(base_dir) / path


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def package_stable_promotion_candidate(
    path: str | Path, candidate: StablePromotionCandidate, *, artifact_base_dir: str | Path | None = None,
    include_verified_artifacts: bool = True,
) -> PromotionCandidatePackage:
    target = Path(path)
    if target.suffix.lower() != '.zip':
        target = target.with_suffix('.zip')
    target.parent.mkdir(parents=True, exist_ok=True)
    entries: dict[str, bytes] = {}
    entries['candidate.json'] = _json_bytes(candidate.to_dict())
    entries['evidence/enterprise_evidence_set.json'] = _json_bytes(candidate.evidence.to_dict())
    entries['evidence/provider_qualification.json'] = _json_bytes(candidate.evidence.qualification.to_dict())
    entries['evidence/promotion_decision.json'] = _json_bytes(candidate.evidence.decision.to_dict())
    entries['diagnostics/promotion_gaps.json'] = _json_bytes({'candidate_id': candidate.candidate_id, 'status': candidate.status.value, 'gaps': [item.to_dict() for item in candidate.gaps], 'next_actions': candidate.next_actions})
    for bundle in candidate.evidence.qualification.bundles:
        entries[f'evidence/target/{_safe_entry_component(bundle.recipe_key)}.json'] = _json_bytes(target_evidence_bundle_to_dict(bundle))
    for report in candidate.evidence.operational_readiness:
        entries[f'evidence/operational/{_safe_entry_component(report.recipe_key)}.json'] = _json_bytes(report.to_dict())
    for report in candidate.rehearsals:
        entries[f'rehearsals/{_safe_entry_component(report.recipe_key)}/{report.kind.value}.json'] = _json_bytes(report.to_dict())
    for recipe in candidate.evidence.recipe_keys:
        runbook = SEMICONDUCTOR_OPERATIONAL_RUNBOOKS.get(recipe)
        if runbook is not None:
            entries[f'runbooks/{_safe_entry_component(recipe)}.json'] = _json_bytes(runbook.to_dict())
    included_artifacts: list[str] = []
    omitted_artifacts: list[str] = []
    if include_verified_artifacts:
        for bundle, trace in zip(candidate.evidence.qualification.bundles, candidate.evidence.qualification.traceability):
            integrity = {item.key: item for item in trace.artifacts}
            for artifact in bundle.artifacts:
                finding = integrity.get(artifact.key)
                source = _resolve_artifact_path(artifact, artifact_base_dir)
                if finding is None or finding.status.value != 'verified' or not source.is_file():
                    omitted_artifacts.append(f'{bundle.recipe_key}:{artifact.key}')
                    continue
                data = source.read_bytes()
                observed = hashlib.sha256(data).hexdigest()
                if observed != artifact.sha256:
                    omitted_artifacts.append(f'{bundle.recipe_key}:{artifact.key}')
                    continue
                safe_name = _safe_entry_component(Path(artifact.path).name or artifact.key)
                safe_recipe = _safe_entry_component(bundle.recipe_key)
                safe_key = _safe_entry_component(artifact.key)
                entry_name = f'artifacts/{safe_recipe}/{safe_key}__{artifact.sha256[:12]}__{safe_name}'
                entries[entry_name] = data
                included_artifacts.append(f'{bundle.recipe_key}:{artifact.key}')
    readme = (
        f'# NiceGUI Base stable-promotion candidate\n\n'
        f'- Candidate: `{candidate.candidate_id}`\n'
        f'- Channel: `{candidate.channel}`\n'
        f'- Target version: `{candidate.target_version}`\n'
        f'- Candidate status: `{candidate.status.value}`\n'
        f'- Evidence decision: `{candidate.evidence.decision.status.value}`\n\n'
        'Packaging a candidate never changes target gate status. Missing, stale, untraced, failed, or unavailable enterprise evidence remains represented by the included decision and gap diagnostics.\n'
    )
    entries['README.md'] = readme.encode('utf-8')
    manifest_lines = [f'{hashlib.sha256(entries[name]).hexdigest()}  {name}' for name in sorted(entries)]
    entries['MANIFEST.sha256'] = ('\n'.join(manifest_lines) + '\n').encode('utf-8')
    fixed_time = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=fixed_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, entries[name])
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return PromotionCandidatePackage(str(target), digest, candidate.candidate_id, candidate.status, tuple(sorted(entries)), tuple(sorted(included_artifacts)), tuple(sorted(omitted_artifacts)))


__all__ = [
    'EnterpriseTargetEvidenceSet','PromotionCandidateGap','PromotionCandidatePackage','PromotionCandidateStatus',
    'PromotionRehearsalKind','PromotionRehearsalReport','PromotionRehearsalStatus','ReleaseChannelPolicy',
    'SEMICONDUCTOR_RELEASE_CHANNEL_POLICIES','StablePromotionCandidate','assimilate_enterprise_target_evidence',
    'build_promotion_rehearsal','build_stable_promotion_candidate','enterprise_target_evidence_set_from_dict',
    'load_enterprise_target_evidence','package_stable_promotion_candidate','promotion_candidate_from_dict',
    'promotion_candidate_gaps','promotion_rehearsal_from_dict','read_enterprise_target_evidence_set','read_promotion_candidate',
    'read_promotion_rehearsal','with_promotion_rehearsal','write_enterprise_target_evidence_set','write_promotion_candidate',
    'write_promotion_rehearsal',
]
