from __future__ import annotations

from pathlib import Path

import nicegui_base
from nicegui_base.certification.mac_coverage import coverage_summary
from nicegui_base.design.hardening_css import build_hardening_css
from nicegui_base.visualization import AxisSpec, AxisType, ChartKind, ChartPanelSpec, SeriesSpec, build_echarts_options

ROOT=Path(__file__).resolve().parents[1]


def test_cartesian_charts_expose_direct_2d_wheel_zoom_and_drag_pan():
    opt=build_echarts_options(
        ChartPanelSpec('Trend',kind=ChartKind.LINE,x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('A','B','C'))),
        (SeriesSpec('a','A',(1,2,3),kind=ChartKind.LINE),),
    )
    zoom=opt['dataZoom']
    assert [item['id'] for item in zoom]==['cui-x-zoom','cui-y-zoom']
    assert zoom[0]['zoomOnMouseWheel'] is True and zoom[1]['zoomOnMouseWheel'] is True
    assert zoom[0]['moveOnMouseMove'] is True and zoom[1]['moveOnMouseMove'] is True
    assert zoom[0]['xAxisIndex']==0 and zoom[1]['yAxisIndex']==0
    assert zoom[0]['minSpan']==zoom[1]['minSpan']==4


def test_heatmap_uses_hidden_echarts_mapping_and_company_scale_band():
    opt=build_echarts_options(
        ChartPanelSpec('Heat',kind=ChartKind.HEATMAP,x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('A','B')),y_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('1','2'))),
        (SeriesSpec('heat','Intensity',((0,0,1.0),(1,0,4.0),(0,1,2.0),(1,1,3.0)),kind=ChartKind.HEATMAP),),
    )
    assert opt['visualMap']['show'] is False
    assert opt['visualMap']['min']==1.0 and opt['visualMap']['max']==4.0
    source=(ROOT/'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    css=(ROOT/'nicegui_base/visualization/css.py').read_text(encoding='utf-8')
    assert 'cui-chart-scale-band' in source and 'cui-chart-scale-band__gradient' in css


def test_single_series_legend_is_suppressed_but_multiseries_legend_remains():
    one=build_echarts_options(ChartPanelSpec('One'),(SeriesSpec('a','A',(1,2)),))
    two=build_echarts_options(ChartPanelSpec('Two'),(SeriesSpec('a','A',(1,2)),SeriesSpec('b','B',(2,3))))
    assert one['legend']=={'show':False}
    assert two['legend']['show'] is True and two['legend']['right']==8


def test_chart_zoom_reads_live_echarts_state_and_targets_axis_ids():
    source=(ROOT/'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    zoom=source[source.index('class ChartZoom'):source.index('class ChartBrush')]
    assert "run_chart_method('getOption')" in zoom
    assert "'cui-x-zoom'" in zoom and "'cui-y-zoom'" in zoom
    assert "'dataZoomId':self.IDS[a]" in zoom
    assert "axis: str = 'both'" in zoom


def test_toolbar_has_discoverable_axis_specific_range_surface():
    source=(ROOT/'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    toolbar=source[source.index('class ChartToolbar'):source.index('class ChartCrossFilter')]
    assert 'View range' in toolbar
    for token in ('Both axes','X axis','Y axis','Wheel/trackpad zooms both axes'):
        assert token in toolbar
    assert 'Image · PNG' in toolbar and 'Data · CSV' in toolbar


def test_wafer_and_spatial_cells_are_clipped_to_exact_visible_boundary():
    source=(ROOT/'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    assert '<clipPath' in source
    assert 'clip-path="url(#{clip_id})"' in source
    assert 'r="168"' in source
    assert 'radius=14' in source
    constitution=(ROOT/'nicegui_base/design/constitution_css.py').read_text(encoding='utf-8')
    assert '.cui-spatial-svg-host svg { width:100%; height:100%; display:block; overflow:hidden; }' in constitution
    from nicegui_base.design.css import build_css
    assert '--cui-radius-surface: 14px' in build_css()
    assert '--cui-radius-surface:' not in constitution


def test_semiconductor_native_set_includes_fingerprint_and_commonality_matrices():
    source=(ROOT/'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    registry=(ROOT/'nicegui_base/visualization/registry.py').read_text(encoding='utf-8')
    lab=(ROOT/'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    for name in ('ChamberFingerprintMatrix','CommonalityMatrix'):
        assert f'class {name}' in source
        assert name in registry and name in lab
        assert hasattr(nicegui_base,name) and name in nicegui_base.__all__
    css=build_hardening_css()
    assert '.cui-fingerprint-outline' in css and '.cui-commonality-outline' in css


def test_plotly_escape_hatch_enables_direct_scroll_zoom_without_modebar():
    source=(ROOT/'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    section=source[source.index('class PlotlyPanel'):source.index('class DistributionPanel')]
    assert "config.setdefault('scrollZoom',True)" in section
    assert "config.setdefault('displayModeBar',False)" in section


def test_browser_certification_proves_2d_zoom_scale_band_and_svg_containment():
    source=(ROOT/'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    for phrase in (
        'chart Zoom in did not adjust both x and y ranges',
        'explicit Y-axis range control did not change y dataZoom',
        'chart wheel did not directly change 2D zoom range',
        'heatmap scale band overlaps chart plot area',
        'wafer dies are not clipped to wafer boundary',
        'chamber fingerprint visualization missing',
        'commonality matrix visualization missing',
    ):
        assert phrase in source


def test_phase5_visual_coverage_is_complete_after_new_native_renderers():
    summary=coverage_summary()
    assert summary['required_visual_components']==183
    assert summary['covered_visual_components']==183
    assert summary['uncovered']==[]
