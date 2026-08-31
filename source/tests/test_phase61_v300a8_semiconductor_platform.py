from __future__ import annotations

import asyncio
import math

import pytest

from nicegui_base import (
    AnalysisContext, Comparison, ComparisonOperator, DataSchema, FieldRole, FieldType, InMemoryDataSource,
    PopulationDefinition, SelectionBus, SemanticField,
)
from nicegui_base.semiconductor import *


def test_wave61_entity_genealogy_is_typed_and_explicit():
    fab=Fab('F1','Fab 1'); area=Area('ETCH','Etch',fab_id=fab.identifier); tool=Tool('T01','Tool 1',area_id=area.identifier); chamber=Chamber('C1','Chamber 1',tool_id=tool.identifier)
    lot=Lot('L1','Lot 1',product_id='P1',route_id='R1'); wafer=Wafer('W01','Wafer 1',lot_id=lot.identifier,slot=1); die=Die('D1','Die',wafer_id=wafer.identifier,die_x=3,die_y=-2)
    assert relationship_fields(chamber)==('tool_id','module_id')
    assert wafer.lot_id=='L1' and die.wafer_id=='W01'
    assert SemiconductorEntityKind.FAB.value=='fab'
    with pytest.raises(ValueError):
        Area('BAD','Missing Fab')
    with pytest.raises(ValueError):
        RecipeVersion('RV1','Bad Recipe Version',recipe_id='RCP1',version='')


def test_wave61_semiconductor_context_reuses_wave60_analysis_context():
    base=AnalysisContext(); base.add_filter(Comparison('site',ComparisonOperator.EQ,'A')); semi=SemiconductorAnalysisContext(base)
    semi.set('product','P1'); semi.set('route','R1'); semi.set('operation','OP10')
    assert semi.context is base and semi.values=={'product':'P1','route':'R1','operation':'OP10'}
    assert any(isinstance(f,Comparison) and f.field=='site' for f in base.filters)
    semi.set('product','P2')
    assert semi.values=={'product':'P2'} and not any(isinstance(f,Comparison) and f.field in {'route','operation'} for f in base.filters)
    # Equal-looking filters owned by another Wave 60 controller remain untouched.
    external=Comparison('product',ComparisonOperator.EQ,'P2'); base.add_filter(external)
    semi.set('product','P3')
    assert any(f is external for f in base.filters)


def test_wave61_semiconductor_context_persists_and_rehydrates_through_wave60_snapshot():
    base=AnalysisContext(); semi=SemiconductorAnalysisContext(base); before=base.revision
    semi.set_many(product='P1',route='R1',operation='OP10')
    assert base.revision==before+1 and base.metadata['semiconductor_context']['operation']=='OP10'
    snapshot=base.snapshot()
    restored=AnalysisContext(); live=SemiconductorAnalysisContext(restored); restored.restore(snapshot)
    assert live.values=={'product':'P1','route':'R1','operation':'OP10'}
    assert any(isinstance(f,Comparison) and f.field=='operation' and f.value=='OP10' for f in restored.filters)
    live.close(); semi.close(); restored.close(); base.close()


def test_wave61_population_roles_stay_on_analysis_context():
    base=AnalysisContext(); semi=SemiconductorAnalysisContext(base); pop=PopulationDefinition('affected',filter=Comparison('lot',ComparisonOperator.EQ,'L1'))
    semi.population('affected',pop); assert base.affected is pop


def test_wave61_dependent_filters_use_datasource_distinct_and_ancestor_constraints():
    schema=DataSchema((SemanticField('product',type=FieldType.STRING,role=FieldRole.ENTITY),SemanticField('route',type=FieldType.STRING),SemanticField('operation',type=FieldType.STRING)),key='operation')
    rows=({'product':'P1','route':'R1','operation':'A'},{'product':'P1','route':'R1','operation':'B'},{'product':'P1','route':'R2','operation':'C'},{'product':'P2','route':'R9','operation':'Z'})
    source=InMemoryDataSource('mfg',rows,schema=schema); semi=SemiconductorAnalysisContext(AnalysisContext()); filters=ManufacturingFilterController(source,semi)
    filters.set('product','P1'); assert asyncio.run(filters.options('route'))==('R1','R2')
    filters.set('route','R1'); assert asyncio.run(filters.options('operation'))==('A','B')
    asyncio.run(source.aclose())


@pytest.mark.parametrize('fn,args',[
    (i_mr,([1,1.1,1.2,1.1,1.0],)),
    (xbar_r,([[1,2,1],[2,2,3],[1,2,2]],)),
    (xbar_s,([[1,2,1],[2,2,3],[1,2,2]],)),
    (p_chart,([1,2,1],[100,100,100])),
    (np_chart,([1,2,1],100)),
    (c_chart,([2,3,1,2],)),
    (u_chart,([2,3,1,2],[10,12,9,11])),
    (ewma,([1,1.1,1.2,1.0],)),
    (cusum,([1,1.1,1.2,1.0],)),
])
def test_wave61_all_requested_spc_families_compute(fn,args):
    result=fn(*args); assert result.values and len(result.center)==len(result.values) and len(result.ucl)==len(result.values) and len(result.lcl)==len(result.values)


def test_wave61_spc_rule_sigma_and_variable_opportunity_are_statistically_aligned():
    xr=xbar_r([[1,2,1],[2,2,3],[1,2,2],[8,8,9]])
    assert xr.metadata['mean_standard_error']==pytest.approx(xr.sigma/math.sqrt(3))
    xs=xbar_s([[1,2,1],[2,2,3],[1,2,2],[8,8,9]])
    assert xs.metadata['sigma_method']=='Sbar/c4' and 0 < xs.metadata['c4'] < 1
    p=p_chart([0,1,9,1],[10,100,10,100])
    u=u_chart([0,1,9,1],[10,100,10,100])
    assert p.metadata['standardized_rule_evaluation'] is True
    assert u.metadata['standardized_rule_evaluation'] is True


def test_wave61_spc_missing_nonfinite_and_degenerate_inputs_are_explicit():
    r=i_mr([1,None,float('nan'),2,3]); assert r.excluded_indices==(1,2)
    with pytest.raises(SPCInputError): i_mr([None,float('nan')])
    with pytest.raises(SPCInputError): xbar_r([[1,2],[1,2,3]])
    with pytest.raises(SPCInputError): np_chart([1,2],[10,20])
    with pytest.raises(SPCInputError): cusum([1,1,1,1])


def test_wave61_western_electric_and_nelson_rules_detect_behavioral_patterns():
    we=detect_western_electric([0,0,0,4],0,1); assert any(v.rule=='WE1' for v in we)
    nel=detect_nelson(list(range(7)),0,10); assert any(v.rule=='N3' for v in nel)
    nel2=detect_nelson([1]*9,0,1); assert any(v.rule=='N2' for v in nel2)


def test_wave61_capability_indices_and_distribution_helpers():
    cap=capability_indices([9,10,11,10,10.5],lsl=7,usl=13,target=10)
    assert cap.cp and cap.cpk and cap.pp and cap.ppk and cap.cpk<=cap.cp
    assert cap.within_method=='moving_range' and cap.overall_method=='sample_stdev'
    assert len(ecdf([3,1,2]))==3 and len(qq_points([1,2,3,4]))==4 and sum(x[2] for x in capability_histogram([1,2,3,4],2))==4
    box=box_distribution([1,2,3,4,5]); assert box.median==3 and box.minimum==1 and box.maximum==5
    density=density_estimate([1,2,3,4,5],points=32); assert len(density)==32 and all(point.density>=0 for point in density)
    ridges=ridge_distributions({'A':[1,2,3],'B':[2,3,4]},points=16); assert set(ridges)=={'A','B'}
    with pytest.raises(SPCInputError): capability_indices([1,1],lsl=2,usl=1)


def _wafer(scale=1.0,wafer='W1'):
    return [WaferSample(x,y,(x*x+y*y)*scale,wafer_id=wafer,defect_class='particle' if x==y==0 else None) for x,y in [(-1,0),(0,0),(1,0),(0,1),(0,-1)]]


def test_wave61_wafer_spatial_library_has_delta_radial_ring_sector_center_edge_and_contour():
    a=_wafer(2); c=_wafer(1); d=delta_wafer(a,c)
    assert len(d)==5 and d[0].value==1
    assert len(radial_profile(a,bins=3))==3 and len(ring_analysis(a,rings=4))==4 and len(sector_analysis(a,sectors=4))==4
    ce=center_edge_decomposition(a); assert ce['center_count']>0 and ce['edge_count']>0
    assert len(contour_grid(a,cells=4))==4 and wafer_comparison(a,c)['delta']>0


def test_wave61_wafer_lot_strip_and_defect_clusters():
    pts=[WaferSample(0,0,1,wafer_id='W1',defect_class='d'),WaferSample(.5,.5,2,wafer_id='W1',defect_class='d'),WaferSample(5,5,3,wafer_id='W2',defect_class='d')]
    assert set(lot_wafer_strip(pts))=={'W1','W2'}
    assert defect_clusters(pts,radius=1,min_points=2)==((0,1),)


def test_wave61_fdc_step_alignment_envelope_and_fingerprints():
    traces={'t1':[TraceSample(2,2,'s','B'),TraceSample(1,1,'s','A')]}; aligned=align_recipe_steps(traces)
    assert list(aligned['t1'])==['A','B']
    env=golden_trace_envelope([[1,2,3],[1,2.2,2.8]]); assert len(env)==3 and env[1].lower<=env[1].mean<=env[1].upper
    rows=[{'chamber':'A','f1':1.0,'f2':2.0},{'chamber':'A','f1':2.0,'f2':4.0},{'chamber':'B','f1':4.0,'f2':8.0}]
    assert chamber_fingerprint(rows,['f1','f2'])['A']['f1']==1.5
    assert len(normalized_fingerprint(rows,['f1','f2']))==3
    sensors=multi_sensor_panel([TraceSample(2,2,'s2'),TraceSample(1,1,'s1'),TraceSample(3,3,'s1')]); assert [x.time for x in sensors['s1']]==[1,3]
    aligned_events=align_trace_events(sensors['s1'],[TraceEvent(2.8,'alarm','alarm')],max_offset=.5); assert aligned_events[0].sample_index==1


def test_wave61_pca_scores_loadings_t2_and_spe_are_directly_testable():
    result=pca([[1,2,1],[2,4,1.1],[3,6,1.2],[4,8,1.4]],components=2)
    assert len(result.loadings)==2 and len(result.scores)==4 and len(hotelling_t2(result))==4 and len(spe_q(result))==4
    assert all(v>=0 for v in result.t2) and all(v>=0 for v in result.spe)
    with pytest.raises(ValueError): pca([[1,2]])


def test_wave61_rca_enrichment_commonality_and_population_artifacts():
    affected=[{'tool':'T1','chamber':'A','x':1.0},{'tool':'T1','chamber':'A','x':2.0},{'tool':'T2','chamber':'B','x':3.0}]
    control=[{'tool':'T2','chamber':'B','x':1.0},{'tool':'T2','chamber':'C','x':1.5},{'tool':'T1','chamber':'C','x':2.0}]
    rank=commonality_ranking(affected,control,['tool','chamber']); assert rank and rank[0].factor in {'tool','chamber'}
    matrix=commonality_matrix(affected,control,['tool']); assert 'tool' in matrix
    assert contribution_waterfall(rank)[0]['end']==rank[0].score
    corr=correlation_matrix([{'x':1,'y':2},{'x':2,'y':4},{'x':3,'y':6}],['x','y']); assert corr['x']['y']==pytest.approx(1)
    pop=population_comparison(affected,control,'x'); assert pop.delta==pytest.approx(.5) and pop.affected_count==3
    with pytest.raises(ValueError): correlation_matrix([{'x':float('nan'),'y':1}],['x','y'])


def test_wave61_rca_graph_evidence_tree_and_sankey():
    rows=[{'lot':'L1','tool':'T1','chamber':'A'},{'lot':'L2','tool':'T1','chamber':'B'}]
    assert genealogy_graph(rows,['lot','tool','chamber'])
    assert cause_tree('yield',{'equipment':['chamber'],'process':['recipe']})
    assert fault_tree('fail',{'OR':['a','b']})
    assert sankey_process_flow(rows,['lot','tool','chamber'])
    repeated=sankey_process_flow([{'lot':'L1','tool':'T1'},{'lot':'L1','tool':'T1'}],['lot','tool']); assert repeated[0].weight==2
    m=evidence_matrix(['H1'],[{'hypothesis':'H1','key':'e1','direction':-1,'strength':.5}]); assert m['H1']['e1']==-.5


def test_wave61_yield_reliability_and_doe_analytics():
    p=yield_pareto([{'bin':'B1','count':3},{'bin':'B2','count':7},{'bin':'B1','count':2}]); assert p[0]['category']=='B2' and p[-1]['cumulative']==1
    assert bin_pareto([{'bin':'B1','count':1}])[0]['value']==1
    assert yield_waterfall([('defect',-2),('parametric',-1)],start=95)[-1]['end']==92
    w=weibull_analysis([10,12,15,20,25]); assert w.beta>0 and w.eta>0 and 0<=w.r2<=1 and w.failures==5 and w.censored==0
    wc=weibull_analysis([10,12,15,20,25],failures=[True,False,True,True,False]); assert wc.censored==2 and 0<wc.reliability(15)<1
    rows=[{'A':-1,'B':-1,'y':1},{'A':-1,'B':1,'y':2},{'A':1,'B':-1,'y':3},{'A':1,'B':1,'y':6},{'A':0,'B':0,'y':2.5},{'A':.5,'B':0,'y':3.1},{'A':0,'B':.5,'y':2.8}]
    assert set(doe_main_effects(rows,['A','B'],'y'))=={'A','B'}
    assert doe_interactions(rows,'A','B','y')
    rs=response_surface(rows,'A','B','y'); assert len(rs.coefficients)==6 and math.isfinite(rs.predict(.2,.3))


def test_wave61_surface_registry_meets_scope_counts_and_machine_guidance():
    reg=SEMICONDUCTOR_SURFACE_REGISTRY
    counts={cat:sum(v.category==cat for v in reg.values()) for cat in {'wafer','fdc','rca','yield','reliability','doe'}}
    assert counts['wafer']>=10 and counts['fdc']>=8 and counts['rca']>=6 and counts['yield']+counts['reliability']+counts['doe']>=6
    assert get_semiconductor_surface('wafer_delta').spatial
    assert any('spatial process change' in text.lower() for text in get_semiconductor_surface('wafer_delta').use_when)
    assert all(definition.avoid_when for definition in reg.values())


def test_wave61_every_surface_uses_shared_context_selection_and_panel_state_contract():
    context=AnalysisContext(); bus=SelectionBus()
    for key in SEMICONDUCTOR_SURFACE_REGISTRY:
        surface=SemiconductorAnalyticalSurface(key,context,bus)
        assert surface.context is context and surface.selections is bus
        assert surface.loading().status.value=='loading'; assert surface.stale('source changed').status.value=='stale'; assert surface.ready().status.value=='ready'
    bus.close(); context.close()


def test_wave61_surface_selection_crossfilters_through_wave60_bus_and_coordinator():
    from nicegui_base import AnalysisCoordinator, SelectionKind
    context=AnalysisContext(); bus=SelectionBus(); coord=AnalysisCoordinator(context,bus); s=SemiconductorAnalyticalSurface('wafer_delta',context,bus)
    f=Comparison('chamber',ComparisonOperator.EQ,'B'); s.select(SelectionKind.WAFER,'W1',{'filter':f,'wafer':'W1'})
    assert f in context.filters; coord.close(); bus.close(); context.close()


def test_wave61_spc_visual_plan_reuses_certified_chart_contract_with_limits_events_and_metadata():
    plan=control_chart_visual(i_mr([10,10.1,10.2,10.0]),lsl=9,usl=11,target=10,event_overlays=[(1,'PM completed')],limit_version='L2',baseline_period='pre-PM')
    assert plan.spec.kind.value=='control' and plan.spec_limits.lower==9 and plan.spec_limits.upper==11 and plan.spec_limits.target==10
    assert {s.key for s in plan.series}=={'value','ucl','center','lcl'}
    assert plan.annotations[0].label=='PM completed' and plan.metadata['limit_version']=='L2' and plan.metadata['baseline_period']=='pre-PM'


def test_wave61_wafer_adapter_reuses_existing_waferpoint_contract():
    points=wafer_points([WaferSample(1,2,3,wafer_id='W1',category='pass')]); assert points[0].x==1 and points[0].metadata['wafer_id']=='W1'


def test_wave61_agent_intelligence_routes_semiconductor_jobs_to_domain_registry_and_golden_workflows():
    from nicegui_base import build_agent_context
    drift=build_agent_context('is chamber B drifting after PM with FDC and SPC')
    assert any(r.category=='semiconductor' for r in drift.recommendations)
    assert 'examples/phase61_fdc_tool_health.py' in drift.golden_examples
    spatial=build_agent_context('where on wafer did the process change')
    assert any(r.category=='semiconductor' for r in spatial.recommendations)
    assert 'examples/phase61_spc_wafer_investigation.py' in spatial.golden_examples
    rca=build_agent_context('RCA commonality for an excursion')
    assert 'examples/phase61_rca_commonality.py' in rca.golden_examples


def test_wave61_chart_export_contract_exposes_copy_data_without_new_dependency():
    from nicegui_base.integrations.nicegui_visualization import ChartExport
    assert hasattr(ChartExport,'copy_csv')


def test_wave61_set_many_is_dependency_order_independent_and_keeps_explicit_descendants():
    left=AnalysisContext(); right=AnalysisContext()
    a=SemiconductorAnalysisContext(left); b=SemiconductorAnalysisContext(right)
    a.set_many(product='P1',route='R1',operation='OP10')
    b.set_many(operation='OP10',route='R1',product='P1')
    assert a.values==b.values=={'product':'P1','route':'R1','operation':'OP10'}
    a.set_many(product='P2',operation='OP20')
    assert a.values=={'product':'P2','operation':'OP20'} and 'route' not in a.values
    a.close(); b.close(); left.close(); right.close()


def test_wave61_dependent_filter_options_preserve_unrelated_wave60_context():
    schema=DataSchema((
        SemanticField('site',type=FieldType.STRING),SemanticField('product',type=FieldType.STRING),
        SemanticField('route',type=FieldType.STRING),SemanticField('operation',type=FieldType.STRING),
    ),key='operation')
    rows=(
        {'site':'A','product':'P1','route':'R1','operation':'A1'},
        {'site':'A','product':'P1','route':'R2','operation':'A2'},
        {'site':'B','product':'P1','route':'R9','operation':'B9'},
    )
    source=InMemoryDataSource('mfg-context',rows,schema=schema)
    base=AnalysisContext(); base.add_filter(Comparison('site',ComparisonOperator.EQ,'A'))
    semi=SemiconductorAnalysisContext(base); filters=ManufacturingFilterController(source,semi)
    filters.set('product','P1')
    assert asyncio.run(filters.options('route'))==('R1','R2')
    semi.close(); base.close(); asyncio.run(source.aclose())


def test_wave61_analytics_reject_malformed_or_nonfinite_inputs_explicitly():
    with pytest.raises(SPCInputError): xbar_r([[1,2],[3,float('nan')]])
    with pytest.raises(SPCInputError): p_chart([1.5],[100])
    with pytest.raises(ValueError): golden_trace_envelope([[1,2],[1]])
    with pytest.raises(ValueError): golden_trace_envelope([[1,float('nan')],[1,2]])
    with pytest.raises(ValueError): yield_pareto([{'bin':'B1','count':-1}])
    with pytest.raises(ValueError): doe_main_effects([{'A':1,'y':float('inf')}],['A'],'y')
    with pytest.raises(ValueError): evidence_matrix(['H1'],[{'hypothesis':'H2','key':'e','strength':1}])
    with pytest.raises(ValueError): SPCParameter('P','Param',lsl=10,usl=9)


def test_wave61_ewma_marks_dynamic_control_limit_violations():
    result=ewma([0,0.1,-0.1,0,10],target=0,lambda_=1.0,L=2.0)
    assert any(v.rule=='EWMA' and 4 in v.indices for v in result.violations)


def test_wave61_fault_tree_preserves_gate_semantics():
    edges=fault_tree('failure',{'OR':['sensor','rf'],'AND':['pressure','flow']})
    assert any(edge.target=='gate:OR' and edge.label=='gate' and edge.metadata['gate']=='OR' for edge in edges)
    assert any(edge.source=='gate:AND' and edge.label=='condition' for edge in edges)


def test_wave61_visual_plans_cover_semiconductor_analytical_families():
    cap=capability_histogram_visual([1,2,3,4],bins=2,lsl=0,usl=5,target=2.5)
    qq=qq_probability_visual([1,2,3,4]); cdf=ecdf_visual([1,2,3,4])
    box=box_distribution_visual({'A':[1,2,3],'B':[2,3,4]})
    density=distribution_density_visual({'A':[1,2,3],'B':[2,3,4]},mode='ridge',points=16)
    samples=[TraceSample(0,1,'pressure'),TraceSample(1,1.2,'pressure')]
    fdc=fdc_trace_visual(samples,envelope=golden_trace_envelope([[1,1.2],[1,1.1]]))
    pc=pca([[1,2],[2,4.1],[3,5.9],[4,8.2]],components=2)
    scores=pca_scores_visual(pc); loadings=pca_loadings_visual(pc)
    ranking=commonality_ranking([{'tool':'T1'}],[{'tool':'T2'}],['tool'])
    common=commonality_ranking_visual(ranking)
    matrix=matrix_visual({'tool':{'T1':1.5,'T2':.5}})
    pareto=pareto_visual(yield_pareto([{'bin':'B1','count':3},{'bin':'B2','count':1}]))
    assert cap.spec.kind.value=='histogram' and cap.spec_limits.target==2.5
    assert qq.series and cdf.series and box.series and density.series and fdc.series
    assert scores.series and loadings.series and common.series and matrix.series and pareto.series


def test_wave61_machine_catalog_matches_runtime_registry_and_has_negative_guidance():
    from nicegui_base import load_framework_catalog
    catalog=load_framework_catalog(); entries=catalog['registries']['semiconductor']
    assert {entry['_registry_key'] for entry in entries}==set(SEMICONDUCTOR_SURFACE_REGISTRY)
    assert all(entry['avoid_when'] for entry in entries)
    assert catalog['registry_counts']['semiconductor']==len(SEMICONDUCTOR_SURFACE_REGISTRY)


def test_wave61_integrated_golden_examples_execute_and_share_context_contracts():
    from examples.phase61_spc_wafer_investigation import build_analysis as build_spc
    from examples.phase61_fdc_tool_health import build_analysis as build_fdc
    from examples.phase61_rca_commonality import build_analysis as build_rca
    for builder in (build_spc,build_fdc,build_rca):
        result=builder()
        assert result['visuals'] and result['surfaces']
        assert all(surface.context is result['context'] and surface.selections is result['selections'] for surface in result['surfaces'].values())
        for surface in result['surfaces'].values(): surface.close()
        if 'source' in result: asyncio.run(result['source'].aclose())
        result['semiconductor'].close(); result['coordinator'].close(); result['selections'].close(); result['context'].close()
