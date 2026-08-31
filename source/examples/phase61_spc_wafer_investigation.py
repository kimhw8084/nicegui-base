"""Wave 61 golden workflow: SPC + capability + wafer + populations + records.

The example intentionally composes one AnalysisContext and SelectionBus across records,
SPC/capability visual plans, spatial data, and affected/control populations.  It stays
framework-neutral so it can execute in source validation without a browser runtime; the
same plans feed NiceGUI Base's certified NiceGUI renderers when NiceGUI is installed.
"""
from __future__ import annotations
from nicegui_base import AnalysisCoordinator, AnalysisContext, Comparison, ComparisonOperator, DataSchema, FieldRole, FieldType, InMemoryDataSource, PopulationDefinition, SelectionBus, SemanticField
from nicegui_base.semiconductor import (
    SemiconductorAnalysisContext, SemiconductorAnalyticalSurface, WaferSample,
    affected_control_visual, capability_histogram_visual, capability_indices,
    control_chart_visual, delta_wafer, i_mr, radial_profile, wafer_points,
)

ROWS=(
 {'id':1,'product':'P1','route':'R1','operation':'ETCH10','tool':'T1','chamber':'A','lot':'L1','wafer':'W1','cd':10.0,'x':-1,'y':0,'affected':True},
 {'id':2,'product':'P1','route':'R1','operation':'ETCH10','tool':'T1','chamber':'A','lot':'L1','wafer':'W1','cd':10.4,'x':0,'y':0,'affected':True},
 {'id':3,'product':'P1','route':'R1','operation':'ETCH10','tool':'T1','chamber':'B','lot':'L0','wafer':'W0','cd':9.9,'x':-1,'y':0,'affected':False},
 {'id':4,'product':'P1','route':'R1','operation':'ETCH10','tool':'T1','chamber':'B','lot':'L0','wafer':'W0','cd':10.0,'x':0,'y':0,'affected':False},
)

def build_analysis():
    schema=DataSchema(tuple(SemanticField(k,type=(FieldType.FLOAT if k in {'cd','x','y'} else FieldType.BOOLEAN if k=='affected' else FieldType.INTEGER if k=='id' else FieldType.STRING),role=(FieldRole.MEASUREMENT if k=='cd' else FieldRole.IDENTIFIER if k=='id' else FieldRole.DIMENSION)) for k in ROWS[0]),key='id')
    source=InMemoryDataSource('process',ROWS,schema=schema)
    context=AnalysisContext(source_key='process'); selections=SelectionBus(); coordinator=AnalysisCoordinator(context,selections); semi=SemiconductorAnalysisContext(context)
    semi.set_many(product='P1',route='R1',operation='ETCH10')
    context.set_affected(PopulationDefinition('affected',filter=Comparison('chamber',ComparisonOperator.EQ,'A')))
    context.set_control(PopulationDefinition('control',filter=Comparison('chamber',ComparisonOperator.EQ,'B')))
    affected=[r['cd'] for r in ROWS if r['affected']]; control=[r['cd'] for r in ROWS if not r['affected']]
    amap=[WaferSample(r['x'],r['y'],r['cd'],wafer_id=r['wafer']) for r in ROWS if r['affected']]
    cmap=[WaferSample(r['x'],r['y'],r['cd'],wafer_id=r['wafer']) for r in ROWS if not r['affected']]
    spc=i_mr(affected+control); capability=capability_indices(affected+control,lsl=9.0,usl=11.0,target=10.0); delta=delta_wafer(amap,cmap)
    surfaces={key:SemiconductorAnalyticalSurface(key,context,selections) for key in ('spc_i_mr','capability_histogram','wafer_delta','rca_affected_control')}
    return {
        'source':source,'context':context,'selections':selections,'coordinator':coordinator,'semiconductor':semi,'surfaces':surfaces,
        'spc':spc,'capability':capability,'delta_wafer':delta,'radial':radial_profile(amap,bins=2),'records':ROWS,
        'visuals':{
            'spc':control_chart_visual(spc,lsl=9.0,usl=11.0,target=10.0,baseline_period='control population'),
            'capability':capability_histogram_visual(affected+control,lsl=9.0,usl=11.0,target=10.0,bins=4),
            'affected_control':affected_control_visual(affected,control),
            'wafer_delta_points':wafer_points(delta),
        },
    }
