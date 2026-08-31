from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class FilterOperation(str, Enum):
    EQUALS='equals'; NOT_EQUALS='not_equals'; IN='in'; NOT_IN='not_in'
    GT='gt'; GTE='gte'; LT='lt'; LTE='lte'; BETWEEN='between'
    CONTAINS='contains'; STARTS_WITH='starts_with'; ENDS_WITH='ends_with'
    IS_EMPTY='is_empty'; IS_NOT_EMPTY='is_not_empty'


class Aggregation(str, Enum):
    SUM='sum'; AVG='avg'; MIN='min'; MAX='max'; COUNT='count'; COUNT_DISTINCT='count_distinct'


def _clean_key(value: str, label: str) -> str:
    cleaned=str(value).strip()
    if not cleaned:
        raise ValueError(f'{label} must not be empty')
    return cleaned


@dataclass(frozen=True, slots=True)
class Dimension:
    key: str
    label: str | None = None
    field: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'key', _clean_key(self.key, 'Dimension key'))
        if self.field is not None:
            object.__setattr__(self, 'field', _clean_key(self.field, 'Dimension field'))

    @property
    def source_field(self) -> str:
        return self.field or self.key


@dataclass(frozen=True, slots=True)
class Metric:
    key: str
    label: str | None = None
    field: str | None = None
    aggregation: Aggregation = Aggregation.SUM

    def __post_init__(self) -> None:
        object.__setattr__(self, 'key', _clean_key(self.key, 'Metric key'))
        if self.field is not None:
            object.__setattr__(self, 'field', _clean_key(self.field, 'Metric field'))
        if self.aggregation is not Aggregation.COUNT and not (self.field or self.key):
            raise ValueError('Metric field is required')

    @property
    def source_field(self) -> str | None:
        return self.field or (None if self.aggregation is Aggregation.COUNT else self.key)


@dataclass(frozen=True, slots=True)
class FilterClause:
    field: str
    operation: FilterOperation
    value: Any = None
    value2: Any = None
    filter_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'field', _clean_key(self.field, 'FilterClause field'))
        if self.filter_id is not None:
            object.__setattr__(self, 'filter_id', _clean_key(self.filter_id, 'FilterClause filter_id'))
        op=self.operation
        if op in {FilterOperation.IN, FilterOperation.NOT_IN}:
            value=self.value
            if isinstance(value, (str, bytes, bytearray, Mapping)) or not isinstance(value, Collection):
                raise TypeError(f'{op.value} filter requires a non-string collection value')
        elif op is FilterOperation.BETWEEN:
            if self.value is None or self.value2 is None:
                raise ValueError('between filter requires both value and value2')
        elif op in {FilterOperation.GT, FilterOperation.GTE, FilterOperation.LT, FilterOperation.LTE}:
            if self.value is None:
                raise ValueError(f'{op.value} filter requires value')

    @property
    def key(self) -> str:
        return self.filter_id or self.field


@dataclass(frozen=True, slots=True)
class SortClause:
    key: str
    descending: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, 'key', _clean_key(self.key, 'SortClause key'))


@dataclass(frozen=True, slots=True)
class DataQuery:
    filters: tuple[FilterClause, ...] = ()
    search: str = ''
    search_fields: tuple[str, ...] = ()
    dimensions: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    sorts: tuple[SortClause, ...] = ()
    offset: int = 0
    limit: int | None = None

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError('offset must be >= 0')
        if self.limit is not None and self.limit < 1:
            raise ValueError('limit must be >= 1')
        for field in self.search_fields:
            _clean_key(field, 'search field')
        for key in self.dimensions:
            _clean_key(key, 'dimension key')
        for key in self.metrics:
            _clean_key(key, 'metric key')


@dataclass(frozen=True, slots=True)
class DataResult:
    rows: tuple[dict[str, Any], ...]
    total: int
    revision: int = 0
    filtered_total: int | None = None


@dataclass(frozen=True, slots=True)
class DataSessionSnapshot:
    revision: int
    filters: tuple[FilterClause, ...]
    search: str = ''
