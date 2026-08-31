from __future__ import annotations

import asyncio
import math
import time
from collections import OrderedDict
from copy import deepcopy
from typing import Any, Mapping, Sequence

from .models import (
    AggregateResult, DataSchema, DistinctResult, FieldRole, QueryResult, QueryStats,
    SemanticField, SourceCapabilities, SourceHealth, SourceHealthStatus, SourceProvenance, infer_field_type,
)
from .query import (
    AggregateFunction, AggregateQuery, And, Between, Comparison, ComparisonOperator, FilterExpression,
    In, IsNull, Not, Or, Query, SortDirection, TextMatch, TextMatchMode, fields_in_filter,
)
from .source import DataSource


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _sort_key(value: Any) -> tuple[int, str, Any]:
    if value is None:
        return (2, '', 0)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (0, 'number', float(value))
    return (1, type(value).__name__, str(value).casefold())


def _matches(row: Mapping[str, Any], expression: FilterExpression | None) -> bool:
    if expression is None:
        return True
    if isinstance(expression, Comparison):
        value = row.get(expression.field)
        target = expression.value
        if expression.operator is ComparisonOperator.EQ:
            return value == target
        if expression.operator is ComparisonOperator.NE:
            return value != target
        try:
            if expression.operator is ComparisonOperator.GT: return value > target
            if expression.operator is ComparisonOperator.GTE: return value >= target
            if expression.operator is ComparisonOperator.LT: return value < target
            if expression.operator is ComparisonOperator.LTE: return value <= target
        except TypeError:
            return False
    if isinstance(expression, In):
        matched = row.get(expression.field) in expression.values
        return not matched if expression.negate else matched
    if isinstance(expression, Between):
        try:
            return expression.lower <= row.get(expression.field) <= expression.upper
        except TypeError:
            return False
    if isinstance(expression, TextMatch):
        value = row.get(expression.field)
        text = '' if value is None else str(value)
        needle = expression.value
        if not expression.case_sensitive:
            text, needle = text.casefold(), needle.casefold()
        if expression.mode is TextMatchMode.CONTAINS:
            matched = needle in text
        elif expression.mode is TextMatchMode.STARTS_WITH:
            matched = text.startswith(needle)
        else:
            matched = text.endswith(needle)
        return not matched if expression.negate else matched
    if isinstance(expression, IsNull):
        matched = row.get(expression.field) is None
        return not matched if expression.negate else matched
    if isinstance(expression, And):
        return all(_matches(row, term) for term in expression.terms)
    if isinstance(expression, Or):
        return any(_matches(row, term) for term in expression.terms)
    if isinstance(expression, Not):
        return not _matches(row, expression.term)
    raise TypeError(f'unsupported filter expression: {type(expression).__name__}')


class InMemoryDataSource(DataSource):
    def __init__(self, key: str, rows: Sequence[Mapping[str, Any]], *, schema: DataSchema | None = None, timeout_seconds: float | None = 30.0) -> None:
        super().__init__(key, timeout_seconds=timeout_seconds)
        self._rows = tuple(deepcopy(dict(row)) for row in rows)
        self._schema = schema or self._infer_schema()
        for row in self._rows:
            extra = set(row) - set(self._schema.names)
            if extra:
                raise KeyError(f'row contains fields outside schema: {sorted(extra)!r}')

    @property
    def provider(self) -> str:
        return 'memory'

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            filter_pushdown=False, search_pushdown=False, sort_pushdown=False,
            pagination_pushdown=False, aggregation_pushdown=False, distinct_pushdown=False,
            projection_pushdown=False, cancellation=True,
        )

    def _infer_schema(self) -> DataSchema:
        names = tuple(dict.fromkeys(key for row in self._rows for key in row))
        fields = tuple(
            SemanticField(
                name,
                type=infer_field_type(tuple(row.get(name) for row in self._rows)),
                role=FieldRole.ATTRIBUTE,
                nullable=any(row.get(name) is None for row in self._rows),
            )
            for name in names
        )
        return DataSchema(fields, key=self.key, revision='inferred-v1')

    async def schema(self) -> DataSchema:
        self._ensure_open()
        await asyncio.sleep(0)
        return self._schema

    def _validate_query(self, query: Query) -> None:
        for field in fields_in_filter(query.filter): self._schema.require(field)
        for field in query.search_fields: self._schema.require(field)
        for field in query.projection: self._schema.require(field)
        for sort in query.sorts: self._schema.require(sort.field)

    def _filtered(self, query: Query) -> list[dict[str, Any]]:
        self._validate_query(query)
        needle = query.search.strip().casefold()
        search_fields = query.search_fields or self._schema.names
        output = []
        for row in self._rows:
            if not _matches(row, query.filter):
                continue
            if needle and not any(needle in str(row.get(field)).casefold() for field in search_fields if row.get(field) is not None):
                continue
            output.append(dict(row))
        return output

    async def query(self, query: Query = Query()) -> QueryResult:
        async def run() -> QueryResult:
            started = time.perf_counter()
            rows = self._filtered(query)
            filtered_total = len(rows)
            for sort in reversed(query.sorts):
                rows.sort(key=lambda row, field=sort.field: _sort_key(row.get(field)), reverse=sort.direction is SortDirection.DESC)
            start = query.offset
            stop = None if query.limit is None else start + query.limit
            page = rows[start:stop]
            if query.projection:
                page = [{field: row.get(field) for field in query.projection} for row in page]
            await asyncio.sleep(0)
            elapsed = (time.perf_counter() - started) * 1000
            return QueryResult(
                tuple(deepcopy(page)), len(self._rows), filtered_total,
                SourceProvenance.now(self.key, self.provider, schema_revision=self._schema.revision),
                QueryStats(elapsed, len(page), False, rows_scanned=len(self._rows)),
            )
        return await self._run_with_timeout(run())

    async def aggregate(self, query: AggregateQuery) -> AggregateResult:
        async def run() -> AggregateResult:
            started = time.perf_counter()
            base = Query(filter=query.filter, search=query.search, search_fields=query.search_fields)
            rows = self._filtered(base)
            for field in query.dimensions: self._schema.require(field)
            for item in query.aggregations:
                if item.field is not None: self._schema.require(item.field)
            groups: OrderedDict[tuple[Any, ...], list[dict[str, Any]]] = OrderedDict()
            if query.dimensions:
                for row in rows:
                    groups.setdefault(tuple(row.get(field) for field in query.dimensions), []).append(row)
            else:
                groups[()] = rows
            output: list[dict[str, Any]] = []
            for keys, group_rows in groups.items():
                result = {field: value for field, value in zip(query.dimensions, keys)}
                for item in query.aggregations:
                    values = [row.get(item.field) for row in group_rows] if item.field is not None else []
                    if item.function is AggregateFunction.COUNT:
                        result[item.key] = len(group_rows) if item.field is None else sum(value is not None for value in values)
                    elif item.function is AggregateFunction.COUNT_DISTINCT:
                        result[item.key] = len({repr(value) for value in values if value is not None})
                    else:
                        numbers = []
                        for raw in values:
                            if raw is None: continue
                            value = _finite_number(raw)
                            if value is None:
                                raise TypeError(f'aggregation {item.key!r} requires finite numeric values; got {raw!r}')
                            numbers.append(value)
                        if not numbers:
                            result[item.key] = None
                        elif item.function is AggregateFunction.SUM: result[item.key] = sum(numbers)
                        elif item.function is AggregateFunction.AVG: result[item.key] = sum(numbers) / len(numbers)
                        elif item.function is AggregateFunction.MIN: result[item.key] = min(numbers)
                        elif item.function is AggregateFunction.MAX: result[item.key] = max(numbers)
                output.append(result)
            output_fields = set(query.dimensions) | {item.key for item in query.aggregations}
            for sort in query.sorts:
                if sort.field not in output_fields:
                    raise KeyError(f'unknown aggregate sort field: {sort.field}')
            for sort in reversed(query.sorts):
                output.sort(key=lambda row, field=sort.field: _sort_key(row.get(field)), reverse=sort.direction is SortDirection.DESC)
            start = query.offset; stop = None if query.limit is None else start + query.limit
            page = output[start:stop]
            await asyncio.sleep(0)
            elapsed = (time.perf_counter() - started) * 1000
            return AggregateResult(
                tuple(deepcopy(page)), SourceProvenance.now(self.key, self.provider, schema_revision=self._schema.revision),
                QueryStats(elapsed, len(page), False, rows_scanned=len(self._rows)),
            )
        return await self._run_with_timeout(run())

    async def distinct(self, field: str, query: Query = Query()) -> DistinctResult:
        async def run() -> DistinctResult:
            started = time.perf_counter()
            self._schema.require(field)
            rows = self._filtered(Query(filter=query.filter, search=query.search, search_fields=query.search_fields))
            values = []
            for row in rows:
                value = row.get(field)
                if value not in values:
                    values.append(value)
            await asyncio.sleep(0)
            elapsed = (time.perf_counter() - started) * 1000
            return DistinctResult(
                tuple(deepcopy(values)), len(values), SourceProvenance.now(self.key, self.provider, schema_revision=self._schema.revision),
                QueryStats(elapsed, len(values), False, rows_scanned=len(self._rows)),
            )
        return await self._run_with_timeout(run())

    async def health(self) -> SourceHealth:
        self._ensure_open()
        return SourceHealth.current(SourceHealthStatus.HEALTHY, message='in-memory source ready')


__all__ = ['InMemoryDataSource']
