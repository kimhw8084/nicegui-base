from __future__ import annotations

import asyncio
import io
from pathlib import Path

import pytest

from nicegui_base.ai.gate import run_application_gate
from nicegui_base.ai.project import _TEMPLATE_NAMES, create_application
from nicegui_base.data_engine import (
    Aggregation,
    DataQuery,
    DataSession,
    Dataset,
    Dimension,
    FilterClause,
    FilterOperation,
    Metric,
)
from nicegui_base.data_table import (
    FilterGroup,
    FilterLogic,
    FilterOperator,
    FilterSpec,
    TableQuery,
    TableQueryEngine,
)
from nicegui_base.performance import LazyResource, RetryPolicy
from nicegui_base.security import UploadPolicy
from nicegui_base.visualization import (
    ChartAnnotation,
    ChartEvent,
    ChartPanelSpec,
    CrossFilterBinding,
    CrossFilterEngine,
    FilterMutationAction,
    SeriesSpec,
    SpatialPoint,
    WaferPoint,
    build_echarts_options,
)

ROOT = Path(__file__).parents[1]


def _dataset() -> Dataset:
    return Dataset(
        'measurements',
        (
            {'id': 1, 'tool': 'A', 'value': 10.0},
            {'id': 2, 'tool': 'B', 'value': 20.0},
            {'id': 3, 'tool': 'B', 'value': 30.0},
        ),
        dimensions=(Dimension('tool'),),
        metrics=(Metric('value_sum', field='value', aggregation=Aggregation.SUM),),
        row_key='id',
    )


def test_data_session_transaction_rolls_back_and_nested_scope_is_atomic():
    session = DataSession(_dataset())
    session.set_filter(FilterClause('tool', FilterOperation.EQUALS, 'A'))
    baseline_revision = session.revision

    with pytest.raises(RuntimeError, match='boom'):
        with session.transaction():
            session.set_filter(FilterClause('tool', FilterOperation.EQUALS, 'B'))
            session.set_search('30')
            raise RuntimeError('boom')

    assert session.filters == (FilterClause('tool', FilterOperation.EQUALS, 'A'),)
    assert session.search == ''
    assert session.revision == baseline_revision

    with session.transaction():
        session.set_search('20')
        try:
            with session.transaction():
                session.set_filter(FilterClause('tool', FilterOperation.EQUALS, 'B'))
                raise ValueError('inner')
        except ValueError:
            pass
        assert session.filters == (FilterClause('tool', FilterOperation.EQUALS, 'A'),)
        assert session.search == '20'

    assert session.revision == baseline_revision + 1


def test_closed_data_session_rejects_reads_writes_bindings_and_transactions():
    session = DataSession(_dataset())
    session.close()
    assert session.closed is True
    operations = (
        lambda: session.query(),
        lambda: session.rows(),
        lambda: session.metric('value_sum'),
        lambda: session.snapshot(),
        lambda: session.set_search('x'),
        lambda: session.set_filter(FilterClause('tool', FilterOperation.EQUALS, 'A')),
        lambda: session.watch(lambda _: None),
        lambda: session.bind(lambda s: s.revision),
    )
    for operation in operations:
        with pytest.raises(RuntimeError, match='closed'):
            operation()
    with pytest.raises(RuntimeError, match='closed'):
        with session.transaction():
            pass


def test_dataset_rejects_unknown_schema_fields_and_bad_collection_filters():
    rows = ({'id': 1, 'tool': 'A', 'value': 1.0},)
    with pytest.raises(KeyError, match='dimension'):
        Dataset('bad-dimension', rows, dimensions=(Dimension('chamber', field='chmaber'),))
    with pytest.raises(KeyError, match='metric'):
        Dataset('bad-metric', rows, metrics=(Metric('value', field='vlaue'),))
    with pytest.raises(KeyError, match='row_key'):
        Dataset('bad-key', rows, row_key='missing')
    with pytest.raises(TypeError, match='non-string collection'):
        FilterClause('tool', FilterOperation.IN, 'ABC')
    with pytest.raises(TypeError, match='non-string collection'):
        FilterSpec('tool', FilterOperator.IN, 'ABC')


def test_numeric_metric_rejects_non_numeric_values_instead_of_returning_plausible_zero():
    dataset = Dataset(
        'bad-values',
        ({'value': 'not-a-number'},),
        metrics=(Metric('total', field='value', aggregation=Aggregation.SUM),),
    )
    with pytest.raises(TypeError, match='finite numeric'):
        dataset.query(DataQuery(metrics=('total',)))


def test_compound_table_filter_ast_handles_and_or_and_zero_cache():
    rows = (
        {'id': 1, 'tool': 'A', 'value': 10},
        {'id': 2, 'tool': 'B', 'value': 20},
        {'id': 3, 'tool': 'C', 'value': 30},
    )
    expression = FilterGroup(
        FilterLogic.OR,
        (
            FilterSpec('tool', FilterOperator.EQUALS, 'A'),
            FilterGroup(
                FilterLogic.AND,
                (
                    FilterSpec('value', FilterOperator.GTE, 20),
                    FilterSpec('tool', FilterOperator.NOT_EQUALS, 'C'),
                ),
            ),
        ),
    )
    engine = TableQueryEngine(rows, max_cached_queries=0)
    result = engine.query(TableQuery(filters=(expression,), page_size=50))
    assert [row['id'] for row in result.rows] == [1, 2]
    with pytest.raises(ValueError, match='max_cached_queries'):
        TableQueryEngine(rows, max_cached_queries=-1)


def test_ag_grid_compound_filter_model_round_trips_same_column():
    from nicegui_base.integrations.nicegui_data_table import _filter_model_from_specs, _filter_specs_from_grid_model

    grid = {
        'value': {
            'operator': 'OR',
            'conditions': [
                {'filterType': 'number', 'type': 'lessThan', 'filter': 10},
                {'filterType': 'number', 'type': 'greaterThan', 'filter': 90},
            ],
        }
    }
    parsed = _filter_specs_from_grid_model(grid)
    assert len(parsed) == 1
    assert isinstance(parsed[0], FilterGroup)
    assert parsed[0].logic is FilterLogic.OR
    assert _filter_model_from_specs(parsed)['value']['operator'] == 'OR'
    assert len(_filter_model_from_specs(parsed)['value']['conditions']) == 2


@pytest.mark.asyncio
async def test_retry_policy_never_retries_cancellation():
    attempts = 0

    async def cancelled():
        nonlocal attempts
        attempts += 1
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await RetryPolicy(attempts=4, base_delay_seconds=0, max_delay_seconds=0, jitter=0).run(cancelled)
    assert attempts == 1


@pytest.mark.asyncio
async def test_lazy_resource_refresh_disposes_old_and_failed_refresh_preserves_current():
    values = iter(['first', 'second'])
    disposed: list[str] = []
    resource = LazyResource(lambda: next(values), disposer=disposed.append)
    assert await resource.get() == 'first'
    assert await resource.get(refresh=True) == 'second'
    assert disposed == ['first']

    def fail():
        raise RuntimeError('replacement failed')

    resource.loader = fail
    with pytest.raises(RuntimeError, match='replacement failed'):
        await resource.get(refresh=True)
    assert resource.loaded is True
    assert await resource.get() == 'second'
    assert disposed == ['first']
    await resource.aclose()
    assert disposed == ['first', 'second']
    with pytest.raises(RuntimeError, match='closed'):
        await resource.get()


def test_upload_policy_rejects_binary_spoof_and_accepts_valid_signature():
    policy = UploadPolicy()
    with pytest.raises(ValueError, match='does not match'):
        policy.validate_content('plot.png', 4, 'image/png', b'NOPE')
    assert policy.validate_content('plot.png', 12, 'image/png', b'\x89PNG\r\n\x1a\nmore') == 'plot.png'
    with pytest.raises(ValueError, match='binary NUL'):
        policy.validate_content('notes.txt', 3, 'text/plain', b'a\x00b')


@pytest.mark.asyncio
async def test_file_upload_handler_enforces_policy_before_application_callback():
    from nicegui_base.integrations.nicegui_components import FileUpload

    calls: list[str] = []
    upload = object.__new__(FileUpload)
    upload._closed = False
    upload.upload_policy = UploadPolicy()
    upload._on_upload = lambda event: calls.append('called')
    class Status:
        text = ''

        def set_text(self, value):
            self.text = value

    upload._upload_status = Status()
    bad_event = type('Event', (), {
        'name': 'image.png', 'size': 4, 'content_type': 'image/png', 'content': io.BytesIO(b'NOPE')
    })()
    await upload._handle_upload(bad_event)
    assert calls == []
    assert 'does not match' in upload._upload_status.text

    good = b'\x89PNG\r\n\x1a\nbody'
    good_event = type('Event', (), {
        'name': 'image.png', 'size': len(good), 'content_type': 'image/png', 'content': io.BytesIO(good)
    })()
    await upload._handle_upload(good_event)
    assert calls == ['called']


def test_navigation_permissions_fail_closed_and_allow_explicitly_authorized_items():
    from nicegui_base.integrations.nicegui_layout import _nav_visible
    from nicegui_base.navigation import NavItem

    protected = NavItem('protected', 'Protected', '/protected', permission='fab.read')
    public = NavItem('public', 'Public', '/public')
    assert _nav_visible(public, None) is True
    assert _nav_visible(protected, None) is False
    assert _nav_visible(protected, lambda permission: permission == 'fab.read') is True
    assert _nav_visible(protected, lambda _: False) is False


def test_visualization_record_series_annotations_and_spatial_contract_are_executable():
    series = SeriesSpec(
        'cd', 'CD',
        ({'ts': 'T1', 'reading': 10.1}, {'ts': 'T2', 'reading': 10.3}),
        x_key='ts', y_key='reading',
    )
    options = build_echarts_options(
        ChartPanelSpec('Process'),
        (series,),
        annotations=(ChartAnnotation('T2', 'PM event'), ChartAnnotation('T1', 'Point event', y=10.1)),
    )
    assert options['series'][0]['data'] == [['T1', 10.1], ['T2', 10.3]]
    assert options['series'][0]['markLine']['data'][0]['xAxis'] == 'T2'
    assert options['series'][0]['markPoint']['data'][0]['coord'] == ['T1', 10.1]

    for cls in (WaferPoint, SpatialPoint):
        with pytest.raises(ValueError, match='finite'):
            cls(0.0, 0.0, float('nan'))
        with pytest.raises(ValueError, match='finite'):
            cls(0.0, 0.0, 'bad')  # type: ignore[arg-type]
        assert cls(0.0, 0.0, None).value is None


def test_cross_filter_clear_emits_explicit_remove_event():
    engine = CrossFilterEngine((CrossFilterBinding('chart', 'select', 'tool'),))
    seen = []
    engine.subscribe(seen.append)
    engine.dispatch(ChartEvent('chart', 'select', value='ETCH01'))
    removals = engine.clear('tool')
    assert len(removals) == 1
    assert removals[0].action is FilterMutationAction.REMOVE
    assert removals[0].value is None
    assert seen[-1].action is FilterMutationAction.REMOVE
    assert engine.active_filters == {}


def test_callback_arity_resolution_does_not_swallow_callback_internal_type_error():
    from nicegui_base.integrations.nicegui_interactions import _call_with_optional_event

    def broken(event):
        raise TypeError('inside callback')

    with pytest.raises(TypeError, match='inside callback'):
        _call_with_optional_event(broken, object())


def test_dirty_guard_and_upload_bridge_install_lifecycle_cleanup_contracts():
    interaction_source = (ROOT / 'nicegui_base/integrations/nicegui_interactions.py').read_text(encoding='utf-8')
    upload_source = (ROOT / 'nicegui_base/integrations/nicegui_components.py').read_text(encoding='utf-8')
    assert "window.addEventListener('pagehide', cleanup" in interaction_source
    assert "document.removeEventListener('click', clickCapture, true)" in interaction_source
    assert "uploader.__cuiPasteCleanup=cleanup" in upload_source
    assert "el?.__cuiPasteCleanup?.()" in upload_source


def test_every_generated_application_template_executes_build_page(tmp_path):
    for template in _TEMPLATE_NAMES:
        target = tmp_path / template
        create_application(target, name=f'Wave58 {template}', template=template)
        report = run_application_gate(target)
        build_page = next(check for check in report.checks if check.name == 'build-page')
        assert build_page.status == 'PASS', (template, build_page.detail)
        assert report.passed is True, template

@pytest.mark.asyncio
async def test_datatable_update_rows_returns_live_task_instead_of_dropping_coroutine():
    from nicegui_base.integrations.nicegui_data_table import DataTable

    table = object.__new__(DataTable)
    seen = []

    async def replace(rows):
        await asyncio.sleep(0)
        seen.extend(rows)

    table.replace_rows = replace
    task = table.update_rows(({'id': 7},))
    assert isinstance(task, asyncio.Task)
    await task
    assert seen == [{'id': 7}]


def test_datatable_update_rows_fails_loudly_without_event_loop():
    from nicegui_base.integrations.nicegui_data_table import DataTable

    table = object.__new__(DataTable)
    table.replace_rows = lambda rows: None
    with pytest.raises(RuntimeError, match='running event loop'):
        table.update_rows(({'id': 1},))


@pytest.mark.asyncio
async def test_datatable_live_export_uses_formula_safe_company_serializer(monkeypatch):
    import nicegui_base.integrations.nicegui_data_table as table_module
    from nicegui_base.data_table import DataTableSpec, TableColumn
    from nicegui_base.integrations.nicegui_data_table import DataTable

    captured = {}

    class FakeUI:
        def download(self, content, *, filename=None, media_type=None):
            captured.update(content=content, filename=filename, media_type=media_type)

    monkeypatch.setattr(table_module, '_ui', lambda: FakeUI())
    table = object.__new__(DataTable)
    table.rows = [{'id': 1, 'label': '=HYPERLINK("bad")'}]
    table.spec = DataTableSpec(columns=(TableColumn('id', 'ID'), TableColumn('label', 'Label')))
    await table.export('safe.csv')
    decoded = captured['content'].decode('utf-8-sig')
    assert "'=HYPERLINK" in decoded
    assert captured['filename'] == 'safe.csv'


@pytest.mark.asyncio
async def test_form_validator_internal_type_error_is_not_treated_as_signature_mismatch():
    from nicegui_base.integrations.nicegui_interactions import Form

    class BrokenControl:
        def validate(self):
            raise TypeError('validator implementation bug')

    class FakeElement:
        def descendants(self, **_):
            return (BrokenControl(),)

    form = object.__new__(Form)
    form.element = FakeElement()
    with pytest.raises(TypeError, match='validator implementation bug'):
        await form.validate()


@pytest.mark.asyncio
async def test_async_loader_has_reload_semantics_and_tab_state_has_distinct_lifecycle():
    from nicegui_base.async_tools import AsyncLoader
    from nicegui_base.state import SessionState, TabState

    calls = 0

    async def load():
        nonlocal calls
        calls += 1
        return calls

    loader = AsyncLoader[int]()
    assert await loader.load(load) == 1
    assert await loader.reload() == 2
    await loader.aclose()

    session = SessionState({'value': 1})
    tab = TabState({'value': 1})
    session.close()
    tab.close()
    assert dict(session._data) == {'value': 1}
    assert dict(tab._data) == {}
