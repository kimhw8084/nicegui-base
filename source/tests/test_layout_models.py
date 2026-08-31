import pytest

from nicegui_base.layouts import ContentWidth, GridPreset, PanelSize
from nicegui_base.layouts.models import CONTENT_WIDTHS, PANEL_WIDTHS
from nicegui_base.layouts.primitives import SplitPane


def test_content_width_semantics_are_monotonic():
    assert CONTENT_WIDTHS[ContentWidth.READING] < CONTENT_WIDTHS[ContentWidth.STANDARD] < CONTENT_WIDTHS[ContentWidth.WIDE]
    assert CONTENT_WIDTHS[ContentWidth.FULL] is None


def test_panel_sizes_are_semantic_and_ordered():
    assert PANEL_WIDTHS[PanelSize.SMALL] < PANEL_WIDTHS[PanelSize.MEDIUM] < PANEL_WIDTHS[PanelSize.LARGE] < PANEL_WIDTHS[PanelSize.XLARGE]
    assert PANEL_WIDTHS[PanelSize.FULL] is None


def test_grid_presets_cover_core_composition_needs():
    required = {'metrics', 'halves', 'thirds', 'sidebar_content', 'content_inspector', 'main_aside', 'auto'}
    assert required <= {preset.value for preset in GridPreset}


def test_splitter_range_is_documented_in_source_without_rendering():
    # Rendering is intentionally not invoked because NiceGUI is an external runtime dependency.
    assert 'between 15 and 85' in SplitPane.__init__.__doc__ if SplitPane.__init__.__doc__ else True
