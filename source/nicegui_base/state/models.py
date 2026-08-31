from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class StateScope(str, Enum):
    COMPONENT = 'component'
    PAGE = 'page'
    SESSION = 'session'
    USER = 'user'
    TAB = 'tab'
    URL = 'url'


class PageStatus(str, Enum):
    IDLE = 'idle'
    LOADING = 'loading'
    READY = 'ready'
    EMPTY = 'empty'
    ERROR = 'error'
    REFRESHING = 'refreshing'
    STALE = 'stale'


@dataclass(frozen=True, slots=True)
class PageState:
    status: PageStatus = PageStatus.IDLE
    message: str | None = None
    error_id: str | None = None
    last_updated: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status is PageStatus.ERROR and not (self.message or self.error_id):
            raise ValueError('Error PageState requires message or error_id')
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))

    @classmethod
    def ready(cls, *, metadata: Mapping[str, Any] | None = None) -> 'PageState':
        return cls(PageStatus.READY, last_updated=datetime.now(timezone.utc), metadata=metadata or {})


class SidebarPreference(str, Enum):
    EXPANDED = 'expanded'
    COMPACT = 'compact'
    HIDDEN = 'hidden'


@dataclass(frozen=True, slots=True)
class UserPreferences:
    theme: str = 'system'
    density: str = 'compact'
    sidebar: SidebarPreference = SidebarPreference.EXPANDED
    table_states: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    filter_views: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    favorites: tuple[str, ...] = ()
    recent_entities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.theme not in {'light', 'dark', 'system'}:
            raise ValueError('theme must be light, dark, or system')
        if self.density not in {'comfortable', 'compact', 'dense'}:
            raise ValueError('density must be comfortable, compact, or dense')
        object.__setattr__(self, 'table_states', MappingProxyType({k: MappingProxyType(dict(v)) for k, v in self.table_states.items()}))
        object.__setattr__(self, 'filter_views', MappingProxyType({k: MappingProxyType(dict(v)) for k, v in self.filter_views.items()}))

    def to_dict(self) -> dict[str, Any]:
        return {
            'theme': self.theme,
            'density': self.density,
            'sidebar': self.sidebar.value,
            'table_states': {k: dict(v) for k, v in self.table_states.items()},
            'filter_views': {k: dict(v) for k, v in self.filter_views.items()},
            'favorites': list(self.favorites),
            'recent_entities': list(self.recent_entities),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> 'UserPreferences':
        data = dict(data or {})
        return cls(
            theme=data.get('theme', 'system'),
            density=data.get('density', 'compact'),
            sidebar=SidebarPreference(data.get('sidebar', 'expanded')),
            table_states=data.get('table_states', {}),
            filter_views=data.get('filter_views', {}),
            favorites=tuple(data.get('favorites', ())),
            recent_entities=tuple(data.get('recent_entities', ())),
        )
