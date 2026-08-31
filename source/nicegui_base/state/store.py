from __future__ import annotations

from collections.abc import Callable, Iterator, MutableMapping
from contextlib import contextmanager
from copy import deepcopy
from typing import Any


Watcher = Callable[[str, Any, Any], None]


class StateStore(MutableMapping[str, Any]):
    """Small observable state container with atomic batch updates.

    The store intentionally stays UI-framework agnostic. It can wrap an in-memory
    dictionary, NiceGUI storage, Redis-backed mappings, or a test fake.
    """

    def __init__(self, initial: dict[str, Any] | None = None, *, backing: MutableMapping[str, Any] | None = None):
        self._data: MutableMapping[str, Any] = backing if backing is not None else {}
        if initial:
            self._data.update(deepcopy(initial))
        self._watchers: list[Watcher] = []
        self._key_watchers: dict[str, list[Watcher]] = {}
        self._batch_depth = 0
        self._pending: dict[str, tuple[Any, Any]] = {}
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError(f'{type(self).__name__} is closed')

    def __getitem__(self, key: str) -> Any:
        self._ensure_open(); return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._ensure_open(); old = self._data.get(key)
        if old == value:
            return
        self._data[key] = value
        if self._batch_depth:
            first_old = self._pending.get(key, (old, value))[0]
            self._pending[key] = (first_old, value)
        else:
            self._notify(key, old, value)

    def __delitem__(self, key: str) -> None:
        self._ensure_open(); old = self._data[key]
        del self._data[key]
        if self._batch_depth:
            self._pending[key] = (old, None)
        else:
            self._notify(key, old, None)

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def watch(self, callback: Watcher) -> Callable[[], None]:
        self._ensure_open(); self._watchers.append(callback)
        def unsubscribe() -> None:
            if callback in self._watchers:
                self._watchers.remove(callback)
        return unsubscribe

    def watch_key(self, key: str, callback: Watcher) -> Callable[[], None]:
        self._ensure_open(); self._key_watchers.setdefault(key, []).append(callback)
        def unsubscribe() -> None:
            items=self._key_watchers.get(key, [])
            if callback in items: items.remove(callback)
            if not items: self._key_watchers.pop(key, None)
        return unsubscribe

    def set_many(self, values: dict[str, Any]) -> None:
        with self.batch():
            for key, value in values.items():
                self[key] = value

    @contextmanager
    def batch(self):
        self._batch_depth += 1
        try:
            yield self
        finally:
            self._batch_depth -= 1
            if self._batch_depth == 0 and self._pending:
                pending = self._pending
                self._pending = {}
                for key, (old, new) in pending.items():
                    if old != new:
                        self._notify(key, old, new)

    def snapshot(self) -> dict[str, Any]:
        self._ensure_open(); return deepcopy(dict(self._data))

    def close(self, *, clear: bool = False) -> None:
        if self._closed: return
        self._closed=True; self._watchers.clear(); self._key_watchers.clear(); self._pending.clear(); self._batch_depth=0
        if clear: self._data.clear()

    def _notify(self, key: str, old: Any, new: Any) -> None:
        for watcher in tuple(self._watchers):
            watcher(key, old, new)
        for watcher in tuple(self._key_watchers.get(key, ())):
            watcher(key, old, new)


class SessionState(StateStore):
    """Session-scoped observable state. Values survive ``close`` by default."""
    scope = 'session'

    def close(self, *, clear: bool = False) -> None:
        super().close(clear=clear)


class BrowserState(StateStore):
    """Logical browser/user preference state.

    On NiceGUI this should normally bind to app.storage.user rather than
    app.storage.browser because browser storage becomes read-only after response.
    """


class TabState(StateStore):
    """Tab/workspace-local state that clears its values when closed."""
    scope = 'tab'

    def close(self, *, clear: bool = True) -> None:
        super().close(clear=clear)
