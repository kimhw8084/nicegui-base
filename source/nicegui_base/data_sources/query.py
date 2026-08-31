from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


def _clean(value: str, label: str) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f'{label} must not be empty')
    return cleaned


class ComparisonOperator(str, Enum):
    EQ = 'eq'
    NE = 'ne'
    GT = 'gt'
    GTE = 'gte'
    LT = 'lt'
    LTE = 'lte'


class TextMatchMode(str, Enum):
    CONTAINS = 'contains'
    STARTS_WITH = 'starts_with'
    ENDS_WITH = 'ends_with'


class SortDirection(str, Enum):
    ASC = 'asc'
    DESC = 'desc'


class AggregateFunction(str, Enum):
    COUNT = 'count'
    SUM = 'sum'
    AVG = 'avg'
    MIN = 'min'
    MAX = 'max'
    COUNT_DISTINCT = 'count_distinct'


class FilterExpression:
    """Marker base class for the typed query filter AST."""


@dataclass(frozen=True, slots=True)
class Comparison(FilterExpression):
    field: str
    operator: ComparisonOperator
    value: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, 'field', _clean(self.field, 'comparison field'))


@dataclass(frozen=True, slots=True)
class In(FilterExpression):
    field: str
    values: tuple[Any, ...]
    negate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, 'field', _clean(self.field, 'in field'))
        object.__setattr__(self, 'values', tuple(self.values))
        if not self.values:
            raise ValueError('IN values must not be empty')


@dataclass(frozen=True, slots=True)
class Between(FilterExpression):
    field: str
    lower: Any
    upper: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, 'field', _clean(self.field, 'between field'))
        if self.lower is None or self.upper is None:
            raise ValueError('between lower and upper values are required')


@dataclass(frozen=True, slots=True)
class TextMatch(FilterExpression):
    field: str
    value: str
    mode: TextMatchMode = TextMatchMode.CONTAINS
    case_sensitive: bool = False
    negate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, 'field', _clean(self.field, 'text field'))
        object.__setattr__(self, 'value', str(self.value))


@dataclass(frozen=True, slots=True)
class IsNull(FilterExpression):
    field: str
    negate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, 'field', _clean(self.field, 'null field'))


@dataclass(frozen=True, slots=True)
class And(FilterExpression):
    terms: tuple[FilterExpression, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'terms', tuple(self.terms))
        if not self.terms:
            raise ValueError('AND requires at least one term')


@dataclass(frozen=True, slots=True)
class Or(FilterExpression):
    terms: tuple[FilterExpression, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'terms', tuple(self.terms))
        if not self.terms:
            raise ValueError('OR requires at least one term')


@dataclass(frozen=True, slots=True)
class Not(FilterExpression):
    term: FilterExpression


@dataclass(frozen=True, slots=True)
class QuerySort:
    field: str
    direction: SortDirection = SortDirection.ASC

    def __post_init__(self) -> None:
        object.__setattr__(self, 'field', _clean(self.field, 'sort field'))


@dataclass(frozen=True, slots=True)
class Query:
    filter: FilterExpression | None = None
    search: str = ''
    search_fields: tuple[str, ...] = ()
    projection: tuple[str, ...] = ()
    sorts: tuple[QuerySort, ...] = ()
    offset: int = 0
    limit: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'search', str(self.search))
        object.__setattr__(self, 'search_fields', tuple(_clean(item, 'search field') for item in self.search_fields))
        object.__setattr__(self, 'projection', tuple(_clean(item, 'projection field') for item in self.projection))
        object.__setattr__(self, 'sorts', tuple(self.sorts))
        if self.offset < 0:
            raise ValueError('offset must be >= 0')
        if self.limit is not None and self.limit < 1:
            raise ValueError('limit must be >= 1')


@dataclass(frozen=True, slots=True)
class AggregationSpec:
    key: str
    function: AggregateFunction
    field: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'key', _clean(self.key, 'aggregation key'))
        if self.field is not None:
            object.__setattr__(self, 'field', _clean(self.field, 'aggregation field'))
        if self.function is not AggregateFunction.COUNT and self.field is None:
            raise ValueError(f'{self.function.value} aggregation requires field')


@dataclass(frozen=True, slots=True)
class AggregateQuery:
    filter: FilterExpression | None = None
    search: str = ''
    search_fields: tuple[str, ...] = ()
    dimensions: tuple[str, ...] = ()
    aggregations: tuple[AggregationSpec, ...] = ()
    sorts: tuple[QuerySort, ...] = ()
    offset: int = 0
    limit: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'search', str(self.search))
        object.__setattr__(self, 'search_fields', tuple(_clean(item, 'search field') for item in self.search_fields))
        object.__setattr__(self, 'dimensions', tuple(_clean(item, 'dimension field') for item in self.dimensions))
        object.__setattr__(self, 'aggregations', tuple(self.aggregations))
        object.__setattr__(self, 'sorts', tuple(self.sorts))
        if len({item.key for item in self.aggregations}) != len(self.aggregations):
            raise ValueError('duplicate aggregation keys')
        if self.offset < 0:
            raise ValueError('offset must be >= 0')
        if self.limit is not None and self.limit < 1:
            raise ValueError('limit must be >= 1')


def fields_in_filter(expression: FilterExpression | None) -> tuple[str, ...]:
    if expression is None:
        return ()
    if isinstance(expression, (Comparison, In, Between, TextMatch, IsNull)):
        return (expression.field,)
    if isinstance(expression, (And, Or)):
        return tuple(dict.fromkeys(field for term in expression.terms for field in fields_in_filter(term)))
    if isinstance(expression, Not):
        return fields_in_filter(expression.term)
    raise TypeError(f'unsupported filter expression: {type(expression).__name__}')


__all__ = [name for name in globals() if not name.startswith('_')]
