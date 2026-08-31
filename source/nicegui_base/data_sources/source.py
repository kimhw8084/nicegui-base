from __future__ import annotations

import abc
import asyncio
from typing import Any

from .models import AggregateResult, DataSchema, DistinctResult, QueryResult, SourceCapabilities, SourceHealth
from .query import AggregateQuery, Query


class DataSource(abc.ABC):
    """Async, provider-neutral analytical data boundary.

    Providers validate every referenced field against ``schema()`` and should push
    filter/sort/pagination/aggregation work to their backend whenever capabilities
    declare that support.
    """

    def __init__(self, key: str, *, timeout_seconds: float | None = 30.0) -> None:
        cleaned = str(key).strip()
        if not cleaned:
            raise ValueError('data source key must not be empty')
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError('timeout_seconds must be > 0')
        self.key = cleaned
        self.timeout_seconds = timeout_seconds
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    @abc.abstractmethod
    def provider(self) -> str: ...

    @property
    @abc.abstractmethod
    def capabilities(self) -> SourceCapabilities: ...

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError(f'DataSource {self.key!r} is closed')

    async def _run_with_timeout(self, awaitable):
        self._ensure_open()
        if self.timeout_seconds is None:
            return await awaitable
        return await asyncio.wait_for(awaitable, timeout=self.timeout_seconds)

    @abc.abstractmethod
    async def schema(self) -> DataSchema: ...

    @abc.abstractmethod
    async def query(self, query: Query = Query()) -> QueryResult: ...

    @abc.abstractmethod
    async def aggregate(self, query: AggregateQuery) -> AggregateResult: ...

    async def count(self, query: Query = Query()) -> int:
        result = await self.query(Query(filter=query.filter, search=query.search, search_fields=query.search_fields, limit=1))
        return result.filtered_total

    @abc.abstractmethod
    async def distinct(self, field: str, query: Query = Query()) -> DistinctResult: ...

    @abc.abstractmethod
    async def health(self) -> SourceHealth: ...

    async def aclose(self) -> None:
        self._closed = True

    async def __aenter__(self) -> 'DataSource':
        self._ensure_open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        await self.aclose()
        return False


__all__ = ['DataSource']
