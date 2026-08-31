from __future__ import annotations
import asyncio, inspect, secrets
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable
from .models import JobHandle, JobSnapshot, JobStatus

JobCallable=Callable[[],Any|Awaitable[Any]]

@runtime_checkable
class DurableJobAdapter(Protocol):
    """Backend-neutral long-running job contract.

    Implementations may map this API to an internal scheduler, queue, workflow engine, or durable service.
    UI/page code depends on this contract rather than a specific queue product.
    """
    async def submit(self, work:JobCallable, *, label:str|None=None, metadata:dict[str,Any]|None=None)->JobHandle: ...
    async def snapshot(self, handle:JobHandle)->JobSnapshot: ...
    async def cancel(self, handle:JobHandle)->bool: ...
    async def result(self, handle:JobHandle)->Any: ...

class InProcessJobAdapter:
    """Reference adapter for short-lived deployments; not restart-durable."""
    def __init__(self, *, max_jobs:int=256):
        if max_jobs<1: raise ValueError('max_jobs must be positive')
        self.max_jobs=max_jobs; self._tasks:dict[str,asyncio.Task]={}; self._handles:dict[str,JobHandle]={}

    def _prune(self)->None:
        completed=[key for key,task in self._tasks.items() if task.done()]
        while len(self._tasks)>=self.max_jobs and completed:
            key=completed.pop(0); self._tasks.pop(key,None); self._handles.pop(key,None)
        if len(self._tasks)>=self.max_jobs: raise RuntimeError('job capacity reached; use a durable external adapter for higher concurrency')

    async def submit(self, work:JobCallable, *, label:str|None=None, metadata:dict[str,Any]|None=None)->JobHandle:
        self._prune(); job_id=secrets.token_urlsafe(12); handle=JobHandle(job_id,label,metadata or {})
        async def runner():
            value=work(); return await value if inspect.isawaitable(value) else value
        self._handles[job_id]=handle; self._tasks[job_id]=asyncio.create_task(runner(),name=f'nicegui-base-job:{job_id}')
        return handle

    def _task(self, handle:JobHandle)->asyncio.Task:
        try:return self._tasks[handle.job_id]
        except KeyError as exc:raise KeyError(f'Unknown job: {handle.job_id}') from exc

    async def snapshot(self, handle:JobHandle)->JobSnapshot:
        task=self._task(handle)
        if task.cancelled(): return JobSnapshot(handle,JobStatus.CANCELLED)
        if not task.done(): return JobSnapshot(handle,JobStatus.RUNNING)
        exc=task.exception()
        if exc is not None:return JobSnapshot(handle,JobStatus.FAILED,error=str(exc))
        return JobSnapshot(handle,JobStatus.SUCCEEDED,result_available=True)

    async def cancel(self, handle:JobHandle)->bool:
        task=self._task(handle)
        if task.done(): return False
        task.cancel(); return True

    async def result(self, handle:JobHandle)->Any:
        return await self._task(handle)

__all__=['JobCallable','DurableJobAdapter','InProcessJobAdapter']
