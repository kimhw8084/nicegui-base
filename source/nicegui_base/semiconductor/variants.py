from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .recipes import RecipeFilterDefinition, RecipePanelDefinition, SemiconductorRecipeDefinition, get_semiconductor_recipe


@dataclass(frozen=True, slots=True)
class PanelLayoutOverride:
    columns: int | None = None
    rows: int | None = None

    def __post_init__(self) -> None:
        if self.columns is not None and self.columns < 1:
            raise ValueError('panel override columns must be >= 1')
        if self.rows is not None and self.rows < 1:
            raise ValueError('panel override rows must be >= 1')


@dataclass(frozen=True, slots=True)
class RecipeVariantDefinition:
    key: str
    recipe_key: str
    label: str
    description: str
    hidden_panels: tuple[str, ...] = ()
    panel_order: tuple[str, ...] = ()
    panel_layout: Mapping[str, PanelLayoutOverride] = field(default_factory=dict)
    pinned_filters: tuple[str, ...] = ()
    field_overrides: Mapping[str, str] = field(default_factory=dict)
    initial_filters: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip() or not self.description.strip():
            raise ValueError('recipe variant key, label and description must not be empty')
        recipe = get_semiconductor_recipe(self.recipe_key)
        panel_ids = {item.panel_id for item in recipe.panels}
        filter_keys = {item.key for item in recipe.filters}
        requirement_keys = {item.key for item in recipe.field_requirements}
        unknown_panels = (set(self.hidden_panels) | set(self.panel_order) | set(self.panel_layout)) - panel_ids
        if unknown_panels:
            raise KeyError(f'variant references unknown recipe panels: {sorted(unknown_panels)!r}')
        if len(self.panel_order) != len(set(self.panel_order)):
            raise ValueError('variant panel_order contains duplicates')
        unknown_filters = set(self.pinned_filters) - filter_keys
        if unknown_filters:
            raise KeyError(f'variant references unknown recipe filters: {sorted(unknown_filters)!r}')
        unknown_fields = set(self.field_overrides) - requirement_keys
        unknown_initial = set(self.initial_filters) - filter_keys
        if unknown_initial:
            raise KeyError(f'variant references unknown initial filters: {sorted(unknown_initial)!r}')
        if unknown_fields:
            raise KeyError(f'variant references unknown logical fields: {sorted(unknown_fields)!r}')
        object.__setattr__(self, 'recipe_key', recipe.key)
        object.__setattr__(self, 'hidden_panels', tuple(dict.fromkeys(self.hidden_panels)))
        object.__setattr__(self, 'panel_order', tuple(self.panel_order))
        object.__setattr__(self, 'panel_layout', MappingProxyType(dict(self.panel_layout)))
        object.__setattr__(self, 'pinned_filters', tuple(dict.fromkeys(self.pinned_filters)))
        object.__setattr__(self, 'field_overrides', MappingProxyType(dict(self.field_overrides)))
        object.__setattr__(self, 'initial_filters', MappingProxyType(dict(self.initial_filters)))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class RecipeCustomization:
    hidden_panels: tuple[str, ...] = ()
    panel_order: tuple[str, ...] = ()
    panel_layout: Mapping[str, PanelLayoutOverride] = field(default_factory=dict)
    pinned_filters: tuple[str, ...] = ()
    field_overrides: Mapping[str, str] = field(default_factory=dict)
    initial_filters: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'hidden_panels', tuple(dict.fromkeys(self.hidden_panels)))
        object.__setattr__(self, 'panel_order', tuple(self.panel_order))
        object.__setattr__(self, 'panel_layout', MappingProxyType(dict(self.panel_layout)))
        object.__setattr__(self, 'pinned_filters', tuple(dict.fromkeys(self.pinned_filters)))
        object.__setattr__(self, 'field_overrides', MappingProxyType(dict(self.field_overrides)))
        object.__setattr__(self, 'initial_filters', MappingProxyType(dict(self.initial_filters)))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class ResolvedRecipeConfiguration:
    recipe: SemiconductorRecipeDefinition
    variant_key: str | None
    field_overrides: Mapping[str, str]
    initial_filters: Mapping[str, Any]
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'field_overrides', MappingProxyType(dict(self.field_overrides)))
        object.__setattr__(self, 'initial_filters', MappingProxyType(dict(self.initial_filters)))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))


# One governed focused mode per complete application. These are intentionally layout/
# visibility presets over the canonical recipe rather than forks of its analytical logic.
_VARIANTS = (
    RecipeVariantDefinition('spc-monitor-fast-response','spc-monitor','Fast response','Prioritize drift, capability and records during active process monitoring.',hidden_panels=('wafer',),panel_order=('control','capability','records'),pinned_filters=('product','operation','tool','chamber')),
    RecipeVariantDefinition('excursion-containment','excursion-defense-line','Containment','Prioritize affected/control, wafer delta, commonality and records during containment.',panel_order=('population','wafer_delta','commonality','records'),pinned_filters=('product','operation','tool','chamber','lot')),
    RecipeVariantDefinition('fdc-chamber-triage','fdc-tool-health','Chamber triage','Prioritize traces, golden envelope, chamber fingerprint and equipment events.',panel_order=('trace','envelope','fingerprint','events'),pinned_filters=('area','recipe','tool','chamber')),
    RecipeVariantDefinition('lot-wafer-spatial','lot-wafer-explorer','Spatial review','Prioritize wafer strip, continuous/bin maps, defects and records.',panel_order=('lot_strip','wafer_map','wafer_bins','defects','records'),pinned_filters=('product','operation','lot','wafer')),
    RecipeVariantDefinition('yield-loss-triage','yield-loss','Yield triage','Prioritize Pareto, decomposition, wafer bins and loss records.',panel_order=('yield_pareto','bin_pareto','waterfall','wafer_bins','records'),pinned_filters=('product','operation','tool','chamber','lot')),
    RecipeVariantDefinition('pm-recovery','pm-effect-analysis','Recovery verification','Prioritize pre/post comparison, chamber comparison, SPC and records after PM.',panel_order=('population','chambers','spc','capability','records'),pinned_filters=('operation','recipe','tool','chamber')),
    RecipeVariantDefinition('chamber-match-core','chamber-matching','Matching core','Prioritize fingerprint, distributions, PCA and spatial corroboration.',panel_order=('fingerprint','distribution','pca','loadings','wafer'),pinned_filters=('operation','recipe','tool','chamber')),
    RecipeVariantDefinition('rca-evidence-first','rca-cockpit','Evidence first','Prioritize affected/control, commonality, evidence, genealogy and records.',panel_order=('population','commonality','evidence','genealogy','records'),pinned_filters=('product','operation','tool','chamber','lot')),
)

SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY: Mapping[str, RecipeVariantDefinition] = MappingProxyType({item.key: item for item in _VARIANTS})


def get_semiconductor_recipe_variant(key: str) -> RecipeVariantDefinition:
    normalized = str(key).strip().casefold().replace('_', '-')
    try:
        return SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY[normalized]
    except KeyError as exc:
        raise KeyError(f'unknown semiconductor recipe variant {key!r}; available: {", ".join(SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY)}') from exc


def variants_for_recipe(recipe: str | SemiconductorRecipeDefinition) -> tuple[RecipeVariantDefinition, ...]:
    definition = get_semiconductor_recipe(recipe) if isinstance(recipe, str) else recipe
    return tuple(item for item in _VARIANTS if item.recipe_key == definition.key)


def _validate_customization(recipe: SemiconductorRecipeDefinition, customization: RecipeCustomization) -> None:
    panel_ids = {item.panel_id for item in recipe.panels}
    filters = {item.key for item in recipe.filters}
    requirements = {item.key for item in recipe.field_requirements}
    unknown_panels = (set(customization.hidden_panels) | set(customization.panel_order) | set(customization.panel_layout)) - panel_ids
    if unknown_panels:
        raise KeyError(f'customization references unknown recipe panels: {sorted(unknown_panels)!r}')
    if len(customization.panel_order) != len(set(customization.panel_order)):
        raise ValueError('customization panel_order contains duplicates')
    if set(customization.pinned_filters) - filters:
        raise KeyError('customization references unknown recipe filters')
    if set(customization.field_overrides) - requirements:
        raise KeyError('customization references unknown logical fields')
    if set(customization.initial_filters) - filters:
        raise KeyError('customization references unknown initial manufacturing filters')


def resolve_recipe_configuration(
    recipe: str | SemiconductorRecipeDefinition,
    *,
    variant: str | RecipeVariantDefinition | None = None,
    customization: RecipeCustomization | None = None,
) -> ResolvedRecipeConfiguration:
    base = get_semiconductor_recipe(recipe) if isinstance(recipe, str) else recipe
    chosen = None
    if variant is not None:
        chosen = get_semiconductor_recipe_variant(variant) if isinstance(variant, str) else variant
        if chosen.recipe_key != base.key:
            raise ValueError(f'variant {chosen.key!r} belongs to {chosen.recipe_key!r}, not {base.key!r}')
    custom = customization or RecipeCustomization()
    _validate_customization(base, custom)

    hidden = set(chosen.hidden_panels if chosen else ()) | set(custom.hidden_panels)
    layout: dict[str, PanelLayoutOverride] = dict(chosen.panel_layout if chosen else {})
    layout.update(custom.panel_layout)
    order: list[str] = []
    for source in ((chosen.panel_order if chosen else ()), custom.panel_order):
        for panel_id in source:
            if panel_id not in order:
                order.append(panel_id)
    for panel in base.panels:
        if panel.panel_id not in order:
            order.append(panel.panel_id)

    panels: list[RecipePanelDefinition] = []
    by_id = {item.panel_id: item for item in base.panels}
    for panel_id in order:
        if panel_id in hidden:
            continue
        panel = by_id[panel_id]
        override = layout.get(panel_id)
        if override:
            panel = replace(
                panel,
                preferred_columns=override.columns or panel.preferred_columns,
                preferred_rows=override.rows or panel.preferred_rows,
            )
        panels.append(panel)
    visible = {item.panel_id for item in panels}
    interactions = tuple(
        replace(item, target_panels=tuple(target for target in item.target_panels if target in visible))
        for item in base.interactions
        if item.source_panel in visible and any(target in visible for target in item.target_panels)
    )
    pinned = set(chosen.pinned_filters if chosen else ()) | set(custom.pinned_filters)
    filters = tuple(replace(item, pinned=True) if item.key in pinned else item for item in base.filters)
    field_overrides = dict(chosen.field_overrides if chosen else {})
    field_overrides.update(custom.field_overrides)
    initial_filters = dict(chosen.initial_filters if chosen else {})
    initial_filters.update(custom.initial_filters)
    metadata = dict(chosen.metadata if chosen else {})
    metadata.update(custom.metadata)
    metadata['variant_key'] = chosen.key if chosen else None

    resolved = replace(base, panels=tuple(panels), filters=filters, interactions=interactions)
    return ResolvedRecipeConfiguration(resolved, chosen.key if chosen else None, field_overrides, initial_filters, metadata)


def recipe_variant_catalog_entries() -> tuple[dict[str, Any], ...]:
    return tuple({
        'key': item.key, 'recipe_key': item.recipe_key, 'label': item.label, 'description': item.description,
        'hidden_panels': item.hidden_panels, 'panel_order': item.panel_order, 'pinned_filters': item.pinned_filters,
    } for item in _VARIANTS)


__all__ = [
    'PanelLayoutOverride','RecipeCustomization','RecipeVariantDefinition','ResolvedRecipeConfiguration',
    'SEMICONDUCTOR_RECIPE_VARIANT_REGISTRY','get_semiconductor_recipe_variant','recipe_variant_catalog_entries',
    'resolve_recipe_configuration','variants_for_recipe',
]
