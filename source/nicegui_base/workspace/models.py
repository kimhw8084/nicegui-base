from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class WorkspaceBreakpoint(str, Enum):
    PHONE = 'phone'
    TABLET = 'tablet'
    LAPTOP = 'laptop'
    DESKTOP = 'desktop'
    WIDE = 'wide'


GRID_COLUMNS: Mapping[WorkspaceBreakpoint, int] = {
    WorkspaceBreakpoint.PHONE: 4,
    WorkspaceBreakpoint.TABLET: 8,
    WorkspaceBreakpoint.LAPTOP: 12,
    WorkspaceBreakpoint.DESKTOP: 12,
    WorkspaceBreakpoint.WIDE: 16,
}


@dataclass(frozen=True, slots=True)
class PanelSpec:
    panel_id: str
    preferred_columns: int = 6
    preferred_rows: int = 4
    min_columns: int = 2
    max_columns: int | None = None
    min_rows: int = 2
    max_rows: int | None = None
    phone_full_width: bool = True
    locked: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.panel_id.strip():
            raise ValueError('panel_id must not be empty')
        if self.min_columns < 1 or self.preferred_columns < 1:
            raise ValueError('panel column spans must be >= 1')
        if self.min_rows < 1 or self.preferred_rows < 1:
            raise ValueError('panel row spans must be >= 1')
        if self.max_columns is not None and self.max_columns < self.min_columns:
            raise ValueError('max_columns must be >= min_columns')
        if self.max_rows is not None and self.max_rows < self.min_rows:
            raise ValueError('max_rows must be >= min_rows')


@dataclass(frozen=True, slots=True)
class GridPlacement:
    panel_id: str
    breakpoint: WorkspaceBreakpoint
    column: int
    row: int
    column_span: int
    row_span: int

    def __post_init__(self) -> None:
        if not self.panel_id.strip():
            raise ValueError('panel_id must not be empty')
        if self.column < 0 or self.row < 0:
            raise ValueError('grid coordinates must be >= 0')
        if self.column_span < 1 or self.row_span < 1:
            raise ValueError('grid spans must be >= 1')

    @property
    def right(self) -> int:
        return self.column + self.column_span

    @property
    def bottom(self) -> int:
        return self.row + self.row_span

    def intersects(self, other: 'GridPlacement') -> bool:
        if self.breakpoint is not other.breakpoint:
            return False
        return not (
            self.right <= other.column
            or other.right <= self.column
            or self.bottom <= other.row
            or other.bottom <= self.row
        )


@dataclass(frozen=True, slots=True)
class WorkspaceLayoutSnapshot:
    schema_version: int
    revision: int
    panels: tuple[PanelSpec, ...]
    placements: tuple[GridPlacement, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f'unsupported workspace snapshot schema {self.schema_version}')
        if self.revision < 0:
            raise ValueError('revision must be >= 0')


__all__ = [
    'GRID_COLUMNS', 'GridPlacement', 'PanelSpec', 'WorkspaceBreakpoint', 'WorkspaceLayoutSnapshot',
]

class DockPosition(str, Enum):
    NONE = 'none'
    LEFT = 'left'
    RIGHT = 'right'
    TOP = 'top'
    BOTTOM = 'bottom'


@dataclass(frozen=True, slots=True)
class PanelInteractionState:
    panel_id: str
    collapsed: bool = False
    hidden: bool = False
    locked: bool = False
    dock: DockPosition = DockPosition.NONE
    split_group: str | None = None

    def __post_init__(self) -> None:
        if not self.panel_id.strip():
            raise ValueError('panel_id must not be empty')
        if self.split_group is not None and not self.split_group.strip():
            raise ValueError('split_group must not be empty')


@dataclass(frozen=True, slots=True)
class WorkspaceInteractionSnapshot:
    revision: int
    states: tuple[PanelInteractionState, ...] = ()

    def __post_init__(self) -> None:
        if self.revision < 0:
            raise ValueError('workspace interaction revision must be >= 0')
        ids = [item.panel_id for item in self.states]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate workspace interaction panel ids')


__all__ = [name for name in globals() if not name.startswith('_')]
