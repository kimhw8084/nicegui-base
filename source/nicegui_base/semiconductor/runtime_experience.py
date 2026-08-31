from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from nicegui_base.analysis import AnalysisStatus
from nicegui_base.data_sources import Comparison, ComparisonOperator, Query, fields_in_filter
from nicegui_base.runtime import StateSnapshot, WorkspaceSnapshot, workspace_snapshot_from_dict, workspace_snapshot_to_dict

from .conformance import AdapterDiagnostic, ConformanceSeverity


class RuntimeExperienceStatus(str, Enum):
    READY = 'ready'
    DEGRADED = 'degraded'
    BLOCKED = 'blocked'
    LOADING = 'loading'
    EMPTY = 'empty'
    STALE = 'stale'
    PARTIAL = 'partial'


@dataclass(frozen=True, slots=True)
class RuntimeExperienceState:
    recipe_key: str
    variant_key: str | None
    provider: str
    status: RuntimeExperienceStatus
    message: str
    panel_states: Mapping[str, AnalysisStatus]
    manufacturing_context: Mapping[str, Any]
    selection_count: int
    warnings: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'panel_states', MappingProxyType(dict(self.panel_states)))
        object.__setattr__(self, 'manufacturing_context', MappingProxyType(dict(self.manufacturing_context)))
        object.__setattr__(self, 'warnings', tuple(self.warnings))
        object.__setattr__(self, 'next_actions', tuple(self.next_actions))

    def to_dict(self) -> dict[str, Any]:
        return {
            'recipe_key': self.recipe_key,
            'variant_key': self.variant_key,
            'provider': self.provider,
            'status': self.status.value,
            'message': self.message,
            'panel_states': {key: value.value for key, value in self.panel_states.items()},
            'manufacturing_context': dict(self.manufacturing_context),
            'selection_count': self.selection_count,
            'warnings': self.warnings,
            'next_actions': self.next_actions,
        }


@dataclass(frozen=True, slots=True)
class RecipeRuntimePreset:
    name: str
    recipe_key: str
    variant_key: str | None
    workspace: WorkspaceSnapshot
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f'unsupported recipe runtime preset schema {self.schema_version}')
        if not self.name.strip() or not self.recipe_key.strip():
            raise ValueError('preset name and recipe_key must not be empty')
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class RuntimePerformancePolicy:
    page_size: int = 3
    require_filter_pushdown: bool = True
    require_pagination_pushdown: bool = True
    require_projection_pushdown: bool = True
    max_query_elapsed_ms: float | None = None
    max_rows_scanned_per_returned_row: float | None = None

    def __post_init__(self) -> None:
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError('page_size must be between 1 and 100')
        if self.max_query_elapsed_ms is not None and self.max_query_elapsed_ms <= 0:
            raise ValueError('max_query_elapsed_ms must be > 0')
        if self.max_rows_scanned_per_returned_row is not None and self.max_rows_scanned_per_returned_row <= 0:
            raise ValueError('max_rows_scanned_per_returned_row must be > 0')


@dataclass(frozen=True, slots=True)
class RuntimePerformanceObservation:
    operation: str
    elapsed_ms: float
    rows_returned: int
    filtered_total: int
    pushdown: bool
    rows_scanned: int | None


@dataclass(frozen=True, slots=True)
class RuntimePerformanceReport:
    recipe_key: str
    source_key: str
    provider: str
    observations: tuple[RuntimePerformanceObservation, ...]
    diagnostics: tuple[AdapterDiagnostic, ...]

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
            'source_key': self.source_key,
            'provider': self.provider,
            'passed': self.passed,
            'observations': [item.__dict__ if hasattr(item, '__dict__') else {
                'operation': item.operation,
                'elapsed_ms': item.elapsed_ms,
                'rows_returned': item.rows_returned,
                'filtered_total': item.filtered_total,
                'pushdown': item.pushdown,
                'rows_scanned': item.rows_scanned,
            } for item in self.observations],
            'diagnostics': [
                {'code': item.code, 'severity': item.severity.value, 'message': item.message, 'details': dict(item.details)}
                for item in self.diagnostics
            ],
        }


def build_runtime_experience_state(runtime, probe=None) -> RuntimeExperienceState:
    panel_states = {key: surface.controller.state.status for key, surface in runtime.assembly.surfaces.items()}
    values = tuple(panel_states.values())
    warnings = tuple(runtime.onboarding.warnings)
    next_actions: list[str] = []
    if runtime._closed:
        status = RuntimeExperienceStatus.BLOCKED
        message = 'Runtime is closed'
        next_actions.append('Create or reopen the recipe runtime')
    elif any(value is AnalysisStatus.ERROR for value in values):
        status = RuntimeExperienceStatus.BLOCKED
        message = 'One or more analytical panels are in error'
        next_actions.append('Inspect the failed panel and source diagnostics')
    elif any(value is AnalysisStatus.LOADING for value in values):
        status = RuntimeExperienceStatus.LOADING
        message = 'Refreshing the current manufacturing context'
    elif values and all(value is AnalysisStatus.EMPTY for value in values):
        status = RuntimeExperienceStatus.EMPTY
        message = 'No rows match the current manufacturing context'
        next_actions.append('Broaden or clear one or more manufacturing filters')
    elif any(value is AnalysisStatus.STALE for value in values):
        status = RuntimeExperienceStatus.STALE
        message = 'Analysis context changed after the last refresh'
        next_actions.append('Refresh to apply the current context')
    elif any(value in {AnalysisStatus.PARTIAL, AnalysisStatus.EMPTY} for value in values):
        status = RuntimeExperienceStatus.PARTIAL
        message = 'Some runtime surfaces have partial or empty data'
    elif not runtime.onboarding.ready:
        status = RuntimeExperienceStatus.DEGRADED
        message = 'Runtime is available with unresolved optional/required onboarding semantics'
        next_actions.append('Resolve onboarding field mappings')
    elif probe is not None and getattr(probe, 'readiness', None) is not None and getattr(probe.readiness, 'value', '') == 'degraded':
        status = RuntimeExperienceStatus.DEGRADED
        message = 'Runtime readiness probe completed with degraded readiness'
    else:
        status = RuntimeExperienceStatus.READY
        message = 'Runtime is ready for the current manufacturing context'
    return RuntimeExperienceState(
        runtime.recipe.key,
        runtime.configuration.variant_key,
        runtime.source.provider,
        status,
        message,
        panel_states,
        runtime.assembly.semiconductor.values,
        len(runtime.selections.selections),
        warnings,
        tuple(dict.fromkeys(next_actions)),
    )


def capture_recipe_runtime_preset(runtime, name: str, *, metadata: Mapping[str, Any] | None = None) -> RecipeRuntimePreset:
    workspace = WorkspaceSnapshot(
        workspace_id=f'semiconductor:{runtime.recipe.key}',
        state=StateSnapshot(0, {}),
        layout=runtime.assembly.workspace.layout.snapshot(),
        data_sessions={},
        analysis=runtime.context.snapshot(),
        selections=runtime.selections.snapshot(),
        interactions=runtime.assembly.workspace.snapshot(),
    )
    return RecipeRuntimePreset(name, runtime.recipe.key, runtime.configuration.variant_key, workspace, metadata or {})


def recipe_runtime_preset_to_dict(preset: RecipeRuntimePreset) -> dict[str, Any]:
    return {
        'schema_version': preset.schema_version,
        'name': preset.name,
        'recipe_key': preset.recipe_key,
        'variant_key': preset.variant_key,
        'metadata': dict(preset.metadata),
        'workspace': workspace_snapshot_to_dict(preset.workspace),
    }


def recipe_runtime_preset_from_dict(payload: Mapping[str, Any]) -> RecipeRuntimePreset:
    if int(payload.get('schema_version', 0)) != 1:
        raise ValueError(f'unsupported recipe runtime preset schema {payload.get("schema_version")!r}')
    workspace_payload = payload.get('workspace')
    if not isinstance(workspace_payload, Mapping):
        raise TypeError('recipe runtime preset workspace must be a mapping')
    return RecipeRuntimePreset(
        str(payload['name']),
        str(payload['recipe_key']),
        payload.get('variant_key'),
        workspace_snapshot_from_dict(workspace_payload),
        payload.get('metadata', {}),
    )


def serialize_recipe_runtime_preset(preset: RecipeRuntimePreset, *, indent: int | None = None) -> str:
    return json.dumps(recipe_runtime_preset_to_dict(preset), indent=indent, sort_keys=True, ensure_ascii=False)


def deserialize_recipe_runtime_preset(value: str) -> RecipeRuntimePreset:
    payload = json.loads(value)
    if not isinstance(payload, Mapping):
        raise TypeError('recipe runtime preset JSON must contain an object')
    return recipe_runtime_preset_from_dict(payload)


def _snapshot_filter_fields(snapshot) -> tuple[str, ...]:
    fields: list[str] = []
    for expression in snapshot.filters:
        fields.extend(fields_in_filter(expression))
    if snapshot.time_range is not None:
        fields.append(snapshot.time_range.field)
    for population in (snapshot.affected, snapshot.control, snapshot.baseline):
        if population is not None:
            fields.extend(fields_in_filter(population.filter))
    return tuple(dict.fromkeys(fields))


async def restore_recipe_runtime_preset(runtime, preset: RecipeRuntimePreset, *, strict_variant: bool = True) -> None:
    if preset.recipe_key != runtime.recipe.key:
        raise ValueError(f'preset is for recipe {preset.recipe_key!r}, not {runtime.recipe.key!r}')
    if strict_variant and preset.variant_key != runtime.configuration.variant_key:
        raise ValueError(f'preset variant {preset.variant_key!r} does not match runtime variant {runtime.configuration.variant_key!r}')
    schema = await runtime.source.schema()
    analysis = preset.workspace.analysis
    if analysis is None:
        raise ValueError('recipe runtime preset does not contain analysis context')
    unknown_fields = set(_snapshot_filter_fields(analysis)) - set(schema.names)
    if unknown_fields:
        raise KeyError(f'preset analysis context references fields unavailable in the current source: {sorted(unknown_fields)!r}')
    current_panels = set(runtime.assembly.workspace.layout.panels)
    preset_panels = {item.panel_id for item in preset.workspace.layout.panels}
    if preset_panels != current_panels:
        raise ValueError('preset workspace panels do not match the current resolved recipe configuration')
    current_source = runtime.source.key
    runtime.assembly.workspace.layout.restore(preset.workspace.layout)
    if preset.workspace.interactions is not None:
        runtime.assembly.workspace.restore(preset.workspace.interactions)
    runtime.context.restore(replace(analysis, source_key=current_source))
    if preset.workspace.selections is not None:
        runtime.selections.restore(preset.workspace.selections, source='recipe-runtime-preset')


def _performance_observation(operation: str, result) -> RuntimePerformanceObservation:
    return RuntimePerformanceObservation(operation, result.stats.elapsed_ms, len(result.rows), result.filtered_total, result.stats.pushdown, result.stats.rows_scanned)


def _check_performance_observation(observation: RuntimePerformanceObservation, diagnostics: list[AdapterDiagnostic], policy: RuntimePerformancePolicy, *, require_pushdown: bool) -> None:
    if require_pushdown and not observation.pushdown:
        diagnostics.append(AdapterDiagnostic(f'{observation.operation}_pushdown_not_observed', ConformanceSeverity.ERROR, f'{observation.operation} did not report backend pushdown'))
    if policy.max_query_elapsed_ms is not None and observation.elapsed_ms > policy.max_query_elapsed_ms:
        diagnostics.append(AdapterDiagnostic(f'{observation.operation}_latency_exceeded', ConformanceSeverity.ERROR, f'{observation.operation} exceeded the configured performance budget', {'elapsed_ms': observation.elapsed_ms, 'budget_ms': policy.max_query_elapsed_ms}))
    if policy.max_rows_scanned_per_returned_row is not None and observation.rows_scanned is not None:
        denominator = max(1, observation.rows_returned)
        ratio = observation.rows_scanned / denominator
        if ratio > policy.max_rows_scanned_per_returned_row:
            diagnostics.append(AdapterDiagnostic(f'{observation.operation}_scan_amplification', ConformanceSeverity.ERROR, f'{observation.operation} scanned too many rows per returned row', {'ratio': ratio, 'budget': policy.max_rows_scanned_per_returned_row}))


async def probe_semiconductor_runtime_performance(runtime, *, policy: RuntimePerformancePolicy = RuntimePerformancePolicy()) -> RuntimePerformanceReport:
    """Run bounded runtime queries that make pushdown claims observable without loading the source."""
    diagnostics: list[AdapterDiagnostic] = []
    observations: list[RuntimePerformanceObservation] = []
    projection = tuple(dict.fromkeys(runtime.bindings.values()))[:8]
    base = runtime.context.query(Query(limit=policy.page_size, projection=projection))
    first = await runtime.source.query(base)
    first_obs = _performance_observation('context_page', first)
    observations.append(first_obs)
    _check_performance_observation(first_obs, diagnostics, policy, require_pushdown=policy.require_projection_pushdown)
    if len(first.rows) > policy.page_size:
        diagnostics.append(AdapterDiagnostic('context_page_limit_violated', ConformanceSeverity.ERROR, 'context page returned more rows than requested'))

    second = await runtime.source.query(runtime.context.query(Query(offset=policy.page_size, limit=policy.page_size, projection=projection)))
    second_obs = _performance_observation('pagination', second)
    observations.append(second_obs)
    _check_performance_observation(second_obs, diagnostics, policy, require_pushdown=policy.require_pagination_pushdown)

    if projection and first.rows:
        field = projection[0]
        value = first.rows[0].get(field)
        filtered = await runtime.source.query(runtime.context.query(Query(filter=Comparison(field, ComparisonOperator.EQ, value), limit=policy.page_size, projection=projection)))
        filtered_obs = _performance_observation('filter', filtered)
        observations.append(filtered_obs)
        _check_performance_observation(filtered_obs, diagnostics, policy, require_pushdown=policy.require_filter_pushdown)

    caps = runtime.source.capabilities
    for attr, required in (
        ('filter_pushdown', policy.require_filter_pushdown),
        ('pagination_pushdown', policy.require_pagination_pushdown),
        ('projection_pushdown', policy.require_projection_pushdown),
    ):
        if required and not getattr(caps, attr):
            diagnostics.append(AdapterDiagnostic(f'missing_{attr}', ConformanceSeverity.ERROR, f'production performance policy requires {attr.replace("_", " ")}'))
    if not diagnostics:
        diagnostics.append(AdapterDiagnostic('runtime_performance_pass', ConformanceSeverity.INFO, 'bounded runtime pushdown probes completed without findings'))
    return RuntimePerformanceReport(runtime.recipe.key, runtime.source.key, runtime.source.provider, tuple(observations), tuple(diagnostics))


__all__ = [
    'RecipeRuntimePreset','RuntimeExperienceState','RuntimeExperienceStatus','RuntimePerformanceObservation',
    'RuntimePerformancePolicy','RuntimePerformanceReport','build_runtime_experience_state','capture_recipe_runtime_preset',
    'deserialize_recipe_runtime_preset','probe_semiconductor_runtime_performance','recipe_runtime_preset_from_dict',
    'recipe_runtime_preset_to_dict','restore_recipe_runtime_preset','serialize_recipe_runtime_preset',
]
