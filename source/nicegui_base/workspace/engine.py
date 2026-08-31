from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import replace
from typing import Any

from nicegui_base.design import BREAKPOINTS

from .models import GRID_COLUMNS, GridPlacement, PanelSpec, WorkspaceBreakpoint, WorkspaceLayoutSnapshot

LayoutWatcher = Callable[['WorkspaceLayoutEngine'], Any]


_BREAKPOINT_ORDER = (
    WorkspaceBreakpoint.PHONE,
    WorkspaceBreakpoint.TABLET,
    WorkspaceBreakpoint.LAPTOP,
    WorkspaceBreakpoint.DESKTOP,
    WorkspaceBreakpoint.WIDE,
)


class WorkspaceLayoutEngine:
    """Framework-neutral adaptive grid authority for v3 workspaces.

    Existing NiceGUI Base layouts do not opt into this engine automatically. A page can
    migrate panel-by-panel, which preserves the proven v2 renderer while allowing v3
    workspaces to gain deterministic drag/resize persistence and responsive reflow.
    """

    def __init__(self) -> None:
        self._panels: dict[str, PanelSpec] = {}
        self._placements: dict[WorkspaceBreakpoint, dict[str, GridPlacement]] = {
            breakpoint: {} for breakpoint in WorkspaceBreakpoint
        }
        self._registration_order: list[str] = []
        self._watchers: list[LayoutWatcher] = []
        self.revision = 0

    @property
    def panels(self) -> Mapping[str, PanelSpec]:
        return deepcopy(self._panels)

    def watch(self, callback: LayoutWatcher) -> Callable[[], None]:
        self._watchers.append(callback)

        def unsubscribe() -> None:
            if callback in self._watchers:
                self._watchers.remove(callback)

        return unsubscribe

    def _changed(self) -> None:
        self.revision += 1
        for callback in tuple(self._watchers):
            callback(self)

    @staticmethod
    def breakpoint_for_width(width_px: int) -> WorkspaceBreakpoint:
        if width_px < 0:
            raise ValueError('width_px must be >= 0')
        if width_px < int(BREAKPOINTS['phone']):
            return WorkspaceBreakpoint.PHONE
        if width_px < int(BREAKPOINTS['tablet']):
            return WorkspaceBreakpoint.TABLET
        if width_px < int(BREAKPOINTS['laptop']):
            return WorkspaceBreakpoint.LAPTOP
        if width_px < int(BREAKPOINTS['wide']):
            return WorkspaceBreakpoint.DESKTOP
        return WorkspaceBreakpoint.WIDE

    @staticmethod
    def columns(breakpoint: WorkspaceBreakpoint) -> int:
        return GRID_COLUMNS[breakpoint]

    def _normalized_span(self, spec: PanelSpec, breakpoint: WorkspaceBreakpoint, *, column_span: int | None = None, row_span: int | None = None) -> tuple[int, int]:
        columns = self.columns(breakpoint)
        if breakpoint is WorkspaceBreakpoint.PHONE and spec.phone_full_width:
            col_span = columns
        else:
            desired = spec.preferred_columns if column_span is None else column_span
            maximum = columns if spec.max_columns is None else min(columns, spec.max_columns)
            minimum = min(columns, spec.min_columns)
            col_span = max(minimum, min(maximum, desired))
        desired_rows = spec.preferred_rows if row_span is None else row_span
        row_max = spec.max_rows if spec.max_rows is not None else desired_rows
        rows = max(spec.min_rows, min(row_max, desired_rows))
        return col_span, rows

    def register_panel(self, spec: PanelSpec, *, placements: Mapping[WorkspaceBreakpoint, GridPlacement] | None = None) -> None:
        if spec.panel_id in self._panels:
            raise ValueError(f'duplicate panel: {spec.panel_id}')
        self._panels[spec.panel_id] = deepcopy(spec)
        self._registration_order.append(spec.panel_id)
        provided = dict(placements or {})
        try:
            for breakpoint in _BREAKPOINT_ORDER:
                placement = provided.get(breakpoint)
                if placement is not None:
                    self._validate_placement(spec, placement)
                    self._placements[breakpoint][spec.panel_id] = placement
                    self._resolve_collisions(breakpoint, anchor_id=spec.panel_id)
                else:
                    self._placements[breakpoint][spec.panel_id] = self._first_available(spec, breakpoint)
        except BaseException:
            self._panels.pop(spec.panel_id, None)
            self._registration_order.remove(spec.panel_id)
            for values in self._placements.values():
                values.pop(spec.panel_id, None)
            raise
        self._changed()

    def remove_panel(self, panel_id: str) -> bool:
        if panel_id not in self._panels:
            return False
        self._panels.pop(panel_id)
        self._registration_order.remove(panel_id)
        for breakpoint in _BREAKPOINT_ORDER:
            self._placements[breakpoint].pop(panel_id, None)
            self.compact(breakpoint, emit=False)
        self._changed()
        return True

    def placement(self, panel_id: str, breakpoint: WorkspaceBreakpoint) -> GridPlacement:
        try:
            return deepcopy(self._placements[breakpoint][panel_id])
        except KeyError as exc:
            raise KeyError(panel_id) from exc

    def layout(self, breakpoint: WorkspaceBreakpoint) -> tuple[GridPlacement, ...]:
        order = {panel_id: index for index, panel_id in enumerate(self._registration_order)}
        return tuple(
            deepcopy(item)
            for item in sorted(
                self._placements[breakpoint].values(),
                key=lambda item: (item.row, item.column, order[item.panel_id]),
            )
        )

    def layout_for_width(self, width_px: int) -> tuple[GridPlacement, ...]:
        return self.layout(self.breakpoint_for_width(width_px))

    def move(self, panel_id: str, breakpoint: WorkspaceBreakpoint, *, column: int, row: int) -> GridPlacement:
        spec = self._require_panel(panel_id)
        if spec.locked:
            raise PermissionError(f'panel is locked: {panel_id}')
        current = self.placement(panel_id, breakpoint)
        columns = self.columns(breakpoint)
        candidate = replace(
            current,
            column=max(0, min(column, columns - current.column_span)),
            row=max(0, row),
        )
        self._placements[breakpoint][panel_id] = candidate
        self._resolve_collisions(breakpoint, anchor_id=panel_id)
        self.compact(breakpoint, emit=False, pinned_id=panel_id)
        self._changed()
        return self.placement(panel_id, breakpoint)

    def resize(self, panel_id: str, breakpoint: WorkspaceBreakpoint, *, column_span: int, row_span: int) -> GridPlacement:
        spec = self._require_panel(panel_id)
        if spec.locked:
            raise PermissionError(f'panel is locked: {panel_id}')
        current = self.placement(panel_id, breakpoint)
        width, height = self._normalized_span(spec, breakpoint, column_span=column_span, row_span=row_span)
        columns = self.columns(breakpoint)
        candidate = replace(
            current,
            column_span=width,
            row_span=height,
            column=min(current.column, columns - width),
        )
        self._placements[breakpoint][panel_id] = candidate
        self._resolve_collisions(breakpoint, anchor_id=panel_id)
        self.compact(breakpoint, emit=False, pinned_id=panel_id)
        self._changed()
        return self.placement(panel_id, breakpoint)

    def compact(self, breakpoint: WorkspaceBreakpoint, *, emit: bool = True, pinned_id: str | None = None) -> None:
        values = self._placements[breakpoint]
        if not values:
            return
        order = {panel_id: index for index, panel_id in enumerate(self._registration_order)}
        pinned = values.get(pinned_id) if pinned_id is not None else None
        placed: dict[str, GridPlacement] = {}
        if pinned is not None:
            placed[pinned.panel_id] = pinned
        for item in sorted(values.values(), key=lambda p: (p.row, p.column, order[p.panel_id])):
            if item.panel_id == pinned_id:
                continue
            row = 0
            candidate = replace(item, row=0)
            while self._collides(candidate, placed.values()):
                next_rows = [other.bottom for other in placed.values() if self._horizontal_overlap(candidate, other)]
                row = max(row + 1, min(next_rows) if next_rows else row + 1)
                candidate = replace(candidate, row=row)
            placed[item.panel_id] = candidate
        changed = placed != values
        self._placements[breakpoint] = placed
        if changed and emit:
            self._changed()

    def derive_breakpoint(self, target: WorkspaceBreakpoint, *, source: WorkspaceBreakpoint | None = None) -> None:
        if source is None:
            source = self._nearest_populated_breakpoint(target)
        source_columns = self.columns(source)
        target_columns = self.columns(target)
        next_values: dict[str, GridPlacement] = {}
        for panel_id in self._registration_order:
            spec = self._panels[panel_id]
            source_item = self._placements[source].get(panel_id)
            if source_item is None:
                next_values[panel_id] = self._first_available(spec, target, occupied=next_values.values())
                continue
            if target is WorkspaceBreakpoint.PHONE and spec.phone_full_width:
                width = target_columns
                column = 0
            else:
                width, _ = self._normalized_span(
                    spec,
                    target,
                    column_span=max(1, round(source_item.column_span * target_columns / source_columns)),
                    row_span=source_item.row_span,
                )
                column = min(target_columns - width, max(0, round(source_item.column * target_columns / source_columns)))
            _, height = self._normalized_span(spec, target, column_span=width, row_span=source_item.row_span)
            next_values[panel_id] = GridPlacement(panel_id, target, column, source_item.row, width, height)
        self._placements[target] = next_values
        self._resolve_all(target)
        self.compact(target, emit=False)
        self._changed()

    def snapshot(self) -> WorkspaceLayoutSnapshot:
        return WorkspaceLayoutSnapshot(
            schema_version=1,
            revision=self.revision,
            panels=tuple(deepcopy(self._panels[panel_id]) for panel_id in self._registration_order),
            placements=tuple(
                deepcopy(self._placements[breakpoint][panel_id])
                for breakpoint in _BREAKPOINT_ORDER
                for panel_id in self._registration_order
                if panel_id in self._placements[breakpoint]
            ),
        )

    def restore(self, snapshot: WorkspaceLayoutSnapshot) -> None:
        if snapshot.schema_version != 1:
            raise ValueError(f'unsupported workspace snapshot schema {snapshot.schema_version}')
        panels = {panel.panel_id: deepcopy(panel) for panel in snapshot.panels}
        if len(panels) != len(snapshot.panels):
            raise ValueError('snapshot contains duplicate panel ids')
        placements: dict[WorkspaceBreakpoint, dict[str, GridPlacement]] = {breakpoint: {} for breakpoint in WorkspaceBreakpoint}
        for item in snapshot.placements:
            if item.panel_id not in panels:
                raise ValueError(f'placement references unknown panel {item.panel_id!r}')
            self._validate_placement(panels[item.panel_id], item)
            if item.panel_id in placements[item.breakpoint]:
                raise ValueError(f'duplicate placement for {item.panel_id!r} at {item.breakpoint.value}')
            placements[item.breakpoint][item.panel_id] = deepcopy(item)
        for breakpoint, values in placements.items():
            if self._has_collision(values.values()):
                raise ValueError(f'snapshot contains overlapping placements at {breakpoint.value}')
        self._panels = panels
        self._registration_order = [panel.panel_id for panel in snapshot.panels]
        self._placements = placements
        for breakpoint in _BREAKPOINT_ORDER:
            for panel_id in self._registration_order:
                if panel_id not in self._placements[breakpoint]:
                    self._placements[breakpoint][panel_id] = self._first_available(self._panels[panel_id], breakpoint)
        self._changed()

    def css_grid_style(self, panel_id: str, width_px: int) -> str:
        placement = self.placement(panel_id, self.breakpoint_for_width(width_px))
        return (
            f'grid-column:{placement.column + 1} / span {placement.column_span};'
            f'grid-row:{placement.row + 1} / span {placement.row_span};'
        )

    def _require_panel(self, panel_id: str) -> PanelSpec:
        try:
            return self._panels[panel_id]
        except KeyError as exc:
            raise KeyError(panel_id) from exc

    def _validate_placement(self, spec: PanelSpec, placement: GridPlacement) -> None:
        if placement.panel_id != spec.panel_id:
            raise ValueError('placement panel_id does not match panel spec')
        columns = self.columns(placement.breakpoint)
        width, height = self._normalized_span(spec, placement.breakpoint, column_span=placement.column_span, row_span=placement.row_span)
        if width != placement.column_span or height != placement.row_span:
            raise ValueError(f'placement span violates constraints for {spec.panel_id!r}')
        if placement.right > columns:
            raise ValueError(f'placement exceeds {columns}-column {placement.breakpoint.value} grid')

    def _first_available(self, spec: PanelSpec, breakpoint: WorkspaceBreakpoint, *, occupied=None) -> GridPlacement:
        width, height = self._normalized_span(spec, breakpoint)
        columns = self.columns(breakpoint)
        others = tuple(self._placements[breakpoint].values()) if occupied is None else tuple(occupied)
        row = 0
        while True:
            for column in range(0, columns - width + 1):
                candidate = GridPlacement(spec.panel_id, breakpoint, column, row, width, height)
                if not self._collides(candidate, others):
                    return candidate
            row += 1

    @staticmethod
    def _horizontal_overlap(a: GridPlacement, b: GridPlacement) -> bool:
        return not (a.right <= b.column or b.right <= a.column)

    @staticmethod
    def _collides(candidate: GridPlacement, others) -> bool:
        return any(candidate.panel_id != other.panel_id and candidate.intersects(other) for other in others)

    @staticmethod
    def _has_collision(items) -> bool:
        values = tuple(items)
        return any(a.intersects(b) for index, a in enumerate(values) for b in values[index + 1:])

    def _resolve_collisions(self, breakpoint: WorkspaceBreakpoint, *, anchor_id: str) -> None:
        values = self._placements[breakpoint]
        anchor = values[anchor_id]
        order = {panel_id: index for index, panel_id in enumerate(self._registration_order)}
        for panel_id in sorted((key for key in values if key != anchor_id), key=order.__getitem__):
            candidate = values[panel_id]
            if not candidate.intersects(anchor):
                continue
            candidate = replace(candidate, row=anchor.bottom)
            while self._collides(candidate, [item for key, item in values.items() if key != panel_id]):
                candidate = replace(candidate, row=candidate.row + 1)
            values[panel_id] = candidate
        self._resolve_all(breakpoint, anchor_id=anchor_id)

    def _resolve_all(self, breakpoint: WorkspaceBreakpoint, *, anchor_id: str | None = None) -> None:
        values = self._placements[breakpoint]
        order = {panel_id: index for index, panel_id in enumerate(self._registration_order)}
        keys = sorted(values, key=lambda key: (0 if key == anchor_id else 1, values[key].row, values[key].column, order[key]))
        placed: dict[str, GridPlacement] = {}
        for panel_id in keys:
            item = values[panel_id]
            while self._collides(item, placed.values()):
                blockers = [other.bottom for other in placed.values() if self._horizontal_overlap(item, other)]
                item = replace(item, row=max(blockers) if blockers else item.row + 1)
            placed[panel_id] = item
        self._placements[breakpoint] = placed

    def _nearest_populated_breakpoint(self, target: WorkspaceBreakpoint) -> WorkspaceBreakpoint:
        target_index = _BREAKPOINT_ORDER.index(target)
        candidates = sorted(_BREAKPOINT_ORDER, key=lambda item: abs(_BREAKPOINT_ORDER.index(item) - target_index))
        for item in candidates:
            if self._placements[item]:
                return item
        return target


__all__ = ['WorkspaceLayoutEngine']
