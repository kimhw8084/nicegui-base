from __future__ import annotations

import sys
import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_default_visualization_theme_is_side_effect_free_and_tracks_explicit_theme(monkeypatch):
    visualization = importlib.import_module('nicegui_base.integrations.nicegui_visualization')
    from nicegui_base.visualization import ChartKind, ChartPanelSpec, SeriesSpec

    sys.path.insert(0, str(ROOT / 'tools'))
    import execute_visualization_examples as support

    monkeypatch.setattr(visualization, '_CURRENT_THEME_MODE', 'light')
    with support._fake_nicegui():
        nicegui = sys.modules['nicegui']

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
