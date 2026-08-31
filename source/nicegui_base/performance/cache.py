from __future__ import annotations
import asyncio, inspect, time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Hashable
from dataclasses import dataclass
from threading import RLock
from typing import Generic, TypeVar
T=TypeVar('T')

@dataclass(slots=True)
class _Entry(Generic[T]):
    value:T; expires_at:float

class TTLCache(Generic[T]):
    """Bounded thread-safe TTL/LRU cache for deterministic local results."""
    def __init__(self, *, maxsize:int=128, ttl_seconds:float=60.0):
        if maxsize<1: raise ValueError('maxsize must be >= 1')
        if ttl_seconds<=0: raise ValueError('ttl_seconds must be > 0')
        self.maxsize=maxsize; self.ttl_seconds=ttl_seconds; self._data:OrderedDict[Hashable,_Entry[T]]=OrderedDict(); self._lock=RLock()
    def get(self,key:Hashable,default=None):
        now=time.monotonic()
        with self._lock:
            entry=self._data.get(key)
            if entry is None: return default
            if entry.expires_at<=now:
                self._data.pop(key,None); return default
            self._data.move_to_end(key); return entry.value
    def set(self,key:Hashable,value:T)->T:
        with self._lock:
            self._data[key]=_Entry(value,time.monotonic()+self.ttl_seconds); self._data.move_to_end(key)
            while len(self._data)>self.maxsize: self._data.popitem(last=False)
        return value
    def pop(self,key:Hashable,default=None):
        with self._lock:
            entry=self._data.pop(key,None); return default if entry is None else entry.value
    def clear(self):
        with self._lock: self._data.clear()
    def __len__(self):
        with self._lock:
            now=time.monotonic(); expired=[k for k,v in self._data.items() if v.expires_at<=now]
            for k in expired:self._data.pop(k,None)
            return len(self._data)

class AsyncSingleFlightCache(Generic[T]):
    """TTL cache that coalesces concurrent identical async loads."""
    def __init__(self, *, maxsize:int=128, ttl_seconds:float=60.0):
        self.cache=TTLCache[T](maxsize=maxsize,ttl_seconds=ttl_seconds); self._inflight:dict[Hashable,asyncio.Task[T]]={}; self._lock=asyncio.Lock()
    async def get_or_load(self,key:Hashable,loader:Callable[[],T|Awaitable[T]], *, refresh:bool=False)->T:
        if not refresh:
            hit=self.cache.get(key, _MISS)
            if hit is not _MISS: return hit
        async with self._lock:
            if not refresh:
                hit=self.cache.get(key,_MISS)
                if hit is not _MISS:return hit
            task=self._inflight.get(key)
            if task is None or task.done():
                async def invoke():
                    value=loader(); return await value if inspect.isawaitable(value) else value
                task=asyncio.create_task(invoke()); self._inflight[key]=task
        try:
            value=await asyncio.shield(task); self.cache.set(key,value); return value
        finally:
            if task.done():
                async with self._lock:
                    if self._inflight.get(key) is task:self._inflight.pop(key,None)
    def invalidate(self,key:Hashable)->None:self.cache.pop(key,None)
    def clear(self)->None:self.cache.clear()

_MISS=object()
