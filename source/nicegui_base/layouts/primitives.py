from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any

from .models import Align, ContentWidth, Gap, GridPreset, StackDirection


def _ui():
    try:
        from nicegui import ui
    except ImportError as exc:  # pragma: no cover - exercised only without optional runtime
        raise RuntimeError('NiceGUI is required to render nicegui_base layout primitives.') from exc
    return ui


class _ElementContext(AbstractContextManager):
    def __init__(self, element: Any) -> None:
        self.element = element

    def __enter__(self):
        self.element.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self.element.__exit__(exc_type, exc, tb)


class Page(_ElementContext):
    def __init__(self, width: ContentWidth = ContentWidth.WIDE):
        element = _ui().column().classes(f'cui-page cui-page--{width.value}')
        super().__init__(element)
        self.width = width


class Section(_ElementContext):
    def __init__(self):
        super().__init__(_ui().column().classes('cui-section'))


class Stack(_ElementContext):
    def __init__(self, direction: StackDirection = StackDirection.VERTICAL, gap: Gap = Gap.MD, align: Align = Align.STRETCH):
        element = _ui().element('div').classes(f'cui-stack cui-stack--{direction.value} cui-gap--{gap.value} cui-align--{align.value}')
        super().__init__(element)


class Grid(_ElementContext):
    def __init__(self, preset: GridPreset = GridPreset.AUTO):
        super().__init__(_ui().element('div').classes(f'cui-grid cui-grid--{preset.value}'))
        self.preset = preset


class ScrollablePanel(_ElementContext):
    def __init__(self):
        super().__init__(_ui().element('div').classes('cui-scrollable'))


class StickyPanel(_ElementContext):
    def __init__(self):
        super().__init__(_ui().element('div').classes('cui-sticky'))


class FullScreenWorkspace(_ElementContext):
    def __init__(self):
        super().__init__(_ui().element('div').classes('cui-workspace'))


class SplitPane(AbstractContextManager):
    """Semantic wrapper around NiceGUI's splitter.

    Use ``with SplitPane() as split:`` then ``with split.primary:`` and
    ``with split.secondary:``. The exact underlying NiceGUI splitter API is
    intentionally hidden from application code.
    """

    def __init__(self, primary_percent: int = 68):
        if not 15 <= primary_percent <= 85:
            raise ValueError('primary_percent must be between 15 and 85.')
        self._splitter = _ui().splitter(value=primary_percent).classes('cui-splitter')
        self.primary = self._splitter.before
        self.secondary = self._splitter.after

    def __enter__(self):
        self._splitter.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._splitter.__exit__(exc_type, exc, tb)

class ResponsiveGrid(Grid):
    """Named responsive grid; breakpoints and collapse rules are framework-owned."""

    def __init__(self, preset: GridPreset = GridPreset.AUTO):
        super().__init__(preset=preset)


class DashboardGrid(Grid):
    def __init__(self):
        super().__init__(preset=GridPreset.METRICS)


class MasterDetailLayout(Grid):
    def __init__(self):
        super().__init__(preset=GridPreset.CONTENT_INSPECTOR)


class ResizablePanel(_ElementContext):
    """A semantic resizable-region container used inside split/workspace patterns."""

    def __init__(self):
        super().__init__(_ui().element('div').classes('cui-resizable-panel'))


class ActionRow(_ElementContext):
    """Right-aligned action composition with framework-owned gap/wrapping."""
    def __init__(self):
        super().__init__(_ui().element('div').classes('cui-action-row'))


class ButtonCluster(_ElementContext):
    """Non-joined button cluster; sibling spacing is guaranteed by the framework."""
    def __init__(self):
        super().__init__(_ui().element('div').classes('cui-button-cluster'))


class ToolbarGroup(_ElementContext):
    def __init__(self):
        super().__init__(_ui().element('div').classes('cui-toolbar-group'))


class FormStack(_ElementContext):
    def __init__(self):
        super().__init__(_ui().element('div').classes('cui-form-stack'))


class AlertStack(_ElementContext):
    def __init__(self):
        super().__init__(_ui().element('div').classes('cui-alert-stack'))


class ContentColumn(_ElementContext):
    def __init__(self):
        super().__init__(_ui().element('div').classes('cui-content-column'))


class SurfaceGrid(_ElementContext):
    def __init__(self):
        super().__init__(_ui().element('div').classes('cui-surface-grid'))
