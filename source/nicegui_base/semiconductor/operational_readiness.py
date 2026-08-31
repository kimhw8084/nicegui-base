from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from nicegui_base.diagnostics import HealthReport, HealthState

from .benchmarking import SemiconductorBenchmarkReport
from .conformance import AdapterConformanceReport
from .operations import review_recipe_configuration
from .runtime_experience import RuntimeExperienceState, RuntimeExperienceStatus, RuntimePerformanceReport, build_runtime_experience_state


class OperationalReadinessState(str, Enum):
    READY = 'ready'
    DEGRADED = 'degraded'
    BLOCKED = 'blocked'
    PENDING = 'pending'


@dataclass(frozen=True, slots=True)
class OperationalReadinessCheck:
    key: str
    label: str
    state: OperationalReadinessState
    detail: str
    remediation: str = ''
    required_for_run: bool = False
    required_for_release: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip() or not self.detail.strip():
            raise ValueError('operational readiness check key, label and detail must not be empty')
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key,
            'label': self.label,
            'state': self.state.value,
            'detail': self.detail,
            'remediation': self.remediation,
            'required_for_run': self.required_for_run,
            'required_for_release': self.required_for_release,
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class SemiconductorOperationalReadiness:
    recipe_key: str
    source_key: str
    provider: str
    checks: tuple[OperationalReadinessCheck, ...]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'))

    def __post_init__(self) -> None:
        object.__setattr__(self, 'checks', tuple(self.checks))
        keys = [item.key for item in self.checks]
        if len(keys) != len(set(keys)):
            raise ValueError('operational readiness contains duplicate check keys')

    @property
    def ready_to_run(self) -> bool:
        required = tuple(item for item in self.checks if item.required_for_run)
        return bool(required) and all(item.state in {OperationalReadinessState.READY, OperationalReadinessState.DEGRADED} for item in required)

    @property
    def ready_for_release(self) -> bool:
        required = tuple(item for item in self.checks if item.required_for_release)
        return bool(required) and all(item.state is OperationalReadinessState.READY for item in required)

    @property
    def state(self) -> OperationalReadinessState:
        required = tuple(item for item in self.checks if item.required_for_release)
        if any(item.state is OperationalReadinessState.BLOCKED for item in required):
            return OperationalReadinessState.BLOCKED
        if any(item.state is OperationalReadinessState.PENDING for item in required):
            return OperationalReadinessState.PENDING
        if any(item.state is OperationalReadinessState.DEGRADED for item in required):
            return OperationalReadinessState.DEGRADED
        return OperationalReadinessState.READY if self.ready_for_release else OperationalReadinessState.PENDING

    @property
    def next_actions(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.remediation for item in self.checks if item.state is not OperationalReadinessState.READY and item.remediation))

    def to_dict(self) -> dict[str, Any]:
        return {
            'recipe_key': self.recipe_key,
            'source_key': self.source_key,
            'provider': self.provider,
            'state': self.state.value,
            'ready_to_run': self.ready_to_run,
            'ready_for_release': self.ready_for_release,
            'generated_at': self.generated_at,
            'checks': [item.to_dict() for item in self.checks],
            'next_actions': self.next_actions,
        }


@dataclass(frozen=True, slots=True)
class OperationalRunbookStep:
    key: str
    title: str
    trigger: str
    action: str
    evidence_to_capture: tuple[str, ...] = ()
    required: bool = True

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.key, self.title, self.trigger, self.action)):
            raise ValueError('runbook step key, title, trigger and action must not be empty')
        object.__setattr__(self, 'evidence_to_capture', tuple(self.evidence_to_capture))

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key,
            'title': self.title,
            'trigger': self.trigger,
            'action': self.action,
            'evidence_to_capture': self.evidence_to_capture,
            'required': self.required,
        }


@dataclass(frozen=True, slots=True)
class SemiconductorOperationalRunbook:
    recipe_key: str
    steps: tuple[OperationalRunbookStep, ...]
    version: str = '1'

    def __post_init__(self) -> None:
        if not self.recipe_key.strip() or not self.version.strip():
            raise ValueError('runbook recipe_key and version must not be empty')
        object.__setattr__(self, 'steps', tuple(self.steps))
        keys = [item.key for item in self.steps]
        if len(keys) != len(set(keys)):
            raise ValueError('operational runbook contains duplicate step keys')

    def to_dict(self) -> dict[str, Any]:
        return {'recipe_key': self.recipe_key, 'version': self.version, 'steps': [item.to_dict() for item in self.steps]}


_RECIPE_INCIDENT_ACTIONS = {
    'spc-monitor': ('Freeze the reviewed baseline/limit version before interpreting new violations.', ('limit-version', 'baseline-window', 'violation-records')),
    'excursion-defense-line': ('Freeze affected/control population definitions and preserve the first detected excursion evidence.', ('affected-population', 'control-population', 'excursion-timeline')),
    'fdc-tool-health': ('Preserve raw/aligned traces, alarm/event overlays and the active recipe-step context before remediation.', ('trace-sample', 'alarm-events', 'recipe-version')),
    'lot-wafer-explorer': ('Preserve lot/wafer selection, spatial coordinates and map transformation settings before comparison.', ('lot-wafer-context', 'wafer-map', 'selection-snapshot')),
    'yield-loss': ('Freeze product/operation scope and bin/category definitions before recomputing loss contribution.', ('yield-population', 'bin-definition', 'pareto-snapshot')),
    'pm-effect-analysis': ('Preserve PM event identity and pre/post populations before changing process context.', ('pm-event', 'pre-pm-population', 'post-pm-population')),
    'chamber-matching': ('Preserve tool/recipe context and chamber fingerprint inputs before tuning or exclusion.', ('tool-recipe-context', 'chamber-fingerprint', 'comparison-population')),
    'rca-cockpit': ('Freeze affected/control populations, evidence matrix and genealogy scope before changing hypotheses.', ('affected-population', 'control-population', 'evidence-graph')),
}


def build_semiconductor_operational_runbook(recipe_key: str) -> SemiconductorOperationalRunbook:
    if recipe_key not in _RECIPE_INCIDENT_ACTIONS:
        raise KeyError(f'unknown semiconductor recipe {recipe_key!r}')
    incident_action, evidence = _RECIPE_INCIDENT_ACTIONS[recipe_key]
    steps = (
        OperationalRunbookStep('startup', 'Startup qualification', 'Before enabling operational use', 'Confirm source health, semantic bindings, current manufacturing context and bounded runtime readiness.', ('setup-workflow', 'runtime-probe')),
        OperationalRunbookStep('stale-data', 'Stale or delayed data', 'Freshness becomes stale or source health degrades', 'Stop interpreting new analytical changes as current, show stale state, and restore the provider/feed before refresh.', ('source-health', 'freshness-timestamp')),
        OperationalRunbookStep('incident', 'Engineering incident preservation', 'Excursion, unexpected drift, alarm or analytical anomaly', incident_action, evidence),
        OperationalRunbookStep('provider-failure', 'Provider degradation', 'Provider health, conformance or pushdown assumptions fail', 'Fail closed for release-sensitive workflows, use only approved fallback behavior, and rerun bounded conformance before returning to service.', ('provider-health', 'conformance-report', 'query-stats')),
        OperationalRunbookStep('rollback', 'Configuration rollback', 'A new preset/configuration produces unsafe, empty or inconsistent behavior', 'Restore the last reviewed Wave 60 workspace/runtime preset; never rewrite DataSource or AnalysisContext state out-of-band.', ('runtime-preset', 'configuration-review')),
        OperationalRunbookStep('release-evidence', 'Release evidence capture', 'Before promotion or after target-environment changes', 'Capture target runtime/browser/provider/benchmark evidence with hashes and timestamps; missing evidence remains pending.', ('target-evidence-bundle', 'artifact-hashes')),
    )
    return SemiconductorOperationalRunbook(recipe_key, steps)


def _state(value: bool, *, pending: bool = False, degraded: bool = False) -> OperationalReadinessState:
    if pending:
        return OperationalReadinessState.PENDING
    if value:
        return OperationalReadinessState.DEGRADED if degraded else OperationalReadinessState.READY
    return OperationalReadinessState.BLOCKED


SEMICONDUCTOR_OPERATIONAL_RUNBOOKS: Mapping[str, SemiconductorOperationalRunbook] = MappingProxyType({key: build_semiconductor_operational_runbook(key) for key in _RECIPE_INCIDENT_ACTIONS})


def assess_semiconductor_operational_readiness(
    runtime,
    *,
    runtime_experience: RuntimeExperienceState | None = None,
    adapter_conformance: AdapterConformanceReport | None = None,
    performance: RuntimePerformanceReport | None = None,
    benchmark: SemiconductorBenchmarkReport | None = None,
    health_report: HealthReport | None = None,
) -> SemiconductorOperationalReadiness:
    """Create provider-neutral operational readiness without running unbounded probes."""
    experience = runtime_experience or build_runtime_experience_state(runtime)
    health = runtime.onboarding.source_health
    review = review_recipe_configuration(runtime, adapter_conformance=adapter_conformance, benchmark=benchmark)
    checks: list[OperationalReadinessCheck] = []
    checks.append(OperationalReadinessCheck(
        'source-health', 'Provider/source health',
        _state(health.healthy), f'Source health is {health.status.value}.',
        'Restore provider health before operational use.', True, True,
        {'latency_ms': health.latency_ms, 'freshness_at': health.freshness_at},
    ))
    checks.append(OperationalReadinessCheck(
        'semantic-onboarding', 'Semantic onboarding',
        _state(runtime.onboarding.ready),
        'Required semiconductor semantics are bound.' if runtime.onboarding.ready else 'Required semiconductor semantics are unresolved.',
        'Resolve required or ambiguous semantic mappings explicitly.', True, True,
    ))
    runtime_ok = experience.status is RuntimeExperienceStatus.READY
    runtime_pending = experience.status in {RuntimeExperienceStatus.LOADING, RuntimeExperienceStatus.STALE}
    runtime_degraded = experience.status in {RuntimeExperienceStatus.DEGRADED, RuntimeExperienceStatus.PARTIAL, RuntimeExperienceStatus.EMPTY}
    runtime_state = (OperationalReadinessState.PENDING if runtime_pending else (OperationalReadinessState.DEGRADED if runtime_degraded else (OperationalReadinessState.READY if runtime_ok else OperationalReadinessState.BLOCKED)))
    checks.append(OperationalReadinessCheck(
        'runtime-state', 'Runtime analytical state',
        runtime_state, experience.message,
        'Refresh and resolve runtime warnings/errors before operational use.', True, True,
        {'status': experience.status.value},
    ))
    checks.append(OperationalReadinessCheck(
        'recipe-guardrails', 'Recipe operational guardrails',
        _state(not review.blocking, degraded=bool(review.warnings)),
        f'{len(review.blocking)} blocking and {len(review.warnings)} warning findings.',
        'Resolve blocking recipe configuration findings and review warnings.', True, True,
    ))
    checks.append(OperationalReadinessCheck(
        'provider-conformance', 'Approved provider conformance',
        OperationalReadinessState.PENDING if adapter_conformance is None else _state(adapter_conformance.passed),
        'Provider conformance evidence is pending.' if adapter_conformance is None else ('Provider conformance passed.' if adapter_conformance.passed else 'Provider conformance failed.'),
        'Run and pass the production provider conformance profile.', False, True,
    ))
    checks.append(OperationalReadinessCheck(
        'runtime-performance', 'Representative runtime pushdown/performance',
        OperationalReadinessState.PENDING if performance is None else _state(performance.passed),
        'Representative runtime performance evidence is pending.' if performance is None else ('Runtime performance passed.' if performance.passed else 'Runtime performance failed.'),
        'Run bounded performance probes against representative target data.', False, True,
    ))
    checks.append(OperationalReadinessCheck(
        'provider-benchmark', 'Governed provider benchmark',
        OperationalReadinessState.PENDING if benchmark is None else _state(benchmark.passed),
        'Governed benchmark evidence is pending.' if benchmark is None else ('Provider benchmark passed.' if benchmark.passed else 'Provider benchmark failed.'),
        'Run the governed provider benchmark profile on representative target data.', False, True,
    ))
    if health_report is not None:
        state = OperationalReadinessState.READY if health_report.state is HealthState.HEALTHY else (OperationalReadinessState.DEGRADED if health_report.state is HealthState.DEGRADED and health_report.ready else OperationalReadinessState.BLOCKED)
        checks.append(OperationalReadinessCheck(
            'application-health', 'Application health registry', state,
            f'Application health registry reports {health_report.state.value}.',
            'Resolve critical application health failures before release.', False, True,
            {'ready': health_report.ready, 'checks': len(health_report.checks)},
        ))
    return SemiconductorOperationalReadiness(runtime.recipe.key, runtime.source.key, runtime.source.provider, tuple(checks))


def operational_readiness_to_dict(report: SemiconductorOperationalReadiness) -> dict[str, Any]:
    return report.to_dict()


def operational_readiness_from_dict(payload: Mapping[str, Any]) -> SemiconductorOperationalReadiness:
    checks_payload = payload.get('checks')
    if not isinstance(checks_payload, list):
        raise TypeError('operational readiness checks must be a list')
    checks = tuple(OperationalReadinessCheck(
        str(item['key']), str(item['label']), OperationalReadinessState(str(item['state'])), str(item['detail']),
        str(item.get('remediation','')), bool(item.get('required_for_run',False)), bool(item.get('required_for_release',True)), item.get('metadata',{}),
    ) for item in checks_payload)
    return SemiconductorOperationalReadiness(
        str(payload['recipe_key']), str(payload['source_key']), str(payload['provider']), checks,
        str(payload.get('generated_at') or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')),
    )


def write_operational_readiness(path: str | Path, report: SemiconductorOperationalReadiness) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    return target


def read_operational_readiness(path: str | Path) -> SemiconductorOperationalReadiness:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, Mapping):
        raise TypeError('operational readiness JSON must contain an object')
    return operational_readiness_from_dict(payload)


__all__ = [
    'OperationalReadinessCheck','OperationalReadinessState','OperationalRunbookStep','SemiconductorOperationalReadiness',
    'SemiconductorOperationalRunbook','SEMICONDUCTOR_OPERATIONAL_RUNBOOKS','assess_semiconductor_operational_readiness','build_semiconductor_operational_runbook','operational_readiness_from_dict','operational_readiness_to_dict','read_operational_readiness','write_operational_readiness',
]
