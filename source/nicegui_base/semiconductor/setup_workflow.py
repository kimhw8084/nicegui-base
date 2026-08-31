from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from .benchmarking import SemiconductorBenchmarkReport
from .conformance import AdapterConformanceReport
from .onboarding import RecipeOnboardingView, build_recipe_onboarding_view
from .operations import RecipeConfigurationReview, review_recipe_configuration


class SetupStepStatus(str, Enum):
    COMPLETE = 'complete'
    ACTION_REQUIRED = 'action_required'
    BLOCKED = 'blocked'
    PENDING = 'pending'
    SKIPPED = 'skipped'


@dataclass(frozen=True, slots=True)
class RecipeSetupStep:
    key: str
    title: str
    status: SetupStepStatus
    summary: str
    actions: tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.title.strip() or not self.summary.strip():
            raise ValueError('recipe setup step key, title and summary must not be empty')
        object.__setattr__(self, 'actions', tuple(self.actions))
        object.__setattr__(self, 'details', MappingProxyType(dict(self.details)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key,
            'title': self.title,
            'status': self.status.value,
            'summary': self.summary,
            'actions': self.actions,
            'details': dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class RecipeSetupWorkflow:
    recipe_key: str
    variant_key: str | None
    source_key: str
    provider: str
    steps: tuple[RecipeSetupStep, ...]
    onboarding: RecipeOnboardingView
    configuration_review: RecipeConfigurationReview

    def __post_init__(self) -> None:
        object.__setattr__(self, 'steps', tuple(self.steps))
        keys = [item.key for item in self.steps]
        if len(keys) != len(set(keys)):
            raise ValueError('recipe setup workflow contains duplicate step keys')

    @property
    def completion_ratio(self) -> float:
        applicable = tuple(item for item in self.steps if item.status is not SetupStepStatus.SKIPPED)
        if not applicable:
            return 1.0
        return sum(item.status is SetupStepStatus.COMPLETE for item in applicable) / len(applicable)

    @property
    def blocked(self) -> bool:
        return any(item.status is SetupStepStatus.BLOCKED for item in self.steps)

    @property
    def ready_to_run(self) -> bool:
        required = {'provider','bindings','configuration','runtime'}
        by_key = {item.key: item for item in self.steps}
        return (
            by_key['provider'].status is SetupStepStatus.COMPLETE
            and by_key['bindings'].status is SetupStepStatus.COMPLETE
            and by_key['runtime'].status is SetupStepStatus.COMPLETE
            and by_key['configuration'].status in {SetupStepStatus.COMPLETE, SetupStepStatus.ACTION_REQUIRED}
        )

    @property
    def ready_for_release(self) -> bool:
        return bool(self.steps) and all(item.status in {SetupStepStatus.COMPLETE, SetupStepStatus.SKIPPED} for item in self.steps)

    @property
    def next_actions(self) -> tuple[str, ...]:
        actions: list[str] = []
        for item in self.steps:
            if item.status is not SetupStepStatus.COMPLETE:
                actions.extend(item.actions)
        return tuple(dict.fromkeys(actions))

    def to_dict(self) -> dict[str, Any]:
        return {
            'recipe_key': self.recipe_key,
            'variant_key': self.variant_key,
            'source_key': self.source_key,
            'provider': self.provider,
            'completion_ratio': self.completion_ratio,
            'blocked': self.blocked,
            'ready_to_run': self.ready_to_run,
            'ready_for_release': self.ready_for_release,
            'steps': [item.to_dict() for item in self.steps],
            'next_actions': self.next_actions,
            'onboarding': self.onboarding.to_dict(),
            'configuration_review': self.configuration_review.to_dict(),
        }


def _status_from_findings(review: RecipeConfigurationReview) -> SetupStepStatus:
    if review.blocking:
        return SetupStepStatus.BLOCKED
    if review.warnings:
        return SetupStepStatus.ACTION_REQUIRED
    return SetupStepStatus.COMPLETE


def build_recipe_setup_workflow(
    runtime,
    *,
    probe=None,
    adapter_conformance: AdapterConformanceReport | None = None,
    benchmark: SemiconductorBenchmarkReport | None = None,
    target_certification=None,
) -> RecipeSetupWorkflow:
    onboarding = build_recipe_onboarding_view(runtime.recipe, runtime.onboarding)
    review = review_recipe_configuration(runtime, adapter_conformance=adapter_conformance, benchmark=benchmark)
    health = runtime.onboarding.source_health

    provider_status = SetupStepStatus.COMPLETE if health.healthy else SetupStepStatus.BLOCKED
    bindings_status = SetupStepStatus.COMPLETE if onboarding.ready else SetupStepStatus.BLOCKED
    config_status = _status_from_findings(review)
    if probe is None:
        runtime_status = SetupStepStatus.PENDING
        runtime_summary = 'Run the bounded runtime readiness probe for the current manufacturing context.'
        runtime_actions = ('Run runtime.refresh() before operational use.',)
    else:
        readiness = getattr(getattr(probe, 'readiness', None), 'value', '')
        runtime_status = SetupStepStatus.COMPLETE if readiness == 'ready' else (SetupStepStatus.BLOCKED if readiness == 'blocked' else SetupStepStatus.ACTION_REQUIRED)
        runtime_summary = f'Bounded runtime probe reported {readiness or "unknown"} readiness with {getattr(probe, "rows_available", 0)} matching rows.'
        runtime_actions = () if runtime_status is SetupStepStatus.COMPLETE else ('Review runtime warnings and current manufacturing context.',)

    if adapter_conformance is None:
        conformance_status = SetupStepStatus.PENDING
        conformance_summary = 'Production adapter conformance has not been attached.'
        conformance_actions = ('Run the approved provider adapter conformance profile.',)
    else:
        conformance_status = SetupStepStatus.COMPLETE if adapter_conformance.passed else SetupStepStatus.BLOCKED
        conformance_summary = 'Provider conformance passed.' if adapter_conformance.passed else 'Provider conformance contains blocking findings.'
        conformance_actions = () if adapter_conformance.passed else ('Resolve provider conformance errors.',)

    if benchmark is None:
        benchmark_status = SetupStepStatus.PENDING
        benchmark_summary = 'Representative provider benchmark has not been attached.'
        benchmark_actions = ('Run the provider-rc benchmark on representative target data.',)
    else:
        benchmark_status = SetupStepStatus.COMPLETE if benchmark.passed else SetupStepStatus.BLOCKED
        benchmark_summary = f'Benchmark profile {benchmark.profile_key} passed.' if benchmark.passed else f'Benchmark profile {benchmark.profile_key} contains blocking findings.'
        benchmark_actions = () if benchmark.passed else ('Resolve benchmark/pushdown findings.',)

    if target_certification is None:
        target_status = SetupStepStatus.PENDING
        target_summary = 'Target runtime/browser/human evidence remains pending.'
        target_actions = ('Capture target-environment evidence without editing framework internals.',)
    else:
        target_status = SetupStepStatus.COMPLETE if target_certification.promotable else (SetupStepStatus.BLOCKED if target_certification.failed else SetupStepStatus.PENDING)
        target_summary = 'All target gates passed.' if target_certification.promotable else 'Target certification still contains pending or failed gates.'
        target_actions = () if target_certification.promotable else tuple(f'Complete target gate: {item.label}' for item in (*target_certification.failed, *target_certification.pending))

    steps = (
        RecipeSetupStep('provider','Provider & source health',provider_status,
                        f'{runtime.source.provider}:{runtime.source.key} health is {health.status.value}.',
                        () if provider_status is SetupStepStatus.COMPLETE else ('Resolve provider health before continuing.',),
                        {'health': health.status.value, 'latency_ms': health.latency_ms}),
        RecipeSetupStep('bindings','Semantic field mappings',bindings_status,
                        f'{onboarding.bound_fields}/{len(onboarding.fields)} governed semantic fields are bound.',
                        onboarding.blocking_actions,
                        {'completion_ratio': onboarding.completion_ratio}),
        RecipeSetupStep('configuration','Recipe configuration review',config_status,
                        'Recipe guardrails and configuration have been reviewed.' if config_status is SetupStepStatus.COMPLETE else 'Recipe configuration has unresolved operational guardrails.',
                        tuple(item.remediation for item in (*review.blocking, *review.warnings)),
                        {'blocking': len(review.blocking), 'warnings': len(review.warnings)}),
        RecipeSetupStep('runtime','Bounded runtime readiness',runtime_status,runtime_summary,runtime_actions),
        RecipeSetupStep('conformance','Provider conformance',conformance_status,conformance_summary,conformance_actions),
        RecipeSetupStep('benchmark','Representative performance',benchmark_status,benchmark_summary,benchmark_actions),
        RecipeSetupStep('target-certification','Target environment certification',target_status,target_summary,target_actions),
    )
    return RecipeSetupWorkflow(runtime.recipe.key, runtime.configuration.variant_key, runtime.source.key, runtime.source.provider, steps, onboarding, review)


async def prepare_recipe_setup_workflow(
    runtime,
    *,
    adapter_conformance: AdapterConformanceReport | None = None,
    benchmark: SemiconductorBenchmarkReport | None = None,
    target_certification=None,
    refresh: bool = True,
) -> RecipeSetupWorkflow:
    probe = await runtime.refresh() if refresh else None
    return build_recipe_setup_workflow(
        runtime,
        probe=probe,
        adapter_conformance=adapter_conformance,
        benchmark=benchmark,
        target_certification=target_certification,
    )


__all__ = [
    'RecipeSetupStep','RecipeSetupWorkflow','SetupStepStatus','build_recipe_setup_workflow','prepare_recipe_setup_workflow',
]
