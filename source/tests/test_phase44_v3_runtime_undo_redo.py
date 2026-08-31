from __future__ import annotations

import pytest

from nicegui_base import RuntimeState, StateKey, StateNamespace


def test_v3_state_undo_redo_operates_on_committed_transaction_as_one_history_step():
    state = RuntimeState()
    count = StateKey[int]('count', StateNamespace.VIEW)
    label = StateKey[str]('label', StateNamespace.VIEW)
    with state.transaction(source='edit'):
        state.set(count, 1)
        state.set(count, 2)
        state.set(label, 'ready')
    assert state.can_undo and not state.can_redo and state.revision == 1
    assert state.undo()
    assert not state.contains(count) and not state.contains(label)
    assert state.can_redo and state.revision == 2
    assert state.redo()
    assert state.get(count) == 2 and state.get(label) == 'ready'
    assert state.revision == 3


def test_v3_state_undo_redo_preserves_absent_vs_none_semantics():
    state = RuntimeState()
    key = StateKey[object]('nullable')
    state.set(key, None)
    assert state.undo() and not state.contains(key)
    assert state.redo() and state.contains(key) and state.get(key) is None


def test_v3_new_edit_after_undo_clears_stale_redo_branch():
    state = RuntimeState(); key = StateKey[int]('value', default=0)
    state.set(key, 1); state.set(key, 2)
    assert state.undo() and state.get(key) == 1 and state.can_redo
    state.set(key, 3)
    assert state.get(key) == 3 and not state.can_redo


def test_v3_undo_and_redo_are_rejected_inside_active_transaction():
    state = RuntimeState(); key = StateKey[int]('value')
    state.set(key, 1)
    with state.transaction():
        with pytest.raises(RuntimeError, match='active state transaction'):
            state.undo()
        with pytest.raises(RuntimeError, match='active state transaction'):
            state.redo()


def test_v3_undo_redo_emit_governed_mutations_without_corrupting_original_undo_batch():
    state = RuntimeState(); key = StateKey[list[int]]('items')
    seen=[]; state.watch(seen.append)
    state.set(key, [1, 2], source='seed')
    state.undo(); state.redo()
    assert [mutation.source for mutation in seen] == ['seed', 'undo', 'redo']
    leaked = state.get(key); leaked.append(9)
    assert state.get(key) == [1, 2]
