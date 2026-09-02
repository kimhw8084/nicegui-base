from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

_ROUTE_RE = re.compile(r'^/[a-z0-9][a-z0-9-]*$')
_MODULE_RE = re.compile(r'^[a-z][a-z0-9_]*$')


@dataclass(frozen=True, slots=True)
class BlueprintPageSpec:
    key: str
    title: str
    route: str
    pattern_key: str | None
    purpose: str
    primary: bool = False

    def __post_init__(self) -> None:
        if not _MODULE_RE.fullmatch(self.key):
            raise ValueError(f'invalid blueprint page key: {self.key!r}')
        if self.route != '/' and not _ROUTE_RE.fullmatch(self.route):
            raise ValueError(f'invalid blueprint route: {self.route!r}')
        if not self.title.strip() or not self.purpose.strip():
            raise ValueError('blueprint page title and purpose must not be empty')
        if self.primary and self.route != '/':
            raise ValueError('primary blueprint page must own the root route')
        if self.primary and self.pattern_key is not None:
            raise ValueError('primary blueprint page inherits the current project pattern')
        if not self.primary and not self.pattern_key:
            raise ValueError('secondary blueprint pages require a canonical pattern key')

    @property
    def module(self) -> str:
        return 'home' if self.route == '/' else self.key


@dataclass(frozen=True, slots=True)
class AppBlueprintSpec:
    key: str
    title: str
    description: str
    category: str
    pages: tuple[BlueprintPageSpec, ...]
    tags: tuple[str, ...] = ()
    preferred_patterns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _MODULE_RE.fullmatch(self.key.replace('-', '_')):
            raise ValueError(f'invalid blueprint key: {self.key!r}')
        if not 2 <= len(self.pages) <= 6:
            raise ValueError('application blueprints must contain 2-6 pages')
        roots = [page for page in self.pages if page.route == '/']
        if len(roots) != 1 or not roots[0].primary:
            raise ValueError('application blueprints require exactly one primary root page')
        routes = [page.route for page in self.pages]
        keys = [page.key for page in self.pages]
        modules = [page.module for page in self.pages]
        if len(routes) != len(set(routes)):
            raise ValueError(f'{self.key} contains duplicate routes')
        if len(keys) != len(set(keys)) or len(modules) != len(set(modules)):
            raise ValueError(f'{self.key} contains duplicate page identities')


@dataclass(frozen=True, slots=True)
class BlueprintPagePlan:
    key: str
    title: str
    route: str
    module: str
    pattern_key: str
    purpose: str
    placements: Mapping[str, tuple[str, ...]]
    primary: bool

    def to_dict(self) -> dict[str, object]:
        return {
            'key': self.key,
            'title': self.title,
            'route': self.route,
            'module': self.module,
            'pattern_key': self.pattern_key,
            'purpose': self.purpose,
            'placements': {slot: list(keys) for slot, keys in self.placements.items()},
            'primary': self.primary,
        }


@dataclass(frozen=True, slots=True)
class ResolvedAppBlueprint:
    key: str
    title: str
    description: str
    pages: tuple[BlueprintPagePlan, ...]

    @property
    def routes(self) -> tuple[str, ...]:
        return tuple(page.route for page in self.pages)

    def to_dict(self) -> dict[str, object]:
        return {
            'schema_version': 1,
            'blueprint_key': self.key,
            'title': self.title,
            'description': self.description,
            'routes': list(self.routes),
            'pages': [page.to_dict() for page in self.pages],
        }


@dataclass(frozen=True, slots=True)
class BlueprintRecommendation:
    blueprint: AppBlueprintSpec
    score: int
    reasons: tuple[str, ...]


_PRIMARY = BlueprintPageSpec(
    'workspace', 'Workspace', '/', None,
    'The primary page composed explicitly in NiceGUI Base Workbench.', primary=True,
)

APP_BLUEPRINTS: tuple[AppBlueprintSpec, ...] = (
    AppBlueprintSpec(
        'engineering-control-center', 'Engineering Control Center',
        'Primary engineering workspace plus overview, data exploration, investigation, comparison and settings.',
        'Engineering',
        (
            _PRIMARY,
            BlueprintPageSpec('overview', 'Overview', '/overview', 'dashboard', 'Scan KPIs, health and the current engineering situation.'),
            BlueprintPageSpec('data', 'Data Explorer', '/data', 'data_explorer', 'Filter and inspect the records behind the analytical workspace.'),
            BlueprintPageSpec('investigate', 'Investigate', '/investigate', 'analysis_workspace', 'Perform deeper analytical investigation with shared evidence context.'),
            BlueprintPageSpec('compare', 'Compare', '/compare', 'comparison', 'Compare baseline/current populations or engineering scenarios.'),
            BlueprintPageSpec('settings', 'Settings', '/settings', 'settings', 'Manage application-level configuration using the governed settings pattern.'),
        ),
        ('engineering', 'analysis', 'rca', 'monitoring', 'comparison'),
        ('analysis_workspace', 'monitoring', 'comparison', 'data_explorer'),
    ),
    AppBlueprintSpec(
        'monitoring-operations', 'Monitoring Operations Center',
        'Continuous monitoring workspace with operational overview, records, investigation and settings.',
        'Engineering',
        (
            _PRIMARY,
            BlueprintPageSpec('overview', 'Overview', '/overview', 'dashboard', 'Summarize current health, KPIs and exceptions.'),
            BlueprintPageSpec('records', 'Records', '/records', 'data_explorer', 'Inspect the observations and records driving monitored state.'),
            BlueprintPageSpec('investigate', 'Investigate', '/investigate', 'analysis_workspace', 'Drill into abnormal behavior without leaving the application.'),
            BlueprintPageSpec('settings', 'Settings', '/settings', 'settings', 'Configure monitoring/application preferences through a standard settings surface.'),
        ),
        ('monitor', 'health', 'alerts', 'operations', 'fdc', 'spc'),
        ('monitoring', 'dashboard'),
    ),
    AppBlueprintSpec(
        'analysis-investigation-suite', 'Analysis & Investigation Suite',
        'Focused analytical application with overview, comparison and supporting-record pages.',
        'Engineering',
        (
            _PRIMARY,
            BlueprintPageSpec('overview', 'Overview', '/overview', 'dashboard', 'Summarize the investigation population and high-value signals.'),
            BlueprintPageSpec('compare', 'Compare', '/compare', 'comparison', 'Compare populations, baselines, tools or scenarios.'),
            BlueprintPageSpec('records', 'Evidence Records', '/records', 'data_explorer', 'Inspect supporting records while preserving analytical context.'),
        ),
        ('analysis', 'investigation', 'rca', 'comparison', 'evidence'),
        ('analysis_workspace', 'comparison'),
    ),
    AppBlueprintSpec(
        'data-management-center', 'Data Management Center',
        'Data exploration application with governed manage, search and settings pages.',
        'Generic',
        (
            _PRIMARY,
            BlueprintPageSpec('manage', 'Manage Records', '/manage', 'crud', 'Create, inspect and manage records through the governed CRUD pattern.'),
            BlueprintPageSpec('search', 'Search', '/search', 'search', 'Find records quickly with a dedicated search experience.'),
            BlueprintPageSpec('settings', 'Settings', '/settings', 'settings', 'Manage configuration and user-facing preferences.'),
        ),
        ('data', 'records', 'crud', 'search', 'admin'),
        ('data_explorer', 'crud', 'search'),
    ),
    AppBlueprintSpec(
        'workflow-operations', 'Workflow Operations',
        'Operational workspace with records, a guided workflow and configuration.',
        'Generic',
        (
            _PRIMARY,
            BlueprintPageSpec('records', 'Records', '/records', 'data_explorer', 'Explore the records that feed the workflow.'),
            BlueprintPageSpec('workflow', 'Guided Workflow', '/workflow', 'wizard', 'Guide users through the canonical multi-step workflow pattern.'),
            BlueprintPageSpec('settings', 'Settings', '/settings', 'settings', 'Manage workflow/application configuration.'),
        ),
        ('workflow', 'wizard', 'operations', 'records'),
        ('wizard', 'crud', 'data_explorer'),
    ),
    AppBlueprintSpec(
        'compact-standard-app', 'Compact Standard App',
        'The smallest governed multi-page application: the composed workspace plus settings.',
        'Generic',
        (
            _PRIMARY,
            BlueprintPageSpec('settings', 'Settings', '/settings', 'settings', 'Keep application configuration separate from the primary work surface.'),
        ),
        ('compact', 'small', 'settings', 'starter'),
        ('dashboard', 'data_explorer', 'crud', 'search', 'settings', 'wizard'),
    ),
)

_BLUEPRINT_BY_KEY = {item.key: item for item in APP_BLUEPRINTS}


def get_app_blueprint(key: str) -> AppBlueprintSpec:
    try:
        return _BLUEPRINT_BY_KEY[str(key)]
    except KeyError as exc:
        raise KeyError(f'unknown application blueprint: {key!r}') from exc


def _goal_tokens(project: Mapping[str, Any]) -> set[str]:
    text = ' '.join(str(project.get(key) or '') for key in ('goal', 'problem_type', 'pattern_key')).casefold()
    return {token for token in re.split(r'[^a-z0-9]+', text) if len(token) >= 3}


def recommend_app_blueprints(project: Mapping[str, Any]) -> tuple[BlueprintRecommendation, ...]:
    pattern = str(project.get('pattern_key') or '')
    tokens = _goal_tokens(project)
    recommendations: list[BlueprintRecommendation] = []
    for blueprint in APP_BLUEPRINTS:
        score = 0
        reasons: list[str] = []
        if pattern and pattern in blueprint.preferred_patterns:
            score += 120
            reasons.append(f'Primary pattern {pattern.replace("_", " ")} is a preferred fit.')
        tag_hits = sorted(tokens & {tag.casefold() for tag in blueprint.tags})
        if tag_hits:
            score += 25 * len(tag_hits)
            reasons.append('Goal matches: ' + ', '.join(tag_hits[:5]))
        if 'engineering' in str(project.get('problem_type') or '').casefold() and blueprint.category == 'Engineering':
            score += 35
            reasons.append('Matches the engineering application intent.')
        if 'generic' in str(project.get('problem_type') or '').casefold() and blueprint.category == 'Generic':
            score += 35
            reasons.append('Matches the generic application intent.')
        if not reasons:
            reasons.append(blueprint.description)
        recommendations.append(BlueprintRecommendation(blueprint, score, tuple(reasons)))
    recommendations.sort(key=lambda item: (-item.score, len(item.blueprint.pages), item.blueprint.title.casefold()))
    return tuple(recommendations)


def resolve_app_blueprint(project: Mapping[str, Any], entries: Iterable[Any], *, data_model: Any | None = None) -> ResolvedAppBlueprint:
    key = str(project.get('blueprint_key') or '')
    if not key:
        raise ValueError('project does not select an application blueprint')
    blueprint = get_app_blueprint(key)
    pattern_key = str(project.get('pattern_key') or '')
    if not pattern_key:
        raise ValueError('application blueprint requires a primary page pattern')
    primary_placements = project.get('placements') if isinstance(project.get('placements'), Mapping) else {}
    pages: list[BlueprintPagePlan] = []
    from .starter_kits import recommend_composition
    entries_tuple = tuple(entries)
    for page in blueprint.pages:
        if page.primary:
            placements = {
                str(slot): tuple(str(item) for item in keys)
                for slot, keys in primary_placements.items() if isinstance(keys, (list, tuple))
            }
            pages.append(BlueprintPagePlan(
                page.key, page.title, page.route, page.module, pattern_key,
                str(project.get('goal') or page.purpose), placements, True,
            ))
            continue
        resolution = recommend_composition(
            str(page.pattern_key), entries_tuple,
            goal=f"{project.get('goal', '')} {page.purpose}".strip(),
            data_model=data_model,
        )
        if resolution.unresolved:
            raise ValueError(
                f'{blueprint.key}:{page.key} could not resolve required capability intents: {resolution.unresolved}'
            )
        pages.append(BlueprintPagePlan(
            page.key, page.title, page.route, page.module, str(page.pattern_key), page.purpose,
            {slot: tuple(keys) for slot, keys in resolution.placements.items()}, False,
        ))
    return ResolvedAppBlueprint(blueprint.key, blueprint.title, blueprint.description, tuple(pages))


def validate_app_blueprint_manifest(value: Any) -> tuple[str, ...]:
    findings: list[str] = []
    if not isinstance(value, Mapping):
        return ('blueprint:not_object',)
    if value.get('schema_version') != 1:
        findings.append('blueprint:schema_version')
    key = str(value.get('blueprint_key') or '')
    canonical = None
    try:
        canonical = get_app_blueprint(key)
    except KeyError:
        findings.append('blueprint:unknown_key')
    pages = value.get('pages')
    if not isinstance(pages, list) or not 2 <= len(pages) <= 6:
        findings.append('blueprint:pages')
        pages = []
    routes: list[str] = []
    modules: list[str] = []
    primary = 0
    for page in pages:
        if not isinstance(page, Mapping):
            findings.append('blueprint:page_not_object')
            continue
        route = str(page.get('route') or '')
        module = str(page.get('module') or '')
        if route != '/' and not _ROUTE_RE.fullmatch(route):
            findings.append(f'blueprint:route:{route}')
        if not _MODULE_RE.fullmatch(module):
            findings.append(f'blueprint:module:{module}')
        if page.get('primary'):
            primary += 1
            if route != '/' or module != 'home':
                findings.append('blueprint:invalid_primary_page')
        routes.append(route); modules.append(module)
    if len(routes) != len(set(routes)):
        findings.append('blueprint:duplicate_routes')
    if len(modules) != len(set(modules)):
        findings.append('blueprint:duplicate_modules')
    if primary != 1 or '/' not in routes:
        findings.append('blueprint:root_page')
    declared_routes = value.get('routes')
    if not isinstance(declared_routes, list) or [str(item) for item in declared_routes] != routes:
        findings.append('blueprint:route_manifest')
    if canonical is not None and pages:
        expected_routes = [page.route for page in canonical.pages]
        expected_modules = [page.module for page in canonical.pages]
        if routes != expected_routes:
            findings.append('blueprint:canonical_routes')
        if modules != expected_modules:
            findings.append('blueprint:canonical_modules')
        for actual, expected in zip(pages, canonical.pages):
            if not isinstance(actual, Mapping):
                continue
            if not expected.primary and str(actual.get('pattern_key') or '') != str(expected.pattern_key):
                findings.append(f'blueprint:canonical_pattern:{expected.key}')
    return tuple(dict.fromkeys(findings))


__all__ = [
    'APP_BLUEPRINTS', 'AppBlueprintSpec', 'BlueprintPagePlan', 'BlueprintPageSpec', 'BlueprintRecommendation',
    'ResolvedAppBlueprint', 'get_app_blueprint', 'recommend_app_blueprints', 'resolve_app_blueprint',
    'validate_app_blueprint_manifest',
]
