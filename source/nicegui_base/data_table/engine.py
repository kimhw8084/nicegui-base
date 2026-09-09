from __future__ import annotations

import csv
import io
from collections import OrderedDict
from typing import Any, Iterable, Mapping, Sequence

from .models import (
    FilterExpression, FilterGroup, FilterLogic, FilterOperator, FilterSpec,
    SortDirection, TableColumn, TableQuery, TableResult,
)


def _norm(value: Any) -> Any:
    return '' if value is None else value


def _compile_filter(spec: FilterSpec):
    op = spec.operator
    target = spec.value
    values = set(target) if op in {FilterOperator.IN, FilterOperator.NOT_IN} else None
    needle = str(target).lower() if op in {
        FilterOperator.CONTAINS, FilterOperator.NOT_CONTAINS,
        FilterOperator.STARTS_WITH, FilterOperator.ENDS_WITH,
    } else None

    def match(value: Any) -> bool:
        normalized = _norm(value)
        if op is FilterOperator.IS_EMPTY:
            return value is None or value == ''
        if op is FilterOperator.IS_NOT_EMPTY:
            return not (value is None or value == '')
        if op is FilterOperator.CONTAINS:
            return needle in str(normalized).lower()
        if op is FilterOperator.NOT_CONTAINS:
            return needle not in str(normalized).lower()
        if op is FilterOperator.STARTS_WITH:
            return str(normalized).lower().startswith(needle)
        if op is FilterOperator.ENDS_WITH:
            return str(normalized).lower().endswith(needle)
        if op is FilterOperator.EQUALS:
            return normalized == target
        if op is FilterOperator.NOT_EQUALS:
            return normalized != target
        if op is FilterOperator.IN:
            return normalized in values
        if op is FilterOperator.NOT_IN:
            return normalized not in values
        try:
            if op is FilterOperator.GT: return normalized > target
            if op is FilterOperator.GTE: return normalized >= target
            if op is FilterOperator.LT: return normalized < target
            if op is FilterOperator.LTE: return normalized <= target
            if op is FilterOperator.BETWEEN: return target <= normalized <= spec.value2
        except TypeError:
            return False
        raise ValueError(f'Unsupported filter operator: {op!r}')

    return lambda row: match(row.get(spec.key))


def _compile_expression(expression: FilterExpression):
    if isinstance(expression, FilterSpec):
        return _compile_filter(expression)
    children = tuple(_compile_expression(child) for child in expression.filters)
    if expression.logic is FilterLogic.OR:
        return lambda row: any(child(row) for child in children)
    return lambda row: all(child(row) for child in children)


def _filtered_sorted(rows, query: TableQuery, searchable_columns: Sequence[str] | None = None,
                     search_index: Sequence[str] | None = None):
    needle = query.search.lower().strip()
    compiled = tuple(_compile_expression(item) for item in query.filters)
    out = []
    allowed = set(searchable_columns) if searchable_columns is not None else None
    one = compiled[0] if len(compiled) == 1 else None
    if search_index is not None and needle:
        for index, row in enumerate(rows):
            if needle not in search_index[index]:
                continue
            if one is not None and not one(row):
                continue
            if one is None and compiled and not all(fn(row) for fn in compiled):
                continue
            out.append(row)
    else:
        for row in rows:
            if needle and not any(needle in str(value).lower() for key, value in row.items() if allowed is None or key in allowed):
                continue
            if one is not None and not one(row):
                continue
            if one is None and compiled and not all(fn(row) for fn in compiled):
                continue
            out.append(row)
    for spec in reversed(query.sorts):
        nonnull = [row for row in out if row.get(spec.key) is not None]
        nulls = [row for row in out if row.get(spec.key) is None]
        try:
            nonnull.sort(key=lambda row: row.get(spec.key), reverse=spec.direction is SortDirection.DESC)
        except TypeError:
            nonnull.sort(key=lambda row: (type(row.get(spec.key)).__name__, str(row.get(spec.key))), reverse=spec.direction is SortDirection.DESC)
        out = nonnull + nulls
    return out


def apply_query(rows: Iterable[Mapping[str, Any]], query: TableQuery, *, searchable_columns: Sequence[str] | None = None) -> TableResult:
    data = _filtered_sorted(list(rows), query, searchable_columns)
    total = len(data)
    start = (query.page - 1) * query.page_size
    return TableResult(tuple(data[start:start + query.page_size]), total, query.page, query.page_size)


def _freeze(value: Any):
    if isinstance(value, dict): return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple, set)): return tuple(_freeze(item) for item in value)
    try:
        hash(value)
        return value
    except TypeError:
        return repr(value)


def _freeze_filter(item: FilterExpression):
    if isinstance(item, FilterGroup):
        return ('group', item.logic.value, tuple(_freeze_filter(child) for child in item.filters))
    return ('filter', item.key, item.operator.value, _freeze(item.value), _freeze(item.value2))


def _query_key(query: TableQuery, *, include_page: bool = True):
    base = (
        query.search,
        tuple((sort.key, sort.direction.value) for sort in query.sorts),
        tuple(_freeze_filter(item) for item in query.filters),
        query.page_size,
    )
    return base + (query.page,) if include_page else base


class TableQueryEngine:
    """Bounded repeated-query engine for stable in-memory datasets."""

    def __init__(self, rows: Iterable[Mapping[str, Any]], *, searchable_columns: Sequence[str] | None = None,
                 max_cached_queries: int = 32, build_search_index: bool = True):
        if max_cached_queries < 0:
            raise ValueError('max_cached_queries must be >= 0')
        self.rows = tuple(rows)
        self.searchable_columns = tuple(searchable_columns) if searchable_columns is not None else None
        self.max_cached_queries = max_cached_queries
        self._cache = OrderedDict()
        self._search_index = None
        if build_search_index:
            allowed = set(self.searchable_columns) if self.searchable_columns is not None else None
            self._search_index = tuple(
                ' '.join(str(value).lower() for key, value in row.items() if allowed is None or key in allowed)
                for row in self.rows
            )

    def query(self, query: TableQuery) -> TableResult:
        base = _query_key(query, include_page=False)
        data = self._cache.get(base) if self.max_cached_queries else None
        if data is None:
            data = tuple(_filtered_sorted(self.rows, query, self.searchable_columns, self._search_index))
            if self.max_cached_queries:
                self._cache[base] = data
                self._cache.move_to_end(base)
                while len(self._cache) > self.max_cached_queries:
                    self._cache.popitem(last=False)
        else:
            self._cache.move_to_end(base)
        start = (query.page - 1) * query.page_size
        return TableResult(tuple(data[start:start + query.page_size]), len(data), query.page, query.page_size)

    def clear(self):
        self._cache.clear()


def format_cell(value: Any, column: TableColumn) -> str:
    if value is None: return '—'
    if column.kind.value == 'percent':
        decimals = column.decimals if column.decimals is not None else 1
        return f'{float(value):.{decimals}f}%'
    if column.kind.value == 'float':
        decimals = column.decimals if column.decimals is not None else 2
        text = f'{float(value):,.{decimals}f}'
    elif column.kind.value == 'integer': text = f'{int(value):,}'
    elif column.kind.value == 'boolean': text = 'Yes' if bool(value) else 'No'
    elif column.kind.value == 'datetime': text = value.strftime('%Y-%m-%d %H:%M') if hasattr(value, 'strftime') else str(value)
    else: text = str(value)
    return f'{text} {column.unit}'.strip() if column.unit else text


def _excel_safe(text: str) -> str:
    stripped = text.lstrip()
    return "'" + text if stripped.startswith(('=', '+', '-', '@')) else text


def export_csv(rows: Iterable[Mapping[str, Any]], columns: Sequence[TableColumn]) -> str:
    visible = [column for column in columns if column.visible and column.kind.value != 'action']
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow([column.label for column in visible])
    for row in rows:
        cells = []
        for column in visible:
            text = format_cell(row.get(column.key), column)
            cells.append(_excel_safe(text) if column.kind.value in {'text', 'link', 'status', 'custom'} else text)
        writer.writerow(cells)
    return stream.getvalue()


__all__ = ['TableQueryEngine', 'apply_query', 'format_cell', 'export_csv']
