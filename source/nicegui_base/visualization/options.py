from __future__ import annotations

import math
from typing import Any, Sequence

from nicegui_base.design.tokens import FONT_SIZES, FONT_WEIGHTS, MOTION_DURATIONS_MS

from .models import AnnotationIntent, AxisSpec, AxisType, ChartAnnotation, ChartKind, ChartPanelSpec, LegendPosition, ScaleMode, SeriesSpec, SpecLimits, ThresholdSpec
from .palette import CATEGORICAL, stable_series_color
from .theme import ChartTheme, chart_theme
from .formatting import javascript_visual_number_formatter


HEATMAP_SCALE = ('#E9F2FF','#A9CFFF','#5B9EFF','#246DCE','#183E76')
DIVERGING_SCALE = ('#2C7BE5','#62B0FF','#E6EEF5','#F3B25F','#D44A42')


def _supports_cartesian_zoom(kind: ChartKind) -> bool:
    return kind not in (ChartKind.DONUT, ChartKind.GAUGE, ChartKind.WAFER, ChartKind.SPATIAL)


def _axis(axis: AxisSpec, theme: ChartTheme) -> dict[str, Any]:
    d: dict[str, Any] = {
        'type': axis.kind.value,
        'name': axis.label or '',
        'inverse': axis.inverse,
        'boundaryGap': axis.kind is AxisType.CATEGORY,
        'axisLine': {'show': False},
        'axisTick': {'show': False},
        'axisLabel': {'color': theme.text_secondary, 'fontSize': FONT_SIZES['11'], 'margin': 10, 'hideOverlap': True},
        'nameTextStyle': {'color': theme.text_secondary, 'fontSize': FONT_SIZES['11'], 'padding': [0, 0, 4, 0]},
        'splitLine': {'show': axis.show_grid, 'lineStyle': {'color': theme.grid, 'width': 1}},
        'splitNumber': 4,
    }
    if axis.kind is AxisType.CATEGORY and axis.categories:
        d['data'] = list(axis.categories)
    if axis.kind in (AxisType.VALUE, AxisType.TIME, AxisType.LOG):
        d['axisLabel'][':formatter'] = javascript_visual_number_formatter(axis.unit)
    if axis.min_value is not None:
        d['min'] = axis.min_value
    if axis.max_value is not None:
        d['max'] = axis.max_value
    return d


def _legend(pos: LegendPosition, theme: ChartTheme) -> dict[str, Any]:
    if pos is LegendPosition.HIDDEN:
        return {'show': False}
    d: dict[str, Any] = {
        'show': True,
        'itemWidth': 8,
        'itemHeight': 8,
        'itemGap': 16,
        'icon': 'circle',
        'textStyle': {'color': theme.text_secondary, 'fontSize': FONT_SIZES['11'], 'fontWeight': FONT_WEIGHTS['500']},
    }
    if pos in (LegendPosition.TOP, LegendPosition.BOTTOM):
        d[pos.value] = 4
        d['right'] = 8
    else:
        d[pos.value] = 8
        d['orient'] = 'vertical'
    return d


def _donut_data(data: Sequence[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict) and 'value' in item:
            result.append(dict(item))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            # Lab/public API uses (label, value). ECharts pie wants {name,value}.
            result.append({'name': str(item[0]), 'value': item[1]})
        else:
            result.append({'name': str(item), 'value': item})
    return result


def _series(s: SeriesSpec, theme: ChartTheme) -> dict[str, Any]:
    semantic = {'success': theme.success, 'warning': theme.warning, 'danger': theme.danger, 'info': theme.info, 'neutral': theme.text_secondary, 'accent': theme.accent}
    color = semantic.get(s.semantic_color or '') or stable_series_color(s.key)
    kind = s.kind
    echarts_type = {
        ChartKind.LINE:'line', ChartKind.AREA:'line', ChartKind.BAR:'bar', ChartKind.STACKED_BAR:'bar',
        ChartKind.SCATTER:'scatter', ChartKind.HISTOGRAM:'bar', ChartKind.BOX_PLOT:'boxplot',
        ChartKind.HEATMAP:'heatmap', ChartKind.TIMELINE:'line', ChartKind.DONUT:'pie', ChartKind.GAUGE:'gauge',
        ChartKind.WAFER:'scatter', ChartKind.SPATIAL:'scatter', ChartKind.PARETO:'bar', ChartKind.CONTROL:'line',
    }[kind]
    data: Any = [[item[s.x_key], item[s.y_key]] for item in s.data] if s.x_key is not None else list(s.data)
    if kind is ChartKind.DONUT:
        data = _donut_data(s.data)
        for index, item in enumerate(data):
            item['itemStyle'] = {'color': CATEGORICAL[index % len(CATEGORICAL)]}
    elif kind is ChartKind.GAUGE:
        value = s.data[0] if s.data else 0
        data = [{'value': value, 'name': s.label}]
    d: dict[str, Any] = {'name': s.label, 'type': echarts_type, 'data': data, 'itemStyle': {'color': color}}
    if s.y_axis_index:
        d['yAxisIndex'] = s.y_axis_index
    if kind in (ChartKind.LINE, ChartKind.AREA, ChartKind.TIMELINE, ChartKind.CONTROL):
        d.update({
            'smooth': s.smooth,
            'symbol': s.marker.value,
            'symbolSize': 6,
            'showSymbol': len(s.data) <= 36,
            'lineStyle': {'type': s.line_style.value, 'color': color, 'width': 2.5, 'cap': 'round', 'join': 'round'},
            'emphasis': {'focus': 'series', 'lineStyle': {'width': 3}},
        })
    if kind is ChartKind.AREA:
        d['areaStyle'] = {'opacity': .10, 'color': color}
    if kind in (ChartKind.BAR, ChartKind.STACKED_BAR, ChartKind.HISTOGRAM):
        d['barMaxWidth'] = 28
        d['itemStyle'] = {'color': color, 'borderRadius': [5, 5, 2, 2] if kind is not ChartKind.STACKED_BAR else [0, 0, 0, 0]}
    if kind is ChartKind.STACKED_BAR:
        d['stack'] = s.stack or 'total'
    if kind is ChartKind.DONUT:
        d.update({
            'radius': ['62%', '80%'], 'center': ['50%', '52%'], 'avoidLabelOverlap': True,
            'label': {'show': False}, 'labelLine': {'show': False},
            'emphasis': {'scale': True, 'scaleSize': 5, 'itemStyle': {'shadowBlur': 18, 'shadowColor': 'rgba(0,0,0,.12)'}},
        })
    if kind is ChartKind.GAUGE:
        d.update({
            'radius': '86%', 'startAngle': 210, 'endAngle': -30,
            'progress': {'show': True, 'roundCap': True, 'width': 12, 'itemStyle': {'color': color}},
            'axisLine': {'roundCap': True, 'lineStyle': {'width': 12, 'color': [[1, theme.grid]]}},
            'axisTick': {'show': False}, 'splitLine': {'show': False}, 'axisLabel': {'show': False}, 'pointer': {'show': False},
            'detail': {'valueAnimation': True, 'formatter': '{value}%', 'fontSize': FONT_SIZES['26'], 'fontWeight': FONT_WEIGHTS['650'], 'color': theme.text_primary, 'offsetCenter': [0, '4%']},
            'title': {'offsetCenter': [0, '36%'], 'fontSize': FONT_SIZES['11'], 'color': theme.text_secondary},
        })
    if kind is ChartKind.HEATMAP:
        d['itemStyle'] = {'borderRadius': 5, 'borderWidth': 2, 'borderColor': theme.background}
        d['emphasis'] = {'itemStyle': {'shadowBlur': 10, 'shadowColor': 'rgba(0,0,0,.16)', 'borderColor': theme.text_primary}}
    if kind in (ChartKind.WAFER, ChartKind.SPATIAL):
        d.update({
            'symbol': 'roundRect' if kind is ChartKind.WAFER else 'circle',
            'symbolSize': 14 if kind is ChartKind.WAFER else 16,
            'itemStyle': {'borderWidth': 1, 'borderColor': theme.background, 'opacity': .96},
            'emphasis': {'scale': 1.35, 'itemStyle': {'borderWidth': 2, 'borderColor': theme.text_primary, 'shadowBlur': 12, 'shadowColor': 'rgba(0,0,0,.18)'}},
        })
    n = len(s.data)
    if n > 2000 and kind in (ChartKind.LINE, ChartKind.AREA, ChartKind.TIMELINE, ChartKind.CONTROL):
        d['sampling'] = 'lttb'; d['showSymbol'] = False
    if n > 2000 and kind in (ChartKind.SCATTER, ChartKind.WAFER, ChartKind.SPATIAL, ChartKind.BAR, ChartKind.STACKED_BAR):
        d['large'] = True; d['largeThreshold'] = 2000; d['progressive'] = 5000
    return d


def _spatial_values(series: Sequence[SeriesSpec]) -> list[float]:
    values: list[float] = []
    for ss in series:
        for item in ss.data:
            if isinstance(item, (list, tuple)) and len(item) >= 3 and isinstance(item[2], (int, float)):
                values.append(float(item[2]))
    return values


def _mark_line_label(text: str, color: str, *, coordinate: str, align: str | None = None,
                     position: str | None = None, inverted_y_axis: bool = False) -> dict[str, Any]:
    """Keep reference labels attached to their line with bounded orientation-aware placement."""
    label: dict[str, Any] = {
        'formatter': text,
        'color': color,
        'fontSize': FONT_SIZES['10'],
        # ECharts rotates vertical-line labels for every ``inside*`` position.
        # Start/end keep their text horizontal; the endpoint is selected so it
        # sits at the top of the visible plot, in the reserved axis-name band.
        'position': position or ('insideStartTop' if coordinate == 'yAxis' else (
            'start' if inverted_y_axis else 'end'
        )),
        'distance': [6, 4],
    }
    if coordinate == 'xAxis' and align is not None:
        label['align'] = align
    return label


def _finite_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
        return float(value)
    return None


def _series_axis_values(series: Sequence[SeriesSpec], *, y_axis: bool) -> list[Any]:
    values: list[Any] = []
    for item in series:
        if item.x_key is not None:
            key = item.y_key if y_axis else item.x_key
            values.extend(row[key] for row in item.data)
        elif item.data and isinstance(item.data[0], (tuple, list)) and len(item.data[0]) >= 2:
            index = 1 if y_axis else 0
            values.extend(row[index] for row in item.data if isinstance(row, (tuple, list)) and len(row) > index)
        else:
            values.extend(item.data)
    return values


def _axis_value_ratio(value: Any, axis: AxisSpec, values: Sequence[Any]) -> float | None:
    """Estimate a reference's normalized axis position for an inward label side."""
    if axis.kind is AxisType.CATEGORY:
        categories = tuple(axis.categories)
        if not categories:
            unique_categories: list[Any] = []
            for item in values:
                if item not in unique_categories:
                    unique_categories.append(item)
            categories = tuple(unique_categories)
        try:
            index = categories.index(value)
        except ValueError:
            index = value if isinstance(value, int) and not isinstance(value, bool) else None
        if index is None or len(categories) <= 1:
            return None
        ratio = max(0.0, min(1.0, index / (len(categories) - 1)))
    else:
        numeric_values = [number for item in values if (number := _finite_number(item)) is not None]
        numeric_value = _finite_number(value)
        if numeric_value is None:
            return None
        if axis.kind is AxisType.LOG:
            numeric_values = [item for item in numeric_values if item > 0]
            if numeric_value <= 0:
                return None
            low = float(axis.min_value) if axis.min_value is not None else (min(numeric_values) if numeric_values else numeric_value)
            high = float(axis.max_value) if axis.max_value is not None else (max(numeric_values) if numeric_values else numeric_value)
            if low <= 0 or high <= low:
                return None
            ratio = (math.log(numeric_value) - math.log(low)) / (math.log(high) - math.log(low))
        else:
            low = float(axis.min_value) if axis.min_value is not None else min(numeric_values, default=numeric_value)
            high = float(axis.max_value) if axis.max_value is not None else max(numeric_values, default=numeric_value)
            # Value axes default to including zero. Match that contract when a
            # shared option does not set explicit bounds, without changing axis
            # geometry or reserving additional chart space.
            if axis.min_value is None and low > 0:
                low = 0.0
            if axis.max_value is None and high < 0:
                high = 0.0
            if high <= low:
                return None
            ratio = (numeric_value - low) / (high - low)
        ratio = max(0.0, min(1.0, ratio))
    return 1.0 - ratio if axis.inverse else ratio


def _horizontal_mark_line_position(index: int, value: Any, axis: AxisSpec,
                                   series: Sequence[SeriesSpec], reference_values: Sequence[Any]) -> str:
    """Place a horizontal reference label on the side with more plot interior."""
    values = (*_series_axis_values(series, y_axis=True), *reference_values)
    ratio = _axis_value_ratio(value, axis, values)
    # High values map near the top of a normal y-axis, so put their labels below
    # the line. Low values use the opposite side. Midpoint ties alternate to
    # keep otherwise coincident labels from stacking on the same side.
    if ratio is None:
        side = 'Top' if index % 2 == 0 else 'Bottom'
    elif ratio > 0.5:
        side = 'Bottom'
    elif ratio < 0.5:
        side = 'Top'
    else:
        side = 'Top' if index % 2 == 0 else 'Bottom'
    endpoint = 'insideStart' if index % 2 == 0 else 'insideEnd'
    return endpoint + side


def _x_axis_label_align(value: Any, axis: AxisSpec, series: Sequence[SeriesSpec],
                        reference_values: Sequence[Any] = ()) -> str:
    """Align vertical reference labels toward the interior edge of the plot."""
    if axis.kind is AxisType.CATEGORY:
        categories = tuple(axis.categories)
        category_count = len(categories) or max((len(item.data) for item in series), default=0)
        try:
            index = categories.index(value)
        except ValueError:
            index = value if isinstance(value, int) and not isinstance(value, bool) else None
        if index is None or category_count <= 1:
            return 'center'
        ratio = max(0.0, min(1.0, index / (category_count - 1)))
    else:
        values: list[float] = []
        for item in reference_values:
            if isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(float(item)):
                values.append(float(item))
        for item in series:
            if item.x_key is not None:
                candidates = (row[item.x_key] for row in item.data)
            elif item.data and isinstance(item.data[0], (tuple, list)) and len(item.data[0]) >= 2:
                candidates = (row[0] for row in item.data if isinstance(row, (tuple, list)) and len(row) >= 2)
            else:
                candidates = range(len(item.data))
            for candidate in candidates:
                if isinstance(candidate, (int, float)) and not isinstance(candidate, bool) and math.isfinite(float(candidate)):
                    values.append(float(candidate))
        low = float(axis.min_value) if axis.min_value is not None else (min(values) if values else None)
        high = float(axis.max_value) if axis.max_value is not None else (max(values) if values else None)
        if low is None or high is None or high <= low or not isinstance(value, (int, float)):
            return 'center'
        ratio = max(0.0, min(1.0, (float(value) - low) / (high - low)))
    if axis.inverse:
        ratio = 1.0 - ratio
    if ratio <= 0.33:
        return 'left'
    if ratio >= 0.67:
        return 'right'
    return 'center'


def build_echarts_options(spec: ChartPanelSpec, series: Sequence[SeriesSpec], *,
                          thresholds: Sequence[ThresholdSpec]=(), spec_limits: SpecLimits | None=None,
                          annotations: Sequence[ChartAnnotation]=(), theme: ChartTheme | None=None) -> dict[str, Any]:
    theme = theme or chart_theme('light')
    item_trigger = spec.kind in (ChartKind.SCATTER, ChartKind.WAFER, ChartKind.SPATIAL, ChartKind.DONUT, ChartKind.HEATMAP, ChartKind.GAUGE)
    visible_series=tuple(s for s in series if s.visible)
    legend=_legend(spec.legend, theme)
    if len(visible_series) <= 1 and spec.kind is not ChartKind.DONUT:
        # A one-series legend repeats the chart title/metric and steals plot space.
        legend={'show': False}
    options: dict[str, Any] = {
        'backgroundColor': theme.background,
        'animation': spec.animate,
        'animationDuration': MOTION_DURATIONS_MS['chart'],
        'animationDurationUpdate': MOTION_DURATIONS_MS['shell'],
        'animationEasing': 'cubicOut',
        'animationEasingUpdate': 'cubicOut',
        'textStyle': {'fontFamily':'-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif','color':theme.text_primary},
        'tooltip': {
            'trigger':'item' if item_trigger else 'axis',
            'confine': True,
            'backgroundColor': theme.surface_elevated,
            'borderWidth': 0,
            'padding': [10, 12],
            'extraCssText': 'border-radius:14px;box-shadow:0 12px 34px rgba(0,0,0,.14);',
            'textStyle': {'color':theme.text_primary,'fontSize':FONT_SIZES['11']},
            'axisPointer': {'type':'line','lineStyle':{'color':theme.text_secondary,'width':1,'opacity':.35}},
        },
        'legend': legend,
        'grid': {'left':22,'right':22,'top':54,'bottom':30,'containLabel':True},
        'xAxis': _axis(spec.x_axis, theme),
        'yAxis': _axis(spec.y_axis, theme),
        'series': [_series(s, theme) for s in visible_series],
    }
    # Stacked segments share one silhouette: interior joins are square and only
    # the outside top/bottom corners are rounded. This prevents visible seams.
    stack_groups: dict[str, list[int]] = {}
    for idx, ss in enumerate(visible_series):
        if ss.kind is ChartKind.STACKED_BAR:
            stack_groups.setdefault(ss.stack or 'total', []).append(idx)
    for indexes in stack_groups.values():
        if len(indexes) == 1:
            options['series'][indexes[0]]['itemStyle']['borderRadius'] = [5, 5, 5, 5]
        else:
            options['series'][indexes[0]]['itemStyle']['borderRadius'] = [0, 0, 5, 5]
            for idx in indexes[1:-1]:
                options['series'][idx]['itemStyle']['borderRadius'] = [0, 0, 0, 0]
            options['series'][indexes[-1]]['itemStyle']['borderRadius'] = [5, 5, 0, 0]
    if isinstance(options.get('xAxis'), dict) and spec.x_axis.label:
        options['xAxis'].update({'nameLocation':'middle','nameGap':30})
    if isinstance(options.get('yAxis'), dict) and spec.y_axis.label:
        options['yAxis'].update({'nameLocation':'middle','nameGap':46})
    if spec.kind is ChartKind.PARETO:
        options['yAxis'] = [_axis(spec.y_axis, theme), _axis(AxisSpec(label='Cumulative',kind=AxisType.VALUE,unit='%',min_value=0,max_value=100),theme)]
    if spec.kind is ChartKind.HEATMAP:
        values = _spatial_values(series)
        if spec.scale_mode is ScaleMode.DIVERGING:
            magnitude = max(
                abs(float(spec.color_min)) if spec.color_min is not None else 0.0,
                abs(float(spec.color_max)) if spec.color_max is not None else 0.0,
                max((abs(value) for value in values), default=0.0),
                1e-12,
            )
            color_min = float(spec.color_min) if spec.color_min is not None else -magnitude
            color_max = float(spec.color_max) if spec.color_max is not None else magnitude
            if not color_min < 0 < color_max:
                raise ValueError('diverging heatmap scale must cross zero')
            palette = DIVERGING_SCALE
        else:
            color_min = float(spec.color_min) if spec.color_min is not None else (min(values) if values else 0.0)
            color_max = float(spec.color_max) if spec.color_max is not None else (max(values) if values else 1.0)
            palette = HEATMAP_SCALE
        # Color mapping remains inside ECharts, but NiceGUI Base owns the visible scale band below the plot.
        # This prevents the floating visualMap from colliding with axis tooltips/cursors.
        options['visualMap'] = {
            'show': False,
            'min': color_min, 'max': color_max,
            'calculable': False,
            'inRange': {'color': list(palette)},
        }
        options['legend'] = {'show': False}
        options['grid'].update({'top':24,'bottom':28})
    if spec.kind in (ChartKind.DONUT, ChartKind.GAUGE):
        options.pop('xAxis', None); options.pop('yAxis', None); options.pop('grid', None)
    if spec.kind in (ChartKind.WAFER, ChartKind.SPATIAL):
        values = _spatial_values(series)
        options['xAxis'].update({'show': False, 'scale': True, 'min': 'dataMin', 'max': 'dataMax'})
        options['yAxis'].update({'show': False, 'scale': True, 'min': 'dataMin', 'max': 'dataMax'})
        options['grid'] = {'left':26,'right':88,'top':20,'bottom':20,'containLabel':False}
        options['visualMap'] = {
            'show': True, 'min': min(values) if values else 0, 'max': max(values) if values else 1,
            'orient': 'vertical', 'right': 10, 'top': 'middle', 'itemHeight': 112, 'itemWidth': 8,
            'calculable': False, 'precision': 2,
            'inRange': {'color': list(DIVERGING_SCALE)},
            'textStyle': {'color': theme.text_secondary, 'fontSize': FONT_SIZES['10']},
        }
        if spec.kind is ChartKind.WAFER:
            # Visual wafer body and notch are ECharts graphics, not a generic scatter frame.
            options['graphic'] = [
                {'type':'circle','left':'center','top':'middle','shape':{'r':132},'style':{'fill':'transparent','stroke':theme.border,'lineWidth':1.5},'silent':True},
                {'type':'polygon','left':'center','bottom':15,'shape':{'points':[[0,0],[7,8],[14,0]]},'style':{'fill':theme.background,'stroke':theme.border,'lineWidth':1},'silent':True},
            ]
    if spec.toolbar.zoom and _supports_cartesian_zoom(spec.kind):
        # Direct manipulation is deliberately 2D: ordinary wheel/trackpad gestures zoom both
        # domains and drag pans both domains. The Company toolbar also exposes explicit X/Y
        # range controls for precision work, so no modifier gesture is required for discovery.
        options['dataZoom'] = [
            {
                'id':'cui-x-zoom','type':'inside','xAxisIndex':0,'filterMode':'filter',
                'zoomOnMouseWheel':True,'moveOnMouseMove':True,'moveOnMouseWheel':False,
                'preventDefaultMouseMove':True,'start':0,'end':100,'minSpan':4,'throttle':32,
            },
            {
                'id':'cui-y-zoom','type':'inside','yAxisIndex':0,'filterMode':'none',
                'zoomOnMouseWheel':True,'moveOnMouseMove':True,'moveOnMouseWheel':False,
                'preventDefaultMouseMove':True,'start':0,'end':100,'minSpan':4,'throttle':32,
            },
        ]
    feature: dict[str, Any] = {}
    if spec.toolbar.reset: feature['restore'] = {'show': True, 'title':'Reset'}
    if spec.toolbar.export_image: feature['saveAsImage'] = {'show': True, 'title':'Export image','pixelRatio':2,'backgroundColor':'transparent'}
    if spec.toolbar.data_view: feature['dataView'] = {'show': True, 'title':'Data view','readOnly':True}
    if feature: options['toolbox'] = {'show': False, 'feature': feature}

    mark_lines=[]
    horizontal_references: list[Any] = [item.value for item in thresholds]
    if spec.kind is not ChartKind.HISTOGRAM and spec_limits is not None:
        horizontal_references.extend(value for value in (spec_limits.lower, spec_limits.target, spec_limits.upper) if value is not None)
    for index, t in enumerate(thresholds):
        color={'info':theme.info,'success':theme.success,'warning':theme.warning,'danger':theme.danger,'neutral':theme.text_secondary}[t.intent.value]
        position = _horizontal_mark_line_position(index, t.value, spec.y_axis, visible_series, horizontal_references)
        mark_lines.append({'yAxis':t.value,'name':t.label,'lineStyle':{'type':t.line_style.value,'color':color,'width':1.2},'label':_mark_line_label(t.label,theme.text_secondary,coordinate='yAxis',position=position)})
    if spec_limits:
        # Capability limits are vertical annotations on a numeric measurement
        # axis. Every other limit contract is a horizontal y-axis reference.
        coordinate = 'xAxis' if spec.kind is ChartKind.HISTOGRAM else 'yAxis'
        refs = tuple(value for value in (spec_limits.lower, spec_limits.target, spec_limits.upper) if value is not None)
        for value, label, style, color in (
            (spec_limits.lower, spec_limits.lower_label, 'dashed', theme.danger),
            (spec_limits.upper, spec_limits.upper_label, 'dashed', theme.danger),
            (spec_limits.target, spec_limits.target_label, 'dotted', theme.info),
        ):
            if value is None:
                continue
            align = _x_axis_label_align(value, spec.x_axis, visible_series, refs) if coordinate == 'xAxis' else None
            position = _horizontal_mark_line_position(len(mark_lines), value, spec.y_axis, visible_series, horizontal_references) if coordinate == 'yAxis' else None
            mark_lines.append({coordinate:value,'name':label,'lineStyle':{'type':style,'color':color,'width':1.2},'label':_mark_line_label(label,color,coordinate=coordinate,align=align,position=position,inverted_y_axis=spec.y_axis.inverse)})
    annotation_colors={AnnotationIntent.INFO:theme.info,AnnotationIntent.SUCCESS:theme.success,AnnotationIntent.WARNING:theme.warning,AnnotationIntent.DANGER:theme.danger,AnnotationIntent.NEUTRAL:theme.text_secondary}
    mark_points=[]
    for annotation in annotations:
        color=annotation_colors[annotation.intent]
        if annotation.y is None:
            refs = tuple(item.x for item in annotations if item.y is None)
            align = _x_axis_label_align(annotation.x, spec.x_axis, visible_series, refs)
            mark_lines.append({'xAxis':annotation.x,'name':annotation.label,'lineStyle':{'type':'dotted','color':color,'width':1.2},'label':_mark_line_label(annotation.label,color,coordinate='xAxis',align=align,inverted_y_axis=spec.y_axis.inverse)})
        else:
            mark_points.append({'name':annotation.label,'coord':[annotation.x,annotation.y],'value':annotation.label,'itemStyle':{'color':color},'label':{'formatter':annotation.label,'color':color,'fontSize':FONT_SIZES['10']}})
    if options['series']:
        if mark_lines:
            options['series'][0]['markLine'] = {'symbol':['none','none'],'silent':True,'data':mark_lines}
        if mark_points:
            options['series'][0]['markPoint'] = {'symbol':'pin','symbolSize':42,'data':mark_points}
    return options


__all__=['HEATMAP_SCALE','DIVERGING_SCALE','build_echarts_options']
