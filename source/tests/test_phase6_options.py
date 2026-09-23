from nicegui_base.visualization import (
    AnnotationIntent, AxisSpec, AxisType, ChartAnnotation, ChartKind, ChartPanelSpec, LegendPosition, SeriesSpec,
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
    assert [x['label']['position'] for x in data]==['insideStartTop','insideEndTop','insideStartBottom','insideEndBottom']
    assert all(x['label']['formatter']==x['name'] for x in data)

def test_threshold_labels_keep_full_text_inside_horizontal_reference_lines():
    label='Upper Control Limit (UCL)'
    options=build_echarts_options(
        ChartPanelSpec('Control',kind=ChartKind.CONTROL),
        [SeriesSpec('x','X',[1,2],kind=ChartKind.CONTROL)],
        thresholds=[ThresholdSpec(2.5,label)],
    )
    mark=options['series'][0]['markLine']['data'][0]
    assert mark['yAxis']==2.5 and 'xAxis' not in mark
    assert mark['label']=={
        'formatter':label,'color':chart_theme('light').text_secondary,'fontSize':10,
        'position':'insideStartBottom','distance':[6,4],
    }

def test_spec_limit_label_geometry_follows_horizontal_or_vertical_reference_orientation():
    limits=SpecLimits(lower=0,target=1,upper=2,lower_label='Lower Specification Limit',
                      target_label='Nominal Target',upper_label='Upper Specification Limit')
    horizontal=build_echarts_options(
        ChartPanelSpec('Trend',kind=ChartKind.LINE),
        [SeriesSpec('trend','Trend',[1,2,3])],spec_limits=limits,
    )['series'][0]['markLine']['data']
    assert all('yAxis' in item and 'xAxis' not in item for item in horizontal)
    assert [item['label']['formatter'] for item in horizontal]==[
        'Lower Specification Limit','Upper Specification Limit','Nominal Target',
    ]
    assert [item['label']['position'] for item in horizontal]==[
        'insideStartTop','insideEndBottom','insideStartTop',
    ]

    vertical=build_echarts_options(
        ChartPanelSpec('Capability',kind=ChartKind.HISTOGRAM,
                       x_axis=AxisSpec(kind=AxisType.VALUE)),
        [SeriesSpec('hist','Count',((0,1),(1,3),(2,1)),kind=ChartKind.HISTOGRAM)],
        spec_limits=limits,
    )['series'][0]['markLine']['data']
    assert all('xAxis' in item and 'yAxis' not in item for item in vertical)
    assert [item['label']['formatter'] for item in vertical]==[
        'Lower Specification Limit','Upper Specification Limit','Nominal Target',
    ]
    assert all(item['label']['position']=='end' for item in vertical)
    assert [item['label']['align'] for item in vertical]==['left','right','center']
    assert all(item['label']['distance']==[6,4] for item in vertical)

def test_vertical_annotation_label_is_bounded_and_respects_inverted_value_axis():
    options=build_echarts_options(
        ChartPanelSpec('Events',x_axis=AxisSpec(kind=AxisType.VALUE,min_value=0,max_value=10),
                       y_axis=AxisSpec(kind=AxisType.VALUE,inverse=True)),
        [SeriesSpec('s','S',((0,1),(5,2),(10,3)))],
        annotations=(ChartAnnotation(0,'Left event'),ChartAnnotation(10,'Right event')),
    )
    labels=[item['label'] for item in options['series'][0]['markLine']['data']]
    assert [label['position'] for label in labels]==['start','start']
    assert [label['align'] for label in labels]==['left','right']
    assert all(label['distance']==[6,4] for label in labels)


def test_horizontal_reference_labels_choose_the_inward_side_of_the_y_axis():
    options=build_echarts_options(
        ChartPanelSpec('Limits',y_axis=AxisSpec(kind=AxisType.VALUE,min_value=0,max_value=100)),
        [SeriesSpec('measurement','Measurement',[20,48,51,97])],
        thresholds=(ThresholdSpec(96,'UCL'),ThresholdSpec(8,'LCL'),ThresholdSpec(50,'Center')),
    )
    marks=options['series'][0]['markLine']['data']
    assert [item['label']['formatter'] for item in marks]==['UCL','LCL','Center']
    assert all('yAxis' in item and 'xAxis' not in item for item in marks)
    assert [item['label']['position'] for item in marks]==[
        'insideStartBottom','insideEndTop','insideStartTop',
    ]
    assert all(item['label']['distance']==[6,4] for item in marks)

def test_mark_line_layout_keeps_theme_colors_and_does_not_add_global_gutter():
    series=[SeriesSpec('x','X',[1,2,3],kind=ChartKind.CONTROL)]
    for mode in ('light','dark'):
        theme=chart_theme(mode)
        plain=build_echarts_options(ChartPanelSpec('Plain'),series,theme=theme)
        annotated=build_echarts_options(
            ChartPanelSpec('Control',kind=ChartKind.CONTROL),series,
            thresholds=[ThresholdSpec(2,'Watch',AnnotationIntent.WARNING)],
            spec_limits=SpecLimits(lower=0,upper=3,target=2),theme=theme,
        )
        assert plain['grid']['right']==annotated['grid']['right']==22
        assert plain['backgroundColor']==annotated['backgroundColor']==theme.background
        marks=annotated['series'][0]['markLine']['data']
        assert marks[0]['lineStyle']['color']==theme.warning
        assert marks[1]['lineStyle']['color']==theme.danger
        assert marks[2]['lineStyle']['color']==theme.danger
        assert marks[3]['lineStyle']['color']==theme.info
        assert marks[1]['label']['color']==theme.danger
        assert marks[3]['label']['color']==theme.info

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
