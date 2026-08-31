from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

BoolResolver = bool | Callable[[], bool]


def _resolve(value: BoolResolver) -> bool:
    return bool(value() if callable(value) else value)


def _subsequence(needle: str, haystack: str) -> bool:
    it = iter(haystack)
    return all(any(ch == candidate for candidate in it) for ch in needle)


@dataclass(frozen=True, slots=True)
class Command:
    key: str
    label: str
    handler: Callable[[], Any]
    keywords: tuple[str, ...] = ()
    shortcut: str | None = None
    group: str = 'General'
    description: str | None = None
    enabled: BoolResolver = True
    visible: BoolResolver = True

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError('Command key and label required')
        if any(not item.strip() for item in self.keywords):
            raise ValueError('Command keywords must not contain empty values')

    @property
    def is_enabled(self) -> bool:
        return _resolve(self.enabled)

    @property
    def is_visible(self) -> bool:
        return _resolve(self.visible)


class CommandRegistry:
    """Deterministic command registry with fuzzy ranking and recent-command memory."""

    def __init__(self, *, recent_limit: int = 8):
        if recent_limit < 0:
            raise ValueError('recent_limit must be >= 0')
        self._items: dict[str, Command] = {}
        self._recent: list[str] = []
        self.recent_limit = recent_limit

    def register(self, command: Command) -> None:
        if command.key in self._items:
            raise ValueError(f'Duplicate command: {command.key}')
        self._items[command.key] = command

    def unregister(self, key: str) -> None:
        self._items.pop(key, None)
        self._recent = [item for item in self._recent if item != key]

    def get(self, key: str) -> Command | None:
        return self._items.get(key)

    @property
    def recent(self) -> tuple[Command, ...]:
        return tuple(self._items[key] for key in self._recent if key in self._items and self._items[key].is_visible)

    def _remember(self, key: str) -> None:
        if self.recent_limit == 0:
            return
        self._recent = [item for item in self._recent if item != key]
        self._recent.insert(0, key)
        del self._recent[self.recent_limit:]

    def execute(self, key: str) -> Any:
        command = self._items.get(key)
        if command is None or not command.is_visible:
            raise KeyError(key)
        if not command.is_enabled:
            raise PermissionError(f'Command is disabled: {key}')
        value = command.handler()
        if inspect.isawaitable(value):
            async def finish():
                result = await value
                self._remember(key)
                return result
            return finish()
        self._remember(key)
        return value

    @staticmethod
    def _score(command: Command, query: str) -> tuple[int, int, str, str]:
        label = command.label.casefold()
        key = command.key.casefold()
        group = command.group.casefold()
        keywords = tuple(item.casefold() for item in command.keywords)
        words = tuple(label.replace('-', ' ').replace('_', ' ').split())
        if label == query or key == query:
            rank = 0
        elif label.startswith(query):
            rank = 1
        elif key.startswith(query):
            rank = 2
        elif any(word.startswith(query) for word in words):
            rank = 3
        elif any(item.startswith(query) for item in keywords):
            rank = 4
        elif query in label:
            rank = 5
        elif query in key or any(query in item for item in keywords) or query in group:
            rank = 6
        elif _subsequence(query, label) or _subsequence(query, key):
            rank = 7
        else:
            rank = 99
        return rank, len(label), command.group.casefold(), label

    def search(self, query: str = '', *, limit: int = 20) -> tuple[Command, ...]:
        if limit < 1:
            return ()
        q = query.strip().casefold()
        visible = [item for item in self._items.values() if item.is_visible]
        if not q:
            recent_keys = {item.key for item in self.recent}
            ordered = [*self.recent, *sorted((item for item in visible if item.key not in recent_keys), key=lambda c: (c.group.casefold(), c.label.casefold()))]
            return tuple(ordered[:limit])
        scored = [(self._score(item, q), item) for item in visible]
        matched = [pair for pair in scored if pair[0][0] < 99]
        matched.sort(key=lambda pair: pair[0])
        return tuple(item for _, item in matched[:limit])
