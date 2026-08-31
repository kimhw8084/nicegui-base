from __future__ import annotations
import asyncio, inspect, time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Hashable, TypeVar
from collections.abc import Awaitable, Callable
from .cache import AsyncSingleFlightCache
from .runtime import PerformanceMonitor
T=TypeVar('T')
class DataLoadStatus(str,Enum):IDLE='idle'; LOADING='loading'; READY='ready'; REFRESHING='refreshing'; ERROR='error'; CANCELLED='cancelled'
@dataclass(slots=True)
class AnalyticalDataState(Generic[T]):
    status:DataLoadStatus=DataLoadStatus.IDLE; data:T|None=None; error:BaseException|None=None; stale:bool=False; duration_ms:float|None=None
class AnalyticalDataController(Generic[T]):
    """Latest-request-wins analytical loading with debounce, single-flight cache and stale-data preservation."""
    def __init__(self,loader:Callable[[Any],T|Awaitable[T]], *, debounce_seconds:float=.15, cache_ttl_seconds:float=60, cache_size:int=64, monitor:PerformanceMonitor|None=None):
        self.loader=loader; self.debounce=max(0,debounce_seconds); self.cache=AsyncSingleFlightCache[T](maxsize=cache_size,ttl_seconds=cache_ttl_seconds); self.monitor=monitor; self.state=AnalyticalDataState[T](); self._generation=0; self._task:asyncio.Task[T]|None=None
    async def load(self,query:Any, *, cache_key:Hashable|None=None, refresh:bool=False)->T|None:
        self._generation+=1; gen=self._generation
        if self._task and not self._task.done():self._task.cancel()
        previous=self.state.data; self.state.status=DataLoadStatus.REFRESHING if previous is not None else DataLoadStatus.LOADING; self.state.error=None; self.state.stale=previous is not None
        async def run():
            if self.debounce:await asyncio.sleep(self.debounce)
            key=cache_key if cache_key is not None else repr(query)
            async def fetch():
                value=self.loader(query); return await value if inspect.isawaitable(value) else value
            return await self.cache.get_or_load(key,fetch,refresh=refresh)
        self._task=asyncio.create_task(run()); t=time.perf_counter()
        try:
            result=await self._task
            if gen!=self._generation:return None
            ms=(time.perf_counter()-t)*1000; self.state=AnalyticalDataState(DataLoadStatus.READY,result,None,False,ms)
            if self.monitor:self.monitor.record('analytical_load',ms,cache_key=str(cache_key) if cache_key is not None else None)
            return result
        except asyncio.CancelledError:
            if gen==self._generation:self.state.status=DataLoadStatus.CANCELLED
            return None
        except BaseException as exc:
            if gen==self._generation:self.state=AnalyticalDataState(DataLoadStatus.ERROR,previous,exc,previous is not None,(time.perf_counter()-t)*1000)
            raise
        finally:
            if gen==self._generation:self._task=None
    async def cancel(self):
        self._generation+=1
        if self._task and not self._task.done():
            self._task.cancel()
            try:await self._task
            except asyncio.CancelledError:pass
        self._task=None; self.state.status=DataLoadStatus.CANCELLED
