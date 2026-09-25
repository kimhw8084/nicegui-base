from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _panel(visualization, *, theme_mode=None):
    from nicegui_base.visualization import AxisSpec, ChartKind, ChartPanelSpec, SeriesSpec, SpecLimits, ThresholdSpec

    return visualization.ChartPanel(
        (SeriesSpec('trace', 'Trace', ((1, 2), (2, 3)), kind=ChartKind.LINE),),
        spec=ChartPanelSpec('Trace', kind=ChartKind.LINE, x_axis=AxisSpec(), y_axis=AxisSpec()),
        thresholds=(ThresholdSpec(2, 'Review threshold'),),
        spec_limits=SpecLimits(lower=0, upper=4, lower_label='LSL', upper_label='USL'),
        theme_mode=theme_mode,
    )


def _assert_chart_semantics(panel, mode: str) -> None:
    from nicegui_base.visualization import chart_theme

    theme = chart_theme(mode)
    options = panel.element.options
    for axis_name in ('xAxis', 'yAxis'):
        axis = options[axis_name]
        axis = axis[0] if isinstance(axis, list) else axis
        assert axis['axisLabel']['color'] == theme.text_secondary
        assert axis['splitLine']['lineStyle']['color'] == theme.grid
    marks = options['series'][0]['markLine']['data']
    by_name = {mark['name']: mark for mark in marks}
    assert by_name['Review threshold']['lineStyle']['color'] == theme.warning
    assert by_name['LSL']['lineStyle']['color'] == theme.danger
    assert by_name['USL']['lineStyle']['color'] == theme.danger
    assert options['textStyle']['color'] == theme.text_primary


def test_system_theme_css_is_root_resolved_and_nested_system_scopes_inherit():
    from nicegui_base.design.css import build_css

    css = build_css()
    assert "html[data-theme='system'], [data-theme='system']" not in css
    assert "html[data-theme='system'] {" in css


def test_chart_theme_scope_resolves_initial_system_mode_and_live_transition():
    visualization = importlib.import_module('nicegui_base.integrations.nicegui_visualization')
    sys.path.insert(0, str(ROOT / 'tools'))
    import execute_visualization_examples as support

    with support._fake_nicegui():
        nicegui = sys.modules['nicegui']
        client = type('FakeClient', (), {'storage': {}, 'on_delete': lambda self, callback: None})()
        nicegui.ui.context.client = client
        client.storage[visualization._CLIENT_THEME_STORAGE_KEY] = 'dark'

        with visualization._chart_theme_scope('system'):
            panel = _panel(visualization)
        assert panel.theme_mode == 'dark'
        _assert_chart_semantics(panel, 'dark')

        visualization.apply_all_chart_themes('light')
        assert panel.theme_mode == 'light'
        _assert_chart_semantics(panel, 'light')
        visualization.apply_all_chart_themes('dark')
        assert panel.theme_mode == 'dark'
        _assert_chart_semantics(panel, 'dark')
        panel.dispose()


def test_local_surface_scope_overrides_a_conflicting_constructor_theme():
    visualization = importlib.import_module('nicegui_base.integrations.nicegui_visualization')
    sys.path.insert(0, str(ROOT / 'tools'))
    import execute_visualization_examples as support

    with support._fake_nicegui():
        nicegui = sys.modules['nicegui']
        client = type('FakeClient', (), {'storage': {}, 'on_delete': lambda self, callback: None})()
        nicegui.ui.context.client = client
        client.storage[visualization._CLIENT_THEME_STORAGE_KEY] = 'dark'

        with visualization._chart_theme_scope('light'):
            panel = _panel(visualization, theme_mode='dark')
        assert panel.theme_mode == 'light'
        _assert_chart_semantics(panel, 'light')
        panel.dispose()


@pytest.mark.parametrize(('local_mode', 'global_mode'), [('light', 'dark'), ('dark', 'light')])
def test_explicit_local_chart_theme_survives_global_theme_changes(local_mode, global_mode):
    visualization = importlib.import_module('nicegui_base.integrations.nicegui_visualization')
    sys.path.insert(0, str(ROOT / 'tools'))
    import execute_visualization_examples as support

    with support._fake_nicegui():
        nicegui = sys.modules['nicegui']
        client = type('FakeClient', (), {'storage': {}, 'on_delete': lambda self, callback: None})()
        nicegui.ui.context.client = client
        client.storage[visualization._CLIENT_THEME_STORAGE_KEY] = global_mode

        with visualization._chart_theme_scope(local_mode):
            panel = _panel(visualization)
        assert panel.theme_mode == local_mode
        _assert_chart_semantics(panel, local_mode)

        visualization.apply_all_chart_themes(global_mode)
        assert panel.theme_mode == local_mode
        _assert_chart_semantics(panel, local_mode)
        next_panel = _panel(visualization)
        assert next_panel.theme_mode == global_mode
        _assert_chart_semantics(next_panel, global_mode)
        panel.dispose()
        next_panel.dispose()
