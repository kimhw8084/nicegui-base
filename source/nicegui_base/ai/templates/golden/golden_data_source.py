"""Golden provider-neutral data-source example.

Swap InMemoryDataSource for SQLiteDataSource/DBAPIDataSource without changing the query.
"""
from nicegui_base import (
    AggregateFunction, AggregateQuery, AggregationSpec, Comparison, ComparisonOperator,
    DataSchema, FieldRole, FieldType, InMemoryDataSource, Query, QuerySort,
    QuerySortDirection, SemanticField,
)

SCHEMA = DataSchema((
    SemanticField('wafer_id', type=FieldType.STRING, role=FieldRole.IDENTIFIER, nullable=False),
    SemanticField('chamber', type=FieldType.CATEGORY, role=FieldRole.ENTITY, nullable=False),
    SemanticField('cd', type=FieldType.FLOAT, role=FieldRole.MEASUREMENT, unit='nm'),
), key='metrology')

SOURCE = InMemoryDataSource('metrology', (
    {'wafer_id': 'W01', 'chamber': 'CH-A', 'cd': 12.1},
    {'wafer_id': 'W02', 'chamber': 'CH-B', 'cd': 12.8},
), schema=SCHEMA)

DETAIL_QUERY = Query(
    filter=Comparison('chamber', ComparisonOperator.EQ, 'CH-A'),
    sorts=(QuerySort('wafer_id'),),
    limit=100,
)

SUMMARY_QUERY = AggregateQuery(
    dimensions=('chamber',),
    aggregations=(AggregationSpec('avg_cd', AggregateFunction.AVG, 'cd'),),
)
