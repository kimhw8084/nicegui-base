"""Explicit canonical table/chart examples. No chart-type substitutions."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from math import hypot
from statistics import mean
from typing import Any

from .preview_data import numeric_data, resolve_category_field

VISUALIZATION_KEYS = frozenset({
    'ChartPanel', 'LineChart', 'AreaChart', 'BarChart', 'StackedBarChart', 'ScatterChart',
    'Histogram', 'BoxPlot', 'Heatmap', 'ParetoChart', 'ControlChart', 'TimelineChart',
    'DonutChart', 'Gauge', 'WaferMap', 'SpatialMap', 'WaferComparisonMap',
    'ChamberFingerprintMatrix', 'CommonalityMatrix', 'RadialProfilePlot',
    'DistributionPanel', 'ProcessTrendPanel', 'ChartCrossFilter', 'PlotlyPanel',
})
TABLE_KEYS = frozenset({'data_table', 'server_data_table', 'editable_table', 'master_detail_table', 'table_toolbar', 'selection_bar'})


def _event(sink, name):
    def callback(event=None):
        if sink:
            sink(name)
    return callback


def visualization_data(rows, *, options=None, schema=None, measurement_field=None, category_field=None):
    """Return the actual chart field, labels and aligned values for a dataset."""
    options = dict(options or {})
    field, values = numeric_data(
        rows,
        options.get('measurement') or None,
        schema=schema,
        measurement_field=measurement_field,
    )
    label_field = options.get('label_field') or category_field
    if label_field:
        label_field = resolve_category_field(rows, schema=schema, field=label_field)
    else:
        label_field = resolve_category_field(rows, schema=schema)
    if not label_field:
        label_field = next((name for name in ('id', 'record_id', 'key') if any(name in row for row in rows)), None)
    labels = tuple(
        str(row.get(label_field)) if label_field and row.get(label_field) not in (None, '') else str(index + 1)
        for index, row in enumerate(rows)
    )
    return field, labels, values


def render_visualization(
    key: str,
    *,
    title: str,
    rows,
    options=None,
    on_event=None,
    schema=None,
    measurement_field=None,
    category_field=None,
):
    from nicegui import ui
    from nicegui_base.integrations import nicegui_visualization as v
    from nicegui_base.visualization import AxisSpec, AxisType, ChartKind, ChartPanelSpec, SeriesSpec, SpecLimits, SpatialPoint, WaferPoint
    options = dict(options or {})
    if key not in VISUALIZATION_KEYS:
        raise KeyError(f'Unsupported visualization: {key}')
    if not rows:
        ui.label('No data. Add rows in the Data tab.').classes('cui-workbench-note')
        return
    field, labels, values = visualization_data(
        rows,
        options=options,
        schema=schema,
        measurement_field=measurement_field,
        category_field=category_field,
    )
    finite_values = tuple(value for value in values if value is not None)
    axis = AxisSpec(kind=AxisType.CATEGORY, categories=labels)
    series = (SeriesSpec(field, field.replace('_', ' ').title(), values),)
    limits = None
    if options.get('show_limits') == 'on':
        low, high = min(finite_values), max(finite_values)
        margin = (high-low)*.1 or 1
        limits = SpecLimits(lower=low-margin, upper=high+margin, target=mean(finite_values))
    if key in {'LineChart','AreaChart','BarChart','StackedBarChart','ControlChart','TimelineChart'}:
        return getattr(v, key)(title, series, x_axis=axis, spec_limits=limits, on_click=_event(on_event, f'{key} selected'))
    if key == 'ChartPanel':
        return v.ChartPanel(series, spec=ChartPanelSpec(title=title, kind=ChartKind.LINE, x_axis=axis))
    if key == 'ScatterChart':
        return v.ScatterChart(title, (SeriesSpec(field, field, tuple((i+1,n) for i,n in enumerate(values))),))
    if key in {'Histogram', 'DistributionPanel'}:
        # Histogram takes bin counts, not raw measurements.
        low, high = min(finite_values), max(finite_values)
        width = (high-low)/8 or 1
        counts = [0]*8
        for n in finite_values:
            counts[min(7,max(0,int((n-low)/width)))] += 1
        bins = tuple(f'{low+i*width:.3g}' for i in range(8))
        return getattr(v, key)(title, (SeriesSpec('count','Count',tuple(counts)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=bins))
    if key == 'BoxPlot':
        ordered = sorted(finite_values)
        def q(p):
            index = (len(ordered)-1)*p; a = int(index); b = min(len(ordered)-1,a+1)
            return ordered[a]+(ordered[b]-ordered[a])*(index-a)
        return v.BoxPlot(title,(SeriesSpec('distribution',field,((ordered[0],q(.25),q(.5),q(.75),ordered[-1]),)),),
                         x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Current',)))
    if key == 'DonutChart':
        if any(n < 0 for n in finite_values):
            raise ValueError('Donut values must be non-negative.')
        return v.DonutChart(title,(SeriesSpec('parts',field,tuple((label, value) for label, value in zip(labels, values) if value is not None)),))
    if key == 'Gauge':
        return v.Gauge(title,(SeriesSpec(field,field,(mean(finite_values),)),))
    if key == 'ParetoChart':
        if any(n < 0 for n in finite_values):
            raise ValueError('Pareto values must be non-negative.')
        ranked = sorted(((label, value) for label, value in zip(labels, values) if value is not None), key=lambda pair:pair[1], reverse=True)
        total=sum(value for _, value in ranked); cumulative=[]; current=0
        for _,number in ranked:
            current += number; cumulative.append(100*current/total if total else 0)
        return v.ParetoChart(title,tuple(x[0] for x in ranked),tuple(x[1] for x in ranked),tuple(cumulative))
    if key in {'Heatmap','ChamberFingerprintMatrix','CommonalityMatrix'}:
        column_names = tuple(dict.fromkeys(str(row.get('sensor','Measurement')) for row in rows))
        row_names = tuple(dict.fromkeys(str(row.get('chamber',row.get('tool','Current'))) for row in rows))
        cells=[]
        for row_name in row_names:
            cells.append(tuple(mean([float(r[field]) for r in rows if
                str(r.get('chamber',r.get('tool','Current')))==row_name and str(r.get('sensor','Measurement'))==col and r.get(field) is not None and r.get(field) != ''] or [0.0]) for col in column_names))
        if key == 'ChamberFingerprintMatrix':
            ui.label('Cell means grouped by chamber/tool and sensor; this example does not calculate anomaly scores.').classes('cui-workbench-note')
            return v.ChamberFingerprintMatrix(title,row_names,column_names,cells)
        if key == 'CommonalityMatrix':
            ui.label('Illustrative normalized cell means, not association probabilities or causal commonality scores.').classes('cui-workbench-note')
            maximum=max((abs(x) for row in cells for x in row), default=1) or 1
            return v.CommonalityMatrix(title,row_names,column_names,tuple(tuple(max(0,x/maximum) for x in row) for row in cells))
        triples=tuple((x,y,n) for y,row in enumerate(cells) for x,n in enumerate(row))
        return v.Heatmap(title,(SeriesSpec('heat',field,triples),),x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=column_names),
                         y_axis=AxisSpec(kind=AxisType.CATEGORY,categories=row_names))
    if key in {'WaferMap','SpatialMap','WaferComparisonMap','RadialProfilePlot'}:
        if not all('x' in row and 'y' in row and field in row for row in rows):
            raise ValueError('Spatial examples require x, y and the selected measurement column.')
        points=tuple(WaferPoint(float(r['x']),float(r['y']),float(r[field])) for r in rows)
        if key == 'WaferMap': return v.WaferMap(title,points)
        if key == 'SpatialMap':
            return v.SpatialMap(title,tuple(SpatialPoint(float(r['x']),float(r['y']),float(r[field])) for r in rows))
        if key == 'WaferComparisonMap':
            controls=tuple(WaferPoint(p.x,p.y,mean(finite_values)) for p in points)
            return v.WaferComparisonMap(title,points,controls,description='Reference comparison uses the current population mean, not a measured control population.')
        ordered=sorted(points,key=lambda p:hypot(p.x,p.y))
        return v.RadialProfilePlot(title,tuple(p.value for p in ordered),tuple(mean(finite_values) for _ in ordered),
                                  description='Samples ordered by radius; reference is the current population mean.')
    if key == 'ProcessTrendPanel':
        return v.ProcessTrendPanel(title,series,x_axis=axis,spec_limits=limits)
    if key == 'PlotlyPanel':
        return v.PlotlyPanel(title,{'data':[{'type':'scatter','mode':'lines+markers','x':list(labels),'y':list(values)}],
                                    'layout':{'title':title,'margin':{'t':40,'l':40,'r':20,'b':40}}})
    if key == 'ChartCrossFilter':
        link=v.ChartCrossFilter()
        ui.label('ChartCrossFilter is a coordination helper; it does not draw a chart itself.').classes('cui-workbench-note')
        ui.label(type(link.engine).__name__).classes('cui-workbench-chip')
        return link
    raise AssertionError(f'No renderer for declared chart {key}')


def preview_table_data(rows):
    """Use a private positional key without overwriting a user-supplied field."""
    names={str(name) for row in rows for name in row}
    row_key='__preview_row'
    while row_key in names:
        row_key += '_'
    return [{**row,row_key:index} for index,row in enumerate(rows)], row_key


def render_table(key: str, *, title: str, rows, options=None, on_event=None):
    from nicegui_base.integrations.nicegui_data_table import DataTable, EditableTable, ServerDataTable, MasterDetailTable, TableToolbar, TableSelectionBar
    from nicegui_base.integrations.nicegui_content import PropertyGrid
    from nicegui_base.content import KeyValueItem
    from nicegui_base.data_table import TableColumn, ColumnKind, TableDensity, SelectionMode, TableResult, BulkAction
    if key not in TABLE_KEYS:
        raise KeyError(f'Unsupported table {key}')
    options=dict(options or {})
    data,row_key=preview_table_data(rows)
    names=tuple(dict.fromkeys(str(name) for row in rows for name in row))
    columns=tuple(TableColumn(name,name.replace('_',' ').title(), editable=key=='editable_table') for name in names)
    if not columns:
        columns=(TableColumn('value','Value'),)
    common={'title':title,'row_key':row_key,'density':TableDensity(options.get('density','compact')),
            'selection':SelectionMode(options.get('selection','multiple' if key=='selection_bar' else 'single'))}
    if key == 'editable_table':
        def saved(row, name, value):
            data[int(row[row_key])][name]=value
            if on_event: on_event(f'Edited {name}: {value}')
        return EditableTable(data,columns,save_edit=saved,**common)
    if key == 'server_data_table':
        async def fetch(query):
            # In-memory demonstration honours page/page_size; production replaces this provider.
            start=max(0,query.page-1)*query.page_size
            return TableResult(tuple(data[start:start+query.page_size]), total=len(data),page=query.page,page_size=query.page_size)
        return ServerDataTable(columns,fetch=fetch,**common)
    if key == 'master_detail_table':
        def details(row):
            PropertyGrid(tuple(KeyValueItem(str(k),str(k),str(v)) for k,v in row.items() if k!=row_key))
        return MasterDetailTable(data,columns,detail_renderer=details,**common)
    table=DataTable(data,columns,show_toolbar=key!='table_toolbar',on_select=_event(on_event,'Table selection changed'),**common)
    if key == 'table_toolbar': TableToolbar(table)
    if key == 'selection_bar': TableSelectionBar(table=table)
    return table
