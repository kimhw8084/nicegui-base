from __future__ import annotations

import asyncio
import sqlite3
import time
from collections.abc import Callable
from contextlib import closing
from typing import Any

from .models import (
    AggregateResult, DataSchema, DistinctResult, FieldRole, FieldType, QueryResult, QueryStats,
    SemanticField, SourceCapabilities, SourceHealth, SourceHealthStatus, SourceProvenance,
)
from .query import (
    AggregateFunction, AggregateQuery, And, Between, Comparison, ComparisonOperator, FilterExpression, In,
    IsNull, Not, Or, Query, QuerySort, SortDirection, TextMatch, TextMatchMode, fields_in_filter,
)
from .source import DataSource


def _sqlite_type(type_name: str) -> FieldType:
    upper = (type_name or '').upper()
    if 'INT' in upper: return FieldType.INTEGER
    if any(token in upper for token in ('REAL', 'FLOA', 'DOUB')): return FieldType.FLOAT
    if any(token in upper for token in ('NUM', 'DEC')): return FieldType.DECIMAL
    if 'BOOL' in upper: return FieldType.BOOLEAN
    if 'DATE' in upper and 'TIME' not in upper: return FieldType.DATE
    if any(token in upper for token in ('TIME', 'DATE')): return FieldType.DATETIME
    if any(token in upper for token in ('CHAR', 'CLOB', 'TEXT')): return FieldType.STRING
    return FieldType.UNKNOWN


def _escape_like(value: str) -> str:
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


class DBAPIDataSource(DataSource):
    """DB-API 2.0 analytical source with parameterized values and pushdown."""

    def __init__(self, key: str, *, connection_factory: Callable[[], Any], table: str, schema: DataSchema, timeout_seconds: float | None = 30.0) -> None:
        super().__init__(key, timeout_seconds=timeout_seconds)
        if not table.strip(): raise ValueError('table must not be empty')
        self.connection_factory = connection_factory
        self.table = table.strip()
        self._schema = schema

    @property
    def provider(self) -> str:
        return 'dbapi'

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            filter_pushdown=True, search_pushdown=True, sort_pushdown=True, pagination_pushdown=True,
            aggregation_pushdown=True, distinct_pushdown=True, projection_pushdown=True,
            cancellation=False, transactions=False,
        )

    def _quote(self, identifier: str) -> str:
        self._schema.require(identifier)
        return '"' + identifier.replace('"', '""') + '"'

    @property
    def _table_sql(self) -> str:
        # Table names come from application configuration rather than user input.
        # Quote each path component to avoid accidental keyword collisions.
        parts = self.table.split('.')
        if any(not part or '\x00' in part for part in parts):
            raise ValueError('invalid table name')
        return '.'.join('"' + part.replace('"', '""') + '"' for part in parts)

    async def schema(self) -> DataSchema:
        self._ensure_open(); return self._schema

    def _validate_query(self, query: Query) -> None:
        for field in fields_in_filter(query.filter): self._schema.require(field)
        for field in query.search_fields: self._schema.require(field)
        for field in query.projection: self._schema.require(field)
        for sort in query.sorts: self._schema.require(sort.field)

    def _compile_filter(self, expression: FilterExpression | None) -> tuple[str, list[Any]]:
        if expression is None: return '', []
        if isinstance(expression, Comparison):
            field = self._quote(expression.field)
            operators = {ComparisonOperator.EQ:'=', ComparisonOperator.NE:'!=', ComparisonOperator.GT:'>', ComparisonOperator.GTE:'>=', ComparisonOperator.LT:'<', ComparisonOperator.LTE:'<='}
            if expression.value is None and expression.operator in {ComparisonOperator.EQ, ComparisonOperator.NE}:
                return f'{field} IS {"NOT " if expression.operator is ComparisonOperator.NE else ""}NULL', []
            return f'{field} {operators[expression.operator]} ?', [expression.value]
        if isinstance(expression, In):
            field = self._quote(expression.field)
            marks = ','.join('?' for _ in expression.values)
            return f'{field} {"NOT " if expression.negate else ""}IN ({marks})', list(expression.values)
        if isinstance(expression, Between):
            return f'{self._quote(expression.field)} BETWEEN ? AND ?', [expression.lower, expression.upper]
        if isinstance(expression, TextMatch):
            field = self._quote(expression.field)
            escaped = _escape_like(expression.value)
            if expression.mode is TextMatchMode.CONTAINS: pattern = f'%{escaped}%'
            elif expression.mode is TextMatchMode.STARTS_WITH: pattern = f'{escaped}%'
            else: pattern = f'%{escaped}'
            lhs = field if expression.case_sensitive else f'LOWER({field})'
            rhs = pattern if expression.case_sensitive else pattern.casefold()
            return f'{lhs} {"NOT " if expression.negate else ""}LIKE ? ESCAPE \'\\\'', [rhs]
        if isinstance(expression, IsNull):
            return f'{self._quote(expression.field)} IS {"NOT " if expression.negate else ""}NULL', []
        if isinstance(expression, (And, Or)):
            compiled = [self._compile_filter(term) for term in expression.terms]
            joiner = ' AND ' if isinstance(expression, And) else ' OR '
            return '(' + joiner.join(sql for sql, _ in compiled) + ')', [value for _, values in compiled for value in values]
        if isinstance(expression, Not):
            sql, params = self._compile_filter(expression.term)
            return f'NOT ({sql})', params
        raise TypeError(f'unsupported filter expression: {type(expression).__name__}')

    def _where(self, query: Query | AggregateQuery) -> tuple[str, list[Any]]:
        clauses: list[str] = []; params: list[Any] = []
        sql, values = self._compile_filter(query.filter)
        if sql: clauses.append(sql); params.extend(values)
        needle = query.search.strip()
        if needle:
            fields = query.search_fields or self._schema.names
            for field in fields: self._schema.require(field)
            escaped = _escape_like(needle.casefold())
            terms = [f'LOWER(CAST({self._quote(field)} AS TEXT)) LIKE ? ESCAPE \'\\\'' for field in fields]
            clauses.append('(' + ' OR '.join(terms) + ')')
            params.extend([f'%{escaped}%'] * len(terms))
        return (' WHERE ' + ' AND '.join(clauses), params) if clauses else ('', params)

    def _execute(self, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> tuple[list[str], list[tuple[Any, ...]]]:
        with closing(self.connection_factory()) as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, params)
                columns = [item[0] for item in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                return columns, rows
            finally:
                cursor.close()

    async def _thread(self, fn, *args):
        self._ensure_open()
        return await self._run_with_timeout(asyncio.to_thread(fn, *args))

    async def query(self, query: Query = Query()) -> QueryResult:
        self._validate_query(query)
        started = time.perf_counter(); where, params = self._where(query)
        projection = query.projection or self._schema.names
        fields = ', '.join(self._quote(field) for field in projection)
        order = ''
        if query.sorts:
            order = ' ORDER BY ' + ', '.join(f'{self._quote(item.field)} {"DESC" if item.direction is SortDirection.DESC else "ASC"}' for item in query.sorts)
        paging = ''; page_params = list(params)
        if query.limit is not None:
            paging = ' LIMIT ? OFFSET ?'; page_params.extend([query.limit, query.offset])
        elif query.offset:
            paging = ' LIMIT ? OFFSET ?'; page_params.extend([-1, query.offset])
        sql = f'SELECT {fields} FROM {self._table_sql}{where}{order}{paging}'
        count_all = f'SELECT COUNT(*) AS n FROM {self._table_sql}'
        count_filtered = f'SELECT COUNT(*) AS n FROM {self._table_sql}{where}'
        (columns, raw), (_, total_rows), (_, filtered_rows) = await asyncio.gather(
            self._thread(self._execute, sql, page_params),
            self._thread(self._execute, count_all, []),
            self._thread(self._execute, count_filtered, params),
        )
        rows = tuple(dict(zip(columns, row)) for row in raw)
        elapsed = (time.perf_counter() - started) * 1000
        return QueryResult(rows, int(total_rows[0][0]), int(filtered_rows[0][0]), SourceProvenance.now(self.key, self.provider, schema_revision=self._schema.revision), QueryStats(elapsed, len(rows), True))

    async def aggregate(self, query: AggregateQuery) -> AggregateResult:
        for field in query.dimensions: self._schema.require(field)
        select = [self._quote(field) for field in query.dimensions]
        for item in query.aggregations:
            field = None if item.field is None else self._quote(item.field)
            if item.field is not None: self._schema.require(item.field)
            if item.function is AggregateFunction.COUNT:
                expr = 'COUNT(*)' if field is None else f'COUNT({field})'
            elif item.function is AggregateFunction.COUNT_DISTINCT: expr = f'COUNT(DISTINCT {field})'
            elif item.function is AggregateFunction.SUM: expr = f'SUM({field})'
            elif item.function is AggregateFunction.AVG: expr = f'AVG({field})'
            elif item.function is AggregateFunction.MIN: expr = f'MIN({field})'
            else: expr = f'MAX({field})'
            select.append(f'{expr} AS "{item.key.replace(chr(34), chr(34)*2)}"')
        if not select: raise ValueError('aggregate query requires dimensions or aggregations')
        where, params = self._where(query)
        group = ' GROUP BY ' + ', '.join(self._quote(field) for field in query.dimensions) if query.dimensions else ''
        output_fields = set(query.dimensions) | {item.key for item in query.aggregations}
        order_parts = []
        for item in query.sorts:
            if item.field not in output_fields: raise KeyError(f'unknown aggregate sort field: {item.field}')
            quoted = '"' + item.field.replace('"', '""') + '"'
            order_parts.append(f'{quoted} {"DESC" if item.direction is SortDirection.DESC else "ASC"}')
        order = ' ORDER BY ' + ', '.join(order_parts) if order_parts else ''
        paging = ''; final_params = list(params)
        if query.limit is not None:
            paging = ' LIMIT ? OFFSET ?'; final_params.extend([query.limit, query.offset])
        elif query.offset:
            paging = ' LIMIT ? OFFSET ?'; final_params.extend([-1, query.offset])
        sql = f'SELECT {", ".join(select)} FROM {self._table_sql}{where}{group}{order}{paging}'
        started = time.perf_counter(); columns, raw = await self._thread(self._execute, sql, final_params)
        rows = tuple(dict(zip(columns, row)) for row in raw); elapsed = (time.perf_counter() - started) * 1000
        return AggregateResult(rows, SourceProvenance.now(self.key, self.provider, schema_revision=self._schema.revision), QueryStats(elapsed, len(rows), True))

    async def distinct(self, field: str, query: Query = Query()) -> DistinctResult:
        self._schema.require(field); self._validate_query(query)
        where, params = self._where(query)
        quoted = self._quote(field)
        sql = f'SELECT DISTINCT {quoted} AS value FROM {self._table_sql}{where} ORDER BY {quoted}'
        started = time.perf_counter(); _, raw = await self._thread(self._execute, sql, params)
        values = tuple(row[0] for row in raw); elapsed = (time.perf_counter() - started) * 1000
        return DistinctResult(values, len(values), SourceProvenance.now(self.key, self.provider, schema_revision=self._schema.revision), QueryStats(elapsed, len(values), True))

    async def health(self) -> SourceHealth:
        started = time.perf_counter()
        try:
            await self._thread(self._execute, 'SELECT 1', [])
        except Exception as exc:
            return SourceHealth.current(SourceHealthStatus.UNAVAILABLE, message=f'{type(exc).__name__}: {exc}')
        return SourceHealth.current(SourceHealthStatus.HEALTHY, message='DB-API source reachable', latency_ms=(time.perf_counter() - started) * 1000)


class SQLiteDataSource(DBAPIDataSource):
    def __init__(self, key: str, path: str, table: str, *, schema: DataSchema | None = None, timeout_seconds: float | None = 30.0) -> None:
        self.path = str(path)
        if schema is None:
            schema = self._read_schema(self.path, table, key)
        super().__init__(key, connection_factory=lambda: sqlite3.connect(self.path, timeout=30), table=table, schema=schema, timeout_seconds=timeout_seconds)

    @property
    def provider(self) -> str:
        return 'sqlite'

    @staticmethod
    def _read_schema(path: str, table: str, key: str) -> DataSchema:
        if not table.strip(): raise ValueError('table must not be empty')
        escaped = table.replace('"', '""')
        with closing(sqlite3.connect(path)) as connection:
            rows = connection.execute(f'PRAGMA table_info("{escaped}")').fetchall()
        if not rows:
            raise KeyError(f'unknown SQLite table: {table}')
        fields = tuple(
            SemanticField(
                str(name), type=_sqlite_type(str(type_name)),
                role=FieldRole.IDENTIFIER if int(pk) else FieldRole.ATTRIBUTE,
                nullable=not bool(notnull),
            )
            for _cid, name, type_name, notnull, _default, pk in rows
        )
        return DataSchema(fields, key=key, revision='sqlite-pragma-v1', metadata={'table': table})


__all__ = ['DBAPIDataSource', 'SQLiteDataSource']
