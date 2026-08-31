from __future__ import annotations

import abc
import importlib
import inspect
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from nicegui_base.data_sources import DataSource

from .conformance import (
    AdapterConformancePolicy,
    AdapterConformanceReport,
    AdapterDiagnostic,
    ConformanceSeverity,
    run_semiconductor_adapter_conformance,
)
from .onboarding import AdaptedSemiconductorSource, SemiconductorSourceAdapter, SmartBindingPolicy
from .recipes import SEMICONDUCTOR_RECIPE_REGISTRY, SemiconductorRecipeDefinition, get_semiconductor_recipe

_PROVIDER_KEY = re.compile(r'^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$')


@dataclass(frozen=True, slots=True)
class ProviderAdapterManifest:
    """Provider-neutral identity and support declaration for an adapter implementation."""

    key: str
    display_name: str
    version: str = '1'
    supported_recipes: tuple[str, ...] = ()
    description: str = ''
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        key = self.key.strip()
        if not _PROVIDER_KEY.match(key):
            raise ValueError('provider adapter key must be lowercase alphanumeric with optional -/_ separators')
        if not self.display_name.strip() or not self.version.strip():
            raise ValueError('provider adapter display_name and version must not be empty')
        recipes = tuple(dict.fromkeys(item.strip() for item in self.supported_recipes if item.strip()))
        unknown = set(recipes) - set(SEMICONDUCTOR_RECIPE_REGISTRY)
        if unknown:
            raise KeyError(f'provider adapter manifest references unknown recipes: {sorted(unknown)!r}')
        object.__setattr__(self, 'key', key)
        object.__setattr__(self, 'supported_recipes', recipes)
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def supports(self, recipe: str | SemiconductorRecipeDefinition) -> bool:
        key = recipe.key if isinstance(recipe, SemiconductorRecipeDefinition) else str(recipe)
        return not self.supported_recipes or key in self.supported_recipes

    def to_dict(self) -> dict[str, Any]:
        return {
            'key': self.key,
            'display_name': self.display_name,
            'version': self.version,
            'supported_recipes': self.supported_recipes,
            'description': self.description,
            'metadata': dict(self.metadata),
        }


class SemiconductorProviderAdapterBase(abc.ABC):
    """SDK convenience base that still returns the Wave 59 ``DataSource`` authority.

    Provider implementations normally only override ``build_source``. The base class
    deliberately owns no query, filter, state, authentication, or deployment semantics.
    """

    manifest: ProviderAdapterManifest

    @property
    def key(self) -> str:
        return self.manifest.key

    @abc.abstractmethod
    async def build_source(self, recipe: SemiconductorRecipeDefinition) -> DataSource:
        """Return a provider-backed Wave 59 DataSource for the requested recipe."""
        raise NotImplementedError

    def field_overrides(self, recipe: SemiconductorRecipeDefinition) -> Mapping[str, str]:
        return {}

    def adapter_metadata(self, recipe: SemiconductorRecipeDefinition) -> Mapping[str, Any]:
        return {'provider_adapter': self.manifest.key, 'provider_adapter_version': self.manifest.version}

    def owns_source(self, recipe: SemiconductorRecipeDefinition) -> bool:
        return True

    async def open(self, recipe: SemiconductorRecipeDefinition) -> AdaptedSemiconductorSource:
        if not self.manifest.supports(recipe):
            raise ValueError(f'provider adapter {self.manifest.key!r} does not declare support for recipe {recipe.key!r}')
        source = await self.build_source(recipe)
        if not isinstance(source, DataSource):
            raise TypeError('SemiconductorProviderAdapterBase.build_source() must return a DataSource')
        return AdaptedSemiconductorSource(
            source,
            field_overrides=self.field_overrides(recipe),
            metadata={**self.manifest.to_dict(), **dict(self.adapter_metadata(recipe))},
            owns_source=self.owns_source(recipe),
        )


@dataclass(frozen=True, slots=True)
class ProviderConformanceProfile:
    key: str
    description: str
    policy: AdapterConformancePolicy

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.description.strip():
            raise ValueError('provider conformance profile key and description must not be empty')


PROVIDER_CONFORMANCE_PROFILES: Mapping[str, ProviderConformanceProfile] = MappingProxyType({
    'development': ProviderConformanceProfile(
        'development',
        'Bounded developer fixture profile; validates behavior without requiring backend pushdown.',
        AdapterConformancePolicy(
            require_filter_pushdown=False,
            require_pagination_pushdown=False,
            require_projection_pushdown=False,
            require_distinct_pushdown=False,
        ),
    ),
    'production': ProviderConformanceProfile(
        'production',
        'Release-candidate provider profile; requires observed filter/pagination/projection pushdown.',
        AdapterConformancePolicy(
            require_filter_pushdown=True,
            require_pagination_pushdown=True,
            require_projection_pushdown=True,
            require_distinct_pushdown=False,
        ),
    ),
})


@dataclass(frozen=True, slots=True)
class ProviderConformanceFixture:
    name: str
    recipe_key: str
    profile_key: str = 'production'
    field_overrides: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError('provider conformance fixture name must not be empty')
        get_semiconductor_recipe(self.recipe_key)
        if self.profile_key not in PROVIDER_CONFORMANCE_PROFILES:
            raise KeyError(f'unknown provider conformance profile {self.profile_key!r}')
        object.__setattr__(self, 'field_overrides', MappingProxyType(dict(self.field_overrides)))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def profile(self) -> ProviderConformanceProfile:
        return PROVIDER_CONFORMANCE_PROFILES[self.profile_key]

    def to_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'recipe_key': self.recipe_key,
            'profile_key': self.profile_key,
            'field_overrides': dict(self.field_overrides),
            'metadata': dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ProviderDiagnosticGuidance:
    code: str
    severity: ConformanceSeverity
    summary: str
    remediation: str
    source_details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.summary.strip() or not self.remediation.strip():
            raise ValueError('provider diagnostic guidance fields must not be empty')
        object.__setattr__(self, 'source_details', MappingProxyType(dict(self.source_details)))

    def to_dict(self) -> dict[str, Any]:
        return {
            'code': self.code,
            'severity': self.severity.value,
            'summary': self.summary,
            'remediation': self.remediation,
            'source_details': dict(self.source_details),
        }


_REMEDIATION_TEMPLATES: tuple[tuple[str, str], ...] = (
    ('missing_filter_pushdown', 'Implement filter compilation in the provider or use a production provider that pushes governed filters to the backend.'),
    ('filter_pushdown_not_observed', 'Ensure filtered queries execute in the backend and return QueryStats(pushdown=True) only when that actually occurred.'),
    ('missing_pagination_pushdown', 'Implement backend LIMIT/OFFSET or equivalent cursor pagination before using this provider at fab scale.'),
    ('pagination_pushdown_not_observed', 'Apply pagination in the backend and report observed pushdown truthfully in QueryStats.'),
    ('missing_projection_pushdown', 'Project only requested columns in the backend for production workloads.'),
    ('projection_pushdown_not_observed', 'Honor Query.projection at the provider boundary instead of selecting the full source row.'),
    ('missing_distinct_pushdown', 'Implement backend DISTINCT for manufacturing filter-option queries or relax the policy only for a bounded development fixture.'),
    ('distinct_pushdown_not_observed', 'Execute distinct-value discovery in the backend and report observed pushdown truthfully.'),
    ('source_unhealthy', 'Resolve provider connectivity/credentials/upstream health before promoting the application.'),
    ('probe_limit_violated', 'Honor the bounded conformance query limit; conformance probes must never enumerate the production source.'),
    ('latency_exceeded', 'Tune provider/backend execution or set an evidence-based budget for the representative environment.'),
)


def provider_diagnostic_guidance(diagnostic: AdapterDiagnostic) -> ProviderDiagnosticGuidance:
    remediation = 'Inspect the diagnostic details and provider implementation; do not suppress the finding without evidence.'
    for token, text in _REMEDIATION_TEMPLATES:
        if token in diagnostic.code:
            remediation = text
            break
    return ProviderDiagnosticGuidance(diagnostic.code, diagnostic.severity, diagnostic.message, remediation, diagnostic.details)


def provider_report_guidance(report: AdapterConformanceReport) -> tuple[ProviderDiagnosticGuidance, ...]:
    return tuple(provider_diagnostic_guidance(item) for item in report.diagnostics)


@dataclass(frozen=True, slots=True)
class ProviderFixtureResult:
    fixture: ProviderConformanceFixture
    report: AdapterConformanceReport
    guidance: tuple[ProviderDiagnosticGuidance, ...]

    @property
    def passed(self) -> bool:
        return self.report.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            'fixture': self.fixture.to_dict(),
            'passed': self.passed,
            'report': self.report.to_dict(),
            'guidance': [item.to_dict() for item in self.guidance],
        }


@dataclass(frozen=True, slots=True)
class ProviderConformanceSuiteReport:
    adapter_key: str
    results: tuple[ProviderFixtureResult, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'results', tuple(self.results))

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(item.passed for item in self.results)

    @property
    def failed_fixtures(self) -> tuple[str, ...]:
        return tuple(item.fixture.name for item in self.results if not item.passed)

    def to_dict(self) -> dict[str, Any]:
        return {'adapter_key': self.adapter_key, 'passed': self.passed, 'failed_fixtures': self.failed_fixtures, 'results': [item.to_dict() for item in self.results]}


async def run_provider_conformance_fixture(
    adapter: SemiconductorSourceAdapter,
    fixture: ProviderConformanceFixture,
    *,
    binding_policy: SmartBindingPolicy = SmartBindingPolicy(),
) -> ProviderFixtureResult:
    report = await run_semiconductor_adapter_conformance(
        fixture.recipe_key,
        adapter,
        field_overrides=fixture.field_overrides,
        policy=fixture.profile.policy,
        binding_policy=binding_policy,
    )
    return ProviderFixtureResult(fixture, report, provider_report_guidance(report))


async def run_provider_conformance_suite(
    adapter: SemiconductorSourceAdapter,
    fixtures: Sequence[ProviderConformanceFixture],
    *,
    binding_policy: SmartBindingPolicy = SmartBindingPolicy(),
) -> ProviderConformanceSuiteReport:
    if not isinstance(adapter, SemiconductorSourceAdapter):
        raise TypeError('adapter must implement SemiconductorSourceAdapter')
    items = tuple(fixtures)
    if not items:
        raise ValueError('provider conformance suite requires at least one fixture')
    results: list[ProviderFixtureResult] = []
    for fixture in items:
        results.append(await run_provider_conformance_fixture(adapter, fixture, binding_policy=binding_policy))
    return ProviderConformanceSuiteReport(str(adapter.key), tuple(results))


def load_semiconductor_adapter(reference: str) -> SemiconductorSourceAdapter:
    """Load ``module:object`` for local provider conformance CLI execution."""
    module_name, sep, attribute = reference.partition(':')
    if not sep or not module_name.strip() or not attribute.strip():
        raise ValueError('adapter reference must use module:object syntax')
    module = importlib.import_module(module_name)
    target = getattr(module, attribute)
    value = target() if inspect.isclass(target) else target
    if not isinstance(value, SemiconductorSourceAdapter):
        raise TypeError(f'{reference!r} does not resolve to a SemiconductorSourceAdapter')
    return value


def provider_fixture_from_dict(payload: Mapping[str, Any]) -> ProviderConformanceFixture:
    return ProviderConformanceFixture(
        str(payload['name']),
        str(payload['recipe_key']),
        str(payload.get('profile_key', 'production')),
        payload.get('field_overrides', {}),
        payload.get('metadata', {}),
    )


def load_provider_fixtures(path: str | Path) -> tuple[ProviderConformanceFixture, ...]:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    raw = payload.get('fixtures') if isinstance(payload, Mapping) else payload
    if not isinstance(raw, list):
        raise TypeError('provider fixture JSON must contain a list or {"fixtures": [...]}')
    return tuple(provider_fixture_from_dict(item) for item in raw)


def provider_adapter_template_source(*, key: str, class_name: str = 'CompanySemiconductorAdapter') -> str:
    manifest = ProviderAdapterManifest(key, key.replace('-', ' ').replace('_', ' ').title())
    return f'''from __future__ import annotations\n\nfrom nicegui_base import ProviderAdapterManifest, SemiconductorProviderAdapterBase\nfrom services.data_source import build_source\n\n\nclass {class_name}(SemiconductorProviderAdapterBase):\n    manifest = ProviderAdapterManifest({manifest.key!r}, {manifest.display_name!r})\n\n    async def build_source(self, recipe):\n        # Replace build_source() internals with the approved provider.\n        # Always return a NiceGUI Base DataSource; keep auth/database/proxy details here.\n        return build_source()\n\n    def field_overrides(self, recipe):\n        # Return only explicit, reviewed logical-field -> source-field mappings.\n        return {{}}\n'''


def provider_fixture_template(*, recipes: Sequence[str] = ('spc-monitor',), profile_key: str = 'production') -> dict[str, Any]:
    fixtures = [ProviderConformanceFixture(f'{key}-{profile_key}', key, profile_key).to_dict() for key in recipes]
    return {'schema_version': 1, 'fixtures': fixtures}


__all__ = [
    'PROVIDER_CONFORMANCE_PROFILES', 'ProviderAdapterManifest', 'ProviderConformanceFixture',
    'ProviderConformanceProfile', 'ProviderConformanceSuiteReport', 'ProviderDiagnosticGuidance',
    'ProviderFixtureResult', 'SemiconductorProviderAdapterBase', 'load_provider_fixtures',
    'load_semiconductor_adapter', 'provider_adapter_template_source', 'provider_diagnostic_guidance',
    'provider_fixture_from_dict', 'provider_fixture_template', 'provider_report_guidance',
    'run_provider_conformance_fixture', 'run_provider_conformance_suite',
]
