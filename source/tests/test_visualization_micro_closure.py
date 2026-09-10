"""Behavioral regressions for the final visualization semantic corrections."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from nicegui_base.visualization import AxisSpec, AxisType, ChartKind, ChartPanelSpec, ScaleMode, SeriesSpec, build_echarts_options
from nicegui_base.visualization.formatting import format_visual_number


ROOT = Path(__file__).resolve().parents[2]


def test_visual_number_formatter_bounds_binary_float_noise_and_keeps_units_separate():
    assert format_visual_number(3.3000000000000003) == '3.3'
    assert format_visual_number(-3.2000000000000006) == '-3.2'
    assert format_visual_number(42.287749160134375) == '42.29'
    assert format_visual_number(0.0) == '0'


def test_chart_data_view_formats_xy_values_without_mapping_repr():
    sys.path.insert(0, str(ROOT / 'tools'))
    import execute_visualization_examples as support
    from nicegui_base import ChartPanel, ChartPanelSpec

    with support._fake_nicegui():
        panel = ChartPanel(
            (SeriesSpec('trace', 'Trace', ({'time': 1, 'value': 0.30000000000000004},), kind=ChartKind.LINE, x_key='time', y_key='value'),),
            spec=ChartPanelSpec('Trace', x_axis=AxisSpec(kind=AxisType.VALUE), y_axis=AxisSpec(kind=AxisType.VALUE)),
        )
        rows = panel.data_view.rows()
        csv_text = panel.export.csv_text()
        panel.dispose()
    assert rows[0]['value'] == 0.30000000000000004
    assert '0.3' in csv_text and "{'time'" not in csv_text


def test_waterfall_uses_signed_start_end_geometry_and_reconciles_net():
    from nicegui_base.integrations.nicegui_visualization import _WaterfallDiagram

    options = _WaterfallDiagram.build_options(('Gain', 'Loss', 'Recovery'), (3.3, -3.2, .6))
    bars = {item['name']: item for series in options['series'] for item in series['data']}
    assert bars['Gain']['value'][1:3] == [0.0, pytest.approx(3.3)]
    assert bars['Loss']['value'][1:3] == [pytest.approx(3.3), pytest.approx(.1)]
    assert bars['Loss']['value'][3] < 0
    assert bars['Loss']['deltaLabel'] == '-3.2'
    assert bars['Net']['value'][1:3] == [0.0, pytest.approx(.7)]
    assert options['yAxis']['min'] < 0 < options['yAxis']['max']
    assert all(series['type'] == 'custom' for series in options['series'])

    negative = _WaterfallDiagram.build_options(('Loss', 'Net'), (-1.8, -3.2))
    negative_bars = {item['name']: item for series in negative['series'] for item in series['data']}
    assert negative_bars['Net']['value'][1:3] == [0.0, pytest.approx(-5.0)]
    assert negative['yAxis']['max'] > 0


def test_qq_axis_uses_observed_data_extent_not_an_irrelevant_zero_baseline():
    from nicegui_base.integrations.nicegui_visualization import _QQProbabilityPlot

    options = _QQProbabilityPlot.build_options('Q-Q', ((-1.0, 39.5), (0.0, 40.0), (1.0, 40.5)))
    y_axis = options['yAxis']
    assert y_axis['min'] == pytest.approx(39.4)
    assert y_axis['max'] == pytest.approx(40.6)
    assert options['series'][0]['type'] == 'scatter'
    assert options['series'][1]['type'] == 'line'
    assert all(39.4 <= point[1] <= 40.6 for point in options['series'][1]['data'])


def test_correlation_heatmap_has_symmetric_diverging_scale_and_missing_values_are_not_zero():
    spec = ChartPanelSpec(
        'Correlation', kind=ChartKind.HEATMAP, scale_mode=ScaleMode.DIVERGING,
        color_min=-1.0, color_max=1.0,
        x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=('CD', 'Pressure', 'RF')),
        y_axis=AxisSpec(kind=AxisType.CATEGORY, categories=('CD', 'Pressure', 'RF')),
    )
    cells = ((0, 0, 1.0), (1, 1, 1.0), (2, 2, 1.0), (0, 1, -.4), (1, 0, -.4))
    visual = build_echarts_options(spec, (SeriesSpec('corr', 'Correlation', cells),))
    scale = visual['visualMap']
    assert scale['min'] < 0 < scale['max']
    assert scale['min'] == -scale['max']
    assert scale['inRange']['color'][0] != scale['inRange']['color'][-1]
    assert cells == tuple(cell for cell in cells if cell[2] != 0 or cell[0] == cell[1])


def test_categorical_wafer_separates_category_fill_from_alert_outline():
    sys.path.insert(0, str(ROOT / 'tools'))
    import execute_visualization_examples as support
    from nicegui_base import WaferMap, WaferPoint

    with support._fake_nicegui():
        wafer = WaferMap(
            'Categories',
            (WaferPoint(0, 0, 1, metadata={'category': 'Nominal'}), WaferPoint(1, 0, 1, metadata={'category': 'Watch'})),
            scale_mode=ScaleMode.CATEGORICAL, category_key='category', legend_labels=('Nominal', 'Watch'),
        )
    assert 'is-watch' not in wafer.svg
    assert 'cui-spatial-bin-0' in wafer.svg and 'cui-spatial-bin-1' in wafer.svg
    assert wafer.legend_mapping['Nominal'] != wafer.legend_mapping['Watch']


def test_specialized_responsive_options_keep_sankey_labels_and_fault_tree_leaves_readable():
    from nicegui_base.integrations.nicegui_visualization import _FaultTreeDiagram, _SankeyDiagram

    sankey = _SankeyDiagram.build_options(('Affected', 'ETCH-021', 'CH-3', 'Review'), (('Affected', 'ETCH-021', 84), ('ETCH-021', 'CH-3', 61), ('CH-3', 'Review', 43)))
    assert sankey['series'][0]['right'] >= 72
    assert sankey['media'][0]['query']['maxWidth'] <= 520
    assert sankey['media'][0]['option']['series'][0]['right'] >= 80
    assert sankey['series'][0]['label']['color'] == '#1D1D1F'
    assert _SankeyDiagram.build_options(('A', 'B'), (('A', 'B', 1),), theme_mode='dark')['series'][0]['label']['color'] == '#F5F5F7'

    tree = _FaultTreeDiagram.build_options({'name': 'OOS', 'children': ({'name': 'OR', 'gate': 'OR', 'children': ({'name': 'Pressure'}, {'name': 'RF'} )},)})
    series = tree['series'][0]
    assert series['orient'] == 'LR'
    assert series['layout'] == 'orthogonal'
    assert series['nodeGap'] >= 20
    assert series['leaves']['label']['position'] == 'right'


def test_small_multiple_workbench_uses_compact_shared_scale_children():
    app = (ROOT / 'source' / 'nicegui_base' / 'workbench' / 'app.py').read_text(encoding='utf-8')
    assert 'cui-workbench-mini-grid--wafer-multiples' in app
    assert 'size=ChartSize.COMPACT' in app
    assert 'scale_min=shared_low, scale_max=shared_high' in app
