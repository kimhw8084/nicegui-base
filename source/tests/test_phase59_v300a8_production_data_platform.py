from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from nicegui_base import (
    AggregateFunction, AggregateQuery, AggregationSpec, And, ApplicationRuntime, Between, Comparison,
    ComparisonOperator, CSVDataSource, DataSchema, DataSourceRegistry, Dataset, Dimension, FieldRole,
    FieldType, In, InMemoryDataSource, Metric, Not, Or, Query, QuerySort, QuerySortDirection, SemanticField,
    SQLiteDataSource, TextMatch, TextMatchMode,
)


ROWS = (
    {'id': 1, 'area': 'ETCH', 'chamber': 'A', 'cd': 12.0, 'note': '100% pass'},
    {'id': 2, 'area': 'ETCH', 'chamber': 'B', 'cd': 14.0, 'note': 'under_score'},
    {'id': 3, 'area': 'CVD', 'chamber': 'A', 'cd': 9.0, 'note': None},
    {'id': 4, 'area': 'CVD', 'chamber': 'C', 'cd': 15.0, 'note': 'PASS'},
)


def _schema() -> DataSchema:
    return DataSchema((
        SemanticField('id', type=FieldType.INTEGER, role=FieldRole.IDENTIFIER, nullable=False),
        SemanticField('area', type=FieldType.CATEGORY, role=FieldRole.DIMENSION, nullable=False),
        SemanticField('chamber', type=FieldType.CATEGORY, role=FieldRole.ENTITY, nullable=False),
        SemanticField('cd', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT, unit='nm'),
        SemanticField('note', type=FieldType.STRING),
    ), key='process', revision='test-v1')


def _sqlite(tmp_path: Path) -> SQLiteDataSource:
    path = tmp_path / 'fab.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE process (id INTEGER PRIMARY KEY, area TEXT NOT NULL, chamber TEXT NOT NULL, cd REAL, note TEXT)')
        db.executemany('INSERT INTO process VALUES (:id,:area,:chamber,:cd,:note)', ROWS)
    return SQLiteDataSource('process', str(path), 'process')


def test_wave59_semantic_schema_rejects_duplicate_fields():
    with pytest.raises(ValueError, match='duplicate'):
        DataSchema((SemanticField('x'), SemanticField('x')))


def test_wave59_semantic_schema_exposes_metadata_and_require():
    schema = _schema()
    assert schema.require('cd').unit == 'nm'
    assert schema.require('id').role is FieldRole.IDENTIFIER
    with pytest.raises(KeyError, match='unknown field'):
        schema.require('missing')


def test_wave59_in_memory_source_infers_schema():
    source = InMemoryDataSource('sample', ROWS)
    schema = asyncio.run(source.schema())
    assert schema.require('id').type is FieldType.INTEGER
    assert schema.require('cd').type is FieldType.FLOAT


def test_wave59_query_ast_validates_paging_and_in_values():
    with pytest.raises(ValueError): Query(offset=-1)
    with pytest.raises(ValueError): Query(limit=0)
    with pytest.raises(ValueError): In('area', ())


def test_wave59_memory_compound_filter_search_sort_projection():
    source = InMemoryDataSource('process', ROWS, schema=_schema())
    query = Query(
        filter=And((Comparison('area', ComparisonOperator.EQ, 'ETCH'), Between('cd', 10, 20))),
        search='pass', search_fields=('note',), projection=('id', 'cd'),
        sorts=(QuerySort('cd', QuerySortDirection.DESC),), limit=10,
    )
    result = asyncio.run(source.query(query))
    assert result.rows == ({'id': 1, 'cd': 12.0},)
    assert result.total == 4 and result.filtered_total == 1


def test_wave59_memory_or_not_and_in_semantics():
    source = InMemoryDataSource('process', ROWS, schema=_schema())
    expression = And((Or((Comparison('area', ComparisonOperator.EQ, 'CVD'), Comparison('chamber', ComparisonOperator.EQ, 'B'))), Not(In('id', (3,)))))
    result = asyncio.run(source.query(Query(filter=expression, sorts=(QuerySort('id'),))))
    assert [row['id'] for row in result.rows] == [2, 4]


def test_wave59_text_match_treats_percent_as_literal():
    source = InMemoryDataSource('process', ROWS, schema=_schema())
    result = asyncio.run(source.query(Query(filter=TextMatch('note', '100%', TextMatchMode.CONTAINS))))
    assert [row['id'] for row in result.rows] == [1]


def test_wave59_memory_aggregation_and_count_distinct():
    source = InMemoryDataSource('process', ROWS, schema=_schema())
    result = asyncio.run(source.aggregate(AggregateQuery(
        dimensions=('area',),
        aggregations=(AggregationSpec('avg_cd', AggregateFunction.AVG, 'cd'), AggregationSpec('chambers', AggregateFunction.COUNT_DISTINCT, 'chamber')),
        sorts=(QuerySort('area'),),
    )))
    assert result.rows == ({'area': 'CVD', 'avg_cd': 12.0, 'chambers': 2}, {'area': 'ETCH', 'avg_cd': 13.0, 'chambers': 2})


def test_wave59_memory_distinct_respects_filter():
    source = InMemoryDataSource('process', ROWS, schema=_schema())
    result = asyncio.run(source.distinct('chamber', Query(filter=Comparison('area', ComparisonOperator.EQ, 'ETCH'))))
    assert result.values == ('A', 'B')


def test_wave59_unknown_fields_fail_before_querying():
    source = InMemoryDataSource('process', ROWS, schema=_schema())
    with pytest.raises(KeyError):
        asyncio.run(source.query(Query(filter=Comparison('typo', ComparisonOperator.EQ, 1))))


def test_wave59_sqlite_schema_introspection(tmp_path):
    source = _sqlite(tmp_path)
    schema = asyncio.run(source.schema())
    assert schema.require('id').role is FieldRole.IDENTIFIER
    assert schema.require('cd').type is FieldType.FLOAT


def test_wave59_sqlite_query_uses_server_side_filter_sort_page(tmp_path):
    source = _sqlite(tmp_path)
    result = asyncio.run(source.query(Query(
        filter=Comparison('area', ComparisonOperator.EQ, 'ETCH'),
        sorts=(QuerySort('cd', QuerySortDirection.DESC),), projection=('id', 'cd'), limit=1,
    )))
    assert result.rows == ({'id': 2, 'cd': 14.0},)
    assert result.total == 4 and result.filtered_total == 2
    assert result.stats.pushdown is True and result.stats.rows_scanned is None
    assert source.capabilities.cancellation is False


def test_wave59_sqlite_text_wildcards_are_literal(tmp_path):
    source = _sqlite(tmp_path)
    percent = asyncio.run(source.query(Query(filter=TextMatch('note', '%'))))
    underscore = asyncio.run(source.query(Query(filter=TextMatch('note', '_'))))
    assert [row['id'] for row in percent.rows] == [1]
    assert [row['id'] for row in underscore.rows] == [2]


def test_wave59_sqlite_aggregation_matches_memory(tmp_path):
    memory = InMemoryDataSource('mem', ROWS, schema=_schema())
    sql = _sqlite(tmp_path)
    query = AggregateQuery(
        filter=Comparison('cd', ComparisonOperator.GTE, 10),
        dimensions=('area',),
        aggregations=(AggregationSpec('avg_cd', AggregateFunction.AVG, 'cd'), AggregationSpec('n', AggregateFunction.COUNT)),
        sorts=(QuerySort('area'),),
    )
    memory_rows = asyncio.run(memory.aggregate(query)).rows
    sql_rows = asyncio.run(sql.aggregate(query)).rows
    assert sql_rows == memory_rows


def test_wave59_sqlite_distinct_matches_memory(tmp_path):
    memory = InMemoryDataSource('mem', ROWS, schema=_schema())
    sql = _sqlite(tmp_path)
    query = Query(filter=Comparison('area', ComparisonOperator.EQ, 'CVD'))
    assert asyncio.run(sql.distinct('chamber', query)).values == asyncio.run(memory.distinct('chamber', query)).values


def test_wave59_dataset_automatically_bridges_to_data_source():
    runtime = ApplicationRuntime()
    runtime.data.register(Dataset('legacy', ROWS, dimensions=(Dimension('area'),), metrics=(Metric('cd'),), row_key='id'))
    source = runtime.data.get_source('legacy')
    schema = asyncio.run(source.schema())
    assert schema.require('area').role is FieldRole.DIMENSION
    assert schema.require('cd').role is FieldRole.MEASUREMENT


def test_wave59_runtime_and_workspace_expose_source_registry():
    runtime = ApplicationRuntime()
    runtime.data.register_source(InMemoryDataSource('process', ROWS, schema=_schema()))
    workspace = runtime.open_workspace('analysis')
    assert runtime.data_sources.get('process') is workspace.data_source('process')
    asyncio.run(runtime.aclose())
    assert runtime.closed


def test_wave59_registry_rejects_duplicates_and_closes_sources():
    registry = DataSourceRegistry(); source = InMemoryDataSource('process', ROWS, schema=_schema())
    registry.register(source)
    with pytest.raises(ValueError): registry.register(InMemoryDataSource('process', ROWS, schema=_schema()))
    failures = asyncio.run(registry.aclose())
    assert failures == () and source.closed


def test_wave59_csv_provider_is_dependency_free(tmp_path):
    path = tmp_path / 'rows.csv'; path.write_text('id,area\n1,ETCH\n2,CVD\n', encoding='utf-8')
    source = CSVDataSource('csv', path)
    result = asyncio.run(source.query(Query(sorts=(QuerySort('id'),))))
    assert result.provider if False else source.provider == 'csv'
    assert [row['area'] for row in result.rows] == ['ETCH', 'CVD']


def test_wave59_source_health_and_provenance_are_explicit(tmp_path):
    source = _sqlite(tmp_path)
    health = asyncio.run(source.health())
    result = asyncio.run(source.query(Query(limit=1)))
    assert health.healthy
    assert result.provenance.source_key == 'process'
    assert result.provenance.provider == 'sqlite'
    assert result.provenance.queried_at.endswith('Z')


def test_wave59_million_row_sqlite_pushdown_does_not_materialize_full_result(tmp_path):
    path = tmp_path / 'million.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE measurements (id INTEGER PRIMARY KEY, chamber TEXT NOT NULL, value REAL NOT NULL)')
        batch = 10_000
        for start in range(0, 1_000_000, batch):
            db.executemany('INSERT INTO measurements VALUES (?,?,?)', ((i + 1, f'C{(i % 20):02d}', float(i % 1000)) for i in range(start, start + batch)))
    source = SQLiteDataSource('million', str(path), 'measurements')
    result = asyncio.run(source.query(Query(filter=Comparison('chamber', ComparisonOperator.EQ, 'C03'), sorts=(QuerySort('id'),), limit=25)))
    aggregate = asyncio.run(source.aggregate(AggregateQuery(filter=Comparison('chamber', ComparisonOperator.EQ, 'C03'), aggregations=(AggregationSpec('n', AggregateFunction.COUNT),))))
    assert len(result.rows) == 25
    assert result.total == 1_000_000 and result.filtered_total == 50_000
    assert aggregate.rows == ({'n': 50_000},)
    assert result.stats.pushdown and result.stats.rows_scanned is None
