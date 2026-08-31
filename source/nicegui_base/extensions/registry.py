from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any


class ExtensionKind(str, Enum):
    COMPONENT = 'component'
    DATA_SOURCE = 'data_source'
    COMMAND = 'command'
    VISUALIZATION = 'visualization'
    WORKSPACE_PANEL = 'workspace_panel'


@dataclass(frozen=True, slots=True)
class ExtensionDefinition:
    key: str
    kind: ExtensionKind
    factory: Callable[..., Any]
    version: str = '1.0'
    description: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError('extension key must not be empty')
        if not self.version.strip():
            raise ValueError('extension version must not be empty')
        object.__setattr__(self, 'metadata', MappingProxyType(deepcopy(dict(self.metadata))))


class ExtensionRegistry:
    """Explicit v3 extension boundary with deterministic ownership and no import magic."""

    def __init__(self) -> None:
        self._items: dict[tuple[ExtensionKind, str], ExtensionDefinition] = {}

    def register(self, definition: ExtensionDefinition) -> ExtensionDefinition:
        address = (definition.kind, definition.key)
        if address in self._items:
            raise ValueError(f'duplicate {definition.kind.value} extension: {definition.key}')
        self._items[address] = definition
        return definition

    def unregister(self, kind: ExtensionKind, key: str) -> bool:
        return self._items.pop((kind, key), None) is not None

    def get(self, kind: ExtensionKind, key: str) -> ExtensionDefinition | None:
        return self._items.get((kind, key))

    def require(self, kind: ExtensionKind, key: str) -> ExtensionDefinition:
        item = self.get(kind, key)
        if item is None:
            raise KeyError(f'{kind.value}:{key}')
        return item

    def create(self, kind: ExtensionKind, key: str, *args: Any, **kwargs: Any) -> Any:
        return self.require(kind, key).factory(*args, **kwargs)

    def list(self, kind: ExtensionKind | None = None) -> tuple[ExtensionDefinition, ...]:
        values = [item for (item_kind, _), item in self._items.items() if kind is None or item_kind is kind]
        return tuple(sorted(values, key=lambda item: (item.kind.value, item.key)))

    def decorator(self, kind: ExtensionKind, key: str, *, version: str = '1.0', description: str | None = None, metadata: Mapping[str, Any] | None = None):
        def register(factory: Callable[..., Any]):
            self.register(ExtensionDefinition(key, kind, factory, version, description, metadata or {}))
            return factory
        return register

    def component(self, key: str, **kwargs: Any):
        return self.decorator(ExtensionKind.COMPONENT, key, **kwargs)

    def data_source(self, key: str, **kwargs: Any):
        return self.decorator(ExtensionKind.DATA_SOURCE, key, **kwargs)

    def command(self, key: str, **kwargs: Any):
        return self.decorator(ExtensionKind.COMMAND, key, **kwargs)

    def visualization(self, key: str, **kwargs: Any):
        return self.decorator(ExtensionKind.VISUALIZATION, key, **kwargs)

    def workspace_panel(self, key: str, **kwargs: Any):
        return self.decorator(ExtensionKind.WORKSPACE_PANEL, key, **kwargs)


__all__ = ['ExtensionDefinition', 'ExtensionKind', 'ExtensionRegistry']
