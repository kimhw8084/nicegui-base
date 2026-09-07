"""Canonical application composition vocabulary.

The page registry remains the source of layout truth.  This module gives
developers and generated applications one small, typed vocabulary for composing
that truth without rebuilding shell, state, filter, metric, or detail anatomy.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

from .registry import PagePattern, get_pattern


COMPOSITION_API_AUTHORITIES: Mapping[str, str] = {
    'shell': 'nicegui_base.integrations.nicegui_layout.AppShell',
    'page_section': 'nicegui_base.patterns.pages.PatternPage.slot',
    'filter_bar': 'nicegui_base.integrations.nicegui_interactions.FilterBar',
    'kpi_strip': 'nicegui_base.integrations.nicegui_content.MetricStrip',
    'chart_table_detail': 'nicegui_base.layouts.Section + registered chart/table',
    'inspector': 'nicegui_base.integrations.nicegui_interactions.InspectorDrawer',
    'state_panel': 'nicegui_base.integrations.nicegui_interactions.StateView',
}


@dataclass(frozen=True, slots=True)
class ApplicationPatternCoverage:
    """A department task mapped to exactly one governed page implementation."""

    key: str
    page_pattern: PagePattern
    purpose: str
    composition_apis: tuple[str, ...]
    recommended_recipe: str | None = None
    responsive_note: str = 'Use the page pattern breakpoint behavior; do not add route-local layout CSS.'

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.purpose.strip():
            raise ValueError('application pattern coverage requires key and purpose')
        if not self.composition_apis or not set(self.composition_apis) <= set(COMPOSITION_API_AUTHORITIES):
            raise ValueError(f'{self.key}: composition API names must resolve to governed authorities')
        get_pattern(self.page_pattern)
        object.__setattr__(self, 'composition_apis', tuple(dict.fromkeys(self.composition_apis)))


_ALL_COMPOSITION_APIS = tuple(COMPOSITION_API_AUTHORITIES)


APPLICATION_PATTERN_COVERAGE = (
    ApplicationPatternCoverage('dashboard', PagePattern.DASHBOARD, 'Summarize KPIs, health and high-value trends.', _ALL_COMPOSITION_APIS, 'spc-monitor'),
    ApplicationPatternCoverage('monitoring', PagePattern.MONITORING, 'Keep operational status, alerts and affected records visible.', _ALL_COMPOSITION_APIS, 'fdc-tool-health'),
    ApplicationPatternCoverage('analysis_workspace', PagePattern.ANALYSIS_WORKSPACE, 'Explore a dense analytical workspace with optional context.', _ALL_COMPOSITION_APIS, 'rca-cockpit'),
    ApplicationPatternCoverage('investigation', PagePattern.ANALYSIS_WORKSPACE, 'Investigate an excursion while preserving evidence and hypotheses.', _ALL_COMPOSITION_APIS, 'excursion-defense-line'),
    ApplicationPatternCoverage('comparison', PagePattern.COMPARISON, 'Compare populations, tools, recipes or scenarios with explicit deltas.', _ALL_COMPOSITION_APIS, 'chamber-matching'),
    ApplicationPatternCoverage('master_detail', PagePattern.MASTER_DETAIL, 'Browse entities while keeping selected detail in context.', _ALL_COMPOSITION_APIS, 'lot-wafer-explorer'),
    ApplicationPatternCoverage('crud', PagePattern.CRUD, 'Manage governed records with local draft and validation behavior.', _ALL_COMPOSITION_APIS),
    ApplicationPatternCoverage('settings', PagePattern.SETTINGS, 'Configure application or user preferences with bounded forms.', _ALL_COMPOSITION_APIS),
    ApplicationPatternCoverage('upload_review', PagePattern.DATA_EXPLORER, 'Upload, validate, map and review tabular data before analysis.', _ALL_COMPOSITION_APIS),
    ApplicationPatternCoverage('report', PagePattern.DASHBOARD, 'Present a bounded evidence-backed operational or engineering report.', _ALL_COMPOSITION_APIS, 'yield-loss'),
    ApplicationPatternCoverage('drill_down', PagePattern.MASTER_DETAIL, 'Move from an aggregate signal to its supporting entity and records.', _ALL_COMPOSITION_APIS, 'lot-wafer-explorer'),
    ApplicationPatternCoverage('full_screen_operations', PagePattern.MONITORING, 'Give operators an uninterrupted status and action workspace.', _ALL_COMPOSITION_APIS, 'fdc-tool-health'),
    ApplicationPatternCoverage('data_explorer', PagePattern.DATA_EXPLORER, 'Filter, inspect and visualize tabular observations.', _ALL_COMPOSITION_APIS),
    ApplicationPatternCoverage('search', PagePattern.SEARCH, 'Find entities across a heterogeneous record population.', _ALL_COMPOSITION_APIS),
    ApplicationPatternCoverage('wizard', PagePattern.WIZARD, 'Guide a bounded setup or review decision step by step.', _ALL_COMPOSITION_APIS),
)

_APPLICATION_PATTERN_BY_KEY = {item.key: item for item in APPLICATION_PATTERN_COVERAGE}


def get_application_pattern(key: str) -> ApplicationPatternCoverage:
    try:
        return _APPLICATION_PATTERN_BY_KEY[str(key).strip().casefold()]
    except KeyError as exc:
        raise KeyError(f'unknown application pattern coverage {key!r}') from exc


@contextmanager
def application_shell(title: str, navigation: Any = None, **kwargs: Any) -> Iterator[Any]:
    """Render the existing Company shell used by the Workbench and exports."""
    from nicegui_base.integrations.nicegui_layout import AppShell

    with AppShell(title, navigation, **kwargs) as shell:
        yield shell


def page_section(page: Any, slot: Any, **kwargs: Any) -> Any:
    """Open a governed PatternPage slot; geometry stays owned by the pattern."""
    return page.slot(slot, **kwargs)


def filter_bar(spec: Any) -> Any:
    from nicegui_base.integrations.nicegui_interactions import FilterBar

    return FilterBar(spec)


def kpi_strip() -> Any:
    from nicegui_base.integrations.nicegui_content import MetricStrip

    return MetricStrip()


@contextmanager
def chart_table_detail(title: str, description: str | None = None) -> Iterator[Any]:
    """Bound a chart/table/detail group to the existing semantic Section primitive."""
    from nicegui import ui
    from nicegui_base.layouts import Section

    with Section() as section:
        ui.label(title).classes('cui-section-title')
        if description:
            ui.label(description).classes('cui-section-description')
        yield section


def inspector(title: str, **kwargs: Any) -> Any:
    from nicegui_base.integrations.nicegui_interactions import InspectorDrawer

    return InspectorDrawer(title, **kwargs)


def state_panel(spec: Any, **kwargs: Any) -> Any:
    from nicegui_base.integrations.nicegui_interactions import StateView

    return StateView(spec, **kwargs)


__all__ = [
    'COMPOSITION_API_AUTHORITIES', 'APPLICATION_PATTERN_COVERAGE',
    'ApplicationPatternCoverage', 'get_application_pattern', 'application_shell',
    'page_section', 'filter_bar', 'kpi_strip', 'chart_table_detail', 'inspector',
    'state_panel',
]
