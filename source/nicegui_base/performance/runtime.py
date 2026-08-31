from __future__ import annotations
import asyncio, inspect, random, time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
T=TypeVar('T')


Cleanup = Callable[[], Any | Awaitable[Any]]


class LifecycleScope:
    """Own cleanup for tasks, listeners, timers and expensive resources.

    A scope is deliberately framework-neutral so NiceGUI integrations, services,
    charts and data surfaces can share one deterministic reverse-order teardown
    contract. Async tasks are cancelled first, then registered cleanup callbacks
    run exactly once. Cleanup failures are returned to the caller so one broken
    resource cannot prevent the remaining resources from being released.
    """

    def __init__(self) -> None:
        self._cleanups: list[tuple[object, Cleanup]] = []
        self._tasks: set[asyncio.Task[Any]] = set()
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def active_task_count(self) -> int:
        return sum(not task.done() for task in self._tasks)

    @property
    def cleanup_count(self) -> int:
        return len(self._cleanups)

    def register(self, cleanup: Cleanup, *, key: object | None = None) -> Callable[[], None]:
        if self._closed:
            raise RuntimeError('LifecycleScope is closed')
        token = key if key is not None else object()
        if key is not None:
            self.unregister(key)
        self._cleanups.append((token, cleanup))

        def unregister() -> None:
            self.unregister(token)

        return unregister

    def unregister(self, key: object) -> bool:
        before = len(self._cleanups)
        self._cleanups[:] = [(token, callback) for token, callback in self._cleanups if token != key]
        return len(self._cleanups) != before

    def track_task(self, task: asyncio.Task[T]) -> asyncio.Task[T]:
        if self._closed:
            task.cancel()
            raise RuntimeError('LifecycleScope is closed')
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def create_task(self, awaitable: Awaitable[T], *, name: str | None = None) -> asyncio.Task[T]:
        return self.track_task(asyncio.create_task(awaitable, name=name))

    async def aclose(self) -> tuple[BaseException, ...]:
        if self._closed:
            return ()
        self._closed = True
        tasks = tuple(task for task in self._tasks if not task.done())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

        failures: list[BaseException] = []
        cleanups = list(reversed(self._cleanups))
        self._cleanups.clear()
        for _, cleanup in cleanups:
            try:
                value = cleanup()
                if inspect.isawaitable(value):
                    await value
            except BaseException as exc:
                failures.append(exc)
        return tuple(failures)

@dataclass(frozen=True,slots=True)
class PerformanceBudget:
    name:str; warning_ms:float; critical_ms:float|None=None
    def __post_init__(self):
        if self.warning_ms<=0: raise ValueError('warning_ms must be > 0')
        if self.critical_ms is not None and self.critical_ms<self.warning_ms: raise ValueError('critical_ms must be >= warning_ms')

@dataclass(frozen=True,slots=True)
class PerformanceSample:
    name:str; duration_ms:float; metadata:dict[str,Any]

class PerformanceMonitor:
    def __init__(self, *, max_samples:int=500):
        if max_samples<1: raise ValueError('max_samples must be >= 1')
        self.samples:deque[PerformanceSample]=deque(maxlen=max_samples); self.budgets:dict[str,PerformanceBudget]={}
    def set_budget(self,budget:PerformanceBudget):self.budgets[budget.name]=budget
    def record(self,name:str,duration_ms:float,**metadata:Any)->PerformanceSample:
        sample=PerformanceSample(name,float(duration_ms),dict(metadata)); self.samples.append(sample); return sample
    def measure(self,name:str,**metadata:Any):
        monitor=self
        class _Ctx:
            def __enter__(self):self.t=time.perf_counter(); return self
            def __exit__(self,*_):monitor.record(name,(time.perf_counter()-self.t)*1000,**metadata)
        return _Ctx()
    def recent(self,name:str|None=None):return tuple(s for s in self.samples if name is None or s.name==name)
    def status(self,name:str,duration_ms:float)->str:
        b=self.budgets.get(name)
        if not b:return 'unbudgeted'
        if b.critical_ms is not None and duration_ms>=b.critical_ms:return 'critical'
        if duration_ms>=b.warning_ms:return 'warning'
        return 'ok'

class LazyResource(Generic[T]):
    """Lazily load one resource and deterministically dispose replacements.

    Refresh is atomic: if a replacement loader fails the existing resource stays
    active. A successful replacement disposes the previous value before returning.
    """
    def __init__(self, loader:Callable[[],T|Awaitable[T]], *, disposer:Callable[[T],Any|Awaitable[Any]]|None=None):
        self.loader=loader; self.disposer=disposer; self._loaded=False; self._value:T|None=None; self._lock=asyncio.Lock(); self._closed=False

    @property
    def loaded(self): return self._loaded

    @property
    def closed(self): return self._closed

    async def _dispose(self, value:T|None)->None:
        if self.disposer is None or value is None:
            return
        result=self.disposer(value)
        if inspect.isawaitable(result):
            await result

    async def get(self, *, refresh:bool=False)->T:
        if self._closed:
            raise RuntimeError('LazyResource is closed')
        if self._loaded and not refresh:
            return self._value  # type: ignore[return-value]
        async with self._lock:
            if self._closed:
                raise RuntimeError('LazyResource is closed')
            if self._loaded and not refresh:
                return self._value  # type: ignore[return-value]
            old_value=self._value if self._loaded else None
            value=self.loader()
            replacement=await value if inspect.isawaitable(value) else value
            self._value=replacement; self._loaded=True
            if old_value is not None and old_value is not replacement:
                await self._dispose(old_value)
            return replacement

    async def aclear(self)->None:
        async with self._lock:
            value=self._value if self._loaded else None
            self._loaded=False; self._value=None
        await self._dispose(value)

    def clear(self)->None:
        """Detach the cached resource. Prefer ``await aclear()`` with a disposer.

        For compatibility, synchronous disposers run immediately. Async disposers
        are scheduled on the running loop; without one they are completed with
        ``asyncio.run`` so resources are never silently leaked.
        """
        value=self._value if self._loaded else None
        self._loaded=False; self._value=None
        if self.disposer is None or value is None:
            return
        result=self.disposer(value)
        if not inspect.isawaitable(result):
            return
        try:
            asyncio.get_running_loop().create_task(result)
        except RuntimeError:
            asyncio.run(result)

    async def aclose(self)->None:
        async with self._lock:
            if self._closed:
                return
            self._closed=True
            value=self._value if self._loaded else None
            self._loaded=False; self._value=None
        await self._dispose(value)

class ConcurrencyGate:
    def __init__(self,limit:int=4):
        if limit<1:raise ValueError('limit must be >= 1')
        self.limit=limit; self._sem=asyncio.Semaphore(limit)
    async def run(self,operation:Callable[[],T|Awaitable[T]])->T:
        async with self._sem:
            value=operation(); return await value if inspect.isawaitable(value) else value

@dataclass(frozen=True,slots=True)
class RetryPolicy:
    attempts:int=3; base_delay_seconds:float=.25; max_delay_seconds:float=2.0; jitter:float=.1
    def __post_init__(self):
        if self.attempts<1:raise ValueError('attempts must be >= 1')
        if self.base_delay_seconds<0 or self.max_delay_seconds<self.base_delay_seconds:raise ValueError('invalid retry delays')
    async def run(self,operation:Callable[[],T|Awaitable[T]], *, retry_if:Callable[[BaseException],bool]|None=None)->T:
        for attempt in range(1,self.attempts+1):
            try:
                value=operation(); return await value if inspect.isawaitable(value) else value
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if attempt>=self.attempts or (retry_if is not None and not retry_if(exc)):raise
                delay=min(self.max_delay_seconds,self.base_delay_seconds*(2**(attempt-1)))
                if self.jitter:delay*=1+random.uniform(-self.jitter,self.jitter)
                await asyncio.sleep(max(0,delay))
        raise RuntimeError('unreachable')

async def run_blocking(func:Callable[...,T], *args:Any, **kwargs:Any)->T:
    return await asyncio.to_thread(func,*args,**kwargs)
