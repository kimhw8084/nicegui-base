import pytest
from nicegui_base.visualization import (
    ChartEvent, CrossFilterBinding, CrossFilterEngine, LinkedAnalysisController, SeriesSpec,
    SpatialPoint, WaferPoint, box_summary, histogram, pareto, series_rows, spatial_bounds, wafer_bounds,
)

def test_crossfilter_dispatch_and_clear():
    e=CrossFilterEngine([CrossFilterBinding('pareto','click','tool')])
    out=e.dispatch(ChartEvent('pareto','click',value='ETCH-01'))
    assert out[0].key=='tool' and out[0].value=='ETCH-01'
    assert e.active_filters['tool'].value=='ETCH-01'
    e.clear('tool'); assert not e.active_filters

def test_crossfilter_payload_key():
    e=CrossFilterEngine([CrossFilterBinding('c','click','chamber')])
    e._bindings[0]=CrossFilterBinding('c','click','chamber')
    out=e.dispatch(ChartEvent('c','click',value='C1',payload={'name':'C2'}))
    assert out[0].value=='C1'

def test_linked_controller_routes_to_registered_target():
    c=LinkedAnalysisController(CrossFilterEngine([CrossFilterBinding('trend','click','lot')]))
    seen=[]; c.register_target('lot',lambda m: seen.append(m.value))
    c.dispatch(ChartEvent('trend','click',value='L123'))
    assert seen==['L123']

def test_histogram_and_validation():
    assert sum(x['count'] for x in histogram([1,2,3,4],2))==4
    assert histogram([],3)==[]
    with pytest.raises(ValueError): histogram([1],0)

def test_pareto_computes_cumulative():
    result=pareto([{'c':'A','v':2},{'c':'B','v':1},{'c':'A','v':1}],'c','v')
    assert result[0]['category']=='A'
    assert round(result[-1]['cumulative_pct'],6)==100

def test_box_summary():
    s=box_summary([1,2,3,4,5])
    assert s['median']==3 and s['min']==1 and s['max']==5 and s['mean']==3
    assert box_summary([]) is None

def test_bounds_helpers():
    assert wafer_bounds([WaferPoint(-1,2),WaferPoint(3,-4)])==(-1,3,-4,2)
    assert spatial_bounds([SpatialPoint(-2,1),SpatialPoint(4,5)])==(-2,4,1,5)
    assert wafer_bounds([]) is None

def test_series_rows():
    rows=series_rows([SeriesSpec('a','A',[10,20])])
    assert rows[1]=={'series':'A','series_key':'a','index':1,'value':20}
