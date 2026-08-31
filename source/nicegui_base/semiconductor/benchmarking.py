from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from types import MappingProxyType
from typing import Any, Mapping

from .conformance import AdapterDiagnostic, ConformanceSeverity
from .runtime_experience import RuntimePerformancePolicy, RuntimePerformanceReport, probe_semiconductor_runtime_performance


def _percentile(values: tuple[float, ...], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction))))
    return float(ordered[index])


@dataclass(frozen=True, slots=True)
class SemiconductorBenchmarkProfile:
    key: str
    description: str
    iterations: int = 3
    warmup_runs: int = 1
    performance_policy: RuntimePerformancePolicy = RuntimePerformancePolicy()
    minimum_filtered_rows: int | None = None
    require_representative_scale: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.description.strip():
            raise ValueError('benchmark profile key and description must not be empty')
        if not 1 <= self.iterations <= 50:
            raise ValueError('benchmark iterations must be between 1 and 50')
        if not 0 <= self.warmup_runs <= 20:
            raise ValueError('benchmark warmup_runs must be between 0 and 20')
        if self.minimum_filtered_rows is not None and self.minimum_filtered_rows < 1:
            raise ValueError('minimum_filtered_rows must be >= 1')
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))


SEMICONDUCTOR_BENCHMARK_PROFILES: Mapping[str, SemiconductorBenchmarkProfile] = MappingProxyType({
    'development-smoke': SemiconductorBenchmarkProfile(
        'development-smoke',
        'Fast bounded developer check; does not claim representative fab-scale readiness.',
        iterations=1,
        warmup_runs=0,
        performance_policy=RuntimePerformancePolicy(
            page_size=3,
            require_filter_pushdown=False,
            require_pagination_pushdown=False,
            require_projection_pushdown=False,
        ),
    ),
    'provider-rc': SemiconductorBenchmarkProfile(
        'provider-rc',
        'Release-candidate provider benchmark with observed pushdown and representative-scale evidence.',
        iterations=5,
        warmup_runs=1,
        performance_policy=RuntimePerformancePolicy(
            page_size=5,
            require_filter_pushdown=True,
            require_pagination_pushdown=True,
            require_projection_pushdown=True,
        ),
        minimum_filtered_rows=10_000,
        require_representative_scale=True,
    ),
})


@dataclass(frozen=True, slots=True)
class BenchmarkOperationSummary:
    operation: str
    samples: tuple[float, ...]
    median_ms: float
    p95_ms: float
    max_ms: float
    pushdown_rate: float
    max_rows_returned: int
    max_filtered_total: int

    def __post_init__(self) -> None:
        object.__setattr__(self, 'samples', tuple(self.samples))
        if not 0.0 <= self.pushdown_rate <= 1.0:
            raise ValueError('pushdown_rate must be between 0 and 1')

    def to_dict(self) -> dict[str, Any]:
        return {
            'operation': self.operation,
            'samples_ms': self.samples,
            'median_ms': self.median_ms,
            'p95_ms': self.p95_ms,
            'max_ms': self.max_ms,
            'pushdown_rate': self.pushdown_rate,
            'max_rows_returned': self.max_rows_returned,
            'max_filtered_total': self.max_filtered_total,
        }


@dataclass(frozen=True, slots=True)
class SemiconductorBenchmarkReport:
    profile_key: str
    recipe_key: str
    source_key: str
    provider: str
    iterations: int
    operation_summaries: tuple[BenchmarkOperationSummary, ...]
    diagnostics: tuple[AdapterDiagnostic, ...]
    raw_runs: tuple[RuntimePerformanceReport, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'operation_summaries', tuple(self.operation_summaries))
        object.__setattr__(self, 'diagnostics', tuple(self.diagnostics))
        object.__setattr__(self, 'raw_runs', tuple(self.raw_runs))

    @property
    def errors(self) -> tuple[AdapterDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity is ConformanceSeverity.ERROR)

    @property
    def warnings(self) -> tuple[AdapterDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity is ConformanceSeverity.WARNING)

    @property
    def passed(self) -> bool:
        return not self.errors

    def to_dict(self, *, include_raw_runs: bool = False) -> dict[str, Any]:
        payload = {
            'profile_key': self.profile_key,
            'recipe_key': self.recipe_key,
            'source_key': self.source_key,
            'provider': self.provider,
            'iterations': self.iterations,
            'passed': self.passed,
            'operation_summaries': [item.to_dict() for item in self.operation_summaries],
            'diagnostics': [
                {'code': item.code, 'severity': item.severity.value, 'message': item.message, 'details': dict(item.details)}
                for item in self.diagnostics
            ],
        }
        if include_raw_runs:
            payload['raw_runs'] = [item.to_dict() for item in self.raw_runs]
        return payload


def get_semiconductor_benchmark_profile(profile: str | SemiconductorBenchmarkProfile) -> SemiconductorBenchmarkProfile:
    if isinstance(profile, SemiconductorBenchmarkProfile):
        return profile
    try:
        return SEMICONDUCTOR_BENCHMARK_PROFILES[profile]
    except KeyError as exc:
        raise KeyError(f'unknown semiconductor benchmark profile {profile!r}') from exc


async def run_semiconductor_runtime_benchmark(
    runtime,
    *,
    profile: str | SemiconductorBenchmarkProfile = 'provider-rc',
) -> SemiconductorBenchmarkReport:
    """Repeat only Wave 64's bounded pushdown probe; never enumerate a full provider source."""
    definition = get_semiconductor_benchmark_profile(profile)
    for _ in range(definition.warmup_runs):
        await probe_semiconductor_runtime_performance(runtime, policy=definition.performance_policy)
    runs = tuple(
        [await probe_semiconductor_runtime_performance(runtime, policy=definition.performance_policy) for _ in range(definition.iterations)]
    )
    diagnostics: list[AdapterDiagnostic] = []
    for run in runs:
        diagnostics.extend(run.errors)
        diagnostics.extend(run.warnings)

    by_operation: dict[str, list[Any]] = {}
    for run in runs:
        for observation in run.observations:
            by_operation.setdefault(observation.operation, []).append(observation)
    summaries: list[BenchmarkOperationSummary] = []
    for operation in sorted(by_operation):
        values = by_operation[operation]
        latencies = tuple(float(item.elapsed_ms) for item in values)
        summaries.append(BenchmarkOperationSummary(
            operation,
            latencies,
            float(median(latencies)),
            _percentile(latencies, 0.95),
            max(latencies),
            sum(1 for item in values if item.pushdown) / len(values),
            max(item.rows_returned for item in values),
            max(item.filtered_total for item in values),
        ))

    observed_rows = max((item.max_filtered_total for item in summaries), default=0)
    if definition.minimum_filtered_rows is not None and observed_rows < definition.minimum_filtered_rows:
        severity = ConformanceSeverity.ERROR if definition.require_representative_scale else ConformanceSeverity.WARNING
        diagnostics.append(AdapterDiagnostic(
            'benchmark_scale_not_representative',
            severity,
            'benchmark source did not demonstrate the configured representative-scale row count',
            {'observed_filtered_rows': observed_rows, 'minimum_filtered_rows': definition.minimum_filtered_rows},
        ))
    if not diagnostics:
        diagnostics.append(AdapterDiagnostic('benchmark_pass', ConformanceSeverity.INFO, 'bounded benchmark profile completed without findings'))
    return SemiconductorBenchmarkReport(
        definition.key,
        runtime.recipe.key,
        runtime.source.key,
        runtime.source.provider,
        definition.iterations,
        tuple(summaries),
        tuple(diagnostics),
        runs,
    )


__all__ = [
    'SEMICONDUCTOR_BENCHMARK_PROFILES', 'BenchmarkOperationSummary', 'SemiconductorBenchmarkProfile',
    'SemiconductorBenchmarkReport', 'get_semiconductor_benchmark_profile', 'run_semiconductor_runtime_benchmark',
]
