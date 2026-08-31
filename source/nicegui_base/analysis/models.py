from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping

from nicegui_base.data_sources import FilterExpression


class AnalysisStatus(str, Enum):
    READY = 'ready'
    LOADING = 'loading'
    EMPTY = 'empty'
    PARTIAL = 'partial'
    STALE = 'stale'
    ERROR = 'error'


class SelectionKind(str, Enum):
    ROW = 'row'
    ENTITY = 'entity'
    TIME_RANGE = 'time_range'
    WAFER = 'wafer'
    DIE = 'die'
    SPATIAL = 'spatial'
    CHART_POINT = 'chart_point'
    SERIES = 'series'
    POPULATION = 'population'


class SelectionMutationMode(str, Enum):
    REPLACE = 'replace'
    ADD = 'add'
    REMOVE = 'remove'
    CLEAR = 'clear'


@dataclass(frozen=True, slots=True)
class TimeRange:
    field: str
    start: date | datetime | str
    end: date | datetime | str

    def __post_init__(self) -> None:
        if not self.field.strip():
            raise ValueError('time range field must not be empty')
        if self.start > self.end:
            raise ValueError('time range start must be <= end')


@dataclass(frozen=True, slots=True)
class PopulationDefinition:
    key: str
    label: str | None = None
    filter: FilterExpression | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError('population key must not be empty')
        object.__setattr__(self, 'metadata', dict(self.metadata))


@dataclass(frozen=True, slots=True)
class EntityContext:
    entity_type: str
    entity_id: Any
    label: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entity_type.strip():
            raise ValueError('entity_type must not be empty')
        object.__setattr__(self, 'attributes', dict(self.attributes))


@dataclass(frozen=True, slots=True)
class Selection:
    kind: SelectionKind
    selection_id: str
    values: Mapping[str, Any] = field(default_factory=dict)
    source: str | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        if not self.selection_id.strip():
            raise ValueError('selection_id must not be empty')
        object.__setattr__(self, 'values', dict(self.values))


@dataclass(frozen=True, slots=True)
class SelectionEvent:
    revision: int
    mode: SelectionMutationMode
    selections: tuple[Selection, ...]
    source: str | None = None


@dataclass(frozen=True, slots=True)
class AnalysisContextSnapshot:
    revision: int
    filters: tuple[FilterExpression, ...] = ()
    search: str = ''
    time_range: TimeRange | None = None
    affected: PopulationDefinition | None = None
    control: PopulationDefinition | None = None
    baseline: PopulationDefinition | None = None
    entity: EntityContext | None = None
    source_key: str | None = None
    as_of: str | None = None
    freshness_at: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.revision < 0:
            raise ValueError('analysis context revision must be >= 0')
        object.__setattr__(self, 'filters', tuple(self.filters))
        object.__setattr__(self, 'metadata', dict(self.metadata))


@dataclass(frozen=True, slots=True)
class SelectionSnapshot:
    revision: int
    selections: tuple[Selection, ...] = ()
    history: tuple[tuple[Selection, ...], ...] = ()

    def __post_init__(self) -> None:
        if self.revision < 0:
            raise ValueError('selection revision must be >= 0')
        object.__setattr__(self, 'selections', tuple(self.selections))
        object.__setattr__(self, 'history', tuple(tuple(items) for items in self.history))


@dataclass(frozen=True, slots=True)
class AnalyticalPanelState:
    status: AnalysisStatus = AnalysisStatus.READY
    message: str | None = None
    stale_reason: str | None = None
    partial_reason: str | None = None
    error_type: str | None = None
    revision: int = 0


__all__ = [name for name in globals() if not name.startswith('_')]
