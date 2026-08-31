from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable
import re

from nicegui_base.data_sources import DataSchema, DataSource, FieldRole, FieldType, SourceCapabilities, SourceHealth

from .recipes import RecipeFieldRequirement, RecipeSourceCompatibility, SemiconductorRecipeDefinition, get_semiconductor_recipe, resolve_recipe_source


class BindingMethod(str, Enum):
    OVERRIDE = 'override'
    EXACT_ALIAS = 'exact_alias'
    NORMALIZED_ALIAS = 'normalized_alias'
    SEMANTIC_ROLE = 'semantic_role'
    NAME_SIMILARITY = 'name_similarity'


@dataclass(frozen=True, slots=True)
class BindingCandidate:
    logical_field: str
    source_field: str
    score: float
    method: BindingMethod
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.logical_field.strip() or not self.source_field.strip():
            raise ValueError('binding candidate fields must not be empty')
        if not 0.0 <= self.score <= 1.0:
            raise ValueError('binding candidate score must be between 0 and 1')
        object.__setattr__(self, 'evidence', tuple(self.evidence))


@dataclass(frozen=True, slots=True)
class BindingDecision:
    logical_field: str
    source_field: str | None
    score: float
    method: BindingMethod | None
    auto_bound: bool
    ambiguous: bool = False
    alternatives: tuple[BindingCandidate, ...] = ()
    reason: str = ''

    def __post_init__(self) -> None:
        object.__setattr__(self, 'alternatives', tuple(self.alternatives))


@dataclass(frozen=True, slots=True)
class SmartBindingPolicy:
    min_auto_score: float = 0.76
    ambiguity_margin: float = 0.03
    max_candidates: int = 5

    def __post_init__(self) -> None:
        if not 0 <= self.min_auto_score <= 1:
            raise ValueError('min_auto_score must be between 0 and 1')
        if not 0 <= self.ambiguity_margin <= 1:
            raise ValueError('ambiguity_margin must be between 0 and 1')
        if self.max_candidates < 1:
            raise ValueError('max_candidates must be >= 1')


@dataclass(frozen=True, slots=True)
class RecipeOnboardingReport:
    recipe_key: str
    source_key: str
    provider: str
    schema_revision: str | None
    compatibility: RecipeSourceCompatibility
    decisions: Mapping[str, BindingDecision]
    recommended_overrides: Mapping[str, str]
    source_health: SourceHealth
    capabilities: SourceCapabilities
    warnings: tuple[str, ...] = ()
    adapter_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'decisions', MappingProxyType(dict(self.decisions)))
        object.__setattr__(self, 'recommended_overrides', MappingProxyType(dict(self.recommended_overrides)))
        object.__setattr__(self, 'warnings', tuple(self.warnings))
        object.__setattr__(self, 'adapter_metadata', MappingProxyType(dict(self.adapter_metadata)))

    @property
    def ready(self) -> bool:
        return self.compatibility.compatible

    @property
    def unresolved_required(self) -> tuple[str, ...]:
        return self.compatibility.missing_required

    def to_dict(self) -> dict[str, Any]:
        return {
            'recipe_key': self.recipe_key,
            'source_key': self.source_key,
            'provider': self.provider,
            'schema_revision': self.schema_revision,
            'ready': self.ready,
            'bindings': dict(self.compatibility.bindings),
            'recommended_overrides': dict(self.recommended_overrides),
            'missing_required': self.compatibility.missing_required,
            'missing_optional': self.compatibility.missing_optional,
            'available_panels': self.compatibility.available_panels,
            'unavailable_panels': self.compatibility.unavailable_panels,
            'available_filters': self.compatibility.available_filters,
            'unavailable_filters': self.compatibility.unavailable_filters,
            'warnings': self.warnings,
            'health': self.source_health.status.value,
            'capabilities': {name: getattr(self.capabilities, name) for name in self.capabilities.__dataclass_fields__},
            'decisions': {
                key: {
                    'source_field': value.source_field,
                    'score': value.score,
                    'method': value.method.value if value.method else None,
                    'auto_bound': value.auto_bound,
                    'ambiguous': value.ambiguous,
                    'reason': value.reason,
                    'alternatives': [
                        {'source_field': item.source_field, 'score': item.score, 'method': item.method.value, 'evidence': item.evidence}
                        for item in value.alternatives
                    ],
                }
                for key, value in self.decisions.items()
            },
            'adapter_metadata': dict(self.adapter_metadata),
        }


@dataclass(frozen=True, slots=True)
class AdaptedSemiconductorSource:
    source: DataSource
    field_overrides: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    owns_source: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, 'field_overrides', MappingProxyType(dict(self.field_overrides)))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))


@runtime_checkable
class SemiconductorSourceAdapter(Protocol):
    """Provider-neutral hook that adapts company data into the existing DataSource authority.

    Implementations may open SQL/ODBC/REST/company sources, but must return a Wave 59
    DataSource and optional explicit semantic overrides. They do not own page/query state.
    """
    key: str

    async def open(self, recipe: SemiconductorRecipeDefinition) -> AdaptedSemiconductorSource: ...


def _norm(value: str) -> str:
    return ''.join(ch for ch in value.casefold() if ch.isalnum())


def _tokens(value: str) -> tuple[str, ...]:
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', value)
    return tuple(token for token in re.split(r'[^A-Za-z0-9]+', text.casefold()) if token)


def _type_role_fit(requirement: RecipeFieldRequirement, field_type: FieldType, role: FieldRole) -> float:
    if requirement.roles and role in requirement.roles:
        return 1.0
    if requirement.roles:
        # Identifiers/dimensions/entities are often represented interchangeably by provider schemas.
        identity = {FieldRole.IDENTIFIER, FieldRole.DIMENSION, FieldRole.ENTITY}
        if role in identity and any(item in identity for item in requirement.roles):
            return 0.72
        return 0.0
    if field_type in {FieldType.FLOAT, FieldType.INTEGER, FieldType.DECIMAL}:
        return 0.58
    return 0.5


def binding_candidates(requirement: RecipeFieldRequirement, schema: DataSchema) -> tuple[BindingCandidate, ...]:
    candidates: list[BindingCandidate] = []
    aliases = tuple(dict.fromkeys((requirement.key, *requirement.candidates)))
    norm_aliases = {_norm(item): item for item in aliases}
    alias_tokens = set(token for item in aliases for token in _tokens(item))
    for field in schema.fields:
        if field.name == requirement.key:
            candidates.append(BindingCandidate(requirement.key, field.name, 1.0, BindingMethod.EXACT_ALIAS, ('exact logical-field name',)))
            continue
        if field.name in requirement.candidates:
            rank = requirement.candidates.index(field.name)
            score = max(0.80, 0.96 - 0.04 * rank)
            candidates.append(BindingCandidate(requirement.key, field.name, score, BindingMethod.EXACT_ALIAS, (f'governed alias rank {rank + 1}',)))
            continue
        normalized = _norm(field.name)
        if normalized in norm_aliases:
            candidates.append(BindingCandidate(requirement.key, field.name, 0.96, BindingMethod.NORMALIZED_ALIAS, (f'normalized alias {norm_aliases[normalized]!r}',)))
            continue
        if requirement.roles and field.role in requirement.roles:
            candidates.append(BindingCandidate(requirement.key, field.name, 0.82, BindingMethod.SEMANTIC_ROLE, (f'schema role {field.role.value}',)))
            continue
        field_tokens = set(_tokens(field.name))
        overlap = len(alias_tokens & field_tokens)
        if overlap:
            union = max(1, len(alias_tokens | field_tokens))
            similarity = overlap / union
            role_fit = _type_role_fit(requirement, field.type, field.role)
            score = min(0.79, 0.54 + 0.20 * similarity + 0.10 * role_fit)
            candidates.append(BindingCandidate(requirement.key, field.name, score, BindingMethod.NAME_SIMILARITY, (f'name token overlap {overlap}', f'role/type fit {role_fit:.2f}')))
    candidates.sort(key=lambda item: (-item.score, item.source_field))
    return tuple(candidates)


def smart_binding_decisions(
    recipe: str | SemiconductorRecipeDefinition,
    schema: DataSchema,
    *,
    field_overrides: Mapping[str, str] | None = None,
    policy: SmartBindingPolicy = SmartBindingPolicy(),
) -> Mapping[str, BindingDecision]:
    definition = get_semiconductor_recipe(recipe) if isinstance(recipe, str) else recipe
    overrides = dict(field_overrides or {})
    available = set(schema.names)
    decisions: dict[str, BindingDecision] = {}
    reserved: set[str] = set()
    for requirement in definition.field_requirements:
        if requirement.key in overrides:
            source_field = overrides[requirement.key]
            if source_field not in available:
                raise KeyError(f'field override {requirement.key!r} references unknown source field {source_field!r}')
            decisions[requirement.key] = BindingDecision(requirement.key, source_field, 1.0, BindingMethod.OVERRIDE, True, reason='explicit application override')
            reserved.add(source_field)
            continue
        ranked = tuple(item for item in binding_candidates(requirement, schema) if item.source_field not in reserved)
        top = ranked[0] if ranked else None
        second = ranked[1] if len(ranked) > 1 else None
        ambiguous = bool(top and second and top.score - second.score < policy.ambiguity_margin)
        auto = bool(top and top.score >= policy.min_auto_score and not ambiguous)
        selected = top.source_field if auto else None
        if auto:
            reserved.add(selected)  # type: ignore[arg-type]
        reason = 'no credible field candidate' if top is None else ('ambiguous top candidates' if ambiguous else ('confidence below automatic threshold' if not auto else 'high-confidence unambiguous match'))
        decisions[requirement.key] = BindingDecision(
            requirement.key, selected, top.score if top else 0.0, top.method if top else None,
            auto, ambiguous, ranked[:policy.max_candidates], reason,
        )
    return MappingProxyType(decisions)


def recommended_field_overrides(decisions: Mapping[str, BindingDecision]) -> Mapping[str, str]:
    return MappingProxyType({key: decision.source_field for key, decision in decisions.items() if decision.auto_bound and decision.source_field is not None})


async def onboard_recipe_source(
    recipe: str | SemiconductorRecipeDefinition,
    source: DataSource,
    *,
    field_overrides: Mapping[str, str] | None = None,
    policy: SmartBindingPolicy = SmartBindingPolicy(),
    adapter_metadata: Mapping[str, Any] | None = None,
) -> RecipeOnboardingReport:
    definition = get_semiconductor_recipe(recipe) if isinstance(recipe, str) else recipe
    schema = await source.schema()
    health = await source.health()
    decisions = smart_binding_decisions(definition, schema, field_overrides=field_overrides, policy=policy)
    smart_overrides = dict(recommended_field_overrides(decisions))
    explicit = dict(field_overrides or {})
    smart_overrides.update(explicit)
    compatibility = resolve_recipe_source(definition, schema, field_overrides=smart_overrides, semantic_role_fallback=False, resolve_unoverridden=False)
    warnings: list[str] = []
    for key, decision in decisions.items():
        requirement = next(item for item in definition.field_requirements if item.key == key)
        if decision.ambiguous:
            warnings.append(f'{key}: ambiguous source fields; provide an explicit override')
        elif decision.source_field is None and requirement.required:
            warnings.append(f'{key}: required semantic is unresolved')
        elif decision.source_field is None:
            warnings.append(f'{key}: optional semantic is unresolved; dependent panels may be omitted')
    if not source.capabilities.filter_pushdown:
        warnings.append('source does not advertise filter pushdown; validate representative fab-scale performance before release')
    if not source.capabilities.pagination_pushdown:
        warnings.append('source does not advertise pagination pushdown; avoid unbounded production record queries')
    if not health.healthy:
        warnings.append(f'source health is {health.status.value}: {health.message or "no provider message"}')
    return RecipeOnboardingReport(
        definition.key, source.key, source.provider, schema.revision, compatibility, decisions,
        smart_overrides, health, source.capabilities, tuple(dict.fromkeys(warnings)), adapter_metadata or {},
    )


async def open_semiconductor_source(
    recipe: str | SemiconductorRecipeDefinition,
    source_or_adapter: DataSource | SemiconductorSourceAdapter,
) -> AdaptedSemiconductorSource:
    definition = get_semiconductor_recipe(recipe) if isinstance(recipe, str) else recipe
    if isinstance(source_or_adapter, DataSource):
        return AdaptedSemiconductorSource(source_or_adapter)
    if not isinstance(source_or_adapter, SemiconductorSourceAdapter):
        raise TypeError('source_or_adapter must be a DataSource or SemiconductorSourceAdapter')
    adapted = await source_or_adapter.open(definition)
    if not isinstance(adapted.source, DataSource):
        raise TypeError('SemiconductorSourceAdapter.open() must return AdaptedSemiconductorSource with a DataSource')
    return adapted


class OnboardingFieldState(str, Enum):
    BOUND = 'bound'
    AMBIGUOUS = 'ambiguous'
    REQUIRED = 'required'
    OPTIONAL = 'optional'


@dataclass(frozen=True, slots=True)
class OnboardingFieldView:
    logical_field: str
    description: str
    required: bool
    state: OnboardingFieldState
    source_field: str | None
    score: float
    method: BindingMethod | None
    reason: str
    alternatives: tuple[BindingCandidate, ...] = ()
    action: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'alternatives', tuple(self.alternatives))


@dataclass(frozen=True, slots=True)
class RecipeOnboardingView:
    recipe_key: str
    source_key: str
    ready: bool
    completion_ratio: float
    fields: tuple[OnboardingFieldView, ...]
    available_panels: tuple[str, ...]
    unavailable_panels: tuple[str, ...]
    available_filters: tuple[str, ...]
    unavailable_filters: tuple[str, ...]
    blocking_actions: tuple[str, ...]
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 0.0 <= self.completion_ratio <= 1.0:
            raise ValueError('completion_ratio must be between 0 and 1')
        for name in ('fields','available_panels','unavailable_panels','available_filters','unavailable_filters','blocking_actions','warnings'):
            object.__setattr__(self, name, tuple(getattr(self, name)))

    @property
    def bound_fields(self) -> int:
        return sum(item.state is OnboardingFieldState.BOUND for item in self.fields)

    @property
    def unresolved_required(self) -> tuple[str, ...]:
        return tuple(item.logical_field for item in self.fields if item.required and item.state is not OnboardingFieldState.BOUND)

    def to_dict(self) -> dict[str, Any]:
        return {
            'recipe_key': self.recipe_key,
            'source_key': self.source_key,
            'ready': self.ready,
            'completion_ratio': self.completion_ratio,
            'fields': [
                {
                    'logical_field': item.logical_field,
                    'description': item.description,
                    'required': item.required,
                    'state': item.state.value,
                    'source_field': item.source_field,
                    'score': item.score,
                    'method': item.method.value if item.method else None,
                    'reason': item.reason,
                    'action': item.action,
                    'alternatives': [
                        {'source_field': alt.source_field, 'score': alt.score, 'method': alt.method.value, 'evidence': alt.evidence}
                        for alt in item.alternatives
                    ],
                }
                for item in self.fields
            ],
            'available_panels': self.available_panels,
            'unavailable_panels': self.unavailable_panels,
            'available_filters': self.available_filters,
            'unavailable_filters': self.unavailable_filters,
            'blocking_actions': self.blocking_actions,
            'warnings': self.warnings,
        }


def build_recipe_onboarding_view(
    recipe: str | SemiconductorRecipeDefinition,
    report: RecipeOnboardingReport,
) -> RecipeOnboardingView:
    """Convert the onboarding report into a deterministic, UI-ready setup model.

    The view never guesses unresolved semantics. Ambiguity is rendered as a blocking
    choice with ranked alternatives so a page can ask the engineer for exactly one
    decision instead of exposing raw schema mechanics.
    """
    definition = get_semiconductor_recipe(recipe) if isinstance(recipe, str) else recipe
    if definition.key != report.recipe_key:
        raise ValueError(f'onboarding report is for {report.recipe_key!r}, not {definition.key!r}')
    fields: list[OnboardingFieldView] = []
    blocking: list[str] = []
    for requirement in definition.field_requirements:
        decision = report.decisions[requirement.key]
        if decision.source_field is not None:
            state = OnboardingFieldState.BOUND
            action = None
        elif decision.ambiguous:
            state = OnboardingFieldState.AMBIGUOUS
            action = f'Choose the source field for {requirement.key}'
        elif requirement.required:
            state = OnboardingFieldState.REQUIRED
            action = f'Map a required source field to {requirement.key}'
        else:
            state = OnboardingFieldState.OPTIONAL
            action = f'Optionally map {requirement.key} to enable more panels'
        if requirement.required and state is not OnboardingFieldState.BOUND:
            blocking.append(action or f'Resolve {requirement.key}')
        fields.append(OnboardingFieldView(
            requirement.key,
            requirement.description,
            requirement.required,
            state,
            decision.source_field,
            decision.score,
            decision.method,
            decision.reason,
            decision.alternatives,
            action,
        ))
    completion = (sum(item.state is OnboardingFieldState.BOUND for item in fields) / len(fields)) if fields else 1.0
    if not report.source_health.healthy:
        blocking.append(f'Restore source health ({report.source_health.status.value})')
    return RecipeOnboardingView(
        definition.key,
        report.source_key,
        report.ready and report.source_health.healthy,
        completion,
        tuple(fields),
        report.compatibility.available_panels,
        report.compatibility.unavailable_panels,
        report.compatibility.available_filters,
        report.compatibility.unavailable_filters,
        tuple(dict.fromkeys(blocking)),
        report.warnings,
    )


__all__ = [
    'AdaptedSemiconductorSource','BindingCandidate','BindingDecision','BindingMethod','OnboardingFieldState','OnboardingFieldView','RecipeOnboardingReport','RecipeOnboardingView',
    'SemiconductorSourceAdapter','SmartBindingPolicy','binding_candidates','build_recipe_onboarding_view','onboard_recipe_source',
    'open_semiconductor_source','recommended_field_overrides','smart_binding_decisions',
]
