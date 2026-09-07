"""Small deterministic discovery facade for coding agents.

This module only projects existing registries. It must not become a second catalog or
pattern/visualization authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from nicegui_base.ai.context import build_agent_context
from nicegui_base.patterns.composition import get_application_pattern
from nicegui_base.workbench.catalog import (
    all_entries,
    catalog_contract_audit as _catalog_contract_audit,
    catalog_family_coverage,
    framework_catalog_audit as _framework_catalog_audit,
    search as _search,
)
from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind


_MAX_RESULTS = 50


def _bounded_limit(limit: int) -> int:
    value = int(limit)
    if value < 1:
        raise ValueError('limit must be at least 1')
    return min(value, _MAX_RESULTS)


@dataclass(frozen=True, slots=True)
class CatalogMatch:
    """Bounded machine-readable projection of a canonical catalog result."""

    key: str
    title: str
    kind: str
    score: int
    route: str
    source_authority: str
    best_for: tuple[str, ...]
    data_contract: tuple[str, ...]
    alternatives: tuple[str, ...]

    @classmethod
    def from_entry(cls, entry: WorkbenchEntry, score: int) -> 'CatalogMatch':
        contract = entry.reference_contract
        return cls(
            key=entry.key,
            title=entry.title,
            kind=entry.kind.value,
            score=score,
            route=entry.route,
            source_authority=entry.source_authority,
            best_for=tuple(contract.best_for[:3]),
            data_contract=tuple(contract.data_contract[:3]),
            alternatives=tuple(contract.alternatives[:4]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {
            'best_for': list(self.best_for),
            'data_contract': list(self.data_contract),
            'alternatives': list(self.alternatives),
        }


@dataclass(frozen=True, slots=True)
class PatternRecommendation:
    requirement: str
    pattern: str
    page_pattern: str
    purpose: str
    starter_template: str
    recipe: str | None
    composition_apis: tuple[str, ...]
    pattern_command: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {'composition_apis': list(self.composition_apis)}


@dataclass(frozen=True, slots=True)
class VisualizationRecommendation:
    intent: str
    schema: tuple[str, ...]
    domain: str | None
    results: tuple[CatalogMatch, ...]

    @property
    def primary(self) -> CatalogMatch | None:
        return self.results[0] if self.results else None

    def to_dict(self) -> dict[str, Any]:
        return {
            'intent': self.intent,
            'schema': list(self.schema),
            'domain': self.domain,
            'primary': self.primary.to_dict() if self.primary else None,
            'results': [item.to_dict() for item in self.results],
        }


@dataclass(frozen=True, slots=True)
class ScaffoldPlan:
    requirement: str
    pattern: str
    recipe: str | None
    pattern_command: str
    recipe_command: str | None
    authority: str
    validation_commands: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {'validation_commands': list(self.validation_commands)}


def catalog_search(
    query: str = '',
    *,
    limit: int = 20,
    intent: str | None = None,
    data_shape: str | None = None,
    domain: str | None = None,
    related_to: str | None = None,
) -> tuple[CatalogMatch, ...]:
    """Search the canonical Reference Explorer projection with bounded output."""
    results = _search(
        query,
        limit=_bounded_limit(limit),
        intent=intent,
        data_shape=data_shape,
        domain=domain,
        related_to=related_to,
    )
    return tuple(CatalogMatch.from_entry(item.entry, item.score) for item in results)


def recommend_pattern(requirement: str) -> PatternRecommendation:
    """Use the existing task-context pattern scorer and expose its authority compactly."""
    pack = build_agent_context(requirement)
    profile = get_application_pattern(pack.dominant_pattern)
    return PatternRecommendation(
        requirement=pack.task,
        pattern=profile.key,
        page_pattern=profile.page_pattern.value,
        purpose=profile.purpose,
        starter_template=pack.starter_template,
        recipe=pack.starter_recipe,
        composition_apis=profile.composition_apis,
        pattern_command=(
            f'nicegui-base create-pattern ./<app> --name "<App Name>" --pattern {profile.key}'
        ),
    )


def recommend_visualization(
    intent: str,
    *,
    schema: Iterable[str] = (),
    domain: str | None = None,
    limit: int = 5,
) -> VisualizationRecommendation:
    """Recommend registered analytical surfaces from intent and named schema fields."""
    text = str(intent).strip()
    if not text:
        raise ValueError('visualization intent must not be empty')
    fields = tuple(dict.fromkeys(str(field).strip() for field in schema if str(field).strip()))
    entries = tuple(item for item in all_entries() if item.kind is WorkbenchKind.ANALYTIC)
    # ``domain`` is an existing ReferenceContract filter; schema fields remain query
    # evidence because field names are application-owned and cannot be a fixed enum.
    from nicegui_base.workbench.search import search_entries

    results = search_entries(entries, text, limit=_bounded_limit(limit), domain=domain)
    if not results and fields:
        results = search_entries(entries, ' '.join((text, *fields)), limit=_bounded_limit(limit), domain=domain)
    return VisualizationRecommendation(
        intent=text,
        schema=fields,
        domain=domain,
        results=tuple(CatalogMatch.from_entry(item.entry, item.score) for item in results),
    )


def scaffold_plan(requirement: str) -> ScaffoldPlan:
    """Return commands only; callers choose the destination and own filesystem writes."""
    recommendation = recommend_pattern(requirement)
    recipe_command = None
    if recommendation.recipe:
        recipe_command = f'nicegui-base create-recipe ./<app> --name "<App Name>" --recipe {recommendation.recipe}'
    return ScaffoldPlan(
        requirement=recommendation.requirement,
        pattern=recommendation.pattern,
        recipe=recommendation.recipe,
        pattern_command=recommendation.pattern_command,
        recipe_command=recipe_command,
        authority='installed nicegui_base public APIs and canonical registries',
        validation_commands=('nicegui-base agent-check .', 'nicegui-base gate .'),
    )


def catalog_audit() -> dict[str, Any]:
    """Validate the canonical catalog projection without maintaining another registry."""
    contract = _catalog_contract_audit()
    framework = _framework_catalog_audit()
    families = catalog_family_coverage()
    return {
        'passed': contract.complete and framework.complete and all(families.values()),
        'catalog': {
            'total': contract.total,
            'conforming': contract.conforming,
            'issues': list(contract.issues),
        },
        'framework_catalog': {
            'declared': framework.declared,
            'identified': framework.identified,
            'canonical_total': framework.canonical_total,
            'visible': framework.visible,
            'missing': [list(item) for item in framework.missing],
            'duplicates': [list(item) for item in framework.duplicates],
        },
        'families': families,
    }


__all__ = [
    'CatalogMatch', 'PatternRecommendation', 'ScaffoldPlan', 'VisualizationRecommendation',
    'catalog_search', 'recommend_pattern', 'recommend_visualization',
    'scaffold_plan', 'catalog_audit',
]
