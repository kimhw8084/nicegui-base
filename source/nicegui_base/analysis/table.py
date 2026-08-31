from __future__ import annotations

from dataclasses import replace
from typing import Any

from nicegui_base.data_sources import (
    And, Between, Comparison, ComparisonOperator, DataSchema, DataSource, FieldType, In, IsNull, Not, Or,
    Query, QuerySort, SortDirection as QuerySortDirection, TextMatch, TextMatchMode,
)
from nicegui_base.data_table import (
    ColumnKind, FilterExpression as TableFilterExpression, FilterGroup, FilterLogic, FilterOperator, FilterSpec,
    SortDirection, TableColumn, TableQuery, TableResult,
)

from .context import AnalysisContext


def table_filter_to_query(item: TableFilterExpression):
    if isinstance(item, FilterGroup):
        terms=tuple(table_filter_to_query(child) for child in item.filters)
        return Or(terms) if item.logic is FilterLogic.OR else And(terms)
    op=item.operator
    comparisons={
        FilterOperator.EQUALS:ComparisonOperator.EQ, FilterOperator.NOT_EQUALS:ComparisonOperator.NE,
        FilterOperator.GT:ComparisonOperator.GT, FilterOperator.GTE:ComparisonOperator.GTE,
        FilterOperator.LT:ComparisonOperator.LT, FilterOperator.LTE:ComparisonOperator.LTE,
    }
    if op in comparisons:return Comparison(item.key,comparisons[op],item.value)
    if op is FilterOperator.IN:return In(item.key,tuple(item.value))
    if op is FilterOperator.NOT_IN:return In(item.key,tuple(item.value),negate=True)
    if op is FilterOperator.BETWEEN:return Between(item.key,item.value,item.value2)
    if op is FilterOperator.IS_EMPTY:return IsNull(item.key)
    if op is FilterOperator.IS_NOT_EMPTY:return IsNull(item.key,negate=True)
    modes={FilterOperator.CONTAINS:TextMatchMode.CONTAINS,FilterOperator.STARTS_WITH:TextMatchMode.STARTS_WITH,FilterOperator.ENDS_WITH:TextMatchMode.ENDS_WITH}
    if op in modes:return TextMatch(item.key,str(item.value),modes[op])
    if op is FilterOperator.NOT_CONTAINS:return TextMatch(item.key,str(item.value),TextMatchMode.CONTAINS,negate=True)
    raise ValueError(f'unsupported table filter operator: {op.value}')


def table_query_to_source(query:TableQuery, *, context:AnalysisContext|None=None)->Query:
    filters=tuple(table_filter_to_query(item) for item in query.filters)
    expression=None if not filters else filters[0] if len(filters)==1 else And(filters)
    sorts=tuple(QuerySort(item.key, QuerySortDirection.ASC if item.direction is SortDirection.ASC else QuerySortDirection.DESC) for item in query.sorts)
    source_query=Query(filter=expression,search=query.search,sorts=sorts,offset=(query.page-1)*query.page_size,limit=query.page_size)
    return context.query(source_query) if context is not None else source_query


async def query_data_source_table(source:DataSource, query:TableQuery, *, context:AnalysisContext|None=None)->TableResult:
    result=await source.query(table_query_to_source(query,context=context))
    return TableResult(rows=result.rows,total=result.filtered_total,page=query.page,page_size=query.page_size)


def columns_from_schema(schema:DataSchema)->tuple[TableColumn,...]:
    kind_map={
        FieldType.INTEGER:ColumnKind.INTEGER,FieldType.FLOAT:ColumnKind.FLOAT,FieldType.DECIMAL:ColumnKind.FLOAT,
        FieldType.BOOLEAN:ColumnKind.BOOLEAN,FieldType.DATE:ColumnKind.DATETIME,FieldType.DATETIME:ColumnKind.DATETIME,
    }
    return tuple(TableColumn(field.name,field.label or field.name.replace('_',' ').title(),kind=kind_map.get(field.type,ColumnKind.TEXT)) for field in schema.fields)


__all__=['columns_from_schema','query_data_source_table','table_filter_to_query','table_query_to_source']
