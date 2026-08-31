from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Sequence


class FilterKind(str, Enum):
    TEXT = 'text'
    SELECT = 'select'
    MULTI_SELECT = 'multi_select'
    DATE_RANGE = 'date_range'
    NUMBER_RANGE = 'number_range'
    STATUS = 'status'
    BOOLEAN = 'boolean'


class FilterPersistence(str, Enum):
    NONE = 'none'
    SESSION = 'session'
    USER = 'user'
    URL = 'url'


@dataclass(frozen=True, slots=True)
class FilterDefinition:
    key: str
    label: str
    kind: FilterKind
    placeholder: str | None = None
    options: Sequence[str] = field(default_factory=tuple)
    default: object | None = None
    advanced: bool = False
    persistence: FilterPersistence = FilterPersistence.SESSION

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError('FilterDefinition requires key and label')


@dataclass(frozen=True, slots=True)
class ActiveFilter:
    key: str
    label: str
    display_value: str
    value: object
    removable: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip() or not self.display_value.strip():
            raise ValueError('ActiveFilter requires key, label, and display value')


@dataclass(frozen=True, slots=True)
class FilterBarSpec:
    filters: Sequence[FilterDefinition] = field(default_factory=tuple)
    active: Sequence[ActiveFilter] = field(default_factory=tuple)
    compact_after: int = 4
    show_clear_all: bool = True
    show_active_count: bool = True

    def __post_init__(self) -> None:
        if self.compact_after < 1:
            raise ValueError('compact_after must be >= 1')

    @property
    def active_count(self) -> int:
        return len(self.active)

    @property
    def has_advanced(self) -> bool:
        return any(item.advanced for item in self.filters)


@dataclass(frozen=True, slots=True)
class FilterPreset:
    key: str
    label: str
    values: Mapping[str, object] = field(default_factory=dict)
    description: str | None = None
    shared: bool = False

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError('FilterPreset requires key and label')
        object.__setattr__(self, 'values', MappingProxyType(dict(self.values)))


@dataclass(frozen=True, slots=True)
class SavedFilterView:
    key: str
    label: str
    values: Mapping[str, object] = field(default_factory=dict)
    is_default: bool = False

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError('SavedFilterView requires key and label')
        object.__setattr__(self, 'values', MappingProxyType(dict(self.values)))
