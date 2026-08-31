from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from .models import Selection, SelectionEvent, SelectionKind, SelectionMutationMode, SelectionSnapshot

SelectionWatcher = Callable[[SelectionEvent], Any]


class SelectionBus:
    """Typed shared selection authority with drill/back history."""
    def __init__(self, *, history_limit: int = 50) -> None:
        if history_limit < 1: raise ValueError('history_limit must be >= 1')
        self._items: list[Selection] = []
        self._history: list[tuple[Selection, ...]] = []
        self._history_limit = history_limit
        self._watchers: list[SelectionWatcher] = []
        self._revision = 0
        self._closed = False

    @property
    def revision(self) -> int: return self._revision
    @property
    def selections(self) -> tuple[Selection, ...]: return tuple(deepcopy(self._items))
    @property
    def can_go_back(self) -> bool: return bool(self._history)
    @property
    def closed(self) -> bool: return self._closed

    def _ensure_open(self):
        if self._closed: raise RuntimeError('SelectionBus is closed')

    def watch(self, callback: SelectionWatcher) -> Callable[[], None]:
        self._ensure_open(); self._watchers.append(callback)
        def unsubscribe():
            if callback in self._watchers: self._watchers.remove(callback)
        return unsubscribe

    def _emit(self, mode: SelectionMutationMode, changed: tuple[Selection, ...], source: str | None) -> SelectionEvent:
        self._revision += 1
        event = SelectionEvent(self._revision, mode, deepcopy(changed), source)
        for callback in tuple(self._watchers): callback(event)
        return event

    @staticmethod
    def _key(item: Selection) -> tuple[SelectionKind, str]: return item.kind, item.selection_id

    def apply(self, selections: Selection | tuple[Selection, ...] | list[Selection] = (), *, mode: SelectionMutationMode = SelectionMutationMode.REPLACE, source: str | None = None) -> SelectionEvent:
        self._ensure_open()
        values = (selections,) if isinstance(selections, Selection) else tuple(selections)
        if mode is SelectionMutationMode.CLEAR:
            changed = tuple(self._items); self._items = []
            return self._emit(mode, changed, source)
        if mode is SelectionMutationMode.REPLACE:
            before = tuple(self._items); self._items = list(deepcopy(values))
            return self._emit(mode, before + tuple(values), source)
        if mode is SelectionMutationMode.ADD:
            existing = {self._key(item) for item in self._items}
            added = tuple(item for item in values if self._key(item) not in existing)
            self._items.extend(deepcopy(list(added)))
            return self._emit(mode, added, source)
        if mode is SelectionMutationMode.REMOVE:
            keys = {self._key(item) for item in values}
            removed = tuple(item for item in self._items if self._key(item) in keys)
            self._items = [item for item in self._items if self._key(item) not in keys]
            return self._emit(mode, removed, source)
        raise ValueError(mode)

    def clear(self, *, source: str | None = None) -> SelectionEvent:
        return self.apply((), mode=SelectionMutationMode.CLEAR, source=source)

    def by_kind(self, kind: SelectionKind) -> tuple[Selection, ...]:
        self._ensure_open(); return tuple(deepcopy(item) for item in self._items if item.kind is kind)

    def drill(self, selections: Selection | tuple[Selection, ...] | list[Selection], *, source: str | None = None) -> SelectionEvent:
        self._ensure_open(); self._history.append(tuple(deepcopy(self._items)))
        if len(self._history) > self._history_limit: self._history.pop(0)
        return self.apply(selections, mode=SelectionMutationMode.REPLACE, source=source)

    def back(self, *, source: str | None = None) -> SelectionEvent | None:
        self._ensure_open()
        if not self._history: return None
        values = self._history.pop()
        return self.apply(values, mode=SelectionMutationMode.REPLACE, source=source)

    def snapshot(self) -> SelectionSnapshot:
        self._ensure_open(); return SelectionSnapshot(self._revision, self.selections, tuple(deepcopy(self._history)))

    def restore(self, snapshot: SelectionSnapshot, *, emit: bool = True, source: str = 'restore') -> None:
        self._ensure_open(); self._items = list(deepcopy(snapshot.selections)); self._history = list(deepcopy(snapshot.history)); self._revision = snapshot.revision
        if emit:
            self._emit(SelectionMutationMode.REPLACE, self.selections, source)

    def close(self) -> None:
        if self._closed: return
        self._closed = True; self._watchers.clear(); self._history.clear()


__all__ = ['SelectionBus', 'SelectionWatcher']
