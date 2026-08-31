from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from nicegui_base.ai.models import AiConstructionDefinition
from nicegui_base.components.registry import COMPONENT_REGISTRY
from nicegui_base.content.registry import CONTENT_REGISTRY
from nicegui_base.convenience_registry import CONVENIENCE_REGISTRY
from nicegui_base.data_table.registry import TABLE_REGISTRY
from nicegui_base.data_sources import DATA_SOURCE_PROVIDERS
from nicegui_base.engineering.registry import ENGINEERING_REGISTRY
from nicegui_base.interaction_registry import INTERACTION_REGISTRY
from nicegui_base.jobs import JOB_REGISTRY
from nicegui_base.patterns.registry import PATTERN_REGISTRY
from nicegui_base.performance import PERFORMANCE_REGISTRY
from nicegui_base.runtime.registry import RUNTIME_REGISTRY
from nicegui_base.security.registry import SECURITY_REGISTRY
from nicegui_base.semiconductor import (
    PROVIDER_CONFORMANCE_PROFILES,
    RECIPE_OPERATIONAL_GUARDRAILS,
    SEMICONDUCTOR_BENCHMARK_PROFILES,
    SEMICONDUCTOR_RECIPE_REGISTRY,
    SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY,
    SEMICONDUCTOR_SURFACE_REGISTRY,
    SEMICONDUCTOR_OPERATIONAL_RUNBOOKS,
)
from nicegui_base.visual.registry import ICON_REGISTRY, ILLUSTRATION_REGISTRY
from nicegui_base.visualization.registry import VISUALIZATION_REGISTRY

_ITEMS = {
    'page_pattern': AiConstructionDefinition(
        'page_pattern', 'A new page or application screen is requested.', 'nicegui_base.patterns.*',
        'PATTERN_REGISTRY / docs/APP_PATTERNS.md', 'Freehand page composition with raw NiceGUI layout.',
        'Page patterns own information hierarchy and responsive transformations.'),
    'layout': AiConstructionDefinition(
        'layout', 'A page needs columns, stacks, split panes, inspectors or responsive rearrangement.', 'nicegui_base.layouts.*',
        'docs/LAYOUT_RULES.md', 'ui.row/ui.column/ui.grid or arbitrary CSS geometry.',
        'Semantic layout primitives preserve approved spacing and breakpoints.'),
    'component': AiConstructionDefinition(
        'component', 'A button, input, status, surface or basic control is needed.', 'nicegui_base components/integrations',
        'COMPONENT_REGISTRY / docs/COMPONENT_CATALOG.md', 'Raw ui.button/ui.input/ui.select or custom control styling.',
        'Framework components own visual states, accessibility, density and theme behavior.'),
    'content': AiConstructionDefinition(
        'content', 'Metrics, detail/property presentation, hierarchy, viewers, workflow steps, comparisons, search results or command UI are needed.', 'nicegui_base.content + integrations',
        'CONTENT_REGISTRY / docs/COMPONENT_CATALOG.md', 'Ad-hoc KPI cards, property markup, raw tree/viewer/stepper composition or custom command modals.',
        'Content primitives complete the common enterprise UI vocabulary while inheriting NiceGUI Base accessibility and design laws.'),
    'form_filter_overlay': AiConstructionDefinition(
        'form_filter_overlay', 'Forms, analytical filters, dialogs, drawers, menus or feedback are needed.', 'nicegui_base.forms/filters/overlays/feedback',
        'INTERACTION_REGISTRY / docs/RECIPES.md', 'Ad-hoc modal/drawer/toast markup.',
        'The interaction grammar defines when each surface is appropriate and how it behaves.'),
    'table': AiConstructionDefinition(
        'table', 'Rows/columns, records, selection, editing or large datasets are required.', 'nicegui_base.data_table + integrations.DataTable',
        'TABLE_REGISTRY / docs/COMPONENT_CATALOG.md', 'Raw ui.aggrid or manually rendered HTML tables.',
        'The DataTable subsystem owns enterprise interaction, persistence and server-side contracts.'),
    'data_source': AiConstructionDefinition(
        'data_source', 'Application data must come from SQL, CSV, an in-memory fixture or another production provider.', 'nicegui_base.data_sources',
        'DATA_SOURCE_PROVIDERS / DATA_SOURCE_GUIDE.md', 'Page-local database calls, loading full production tables into memory, or provider-specific query code in UI modules.',
        'The DataSource contract owns semantic schema, typed queries, pushdown, provenance, cancellation and backend portability.'),
    'visualization': AiConstructionDefinition(
        'visualization', 'A chart, trend, distribution, Pareto, control chart or spatial analysis is required.', 'nicegui_base.visualization',
        'VISUALIZATION_REGISTRY / docs/COMPONENT_CATALOG.md', 'Raw ui.echart, arbitrary palettes or per-app ECharts styling.',
        'The chart layer owns theme, grammar, cross-filter behavior and engineering annotations.'),
    'visual_asset': AiConstructionDefinition(
        'visual_asset', 'An icon, state illustration or dataviz marker is required.', 'Icons.*, Illustrations.*, visual registries',
        'ICON_REGISTRY / docs/ICON_CATALOG.md', 'Emoji, downloaded SVGs or arbitrary icon-name strings.',
        'Canonical semantic assets make recognition deterministic and keep the package offline.'),
    'state_async': AiConstructionDefinition(
        'state_async', 'Persistence, URL state, long-running work, refresh, debounce, cancellation or shortcuts are needed.', 'nicegui_base.state/async_tools/services',
        'CONVENIENCE_REGISTRY / docs/RECIPES.md', 'Direct app.storage manipulation, custom timers or duplicate async logic.',
        'Convenience primitives prevent stale results, duplicate work and inconsistent persistence.'),
    'jobs': AiConstructionDefinition(
        'jobs', 'Work must outlive a request or may need restart-survivable execution.', 'nicegui_base.jobs',
        'JOB_REGISTRY / docs/PERFORMANCE_GUIDE.md', 'Raw asyncio.create_task for business-critical long work.',
        'The durable-job contract lets app code move from in-process tasks to a company scheduler without UI rewrites.'),
    'engineering': AiConstructionDefinition(
        'engineering', 'Semiconductor entities, limits, affected/control comparison, commonality, evidence or RCA are needed.', 'nicegui_base.engineering',
        'ENGINEERING_REGISTRY / docs/COMPONENT_CATALOG.md', 'Reinvented domain status/limits or causal claims from simple overlap.',
        'Domain primitives preserve analytical semantics and evidence/causality boundaries.'),
    'semiconductor': AiConstructionDefinition(
        'semiconductor', 'Semiconductor SPC, wafer/spatial, FDC, commonality, yield, reliability or DOE analytics are needed.', 'nicegui_base.semiconductor.* + SemiconductorAnalyticalPanel',
        'SEMICONDUCTOR_RECIPE_REGISTRY + SEMICONDUCTOR_SURFACE_REGISTRY / docs/SEMICONDUCTOR_APPLICATION_RECIPES.md', 'Page-local SPC formulas, ad-hoc wafer renderers, isolated FDC/RCA population state, or hand-assembled app layouts that duplicate a registered recipe.',
        'Wave 67 adds enterprise evidence assimilation, deterministic stable-channel candidates, actionable promotion gaps, candidate packaging and provider-neutral operational rehearsal recording above Wave 66 qualification/promotion while preserving the Wave 59–64 DataSource, AnalysisContext, SelectionBus, workspace, recipe, onboarding, runtime and conformance authorities.'),
    'performance': AiConstructionDefinition(
        'performance', 'Repeated data work, large local tables, hidden expensive content or backend fan-out needs optimization.', 'nicegui_base.performance',
        'PERFORMANCE_REGISTRY / docs/PERFORMANCE_GUIDE.md', 'Ad-hoc caches, raw background threads, speculative retries or app-specific performance layers.',
        'Performance primitives are bounded, measured, cancellation-aware and documented with explicit avoid-when rules.'),
    'security_runtime': AiConstructionDefinition(
        'security_runtime', 'Authentication, permissions, uploads, logging, proxying, health or deployment are involved.', 'nicegui_base.security/runtime/diagnostics',
        'SECURITY_REGISTRY + RUNTIME_REGISTRY + docs/COMPANY_ENVIRONMENT.md', 'Page-local auth checks, trusted headers without validation, raw secrets or improvised proxy settings.',
        'Security and deployment must remain fail-closed and centrally configurable.'),
}

AI_CONSTRUCTION_REGISTRY: Mapping[str, AiConstructionDefinition] = MappingProxyType(_ITEMS)

FRAMEWORK_REGISTRY_COUNTS = MappingProxyType({
    'components': len(COMPONENT_REGISTRY),
    'content': len(CONTENT_REGISTRY),
    'page_patterns': len(PATTERN_REGISTRY),
    'interactions': len(INTERACTION_REGISTRY),
    'tables': len(TABLE_REGISTRY),
    'data_source_providers': len(DATA_SOURCE_PROVIDERS),
    'visualizations': len(VISUALIZATION_REGISTRY),
    'engineering': len(ENGINEERING_REGISTRY),
    'semiconductor': len(SEMICONDUCTOR_SURFACE_REGISTRY),
    'semiconductor_recipes': len(SEMICONDUCTOR_RECIPE_REGISTRY),
    'semiconductor_recipe_variants': len(SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY),
    'semiconductor_provider_profiles': len(PROVIDER_CONFORMANCE_PROFILES),
    'semiconductor_benchmark_profiles': len(SEMICONDUCTOR_BENCHMARK_PROFILES),
    'semiconductor_operational_guardrails': sum(len(items) for items in RECIPE_OPERATIONAL_GUARDRAILS.values()),
    'semiconductor_operational_runbooks': len(SEMICONDUCTOR_OPERATIONAL_RUNBOOKS),
    'semiconductor_promotion_policies': 1,
    'semiconductor_evidence_freshness_policies': 1,
    'semiconductor_release_channel_policies': 1,
    'security': len(SECURITY_REGISTRY),
    'runtime': len(RUNTIME_REGISTRY),
    'convenience': len(CONVENIENCE_REGISTRY),
    'performance': len(PERFORMANCE_REGISTRY),
    'jobs': len(JOB_REGISTRY),
    'icons': len(ICON_REGISTRY),
    'illustrations': len(ILLUSTRATION_REGISTRY),
})


def get_ai_construction(key: str) -> AiConstructionDefinition:
    try:
        return AI_CONSTRUCTION_REGISTRY[key]
    except KeyError as exc:
        raise KeyError(f'Unknown AI construction category: {key}') from exc
