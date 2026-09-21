from __future__ import annotations

import sys
import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_default_visualization_theme_is_side_effect_free_and_tracks_explicit_theme():
    visualization = importlib.import_module('nicegui_base.integrations.nicegui_visualization')
    from nicegui_base.visualization import ChartKind, ChartPanelSpec, SeriesSpec

    sys.path.insert(0, str(ROOT / 'tools'))
    import execute_visualization_examples as support

    with support._fake_nicegui():
        nicegui = sys.modules['nicegui']
        client = type('FakeClient', (), {'storage': {}, 'on_delete': lambda self, callback: None})()
        nicegui.ui.context.client = client

        dark_mode_calls = []

        def forbidden_dark_mode(*_args, **_kwargs):
            dark_mode_calls.append(True)
            raise AssertionError('visualization theme resolution must not create ui.dark_mode()')

        nicegui.ui.dark_mode = forbidden_dark_mode
        visualization.apply_all_chart_themes('dark')
        panel = visualization.ChartPanel(
            (SeriesSpec('trace', 'Trace', (1, 2), kind=ChartKind.LINE),),
            spec=ChartPanelSpec('Trace', kind=ChartKind.LINE),
        )
        assert panel.theme_mode == 'dark'
        assert visualization._resolve_theme_mode(None) == 'dark'

        visualization.apply_all_chart_themes('light')
        assert panel.theme_mode == 'light'
        next_panel = visualization.ChartPanel(
            (SeriesSpec('trace', 'Trace', (1, 2), kind=ChartKind.LINE),),
            spec=ChartPanelSpec('Trace', kind=ChartKind.LINE),
        )
        assert next_panel.theme_mode == 'light'
        assert dark_mode_calls == []
        panel.dispose()
        next_panel.dispose()


def test_chart_theme_state_and_renderers_are_isolated_per_client():
    visualization = importlib.import_module('nicegui_base.integrations.nicegui_visualization')
    from nicegui_base.visualization import ChartKind, ChartPanelSpec, SeriesSpec

    sys.path.insert(0, str(ROOT / 'tools'))
    import execute_visualization_examples as support

    def panel():
        return visualization.ChartPanel(
            (SeriesSpec('trace', 'Trace', (1, 2), kind=ChartKind.LINE),),
            spec=ChartPanelSpec('Trace', kind=ChartKind.LINE),
        )

    with support._fake_nicegui():
        nicegui = sys.modules['nicegui']
        FakeClient = type('FakeClient', (), {'__init__': lambda self: setattr(self, 'storage', {}), 'on_delete': lambda self, callback: None})
        client_a = FakeClient()
        client_b = FakeClient()

        nicegui.ui.context.client = client_a
        visualization.apply_all_chart_themes('dark')
        panel_a = panel()
        assert panel_a.theme_mode == 'dark'

        nicegui.ui.context.client = client_b
        visualization.apply_all_chart_themes('light')
        panel_b = panel()
        assert panel_b.theme_mode == 'light'
        assert panel_a.theme_mode == 'dark'

        visualization.apply_all_chart_themes('dark')
        assert panel_a.theme_mode == 'dark'
        assert panel_b.theme_mode == 'dark'

        nicegui.ui.context.client = client_a
        visualization.apply_all_chart_themes('light')
        assert panel_a.theme_mode == 'light'
        assert panel_b.theme_mode == 'dark'

        nicegui.ui.context.client = client_b
        visualization.apply_all_chart_themes('light')
        nicegui.ui.context.client = client_a
        next_panel_a = panel()
        assert next_panel_a.theme_mode == 'light'
        assert client_a.storage[visualization._CLIENT_THEME_STORAGE_KEY] == 'light'
        assert client_b.storage[visualization._CLIENT_THEME_STORAGE_KEY] == 'light'

        nicegui.ui.context.client = client_b
        panel_b.dispose()
        nicegui.ui.context.client = client_a
        panel_a.dispose()
        next_panel_a.dispose()
