from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from nicegui_base.layouts.models import ContentWidth, GridPreset, LayoutSlot


class PagePattern(str, Enum):
    DASHBOARD = 'dashboard'
    DATA_EXPLORER = 'data_explorer'
    MASTER_DETAIL = 'master_detail'
    CRUD = 'crud'
    MONITORING = 'monitoring'
    SEARCH = 'search'
    SETTINGS = 'settings'
    WIZARD = 'wizard'
    COMPARISON = 'comparison'
    ANALYSIS_WORKSPACE = 'analysis_workspace'


@dataclass(frozen=True, slots=True)
class PatternDefinition:
    pattern: PagePattern
    purpose: str
    required_slots: tuple[LayoutSlot, ...]
    optional_slots: tuple[LayoutSlot, ...]
    slot_order: tuple[LayoutSlot, ...]
    content_width: ContentWidth
    primary_grid: GridPreset | None
    desktop_behavior: str
    tablet_behavior: str
    phone_behavior: str

    def __post_init__(self) -> None:
        required = set(self.required_slots)
        optional = set(self.optional_slots)
        if required & optional:
            raise ValueError(f'{self.pattern.value}: slots cannot be both required and optional.')
        allowed = required | optional
        if set(self.slot_order) != allowed:
            missing = allowed - set(self.slot_order)
            extra = set(self.slot_order) - allowed
            raise ValueError(f'{self.pattern.value}: slot_order mismatch; missing={missing}, extra={extra}')


_DEFINITIONS = {
    PagePattern.DASHBOARD: PatternDefinition(
        PagePattern.DASHBOARD,
        'High-level KPI and trend overview.',
        (LayoutSlot.HEADER, LayoutSlot.METRICS, LayoutSlot.PRIMARY),
        (LayoutSlot.FILTERS, LayoutSlot.SECONDARY, LayoutSlot.DATA, LayoutSlot.ACTIONS),
        (LayoutSlot.HEADER, LayoutSlot.FILTERS, LayoutSlot.METRICS, LayoutSlot.PRIMARY, LayoutSlot.SECONDARY, LayoutSlot.DATA, LayoutSlot.ACTIONS),
        ContentWidth.WIDE, GridPreset.METRICS,
        'Multi-column metrics and visualization grid.',
        'Metrics and charts reduce to two columns.',
        'Single-column reading order; actions remain reachable at top.',
    ),
    PagePattern.DATA_EXPLORER: PatternDefinition(
        PagePattern.DATA_EXPLORER,
        'Interactive filtering, analysis, records and contextual drill-down.',
        (LayoutSlot.HEADER, LayoutSlot.DATA),
        (LayoutSlot.FILTERS, LayoutSlot.METRICS, LayoutSlot.PRIMARY, LayoutSlot.SECONDARY, LayoutSlot.DETAILS, LayoutSlot.ACTIONS),
        (LayoutSlot.HEADER, LayoutSlot.FILTERS, LayoutSlot.METRICS, LayoutSlot.PRIMARY, LayoutSlot.SECONDARY, LayoutSlot.DATA, LayoutSlot.DETAILS, LayoutSlot.ACTIONS),
        ContentWidth.WIDE, GridPreset.METRICS,
        'Filters inline; analytics above full-width table; detail drawer overlays contextually.',
        'Filters may wrap/collapse; metrics two columns; table full-width.',
        'Filters become drawer; metrics single/paired; detail becomes full-screen drawer.',
    ),
    PagePattern.MASTER_DETAIL: PatternDefinition(
        PagePattern.MASTER_DETAIL,
        'Browse entities while preserving selected-entity context.',
        (LayoutSlot.HEADER, LayoutSlot.DATA, LayoutSlot.DETAILS),
        (LayoutSlot.FILTERS, LayoutSlot.ACTIONS),
        (LayoutSlot.HEADER, LayoutSlot.FILTERS, LayoutSlot.DATA, LayoutSlot.DETAILS, LayoutSlot.ACTIONS),
        ContentWidth.FULL, GridPreset.CONTENT_INSPECTOR,
        'Master and detail remain simultaneously visible; resizable when valuable.',
        'Detail narrows or stacks based on content criticality.',
        'Master first; detail opens as full-screen contextual surface.',
    ),
    PagePattern.CRUD: PatternDefinition(
        PagePattern.CRUD,
        'Search, create, inspect and edit managed records.',
        (LayoutSlot.HEADER, LayoutSlot.DATA),
        (LayoutSlot.FILTERS, LayoutSlot.DETAILS, LayoutSlot.ACTIONS),
        (LayoutSlot.HEADER, LayoutSlot.FILTERS, LayoutSlot.DATA, LayoutSlot.DETAILS, LayoutSlot.ACTIONS),
        ContentWidth.WIDE, None,
        'Table-centered; create/edit in drawer or dedicated page based on complexity.',
        'Same hierarchy with compact toolbars.',
        'Priority columns; create/edit surfaces become full-screen.',
    ),
    PagePattern.MONITORING: PatternDefinition(
        PagePattern.MONITORING,
        'Operational health, alerts and periodically refreshed data.',
        (LayoutSlot.HEADER, LayoutSlot.METRICS, LayoutSlot.PRIMARY),
        (LayoutSlot.FILTERS, LayoutSlot.SECONDARY, LayoutSlot.DATA, LayoutSlot.DETAILS, LayoutSlot.ACTIONS),
        (LayoutSlot.HEADER, LayoutSlot.FILTERS, LayoutSlot.METRICS, LayoutSlot.PRIMARY, LayoutSlot.SECONDARY, LayoutSlot.DATA, LayoutSlot.DETAILS, LayoutSlot.ACTIONS),
        ContentWidth.WIDE, GridPreset.METRICS,
        'Status/alerts lead, followed by KPIs, trends and affected records.',
        'Priority health signals stay above the fold.',
        'Critical status and actions precede compact trends and records.',
    ),
    PagePattern.SEARCH: PatternDefinition(
        PagePattern.SEARCH,
        'Search and refine heterogeneous or entity-oriented results.',
        (LayoutSlot.HEADER, LayoutSlot.FILTERS, LayoutSlot.DATA),
        (LayoutSlot.DETAILS, LayoutSlot.ACTIONS),
        (LayoutSlot.HEADER, LayoutSlot.FILTERS, LayoutSlot.DATA, LayoutSlot.DETAILS, LayoutSlot.ACTIONS),
        ContentWidth.STANDARD, GridPreset.SIDEBAR_CONTENT,
        'Facets and results can coexist; preview opens contextually.',
        'Facets reduce in width or collapse.',
        'Facets become filter drawer; result list owns full width.',
    ),
    PagePattern.SETTINGS: PatternDefinition(
        PagePattern.SETTINGS,
        'Structured application/user configuration.',
        (LayoutSlot.HEADER, LayoutSlot.NAVIGATION, LayoutSlot.CONTENT),
        (LayoutSlot.ACTIONS,),
        (LayoutSlot.HEADER, LayoutSlot.NAVIGATION, LayoutSlot.CONTENT, LayoutSlot.ACTIONS),
        ContentWidth.STANDARD, GridPreset.SIDEBAR_CONTENT,
        'Local settings navigation beside constrained form content.',
        'Navigation may remain compact beside content.',
        'Settings navigation becomes top selector/list before form.',
    ),
    PagePattern.WIZARD: PatternDefinition(
        PagePattern.WIZARD,
        'Guided multi-step task with clear progress and bounded decisions.',
        (LayoutSlot.HEADER, LayoutSlot.CONTENT, LayoutSlot.ACTIONS),
        (LayoutSlot.NAVIGATION,),
        (LayoutSlot.HEADER, LayoutSlot.NAVIGATION, LayoutSlot.CONTENT, LayoutSlot.ACTIONS),
        ContentWidth.READING, None,
        'Constrained centered workflow; progress visible.',
        'Same hierarchy with tighter margins.',
        'Full-width step content with sticky safe-area actions if needed.',
    ),
    PagePattern.COMPARISON: PatternDefinition(
        PagePattern.COMPARISON,
        'Compare baseline/current populations, entities or scenarios.',
        (LayoutSlot.HEADER, LayoutSlot.PRIMARY),
        (LayoutSlot.FILTERS, LayoutSlot.METRICS, LayoutSlot.SECONDARY, LayoutSlot.DATA, LayoutSlot.DETAILS),
        (LayoutSlot.HEADER, LayoutSlot.FILTERS, LayoutSlot.METRICS, LayoutSlot.PRIMARY, LayoutSlot.SECONDARY, LayoutSlot.DATA, LayoutSlot.DETAILS),
        ContentWidth.WIDE, GridPreset.HALVES,
        'Side-by-side comparison wherever direct visual alignment adds value.',
        'Two-column comparison remains where readable, otherwise stacks.',
        'Baseline/current stack with explicit delta summary between/above them.',
    ),
    PagePattern.ANALYSIS_WORKSPACE: PatternDefinition(
        PagePattern.ANALYSIS_WORKSPACE,
        'Maximum-density resizable chart/table analysis environment.',
        (LayoutSlot.HEADER, LayoutSlot.PRIMARY),
        (LayoutSlot.FILTERS, LayoutSlot.SECONDARY, LayoutSlot.DATA, LayoutSlot.DETAILS, LayoutSlot.ACTIONS),
        (LayoutSlot.HEADER, LayoutSlot.FILTERS, LayoutSlot.PRIMARY, LayoutSlot.SECONDARY, LayoutSlot.DATA, LayoutSlot.DETAILS, LayoutSlot.ACTIONS),
        ContentWidth.FULL, GridPreset.CONTENT_INSPECTOR,
        'Minimal chrome; resizable panes; optional inspector.',
        'Inspector may collapse; primary workspace dominates.',
        'Single active workspace pane with contextual full-screen detail.',
    ),
}

PATTERN_REGISTRY: Mapping[PagePattern, PatternDefinition] = MappingProxyType(_DEFINITIONS)


def get_pattern(pattern: PagePattern | str) -> PatternDefinition:
    key = pattern if isinstance(pattern, PagePattern) else PagePattern(pattern)
    return PATTERN_REGISTRY[key]
