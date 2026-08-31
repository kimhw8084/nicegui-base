from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from nicegui_base.analysis import AnalysisContext, AnalysisCoordinator, SelectionBus, SelectionKind
from nicegui_base.data_sources import DataSchema, DataSource, FieldRole
from nicegui_base.workspace import PanelSpec, WorkspaceBreakpoint, WorkspaceController, WorkspaceLayoutEngine

from .context import ManufacturingFilterController, SemiconductorAnalysisContext, SemiconductorFieldMap
from .surfaces import SEMICONDUCTOR_SURFACE_REGISTRY, SemiconductorAnalyticalSurface


class RecipePanelKind(str, Enum):
    ANALYTICAL = 'analytical'
    RECORDS = 'records'
    DETAIL = 'detail'
    EVIDENCE = 'evidence'
    SUMMARY = 'summary'


@dataclass(frozen=True, slots=True)
class RecipeFieldRequirement:
    key: str
    candidates: tuple[str, ...]
    roles: tuple[FieldRole, ...] = ()
    required: bool = True
    description: str = ''

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError('recipe field requirement key must not be empty')
        if not self.candidates and not self.roles:
            raise ValueError(f'recipe field requirement {self.key!r} needs candidates or semantic roles')
        object.__setattr__(self, 'candidates', tuple(dict.fromkeys(item.strip() for item in self.candidates if item.strip())))
        object.__setattr__(self, 'roles', tuple(dict.fromkeys(self.roles)))


@dataclass(frozen=True, slots=True)
class RecipeFilterDefinition:
    key: str
    label: str
    required: bool = False
    pinned: bool = False

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError('recipe filter key and label must not be empty')
        # SemiconductorFieldMap is the governed vocabulary for manufacturing filters.
        SemiconductorFieldMap().field(self.key)


@dataclass(frozen=True, slots=True)
class RecipePanelDefinition:
    panel_id: str
    title: str
    kind: RecipePanelKind
    surface_key: str | None = None
    preferred_columns: int = 6
    preferred_rows: int = 4
    required: bool = True
    description: str = ''
    field_requirements: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.panel_id.strip() or not self.title.strip():
            raise ValueError('recipe panel id and title must not be empty')
        if self.kind is RecipePanelKind.ANALYTICAL:
            if self.surface_key is None:
                raise ValueError(f'analytical panel {self.panel_id!r} requires a surface_key')
            if self.surface_key not in SEMICONDUCTOR_SURFACE_REGISTRY:
                raise KeyError(f'unknown semiconductor surface: {self.surface_key}')
        elif self.surface_key is not None:
            raise ValueError('non-analytical recipe panels must not declare a surface_key')
        if self.preferred_columns < 1 or self.preferred_rows < 1:
            raise ValueError('recipe panel spans must be >= 1')
        object.__setattr__(self, 'field_requirements', tuple(dict.fromkeys(self.field_requirements)))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    def workspace_spec(self) -> PanelSpec:
        metadata = dict(self.metadata)
        metadata.update({'title': self.title, 'recipe_panel_kind': self.kind.value})
        if self.surface_key:
            metadata['surface_key'] = self.surface_key
        if self.description:
            metadata['description'] = self.description
        return PanelSpec(
            self.panel_id,
            preferred_columns=self.preferred_columns,
            preferred_rows=self.preferred_rows,
            min_columns=min(2, self.preferred_columns),
            min_rows=min(2, self.preferred_rows),
            phone_full_width=True,
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class RecipeInteractionDefinition:
    source_panel: str
    target_panels: tuple[str, ...]
    selection_kinds: tuple[SelectionKind, ...]
    crossfilter: bool = True
    linked_hover: bool = False
    description: str = ''

    def __post_init__(self) -> None:
        if not self.source_panel.strip() or not self.target_panels:
            raise ValueError('recipe interaction requires one source and at least one target panel')
        if not self.selection_kinds:
            raise ValueError('recipe interaction requires selection kinds')
        object.__setattr__(self, 'target_panels', tuple(dict.fromkeys(self.target_panels)))
        object.__setattr__(self, 'selection_kinds', tuple(dict.fromkeys(self.selection_kinds)))


@dataclass(frozen=True, slots=True)
class SemiconductorRecipeDefinition:
    key: str
    application_name: str
    purpose: str
    use_when: tuple[str, ...]
    avoid_when: tuple[str, ...]
    entities: tuple[str, ...]
    field_requirements: tuple[RecipeFieldRequirement, ...]
    filters: tuple[RecipeFilterDefinition, ...]
    panels: tuple[RecipePanelDefinition, ...]
    interactions: tuple[RecipeInteractionDefinition, ...]
    populations: tuple[str, ...] = ()
    record_views: tuple[str, ...] = ('records',)
    tags: tuple[str, ...] = ()
    base_template: str = 'analysis-workspace'

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.application_name.strip() or not self.purpose.strip():
            raise ValueError('recipe key, name and purpose must not be empty')
        if not self.panels:
            raise ValueError(f'recipe {self.key!r} requires panels')
        panel_ids = tuple(panel.panel_id for panel in self.panels)
        if len(panel_ids) != len(set(panel_ids)):
            raise ValueError(f'recipe {self.key!r} contains duplicate panel ids')
        requirements = {item.key for item in self.field_requirements}
        for panel in self.panels:
            unknown = set(panel.field_requirements) - requirements
            if unknown:
                raise ValueError(f'panel {panel.panel_id!r} references unknown field requirements: {sorted(unknown)!r}')
        for interaction in self.interactions:
            unknown = {interaction.source_panel, *interaction.target_panels} - set(panel_ids)
            if unknown:
                raise ValueError(f'interaction references unknown panels: {sorted(unknown)!r}')
        if not set(self.populations) <= {'affected', 'control', 'baseline'}:
            raise ValueError('recipe populations must be affected, control and/or baseline')
        object.__setattr__(self, 'use_when', tuple(self.use_when))
        object.__setattr__(self, 'avoid_when', tuple(self.avoid_when))
        object.__setattr__(self, 'entities', tuple(dict.fromkeys(self.entities)))
        object.__setattr__(self, 'field_requirements', tuple(self.field_requirements))
        object.__setattr__(self, 'filters', tuple(self.filters))
        object.__setattr__(self, 'panels', tuple(self.panels))
        object.__setattr__(self, 'interactions', tuple(self.interactions))
        object.__setattr__(self, 'populations', tuple(dict.fromkeys(self.populations)))
        object.__setattr__(self, 'record_views', tuple(dict.fromkeys(self.record_views)))
        object.__setattr__(self, 'tags', tuple(dict.fromkeys(self.tags)))

    @property
    def surface_keys(self) -> tuple[str, ...]:
        return tuple(panel.surface_key for panel in self.panels if panel.surface_key is not None)

    @property
    def analytical_panels(self) -> tuple[RecipePanelDefinition, ...]:
        return tuple(panel for panel in self.panels if panel.kind is RecipePanelKind.ANALYTICAL)


@dataclass(frozen=True, slots=True)
class RecipeSourceCompatibility:
    recipe_key: str
    bindings: Mapping[str, str]
    missing_required: tuple[str, ...]
    missing_optional: tuple[str, ...]
    available_filters: tuple[str, ...]
    unavailable_filters: tuple[str, ...]
    available_panels: tuple[str, ...]
    unavailable_panels: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'bindings', MappingProxyType(dict(self.bindings)))

    @property
    def compatible(self) -> bool:
        return not self.missing_required


class RecipeCompatibilityError(ValueError):
    def __init__(self, compatibility: RecipeSourceCompatibility) -> None:
        self.compatibility = compatibility
        missing = ', '.join(compatibility.missing_required) or 'unknown'
        super().__init__(f"source is incompatible with recipe {compatibility.recipe_key!r}; missing required logical fields: {missing}")


@dataclass(slots=True)
class SemiconductorApplicationAssembly:
    recipe: SemiconductorRecipeDefinition
    source: DataSource
    schema: DataSchema
    compatibility: RecipeSourceCompatibility
    context: AnalysisContext
    selections: SelectionBus
    coordinator: AnalysisCoordinator
    semiconductor: SemiconductorAnalysisContext
    manufacturing_filters: ManufacturingFilterController
    workspace: WorkspaceController
    surfaces: Mapping[str, SemiconductorAnalyticalSurface]
    owns_context: bool = True
    owns_selections: bool = True
    _closed: bool = False

    @property
    def bindings(self) -> Mapping[str, str]:
        return self.compatibility.bindings

    @property
    def panels(self) -> tuple[RecipePanelDefinition, ...]:
        available = set(self.compatibility.available_panels)
        return tuple(panel for panel in self.recipe.panels if panel.panel_id in available)

    async def aclose(self, *, close_source: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        for surface in self.surfaces.values():
            surface.close()
        self.semiconductor.close()
        self.coordinator.close()
        self.workspace.close()
        if self.owns_selections:
            self.selections.close()
        if self.owns_context:
            self.context.close()
        if close_source and not self.source.closed:
            await self.source.aclose()


# Short constructors keep the registry readable while preserving typed contracts.
def _f(key: str, label: str, *, required: bool = False, pinned: bool = False) -> RecipeFilterDefinition:
    return RecipeFilterDefinition(key, label, required=required, pinned=pinned)


def _r(key: str, *candidates: str, roles: Sequence[FieldRole] = (), required: bool = True, description: str = '') -> RecipeFieldRequirement:
    return RecipeFieldRequirement(key, tuple(candidates), tuple(roles), required, description)


def _a(panel_id: str, title: str, surface: str, cols: int = 6, rows: int = 4, *, fields: Sequence[str] = (), required: bool = True, description: str = '') -> RecipePanelDefinition:
    return RecipePanelDefinition(panel_id, title, RecipePanelKind.ANALYTICAL, surface, cols, rows, required, description, tuple(fields))


def _p(panel_id: str, title: str, kind: RecipePanelKind, cols: int = 12, rows: int = 4, *, fields: Sequence[str] = (), required: bool = True, description: str = '') -> RecipePanelDefinition:
    return RecipePanelDefinition(panel_id, title, kind, None, cols, rows, required, description, tuple(fields))


def _i(source: str, targets: Sequence[str], kinds: Sequence[SelectionKind], *, hover: bool = False, description: str = '') -> RecipeInteractionDefinition:
    return RecipeInteractionDefinition(source, tuple(targets), tuple(kinds), True, hover, description)


_COMMON_FILTERS = (
    _f('fab', 'Fab'), _f('area', 'Area'), _f('product', 'Product'), _f('route', 'Route'),
    _f('operation', 'Operation'), _f('recipe', 'Recipe'), _f('recipe_version', 'Recipe version'),
    _f('tool', 'Tool'), _f('chamber', 'Chamber'), _f('lot', 'Lot'), _f('wafer', 'Wafer'),
)


def _filters(*keys: str) -> tuple[RecipeFilterDefinition, ...]:
    lookup = {item.key: item for item in _COMMON_FILTERS}
    return tuple(lookup[key] for key in keys)


_RECIPES = (
    SemiconductorRecipeDefinition(
        'spc-monitor', 'SPCMonitor', 'Monitor process stability, capability and violations with drill-down to manufacturing context.',
        ('monitor a process parameter', 'detect process drift or control-rule violations', 'review capability against specification limits'),
        ('when the process has no defensible baseline or chart family/subgroup definition',),
        ('SPCParameter','Measurement','Product','Operation','Tool','Chamber','Lot','Wafer'),
        (_r('measurement','value','measurement','metric','cd',roles=(FieldRole.MEASUREMENT,)), _r('time','timestamp','event_time','measured_at','time',roles=(FieldRole.TIMESTAMP,),required=False), _r('wafer','wafer','wafer_id',roles=(FieldRole.ENTITY,FieldRole.DIMENSION),required=False), _r('x','x','die_x','wafer_x',required=False), _r('y','y','die_y','wafer_y',required=False), _r('row_id','id','measurement_id',roles=(FieldRole.IDENTIFIER,),required=False)),
        _filters('fab','area','product','route','operation','recipe','tool','chamber','lot','wafer'),
        (
            _a('control','Control chart','spc_i_mr',8,5,fields=('measurement',)),
            _a('capability','Capability','capability_histogram',4,5,fields=('measurement',)),
            _a('distribution','Distribution','ecdf',6,4,fields=('measurement',)),
            _a('wafer','Wafer signature','wafer_continuous',6,4,fields=('measurement','wafer','x','y'),required=False),
            _p('records','Measurement records',RecipePanelKind.RECORDS,12,5,fields=('measurement',)),
        ),
        (
            _i('control',('capability','distribution','wafer','records'),(SelectionKind.CHART_POINT,SelectionKind.TIME_RANGE),hover=True),
            _i('wafer',('control','records'),(SelectionKind.WAFER,SelectionKind.DIE,SelectionKind.SPATIAL),hover=True),
            _i('records',('control','capability','wafer'),(SelectionKind.ROW,)),
        ),
        populations=('baseline',), tags=('spc','capability','drift','monitoring'),
    ),
    SemiconductorRecipeDefinition(
        'excursion-defense-line', 'ExcursionDefenseLine', 'Triage an excursion with affected/control populations, spatial localization, commonality and genealogy evidence.',
        ('build an excursion defense line', 'triage affected versus control material', 'localize and rank likely common factors'),
        ('when affected/control population definitions are not yet governed or comparable',),
        ('Excursion','Investigation','Evidence','Lot','Wafer','Tool','Chamber','Recipe','Operation'),
        (_r('metric','value','measurement','metric','cd','yield_pct',roles=(FieldRole.MEASUREMENT,)), _r('wafer','wafer','wafer_id',roles=(FieldRole.ENTITY,FieldRole.DIMENSION),required=False), _r('x','x','die_x','wafer_x',required=False), _r('y','y','die_y','wafer_y',required=False), _r('row_id','id','measurement_id',roles=(FieldRole.IDENTIFIER,),required=False)),
        _filters('fab','area','product','route','operation','recipe','tool','chamber','lot','wafer'),
        (
            _a('population','Affected vs control','rca_affected_control',6,4,fields=('metric',)),
            _a('wafer_delta','Spatial delta','wafer_delta',6,5,fields=('metric','wafer','x','y'),required=False),
            _a('commonality','Commonality ranking','rca_commonality_ranking',6,5),
            _a('matrix','Commonality matrix','rca_commonality_matrix',6,5),
            _a('genealogy','Genealogy','rca_genealogy_graph',8,5),
            _a('evidence','Evidence matrix','rca_evidence_matrix',4,5),
            _p('records','Excursion records',RecipePanelKind.RECORDS,12,5,fields=('metric',)),
        ),
        (
            _i('population',('wafer_delta','commonality','matrix','records'),(SelectionKind.POPULATION,SelectionKind.CHART_POINT),hover=True),
            _i('commonality',('matrix','genealogy','records'),(SelectionKind.ENTITY,SelectionKind.CHART_POINT)),
            _i('wafer_delta',('population','records','genealogy'),(SelectionKind.WAFER,SelectionKind.SPATIAL),hover=True),
        ),
        populations=('affected','control','baseline'), record_views=('records','investigation','evidence'), tags=('excursion','defense-line','rca','commonality'),
    ),
    SemiconductorRecipeDefinition(
        'fdc-tool-health', 'FdcToolHealth', 'Diagnose equipment health from aligned sensor traces, envelopes, events and multivariate fingerprints.',
        ('analyze FDC traces', 'check tool or chamber health', 'investigate multivariate sensor drift'),
        ('when recipe-step alignment or sensor/event semantics are unavailable',),
        ('Tool','Chamber','Sensor','FDCTrace','FDCFeature','Alarm','EquipmentEvent','RecipeVersion'),
        (_r('trace_time','time','timestamp','sample_time',roles=(FieldRole.TIMESTAMP,)), _r('sensor_value','value','sensor_value','reading',roles=(FieldRole.MEASUREMENT,)), _r('sensor','sensor','sensor_id','parameter',roles=(FieldRole.ENTITY,FieldRole.DIMENSION)), _r('row_id','id','trace_id',roles=(FieldRole.IDENTIFIER,),required=False)),
        _filters('fab','area','recipe','recipe_version','tool','chamber','lot','wafer'),
        (
            _a('trace','Recipe-step traces','fdc_recipe_step_trace',8,5,fields=('trace_time','sensor_value','sensor')),
            _a('envelope','Golden envelope','fdc_golden_envelope',4,5,fields=('trace_time','sensor_value','sensor')),
            _a('sensors','Multi-sensor panel','fdc_multi_sensor',8,5,fields=('trace_time','sensor_value','sensor')),
            _a('fingerprint','Chamber fingerprint','fdc_chamber_fingerprint',4,5,fields=('sensor_value',)),
            _a('pca','PCA scores','fdc_pca_scores',6,4,fields=('sensor_value',)),
            _a('loadings','PCA loadings','fdc_pca_loadings',6,4,fields=('sensor_value',)),
            _a('events','Equipment events','fdc_equipment_event_overlay',12,3,fields=('trace_time',),required=False),
        ),
        (
            _i('trace',('envelope','sensors','events'),(SelectionKind.TIME_RANGE,SelectionKind.CHART_POINT),hover=True),
            _i('pca',('fingerprint','loadings','trace'),(SelectionKind.CHART_POINT,SelectionKind.ENTITY),hover=True),
            _i('fingerprint',('trace','pca'),(SelectionKind.ENTITY,SelectionKind.SERIES)),
        ),
        populations=('baseline',), record_views=('trace_records','events'), tags=('fdc','equipment','tool-health','pca'),
    ),
    SemiconductorRecipeDefinition(
        'lot-wafer-explorer', 'LotWaferExplorer', 'Explore lot-to-wafer-to-die spatial behavior with synchronized maps, defects, profiles and records.',
        ('explore wafers in a lot', 'inspect spatial metrology or defect signatures', 'compare wafer-to-wafer variation'),
        ('when wafer/die coordinates or wafer identity are unavailable',),
        ('Lot','Wafer','Die','Measurement','Inspection','Defect','YieldBin'),
        (_r('wafer','wafer','wafer_id',roles=(FieldRole.ENTITY,FieldRole.DIMENSION)), _r('x','x','die_x','wafer_x'), _r('y','y','die_y','wafer_y'), _r('value','value','measurement','metric','cd',roles=(FieldRole.MEASUREMENT,),required=False), _r('category','category','bin','yield_bin','defect_class',roles=(FieldRole.DIMENSION,),required=False)),
        _filters('fab','area','product','route','operation','tool','chamber','lot','wafer'),
        (
            _a('wafer_map','Wafer map','wafer_continuous',7,6,fields=('wafer','x','y','value'),required=False),
            _a('wafer_bins','Bin / category map','wafer_categorical',5,6,fields=('wafer','x','y','category'),required=False),
            _a('lot_strip','Lot wafer strip','lot_wafer_strip',12,4,fields=('wafer','x','y')),
            _a('radial','Radial profile','wafer_radial',6,4,fields=('wafer','x','y')),
            _a('rings','Ring analysis','wafer_ring',3,4,fields=('wafer','x','y')),
            _a('sectors','Sector analysis','wafer_sector',3,4,fields=('wafer','x','y')),
            _a('defects','Defect clusters','wafer_defect_clusters',6,4,fields=('wafer','x','y','category'),required=False),
            _p('records','Wafer / die records',RecipePanelKind.RECORDS,6,5,fields=('wafer','x','y')),
        ),
        (
            _i('lot_strip',('wafer_map','wafer_bins','radial','rings','sectors','records'),(SelectionKind.WAFER,),hover=True),
            _i('wafer_map',('records','radial','rings','sectors','defects'),(SelectionKind.DIE,SelectionKind.SPATIAL),hover=True),
            _i('records',('wafer_map','wafer_bins'),(SelectionKind.ROW,)),
        ),
        record_views=('records','die_detail','inspection_detail'), tags=('wafer','spatial','lot','defect'),
    ),
    SemiconductorRecipeDefinition(
        'yield-loss', 'YieldLoss', 'Explain yield loss through Pareto/decomposition, bin/spatial signatures and commonality drill-down.',
        ('analyze yield loss', 'rank fail bins or loss contributors', 'explain a yield delta'),
        ('when yield denominators, bin definitions or comparison populations are inconsistent',),
        ('Product','Lot','Wafer','YieldBin','Defect','Operation','Tool','Chamber'),
        (_r('category','bin','yield_bin','category','defect_class',roles=(FieldRole.DIMENSION,)), _r('value','count','loss','value','yield_loss',roles=(FieldRole.MEASUREMENT,)), _r('yield','yield','yield_pct',roles=(FieldRole.MEASUREMENT,),required=False), _r('wafer','wafer','wafer_id',roles=(FieldRole.ENTITY,FieldRole.DIMENSION),required=False), _r('x','x','die_x','wafer_x',required=False), _r('y','y','die_y','wafer_y',required=False)),
        _filters('fab','area','product','route','operation','tool','chamber','lot','wafer'),
        (
            _a('yield_pareto','Yield-loss Pareto','yield_pareto',6,5,fields=('category','value')),
            _a('bin_pareto','Bin Pareto','bin_pareto',6,5,fields=('category','value')),
            _a('waterfall','Yield decomposition','yield_waterfall',7,4,fields=('value',)),
            _a('wafer_bins','Spatial yield bins','wafer_categorical',5,4,fields=('category','wafer','x','y'),required=False),
            _a('commonality','Loss commonality','rca_commonality_ranking',6,5),
            _p('records','Yield-loss records',RecipePanelKind.RECORDS,6,5,fields=('category','value')),
        ),
        (
            _i('yield_pareto',('bin_pareto','waterfall','wafer_bins','commonality','records'),(SelectionKind.CHART_POINT,SelectionKind.ENTITY),hover=True),
            _i('wafer_bins',('commonality','records'),(SelectionKind.WAFER,SelectionKind.DIE,SelectionKind.SPATIAL),hover=True),
        ),
        populations=('affected','control'), record_views=('records','lot_detail'), tags=('yield','pareto','bins','decomposition'),
    ),
    SemiconductorRecipeDefinition(
        'pm-effect-analysis', 'PMEffectAnalysis', 'Compare pre/post-PM populations, chamber behavior, traces and process stability using one shared context.',
        ('measure PM effect', 'compare chamber before and after maintenance', 'validate post-PM recovery'),
        ('when pre/post windows or maintenance-event timing cannot be established',),
        ('PM','Maintenance','Tool','Chamber','EquipmentEvent','Measurement','FDCTrace','SPCParameter'),
        (_r('metric','value','measurement','metric','cd',roles=(FieldRole.MEASUREMENT,)), _r('time','timestamp','event_time','time',roles=(FieldRole.TIMESTAMP,),required=False)),
        _filters('fab','area','product','operation','recipe','tool','chamber','lot'),
        (
            _a('population','Pre vs post PM','rca_affected_control',6,4,fields=('metric',)),
            _a('chambers','Chamber comparison','fdc_tool_chamber_compare',6,4,fields=('metric',)),
            _a('spc','Post-PM stability','spc_i_mr',8,5,fields=('metric',)),
            _a('capability','Capability shift','box_distribution',4,5,fields=('metric',)),
            _a('trace','PM-aligned traces','fdc_equipment_event_overlay',8,5,fields=('metric','time'),required=False),
            _a('fingerprint','Chamber fingerprint','fdc_chamber_fingerprint',4,5,fields=('metric',)),
            _p('records','PM / process records',RecipePanelKind.RECORDS,12,5,fields=('metric',)),
        ),
        (
            _i('population',('chambers','spc','capability','fingerprint','records'),(SelectionKind.POPULATION,SelectionKind.CHART_POINT),hover=True),
            _i('chambers',('trace','spc','records'),(SelectionKind.ENTITY,SelectionKind.SERIES),hover=True),
        ),
        populations=('affected','control','baseline'), record_views=('records','maintenance_detail'), tags=('pm','maintenance','before-after','chamber'),
    ),
    SemiconductorRecipeDefinition(
        'chamber-matching', 'ChamberMatching', 'Compare chamber signatures and distributions to detect mismatch and identify driving variables.',
        ('match chambers', 'compare chambers across a toolset', 'find variables driving chamber separation'),
        ('when chambers do not share comparable process/recipe populations',),
        ('Tool','Chamber','Sensor','FDCFeature','Measurement','RecipeVersion'),
        (_r('feature','value','measurement','metric','sensor_value',roles=(FieldRole.MEASUREMENT,)), _r('chamber','chamber','chamber_id',roles=(FieldRole.ENTITY,FieldRole.DIMENSION)), _r('wafer','wafer','wafer_id',roles=(FieldRole.ENTITY,FieldRole.DIMENSION),required=False), _r('x','x','die_x','wafer_x',required=False), _r('y','y','die_y','wafer_y',required=False)),
        _filters('fab','area','product','operation','recipe','recipe_version','tool','chamber'),
        (
            _a('fingerprint','Chamber fingerprint','fdc_chamber_fingerprint',6,5,fields=('feature','chamber')),
            _a('comparison','Tool / chamber comparison','fdc_tool_chamber_compare',6,5,fields=('feature','chamber')),
            _a('pca','PCA scores','fdc_pca_scores',6,5,fields=('feature','chamber')),
            _a('loadings','PCA loadings','fdc_pca_loadings',6,5,fields=('feature',)),
            _a('distribution','Chamber distributions','ridge_distribution',8,4,fields=('feature','chamber')),
            _a('wafer','Wafer comparison','wafer_comparison',4,4,fields=('feature','wafer','x','y'),required=False),
            _p('records','Matching records',RecipePanelKind.RECORDS,12,5,fields=('feature','chamber')),
        ),
        (
            _i('fingerprint',('comparison','pca','distribution','records'),(SelectionKind.ENTITY,SelectionKind.SERIES),hover=True),
            _i('pca',('loadings','fingerprint','records'),(SelectionKind.CHART_POINT,SelectionKind.ENTITY),hover=True),
        ),
        populations=('control','baseline'), record_views=('records','chamber_detail'), tags=('chamber','matching','fingerprint','pca'),
    ),
    SemiconductorRecipeDefinition(
        'rca-cockpit', 'RcaCockpit', 'Run structured root-cause analysis with populations, commonality, contribution, evidence and genealogy in one cockpit.',
        ('perform RCA', 'investigate root cause or commonality', 'organize hypotheses and evidence around an excursion'),
        ('when the workflow needs causal proof from observational association alone',),
        ('Excursion','Investigation','Hypothesis','Evidence','CorrectiveAction','Lot','Wafer','Tool','Chamber','Recipe','Operation'),
        (_r('metric','value','measurement','metric','yield_pct',roles=(FieldRole.MEASUREMENT,),required=False), _r('row_id','id','record_id',roles=(FieldRole.IDENTIFIER,),required=False)),
        _filters('fab','area','product','route','operation','recipe','tool','chamber','lot','wafer'),
        (
            _a('population','Affected vs control','rca_affected_control',6,4,fields=('metric',),required=False),
            _a('commonality','Commonality ranking','rca_commonality_ranking',6,5),
            _a('matrix','Commonality matrix','rca_commonality_matrix',6,5),
            _a('contribution','Contribution waterfall','rca_contribution_waterfall',6,4),
            _a('evidence','Evidence matrix','rca_evidence_matrix',6,5),
            _a('genealogy','Genealogy / process graph','rca_genealogy_graph',6,5),
            _a('fault_tree','Fault tree','rca_fault_tree',6,5),
            _a('flow','Process flow','rca_sankey',6,5),
            _p('records','Investigation records',RecipePanelKind.RECORDS,12,5),
        ),
        (
            _i('commonality',('matrix','contribution','genealogy','records'),(SelectionKind.ENTITY,SelectionKind.CHART_POINT),hover=True),
            _i('genealogy',('evidence','fault_tree','flow','records'),(SelectionKind.ENTITY,SelectionKind.ROW)),
            _i('population',('commonality','matrix','records'),(SelectionKind.POPULATION,),hover=True),
        ),
        populations=('affected','control','baseline'), record_views=('records','hypotheses','evidence','corrective_actions'), tags=('rca','commonality','evidence','genealogy'),
    ),
)

SEMICONDUCTOR_RECIPE_REGISTRY: Mapping[str, SemiconductorRecipeDefinition] = MappingProxyType({item.key: item for item in _RECIPES})

_RECIPE_ALIASES: Mapping[str, str] = MappingProxyType({
    'spcmonitor': 'spc-monitor', 'spc-monitor': 'spc-monitor',
    'excursiondefenseline': 'excursion-defense-line', 'excursion-defense-line': 'excursion-defense-line',
    'fdctoolhealth': 'fdc-tool-health', 'fdc-tool-health': 'fdc-tool-health',
    'lotwaferexplorer': 'lot-wafer-explorer', 'lot-wafer-explorer': 'lot-wafer-explorer',
    'yieldloss': 'yield-loss', 'yield-loss': 'yield-loss',
    'pmeffectanalysis': 'pm-effect-analysis', 'pm-effect-analysis': 'pm-effect-analysis',
    'chambermatching': 'chamber-matching', 'chamber-matching': 'chamber-matching',
    'rcacockpit': 'rca-cockpit', 'rca-cockpit': 'rca-cockpit',
})


def _normalize_recipe_key(key: str) -> str:
    compact = ''.join(ch for ch in str(key).strip().casefold() if ch.isalnum())
    direct = str(key).strip().casefold().replace('_', '-')
    if direct in SEMICONDUCTOR_RECIPE_REGISTRY:
        return direct
    try:
        return _RECIPE_ALIASES[compact]
    except KeyError as exc:
        raise KeyError(f"unknown semiconductor recipe {key!r}; available: {', '.join(SEMICONDUCTOR_RECIPE_REGISTRY)}") from exc


def get_semiconductor_recipe(key: str) -> SemiconductorRecipeDefinition:
    return SEMICONDUCTOR_RECIPE_REGISTRY[_normalize_recipe_key(key)]


def recommend_semiconductor_recipe(intent: str) -> SemiconductorRecipeDefinition:
    text = intent.strip().casefold()
    if not text:
        raise ValueError('recipe intent must not be empty')
    # High-value workflow phrases resolve before generic token scoring so engineers get
    # the intended complete application rather than a merely related surface family.
    if ('pm' in text or 'maintenance' in text) and any(token in text for token in ('effect','before','after','compare','recovery')):
        return SEMICONDUCTOR_RECIPE_REGISTRY['pm-effect-analysis']
    if any(token in text for token in ('fdc','trace','sensor')) and any(token in text for token in ('health','drift','tool','chamber','alarm')):
        return SEMICONDUCTOR_RECIPE_REGISTRY['fdc-tool-health']
    if 'drift' in text or 'control chart' in text or 'spc' in text or 'capability' in text:
        return SEMICONDUCTOR_RECIPE_REGISTRY['spc-monitor']
    if ('wafer' in text and any(token in text for token in ('change','delta','excursion','affected','control'))) or 'defense line' in text:
        return SEMICONDUCTOR_RECIPE_REGISTRY['excursion-defense-line']
    if 'yield' in text or 'bin pareto' in text:
        return SEMICONDUCTOR_RECIPE_REGISTRY['yield-loss']
    if 'wafer' in text and any(token in text for token in ('lot','explore','map','spatial','defect')):
        return SEMICONDUCTOR_RECIPE_REGISTRY['lot-wafer-explorer']
    if 'chamber' in text and any(token in text for token in ('match','matching','fingerprint','separation')):
        return SEMICONDUCTOR_RECIPE_REGISTRY['chamber-matching']
    if any(token in text for token in ('rca','root cause','commonality','hypothesis','evidence')):
        return SEMICONDUCTOR_RECIPE_REGISTRY['rca-cockpit']
    # Long/explicit phrases are weighted more strongly than generic one-word tags.
    scored: list[tuple[int, int, SemiconductorRecipeDefinition]] = []
    for index, recipe in enumerate(_RECIPES):
        score = 0
        for phrase in (*recipe.use_when, *recipe.tags, recipe.application_name, recipe.key):
            folded = phrase.casefold().replace('-', ' ')
            if folded in text:
                score += 8 if ' ' in folded else 4
            for token in folded.split():
                if len(token) >= 3 and token in text:
                    score += 1
        scored.append((score, -index, recipe))
    score, _, recipe = max(scored, key=lambda item: (item[0], item[1]))
    if score <= 0:
        return SEMICONDUCTOR_RECIPE_REGISTRY['rca-cockpit'] if any(word in text for word in ('investigate','analysis')) else SEMICONDUCTOR_RECIPE_REGISTRY['spc-monitor']
    return recipe


def resolve_recipe_source(
    recipe: str | SemiconductorRecipeDefinition,
    schema: DataSchema,
    *,
    field_overrides: Mapping[str, str] | None = None,
    field_map: SemiconductorFieldMap | None = None,
    semantic_role_fallback: bool = True,
    resolve_unoverridden: bool = True,
) -> RecipeSourceCompatibility:
    definition = get_semiconductor_recipe(recipe) if isinstance(recipe, str) else recipe
    overrides = dict(field_overrides or {})
    available = set(schema.names)
    bindings: dict[str, str] = {}
    missing_required: list[str] = []
    missing_optional: list[str] = []
    used: set[str] = set()
    for requirement in definition.field_requirements:
        chosen = overrides.get(requirement.key)
        if chosen is not None:
            if chosen not in available:
                raise KeyError(f'field override {requirement.key!r} references unknown source field {chosen!r}')
        else:
            chosen = None
            if resolve_unoverridden:
                chosen = next((candidate for candidate in requirement.candidates if candidate in available), None)
                if chosen is None and requirement.roles and semantic_role_fallback:
                    chosen = next((field.name for field in schema.fields if field.name not in used and field.role in requirement.roles), None)
        if chosen is None:
            (missing_required if requirement.required else missing_optional).append(requirement.key)
        else:
            bindings[requirement.key] = chosen
            used.add(chosen)

    fmap = field_map or SemiconductorFieldMap()
    available_filters: list[str] = []
    unavailable_filters: list[str] = []
    for item in definition.filters:
        target = fmap.field(item.key)
        (available_filters if target in available else unavailable_filters).append(item.key)
        if item.required and target not in available:
            missing_required.append(f'filter:{item.key}')

    available_panels: list[str] = []
    unavailable_panels: list[str] = []
    missing = set(missing_required) | set(missing_optional)
    for panel in definition.panels:
        if any(key in missing for key in panel.field_requirements):
            unavailable_panels.append(panel.panel_id)
            if panel.required:
                for key in panel.field_requirements:
                    if key not in bindings and key not in missing_required:
                        missing_required.append(key)
        else:
            available_panels.append(panel.panel_id)

    return RecipeSourceCompatibility(
        definition.key, bindings, tuple(dict.fromkeys(missing_required)), tuple(dict.fromkeys(missing_optional)),
        tuple(available_filters), tuple(unavailable_filters), tuple(available_panels), tuple(unavailable_panels),
    )


async def assemble_semiconductor_application(
    recipe: str | SemiconductorRecipeDefinition,
    source: DataSource,
    *,
    context: AnalysisContext | None = None,
    selections: SelectionBus | None = None,
    field_overrides: Mapping[str, str] | None = None,
    field_map: SemiconductorFieldMap | None = None,
    strict: bool = True,
) -> SemiconductorApplicationAssembly:
    definition = get_semiconductor_recipe(recipe) if isinstance(recipe, str) else recipe
    schema = await source.schema()
    compatibility = resolve_recipe_source(definition, schema, field_overrides=field_overrides, field_map=field_map)
    if strict and not compatibility.compatible:
        raise RecipeCompatibilityError(compatibility)

    owns_context = context is None
    owns_selections = selections is None
    ctx = context or AnalysisContext(source_key=source.key)
    bus = selections or SelectionBus()
    coordinator = AnalysisCoordinator(ctx, bus)
    semiconductor = SemiconductorAnalysisContext(ctx, fields=field_map)
    filters = ManufacturingFilterController(source, semiconductor)
    layout = WorkspaceLayoutEngine()
    workspace = WorkspaceController(layout)
    available_panels = set(compatibility.available_panels)
    surfaces: dict[str, SemiconductorAnalyticalSurface] = {}

    for panel in definition.panels:
        if panel.panel_id not in available_panels:
            continue
        workspace.register_panel(panel.workspace_spec())
        if panel.surface_key is not None:
            surfaces[panel.panel_id] = SemiconductorAnalyticalSurface(panel.surface_key, ctx, bus)
    # Registration creates deterministic geometry at every breakpoint already; deriving
    # explicitly from desktop keeps recipe intent stable if layout defaults evolve later.
    for breakpoint in (WorkspaceBreakpoint.TABLET, WorkspaceBreakpoint.PHONE):
        layout.derive_breakpoint(breakpoint, source=WorkspaceBreakpoint.DESKTOP)

    ctx.set_metadata({
        **ctx.metadata,
        'semiconductor_recipe': {
            'key': definition.key,
            'application_name': definition.application_name,
            'bindings': dict(compatibility.bindings),
            'available_panels': compatibility.available_panels,
            'unavailable_panels': compatibility.unavailable_panels,
        },
    })
    return SemiconductorApplicationAssembly(
        definition, source, schema, compatibility, ctx, bus, coordinator, semiconductor, filters,
        workspace, MappingProxyType(surfaces), owns_context=owns_context, owns_selections=owns_selections,
    )


def recipe_catalog_entries() -> tuple[dict[str, Any], ...]:
    """Machine-readable recipe catalog for agents/docs without runtime objects."""
    from .variants import variants_for_recipe
    return tuple({
        'key': recipe.key,
        'application_name': recipe.application_name,
        'purpose': recipe.purpose,
        'use_when': recipe.use_when,
        'avoid_when': recipe.avoid_when,
        'entities': recipe.entities,
        'filters': tuple(item.key for item in recipe.filters),
        'populations': recipe.populations,
        'surfaces': recipe.surface_keys,
        'record_views': recipe.record_views,
        'panel_count': len(recipe.panels),
        'interaction_count': len(recipe.interactions),
        'base_template': recipe.base_template,
        'tags': recipe.tags,
        'variants': tuple(item.key for item in variants_for_recipe(recipe)),
        'production_onboarding': 'SemiconductorRecipeRuntime.onboarding_view()',
        'guided_setup': 'SemiconductorRecipeRuntime.prepare_setup_workflow()',
        'provider_sdk': 'SemiconductorProviderAdapterBase + provider-check CLI',
        'adapter_conformance': 'run_semiconductor_adapter_conformance()',
        'runtime_performance': 'SemiconductorRecipeRuntime.performance_report()',
        'provider_benchmark': 'SemiconductorRecipeRuntime.benchmark(profile="provider-rc")',
        'configuration_review': 'SemiconductorRecipeRuntime.configuration_review()',
        'runtime_presets': 'SemiconductorRecipeRuntime.capture_preset()/restore_preset()',
        'target_certification': 'build_semiconductor_target_runtime_certification()',
        'target_evidence': 'build_semiconductor_target_evidence_bundle()',
    } for recipe in _RECIPES)


__all__ = [
    'RecipeCompatibilityError','RecipeFieldRequirement','RecipeFilterDefinition','RecipeInteractionDefinition',
    'RecipePanelDefinition','RecipePanelKind','RecipeSourceCompatibility','SEMICONDUCTOR_RECIPE_REGISTRY',
    'SemiconductorApplicationAssembly','SemiconductorRecipeDefinition','assemble_semiconductor_application',
    'get_semiconductor_recipe','recipe_catalog_entries','recommend_semiconductor_recipe','resolve_recipe_source',
]
