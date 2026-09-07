from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class WorkbenchKind(str, Enum):
    COMPONENT = 'component'
    PATTERN = 'pattern'
    ANALYTIC = 'analytic'
    RECIPE = 'recipe'
    REFERENCE = 'reference'


def _contract_values(value: Any, *, fallback: tuple[str, ...] = ()) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else fallback
    if isinstance(value, (list, tuple, set, frozenset)):
        values = tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))
        return values or fallback
    return fallback


_DIRECT_REFERENCE_REGISTRIES = frozenset({
    'content', 'tables', 'visualizations', 'engineering', 'interactions', 'icons', 'illustrations',
})


@dataclass(frozen=True, slots=True)
class ReferenceContract:
    """The human and machine-readable contract for one catalog capability.

    The contract is presentation metadata derived from the canonical registry entry;
    it never replaces the registry as framework truth.  Tuple fields keep the payload
    deterministic and JSON-safe while allowing registry definitions to remain unchanged.
    """

    schema_version: int = 1
    variants: tuple[str, ...] = ()
    configuration: tuple[str, ...] = ()
    when_to_use: tuple[str, ...] = ()
    when_not_to_use: tuple[str, ...] = ()
    data_contract: tuple[str, ...] = ()
    states: tuple[str, ...] = ()
    responsive_behavior: tuple[str, ...] = ()
    accessibility: tuple[str, ...] = ()
    recommended_code: str = ''
    alternatives: tuple[str, ...] = ()
    complements: tuple[str, ...] = ()
    best_for: tuple[str, ...] = ()
    avoid_for: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    domain_tags: tuple[str, ...] = ()
    complexity: str = ''
    density: str = ''
    live_example: bool = False
    example_proof: str = ''
    nonvisual_variant: str | None = None

    @classmethod
    def from_entry(cls, entry: 'WorkbenchEntry') -> 'ReferenceContract':
        metadata = entry.metadata
        registry = str(metadata.get('registry_name') or '').strip().casefold()
        catalog_item = metadata.get('catalog_item')
        catalog_item = catalog_item if isinstance(catalog_item, Mapping) else {}
        variants = _contract_values(metadata.get('variants') or catalog_item.get('variants'), fallback=('default',))
        related = _contract_values(entry.related_keys)
        alternatives = _contract_values(metadata.get('alternatives') or catalog_item.get('alternatives'), fallback=related)
        complements = _contract_values(metadata.get('complements') or catalog_item.get('complements'), fallback=related)
        domains = tuple(dict.fromkeys(
            str(value).strip() for value in (*entry.tags, entry.category, registry.replace('_', ' '))
            if str(value).strip()
        ))
        data_backed = entry.kind in {WorkbenchKind.ANALYTIC, WorkbenchKind.RECIPE} or registry in {
            'tables', 'visualizations', 'analysis', 'data_sources',
        }
        live_example = bool(entry.live_preview and (entry.kind is not WorkbenchKind.REFERENCE or registry in _DIRECT_REFERENCE_REGISTRIES))
        nonvisual_variant = None if live_example else (
            f'Nonvisual contract reference for {entry.source_authority or "the canonical framework authority"}; '
            'use the typed API contract and related runnable composition when implementing it.'
        )
        api_name = str(
            catalog_item.get('public_name') or catalog_item.get('name') or entry.title
        ).strip()
        source = entry.source_authority or 'canonical NiceGUI Base registry'
        public_import = (
            f'from nicegui_base import {api_name}\n\n'
            if api_name.isidentifier() else
            'import nicegui_base\n\n'
        )
        recommended_code = (
            public_import
            + f'# Generated from the current ReferenceContract for {entry.key}\n'
            + f'# Canonical authority: {source}\n'
            + f'# Use the registered {api_name} API; keep domain logic in app-owned services.\n'
        )
        data_contract = (
            ('rows are a sequence of named mappings; preserve field names, row order, nulls, and schema semantics.',
             'numeric values must be finite when consumed by an analytical renderer.')
            if data_backed else
            ('typed framework configuration and registry-defined inputs; no project-owned data mutation is implied.',)
        )
        best_for = _contract_values(entry.use_when, fallback=(entry.description,))
        avoid_for = _contract_values(entry.avoid_when, fallback=('Do not substitute an unregistered visual or state implementation.',))
        requires = _contract_values(metadata.get('requires') or catalog_item.get('requires'), fallback=(source,))
        produces = _contract_values(metadata.get('produces') or catalog_item.get('produces'), fallback=('a governed reference example and production usage guidance',))
        return cls(
            variants=variants,
            configuration=('theme', 'density', 'responsive_width', 'registered options'),
            when_to_use=best_for,
            when_not_to_use=avoid_for,
            data_contract=data_contract,
            states=('loading', 'empty', 'error', 'disabled', 'readonly', 'overflow'),
            responsive_behavior=(
                'desktop: full reference composition',
                'tablet: semantic slots collapse to a readable single column where applicable',
                'phone: controls and content remain keyboard reachable without horizontal overflow',
            ),
            accessibility=(
                'use the registered accessible field/control wrapper',
                'preserve labels, focus order, keyboard activation, and durable state messaging',
            ),
            recommended_code=recommended_code,
            alternatives=alternatives or ('choose a registered alternative for a different task',),
            complements=complements or ('compose with the closest registered page pattern or data contract',),
            best_for=best_for,
            avoid_for=avoid_for,
            requires=requires,
            produces=produces,
            domain_tags=domains or ('framework',),
            complexity='moderate' if entry.kind in {WorkbenchKind.ANALYTIC, WorkbenchKind.RECIPE, WorkbenchKind.PATTERN} else 'focused',
            density='compact',
            live_example=live_example,
            example_proof=(
                f'{"Direct registered renderer" if live_example else "Explicit nonvisual contract"} · '
                f'{entry.route} · {source}'
            ),
            nonvisual_variant=nonvisual_variant,
        )

    def validate(self) -> tuple[str, ...]:
        required = (
            'variants', 'configuration', 'when_to_use', 'when_not_to_use', 'data_contract',
            'states', 'responsive_behavior', 'accessibility', 'recommended_code',
            'alternatives', 'complements', 'best_for', 'avoid_for', 'requires', 'produces',
            'domain_tags', 'complexity', 'density', 'example_proof',
        )
        issues = [f'{field_name} is empty' for field_name in required if not getattr(self, field_name)]
        if not self.live_example and not self.nonvisual_variant:
            issues.append('nonvisual_variant is required when live_example is false')
        if not isinstance(self.live_example, bool):
            issues.append('live_example must be boolean')
        return tuple(issues)

    @property
    def search_terms(self) -> tuple[str, ...]:
        return (*self.best_for, *self.avoid_for, *self.requires, *self.produces, *self.domain_tags,
                *self.alternatives, *self.complements, *self.data_contract, *self.states)

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'variants': list(self.variants),
            'configuration': list(self.configuration),
            'when_to_use': list(self.when_to_use),
            'when_not_to_use': list(self.when_not_to_use),
            'data_contract': list(self.data_contract),
            'states': list(self.states),
            'responsive_behavior': list(self.responsive_behavior),
            'accessibility': list(self.accessibility),
            'recommended_code': self.recommended_code,
            'alternatives': list(self.alternatives),
            'complements': list(self.complements),
            'best_for': list(self.best_for),
            'avoid_for': list(self.avoid_for),
            'requires': list(self.requires),
            'produces': list(self.produces),
            'domain_tags': list(self.domain_tags),
            'complexity': self.complexity,
            'density': self.density,
            'live_example': self.live_example,
            'example_proof': self.example_proof,
            'nonvisual_variant': self.nonvisual_variant,
        }


@dataclass(frozen=True, slots=True)
class WorkbenchEntry:
    """Presentation metadata for one discoverable NiceGUI Base capability.

    This model never becomes domain truth. ``source_authority`` identifies the
    canonical registry/catalog that owns the capability, while preview/sample and
    relationship fields describe only how the Workbench exposes that authority.
    """

    key: str
    kind: WorkbenchKind
    title: str
    description: str
    route: str
    category: str = ''
    aliases: tuple[str, ...] = ()
    use_when: tuple[str, ...] = ()
    avoid_when: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    source_authority: str = ''
    maturity: str = ''
    live_preview: bool = False
    sample_data: bool = False
    related_keys: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    contract: ReferenceContract | None = None

    def __post_init__(self) -> None:
        if self.contract is None:
            object.__setattr__(self, 'contract', ReferenceContract.from_entry(self))

    @property
    def reference_contract(self) -> ReferenceContract:
        # The default is installed in __post_init__; the fallback keeps manually
        # constructed compatibility objects safe if a third-party dataclass bypasses it.
        return self.contract or ReferenceContract.from_entry(self)

    @property
    def searchable_text(self) -> str:
        parts = (
            self.key, self.kind.value, self.title, self.description, self.category,
            self.source_authority, self.maturity,
            *self.aliases, *self.use_when, *self.avoid_when, *self.tags, *self.related_keys,
            *self.reference_contract.search_terms,
        )
        return ' '.join(str(part) for part in parts if part)


@dataclass(frozen=True, slots=True)
class SearchResult:
    entry: WorkbenchEntry
    score: int
    matched_terms: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkbenchCoverage:
    total: int
    components: int
    patterns: int
    analytics: int
    recipes: int
    categories: tuple[str, ...]
