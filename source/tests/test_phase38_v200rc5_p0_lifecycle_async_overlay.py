from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from nicegui_base import ApplicationServices
from nicegui_base.async_tools import AsyncAction, DuplicatePolicy, LatestRequestController, TaskStatus
from nicegui_base.data_table import PinPosition, ServerDataTableSpec, TableColumn, TableDensity, TableState
from nicegui_base.data_table import export_csv
from nicegui_base.certification.pathological_data import PATHOLOGICAL_DATA_FIXTURES, engineering_rows, pathological_rows
from nicegui_base.performance import LazyResource, LifecycleScope, RetryPolicy

pytestmark = pytest.mark.asyncio
ROOT = Path(__file__).resolve().parents[1]


async def test_lifecycle_scope_cancels_tasks_and_cleans_up_once_in_reverse_order():
    scope = LifecycleScope()
    order: list[str] = []
    started = asyncio.Event()

    async def worker():
        started.set()
        try:
            await asyncio.sleep(60)
        finally:
            order.append('task')

    scope.register(lambda: order.append('first'))
    scope.register(lambda: order.append('second'))
    scope.create_task(worker())
    await started.wait()
    failures = await scope.aclose()
    assert failures == ()
    assert order == ['task', 'second', 'first']
    assert scope.closed and scope.active_task_count == 0 and scope.cleanup_count == 0
    assert await scope.aclose() == ()


async def test_lazy_resource_disposer_runs_on_aclose():
    disposed: list[int] = []
    resource = LazyResource(lambda: 7, disposer=lambda value: disposed.append(value))
    assert await resource.get() == 7
    await resource.aclose()
    assert disposed == [7]
    assert not resource.loaded


async def test_application_services_owns_session_lifecycle_cleanup():
    services = ApplicationServices()
    cleaned: list[str] = []
    services.register_cleanup(lambda: cleaned.append('done'), key='test')
    assert await services.aclose() == ()
    assert cleaned == ['done'] and services.lifecycle.closed


async def test_async_action_allow_tracks_concurrent_tasks_without_handle_race():
    action = AsyncAction[int](duplicate_policy=DuplicatePolicy.ALLOW)
    one = asyncio.Event(); two = asyncio.Event()

    async def op(value: int, gate: asyncio.Event):
        await gate.wait()
        return value

    first = asyncio.create_task(action.run(lambda: op(1, one)))
    second = asyncio.create_task(action.run(lambda: op(2, two)))
    await asyncio.sleep(0)
    assert action.active_count == 2 and action.running
    one.set()
    assert await first == 1
    assert action.running and action.active_count == 1
    two.set()
    assert await second == 2
    assert not action.running and action.status is TaskStatus.SUCCESS


async def test_async_action_retry_is_explicitly_idempotent():
    action = AsyncAction[int]()
    retry = RetryPolicy(attempts=2, base_delay_seconds=0, max_delay_seconds=0, jitter=0)
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionError('transient')
        return 9

    with pytest.raises(ValueError, match='idempotent'):
        await action.run(flaky, retry_policy=retry)
    assert await action.run(flaky, retry_policy=retry, retry_if=lambda exc: isinstance(exc, ConnectionError), idempotent=True) == 9
    assert calls == 2


async def test_latest_request_controller_coalesces_cache_and_cancels_stale_work():
    controller = LatestRequestController[int](cache_size=2, cache_ttl_seconds=30)
    gate = asyncio.Event(); calls: list[str] = []

    async def load_a():
        calls.append('a')
        await gate.wait()
        return 1

    first = asyncio.create_task(controller.run('a', load_a))
    await asyncio.sleep(0)
    duplicate = asyncio.create_task(controller.run('a', load_a))
    await asyncio.sleep(0)
    assert calls == ['a']

    newer = asyncio.create_task(controller.run('b', lambda: asyncio.sleep(0, result=2)))
    assert await first is None
    assert await duplicate is None
    assert await newer == 2
    assert await controller.run('b', lambda: (_ for _ in ()).throw(AssertionError('cache miss'))) == 2
    await controller.aclose()
    assert controller.closed


async def test_server_table_spec_validates_request_policy():
    columns = (TableColumn('id', 'ID'),)
    with pytest.raises(ValueError):
        ServerDataTableSpec(columns, retry_attempts=0)
    with pytest.raises(ValueError):
        ServerDataTableSpec(columns, request_timeout_seconds=0)
    spec = ServerDataTableSpec(columns, cache_pages=3, retry_attempts=3)
    assert spec.cache_pages == 3 and spec.cancel_stale_requests is True


async def test_table_state_persistence_migrates_schema_and_reconciles_identity_exactly():
    columns = (
        TableColumn('id', 'ID', min_width=80),
        TableColumn('name', 'Name', min_width=120, max_width=240),
        TableColumn('owner', 'Owner', pinned=PinPosition.RIGHT),
    )
    state = TableState.from_persisted({
        'version': 2,
        'column_keys': ['id', 'name', 'removed'],
        'density': 'dense',
        'search': 'abc',
        'selected_keys': [1, '1'],
        'visible_columns': ['id', 'removed'],
        'column_order': ['name', 'removed', 'id'],
        'column_widths': {'name': 999, 'removed': 120},
        'pinned_left': ['name'],
        'pinned_right': ['name', 'removed'],
        'page': -3,
        'page_size': 100,
        'scroll_row_index': 12,
    }, columns)
    assert state.density is TableDensity.DENSE and state.search == 'abc'
    assert state.visible_columns == ['id', 'owner']  # new default-visible column migrates in
    assert state.column_order == ['name', 'id', 'owner']
    assert state.column_widths == {'name': 240}
    assert state.pinned_left == ['name'] and state.pinned_right == ['owner']
    assert state.page == 1 and state.page_size == 100 and state.scroll_row_index == 12
    assert state.selected_keys == {1, '1'}
    removed = state.reconcile_selection([1, 2])
    assert state.selected_keys == {1} and removed == {'1'}
    payload = state.to_persisted(columns)
    assert payload['version'] == 2 and payload['column_keys'] == ['id', 'name', 'owner']


async def test_data_table_source_turns_persist_state_into_preference_backed_runtime_contract():
    text = (ROOT / 'nicegui_base/integrations/nicegui_data_table.py').read_text(encoding='utf-8')
    for token in (
        'PreferenceService',
        'TableState.from_persisted',
        'save_table_state',
        "run_grid_method('getColumnState')",
        "run_grid_method('getFilterModel')",
        "run_grid_method('getFirstDisplayedRowIndex')",
        "run_row_method(str(key),'setSelected',True,False)",
        "run_grid_method('paginationGoToPage'",
        'reconcile_selection',
        'row identities',
    ):
        assert token in text


async def test_pathological_data_fixture_library_is_deterministic_and_security_reusable():
    assert tuple(PATHOLOGICAL_DATA_FIXTURES) == (
        'empty','one_row','fifty_thousand_rows','one_hundred_columns','null_mixed_numeric','extreme_strings','dates_timezones'
    )
    assert engineering_rows(3) == engineering_rows(3)
    assert len(pathological_rows('empty')) == 0 and len(pathological_rows('one_row')) == 1
    wide = pathological_rows('one_hundred_columns')[0]
    assert len(wide) == 100 and wide['id'] == 'WIDE-001'
    time_rows = pathological_rows('dates_timezones')
    assert {row['zone'] for row in time_rows} == {'America/Chicago','Asia/Seoul'}
    extreme = pathological_rows('extreme_strings')
    csv_text = export_csv(extreme, (TableColumn('id','ID'),TableColumn('csv','CSV'),TableColumn('html','HTML')))
    assert "'=2+2" in csv_text and "'+SUM(A1:A2)" in csv_text and "'@cmd" in csv_text
    assert '<script>alert(1)</script>' in csv_text  # CSV preserves text; it is never interpreted as HTML.


async def test_server_table_source_uses_client_delete_not_reconnect_disconnect_for_cleanup():
    text = (ROOT / 'nicegui_base/integrations/nicegui_data_table.py').read_text(encoding='utf-8')
    section = text.split('class ServerDataTable', 1)[1].split('\nclass EditableTable', 1)[0]
    assert 'LatestRequestController' in section
    base = text.split('class DataTable', 1)[1].split('\nclass ServerDataTable', 1)[0]
    assert '_register_client_delete(ui,self.aclose)' in base
    assert 'ui.context.client.on_disconnect' not in section
    assert 'refresh=True' not in section
    assert 'force=True' in section


async def test_overlay_client_manager_owns_focus_scroll_lock_and_escape_priority():
    text = (ROOT / 'nicegui_base/integrations/nicegui_interactions.py').read_text(encoding='utf-8')
    for token in (
        'window.__companyUiOverlayManager',
        'const lockOwners = new Set()',
        "document.body.style.overflow = 'hidden'",
        "origin.focus({preventScroll:true})",
        "event.stopImmediatePropagation()",
        'data-cui-overlay-close',
        'data-cui-overlay-id',
        "self.element.on('show'",
        "self.element.on('hide'",
    ):
        assert token in text


async def test_async_content_announces_loading_ready_and_refresh_without_exposing_skeleton():
    text = (ROOT / 'nicegui_base/integrations/nicegui_interactions.py').read_text(encoding='utf-8')
    css = (ROOT / 'nicegui_base/feedback/css.py').read_text(encoding='utf-8')
    assert "ui.label('Loading content').classes('cui-live-region')" in text
    assert "ui.label('Content loaded').classes('cui-live-region')" in text
    assert "ui.label('Refreshing content').classes('cui-live-region')" in text
    assert 'aria-busy=' in text and 'aria-hidden="true"' in text
    assert '.cui-live-region{' in css


async def test_browser_certification_has_reusable_frame_longtask_and_resize_probe():
    text = (ROOT / 'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    for token in (
        'def _route_performance_probe(page)',
        "PerformanceObserver.supportedEntryTypes?.includes('longtask')",
        'requestAnimationFrame(step)',
        "dispatchEvent(new Event('resize'))",
        'def _performance_issues(metrics',
        "issues.extend(_performance_issues(_route_performance_probe(page)))",
    ):
        assert token in text


async def test_chart_panel_has_programmatic_summary_data_alternative_and_client_delete_cleanup():
    text = (ROOT / 'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    css = (ROOT / 'nicegui_base/visualization/css.py').read_text(encoding='utf-8')
    for token in (
        'def _chart_accessibility_summary',
        'aria-label="Chart data alternative"',
        'aria-labelledby=',
        'aria-describedby=',
        '_register_client_delete(ui,self.dispose)',
        'def dispose(self) -> None:',
        '_ACTIVE_CHARTS.discard(self)',
    ):
        assert token in text
    assert '.cui-chart-a11y{' in css

async def test_refresh_failure_is_a_distinct_stale_content_state_not_destructive_error():
    from nicegui_base.feedback import AsyncContentSpec, AsyncState
    assert AsyncContentSpec(AsyncState.STALE).state is AsyncState.STALE
    text = (ROOT / 'nicegui_base/integrations/nicegui_interactions.py').read_text(encoding='utf-8')
    css = (ROOT / 'nicegui_base/feedback/css.py').read_text(encoding='utf-8')
    stale = text.split('elif self.spec.state is AsyncState.STALE:', 1)[1]
    assert "result = content()" in text
    assert 'Refresh failed. Showing previously loaded content.' in stale
    assert 'cui-async-stale-indicator' in stale and 'self.spec.retry_label' in stale
    assert '.cui-async-stale-indicator{' in css


async def test_editable_table_latest_edit_owns_commit_and_stale_failure_cannot_rollback(monkeypatch):
    from types import SimpleNamespace
    from nicegui_base.data_table import EditCommitMode, EditableTableSpec
    from nicegui_base.integrations.nicegui_data_table import EditableTable

    class FakeElement:
        def __init__(self): self.rows=[]; self.grid=[]
        async def run_row_method(self, row_id, method, payload): self.rows.append((row_id, method, dict(payload)))
        async def run_grid_method(self, method, *args): self.grid.append((method,args))

    release_first = asyncio.Event()
    async def save(row, key, value):
        if value == 'B':
            await release_first.wait()
            raise ConnectionError('obsolete failure')

    table=EditableTable.__new__(EditableTable)
    table.spec=EditableTableSpec((TableColumn('id','ID'),TableColumn('value','Value',editable=True)), row_key='id', commit_mode=EditCommitMode.OPTIMISTIC)
    table.rows=[{'id':1,'value':'A'}]; table.validate_edit=None; table.save_edit=save; table._edit_revisions={}; table.element=FakeElement()
    first=asyncio.create_task(table._handle_edit(SimpleNamespace(args={'data':{'id':1,'value':'B'},'colId':'value','newValue':'B','oldValue':'A','rowIndex':0})))
    await asyncio.sleep(0)
    second=asyncio.create_task(table._handle_edit(SimpleNamespace(args={'data':{'id':1,'value':'C'},'colId':'value','newValue':'C','oldValue':'B','rowIndex':0})))
    await second
    release_first.set(); await first
    assert table.rows == [{'id':1,'value':'C'}]
    assert table.element.rows[-1][2]['value'] == 'C'
    assert not any(call[0] == 'setGridOption' for call in table.element.grid)


async def test_editable_table_failure_rolls_back_exact_value_restores_focus_and_maps_field_error(monkeypatch):
    from types import SimpleNamespace
    import nicegui_base.integrations.nicegui_data_table as module
    import nicegui_base.integrations.nicegui_feedback_runtime as feedback_runtime
    from nicegui_base.data_table import EditCommitMode, EditableTableSpec
    from nicegui_base.integrations.nicegui_data_table import EditableTable

    class FieldFailure(RuntimeError):
        field_errors={'value':['Must be numeric','Outside limit']}
    class FakeElement:
        def __init__(self): self.rows=[]; self.grid=[]
        async def run_row_method(self, row_id, method, payload): self.rows.append((row_id,method,dict(payload)))
        async def run_grid_method(self, method, *args): self.grid.append((method,args))
    async def save(row,key,value): raise FieldFailure('save failed')
    toasts=[]
    monkeypatch.setattr(module,'_ui',lambda: object())
    monkeypatch.setattr(feedback_runtime,'show_company_toast',lambda ui,message,**kwargs: toasts.append((message,kwargs)))
    table=EditableTable.__new__(EditableTable)
    table.spec=EditableTableSpec((TableColumn('id','ID'),TableColumn('value','Value',editable=True)),row_key='id',commit_mode=EditCommitMode.CONFIRMED)
    table.rows=[{'id':'R1','value':10}]; table.validate_edit=None; table.save_edit=save; table._edit_revisions={}; table.element=FakeElement()
    await table._handle_edit(SimpleNamespace(args={'data':{'id':'R1','value':99},'colId':'value','newValue':99,'oldValue':10,'rowIndex':4}))
    assert table.rows == [{'id':'R1','value':10}]
    assert table.element.rows[0][2]['value'] == 10 and '__cui_pending_fields' in table.element.rows[0][2]
    assert table.element.rows[-1][2] == {'id':'R1','value':10}
    assert ('setFocusedCell',(4,'value')) in table.element.grid
    assert toasts == [('Must be numeric; Outside limit', {'intent':'danger'})]


async def test_editable_cell_pending_state_is_css_only_and_boolean_renderer_is_formatter():
    from nicegui_base.data_table import ColumnKind
    from nicegui_base.integrations.nicegui_data_table import _column_def
    editable=_column_def(TableColumn('value','Value',editable=True))
    assert 'cui-table-cell--pending' in editable['cellClassRules']
    boolean=_column_def(TableColumn('ok','OK',kind=ColumnKind.BOOLEAN))
    assert ':valueFormatter' in boolean and ':cellRenderer' not in boolean
    text=(ROOT/'nicegui_base/data_table/css.py').read_text(encoding='utf-8')
    assert '.ag-cell.cui-table-cell--pending' in text


async def test_chart_updates_coalesce_while_hidden_and_resize_once_visible():
    from nicegui_base.integrations.nicegui_visualization import ChartPanel
    from nicegui_base.visualization import ChartKind, ChartPanelSpec, SeriesSpec

    class FakeElement:
        def __init__(self): self.options={}; self.updates=0; self.methods=[]
        def update(self): self.updates += 1
        async def run_chart_method(self, method, *args): self.methods.append((method,args))

    panel=ChartPanel.__new__(ChartPanel)
    panel.spec=ChartPanelSpec(title='Trend',kind=ChartKind.LINE)
    panel.series=(SeriesSpec('a','A',[1,2],kind=ChartKind.LINE),)
    panel.thresholds=(); panel.spec_limits=None; panel.theme_mode='light'; panel._disposed=False
    panel._renderable=False; panel._pending_render=False; panel.element=FakeElement()
    panel.update_series((SeriesSpec('a','A',[3,4],kind=ChartKind.LINE),))
    panel.apply_theme('dark')
    assert panel.element.updates == 0 and panel._pending_render
    await panel.set_renderable(True)
    assert panel.element.updates == 1 and panel.element.methods == [('resize',())]
    await panel.set_renderable(False)
    panel.update_series((SeriesSpec('a','A',[5,6],kind=ChartKind.LINE),))
    assert panel.element.updates == 1
    await panel.set_renderable(True)
    assert panel.element.updates == 2 and len(panel.element.methods) == 2


async def test_chart_visibility_observer_covers_intersection_zero_size_and_disconnect_cleanup():
    text=(ROOT/'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    for token in ('IntersectionObserver','ResizeObserver','rect.width>0','rect.height>0','!host.isConnected',
                  "self.container.on('cui-chart-visibility'",'await self.set_renderable(visible)','self._pending_render'):
        assert token in text


async def test_p0_lifecycle_and_latest_request_torture_leaves_no_owned_tasks():
    for _ in range(40):
        scope=LifecycleScope()
        scope.create_task(asyncio.sleep(60))
        assert scope.active_task_count == 1
        assert await scope.aclose() == ()
        assert scope.active_task_count == 0
    controller=LatestRequestController[int](cache_size=4,cache_ttl_seconds=1)
    results=[]
    for index in range(60):
        task=asyncio.create_task(controller.run(index,lambda i=index: asyncio.sleep(0,result=i)))
        results.append(task)
    await asyncio.gather(*results)
    await controller.aclose()
    assert controller.closed and controller.running == 0
