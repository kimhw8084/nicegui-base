"""Behavioral regressions for the final visualization semantic corrections."""
from __future__ import annotations

import sys
import re
from pathlib import Path

import pytest

from nicegui_base.visualization import AxisSpec, AxisType, ChartKind, ChartPanelSpec, ScaleMode, SeriesSpec, build_echarts_options
from nicegui_base.visualization.formatting import format_visual_number, javascript_visual_number_formatter


ROOT = Path(__file__).resolve().parents[2]


def test_visual_number_formatter_bounds_binary_float_noise_and_keeps_units_separate():
    assert format_visual_number(3.3000000000000003) == '3.3'
    assert format_visual_number(-3.2000000000000006) == '-3.2'
    assert format_visual_number(42.287749160134375) == '42.29'
    assert format_visual_number(0.0) == '0'


@pytest.mark.parametrize(
    ('value', 'expected'),
    (
        (0, '0'), (1, '1'), (10, '10'), (20, '20'), (100, '100'),
        (1000, '1000'), (1010, '1010'), (1200, '1200'), (-10, '-10'),
        (-200, '-200'), (1.0, '1'), (10.0, '10'), (10.5000, '10.5'),
        (0.0100, '0.01'), (0.00001, '1e-5'),
        (3.3000000000000003, '3.3'), (-3.2000000000000006, '-3.2'),
        (42.287749160134375, '42.29'),
    ),
)
def test_visual_number_formatter_trims_only_fractional_zeroes(value, expected):
    assert format_visual_number(value) == expected


def test_javascript_visual_formatter_uses_the_same_magnitude_policy():
    formatter = javascript_visual_number_formatter()
    assert 'Math.abs(n) >= 1e4' in formatter
    assert 'Math.abs(n) < 1e-4' in formatter
    assert 'toExponential(3)' in formatter
    assert "toFixed(4)" in formatter
    assert "replace(/(\\.\\d*?[1-9])0+$|\\.0+$/,'$1')" in formatter


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


def test_chart_data_view_and_csv_preserve_integer_like_coordinates_and_values():
    sys.path.insert(0, str(ROOT / 'tools'))
    import execute_visualization_examples as support
    from nicegui_base import ChartPanel, ChartPanelSpec
    from nicegui_base.integrations.nicegui_visualization import _format_chart_cell

    with support._fake_nicegui():
        panel = ChartPanel(
            (SeriesSpec(
                'trace', 'Trace',
                ({'time': 10, 'value': 100}, {'time': 100, 'value': 1200}),
                kind=ChartKind.LINE, x_key='time', y_key='value',
            ),),
            spec=ChartPanelSpec('Trace', x_axis=AxisSpec(kind=AxisType.VALUE), y_axis=AxisSpec(kind=AxisType.VALUE)),
        )
        rows = panel.data_view.rows()
        csv_text = panel.export.csv_text()
        panel.dispose()
    assert [(row['x'], row['y'], row['value']) for row in rows] == [(10, 100, 100), (100, 1200, 1200)]
    csv_rows = {line.strip() for line in csv_text.splitlines()[1:]}
    assert 'Trace,0,10,100,100' in csv_rows
    assert 'Trace,1,100,1200,1200' in csv_rows
    assert [_format_chart_cell(value) for value in (10, 100, 1200)] == ['10', '100', '1200']


def test_spatial_legend_and_waterfall_labels_preserve_integer_magnitude():
    from nicegui_base.integrations.nicegui_visualization import _WaterfallDiagram, _spatial_svg_legend

    legend = _spatial_svg_legend(0, 100, x=10, y=10, height=100, title='Measurement')
    assert '>100<' in legend and '>0<' in legend

    options = _WaterfallDiagram.build_options(('Gain', 'Loss'), (10, -20))
    bars = {item['name']: item for series in options['series'] for item in series['data']}
    assert bars['Gain']['deltaLabel'] == '10'
    assert bars['Loss']['deltaLabel'] == '-20'
    assert bars['Net']['deltaLabel'] == '-10'
    assert bars['Net']['value'][2] == pytest.approx(-10)


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


def test_contour_isolines_are_deterministic_data_derived_and_truthfully_sparse():
    from nicegui_base.semiconductor.spatial import WaferSample, contour_isolines

    samples = tuple(
        WaferSample(x, y, 40 + x * 0.7 + y * 0.3)
        for y in range(-3, 4)
        for x in range(-3, 4)
    )
    first = contour_isolines(samples, cells=4)
    second = contour_isolines(samples, cells=4)
    assert first == second
    assert first and all(isoline.level > 0 for isoline in first)
    assert all(segment[0] != segment[1] for isoline in first for segment in isoline.segments)

    changed = tuple(WaferSample(sample.x, sample.y, (sample.value or 0) + (4 if sample.x > 0 else 0)) for sample in samples)
    assert contour_isolines(changed, cells=4) != first

    # With no complete four-corner source cell, the level is unavailable;
    # no below-threshold nearest samples are injected to manufacture a path.
    sparse = (
        WaferSample(0, 0, 10), WaferSample(1, 0, 0),
        WaferSample(0, 1, 0), WaferSample(10, 10, 0),
    )
    sparse_levels = contour_isolines(sparse, cells=6, levels=(9,))
    assert len(sparse_levels) == 1
    assert sparse_levels[0].available is False
    assert sparse_levels[0].segments == ()


def test_contour_renderer_labels_real_levels_and_makes_no_smoothing_claim():
    sys.path.insert(0, str(ROOT / 'tools'))
    import execute_visualization_examples as support
    from nicegui_base import WaferContourPlot, WaferPoint

    points = tuple(
        WaferPoint(x, y, 40 + x * 0.7 + y * 0.3)
        for y in range(-3, 4)
        for x in range(-3, 4)
    )
    with support._fake_nicegui():
        panel = WaferContourPlot('Contour', points)
    labels = re.findall(r'<title>Contour ([^<]+)</title>', panel.svg)
    expected = {format_visual_number(isoline.level) for isoline in panel.contour_isolines if isoline.available}
    assert 'Smoothed field' not in panel.svg
    assert 'Data-derived field' in panel.svg
    assert 'clipPath' in panel.svg and 'clip-path=' in panel.svg
    assert labels
    assert expected and set(labels) <= expected
    assert all(label == format_visual_number(float(label)) for label in labels)


def test_contour_renderer_omits_unavailable_sparse_levels_without_fabricating_paths():
    sys.path.insert(0, str(ROOT / 'tools'))
    import execute_visualization_examples as support
    from nicegui_base import WaferContourPlot, WaferPoint

    sparse = (
        WaferPoint(0, 0, 10), WaferPoint(1, 0, 0),
        WaferPoint(0, 1, 0), WaferPoint(10, 10, 0),
    )
    with support._fake_nicegui():
        panel = WaferContourPlot('Sparse contour', sparse)
    assert panel.contour_levels
    assert panel.contour_available_levels == ()
    assert panel.contour_unavailable_levels == panel.contour_levels
    assert 'data-contour-level=' not in panel.svg
    assert '<title>Contour ' not in panel.svg
    assert not re.findall(r'<path[^>]+ d="[^"]*Z', panel.svg)
