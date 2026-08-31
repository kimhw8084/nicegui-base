from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar

from .context import AnalysisContext
from .selection import SelectionBus

T = TypeVar('T')


class AnalysisBinding(Generic[T]):
    """Refresh a consumer from AnalysisContext with latest-request-wins semantics."""
    def __init__(self, context: AnalysisContext, loader: Callable[[AnalysisContext], T | Awaitable[T]], consumer: Callable[[T], Any | Awaitable[Any]], *, auto: bool = True) -> None:
        self.context=context; self.loader=loader; self.consumer=consumer; self._task: asyncio.Task[Any] | None=None; self._generation=0; self._closed=False
        self._unsubscribe = context.watch(lambda _context: self.request_refresh()) if auto else None

    def request_refresh(self) -> asyncio.Task[Any] | None:
        if self._closed: return None
        try: loop=asyncio.get_running_loop()
        except RuntimeError: return None
        self._generation += 1; generation=self._generation
        if self._task and not self._task.done(): self._task.cancel()
        self._task=loop.create_task(self._run(generation), name='nicegui-base-analysis-binding')
        return self._task

    async def refresh(self) -> None:
        if self._closed: raise RuntimeError('AnalysisBinding is closed')
        self._generation += 1; generation=self._generation
        if self._task and self._task is not asyncio.current_task() and not self._task.done(): self._task.cancel()
        await self._run(generation)

    async def _run(self, generation: int) -> None:
        value=self.loader(self.context); value=await value if inspect.isawaitable(value) else value
        if self._closed or generation != self._generation: return
        result=self.consumer(value)
        if inspect.isawaitable(result): await result

    async def aclose(self) -> None:
        if self._closed: return
        self._closed=True
        if self._unsubscribe: self._unsubscribe(); self._unsubscribe=None
        if self._task and not self._task.done():
            self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass


class AnalysisCoordinator:
    """Default selection→analysis-context translation without page callback plumbing."""
    def __init__(self, context: AnalysisContext, selections: SelectionBus) -> None:
        self.context=context; self.selections=selections; self._selection_filters: tuple[Any, ...]=(); self._unsubscribe=selections.watch(self._on_selection); self._closed=False

    def _on_selection(self, event) -> None:
        # Typed selections can carry a ready-to-apply query expression. This keeps the
        # bus generic while allowing table/chart/wafer adapters to cross-filter.
        expressions=[]
        for item in self.selections.selections:
            expression=item.values.get('filter')
            if expression is not None: expressions.append(expression)
        base=tuple(item for item in self.context.filters if item not in self._selection_filters)
        self._selection_filters=tuple(expressions)
        self.context.set_filters(base+self._selection_filters)

    def close(self) -> None:
        if self._closed:return
        self._closed=True; self._unsubscribe()


__all__=['AnalysisBinding','AnalysisCoordinator']
