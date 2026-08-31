from __future__ import annotations

import pytest

from nicegui_base import (
    Aggregation, ApplicationRuntime, DataEngine, DataQuery, Dataset, Dimension, FilterClause, FilterOperation,
    Metric, SortClause,
)
from nicegui_base.certification.pathological_data import engineering_rows

pytestmark=pytest.mark.asyncio


def manufacturing_dataset() -> Dataset:
    rows=(
        {'id':1,'region':'APAC','tool':'A','revenue':100.0,'yield':.91},
        {'id':2,'region':'APAC','tool':'B','revenue':150.0,'yield':.95},
        {'id':3,'region':'US','tool':'A','revenue':200.0,'yield':.89},
        {'id':4,'region':'EU','tool':'C','revenue':50.0,'yield':None},
    )
    return Dataset('manufacturing',rows,row_key='id',dimensions=(Dimension('region'),Dimension('tool')),metrics=(
        Metric('revenue',aggregation=Aggregation.SUM),
        Metric('avg_yield',field='yield',aggregation=Aggregation.AVG),
        Metric('rows',aggregation=Aggregation.COUNT),
        Metric('tools',field='tool',aggregation=Aggregation.COUNT_DISTINCT),
    ))


async def test_v3_one_filter_session_updates_rows_chart_groups_and_kpi_bindings_together():
    engine=DataEngine(); engine.register(manufacturing_dataset()); session=engine.session('manufacturing')
    table=session.bind(lambda s:s.rows(sorts=(SortClause('id'),)).rows)
    chart=session.bind(lambda s:s.aggregate(dimensions=('region',),metrics=('revenue',),sorts=(SortClause('region'),)).rows)
    kpi=session.bind(lambda s:s.metric('revenue'))
    revisions=[]; table.watch(lambda binding:revisions.append(('table',binding.revision)))
    chart.watch(lambda binding:revisions.append(('chart',binding.revision)))
    kpi.watch(lambda binding:revisions.append(('kpi',binding.revision)))
    session.set_filter(FilterClause('region',FilterOperation.EQUALS,'APAC'))
    assert [row['id'] for row in table.value] == [1,2]
    assert chart.value == ({'region':'APAC','revenue':250.0},)
    assert kpi.value == 250.0
    assert revisions == [('table',1),('chart',1),('kpi',1)]


async def test_v3_data_session_transaction_batches_crossfilters_into_one_revision():
    session=manufacturing_dataset(); engine=DataEngine(); engine.register(session); view=engine.session('manufacturing')
    calls=[]; view.watch(lambda s:calls.append(s.revision))
    with view.transaction():
        view.set_filter(FilterClause('region',FilterOperation.IN,('APAC','US')))
        view.set_filter(FilterClause('tool',FilterOperation.EQUALS,'A'))
        view.set_search('')
    assert view.revision == 1 and calls == [1]
    result=view.aggregate(dimensions=('region',),metrics=('revenue','avg_yield','rows'))
    assert result.rows == ({'region':'APAC','revenue':100.0,'avg_yield':.91,'rows':1},{'region':'US','revenue':200.0,'avg_yield':.89,'rows':1})


async def test_v3_dataset_grouping_handles_nulls_distinct_counts_and_paging_deterministically():
    dataset=manufacturing_dataset()
    grouped=dataset.query(DataQuery(dimensions=('region',),metrics=('revenue','avg_yield','tools'),sorts=(SortClause('revenue',descending=True),)))
    assert [row['region'] for row in grouped.rows] == ['APAC','US','EU']
    assert grouped.rows[-1]['avg_yield'] is None
    page=dataset.query(DataQuery(sorts=(SortClause('revenue',descending=True),),offset=1,limit=2))
    assert [row['id'] for row in page.rows] == [2,1] and page.total == 4 and page.filtered_total == 4


async def test_v3_dataset_and_result_rows_are_defensive_copies():
    source=[{'id':1,'nested':{'x':1}}]
    dataset=Dataset('copy',source,row_key='id'); source[0]['nested']['x']=9
    first=dataset.rows(); first[0]['nested']['x']=7
    assert dataset.rows()[0]['nested']['x'] == 1
    result=dataset.query(); result.rows[0]['nested']['x']=8
    assert dataset.query().rows[0]['nested']['x'] == 1


async def test_v3_filter_operations_cover_semantic_text_range_membership_and_empty_cases():
    dataset=Dataset('filters',(
        {'id':1,'name':'Alpha Tool','x':5,'tag':'A','note':''},
        {'id':2,'name':'Beta','x':10,'tag':'B','note':None},
        {'id':3,'name':'alphabet','x':15,'tag':'C','note':'ok'},
    ),row_key='id')
    cases=(
        (FilterClause('name',FilterOperation.CONTAINS,'alpha'),[1,3]),
        (FilterClause('name',FilterOperation.STARTS_WITH,'beta'),[2]),
        (FilterClause('x',FilterOperation.BETWEEN,6,15),[2,3]),
        (FilterClause('tag',FilterOperation.NOT_IN,('A','C')),[2]),
        (FilterClause('note',FilterOperation.IS_EMPTY),[1,2]),
    )
    for clause,expected in cases:
        assert [row['id'] for row in dataset.query(DataQuery(filters=(clause,))).rows] == expected


async def test_v3_runtime_workspace_owns_isolated_data_sessions_over_shared_dataset_authority():
    runtime=ApplicationRuntime(); runtime.data.register(manufacturing_dataset())
    left=runtime.open_workspace('left'); right=runtime.open_workspace('right')
    a=left.open_data_session('manufacturing'); b=right.open_data_session('manufacturing')
    a.set_filter(FilterClause('region',FilterOperation.EQUALS,'APAC'))
    b.set_filter(FilterClause('region',FilterOperation.EQUALS,'US'))
    assert a.metric('revenue') == 250.0 and b.metric('revenue') == 200.0
    diagnostics=runtime.diagnostics()
    assert diagnostics.registered_datasets == 1 and diagnostics.active_data_sessions == 2
    await runtime.close_workspace('left')
    assert a.closed and not b.closed and runtime.diagnostics().active_data_sessions == 1
    await runtime.aclose(); assert b.closed


async def test_v3_data_engine_handles_existing_50k_pathological_fixture_without_special_case_code():
    rows=engineering_rows(50_000)
    dataset=Dataset('large',rows,row_key='id',dimensions=(Dimension('tool'),),metrics=(Metric('rows',aggregation=Aggregation.COUNT),Metric('measurement',field='value',aggregation=Aggregation.AVG)))
    engine=DataEngine(); engine.register(dataset); session=engine.session('large')
    session.set_filter(FilterClause('status',FilterOperation.EQUALS,'Normal'))
    grouped=session.aggregate(dimensions=('tool',),metrics=('rows','measurement'))
    assert grouped.filtered_total and grouped.filtered_total > 10_000
    assert sum(row['rows'] for row in grouped.rows) == grouped.filtered_total


async def test_v3_data_session_snapshot_restore_rehydrates_filter_state_and_updates_bindings_once():
    engine=DataEngine(); engine.register(manufacturing_dataset()); session=engine.session('manufacturing')
    session.set_filter(FilterClause('region',FilterOperation.EQUALS,'APAC')); snapshot=session.snapshot()
    session.set_filter(FilterClause('region',FilterOperation.EQUALS,'EU')); session.set_search('C')
    calls=[]; binding=session.bind(lambda s:s.metric('revenue')); binding.watch(lambda b:calls.append(b.revision))
    session.restore(snapshot)
    assert session.filters == snapshot.filters and session.search == '' and binding.value == 250.0
    assert calls == [session.revision]

async def test_v3_dataset_builds_lazy_equality_indexes_without_changing_row_order_or_semantics():
    dataset=manufacturing_dataset()
    assert dataset.indexed_fields == frozenset()
    result=dataset.query(DataQuery(filters=(FilterClause('region',FilterOperation.EQUALS,'APAC'),),sorts=(SortClause('id'),)))
    assert [row['id'] for row in result.rows] == [1,2]
    assert dataset.indexed_fields == frozenset({'region'})
    second=dataset.query(DataQuery(filters=(FilterClause('region',FilterOperation.IN,('US','APAC')),),sorts=(SortClause('id'),)))
    assert [row['id'] for row in second.rows] == [1,2,3]
