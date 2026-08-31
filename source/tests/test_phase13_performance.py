import asyncio, time
from nicegui_base import (AnalyticalDataController, AsyncSingleFlightCache, ConcurrencyGate, LazyResource, PerformanceBudget, PerformanceMonitor, RetryPolicy, TTLCache, run_blocking)

def test_ttl_cache_bounded():
    c=TTLCache(maxsize=2,ttl_seconds=60); c.set('a',1); c.set('b',2); c.get('a'); c.set('c',3); assert c.get('b') is None and c.get('a')==1

def test_ttl_expiry():
    c=TTLCache(ttl_seconds=.01); c.set('x',1); time.sleep(.02); assert c.get('x') is None

def test_monitor_budgets():
    m=PerformanceMonitor(max_samples=2); m.set_budget(PerformanceBudget('x',10,20)); assert m.status('x',5)=='ok'; assert m.status('x',15)=='warning'; assert m.status('x',25)=='critical'

def test_monitor_bounded():
    m=PerformanceMonitor(max_samples=2); [m.record('x',i) for i in range(3)]; assert len(m.samples)==2

def test_lazy_resource():
    async def go():
        calls=0
        async def load():
            nonlocal calls; calls+=1; return calls
        r=LazyResource(load); assert await r.get()==1; assert await r.get()==1; assert await r.get(refresh=True)==2
    asyncio.run(go())

def test_single_flight():
    async def go():
        calls=0
        async def load():
            nonlocal calls; calls+=1; await asyncio.sleep(.01); return 7
        c=AsyncSingleFlightCache(); assert await asyncio.gather(*[c.get_or_load('x',load) for _ in range(5)])==[7]*5; assert calls==1
    asyncio.run(go())

def test_concurrency_gate():
    async def go():
        gate=ConcurrencyGate(2); active=peak=0
        async def job():
            nonlocal active,peak; active+=1; peak=max(peak,active); await asyncio.sleep(.005); active-=1
        await asyncio.gather(*[gate.run(job) for _ in range(6)]); assert peak<=2
    asyncio.run(go())

def test_retry_policy():
    async def go():
        calls=0
        async def job():
            nonlocal calls; calls+=1
            if calls<3: raise TimeoutError()
            return 9
        assert await RetryPolicy(attempts=3,base_delay_seconds=0,max_delay_seconds=0,jitter=0).run(job)==9
    asyncio.run(go())

def test_run_blocking():
    assert asyncio.run(run_blocking(lambda x:x+1,3))==4

def test_analytical_controller_latest():
    async def go():
        async def loader(q): await asyncio.sleep(.02 if q==1 else .001); return q
        c=AnalyticalDataController(loader,debounce_seconds=0)
        a=asyncio.create_task(c.load(1)); await asyncio.sleep(.001); b=asyncio.create_task(c.load(2)); await asyncio.gather(a,b); assert c.state.data==2
    asyncio.run(go())
