from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import quote

from .models import WorkbenchEntry, WorkbenchKind


def canonical_catalog_item_key(registry: str, item) -> str:
    """Return the stable identity for one generated framework-catalog record."""
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, Mapping):
        return ''
    for field in (
        '_registry_key', 'key', 'public_name', 'name', 'recipe_key', 'policy_key',
        'profile_key', 'qualification_id', 'version',
    ):
        value = item.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ''


def _humanize(value: str) -> str:
    special = {
        'fdc': 'FDC', 'spc': 'SPC', 'rca': 'RCA', 'doe': 'DOE', 'pca': 'PCA',
        'spe': 'SPE', 'qq': 'Q-Q', 'ecdf': 'ECDF', 'cusum': 'CUSUM', 'ewma': 'EWMA',
        't2': 'T²', 'xbar': 'X̄', 'api': 'API', 'ui': 'UI', 'sql': 'SQL',
    }
    words = []
    for part in value.replace('-', '_').split('_'):
        words.append(special.get(part.casefold(), part.capitalize()))
    return ' '.join(words)


def _surface_aliases(key: str, purpose: str) -> tuple[str, ...]:
    aliases = [key.replace('_', ' ')]
    if key == 'fdc_hotelling_t2':
        aliases += ['Hotelling T²', 'Hotelling T2', 'T²', 'T2', 'multivariate anomaly', 'FDC T2']
    if key == 'fdc_spe_q':
        aliases += ['SPE Q', 'Q statistic', 'PCA residual']
    if key.startswith('wafer_'):
        aliases += ['wafer map', 'spatial']
    if key.startswith('spc_'):
        aliases += ['control chart', 'statistical process control']
    if key.startswith('rca_'):
        aliases += ['root cause analysis', 'investigation']
    if 'capability' in key:
        aliases += ['cp cpk pp ppk', 'process capability']
    return tuple(dict.fromkeys(alias for alias in aliases if alias and alias.casefold() not in purpose.casefold()))


def _surface_recipe_relationships() -> dict[str, tuple[str, ...]]:
    """Derive surface→recipe links from the canonical recipe registry when available."""
    try:
        from nicegui_base.semiconductor.recipes import SEMICONDUCTOR_RECIPE_REGISTRY
    except ImportError:
        return {}
    relationships: dict[str, list[str]] = {}
    for recipe_key, recipe in SEMICONDUCTOR_RECIPE_REGISTRY.items():
        for surface_key in tuple(getattr(recipe, 'surface_keys', ())):
            relationships.setdefault(str(surface_key), []).append(f'recipe:{recipe_key}')
    return {key: tuple(values) for key, values in relationships.items()}


def semiconductor_surface_entries() -> tuple[WorkbenchEntry, ...]:
    from nicegui_base.semiconductor.surfaces import SEMICONDUCTOR_SURFACE_REGISTRY

    relationships = _surface_recipe_relationships()
    entries: list[WorkbenchEntry] = []
    for key, definition in SEMICONDUCTOR_SURFACE_REGISTRY.items():
        entries.append(WorkbenchEntry(
            key=f'analytics:{key}',
            kind=WorkbenchKind.ANALYTIC,
            title=_humanize(key),
            description=definition.purpose,
            route=f'/analytics/{key}',
            category=definition.category,
            aliases=_surface_aliases(key, definition.purpose),
            use_when=tuple(definition.use_when),
            avoid_when=tuple(definition.avoid_when),
            tags=tuple(dict.fromkeys(
                (definition.category, 'engineering', 'semiconductor')
                + (('linked hover',) if definition.linked_hover else ())
                + (('spatial',) if definition.spatial else ())
            )),
            source_authority='SEMICONDUCTOR_SURFACE_REGISTRY',
            live_preview=True,
            sample_data=True,
            related_keys=relationships.get(key, ()),
            metadata={
                'surface_key': key,
                'linked_hover': bool(definition.linked_hover),
                'spatial': bool(definition.spatial),
            },
        ))
    return tuple(entries)


_RECIPE_INTENT_ALIASES = {
    'spc-monitor': ('monitoring app', 'process monitoring', 'new monitoring app'),
    'fdc-tool-health': ('monitoring app', 'equipment monitoring', 'new monitoring app', 'tool health'),
    'excursion-defense-line': ('investigation', 'excursion investigation', 'defense line'),
    'lot-wafer-explorer': ('wafer', 'wafer explorer', 'spatial investigation'),
    'yield-loss': ('yield analysis', 'loss analysis'),
    'pm-effect-analysis': ('maintenance investigation', 'before after pm'),
    'chamber-matching': ('chamber comparison', 'equipment matching'),
    'rca-cockpit': ('investigation', 'root cause investigation', 'analysis workspace'),
}


def semiconductor_recipe_entries() -> tuple[WorkbenchEntry, ...]:
    from nicegui_base.semiconductor.recipes import SEMICONDUCTOR_RECIPE_REGISTRY

    entries: list[WorkbenchEntry] = []
    for key, recipe in SEMICONDUCTOR_RECIPE_REGISTRY.items():
        surface_keys = tuple(recipe.surface_keys)
        surface_aliases = tuple(dict.fromkeys(
            alias
            for surface_key in surface_keys
            for alias in (surface_key.replace('_', ' '), _humanize(surface_key), *_surface_aliases(surface_key, ''))
        ))
        variants: tuple[str, ...] = ()
        try:
            from nicegui_base.semiconductor.variants import variants_for_recipe
            variants = tuple(item.key for item in variants_for_recipe(recipe))
        except (ImportError, AttributeError, KeyError, TypeError, ValueError):
            # Variants are optional catalog enrichment; recipe truth remains canonical.
            variants = ()
        entries.append(WorkbenchEntry(
            key=f'recipe:{key}',
            kind=WorkbenchKind.RECIPE,
            title=recipe.application_name,
            description=recipe.purpose,
            route=f'/recipes/{key}',
            category='semiconductor recipe',
            aliases=tuple(dict.fromkeys((key.replace('-', ' '), *_RECIPE_INTENT_ALIASES.get(key, ()), *surface_aliases))),
            use_when=tuple(recipe.use_when),
            avoid_when=tuple(recipe.avoid_when),
            tags=tuple(recipe.tags),
            source_authority='SEMICONDUCTOR_RECIPE_REGISTRY',
            live_preview=True,
            sample_data=True,
            related_keys=tuple(f'analytics:{surface_key}' for surface_key in surface_keys),
            metadata={
                'recipe_key': key,
                'surfaces': surface_keys,
                'panel_count': len(recipe.panels),
                'interaction_count': len(recipe.interactions),
                'populations': tuple(recipe.populations),
                'variants': variants,
            },
        ))
    return tuple(entries)


def component_entries() -> tuple[WorkbenchEntry, ...]:
    try:
        from nicegui_base.components.registry import COMPONENT_REGISTRY
    except ImportError:
        return ()
    result = []
    for key, item in COMPONENT_REGISTRY.items():
        result.append(WorkbenchEntry(
            key=f'component:{key}', kind=WorkbenchKind.COMPONENT, title=item.public_name,
            description=item.purpose, route=f'/studio/{quote(f"component:{key}", safe="")}', category=item.category,
            aliases=(key.replace('_', ' '),), use_when=tuple(item.preferred_for), tags=('component', item.category),
            source_authority='COMPONENT_REGISTRY', live_preview=True,
            metadata={'component_key': key, 'reference_route': '/controls'},
        ))
    return tuple(result)


_PATTERN_ALIASES = {
    'dashboard': ('kpi app', 'overview app'),
    'data_explorer': ('data explorer', 'editable table', 'table analysis'),
    'master_detail': ('master detail', 'record inspector'),
    'crud': ('editable table', 'record editor', 'create edit records'),
    'monitoring': ('new monitoring app', 'monitoring app', 'alerts health'),
    'search': ('search app', 'faceted search'),
    'settings': ('settings app', 'configuration app'),
    'wizard': ('guided flow', 'step workflow'),
    'comparison': ('compare app', 'affected control'),
    'analysis_workspace': ('investigation', 'analysis workspace', 'engineering investigation'),
}


def pattern_entries() -> tuple[WorkbenchEntry, ...]:
    try:
        from nicegui_base.patterns.registry import PATTERN_REGISTRY
    except ImportError:
        return ()
    route_map = {
        'dashboard': '/patterns/dashboard', 'data_explorer': '/patterns/explorer',
        'master_detail': '/patterns/master-detail', 'crud': '/patterns/crud',
        'monitoring': '/patterns/monitoring', 'search': '/patterns/search',
        'settings': '/patterns/settings', 'wizard': '/patterns/wizard',
        'comparison': '/patterns/comparison', 'analysis_workspace': '/patterns/analysis',
    }
    result = []
    for pattern, definition in PATTERN_REGISTRY.items():
        key = getattr(pattern, 'value', str(pattern))
        result.append(WorkbenchEntry(
            key=f'pattern:{key}', kind=WorkbenchKind.PATTERN, title=_humanize(key),
            description=definition.purpose, route=f'/studio/{quote(f"pattern:{key}", safe="")}', category='application pattern',
            aliases=tuple(dict.fromkeys((key.replace('_', ' '), *_PATTERN_ALIASES.get(key, ())))),
            tags=('pattern', 'starter'), source_authority='PATTERN_REGISTRY', live_preview=True, sample_data=True,
            metadata={'pattern_key': key, 'reference_route': route_map.get(key, '/catalog')},
        ))
    return tuple(result)



_CONSTRUCTION_FAMILIES = {
    'page_pattern': 'generic application patterns',
    'layout': 'shell/layout',
    'component': 'controls',
    'content': 'content/workflow',
    'form_filter_overlay': 'forms/overlays',
    'table': 'tables',
    'data_source': 'data/data sources',
    'visualization': 'generic visualizations',
    'visual_asset': 'visual assets',
    'state_async': 'state/failure utilities',
    'jobs': 'content/workflow',
    'engineering': 'engineering components',
    'semiconductor': 'semiconductor analytics',
    'performance': 'performance/quality utilities',
    'security_runtime': 'state/failure utilities',
}


def construction_entries() -> tuple[WorkbenchEntry, ...]:
    """Expose the canonical construction vocabulary as Workbench reference entries.

    The AI construction registry already owns the framework-level answer to "what kind
    of capability should I use?"  Surfacing it here closes catalog families (layout,
    forms/overlays, state/runtime, performance) that are otherwise easy to hide behind
    low-level registry names.  Workbench only presents that authority; it does not copy
    or reinterpret the underlying API contracts.
    """
    try:
        from nicegui_base.ai.registry import AI_CONSTRUCTION_REGISTRY
    except ImportError:
        return ()
    entries: list[WorkbenchEntry] = []
    for key, definition in AI_CONSTRUCTION_REGISTRY.items():
        family = _CONSTRUCTION_FAMILIES.get(str(key), 'framework guidance')
        catalog_item = {
            'key': str(key),
            'type': 'AiConstructionDefinition',
            'purpose': definition.requirement_signal,
            'preferred_api': definition.preferred_api,
            'inspect_first': definition.inspect_first,
            'prohibited_shortcut': definition.prohibited_shortcut,
            'rationale': definition.rationale,
        }
        entries.append(WorkbenchEntry(
            key=f'construction:{key}',
            kind=WorkbenchKind.REFERENCE,
            title=_humanize(str(key)),
            description=definition.requirement_signal,
            route=f'/studio/{quote(f"construction:{key}", safe="")}',
            category=family,
            aliases=(str(key).replace('_', ' '), definition.preferred_api),
            use_when=(definition.requirement_signal,),
            avoid_when=(definition.prohibited_shortcut,),
            tags=('construction guidance', family, definition.inspect_first),
            source_authority='AI_CONSTRUCTION_REGISTRY',
            live_preview=False,
            sample_data=False,
            metadata={
                'registry_name': 'construction',
                'registry_key': str(key),
                'catalog_item': catalog_item,
                'catalog_family': family,
                'reference_route': '/catalog',
            },
        ))
    return tuple(entries)

_FRAMEWORK_DATA_REGISTRIES = {'analysis','data_sources','engineering','tables','visualizations'}


_FRAMEWORK_REFERENCE_ROUTES = {
    'analysis': '/patterns/analysis',
    'components': '/controls',
    'content': '/content',
    'convenience': '/states',
    'data_sources': '/data',
    'engineering': '/engineering',
    'icons': '/foundation',
    'illustrations': '/states',
    'interactions': '/forms',
    'jobs': '/content',
    'page_patterns': '/foundation',
    'performance': '/performance',
    'runtime': '/performance',
    'security': '/states',
    'semiconductor': '/engineering',
    'tables': '/data',
    'visualizations': '/charts',
}


def framework_catalog_entries(*, known_entries: set[tuple[str, str]]) -> tuple[WorkbenchEntry, ...]:
    """Expose the existing packaged framework catalog without turning it into domain truth.

    `nicegui_base.ai.catalog.load_framework_catalog` is an existing generated catalog over
    canonical registries. Workbench uses it only to make registry families which do not yet
    have a richer first-class adapter searchable/openable. Rich adapters above always win.
    """
    try:
        from nicegui_base.ai.catalog import load_framework_catalog
        catalog = load_framework_catalog()
    except (ImportError, FileNotFoundError, ValueError, TypeError):
        return ()
    registries = catalog.get('registries', {})
    if not isinstance(registries, Mapping):
        return ()
    entries: list[WorkbenchEntry] = []
    seen: set[str] = set()
    for registry_name, items in registries.items():
        if not isinstance(items, list):
            continue
        registry = str(registry_name)
        for item in items:
            raw = canonical_catalog_item_key(registry, item)
            if not raw or (registry, raw) in known_entries:
                continue
            stable = f'framework:{registry}:{raw}'
            if stable in seen:
                continue
            seen.add(stable)
            payload = dict(item) if isinstance(item, Mapping) else {'name': raw, 'value': item}
            public_name = str(payload.get('public_name') or payload.get('title') or payload.get('name') or payload.get('application_name') or payload.get('recipe_key') or _humanize(raw))
            purpose = str(payload.get('purpose') or payload.get('description') or payload.get('message') or payload.get('rule') or (payload.get('use_when') if isinstance(payload.get('use_when'), str) else '') or f'Canonical NiceGUI Base {registry.replace("_", " ")} capability.')
            use_raw = payload.get('use_when', payload.get('when_to_use', ()))
            avoid_raw = payload.get('avoid_when', ())
            use_when = (str(use_raw),) if isinstance(use_raw, str) and use_raw.strip() else tuple(str(x) for x in use_raw if str(x).strip()) if isinstance(use_raw, (list, tuple)) else ()
            avoid_when = (str(avoid_raw),) if isinstance(avoid_raw, str) and avoid_raw.strip() else tuple(str(x) for x in avoid_raw if str(x).strip()) if isinstance(avoid_raw, (list, tuple)) else ()
            tags = tuple(dict.fromkeys(str(value) for value in (registry, payload.get('type') or 'framework capability', payload.get('category'), payload.get('kind')) if value))
            maturity = str(payload.get('maturity') or payload.get('status') or '').strip()
            related_raw = payload.get('related') or payload.get('related_keys') or ()
            if isinstance(related_raw, str):
                related = (related_raw,)
            elif isinstance(related_raw, (list, tuple)):
                related = tuple(str(value) for value in related_raw if str(value).strip())
            else:
                related = ()
            entries.append(WorkbenchEntry(
                key=stable,
                kind=WorkbenchKind.REFERENCE,
                title=public_name,
                description=purpose,
                route=f'/studio/{quote(stable, safe="")}',
                category=registry.replace('_', ' '),
                aliases=(raw.replace('_', ' '),),
                use_when=use_when,
                avoid_when=avoid_when,
                tags=tags,
                source_authority=f'framework_catalog:{registry}',
                maturity=maturity,
                live_preview=bool(_FRAMEWORK_REFERENCE_ROUTES.get(registry)),
                sample_data=registry in _FRAMEWORK_DATA_REGISTRIES,
                related_keys=related,
                metadata={'registry_name': registry, 'registry_key': raw, 'catalog_item': payload, 'reference_route': _FRAMEWORK_REFERENCE_ROUTES.get(registry)},
            ))
    return tuple(entries)


def build_registry_entries() -> tuple[WorkbenchEntry, ...]:
    core = component_entries()
    patterns = pattern_entries()
    surfaces = semiconductor_surface_entries()
    recipes = semiconductor_recipe_entries()
    construction = construction_entries()
    # Suppress only the framework-catalog row that is already represented by a richer
    # first-class adapter. Raw keys are not globally unique across registry families.
    known_entries = {
        *(('components', str(entry.metadata.get('component_key'))) for entry in core),
        *(('page_patterns', str(entry.metadata.get('pattern_key'))) for entry in patterns),
        *(('semiconductor', str(entry.metadata.get('surface_key'))) for entry in surfaces),
        *(('semiconductor_recipes', str(entry.metadata.get('recipe_key'))) for entry in recipes),
    }
    entries = (*core, *patterns, *surfaces, *recipes, *construction, *framework_catalog_entries(known_entries=known_entries))
    keys = [entry.key for entry in entries]
    if len(keys) != len(set(keys)):
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        raise ValueError(f'duplicate Workbench stable keys: {duplicates}')
    canonical_ids: list[tuple[str, str]] = []
    for entry in entries:
        if entry.kind is WorkbenchKind.COMPONENT and entry.metadata.get('component_key'):
            canonical_ids.append(('components', str(entry.metadata['component_key'])))
        elif entry.kind is WorkbenchKind.PATTERN and entry.metadata.get('pattern_key'):
            canonical_ids.append(('page_patterns', str(entry.metadata['pattern_key'])))
        elif entry.kind is WorkbenchKind.ANALYTIC and entry.metadata.get('surface_key'):
            canonical_ids.append(('semiconductor', str(entry.metadata['surface_key'])))
        elif entry.kind is WorkbenchKind.RECIPE and entry.metadata.get('recipe_key'):
            canonical_ids.append(('semiconductor_recipes', str(entry.metadata['recipe_key'])))
        elif entry.kind is WorkbenchKind.REFERENCE:
            registry = str(entry.metadata.get('registry_name') or '')
            raw = str(entry.metadata.get('registry_key') or '')
            if registry and raw and registry != 'construction':
                canonical_ids.append((registry, raw))
    duplicate_ids = sorted({key for key in canonical_ids if canonical_ids.count(key) > 1})
    if duplicate_ids:
        raise ValueError(f'duplicate Workbench canonical catalog identities: {duplicate_ids}')
    return tuple(entries)
