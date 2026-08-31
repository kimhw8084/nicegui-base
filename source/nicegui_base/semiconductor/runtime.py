from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from nicegui_base.analysis import AnalysisContext, AnalysisStatus, Selection, SelectionBus, SelectionKind, SelectionMutationMode
from nicegui_base.data_sources import DataSource, Query, QueryResult

from .onboarding import RecipeOnboardingReport, SemiconductorSourceAdapter, SmartBindingPolicy, onboard_recipe_source, open_semiconductor_source
from .recipes import RecipeCompatibilityError, RecipePanelKind, SemiconductorApplicationAssembly, assemble_semiconductor_application, get_semiconductor_recipe
from .variants import RecipeCustomization, RecipeVariantDefinition, ResolvedRecipeConfiguration, resolve_recipe_configuration


class RuntimeReadiness(str, Enum):
    READY = 'ready'
    DEGRADED = 'degraded'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class RecipeRuntimePolicy:
    strict_bindings: bool = True
    smart_bindings: bool = True
    record_page_size: int = 100
    readiness_probe_rows: int = 1

    def __post_init__(self) -> None:
        if self.record_page_size < 1 or self.record_page_size > 10_000:
            raise ValueError('record_page_size must be between 1 and 10000')
        if self.readiness_probe_rows < 1 or self.readiness_probe_rows > 100:
            raise ValueError('readiness_probe_rows must be between 1 and 100')


@dataclass(frozen=True, slots=True)
class RuntimeProbeResult:
    readiness: RuntimeReadiness
    rows_available: int
    panel_states: Mapping[str, AnalysisStatus]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'panel_states', MappingProxyType(dict(self.panel_states)))
        object.__setattr__(self, 'warnings', tuple(self.warnings))


@dataclass(slots=True)
class SemiconductorRecipeRuntime:
    configuration: ResolvedRecipeConfiguration
    assembly: SemiconductorApplicationAssembly
    onboarding: RecipeOnboardingReport
    policy: RecipeRuntimePolicy
    adapter_owns_source: bool = False
    adapter_metadata: Mapping[str, Any] = field(default_factory=dict)
    _closed: bool = False
    _refreshing: bool = False
    _unsubscribe_context: Any = None

    def __post_init__(self) -> None:
        self.adapter_metadata = MappingProxyType(dict(self.adapter_metadata))
        self._unsubscribe_context = self.assembly.context.watch(self._context_changed)


    def _context_changed(self, context: AnalysisContext) -> None:
        if self._refreshing or self._closed:
            return
        for surface in self.assembly.surfaces.values():
            if surface.controller.state.status is not AnalysisStatus.LOADING:
                surface.stale('analysis context changed', 'Refresh to apply the current manufacturing context')

    @property
    def recipe(self):
        return self.configuration.recipe

    @property
    def context(self):
        return self.assembly.context

    @property
    def selections(self):
        return self.assembly.selections

    @property
    def source(self):
        return self.assembly.source

    @property
    def bindings(self):
        return self.assembly.bindings

    async def refresh(self) -> RuntimeProbeResult:
        """Bounded production-readiness probe; never loads an entire source into memory."""
        warnings = list(self.onboarding.warnings)
        self._refreshing = True
        try:
            health = await self.source.health()
            if not health.healthy:
                error = RuntimeError(health.message or f'source health is {health.status.value}')
                for surface in self.assembly.surfaces.values():
                    surface.error(error)
                return RuntimeProbeResult(RuntimeReadiness.BLOCKED, 0, {key: surface.controller.state.status for key, surface in self.assembly.surfaces.items()}, tuple(warnings))
            for surface in self.assembly.surfaces.values():
                surface.loading('Refreshing shared analysis context')
            try:
                query = self.context.query(Query(limit=self.policy.readiness_probe_rows))
                result = await self.source.query(query)
            except BaseException as exc:
                for surface in self.assembly.surfaces.values():
                    surface.error(exc)
                return RuntimeProbeResult(RuntimeReadiness.BLOCKED, 0, {key: surface.controller.state.status for key, surface in self.assembly.surfaces.items()}, tuple(warnings + [str(exc)]))
            if result.filtered_total == 0:
                for surface in self.assembly.surfaces.values():
                    surface.empty('No rows match the current manufacturing context')
                readiness = RuntimeReadiness.DEGRADED
            else:
                for surface in self.assembly.surfaces.values():
                    surface.ready(f'{result.filtered_total} rows in current context')
                readiness = RuntimeReadiness.READY if self.onboarding.ready else RuntimeReadiness.DEGRADED
            self.context.set_freshness(as_of=result.provenance.queried_at, freshness_at=health.freshness_at or result.provenance.queried_at)
            return RuntimeProbeResult(readiness, result.filtered_total, {key: surface.controller.state.status for key, surface in self.assembly.surfaces.items()}, tuple(warnings))
        finally:
            self._refreshing = False

    async def records(self, *, offset: int = 0, limit: int | None = None, projection: tuple[str, ...] = ()) -> QueryResult:
        if offset < 0:
            raise ValueError('offset must be >= 0')
        size = self.policy.record_page_size if limit is None else limit
        if size < 1 or size > 10_000:
            raise ValueError('limit must be between 1 and 10000')
        query = self.context.query(Query(offset=offset, limit=size, projection=projection))
        return await self.source.query(query)

    def set_manufacturing_filter(self, key: str, value: Any | None) -> None:
        if key not in self.assembly.compatibility.available_filters:
            raise KeyError(f'manufacturing filter {key!r} is unavailable for this source schema')
        self.assembly.manufacturing_filters.set(key, value)

    async def filter_options(self, key: str) -> tuple[Any, ...]:
        if key not in self.assembly.compatibility.available_filters:
            return ()
        return await self.assembly.manufacturing_filters.options(key)

    def select(self, kind: SelectionKind, selection_id: str, values: Mapping[str, Any], *, source: str = 'recipe-runtime', mode: SelectionMutationMode = SelectionMutationMode.REPLACE):
        return self.selections.apply(Selection(kind, selection_id, values, source=source), mode=mode, source=source)

    def onboarding_view(self):
        from .onboarding import build_recipe_onboarding_view
        return build_recipe_onboarding_view(self.recipe, self.onboarding)

    def experience_state(self, probe: RuntimeProbeResult | None = None):
        from .runtime_experience import build_runtime_experience_state
        return build_runtime_experience_state(self, probe)

    def capture_preset(self, name: str, *, metadata: Mapping[str, Any] | None = None):
        from .runtime_experience import capture_recipe_runtime_preset
        return capture_recipe_runtime_preset(self, name, metadata=metadata)

    async def restore_preset(self, preset, *, strict_variant: bool = True) -> None:
        from .runtime_experience import restore_recipe_runtime_preset
        await restore_recipe_runtime_preset(self, preset, strict_variant=strict_variant)

    async def performance_report(self, *, policy=None):
        from .runtime_experience import RuntimePerformancePolicy, probe_semiconductor_runtime_performance
        return await probe_semiconductor_runtime_performance(self, policy=policy or RuntimePerformancePolicy())

    async def benchmark(self, *, profile='provider-rc'):
        from .benchmarking import run_semiconductor_runtime_benchmark
        return await run_semiconductor_runtime_benchmark(self, profile=profile)

    def configuration_review(self, *, adapter_conformance=None, benchmark=None):
        from .operations import review_recipe_configuration
        return review_recipe_configuration(self, adapter_conformance=adapter_conformance, benchmark=benchmark)

    def setup_workflow(self, *, probe=None, adapter_conformance=None, benchmark=None, target_certification=None):
        from .setup_workflow import build_recipe_setup_workflow
        return build_recipe_setup_workflow(self, probe=probe, adapter_conformance=adapter_conformance, benchmark=benchmark, target_certification=target_certification)

    async def prepare_setup_workflow(self, *, adapter_conformance=None, benchmark=None, target_certification=None, refresh=True):
        from .setup_workflow import prepare_recipe_setup_workflow
        return await prepare_recipe_setup_workflow(self, adapter_conformance=adapter_conformance, benchmark=benchmark, target_certification=target_certification, refresh=refresh)

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._unsubscribe_context is not None:
            self._unsubscribe_context(); self._unsubscribe_context = None
        await self.assembly.aclose(close_source=self.adapter_owns_source)


async def create_semiconductor_recipe_runtime(
    recipe: str,
    source_or_adapter: DataSource | SemiconductorSourceAdapter,
    *,
    variant: str | RecipeVariantDefinition | None = None,
    customization: RecipeCustomization | None = None,
    field_overrides: Mapping[str, str] | None = None,
    context: AnalysisContext | None = None,
    selections: SelectionBus | None = None,
    policy: RecipeRuntimePolicy = RecipeRuntimePolicy(),
    binding_policy: SmartBindingPolicy = SmartBindingPolicy(),
) -> SemiconductorRecipeRuntime:
    base = get_semiconductor_recipe(recipe)
    configuration = resolve_recipe_configuration(base, variant=variant, customization=customization)
    adapted = await open_semiconductor_source(configuration.recipe, source_or_adapter)
    explicit = dict(configuration.field_overrides)
    explicit.update(adapted.field_overrides)
    explicit.update(field_overrides or {})
    onboarding = await onboard_recipe_source(configuration.recipe, adapted.source, field_overrides=explicit, policy=binding_policy, adapter_metadata=adapted.metadata)
    overrides = dict(onboarding.recommended_overrides) if policy.smart_bindings else explicit
    overrides.update(explicit)
    if policy.strict_bindings and not onboarding.compatibility.compatible:
        if adapted.owns_source:
            await adapted.source.aclose()
        raise RecipeCompatibilityError(onboarding.compatibility)
    try:
        assembly = await assemble_semiconductor_application(
            configuration.recipe, adapted.source, context=context, selections=selections,
            field_overrides=overrides, strict=policy.strict_bindings,
        )
    except BaseException:
        if adapted.owns_source:
            await adapted.source.aclose()
        raise
    unavailable_initial = set(configuration.initial_filters) - set(assembly.compatibility.available_filters)
    if unavailable_initial:
        await assembly.aclose(close_source=adapted.owns_source)
        raise KeyError(f'initial manufacturing filters unavailable for source schema: {sorted(unavailable_initial)!r}')
    if configuration.initial_filters:
        assembly.semiconductor.set_many(**dict(configuration.initial_filters))
    metadata = assembly.context.metadata
    metadata['semiconductor_runtime'] = {
        'recipe_key': configuration.recipe.key,
        'variant_key': configuration.variant_key,
        'provider': adapted.source.provider,
        'onboarding_ready': onboarding.ready,
        'adapter_metadata': dict(adapted.metadata),
    }
    assembly.context.set_metadata(metadata)
    return SemiconductorRecipeRuntime(configuration, assembly, onboarding, policy, adapted.owns_source, adapted.metadata)


__all__ = [
    'RecipeRuntimePolicy','RuntimeProbeResult','RuntimeReadiness','SemiconductorRecipeRuntime','create_semiconductor_recipe_runtime',
]
