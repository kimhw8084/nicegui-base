from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from nicegui_base.ai.catalog import load_framework_catalog
from nicegui_base.ai.manifest import load_ai_manifest
from nicegui_base.version import FRAMEWORK_VERSION


@dataclass(frozen=True, slots=True)
class AgentRecommendation:
    category: str
    reason: str
    preferred_api: str
    inspect_first: str


@dataclass(frozen=True, slots=True)
class AgentContextPack:
    framework_version: str
    task: str
    dominant_pattern: str
    starter_template: str
    pattern_reason: str
    recommendations: tuple[AgentRecommendation, ...]
    read_first: tuple[str, ...]
    golden_examples: tuple[str, ...]
    hard_prohibitions: tuple[str, ...]
    validation_commands: tuple[str, ...]
    completion_contract: tuple[str, ...]
    starter_recipe: str | None = None
    starter_recipe_variant: str | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload['recommendations'] = [asdict(item) for item in self.recommendations]
        return payload


_PATTERN_SIGNALS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ('analysis_workspace', ('workspace', 'analysis', 'investigation', 'rca', 'spc', 'ewma', 'cusum', 'capability', 'fdc', 'wafer', 'lot', 'chamber', 'excursion', 'yield', 'defect', 'correlation', 'parameter', 'resizable', 'explore'), 'Dense interactive analysis is the dominant task.'),
    ('crud', ('crud', 'create', 'edit', 'delete', 'manage record', 'admin'), 'Record management is the dominant task.'),
    ('data_explorer', ('filter', 'table', 'records', 'data explorer', 'explorer', 'drill', 'dataset'), 'Filtering and inspecting records is the dominant task.'),
    ('monitoring', ('monitor', 'health', 'alert', 'live', 'status', 'operations'), 'Operational status and refresh are the dominant task.'),
    ('comparison', ('compare', 'comparison', 'baseline', 'current', 'delta'), 'Direct comparison is the dominant task.'),
    ('search', ('search', 'find', 'lookup', 'facets'), 'Search and refinement are the dominant task.'),
    ('settings', ('settings', 'configuration', 'preferences'), 'Configuration is the dominant task.'),
    ('wizard', ('wizard', 'step', 'guided', 'onboarding'), 'A bounded multi-step workflow is the dominant task.'),
    ('master_detail', ('master detail', 'browse and inspect', 'selected entity', 'inspector'), 'Browse-and-inspect is the dominant task.'),
    ('dashboard', ('dashboard', 'kpi', 'overview', 'executive', 'summary', 'trend'), 'Overview and KPI consumption are the dominant task.'),
)

_CATEGORY_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('page_pattern', ('page', 'screen', 'dashboard', 'workspace', 'crud', 'settings', 'wizard', 'search')),
    ('layout', ('layout', 'panel', 'split', 'resize', 'responsive', 'workspace')),
    ('component', ('button', 'input', 'select', 'control', 'status', 'badge', 'form')),
    ('content', ('kpi', 'metric', 'details', 'properties', 'activity', 'workflow', 'viewer')),
    ('form_filter_overlay', ('filter', 'form', 'drawer', 'dialog', 'popover', 'toast', 'menu')),
    ('table', ('table', 'rows', 'records', 'grid', 'columns', 'editing', 'pagination')),
    ('visualization', ('chart', 'trend', 'plot', 'distribution', 'pareto', 'wafer', 'visualization')),
    ('visual_asset', ('icon', 'illustration', 'image')),
    ('state_async', ('state', 'async', 'refresh', 'debounce', 'cancel', 'persist', 'url state')),
    ('jobs', ('job', 'background', 'long running', 'survive restart')),
    ('engineering', ('semiconductor', 'wafer', 'chamber', 'lot', 'spec', 'control limit', 'rca', 'commonality')),
    ('semiconductor', ('semiconductor', 'spc', 'ewma', 'cusum', 'capability', 'wafer', 'lot', 'chamber', 'fdc', 'trace', 'commonality', 'yield', 'excursion', 'evidence', 'rca', 'root cause', 'hypothesis', 'parameter', 'correlation', 'weibull', 'doe', 'pm effect', 'drift')),
    ('performance', ('performance', 'large data', '100k', '50k', 'cache', 'latency', 'fan-out')),
    ('security_runtime', ('auth', 'permission', 'upload', 'proxy', 'deployment', 'runtime', 'health', 'secret')),
)

_STARTER_FOR_PATTERN = {
    'dashboard': 'dashboard',
    'data_explorer': 'data-explorer',
    'crud': 'crud',
    'analysis_workspace': 'analysis-workspace',
    'monitoring': 'responsive-operations',
}

_GOLDEN_FOR_PATTERN = {
    'dashboard': 'examples/nicegui_base/golden_dashboard.py',
    'data_explorer': 'examples/nicegui_base/golden_data_explorer.py',
    'crud': 'examples/nicegui_base/golden_crud.py',
    'analysis_workspace': 'examples/nicegui_base/golden_analysis_workspace.py',
}


def _score(text: str, signals: Iterable[str]) -> int:
    folded = text.casefold()
    return sum(3 if ' ' in signal and signal in folded else folded.count(signal) for signal in signals)


def _pattern(task: str) -> tuple[str, str]:
    folded = task.casefold()
    if 'data explorer' in folded or 'data-explorer' in folded:
        return 'data_explorer', 'The requirement explicitly names the governed data-explorer pattern.'
    if 'comparison page' in folded or 'comparison screen' in folded:
        return 'comparison', 'The requirement explicitly requests the governed comparison pattern.'
    scored = [(name, _score(task, signals), reason) for name, signals, reason in _PATTERN_SIGNALS]
    name, score, reason = max(scored, key=lambda item: item[1])
    if score <= 0:
        return 'data_explorer', 'Default to the flexible data-explorer pattern when the task signal is ambiguous.'
    return name, reason


def _catalog_lookup(registry: str, public_name: str) -> dict | None:
    catalog = load_framework_catalog()
    entries = catalog.get('registries', {}).get(registry, ())
    for item in entries:
        if isinstance(item, dict) and item.get('public_name') == public_name:
            return item
    return None


def build_agent_context(task: str) -> AgentContextPack:
    task = task.strip()
    if not task:
        raise ValueError('task must not be empty')
    manifest = load_ai_manifest()
    pattern, pattern_reason = _pattern(task)

    from nicegui_base.ai.registry import AI_CONSTRUCTION_REGISTRY

    categories: list[str] = ['page_pattern']
    for category, signals in _CATEGORY_SIGNALS:
        if category != 'page_pattern' and _score(task, signals) > 0:
            categories.append(category)
    # A task involving multiple analytical surfaces should always share state/data authority.
    if sum(token in task.casefold() for token in ('table', 'chart', 'kpi', 'filter')) >= 2 and 'state_async' not in categories:
        categories.append('state_async')
    starter_template = _STARTER_FOR_PATTERN.get(pattern, 'data-explorer')
    if 'state_async' in categories and any(token in task.casefold() for token in ('async', 'retry', 'submit', 'background task', 'long running')):
        starter_template = 'async-workflow'
    starter_recipe = None
    starter_recipe_variant = None
    if 'semiconductor' in categories:
        from nicegui_base.semiconductor import recommend_semiconductor_recipe, variants_for_recipe
        starter_recipe = recommend_semiconductor_recipe(task).key
        variants = variants_for_recipe(starter_recipe)
        starter_recipe_variant = variants[0].key if variants else None
        starter_template = 'analysis-workspace'
    recommendations = tuple(
        AgentRecommendation(
            category=category,
            reason=AI_CONSTRUCTION_REGISTRY[category].rationale,
            preferred_api=AI_CONSTRUCTION_REGISTRY[category].preferred_api,
            inspect_first=AI_CONSTRUCTION_REGISTRY[category].inspect_first,
        )
        for category in dict.fromkeys(categories)
    )
    examples = [_GOLDEN_FOR_PATTERN.get(pattern, 'examples/nicegui_base/golden_data_explorer.py')]
    if pattern != 'data_explorer' and any(key in categories for key in ('table', 'visualization', 'state_async')):
        examples.append('examples/nicegui_base/golden_data_explorer.py')
    if pattern == 'analysis_workspace':
        examples.append('examples/nicegui_base/golden_analysis_workspace.py')
    folded = task.casefold()
    if 'semiconductor' in categories:
        examples.append('examples/phase66_target_certification_orchestrator.py')
        examples.append('examples/phase65_provider_sdk_release_candidate.py')
        examples.append('examples/phase64_production_adapter_runtime.py')
        examples.append('examples/phase63_recipe_runtime_onboarding.py')
        examples.append('examples/phase62_application_recipe_factory.py')
        if any(token in folded for token in ('fdc','trace','pm','chamber','tool health')):
            examples.append('examples/phase61_fdc_tool_health.py')
        elif any(token in folded for token in ('rca','commonality','excursion','root cause')):
            examples.append('examples/phase61_rca_commonality.py')
        else:
            examples.append('examples/phase61_spc_wafer_investigation.py')

    read_first = (
        'AGENTS.md',
        'docs/nicegui_base/AI_QUICKSTART.md',
        'docs/nicegui_base/APP_PATTERNS.md',
        'docs/nicegui_base/AI_RULES.md',
        '.nicegui_base/framework_catalog.json',
        'docs/nicegui_base/PUBLIC_API_INDEX.md',
    )
    completion = (
        'Keep application code outside nicegui_base/ unless framework development is explicitly requested.',
        'Preserve existing UI/UX contracts; use semantic NiceGUI Base APIs before any escape hatch.',
        'Run strict NiceGUI Base validation after meaningful changes.',
        'Run application tests/startup smoke and inspect browser output for visual changes.',
    )
    return AgentContextPack(
        framework_version=FRAMEWORK_VERSION,
        task=task,
        dominant_pattern=pattern,
        starter_template=starter_template,
        pattern_reason=pattern_reason,
        recommendations=recommendations,
        read_first=read_first,
        golden_examples=tuple(dict.fromkeys(examples)),
        hard_prohibitions=tuple(manifest.get('hard_prohibitions', ())),
        validation_commands=(
            'nicegui-base agent-check .',
            'nicegui-base gate .',
        ),
        completion_contract=completion,
        starter_recipe=starter_recipe,
        starter_recipe_variant=starter_recipe_variant,
    )


def render_agent_context(pack: AgentContextPack) -> str:
    lines = [
        f'# NiceGUI Base agent context — {pack.framework_version}', '',
        f'**Task:** {pack.task}',
        f'**Dominant pattern:** `{pack.dominant_pattern}` — {pack.pattern_reason}',
        f'**Recommended starter:** `{pack.starter_template}`' + (f' + `{pack.starter_recipe}` recipe' if pack.starter_recipe else '') + (f' + `{pack.starter_recipe_variant}` variant' if pack.starter_recipe_variant else ''),
        f'**New-project command:** `nicegui-base create ./<app> --name "<App Name>" --template {pack.starter_template}' + (f' --recipe {pack.starter_recipe}' if pack.starter_recipe else '') + (f' --variant {pack.starter_recipe_variant}' if pack.starter_recipe_variant else '') + '`', '',
        '## Read first',
    ]
    lines.extend(f'- `{item}`' for item in pack.read_first)
    lines.extend(['', '## Recommended construction paths'])
    for item in pack.recommendations:
        lines.append(f'- **{item.category}** → `{item.preferred_api}`; inspect `{item.inspect_first}`. {item.reason}')
    lines.extend(['', '## Golden examples'])
    lines.extend(f'- `{item}`' for item in pack.golden_examples)
    lines.extend(['', '## Completion gate'])
    lines.extend(f'- {item}' for item in pack.completion_contract)
    lines.extend(['', 'Run:'])
    lines.extend(f'`{item}`' for item in pack.validation_commands)
    return '\n'.join(lines) + '\n'


__all__ = ['AgentContextPack', 'AgentRecommendation', 'build_agent_context', 'render_agent_context']
