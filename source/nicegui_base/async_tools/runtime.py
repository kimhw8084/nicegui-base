from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable, Hashable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from nicegui_base.performance import RetryPolicy, TTLCache

from .models import DuplicatePolicy, RefreshStatus, TaskStatus

T = TypeVar('T')


async def _maybe_await(value: T | Awaitable[T]) -> T:
    return await value if inspect.isawaitable(value) else value


class AsyncAction(Generic[T]):
    """Duplicate-safe async action with timeout, retry and deterministic teardown.

    ``IGNORE`` coalesces duplicate callers onto the current task,
    ``CANCEL_PREVIOUS`` provides latest-action-wins semantics, and ``ALLOW`` keeps
    every task independently tracked instead of overwriting a single task handle.
    Retry is opt-in and requires the caller to explicitly declare the operation
    idempotent so mutations are never retried accidentally.
    """
    def __init__(self, *, timeout: float | None = None, duplicate_policy: DuplicatePolicy = DuplicatePolicy.IGNORE):
        self.timeout = timeout
        self.duplicate_policy = duplicate_policy
        self.status = TaskStatus.IDLE
        self.last_result: T | None = None
        self.last_error: BaseException | None = None
        self._task: asyncio.Task[T] | None = None
        self._tasks: set[asyncio.Task[T]] = set()
        self._generation = 0
        self._closed = False

    @property
    def running(self) -> bool:
        return any(not task.done() for task in self._tasks)

    @property
    def active_count(self) -> int:
        return sum(not task.done() for task in self._tasks)

    @property
    def closed(self) -> bool:
        return self._closed

    async def run(self, operation: Callable[[], T | Awaitable[T]], *, retry_policy: RetryPolicy | None = None,
                  retry_if: Callable[[BaseException], bool] | None = None, idempotent: bool = False) -> T | None:
        if self._closed:
            raise RuntimeError('AsyncAction is closed')
        if retry_policy is not None and not idempotent:
            raise ValueError('retry_policy requires idempotent=True')
        if self.running:
            if self.duplicate_policy is DuplicatePolicy.IGNORE and self._task is not None:
                return await asyncio.shield(self._task)
            if self.duplicate_policy is DuplicatePolicy.CANCEL_PREVIOUS:
                await self.cancel()

        self._generation += 1
        generation = self._generation

        async def invoke() -> T:
            async def once() -> T:
                value = operation()
                if self.timeout is None:
                    return await _maybe_await(value)
                return await asyncio.wait_for(_maybe_await(value), timeout=self.timeout)
            if retry_policy is not None:
                return await retry_policy.run(once, retry_if=retry_if)
            return await once()

        self.status = TaskStatus.RUNNING
        self.last_error = None
        task = asyncio.create_task(invoke())
        self._tasks.add(task)
        self._task = task
        try:
            result = await task
            if generation == self._generation:
                self.last_result = result
                self.last_error = None
                self.status = TaskStatus.SUCCESS
            return result
        except asyncio.CancelledError:
            if generation == self._generation:
                self.status = TaskStatus.CANCELLED
            raise
        except BaseException as exc:
            if generation == self._generation:
                self.last_error = exc
                self.status = TaskStatus.ERROR
            raise
        finally:
            self._tasks.discard(task)
            if self._task is task:
                self._task = None
            if generation == self._generation and self._tasks and self.status is not TaskStatus.ERROR:
                self.status = TaskStatus.RUNNING

    async def cancel(self) -> bool:
        task = self._task
        if task is None or task.done():
            return False
        self._generation += 1
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self.status = TaskStatus.CANCELLED
        self._tasks.discard(task)
        if self._task is task:
            self._task = None
        return True

    async def cancel_all(self) -> int:
        tasks = tuple(task for task in self._tasks if not task.done())
        if not tasks:
            return 0
        self._generation += 1
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._task = None
        self.status = TaskStatus.CANCELLED
        return len(tasks)

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self.cancel_all()


class AsyncLoader(AsyncAction[T]):
    """Reloadable latest-request loader for read-oriented async content."""
    def __init__(self, *, timeout: float | None = None):
        super().__init__(timeout=timeout, duplicate_policy=DuplicatePolicy.CANCEL_PREVIOUS)
        self._loader: Callable[[], T | Awaitable[T]] | None = None

    async def load(self, loader: Callable[[], T | Awaitable[T]]) -> T | None:
        self._loader = loader
        return await self.run(loader)

    async def reload(self) -> T | None:
        if self._loader is None:
            raise RuntimeError('AsyncLoader has no previous loader; call load(...) first')
        return await self.run(self._loader)


class CancelableTask(AsyncAction[T]):
    def __init__(self, *, timeout: float | None = None):
        super().__init__(timeout=timeout, duplicate_policy=DuplicatePolicy.CANCEL_PREVIOUS)


@dataclass(slots=True)
class ProgressSnapshot:
    value: float = 0.0
    label: str | None = None


class ProgressTask(AsyncAction[T]):
    def __init__(self, *, timeout: float | None = None):
        super().__init__(timeout=timeout, duplicate_policy=DuplicatePolicy.IGNORE)
        self.progress = ProgressSnapshot()

    def update_progress(self, value: float, label: str | None = None) -> None:
        if not 0 <= value <= 1:
            raise ValueError('Progress must be between 0 and 1')
        self.progress = ProgressSnapshot(value, label)


class Debouncer:
    def __init__(self, delay_seconds: float):
        if delay_seconds < 0: raise ValueError('delay_seconds must be >= 0')
        self.delay = delay_seconds; self._task: asyncio.Task[Any] | None = None; self._generation = 0

    async def call(self, operation: Callable[[], T | Awaitable[T]]) -> T | None:
        self._generation += 1; generation = self._generation
        if self._task and not self._task.done(): self._task.cancel()
        async def invoke():
            await asyncio.sleep(self.delay)
            if generation != self._generation: return None
            return await _maybe_await(operation())
        self._task = asyncio.create_task(invoke())
        try: return await self._task
        except asyncio.CancelledError: return None
        finally:
            if self._task and self._task.done(): self._task = None


class Throttler:
    def __init__(self, interval_seconds: float):
        if interval_seconds <= 0: raise ValueError('interval_seconds must be > 0')
        self.interval = interval_seconds; self._last = 0.0

    async def call(self, operation: Callable[[], T | Awaitable[T]]) -> T | None:
        now = time.monotonic()
        if now - self._last < self.interval: return None
        self._last = now
        return await _maybe_await(operation())


class StaleResponseGuard:
    """Generation token preventing older async responses from overwriting newer state."""
    def __init__(self): self._generation = 0
    def next(self) -> int: self._generation += 1; return self._generation
    def is_current(self, token: int) -> bool: return token == self._generation


class LatestRequestController(Generic[T]):
    """Latest-request-wins controller for idempotent server reads.

    Identical in-flight keys coalesce, a new key cancels the prior request,
    request generations reject stale completion, optional TTL cache prevents
    avoidable repeat fetches, and bounded retry/timeout are applied centrally.
    """

    def __init__(self, *, timeout: float | None = None, retry_policy: RetryPolicy | None = None,
                 cache_size: int = 0, cache_ttl_seconds: float = 15.0, cancel_previous: bool = True):
        self.timeout = timeout
        self.retry_policy = retry_policy
        self.cancel_previous = cancel_previous
        self._cache = TTLCache[T](maxsize=cache_size, ttl_seconds=cache_ttl_seconds) if cache_size > 0 else None
        self._generation = 0
        self._active_key: Hashable | None = None
        self._active_task: asyncio.Task[T] | None = None
        self._tasks: set[asyncio.Task[T]] = set()
        self._closed = False

    @property
    def running(self) -> bool:
        return self._active_task is not None and not self._active_task.done()

    @property
    def request_id(self) -> int:
        return self._generation

    @property
    def closed(self) -> bool:
        return self._closed

    async def run(self, key: Hashable, operation: Callable[[], T | Awaitable[T]], *, refresh: bool = False,
                  retry_if: Callable[[BaseException], bool] | None = None) -> T | None:
        if self._closed:
            raise RuntimeError('LatestRequestController is closed')
        if self._cache is not None and not refresh:
            cached = self._cache.get(key, _CACHE_MISS)
            if cached is not _CACHE_MISS:
                return cached
        if self.running and self._active_task is not None:
            if key == self._active_key:
                task = self._active_task
                request_id = self._generation
                try:
                    return await asyncio.shield(task)
                except asyncio.CancelledError:
                    if self._closed or request_id != self._generation:
                        return None
                    raise
            if self.cancel_previous:
                await self.cancel()

        self._generation += 1
        request_id = self._generation

        async def invoke() -> T:
            async def once() -> T:
                value = operation()
                awaited = _maybe_await(value)
                if self.timeout is None:
                    return await awaited
                return await asyncio.wait_for(awaited, timeout=self.timeout)
            if self.retry_policy is not None:
                return await self.retry_policy.run(once, retry_if=retry_if)
            return await once()

        task = asyncio.create_task(invoke())
        self._tasks.add(task)
        self._active_key = key
        self._active_task = task
        try:
            result = await task
            if self._closed or request_id != self._generation:
                return None
            if self._cache is not None:
                self._cache.set(key, result)
            return result
        except asyncio.CancelledError:
            if request_id != self._generation or self._closed:
                return None
            raise
        finally:
            self._tasks.discard(task)
            if self._active_task is task:
                self._active_task = None
                self._active_key = None

    async def cancel(self) -> bool:
        task = self._active_task
        if task is None or task.done():
            return False
        self._generation += 1
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        if self._active_task is task:
            self._active_task = None
            self._active_key = None
        return True

    def invalidate(self, key: Hashable | None = None) -> None:
        if self._cache is None:
            return
        if key is None:
            self._cache.clear()
        else:
            self._cache.pop(key, None)

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._generation += 1
        tasks = tuple(task for task in self._tasks if not task.done())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._active_task = None
        self._active_key = None
        if self._cache is not None:
            self._cache.clear()


_CACHE_MISS = object()


class AutoRefreshController:
    def __init__(self, operation: Callable[[], Any | Awaitable[Any]], *, interval_seconds: float = 60,
                 stale_after_seconds: float = 300, run_immediately: bool = False):
        if interval_seconds < 1: raise ValueError('interval_seconds must be >= 1')
        self.operation = operation; self.interval = interval_seconds; self.run_immediately = run_immediately
        self.status = RefreshStatus(stale_after_seconds=stale_after_seconds)
        self._task: asyncio.Task[Any] | None = None; self._stop = asyncio.Event()
        self._loader = CancelableTask()

    @property
    def running(self) -> bool: return self._task is not None and not self._task.done()

    async def refresh_now(self) -> Any:
        self.status.last_attempt = datetime.now(timezone.utc); self.status.refreshing = True
        try:
            result = await self._loader.run(self.operation)
            self.status.last_success = datetime.now(timezone.utc); self.status.last_error = None
            return result
        except BaseException as exc:
            self.status.last_error = str(exc); raise
        finally: self.status.refreshing = False

    def start(self) -> None:
        if self.running: return
        self._stop = asyncio.Event()
        async def loop():
            if self.run_immediately:
                try: await self.refresh_now()
                except Exception: pass
            while not self._stop.is_set():
                try: await asyncio.wait_for(self._stop.wait(), timeout=self.interval)
                except asyncio.TimeoutError:
                    try: await self.refresh_now()
                    except Exception: pass
        self._task = asyncio.create_task(loop())

    async def stop(self) -> None:
        self._stop.set()
        await self._loader.cancel()
        if self._task:
            try: await self._task
            except asyncio.CancelledError: pass
        self._task = None
