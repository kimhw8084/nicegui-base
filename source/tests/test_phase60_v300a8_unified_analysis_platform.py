from __future__ import annotations

import asyncio
from datetime import date, datetime
from decimal import Decimal

import pytest

from nicegui_base import (
    AnalysisBinding, AnalysisContext, AnalysisCoordinator, AnalysisStatus, AnalyticalPanelController,
    And, ApplicationRuntime, Between, ColumnKind, Comparison, ComparisonOperator, DataSchema,
    EntityContext, FieldRole, FieldType, FilterGroup, FilterLogic, FilterOperator, FilterSpec,
    InMemoryDataSource, PanelSpec, PopulationDefinition, Query, Selection, SelectionBus,
    SelectionKind, SelectionMutationMode, SemanticField, SortDirection, SortSpec, TableQuery, TimeRange,
    WorkspaceBreakpoint, WorkspaceController, columns_from_schema, deserialize_application_snapshot,
    query_data_source_table, serialize_application_snapshot, table_filter_to_query, table_query_to_source,
)


ROWS = (
    {'id': 1, 'area': 'ETCH', 'chamber': 'A', 'cd': 12.0},
    {'id': 2, 'area': 'ETCH', 'chamber': 'B', 'cd': 14.0},
    {'id': 3, 'area': 'CVD', 'chamber': 'A', 'cd': 9.0},
    {'id': 4, 'area': 'CVD', 'chamber': 'C', 'cd': 15.0},
)


def schema() -> DataSchema:
    return DataSchema((
        SemanticField('id', type=FieldType.INTEGER, role=FieldRole.IDENTIFIER),
        SemanticField('area', type=FieldType.CATEGORY, role=FieldRole.DIMENSION),
        SemanticField('chamber', type=FieldType.CATEGORY, role=FieldRole.ENTITY),
        SemanticField('cd', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT, unit='nm'),
    ), key='id')


def test_wave60_context_revision_and_watchers_are_atomic():
    context = AnalysisContext(); revisions=[]; context.watch(lambda item: revisions.append(item.revision))
    with context.transaction():
        context.set_search('etch'); context.set_source('fab'); context.set_metadata({'owner':'PE'})
    assert context.revision == 1 and revisions == [1]


def test_wave60_context_transaction_rolls_back():
    context=AnalysisContext(); context.set_search('stable'); revision=context.revision
    with pytest.raises(RuntimeError):
        with context.transaction():
            context.set_search('broken'); context.set_source('source'); raise RuntimeError('boom')
    assert context.search == 'stable' and context.source_key is None and context.revision == revision


def test_wave60_context_close_rejects_mutation_and_watch():
    context=AnalysisContext(); context.close()
    with pytest.raises(RuntimeError): context.set_search('x')
    with pytest.raises(RuntimeError): context.watch(lambda _:None)


def test_wave60_context_builds_effective_filter_with_time_population():
    context=AnalysisContext(); context.add_filter(Comparison('area',ComparisonOperator.EQ,'ETCH'))
    context.set_time_range(TimeRange('id',1,3))
    pop=PopulationDefinition('affected',filter=Comparison('chamber',ComparisonOperator.EQ,'A'))
    result=context.effective_filter(population=pop)
    assert isinstance(result,And) and len(result.terms)==3


def test_wave60_context_merges_base_query_and_search():
    context=AnalysisContext(); context.set_search('abc'); context.add_filter(Comparison('area',ComparisonOperator.EQ,'ETCH'))
    query=context.query(Query(filter=Comparison('cd',ComparisonOperator.GT,10),limit=5))
    assert isinstance(query.filter,And) and query.search=='abc' and query.limit==5


def test_wave60_context_snapshot_restore():
    context=AnalysisContext(source_key='source'); context.set_entity(EntityContext('chamber','A')); snap=context.snapshot()
    context.set_entity(EntityContext('chamber','B')); context.restore(snap)
    assert context.entity.entity_id=='A'


def test_wave60_selection_replace_add_remove_clear():
    bus=SelectionBus(); a=Selection(SelectionKind.ENTITY,'A'); b=Selection(SelectionKind.ENTITY,'B')
    bus.apply(a); bus.apply(b,mode=SelectionMutationMode.ADD); assert [x.selection_id for x in bus.selections]==['A','B']
    bus.apply(a,mode=SelectionMutationMode.REMOVE); assert [x.selection_id for x in bus.selections]==['B']
    bus.clear(); assert bus.selections==()


def test_wave60_selection_deduplicates_add_by_typed_identity():
    bus=SelectionBus(); a=Selection(SelectionKind.ROW,'1'); bus.apply(a); bus.apply(a,mode=SelectionMutationMode.ADD)
    assert len(bus.selections)==1


def test_wave60_selection_drill_and_back():
    bus=SelectionBus(); bus.apply(Selection(SelectionKind.ENTITY,'tool'))
    bus.drill(Selection(SelectionKind.ENTITY,'chamber')); assert bus.can_go_back
    bus.back(); assert bus.selections[0].selection_id=='tool'


def test_wave60_selection_snapshot_restore():
    bus=SelectionBus(); bus.apply(Selection(SelectionKind.WAFER,'W1')); snap=bus.snapshot(); bus.clear(); bus.restore(snap,emit=False)
    assert bus.selections[0].kind is SelectionKind.WAFER and bus.revision==snap.revision


def test_wave60_selection_close_rejects_operations():
    bus=SelectionBus(); bus.close()
    with pytest.raises(RuntimeError): bus.clear()


def test_wave60_coordinator_applies_selection_filter_without_losing_base_filter():
    context=AnalysisContext(); base=Comparison('area',ComparisonOperator.EQ,'ETCH'); context.add_filter(base)
    bus=SelectionBus(); coordinator=AnalysisCoordinator(context,bus)
    selected=Comparison('chamber',ComparisonOperator.EQ,'A')
    bus.apply(Selection(SelectionKind.ENTITY,'A',{'filter':selected}))
    assert context.filters==(base,selected)
    bus.clear(); assert context.filters==(base,)
    coordinator.close()


def test_wave60_analysis_binding_refreshes_consumer():
    async def scenario():
        context=AnalysisContext(); values=[]
        binding=AnalysisBinding(context,lambda c:c.search,lambda value:values.append(value),auto=False)
        context.set_search('abc'); await binding.refresh(); await binding.aclose(); return values
    assert asyncio.run(scenario())==['abc']


def test_wave60_analysis_binding_latest_request_wins():
    async def scenario():
        context=AnalysisContext(); values=[]
        async def loader(c):
            value=c.search; await asyncio.sleep(.03 if value=='slow' else .001); return value
        binding=AnalysisBinding(context,loader,lambda value:values.append(value),auto=False)
        context.set_search('slow'); first=asyncio.create_task(binding.refresh()); await asyncio.sleep(.002)
        context.set_search('fast'); await binding.refresh()
        try: await first
        except asyncio.CancelledError: pass
        await binding.aclose(); return values
    assert asyncio.run(scenario())==['fast']


def test_wave60_panel_controller_state_machine():
    c=AnalyticalPanelController(); c.loading('query'); assert c.state.status is AnalysisStatus.LOADING
    c.stale('age','old'); assert c.state.status is AnalysisStatus.STALE and c.state.stale_reason=='age'
    c.error(ValueError('bad')); assert c.state.status is AnalysisStatus.ERROR and c.state.error_type=='ValueError'
    c.ready(); assert c.state.status is AnalysisStatus.READY and c.state.error_type is None


def test_wave60_table_filter_leaf_translation():
    result=table_filter_to_query(FilterSpec('cd',FilterOperator.BETWEEN,10,20))
    assert isinstance(result,Between) and result.lower==10 and result.upper==20


def test_wave60_table_filter_compound_or_is_preserved():
    group=FilterGroup(FilterLogic.OR,(FilterSpec('area',FilterOperator.EQUALS,'ETCH'),FilterSpec('area',FilterOperator.EQUALS,'CVD')))
    result=table_filter_to_query(group)
    assert result.__class__.__name__=='Or' and len(result.terms)==2


def test_wave60_table_query_translation_preserves_page_sort_and_context():
    context=AnalysisContext(); context.add_filter(Comparison('chamber',ComparisonOperator.EQ,'A'))
    table=TableQuery(page=2,page_size=25,sorts=(SortSpec('cd',SortDirection.DESC),),filters=(FilterSpec('area',FilterOperator.EQUALS,'ETCH'),))
    query=table_query_to_source(table,context=context)
    assert query.offset==25 and query.limit==25 and query.sorts[0].direction.value=='desc' and isinstance(query.filter,And)


def test_wave60_data_source_table_query_uses_shared_context():
    source=InMemoryDataSource('process',ROWS,schema=schema()); context=AnalysisContext(); context.add_filter(Comparison('area',ComparisonOperator.EQ,'ETCH'))
    result=asyncio.run(query_data_source_table(source,TableQuery(page=1,page_size=10),context=context))
    assert result.total==2 and [row['id'] for row in result.rows]==[1,2]


def test_wave60_schema_generates_table_columns():
    columns=columns_from_schema(schema()); by_key={item.key:item for item in columns}
    assert by_key['id'].kind is ColumnKind.INTEGER and by_key['cd'].kind is ColumnKind.FLOAT


def test_wave60_workspace_controller_register_and_state():
    c=WorkspaceController(); c.register_panel(PanelSpec('trend',metadata={'title':'Trend'}))
    assert c.state('trend').panel_id=='trend' and c.layout.placement('trend',WorkspaceBreakpoint.DESKTOP).column_span==6


def test_wave60_workspace_move_resize_undo_redo():
    c=WorkspaceController(); c.register_panel(PanelSpec('a')); before=c.layout.placement('a',WorkspaceBreakpoint.DESKTOP)
    c.resize('a',WorkspaceBreakpoint.DESKTOP,column_span=8,row_span=5); assert c.layout.placement('a',WorkspaceBreakpoint.DESKTOP).column_span==8
    assert c.undo(); assert c.layout.placement('a',WorkspaceBreakpoint.DESKTOP)==before
    assert c.redo(); assert c.layout.placement('a',WorkspaceBreakpoint.DESKTOP).column_span==8


def test_wave60_workspace_runtime_lock_blocks_geometry():
    c=WorkspaceController(); c.register_panel(PanelSpec('a')); c.lock('a',True)
    with pytest.raises(PermissionError): c.move('a',WorkspaceBreakpoint.DESKTOP,column=1,row=1)


def test_wave60_workspace_collapse_hide_dock_split_persist():
    from nicegui_base import DockPosition
    c=WorkspaceController(); c.register_panel(PanelSpec('a')); c.collapse('a'); c.hide('a'); c.dock('a',DockPosition.LEFT); c.split('a','left')
    state=c.state('a'); assert state.collapsed and state.hidden and state.dock is DockPosition.LEFT and state.split_group=='left'


def test_wave60_workspace_duplicate_creates_independent_panel():
    c=WorkspaceController(); c.register_panel(PanelSpec('a',metadata={'title':'A'})); clone=c.duplicate('a','a-copy')
    assert clone.panel_id=='a-copy' and set(c.layout.panels)=={'a','a-copy'}


def test_wave60_workspace_snapshot_restore_interactions():
    c=WorkspaceController(); c.register_panel(PanelSpec('a')); c.collapse('a'); snap=(c.layout.snapshot(),c.snapshot()); c.collapse('a',False)
    c.layout.restore(snap[0]); c.restore(snap[1],emit=False); assert c.state('a').collapsed


def test_wave60_runtime_owns_analysis_selection_workspace_controller():
    runtime=ApplicationRuntime(); ws=runtime.open_workspace('analysis')
    assert ws.workspace.layout is ws.layout and ws.analysis.source_key is None and ws.selections.selections==()
    asyncio.run(runtime.aclose()); assert ws.analysis.closed and ws.selections.closed


def test_wave60_runtime_snapshot_restores_complete_analysis_state():
    runtime=ApplicationRuntime(); ws=runtime.open_workspace('analysis'); ws.workspace.register_panel(PanelSpec('trend')); ws.workspace.collapse('trend')
    ws.analysis.set_search('etch'); ws.analysis.set_time_range(TimeRange('id',1,4)); ws.analysis.set_affected(PopulationDefinition('affected',filter=Comparison('area',ComparisonOperator.EQ,'ETCH')))
    ws.selections.apply(Selection(SelectionKind.ENTITY,'A',{'filter':Comparison('chamber',ComparisonOperator.EQ,'A')}))
    snap=runtime.snapshot(); ws.analysis.set_search('changed'); ws.workspace.collapse('trend',False); ws.selections.clear(); ws.restore(snap.workspaces[0])
    assert ws.analysis.search=='etch' and ws.workspace.state('trend').collapsed and ws.selections.selections[0].selection_id=='A'
    asyncio.run(runtime.aclose())


def test_wave60_json_persistence_roundtrips_analysis_decimal_date_datetime():
    runtime=ApplicationRuntime(); ws=runtime.open_workspace('analysis'); ws.workspace.register_panel(PanelSpec('trend'))
    ws.analysis.set_time_range(TimeRange('when',date(2026,1,1),date(2026,1,2)))
    ws.analysis.set_metadata({'limit':Decimal('1.25'),'created':datetime(2026,1,1,12,30)})
    text=serialize_application_snapshot(runtime.snapshot()); restored=deserialize_application_snapshot(text)
    analysis=restored.workspaces[0].analysis
    assert analysis.time_range.start==date(2026,1,1) and analysis.metadata['limit']==Decimal('1.25') and analysis.metadata['created']==datetime(2026,1,1,12,30)
    asyncio.run(runtime.aclose())


def test_wave60_json_persistence_backward_compatible_when_new_fields_absent():
    payload='{"schema_version":1,"state":{"revision":0,"values":{}},"workspaces":[{"schema_version":1,"workspace_id":"w","state":{"revision":0,"values":{}},"layout":{"schema_version":1,"revision":0,"panels":[],"placements":[]},"data_sessions":{}}]}'
    restored=deserialize_application_snapshot(payload)
    ws=restored.workspaces[0]; assert ws.analysis is None and ws.selections is None and ws.interactions is None
