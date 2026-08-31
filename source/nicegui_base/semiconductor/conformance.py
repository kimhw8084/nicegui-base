from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from nicegui_base.data_sources import Comparison, ComparisonOperator, DataSource, Query, QueryStats, SourceCapabilities, SourceHealth

from .onboarding import RecipeOnboardingReport, SemiconductorSourceAdapter, SmartBindingPolicy, onboard_recipe_source, open_semiconductor_source
from .recipes import SemiconductorRecipeDefinition, get_semiconductor_recipe


class ConformanceSeverity(str, Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


@dataclass(frozen=True, slots=True)
class AdapterDiagnostic:
    code: str
    severity: ConformanceSeverity
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError('adapter diagnostic code and message must not be empty')
        object.__setattr__(self, 'details', MappingProxyType(dict(self.details)))


@dataclass(frozen=True, slots=True)
class AdapterConformancePolicy:
    require_healthy: bool = True
    require_filter_pushdown: bool = True
    require_pagination_pushdown: bool = True
    require_projection_pushdown: bool = False
    require_distinct_pushdown: bool = False
    probe_page_size: int = 2
    max_probe_rows: int = 5
    max_health_latency_ms: float | None = None
    max_query_elapsed_ms: float | None = None

    def __post_init__(self) -> None:
        if self.probe_page_size < 1 or self.probe_page_size > self.max_probe_rows:
            raise ValueError('probe_page_size must be between 1 and max_probe_rows')
        if self.max_probe_rows < 1 or self.max_probe_rows > 100:
            raise ValueError('max_probe_rows must be between 1 and 100')
        if self.max_health_latency_ms is not None and self.max_health_latency_ms <= 0:
            raise ValueError('max_health_latency_ms must be > 0')
        if self.max_query_elapsed_ms is not None and self.max_query_elapsed_ms <= 0:
            raise ValueError('max_query_elapsed_ms must be > 0')


@dataclass(frozen=True, slots=True)
class AdapterProbeObservation:
    operation: str
    requested_limit: int | None
    rows_returned: int
    filtered_total: int | None
    stats: QueryStats

    def __post_init__(self) -> None:
        if not self.operation.strip():
            raise ValueError('probe operation must not be empty')
        if self.requested_limit is not None and self.requested_limit < 1:
            raise ValueError('requested_limit must be >= 1')
        if self.rows_returned < 0:
            raise ValueError('rows_returned must be >= 0')


@dataclass(frozen=True, slots=True)
class AdapterConformanceReport:
    recipe_key: str
    adapter_key: str
    source_key: str
    provider: str
    health: SourceHealth
    capabilities: SourceCapabilities
    onboarding: RecipeOnboardingReport
    observations: tuple[AdapterProbeObservation, ...]
    diagnostics: tuple[AdapterDiagnostic, ...]
    source_closed_after_probe: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, 'observations', tuple(self.observations))
        object.__setattr__(self, 'diagnostics', tuple(self.diagnostics))

    @property
    def errors(self) -> tuple[AdapterDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity is ConformanceSeverity.ERROR)

    @property
    def warnings(self) -> tuple[AdapterDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity is ConformanceSeverity.WARNING)

    @property
    def passed(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            'recipe_key': self.recipe_key,
            'adapter_key': self.adapter_key,
            'source_key': self.source_key,
            'provider': self.provider,
            'passed': self.passed,
            'source_closed_after_probe': self.source_closed_after_probe,
            'health': {
                'status': self.health.status.value,
                'message': self.health.message,
                'latency_ms': self.health.latency_ms,
                'freshness_at': self.health.freshness_at,
            },
            'capabilities': {name: getattr(self.capabilities, name) for name in self.capabilities.__dataclass_fields__},
            'onboarding': self.onboarding.to_dict(),
            'observations': [
                {
                    'operation': item.operation,
                    'requested_limit': item.requested_limit,
                    'rows_returned': item.rows_returned,
                    'filtered_total': item.filtered_total,
                    'elapsed_ms': item.stats.elapsed_ms,
                    'pushdown': item.stats.pushdown,
                    'rows_scanned': item.stats.rows_scanned,
                }
                for item in self.observations
            ],
            'diagnostics': [
                {'code': item.code, 'severity': item.severity.value, 'message': item.message, 'details': dict(item.details)}
                for item in self.diagnostics
            ],
        }


class AdapterConformanceError(RuntimeError):
    def __init__(self, report: AdapterConformanceReport) -> None:
        self.report = report
        codes = ', '.join(item.code for item in report.errors) or 'unknown'
        super().__init__(f'semiconductor adapter conformance failed for {report.source_key!r}: {codes}')


def _diagnose_capability(
    diagnostics: list[AdapterDiagnostic],
    capabilities: SourceCapabilities,
    *,
    attribute: str,
    required: bool,
    label: str,
) -> None:
    advertised = bool(getattr(capabilities, attribute))
    if required and not advertised:
        diagnostics.append(AdapterDiagnostic(
            f'missing_{attribute}', ConformanceSeverity.ERROR,
            f'production policy requires {label}, but the source does not advertise it',
        ))
    elif not advertised:
        diagnostics.append(AdapterDiagnostic(
            f'no_{attribute}', ConformanceSeverity.WARNING,
            f'source does not advertise {label}; validate scale limits before production promotion',
        ))


def _observe(operation: str, limit: int | None, result) -> AdapterProbeObservation:
    rows = getattr(result, 'rows', ())
    return AdapterProbeObservation(
        operation,
        limit,
        len(rows),
        getattr(result, 'filtered_total', None),
        result.stats,
    )


def _check_observation(
    observation: AdapterProbeObservation,
    diagnostics: list[AdapterDiagnostic],
    *,
    policy: AdapterConformancePolicy,
    require_pushdown: bool,
) -> None:
    if observation.requested_limit is not None and observation.rows_returned > observation.requested_limit:
        diagnostics.append(AdapterDiagnostic(
            'probe_limit_violated', ConformanceSeverity.ERROR,
            f'{observation.operation} returned more rows than the bounded probe requested',
            {'requested': observation.requested_limit, 'returned': observation.rows_returned},
        ))
    if require_pushdown and not observation.stats.pushdown:
        diagnostics.append(AdapterDiagnostic(
            f'{observation.operation}_pushdown_not_observed', ConformanceSeverity.ERROR,
            f'{observation.operation} is required to execute with backend pushdown, but QueryStats.pushdown is false',
        ))
    if policy.max_query_elapsed_ms is not None and observation.stats.elapsed_ms > policy.max_query_elapsed_ms:
        diagnostics.append(AdapterDiagnostic(
            f'{observation.operation}_latency_exceeded', ConformanceSeverity.ERROR,
            f'{observation.operation} exceeded the configured query latency budget',
            {'elapsed_ms': observation.stats.elapsed_ms, 'budget_ms': policy.max_query_elapsed_ms},
        ))


async def run_semiconductor_adapter_conformance(
    recipe: str | SemiconductorRecipeDefinition,
    source_or_adapter: DataSource | SemiconductorSourceAdapter,
    *,
    field_overrides: Mapping[str, str] | None = None,
    policy: AdapterConformancePolicy = AdapterConformancePolicy(),
    binding_policy: SmartBindingPolicy = SmartBindingPolicy(),
    close_owned_source: bool = True,
) -> AdapterConformanceReport:
    """Probe a semiconductor provider through the existing DataSource contract only.

    Every query is bounded. The function never enumerates an entire production source,
    and it treats a provider's capability flags as auditable claims rather than hints.
    """
    definition = get_semiconductor_recipe(recipe) if isinstance(recipe, str) else recipe
    adapted = await open_semiconductor_source(definition, source_or_adapter)
    source = adapted.source
    adapter_key = getattr(source_or_adapter, 'key', 'direct-datasource') if not isinstance(source_or_adapter, DataSource) else 'direct-datasource'
    diagnostics: list[AdapterDiagnostic] = []
    observations: list[AdapterProbeObservation] = []
    closed = False
    try:
        onboarding = await onboard_recipe_source(
            definition,
            source,
            field_overrides={**dict(adapted.field_overrides), **dict(field_overrides or {})},
            policy=binding_policy,
            adapter_metadata=adapted.metadata,
        )
        health = onboarding.source_health
        capabilities = source.capabilities

        if policy.require_healthy and not health.healthy:
            diagnostics.append(AdapterDiagnostic(
                'source_unhealthy', ConformanceSeverity.ERROR,
                f'source health must be healthy for production conformance; observed {health.status.value}',
                {'message': health.message},
            ))
        elif not health.healthy:
            diagnostics.append(AdapterDiagnostic('source_unhealthy', ConformanceSeverity.WARNING, f'source health is {health.status.value}', {'message': health.message}))
        if policy.max_health_latency_ms is not None and health.latency_ms is not None and health.latency_ms > policy.max_health_latency_ms:
            diagnostics.append(AdapterDiagnostic(
                'health_latency_exceeded', ConformanceSeverity.ERROR,
                'source health check exceeded the configured latency budget',
                {'latency_ms': health.latency_ms, 'budget_ms': policy.max_health_latency_ms},
            ))

        _diagnose_capability(diagnostics, capabilities, attribute='filter_pushdown', required=policy.require_filter_pushdown, label='filter pushdown')
        _diagnose_capability(diagnostics, capabilities, attribute='pagination_pushdown', required=policy.require_pagination_pushdown, label='pagination pushdown')
        _diagnose_capability(diagnostics, capabilities, attribute='projection_pushdown', required=policy.require_projection_pushdown, label='projection pushdown')
        _diagnose_capability(diagnostics, capabilities, attribute='distinct_pushdown', required=policy.require_distinct_pushdown, label='distinct-value pushdown')

        if not onboarding.ready:
            diagnostics.append(AdapterDiagnostic(
                'recipe_bindings_incomplete', ConformanceSeverity.ERROR,
                'source cannot satisfy the recipe required semantic bindings without additional explicit overrides',
                {'missing_required': onboarding.unresolved_required},
            ))

        projection = tuple(dict.fromkeys(onboarding.compatibility.bindings.values()))[:policy.max_probe_rows]
        first_query = Query(limit=policy.probe_page_size, projection=projection)
        first = await source.query(first_query)
        first_obs = _observe('bounded_query', policy.probe_page_size, first)
        observations.append(first_obs)
        _check_observation(first_obs, diagnostics, policy=policy, require_pushdown=False)

        page_query = Query(offset=1, limit=policy.probe_page_size, projection=projection)
        page = await source.query(page_query)
        page_obs = _observe('pagination', policy.probe_page_size, page)
        observations.append(page_obs)
        _check_observation(page_obs, diagnostics, policy=policy, require_pushdown=policy.require_pagination_pushdown or capabilities.pagination_pushdown)

        if projection and first.rows:
            unexpected = set(first.rows[0]) - set(projection)
            if unexpected:
                diagnostics.append(AdapterDiagnostic(
                    'projection_contract_violated', ConformanceSeverity.ERROR,
                    'bounded projection query returned fields outside the requested projection',
                    {'unexpected_fields': tuple(sorted(unexpected))},
                ))
            if (policy.require_projection_pushdown or capabilities.projection_pushdown) and not first.stats.pushdown:
                diagnostics.append(AdapterDiagnostic(
                    'projection_pushdown_not_observed', ConformanceSeverity.ERROR,
                    'projection pushdown is advertised/required but was not observed in QueryStats',
                ))

            filter_field = projection[0]
            filter_value = first.rows[0].get(filter_field)
            filtered = await source.query(Query(
                filter=Comparison(filter_field, ComparisonOperator.EQ, filter_value),
                limit=policy.probe_page_size,
                projection=projection,
            ))
            filter_obs = _observe('filter', policy.probe_page_size, filtered)
            observations.append(filter_obs)
            _check_observation(filter_obs, diagnostics, policy=policy, require_pushdown=policy.require_filter_pushdown or capabilities.filter_pushdown)

            if capabilities.distinct_pushdown or policy.require_distinct_pushdown:
                # The equality predicate bounds cardinality to at most one unique value even
                # for providers whose distinct API does not expose a limit argument.
                distinct = await source.distinct(filter_field, Query(filter=Comparison(filter_field, ComparisonOperator.EQ, filter_value), limit=1))
                distinct_obs = AdapterProbeObservation('distinct', 1, len(distinct.values), distinct.total, distinct.stats)
                observations.append(distinct_obs)
                _check_observation(distinct_obs, diagnostics, policy=policy, require_pushdown=policy.require_distinct_pushdown or capabilities.distinct_pushdown)

        if capabilities.cancellation is False:
            diagnostics.append(AdapterDiagnostic('no_cancellation', ConformanceSeverity.WARNING, 'source does not advertise cancellation support for abandoned production work'))

        if not diagnostics:
            diagnostics.append(AdapterDiagnostic('conformance_pass', ConformanceSeverity.INFO, 'bounded adapter contract probes completed without findings'))

        report = AdapterConformanceReport(
            definition.key, str(adapter_key), source.key, source.provider, health, capabilities,
            onboarding, tuple(observations), tuple(diagnostics), False,
        )
    finally:
        if adapted.owns_source and close_owned_source and not source.closed:
            await source.aclose()
            closed = True

    if closed:
        report = AdapterConformanceReport(
            report.recipe_key, report.adapter_key, report.source_key, report.provider,
            report.health, report.capabilities, report.onboarding, report.observations,
            report.diagnostics, True,
        )
    return report


def assert_semiconductor_adapter_conformance(report: AdapterConformanceReport) -> None:
    if not report.passed:
        raise AdapterConformanceError(report)


__all__ = [
    'AdapterConformanceError','AdapterConformancePolicy','AdapterConformanceReport','AdapterDiagnostic',
    'AdapterProbeObservation','ConformanceSeverity','assert_semiconductor_adapter_conformance',
    'run_semiconductor_adapter_conformance',
]
