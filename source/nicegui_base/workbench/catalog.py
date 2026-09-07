from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .models import WorkbenchCoverage, WorkbenchEntry, WorkbenchKind
from .registry_adapters import build_registry_entries, canonical_catalog_item_key
from .search import search_entries


EXPECTED_FRAMEWORK_CATALOG_RECORDS = 450


REQUIRED_CATALOG_FAMILIES = (
    'shell/layout',
    'controls',
    'forms/overlays',
    'tables',
    'content/workflow',
    'generic visualizations',
    'engineering components',
    'generic application patterns',
    'semiconductor analytics',
    'semiconductor recipes',
    'state/failure utilities',
    'performance/quality utilities',
)


def catalog_family(entry: WorkbenchEntry) -> str | None:
    """Map a discoverable entry to the plan-level catalog family it satisfies.

    This is presentation coverage only. Canonical capability metadata remains owned by
    the source registries identified on each :class:`WorkbenchEntry`.
    """
    if entry.kind is WorkbenchKind.ANALYTIC:
        return 'semiconductor analytics'
    if entry.kind is WorkbenchKind.RECIPE:
        return 'semiconductor recipes'
    if entry.kind is WorkbenchKind.PATTERN:
        return 'generic application patterns'
    if entry.kind is WorkbenchKind.COMPONENT:
        return 'controls'
    family = str(entry.metadata.get('catalog_family') or '').strip()
    if family in REQUIRED_CATALOG_FAMILIES:
        return family
    authority = entry.source_authority.casefold()
    category = entry.category.casefold()
    registry = str(entry.metadata.get('registry_name') or '').casefold()
    text = ' '.join((authority, category, registry))
    if any(token in text for token in ('layout', 'shell', 'navigation')):
        return 'shell/layout'
    if any(token in text for token in ('interaction', 'form', 'filter', 'overlay', 'feedback')):
        return 'forms/overlays'
    if 'table' in text:
        return 'tables'
    if any(token in text for token in ('content', 'workflow', 'jobs')):
        return 'content/workflow'
    if 'visualization' in text:
        return 'generic visualizations'
    if 'engineering' in text:
        return 'engineering components'
    if 'pattern' in text:
        return 'generic application patterns'
    if any(token in text for token in ('state', 'runtime', 'security', 'convenience')):
        return 'state/failure utilities'
    if any(token in text for token in ('performance', 'quality', 'governance', 'diagnostic')):
        return 'performance/quality utilities'
    return None


def catalog_family_coverage(entries: tuple[WorkbenchEntry, ...] | None = None) -> dict[str, int]:
    source = all_entries() if entries is None else tuple(entries)
    counts = {family: 0 for family in REQUIRED_CATALOG_FAMILIES}
    for entry in source:
        family = catalog_family(entry)
        if family in counts:
            counts[family] += 1
    return counts


@lru_cache(maxsize=1)
def all_entries() -> tuple[WorkbenchEntry, ...]:
    return build_registry_entries()


def entries_for(kind: WorkbenchKind | str) -> tuple[WorkbenchEntry, ...]:
    target = kind if isinstance(kind, WorkbenchKind) else WorkbenchKind(kind)
    return tuple(entry for entry in all_entries() if entry.kind is target)


def analytics_entries() -> tuple[WorkbenchEntry, ...]:
    return entries_for(WorkbenchKind.ANALYTIC)


def recipe_entries() -> tuple[WorkbenchEntry, ...]:
    return entries_for(WorkbenchKind.RECIPE)


def search(
    query: str = '',
    *,
    limit: int = 30,
    intent: str | None = None,
    data_shape: str | None = None,
    domain: str | None = None,
    related_to: str | None = None,
):
    return search_entries(
        all_entries(), query, limit=limit, intent=intent, data_shape=data_shape,
        domain=domain, related_to=related_to,
    )


@dataclass(frozen=True, slots=True)
class CatalogContractAudit:
    total: int
    conforming: int
    issues: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.total > 0 and self.total == self.conforming and not self.issues


def catalog_contract_audit(entries: tuple[WorkbenchEntry, ...] | None = None) -> CatalogContractAudit:
    """Validate the typed Reference Explorer contract for the complete catalog projection."""
    source = all_entries() if entries is None else tuple(entries)
    issues: list[str] = []
    for entry in source:
        for issue in entry.reference_contract.validate():
            issues.append(f'{entry.key}: {issue}')
    keys = [entry.key for entry in source]
    issues.extend(f'duplicate key: {key}' for key in sorted({key for key in keys if keys.count(key) > 1}))
    conforming = sum(1 for entry in source if not entry.reference_contract.validate())
    return CatalogContractAudit(len(source), conforming, tuple(issues))


CATALOG_INTENT_FILTERS = (
    ('monitoring', 'Monitoring and health'),
    ('search', 'Search and refine'),
    ('filter', 'Filtering and cross-filtering'),
    ('compare', 'Compare populations or entities'),
    ('investigation', 'Investigation and root cause'),
    ('distribution', 'Distribution analysis'),
    ('settings', 'Settings and configuration'),
    ('workflow', 'Guided workflow'),
    ('table', 'Tabular records'),
    ('visualization', 'Charts and visualizations'),
    ('export', 'Export and generated code'),
)


def catalog_filter_options(entries: tuple[WorkbenchEntry, ...] | None = None) -> dict[str, tuple[str, ...]]:
    """Return bounded, deterministic values suitable for Reference Explorer controls."""
    source = all_entries() if entries is None else tuple(entries)
    domains = sorted({tag for entry in source for tag in entry.reference_contract.domain_tags if tag})
    related = sorted({key for entry in source for key in (*entry.related_keys, *entry.reference_contract.alternatives) if key in {item.key for item in source}})
    return {
        'intents': tuple(key for key, _label in CATALOG_INTENT_FILTERS),
        'data_shapes': ('rows', 'typed', 'numeric'),
        'domains': tuple(domains),
        'related': tuple(related),
    }


def coverage() -> WorkbenchCoverage:
    entries = all_entries()
    return WorkbenchCoverage(
        total=len(entries),
        components=sum(entry.kind is WorkbenchKind.COMPONENT for entry in entries),
        patterns=sum(entry.kind is WorkbenchKind.PATTERN for entry in entries),
        analytics=sum(entry.kind is WorkbenchKind.ANALYTIC for entry in entries),
        recipes=sum(entry.kind is WorkbenchKind.RECIPE for entry in entries),
        categories=tuple(sorted({entry.category for entry in entries if entry.category})),
    )


@dataclass(frozen=True, slots=True)
class FrameworkCatalogAudit:
    declared: int
    identified: int
    canonical_total: int
    visible: int
    missing: tuple[tuple[str, str], ...]
    duplicates: tuple[tuple[str, str], ...]

    @property
    def complete(self) -> bool:
        return (
            self.declared == EXPECTED_FRAMEWORK_CATALOG_RECORDS
            and self.declared == self.identified == self.canonical_total == self.visible
            and not self.missing
            and not self.duplicates
        )


def framework_catalog_audit(entries: tuple[WorkbenchEntry, ...] | None = None) -> FrameworkCatalogAudit:
    """Evaluate shape, visibility, and uniqueness from one catalog payload read."""
    try:
        from nicegui_base.ai.catalog import load_framework_catalog
        payload = load_framework_catalog()
    except (ImportError, FileNotFoundError, ValueError, TypeError):
        return FrameworkCatalogAudit(0, 0, 0, 0, (), ())
    counts = payload.get('registry_counts', {})
    declared = sum(int(value) for value in counts.values() if isinstance(value, int) and not isinstance(value, bool)) if isinstance(counts, dict) else 0
    registries = payload.get('registries', {})
    identified_keys: list[tuple[str, str]] = []
    if isinstance(registries, dict):
        for registry_name, items in registries.items():
            if not isinstance(items, list):
                continue
            registry = str(registry_name)
            for item in items:
                raw = canonical_catalog_item_key(registry, item)
                if raw:
                    identified_keys.append((registry, raw))
    canonical = set(identified_keys)
    source = all_entries() if entries is None else tuple(entries)
    visible_counts: dict[tuple[str, str], int] = {}
    for entry in source:
        key = _workbench_catalog_key(entry)
        if key is not None and key in canonical:
            visible_counts[key] = visible_counts.get(key, 0) + 1
    visible_keys = set(visible_counts)
    return FrameworkCatalogAudit(
        declared=declared,
        identified=len(identified_keys),
        canonical_total=len(canonical),
        visible=len(canonical & visible_keys),
        missing=tuple(sorted(canonical - visible_keys)),
        duplicates=tuple(sorted(key for key, count in visible_counts.items() if count > 1)),
    )


def framework_catalog_shape_counts() -> tuple[int, int]:
    audit = framework_catalog_audit(())
    return audit.declared, audit.identified


def _canonical_framework_catalog_keys() -> set[tuple[str, str]]:
    try:
        from nicegui_base.ai.catalog import load_framework_catalog
        payload = load_framework_catalog()
    except (ImportError, FileNotFoundError, ValueError, TypeError):
        return set()
    registries = payload.get('registries', {})
    if not isinstance(registries, dict):
        return set()
    result: set[tuple[str, str]] = set()
    for registry_name, items in registries.items():
        if not isinstance(items, list):
            continue
        registry = str(registry_name)
        for item in items:
            raw = canonical_catalog_item_key(registry, item)
            if raw:
                result.add((registry, raw))
    return result


def _workbench_catalog_key(entry: WorkbenchEntry) -> tuple[str, str] | None:
    if entry.kind is WorkbenchKind.COMPONENT and entry.metadata.get('component_key'):
        return ('components', str(entry.metadata['component_key']))
    if entry.kind is WorkbenchKind.PATTERN and entry.metadata.get('pattern_key'):
        return ('page_patterns', str(entry.metadata['pattern_key']))
    if entry.kind is WorkbenchKind.ANALYTIC and entry.metadata.get('surface_key'):
        return ('semiconductor', str(entry.metadata['surface_key']))
    if entry.kind is WorkbenchKind.RECIPE and entry.metadata.get('recipe_key'):
        return ('semiconductor_recipes', str(entry.metadata['recipe_key']))
    registry = str(entry.metadata.get('registry_name') or '').strip()
    raw = str(entry.metadata.get('registry_key') or '').strip()
    return (registry, raw) if registry and raw and registry != 'construction' else None


def framework_catalog_duplicate_keys(entries: tuple[WorkbenchEntry, ...] | None = None) -> tuple[tuple[str, str], ...]:
    return framework_catalog_audit(entries).duplicates


def framework_catalog_parity(entries: tuple[WorkbenchEntry, ...] | None = None) -> tuple[int, int, tuple[tuple[str, str], ...]]:
    audit = framework_catalog_audit(entries)
    return audit.canonical_total, audit.visible, audit.missing
