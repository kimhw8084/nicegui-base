"""Wave 61 golden workflow: tool/chamber FDC analysis with shared selection/context."""
from __future__ import annotations
from nicegui_base import AnalysisCoordinator, AnalysisContext, SelectionBus
from nicegui_base.semiconductor import (
    SemiconductorAnalysisContext, SemiconductorAnalyticalSurface, TraceEvent, TraceSample,
    align_recipe_steps, align_trace_events, chamber_fingerprint, fdc_trace_visual,
    golden_trace_envelope, pca, pca_loadings_visual, pca_scores_visual,
)

def build_analysis():
    context=AnalysisContext(source_key='fdc'); selections=SelectionBus(); coordinator=AnalysisCoordinator(context,selections); semi=SemiconductorAnalysisContext(context); semi.set('tool','T1')
    traces={'A1':(TraceSample(0,1.0,'pressure','step1','T1','A'),TraceSample(1,1.2,'pressure','step2','T1','A')),'B1':(TraceSample(0,1.0,'pressure','step1','T1','B'),TraceSample(1,1.8,'pressure','step2','T1','B'))}
    rows=({'chamber':'A','pressure':1.2,'rf':10.0},{'chamber':'A','pressure':1.1,'rf':10.2},{'chamber':'B','pressure':1.8,'rf':12.5},{'chamber':'B','pressure':1.7,'rf':12.2})
    golden=golden_trace_envelope([[1.0,1.2],[1.0,1.1]]); pc=pca([[r['pressure'],r['rf']] for r in rows],components=2)
    trace=traces['B1']; events=align_trace_events(trace,[TraceEvent(1.0,'PM completed','maintenance')],max_offset=.2)
    surfaces={key:SemiconductorAnalyticalSurface(key,context,selections) for key in ('fdc_recipe_step_trace','fdc_golden_envelope','fdc_chamber_fingerprint','fdc_pca_scores','fdc_pca_loadings')}
    return {
        'context':context,'selections':selections,'coordinator':coordinator,'semiconductor':semi,'surfaces':surfaces,
        'aligned':align_recipe_steps(traces),'golden':golden,'fingerprint':chamber_fingerprint(rows,['pressure','rf']),'pca':pc,
        'visuals':{'trace':fdc_trace_visual(trace,envelope=golden,events=events),'pca_scores':pca_scores_visual(pc),'pca_loadings':pca_loadings_visual(pc)},
    }
