import asyncio
import pytest

from nicegui_base.async_tools import AsyncAction, AutoRefreshController, CancelableTask, Debouncer, DuplicatePolicy, ProgressTask, StaleResponseGuard, TaskStatus, Throttler

pytestmark = pytest.mark.asyncio


async def test_async_action_result_and_status():
    action=AsyncAction(timeout=1)
    assert await action.run(lambda: asyncio.sleep(0, result=7)) == 7
    assert action.status is TaskStatus.SUCCESS


async def test_async_action_timeout_errors():
    action=AsyncAction(timeout=.01)
    with pytest.raises(asyncio.TimeoutError): await action.run(lambda: asyncio.sleep(.1))
    assert action.status is TaskStatus.ERROR


async def test_cancelable_task_cancel_previous():
    action=CancelableTask(); started=asyncio.Event()
    async def slow(): started.set(); await asyncio.sleep(10)
    t=asyncio.create_task(action.run(slow)); await started.wait()
    assert await action.cancel() is True
    with pytest.raises(asyncio.CancelledError): await t


async def test_progress_validation():
    task=ProgressTask(); task.update_progress(.5,'Half')
    assert task.progress.value == .5
    with pytest.raises(ValueError): task.update_progress(2)


async def test_debouncer_returns_latest_call():
    d=Debouncer(.02); out=[]
    t1=asyncio.create_task(d.call(lambda: out.append(1)))
    await asyncio.sleep(.005)
    t2=asyncio.create_task(d.call(lambda: out.append(2)))
    await asyncio.gather(t1,t2)
    assert out == [2]


async def test_throttler_suppresses_immediate_duplicate():
    t=Throttler(.1); out=[]
    assert await t.call(lambda: out.append(1)) is None
    assert await t.call(lambda: out.append(2)) is None
    assert out == [1]


async def test_stale_response_guard():
    g=StaleResponseGuard(); a=g.next(); b=g.next()
    assert not g.is_current(a) and g.is_current(b)


async def test_auto_refresh_manual_status():
    calls=[]
    async def op(): calls.append(1); return 9
    c=AutoRefreshController(op, interval_seconds=1, stale_after_seconds=10)
    assert await c.refresh_now() == 9
    assert c.status.last_success is not None and c.status.last_error is None
    assert calls == [1]


async def test_auto_refresh_min_interval():
    with pytest.raises(ValueError): AutoRefreshController(lambda: None, interval_seconds=.5)

async def test_duplicate_ignore_awaits_inflight_result():
    action=AsyncAction(duplicate_policy=DuplicatePolicy.IGNORE); gate=asyncio.Event(); calls=[]
    async def op(): calls.append(1); await gate.wait(); return 42
    first=asyncio.create_task(action.run(op)); await asyncio.sleep(0)
    second=asyncio.create_task(action.run(op)); await asyncio.sleep(0)
    gate.set()
    assert await first == 42 and await second == 42 and calls == [1]
