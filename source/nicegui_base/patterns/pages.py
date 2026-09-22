from __future__ import annotations

from contextlib import AbstractContextManager
from enum import Enum
from typing import Any

from nicegui_base.integrations.nicegui_layout import BackNavigation, PageHeader
from nicegui_base.integrations.nicegui_master_detail import set_master_detail_context_state
from nicegui_base.layouts import LayoutSlot, Page
from nicegui_base.navigation import Breadcrumb
from .registry import PagePattern, get_pattern


class PatternSurface(str, Enum):
    PLAIN = 'plain'
    SUBTLE = 'subtle'
    SURFACE = 'surface'
    INSPECTOR = 'inspector'


def _ui():
    try:
        from nicegui import ui
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('NiceGUI is required to render page patterns.') from exc
    return ui


class PatternPage(AbstractContextManager):
    PATTERN: PagePattern

    def __init__(self, title: str, description: str | None = None, *, breadcrumbs: tuple[Breadcrumb, ...] = ()) -> None:
        self.title = title
        self.description = description
        self.breadcrumbs = breadcrumbs
        self.definition = get_pattern(self.PATTERN)
        self._page: Page | None = None
        self._slots_rendered: set[LayoutSlot] = set()
        self._master_detail_context_element: Any | None = None
        self._master_detail_detail_requested = False

    @property
    def allowed_slots(self) -> frozenset[LayoutSlot]:
        return frozenset(self.definition.required_slots + self.definition.optional_slots)

    def __enter__(self):
        self._page = Page(self.definition.content_width)
        self._page.element.classes(add=f'cui-pattern cui-pattern--{self.PATTERN.value}')
        grid = self.definition.primary_grid.value if self.definition.primary_grid is not None else 'none'
        self._page.element.props(
            f'data-cui-pattern="{self.PATTERN.value}" data-cui-pattern-width="{self.definition.content_width.value}" '
            f'data-cui-pattern-grid="{grid}"'
        )
        self._page.__enter__()
        PageHeader(self.title, self.description, breadcrumbs=self.breadcrumbs)
        return self

    def slot(self, slot: LayoutSlot | str, *, surface: PatternSurface | str | None = None,
             sticky: bool = False, aria_label: str | None = None):
        key = slot if isinstance(slot, LayoutSlot) else LayoutSlot(slot)
        if key not in self.allowed_slots:
            raise ValueError(f'{key.value!r} is not an allowed slot for {self.PATTERN.value}.')
        if key in self._slots_rendered:
            raise ValueError(f'{key.value!r} slot already rendered for {self.PATTERN.value}.')
        self._slots_rendered.add(key)
        default_surface = {
            LayoutSlot.FILTERS: PatternSurface.SUBTLE,
            LayoutSlot.NAVIGATION: PatternSurface.SUBTLE,
            LayoutSlot.DETAILS: PatternSurface.SURFACE,
        }.get(key, PatternSurface.PLAIN)
        tone = surface if isinstance(surface, PatternSurface) else PatternSurface(surface) if surface else default_surface
        classes = f'cui-pattern-slot cui-pattern-slot--{key.value} cui-pattern-slot--{tone.value}' + (' is-sticky' if sticky else '')
        label = aria_label or {
            LayoutSlot.FILTERS: 'Filters', LayoutSlot.METRICS: 'Metrics', LayoutSlot.PRIMARY: 'Primary analysis',
            LayoutSlot.SECONDARY: 'Secondary analysis', LayoutSlot.DATA: 'Data', LayoutSlot.DETAILS: 'Details',
            LayoutSlot.ACTIONS: 'Actions', LayoutSlot.CONTENT: 'Content', LayoutSlot.NAVIGATION: 'Section navigation',
        }.get(key)
        props = f'data-cui-slot="{key.value}" data-cui-slot-surface="{tone.value}"'
        if label: props += f' aria-label="{label}"'
        element = _ui().element('section').classes(classes + (' cui-master-detail-context' if self.PATTERN is PagePattern.MASTER_DETAIL and key is LayoutSlot.DETAILS else ''))
        if self.PATTERN is PagePattern.MASTER_DETAIL and key is LayoutSlot.DETAILS:
            context_state = 'open' if self._master_detail_detail_requested else 'closed'
            context_label = aria_label or 'Selected details'
            props += (
                f' role="region" data-cui-master-detail-context '
                f'data-cui-context-state="{context_state}" '
                f'data-cui-overlay="master-detail-context" '
                f'data-cui-overlay-id="cui-master-detail-context-{element.id}" '
                'data-cui-dismissible="true" tabindex="-1"'
            )
            props += f' aria-label="{context_label}"' if not label else ''
            element.props(props)
            self._master_detail_context_element = element
            ui = _ui()
            with element:
                with ui.element('div').classes('cui-master-detail-context__header'):
                    back = BackNavigation('Back to master list', on_click=self.close_detail)
                    back.element.classes(add='cui-master-detail-context__back')
                    back.element.props('data-cui-overlay-close data-cui-master-detail-close aria-label="Back to master list"')
                body = ui.element('div').classes('cui-master-detail-context__body')
            return body
        element.props(props)
        return element

    def __exit__(self, exc_type, exc, tb):
        assert self._page is not None
        return self._page.__exit__(exc_type, exc, tb)


class DashboardPage(PatternPage): PATTERN = PagePattern.DASHBOARD
class DataExplorerPage(PatternPage): PATTERN = PagePattern.DATA_EXPLORER
class MasterDetailPage(PatternPage):
    PATTERN = PagePattern.MASTER_DETAIL

    def open_detail(self) -> None:
        """Open the selected detail as the phone contextual surface.

        Desktop and tablet keep the governed master/detail composition. On a
        phone this promotes the existing details slot without changing table
        selection, filters, query state, or the rendered detail content.
        """
        self._master_detail_detail_requested = True
        if self._master_detail_context_element is not None:
            set_master_detail_context_state(_ui(), int(self._master_detail_context_element.id), 'open', force=True)

    def close_detail(self) -> None:
        """Close the phone contextual detail and preserve the master context."""
        self._master_detail_detail_requested = False
        if self._master_detail_context_element is not None:
            set_master_detail_context_state(_ui(), int(self._master_detail_context_element.id), 'closed')


class CrudPage(PatternPage): PATTERN = PagePattern.CRUD
class MonitoringPage(PatternPage): PATTERN = PagePattern.MONITORING
class SearchPage(PatternPage): PATTERN = PagePattern.SEARCH
class SettingsPage(PatternPage): PATTERN = PagePattern.SETTINGS
class WizardPage(PatternPage): PATTERN = PagePattern.WIZARD
class ComparisonPage(PatternPage): PATTERN = PagePattern.COMPARISON
class AnalysisWorkspacePage(PatternPage): PATTERN = PagePattern.ANALYSIS_WORKSPACE
