from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


def _clean(value: str, label: str) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f'{label} must not be empty')
    return cleaned


class FieldType(str, Enum):
    STRING = 'string'
    INTEGER = 'integer'
    FLOAT = 'float'
    DECIMAL = 'decimal'
    BOOLEAN = 'boolean'
    DATE = 'date'
    DATETIME = 'datetime'
    CATEGORY = 'category'
    JSON = 'json'
    UNKNOWN = 'unknown'


class FieldRole(str, Enum):
    DIMENSION = 'dimension'
    MEASUREMENT = 'measurement'
    IDENTIFIER = 'identifier'
    TIMESTAMP = 'timestamp'
    ENTITY = 'entity'
    ATTRIBUTE = 'attribute'


class SourceHealthStatus(str, Enum):
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNAVAILABLE = 'unavailable'
    UNKNOWN = 'unknown'


@dataclass(frozen=True, slots=True)
class SemanticField:
    name: str
    label: str | None = None
    type: FieldType = FieldType.UNKNOWN
    role: FieldRole = FieldRole.ATTRIBUTE
    unit: str | None = None
    timezone: str | None = None
    precision: int | None = None
    nullable: bool = True
    description: str | None = None
    sensitivity: str | None = None
    lineage: str | None = None
    format: str | None = None
    allowed_aggregations: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'name', _clean(self.name, 'field name'))
        if self.precision is not None and self.precision < 0:
            raise ValueError('precision must be >= 0')
        for attr in ('unit', 'timezone', 'sensitivity', 'lineage', 'format'):
            value = getattr(self, attr)
            if value is not None:
                object.__setattr__(self, attr, _clean(value, attr))
        object.__setattr__(self, 'allowed_aggregations', tuple(_clean(item, 'aggregation') for item in self.allowed_aggregations))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class DataSchema:
    fields: tuple[SemanticField, ...]
    key: str | None = None
    revision: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        names = [item.name for item in self.fields]
        if len(names) != len(set(names)):
            raise ValueError('schema contains duplicate field names')
        if self.key is not None:
            object.__setattr__(self, 'key', _clean(self.key, 'schema key'))
        if self.revision is not None:
            object.__setattr__(self, 'revision', _clean(self.revision, 'schema revision'))
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.fields)

    def get(self, name: str) -> SemanticField | None:
        return next((item for item in self.fields if item.name == name), None)

    def require(self, name: str) -> SemanticField:
        item = self.get(name)
        if item is None:
            raise KeyError(f'unknown field {name!r}; available fields: {list(self.names)!r}')
        return item


@dataclass(frozen=True, slots=True)
class SourceCapabilities:
    filter_pushdown: bool = False
    search_pushdown: bool = False
    sort_pushdown: bool = False
    pagination_pushdown: bool = False
    aggregation_pushdown: bool = False
    distinct_pushdown: bool = False
    projection_pushdown: bool = False
    cancellation: bool = True
    transactions: bool = False


@dataclass(frozen=True, slots=True)
class SourceProvenance:
    source_key: str
    provider: str
    queried_at: str
    schema_revision: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'source_key', _clean(self.source_key, 'source key'))
        object.__setattr__(self, 'provider', _clean(self.provider, 'provider'))
        object.__setattr__(self, 'details', MappingProxyType(dict(self.details)))

    @classmethod
    def now(cls, source_key: str, provider: str, *, schema_revision: str | None = None, details: Mapping[str, Any] | None = None) -> 'SourceProvenance':
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        return cls(source_key, provider, timestamp, schema_revision, details or {})


@dataclass(frozen=True, slots=True)
class QueryStats:
    elapsed_ms: float
    rows_returned: int
    pushdown: bool
    rows_scanned: int | None = None

    def __post_init__(self) -> None:
        if self.elapsed_ms < 0:
            raise ValueError('elapsed_ms must be >= 0')
        if self.rows_returned < 0:
            raise ValueError('rows_returned must be >= 0')
        if self.rows_scanned is not None and self.rows_scanned < 0:
            raise ValueError('rows_scanned must be >= 0')


@dataclass(frozen=True, slots=True)
class QueryResult:
    rows: tuple[dict[str, Any], ...]
    total: int
    filtered_total: int
    provenance: SourceProvenance
    stats: QueryStats

    def __post_init__(self) -> None:
        if self.total < 0 or self.filtered_total < 0:
            raise ValueError('result totals must be >= 0')


@dataclass(frozen=True, slots=True)
class AggregateResult:
    rows: tuple[dict[str, Any], ...]
    provenance: SourceProvenance
    stats: QueryStats


@dataclass(frozen=True, slots=True)
class DistinctResult:
    values: tuple[Any, ...]
    total: int
    provenance: SourceProvenance
    stats: QueryStats

    def __post_init__(self) -> None:
        if self.total < 0:
            raise ValueError('total must be >= 0')


@dataclass(frozen=True, slots=True)
class SourceHealth:
    status: SourceHealthStatus
    checked_at: str
    message: str | None = None
    latency_ms: float | None = None
    freshness_at: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError('latency_ms must be >= 0')
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @property
    def healthy(self) -> bool:
        return self.status is SourceHealthStatus.HEALTHY

    @classmethod
    def current(cls, status: SourceHealthStatus, *, message: str | None = None, latency_ms: float | None = None, freshness_at: str | None = None, metadata: Mapping[str, Any] | None = None) -> 'SourceHealth':
        checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        return cls(status, checked_at, message, latency_ms, freshness_at, metadata or {})


def infer_field_type(values: tuple[Any, ...]) -> FieldType:
    present = [value for value in values if value is not None]
    if not present:
        return FieldType.UNKNOWN
    if all(isinstance(value, bool) for value in present):
        return FieldType.BOOLEAN
    if all(isinstance(value, int) and not isinstance(value, bool) for value in present):
        return FieldType.INTEGER
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in present):
        return FieldType.FLOAT
    if all(isinstance(value, Decimal) for value in present):
        return FieldType.DECIMAL
    if all(isinstance(value, datetime) for value in present):
        return FieldType.DATETIME
    return FieldType.STRING


__all__ = [name for name in globals() if not name.startswith('_')]
