from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .project_codegen import is_composable_entry
from .search import score_entry


@dataclass(frozen=True, slots=True)
class CapabilityIntent:
    query: str
    preferred_slots: tuple[str, ...]
    family: str = ''
    required: bool = False
    preferred_keys: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GoldenStarterSpec:
    key: str
    title: str
    description: str
    category: str
    pattern_key: str
    goal: str
    problem_type: str
    intents: tuple[CapabilityIntent, ...]
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StarterResolution:
    starter_key: str
    pattern_key: str
    placements: Mapping[str, tuple[str, ...]]
    selected_keys: tuple[str, ...]
    unresolved: tuple[str, ...]
    reasons: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.unresolved


@dataclass(frozen=True, slots=True)
class CompositionDiff:
    added: tuple[tuple[str, str], ...]
    removed: tuple[tuple[str, str], ...]
    moved: tuple[tuple[str, str, str], ...]

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed or self.moved)


_MONITORING_INTENTS = (
    CapabilityIntent('status health badge', ('metrics', 'primary'), 'status_badge', preferred_keys=('component:badge',)),
    CapabilityIntent('alert warning status', ('metrics', 'primary'), 'alert', preferred_keys=('framework:interactions:alert',)),
    CapabilityIntent('line chart trend time', ('primary', 'secondary'), 'visualization', True, ('framework:visualizations:LineChart',)),
    CapabilityIntent('data table records', ('data', 'details'), 'table', preferred_keys=('framework:tables:data_table',)),
    CapabilityIntent('select filter', ('filters',), 'select', preferred_keys=('component:select',)),
)

_EXPLORER_INTENTS = (
    CapabilityIntent('search input', ('filters',), 'search_input', preferred_keys=('component:search_input',)),
    CapabilityIntent('select filter', ('filters',), 'select', preferred_keys=('component:select',)),
    CapabilityIntent('data table records', ('data',), 'table', True, ('framework:tables:data_table',)),
    CapabilityIntent('line chart trend', ('primary', 'secondary'), 'visualization', preferred_keys=('framework:visualizations:LineChart',)),
)

_COMPARISON_INTENTS = (
    CapabilityIntent('comparison baseline affected control', ('primary',), 'analytic', True, ('analytics:rca_affected_control',)),
    CapabilityIntent('box distribution compare', ('secondary', 'primary'), 'visualization', preferred_keys=('framework:visualizations:BoxPlot',)),
    CapabilityIntent('data table records', ('data',), 'table', preferred_keys=('framework:tables:data_table',)),
    CapabilityIntent('metric card delta', ('metrics', 'details'), 'metric_card', preferred_keys=('framework:content:metric_card',)),
    CapabilityIntent('select filter', ('filters',), 'select', preferred_keys=('component:select',)),
)

_ANALYSIS_INTENTS = (
    CapabilityIntent('root cause rca analysis', ('primary',), 'analytic', True, ('analytics:rca_commonality_ranking',)),
    CapabilityIntent('line chart trend', ('secondary', 'primary'), 'visualization', preferred_keys=('framework:visualizations:LineChart',)),
    CapabilityIntent('data table evidence', ('data',), 'table', preferred_keys=('framework:tables:data_table',)),
    CapabilityIntent('select filter', ('filters',), 'select', preferred_keys=('component:select',)),
)


GOLDEN_STARTERS: tuple[GoldenStarterSpec, ...] = (
    GoldenStarterSpec(
        'spc-defense-line', 'SPC Defense Line',
        'Operational SPC page with status, control trend, filters and affected records.',
        'Engineering', 'monitoring',
        'Monitor process stability, surface control-limit excursions immediately, and inspect affected measurements.',
        'engineering analysis',
        (
            CapabilityIntent('spc i mr control chart', ('primary',), 'analytic', True, ('analytics:spc_i_mr',)),
            *_MONITORING_INTENTS,
        ),
        ('spc', 'monitoring', 'defense line'),
    ),
    GoldenStarterSpec(
        'fdc-tool-health', 'FDC Tool Health',
        'Tool/chamber monitoring workspace for sensor drift, health status and affected records.',
        'Engineering', 'monitoring',
        'Monitor FDC sensor behavior and compare tool or chamber health before excursions propagate.',
        'engineering analysis',
        (
            CapabilityIntent('fdc multi sensor', ('primary',), 'analytic', True, ('analytics:fdc_multi_sensor',)),
            CapabilityIntent('fdc tool chamber compare', ('secondary',), 'analytic', preferred_keys=('analytics:fdc_tool_chamber_compare',)),
            *_MONITORING_INTENTS,
        ),
        ('fdc', 'tool health', 'chamber'),
    ),
    GoldenStarterSpec(
        'lot-wafer-explorer', 'Lot / Wafer Explorer',
        'Searchable lot/wafer investigation page with wafer visualization and record drill-down.',
        'Engineering', 'data_explorer',
        'Explore lots and wafers, filter populations, inspect wafer spatial behavior, and drill into measurements.',
        'engineering analysis',
        (
            CapabilityIntent('wafer continuous map', ('primary',), 'analytic', True, ('analytics:wafer_continuous',)),
            CapabilityIntent('wafer comparison', ('secondary',), 'analytic', preferred_keys=('analytics:wafer_comparison',)),
            *_EXPLORER_INTENTS,
        ),
        ('wafer', 'lot', 'explorer'),
    ),
    GoldenStarterSpec(
        'yield-loss-investigation', 'Yield Loss Investigation',
        'Dense analytical workspace for yield Pareto, loss waterfall and supporting evidence.',
        'Engineering', 'analysis_workspace',
        'Investigate yield loss, rank dominant contributors, compare populations, and preserve evidence context.',
        'engineering analysis',
        (
            CapabilityIntent('yield pareto', ('primary',), 'analytic', True, ('analytics:yield_pareto',)),
            CapabilityIntent('yield waterfall', ('secondary',), 'analytic', preferred_keys=('analytics:yield_waterfall',)),
            CapabilityIntent('data table evidence', ('data',), 'table', preferred_keys=('framework:tables:data_table',)),
            CapabilityIntent('select filter', ('filters',), 'select', preferred_keys=('component:select',)),
        ),
        ('yield', 'pareto', 'investigation'),
    ),
    GoldenStarterSpec(
        'pm-effect-analysis', 'PM Effect Analysis',
        'Baseline/current comparison for maintenance-effect verification.',
        'Engineering', 'comparison',
        'Compare pre-PM and post-PM populations, quantify shifts, and inspect affected measurements.',
        'engineering analysis',
        _COMPARISON_INTENTS,
        ('pm', 'comparison', 'baseline'),
    ),
    GoldenStarterSpec(
        'chamber-matching', 'Chamber Matching',
        'Side-by-side chamber fingerprint and distribution comparison.',
        'Engineering', 'comparison',
        'Compare chambers, identify fingerprint differences, and inspect supporting measurement populations.',
        'engineering analysis',
        (
            CapabilityIntent('fdc chamber fingerprint', ('primary',), 'analytic', True, ('analytics:fdc_chamber_fingerprint',)),
            CapabilityIntent('fdc tool chamber compare', ('secondary',), 'analytic', preferred_keys=('analytics:fdc_tool_chamber_compare',)),
            CapabilityIntent('data table records', ('data',), 'table', preferred_keys=('framework:tables:data_table',)),
            CapabilityIntent('select filter', ('filters',), 'select', preferred_keys=('component:select',)),
        ),
        ('chamber', 'matching', 'fingerprint'),
    ),
    GoldenStarterSpec(
        'rca-cockpit', 'RCA Cockpit',
        'Evidence-first root-cause workspace for ranking, relationships and supporting records.',
        'Engineering', 'analysis_workspace',
        'Investigate an excursion, rank commonalities, correlate evidence, and preserve root-cause context.',
        'engineering analysis',
        (
            CapabilityIntent('rca commonality ranking', ('primary',), 'analytic', True, ('analytics:rca_commonality_ranking',)),
            CapabilityIntent('rca evidence matrix', ('secondary',), 'analytic', preferred_keys=('analytics:rca_evidence_matrix',)),
            CapabilityIntent('data table evidence', ('data',), 'table', preferred_keys=('framework:tables:data_table',)),
            CapabilityIntent('select filter', ('filters',), 'select', preferred_keys=('component:select',)),
        ),
        ('rca', 'evidence', 'investigation'),
    ),
    GoldenStarterSpec(
        'process-capability-review', 'Process Capability Review',
        'Capability and stability overview with distribution, trend and records.',
        'Engineering', 'dashboard',
        'Review process capability and stability with specification context, trends, and supporting records.',
        'engineering analysis',
        (
            CapabilityIntent('capability histogram', ('primary',), 'analytic', True, ('analytics:capability_histogram',)),
            CapabilityIntent('spc i mr', ('secondary',), 'analytic', preferred_keys=('analytics:spc_i_mr',)),
            CapabilityIntent('metric card', ('metrics',), 'metric_card', preferred_keys=('framework:content:metric_card',)),
            CapabilityIntent('data table records', ('data',), 'table', preferred_keys=('framework:tables:data_table',)),
        ),
        ('capability', 'spc', 'dashboard'),
    ),
    GoldenStarterSpec(
        'operations-dashboard', 'Operations Dashboard',
        'Generic KPI/trend/records dashboard for an operational process.',
        'Generic', 'dashboard',
        'Summarize operational KPIs, trends, exceptions, and records in one reusable dashboard.',
        'generic application',
        (
            CapabilityIntent('metric card', ('metrics',), 'metric_card', True, ('framework:content:metric_card',)),
            CapabilityIntent('line chart trend', ('primary',), 'visualization', True),
            CapabilityIntent('bar chart', ('secondary',), 'visualization', preferred_keys=('framework:visualizations:BarChart',)),
            CapabilityIntent('data table records', ('data',), 'table', preferred_keys=('framework:tables:data_table',)),
            CapabilityIntent('select filter', ('filters',), 'select', preferred_keys=('component:select',)),
        ),
        ('dashboard', 'kpi', 'operations'),
    ),
    GoldenStarterSpec(
        'generic-data-explorer', 'Data Explorer',
        'Search, filter, visualize and inspect arbitrary tabular records.',
        'Generic', 'data_explorer',
        'Explore and filter records, visualize the current population, and inspect details quickly.',
        'generic application', _EXPLORER_INTENTS,
        ('data', 'table', 'explorer'),
    ),
    GoldenStarterSpec(
        'record-manager', 'Record Manager',
        'Table-centered CRUD starter with search, edit controls and actions.',
        'Generic', 'crud',
        'Search, create, inspect, edit and manage application records consistently.',
        'generic application',
        (
            CapabilityIntent('search input', ('filters',), 'search_input', preferred_keys=('component:search_input',)),
            CapabilityIntent('data table records', ('data',), 'table', True, ('framework:tables:data_table',)),
            CapabilityIntent('text input', ('details',), 'text_input', preferred_keys=('component:text_input',)),
            CapabilityIntent('action button', ('actions',), 'action_button', preferred_keys=('component:action_button',)),
        ),
        ('crud', 'records', 'edit'),
    ),
    GoldenStarterSpec(
        'master-detail-inspector', 'Master / Detail Inspector',
        'Entity list plus persistent detail context.',
        'Generic', 'master_detail',
        'Browse entities while keeping the selected entity details and supporting metadata visible.',
        'generic application',
        (
            CapabilityIntent('data table records', ('data',), 'table', True, ('framework:tables:data_table',)),
            CapabilityIntent('metric card', ('details',), 'metric_card', True),
            CapabilityIntent('select filter', ('filters',), 'select', preferred_keys=('component:select',)),
        ),
        ('master detail', 'entity', 'inspect'),
    ),
    GoldenStarterSpec(
        'configuration-center', 'Configuration Center',
        'Structured settings application with navigation, fields and save actions.',
        'Generic', 'settings',
        'Manage structured application configuration with clear navigation and bounded save actions.',
        'generic application',
        (
            CapabilityIntent('select', ('navigation',), 'select', True),
            CapabilityIntent('text input', ('content',), 'text_input', True, ('component:text_input',)),
            CapabilityIntent('action button', ('actions',), 'action_button', preferred_keys=('component:action_button',)),
        ),
        ('settings', 'configuration', 'forms'),
    ),
    GoldenStarterSpec(
        'guided-workflow', 'Guided Workflow',
        'Constrained multi-step workflow with input and actions.',
        'Generic', 'wizard',
        'Guide a user through a bounded multi-step workflow with minimal decision overhead.',
        'generic application',
        (
            CapabilityIntent('select', ('navigation', 'content'), 'select'),
            CapabilityIntent('text input', ('content',), 'text_input', True, ('component:text_input',)),
            CapabilityIntent('action button', ('actions',), 'action_button', True, ('component:action_button',)),
        ),
        ('wizard', 'workflow', 'guided'),
    ),
    GoldenStarterSpec(
        'comparison-workbench', 'Comparison Workbench',
        'Generic baseline/current comparison with metrics and records.',
        'Generic', 'comparison',
        'Compare two populations or scenarios, summarize deltas, and inspect underlying records.',
        'generic application', _COMPARISON_INTENTS,
        ('comparison', 'baseline', 'delta'),
    ),
    GoldenStarterSpec(
        'engineering-analysis', 'Engineering Analysis Workspace',
        'General-purpose dense engineering investigation workspace.',
        'Engineering', 'analysis_workspace',
        'Investigate engineering data with a primary analytical view, secondary context, filters, and evidence records.',
        'engineering analysis', _ANALYSIS_INTENTS,
        ('analysis', 'engineering', 'workspace'),
    ),
)

_STARTER_BY_KEY = {item.key: item for item in GOLDEN_STARTERS}


def get_golden_starter(key: str) -> GoldenStarterSpec:
    try:
        return _STARTER_BY_KEY[str(key)]
    except KeyError as exc:
        raise KeyError(f'unknown golden starter: {key!r}') from exc


def _kind(entry: Any) -> str:
    return getattr(getattr(entry, 'kind', None), 'value', str(getattr(entry, 'kind', '')))


def _registry(entry: Any) -> str:
    return str(getattr(entry, 'metadata', {}).get('registry_name') or '')


def _registry_key(entry: Any) -> str:
    metadata = getattr(entry, 'metadata', {})
    return str(metadata.get('registry_key') or metadata.get('component_key') or '')


def _family_matches(entry: Any, family: str) -> bool:
    family = str(family or '')
    if not family:
        return True
    if family == 'analytic':
        return _kind(entry) == 'analytic'
    if family == 'table':
        return _registry(entry) == 'tables'
    if family == 'visualization':
        return _registry(entry) == 'visualizations'
    return _registry_key(entry) == family


def _data_boost(entry: Any, data_model: Any | None) -> int:
    if data_model is None:
        return 0
    columns = tuple(getattr(data_model, 'columns', ()) or ())
    roles = {str(getattr(column, 'role', '')) for column in columns}
    types = {str(getattr(column, 'inferred_type', '')) for column in columns}
    boost = 0
    if _kind(entry) == 'analytic' and 'measurement' in roles:
        boost += 30
    if _registry(entry) == 'tables' and len(columns) >= 2:
        boost += 24
    if _registry(entry) == 'visualizations':
        if 'measurement' in roles:
            boost += 18
        if roles & {'dimension', 'timestamp', 'entity'}:
            boost += 12
        if types & {'float', 'integer'}:
            boost += 8
    key = _registry_key(entry)
    if key in {'search_input', 'select'} and roles & {'dimension', 'entity', 'attribute'}:
        boost += 14
    if key in {'metric_card', 'status_badge', 'alert'} and (roles & {'measurement', 'dimension'}):
        boost += 10
    return boost


def _intent_rank(intent: CapabilityIntent, entries: Sequence[Any], data_model: Any | None, used: set[str]) -> list[tuple[int, Any]]:
    ranked: list[tuple[int, Any]] = []
    for entry in entries:
        key = str(getattr(entry, 'key', ''))
        if not key or key in used or not is_composable_entry(entry):
            continue
        family_match = _family_matches(entry, intent.family)
        result = score_entry(entry, intent.query)
        if result is None and not intent.required and not intent.preferred_keys:
            continue
        score = result.score if result is not None else 0
        if family_match:
            score += 130
        elif intent.family:
            score -= 90
        score += _data_boost(entry, data_model)
        if score > 0:
            ranked.append((score, entry))
    ranked.sort(key=lambda item: (-item[0], str(getattr(item[1], 'title', '')).casefold(), str(getattr(item[1], 'key', ''))))
    return ranked


def _fallback_slot(entry: Any, allowed: Sequence[str]) -> str | None:
    allowed_set = set(allowed)
    registry = _registry(entry)
    key = _registry_key(entry)
    kind = _kind(entry)
    candidates: list[str] = []
    if registry == 'tables':
        candidates = ['data', 'details', 'content', 'primary']
    elif registry == 'visualizations' or kind == 'analytic':
        candidates = ['primary', 'secondary', 'content', 'data']
    elif key in {'metric_card', 'metric_strip', 'status_badge', 'alert'}:
        candidates = ['metrics', 'primary', 'details', 'content']
    elif key in {'search_input', 'select'}:
        candidates = ['filters', 'navigation', 'content', 'primary']
    elif key in {'text_input'}:
        candidates = ['content', 'details', 'filters']
    elif key in {'button', 'action_button'}:
        candidates = ['actions', 'content', 'primary']
    for slot in (*candidates, *allowed):
        if slot in allowed_set:
            return slot
    return None


def resolve_starter(spec: GoldenStarterSpec, entries: Iterable[Any], *, data_model: Any | None = None) -> StarterResolution:
    from nicegui_base.patterns.registry import get_pattern
    definition = get_pattern(spec.pattern_key)
    allowed = tuple(slot.value for slot in definition.slot_order if slot.value != 'header')
    available = tuple(entry for entry in entries if is_composable_entry(entry))
    available_by_key = {str(getattr(entry, 'key', '')): entry for entry in available}
    placements: dict[str, list[str]] = {}
    used: set[str] = set()
    selected: list[str] = []
    unresolved: list[str] = []
    reasons: list[str] = [f'Pattern: {definition.pattern.value} · {definition.purpose}']
    for intent in spec.intents:
        exact = next((available_by_key[key] for key in intent.preferred_keys if key in available_by_key and key not in used), None)
        if exact is not None:
            score, entry = 10_000, exact
        else:
            ranked = _intent_rank(intent, available, data_model, used)
            if not ranked:
                if intent.required:
                    unresolved.append(intent.query)
                continue
            score, entry = ranked[0]
        slot = next((slot for slot in intent.preferred_slots if slot in allowed), None) or _fallback_slot(entry, allowed)
        if slot is None:
            if intent.required:
                unresolved.append(intent.query)
            continue
        key = str(entry.key)
        placements.setdefault(slot, []).append(key)
        used.add(key)
        selected.append(key)
        reasons.append(f'{slot}: {entry.title} · {intent.query} · rank {score}')
    return StarterResolution(
        spec.key,
        definition.pattern.value,
        {slot: tuple(keys) for slot, keys in placements.items()},
        tuple(selected),
        tuple(unresolved),
        tuple(reasons),
    )


def pattern_intents(pattern_key: str, goal: str = '') -> tuple[CapabilityIntent, ...]:
    prefix = str(goal or '').strip()
    def q(text: str) -> str:
        return f'{prefix} {text}'.strip()
    table = CapabilityIntent(q('data table records'), ('data', 'details', 'content'), 'table', preferred_keys=('framework:tables:data_table',))
    visual = CapabilityIntent(q('line chart trend'), ('primary', 'secondary', 'content'), 'visualization', preferred_keys=('framework:visualizations:LineChart',))
    analytic = CapabilityIntent(q('analysis'), ('primary', 'secondary'), 'analytic')
    metric = CapabilityIntent(q('metric card'), ('metrics', 'details', 'primary'), 'metric_card', preferred_keys=('framework:content:metric_card',))
    select = CapabilityIntent(q('select filter'), ('filters', 'navigation', 'content'), 'select', preferred_keys=('component:select',))
    search = CapabilityIntent(q('search input'), ('filters',), 'search_input', preferred_keys=('component:search_input',))
    text = CapabilityIntent(q('text input'), ('content', 'details'), 'text_input', preferred_keys=('component:text_input',))
    action = CapabilityIntent(q('action button'), ('actions', 'content'), 'action_button', preferred_keys=('component:action_button',))
    status = CapabilityIntent(q('status badge'), ('metrics', 'primary'), 'status_badge', preferred_keys=('component:badge',))
    alert = CapabilityIntent(q('alert warning'), ('metrics', 'primary'), 'alert', preferred_keys=('framework:interactions:alert',))
    return {
        'dashboard': (metric, visual, CapabilityIntent(q('bar chart'), ('secondary',), 'visualization', preferred_keys=('framework:visualizations:BarChart',)), table, select),
        'data_explorer': (search, select, table, visual, metric),
        'master_detail': (table, metric, select),
        'crud': (search, table, text, action),
        'monitoring': (status, alert, visual, analytic, table, select),
        'search': (search, select, table, metric),
        'settings': (select, text, action),
        'wizard': (select, text, action),
        'comparison': (analytic, visual, table, metric, select),
        'analysis_workspace': (analytic, visual, table, select),
    }.get(str(pattern_key), (analytic, visual, table, select))


def recommend_composition(pattern_key: str, entries: Iterable[Any], *, goal: str = '', data_model: Any | None = None) -> StarterResolution:
    synthetic = GoldenStarterSpec(
        '__auto__', 'Auto composition', 'Schema-aware deterministic composition', 'Automatic',
        pattern_key, goal, 'automatic', pattern_intents(pattern_key, goal), (),
    )
    return resolve_starter(synthetic, entries, data_model=data_model)


def composition_diff(current: Mapping[str, Sequence[str]], recommended: Mapping[str, Sequence[str]]) -> CompositionDiff:
    current_loc = {str(key): str(slot) for slot, keys in current.items() for key in keys}
    next_loc = {str(key): str(slot) for slot, keys in recommended.items() for key in keys}
    added = tuple(sorted((slot, key) for key, slot in next_loc.items() if key not in current_loc))
    removed = tuple(sorted((slot, key) for key, slot in current_loc.items() if key not in next_loc))
    moved = tuple(sorted((key, current_loc[key], next_loc[key]) for key in current_loc.keys() & next_loc.keys() if current_loc[key] != next_loc[key]))
    return CompositionDiff(added, removed, moved)


__all__ = [
    'CapabilityIntent', 'CompositionDiff', 'GOLDEN_STARTERS', 'GoldenStarterSpec', 'StarterResolution',
    'composition_diff', 'get_golden_starter', 'pattern_intents', 'recommend_composition', 'resolve_starter',
]
