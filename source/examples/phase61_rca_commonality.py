"""Wave 61 golden workflow: RCA/commonality using shared affected/control populations and genealogy."""
from __future__ import annotations
from nicegui_base import AnalysisCoordinator, AnalysisContext, Comparison, ComparisonOperator, PopulationDefinition, SelectionBus
from nicegui_base.semiconductor import (
    SemiconductorAnalysisContext, SemiconductorAnalyticalSurface, affected_control_visual,
    commonality_matrix, commonality_ranking, commonality_ranking_visual, genealogy_graph,
    matrix_visual, population_comparison, sankey_process_flow,
)

def build_analysis():
    context=AnalysisContext(source_key='history'); selections=SelectionBus(); coordinator=AnalysisCoordinator(context,selections); semi=SemiconductorAnalysisContext(context)
    affected=({'lot':'L1','tool':'T1','chamber':'A','recipe':'R7','metric':2.4},{'lot':'L2','tool':'T1','chamber':'A','recipe':'R7','metric':2.1})
    control=({'lot':'L3','tool':'T2','chamber':'B','recipe':'R7','metric':1.1},{'lot':'L4','tool':'T2','chamber':'C','recipe':'R6','metric':1.0})
    context.set_affected(PopulationDefinition('affected',filter=Comparison('lot',ComparisonOperator.EQ,'L1'))); context.set_control(PopulationDefinition('control'))
    semi.set('recipe','R7'); ranking=commonality_ranking(affected,control,['tool','chamber','recipe']); matrix=commonality_matrix(affected,control,['tool','chamber','recipe'])
    surfaces={key:SemiconductorAnalyticalSurface(key,context,selections) for key in ('rca_affected_control','rca_commonality_ranking','rca_commonality_matrix','rca_genealogy_graph','rca_sankey')}
    return {
        'context':context,'selections':selections,'coordinator':coordinator,'semiconductor':semi,'surfaces':surfaces,
        'ranking':ranking,'matrix':matrix,'population':population_comparison(affected,control,'metric'),
        'genealogy':genealogy_graph(affected+control,['lot','tool','chamber','recipe']),'flow':sankey_process_flow(affected+control,['lot','tool','chamber','recipe']),
        'visuals':{
            'ranking':commonality_ranking_visual(ranking),
            'matrix':matrix_visual(matrix),
            'affected_control':affected_control_visual([r['metric'] for r in affected],[r['metric'] for r in control]),
        },
    }
