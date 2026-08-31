from __future__ import annotations

import asyncio

import pytest

from nicegui_base import (
    ApplicationRuntime, Command, RuntimeState, StateKey, StateNamespace, WorkspaceRuntime,
)

pytestmark = pytest.mark.asyncio


async def test_v3_runtime_state_transaction_commits_one_revision_and_coalesces_key_changes():
    state=RuntimeState()
    count=StateKey[int]('count',StateNamespace.SESSION,default=0,validator=lambda value:isinstance(value,int) and value>=0)
    name=StateKey[str]('name',StateNamespace.SESSION,default='')
    mutations=[]; state.watch(mutations.append)
    with state.transaction(source='test.batch'):
        state.set(count,1)
        state.set(count,2)
        state.set(name,'alpha')
    assert state.revision == 1
    assert state.get(count) == 2 and state.get(name) == 'alpha'
    assert [(m.key,m.old,m.new,m.revision,m.source) for m in mutations] == [
        ('count',None,2,1,'test.batch'),('name',None,'alpha',1,'test.batch')
    ]


async def test_v3_runtime_state_transaction_rolls_back_exactly_and_emits_nothing_on_failure():
    state=RuntimeState({StateNamespace.APPLICATION:{'mode':'safe'}})
    mode=StateKey[str]('mode',StateNamespace.APPLICATION)
    temp=StateKey[int]('temp',StateNamespace.APPLICATION)
    mutations=[]; state.watch(mutations.append)
    with pytest.raises(RuntimeError,match='abort'):
        with state.transaction(source='failing'):
            state.set(mode,'danger')
            state.set(temp,7)
            raise RuntimeError('abort')
    assert state.get(mode) == 'safe' and not state.contains(temp)
    assert state.revision == 0 and state.history == () and mutations == []


async def test_v3_runtime_state_snapshot_restore_is_revisioned_and_deep_copy_safe():
    state=RuntimeState()
    filters=StateKey[list[str]]('filters',StateNamespace.WORKSPACE,default=[])
    state.set(filters,['A'],source='seed')
    snapshot=state.snapshot()
    leaked=state.get(filters); leaked.append('mutated-read')
    assert state.get(filters) == ['A']  # reads are defensive; mutation must go through set()
    state.set(filters,['B'],source='later')
    state.restore(snapshot)
    assert state.get(filters) == ['A']
    assert snapshot.values['workspace']['filters'] == ['A']
    assert state.revision == 3


async def test_v3_workspace_lifecycle_is_isolated_and_application_close_cascades():
    runtime=ApplicationRuntime()
    one=runtime.open_workspace('one'); two=runtime.open_workspace('two')
    started=asyncio.Event(); cleaned=[]
    async def worker():
        started.set(); await asyncio.sleep(60)
    one.create_task(worker())
    one.register_cleanup(lambda:cleaned.append('one'))
    two.register_cleanup(lambda:cleaned.append('two'))
    await started.wait()
    diagnostics=runtime.diagnostics()
    assert diagnostics.active_workspaces == 2 and diagnostics.active_tasks == 1
    failures=await runtime.aclose()
    assert failures == () and runtime.closed and one.closed and two.closed
    assert cleaned == ['two','one']
    assert runtime.diagnostics().active_workspaces == 0


async def test_v3_application_runtime_rejects_duplicate_workspaces_and_can_close_one_without_parent_leak():
    runtime=ApplicationRuntime(); runtime.open_workspace('analysis')
    with pytest.raises(ValueError,match='already open'): runtime.open_workspace('analysis')
    assert await runtime.close_workspace('analysis') == ()
    assert runtime.workspaces == {} and runtime.services.lifecycle.cleanup_count == 0
    await runtime.aclose()


async def test_v3_command_execution_records_performance_and_runtime_events_for_success_and_failure():
    runtime=ApplicationRuntime()
    runtime.services.commands.register(Command('ok','OK',lambda:42))
    runtime.services.commands.register(Command('fail','Fail',lambda:(_ for _ in ()).throw(ValueError('bad'))))
    assert await runtime.execute_command('ok',workspace_id='w') == 42
    with pytest.raises(ValueError,match='bad'): await runtime.execute_command('fail',workspace_id='w')
    samples=runtime.services.performance.recent('runtime.command')
    assert [sample.metadata['status'] for sample in samples] == ['success','error']
    assert [event.kind for event in runtime.events if event.kind.startswith('command.')] == [
        'command.started','command.completed','command.started','command.failed'
    ]
    await runtime.aclose()


async def test_v3_state_key_validation_and_key_scoped_watchers_are_governed():
    state=RuntimeState(); key=StateKey[int]('percent',validator=lambda value:isinstance(value,int) and 0<=value<=100)
    seen=[]; unsubscribe=state.watch_key(key,seen.append)
    state.set(key,50,source='ui')
    with pytest.raises(ValueError,match='invalid value'): state.set(key,101)
    unsubscribe(); state.set(key,60)
    assert len(seen) == 1 and seen[0].new == 50 and seen[0].source == 'ui'


async def test_v3_runtime_public_surface_is_framework_neutral_and_root_importable():
    assert WorkspaceRuntime.__module__ == 'nicegui_base.runtime.kernel'
    runtime=ApplicationRuntime(); assert runtime.diagnostics().latest_event_sequence == 1
    await runtime.aclose()


async def test_v3_state_key_identity_is_address_only_and_deletion_is_unambiguous_from_none():
    state=RuntimeState()
    first=StateKey[list[int]]('items',StateNamespace.VIEW,default=[])
    second=StateKey[list[int]]('items',StateNamespace.VIEW,default=[99])
    mapping={first:[1,2]}
    assert mapping[second] == [1,2]
    nullable=StateKey[object]('nullable',StateNamespace.VIEW)
    state.set(nullable,None,source='set-none')
    state.delete(nullable,source='delete')
    set_none, deleted=state.history[-2:]
    assert set_none.new is None and set_none.new_present is True
    assert deleted.new is None and deleted.new_present is False
