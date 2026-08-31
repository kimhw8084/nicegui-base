from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_MOD_ORDER = ('ctrl', 'alt', 'shift', 'meta')
_ALIAS = {'cmd': 'meta', 'command': 'meta', 'control': 'ctrl', 'option': 'alt', 'esc': 'escape', 'return': 'enter'}


def normalize_shortcut(value: str) -> str:
    parts = [p.strip().lower() for p in value.replace('-', '+').split('+') if p.strip()]
    if not parts: raise ValueError('Shortcut must not be empty')
    parts = [_ALIAS.get(p, p) for p in parts]
    modifiers = [m for m in _MOD_ORDER if m in parts]
    keys = [p for p in parts if p not in _MOD_ORDER]
    if len(keys) != 1: raise ValueError('Shortcut must contain exactly one non-modifier key')
    return '+'.join([*modifiers, keys[0]])


@dataclass(frozen=True, slots=True)
class KeyboardShortcut:
    keys: str
    handler: Callable[[], Any]
    description: str
    scope: str = 'page'
    allow_in_input: bool = False

    def __post_init__(self) -> None:
        if not self.description.strip(): raise ValueError('Keyboard shortcut description is required')
        object.__setattr__(self, 'keys', normalize_shortcut(self.keys))


class KeyboardShortcutRegistry:
    def __init__(self): self._items: dict[str, KeyboardShortcut] = {}
    def register(self, shortcut: KeyboardShortcut) -> None:
        if shortcut.keys in self._items: raise ValueError(f'Duplicate shortcut: {shortcut.keys}')
        self._items[shortcut.keys] = shortcut
    def unregister(self, keys: str) -> None: self._items.pop(normalize_shortcut(keys), None)
    def get(self, keys: str) -> KeyboardShortcut | None: return self._items.get(normalize_shortcut(keys))
    def trigger(self, keys: str) -> Any:
        item = self.get(keys); return item.handler() if item else None
    def help(self) -> tuple[tuple[str, str], ...]: return tuple((k, v.description) for k, v in sorted(self._items.items()))
