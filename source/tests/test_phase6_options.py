from nicegui_base.visualization import (
    AnnotationIntent, AxisSpec, AxisType, ChartKind, ChartPanelSpec, LegendPosition, SeriesSpec,
    SpecLimits, ThresholdSpec, build_echarts_options, chart_theme,
)

def test_line_options_have_theme_tooltip_grid_and_series():
    spec=ChartPanelSpec('Trend',x_axis=AxisSpec(kind=AxisType.CATEGORY))
    opt=build_echarts_options(spec,[SeriesSpec('a','A',[1,2,3])],theme=chart_theme('dark'))
    assert opt['series'][0]['type']=='line'
    assert opt['tooltip']['backgroundColor']==chart_theme('dark').surface_elevated
    assert opt['xAxis']['type']=='category'
    assert 'dataZoom' in opt and 'toolbox' in opt

def test_area_and_stacked_bar_semantics():
    area=build_echarts_options(ChartPanelSpec('A',kind=ChartKind.AREA),[SeriesSpec('a','A',[1],kind=ChartKind.AREA)])
    assert 'areaStyle' in area['series'][0]
    bar=build_echarts_options(ChartPanelSpec('B',kind=ChartKind.STACKED_BAR),[SeriesSpec('b','B',[1],kind=ChartKind.STACKED_BAR)])
    assert bar['series'][0]['stack']=='total'

def test_spec_limits_and_thresholds_become_mark_lines():
    spec=ChartPanelSpec('Control',kind=ChartKind.CONTROL)
    opt=build_echarts_options(spec,[SeriesSpec('x','X',[1,2],kind=ChartKind.CONTROL)],
        thresholds=[ThresholdSpec(1.5,'Watch',AnnotationIntent.WARNING)],spec_limits=SpecLimits(0,3,1.5))
    data=opt['series'][0]['markLine']['data']
    assert {x['name'] for x in data}=={'Watch','LSL','USL','Target'}

def test_large_series_gets_performance_hints():
    data=list(range(2501))
    opt=build_echarts_options(ChartPanelSpec('Large'),[SeriesSpec('a','A',data)])
    s=opt['series'][0]
    assert s['sampling']=='lttb' and s['showSymbol'] is False

def test_large_scatter_gets_progressive_mode():
    data=[[i,i] for i in range(2501)]
    spec=ChartPanelSpec('Scatter',kind=ChartKind.SCATTER)
    opt=build_echarts_options(spec,[SeriesSpec('s','S',data,kind=ChartKind.SCATTER)])
    assert opt['series'][0]['large'] is True

def test_hidden_legend():
    opt=build_echarts_options(ChartPanelSpec('X',legend=LegendPosition.HIDDEN),[SeriesSpec('x','X',[1])])
    assert opt['legend']=={'show':False}

def test_options_do_not_leak_css_vars_into_canvas_colors():
    opt=build_echarts_options(ChartPanelSpec('X'),[SeriesSpec('x','X',[1])])
    text=str(opt)
    assert 'var(--cui-' not in text
