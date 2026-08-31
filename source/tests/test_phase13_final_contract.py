import asyncio
import pytest
from nicegui_base import AnalyticalDataController, Command, CommandRegistry, PERFORMANCE_REGISTRY, WorkspacePreferenceService
from nicegui_base.ai import FRAMEWORK_REGISTRY_COUNTS, install_ai_materials

def test_ai_counts_include_performance(): assert FRAMEWORK_REGISTRY_COUNTS['performance']==10

def test_performance_guide_installs(tmp_path):
    install_ai_materials(tmp_path); assert (tmp_path/'docs/nicegui_base/PERFORMANCE_GUIDE.md').exists()

def test_command_duplicate_rejected():
    r=CommandRegistry(); r.register(Command('x','X',lambda:None))
    with pytest.raises(ValueError): r.register(Command('x','Other',lambda:None))

def test_workspace_names_sorted():
    b={}; w=WorkspacePreferenceService(b); w.save_workspace('z',{}); w.save_workspace('a',{}); assert w.list_workspaces()==('a','z')

def test_analytical_controller_cache_reuses_loader():
    async def go():
        calls=0
        async def load(q):
            nonlocal calls; calls+=1; return q
        c=AnalyticalDataController(load,debounce_seconds=0,cache_ttl_seconds=60)
        assert await c.load('x')=='x'; assert await c.load('x')=='x'; assert calls==1
    asyncio.run(go())

def test_performance_registry_has_avoid_guidance(): assert all(x.avoid_when for x in PERFORMANCE_REGISTRY.values())

def test_performance_registry_keys_unique(): assert len(PERFORMANCE_REGISTRY)==len(set(PERFORMANCE_REGISTRY))
