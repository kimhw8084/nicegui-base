from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Any

from .source import DataSource


class DataSourceRegistry:
    """Owns named data sources and disposes them deterministically."""

    def __init__(self) -> None:
        self._sources: dict[str, DataSource] = {}
        self._closed = False

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError('DataSourceRegistry is closed')

    @property
    def sources(self) -> Mapping[str, DataSource]:
        return dict(self._sources)

    def register(self, source: DataSource) -> DataSource:
        self._ensure_open()
        if source.key in self._sources:
            raise ValueError(f'data source already registered: {source.key}')
        self._sources[source.key] = source
        return source

    def unregister(self, key: str) -> DataSource | None:
        self._ensure_open()
        return self._sources.pop(key, None)

    def get(self, key: str) -> DataSource:
        self._ensure_open()
        try:
            return self._sources[key]
        except KeyError:
            raise KeyError(f'unknown data source: {key}') from None

    async def remove(self, key: str) -> bool:
        source = self.unregister(key)
        if source is None: return False
        await source.aclose()
        return True

    async def aclose(self) -> tuple[BaseException, ...]:
        if self._closed:
            return ()
        self._closed = True
        failures: list[BaseException] = []
        for source in reversed(tuple(self._sources.values())):
            try:
                result = source.aclose()
                if inspect.isawaitable(result): await result
            except BaseException as exc:
                failures.append(exc)
        self._sources.clear()
        return tuple(failures)


__all__ = ['DataSourceRegistry']
