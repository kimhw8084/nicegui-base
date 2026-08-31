from __future__ import annotations

import pytest

from nicegui_base import Aggregation, ApplicationRuntime, Dataset, Dimension, FilterClause, FilterOperation, Metric, StateKey
from nicegui_base.workspace import PanelSpec, WorkspaceBreakpoint

pytestmark = pytest.mark.asyncio


def dataset() -> Dataset:
    return Dataset(
        'ops',
        (
            {'id': 1, 'region': 'APAC', 'value': 10},
            {'id': 2, 'region': 'US', 'value': 20},
            {'id': 3, 'region': 'APAC', 'value': 30},
        ),
        row_key='id',
        dimensions=(Dimension('region'),),
        metrics=(Metric('value', aggregation=Aggregation.SUM),),
    )


async def test_v3_workspace_snapshot_restores_state_layout_and_filter_session_as_one_atomic_workspace_contract():
    runtime = ApplicationRuntime(); runtime.data.register(dataset())
    workspace = runtime.open_workspace('analysis')
    key = StateKey('selected_lot', default='none')
    workspace.state.set(key, 'LOT-42')
    workspace.layout.register_panel(PanelSpec('trend', preferred_columns=8))
    workspace.layout.register_panel(PanelSpec('table', preferred_columns=12))
    workspace.layout.move('trend', WorkspaceBreakpoint.DESKTOP, column=4, row=0)
    session = workspace.open_data_session('ops', session_id='primary')
    session.set_filter(FilterClause('region', FilterOperation.EQUALS, 'APAC'))
    snapshot = workspace.snapshot()

    workspace.state.set(key, 'CHANGED')
    workspace.layout.resize('trend', WorkspaceBreakpoint.DESKTOP, column_span=4, row_span=2)
    session.set_filter(FilterClause('region', FilterOperation.EQUALS, 'US'))
    workspace.restore(snapshot)

    restored = workspace.data_sessions['primary']
    assert workspace.state.get(key) == 'LOT-42'
    assert workspace.layout.placement('trend', WorkspaceBreakpoint.DESKTOP) == snapshot.layout.placements[3 * 2]
    assert restored.metric('value') == 40.0
    assert runtime.diagnostics().workspace_panels == 2
    await runtime.aclose()


async def test_v3_application_snapshot_can_remove_extra_workspaces_and_rehydrate_missing_ones_without_shared_state_leakage():
    runtime = ApplicationRuntime(); runtime.data.register(dataset())
    left = runtime.open_workspace('left'); left.layout.register_panel(PanelSpec('a'))
    left.open_data_session('ops').set_filter(FilterClause('region', FilterOperation.EQUALS, 'APAC'))
    snapshot = runtime.snapshot()
    await runtime.close_workspace('left')
    runtime.open_workspace('temporary')

    await runtime.restore(snapshot)
    assert set(runtime.workspaces) == {'left'}
    restored = runtime.workspaces['left']
    assert restored.data_sessions['default'].metric('value') == 40.0
    assert len(restored.layout.panels) == 1
    assert runtime.events[-1].kind == 'runtime.restored'
    await runtime.aclose()


async def test_v3_workspace_snapshot_rejects_cross_workspace_restore():
    runtime = ApplicationRuntime(); runtime.data.register(dataset())
    a = runtime.open_workspace('a'); b = runtime.open_workspace('b')
    snapshot = a.snapshot()
    with pytest.raises(ValueError, match='does not match'):
        b.restore(snapshot)
    await runtime.aclose()
