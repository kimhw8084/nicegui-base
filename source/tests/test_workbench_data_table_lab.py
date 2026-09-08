from __future__ import annotations

from pathlib import Path

import asyncio
import math


ROOT = Path(__file__).resolve().parents[1]


def test_data_lab_has_one_coherent_fixture_and_exact_lab_order() -> None:
    from nicegui_base.workbench.data_table_lab import LAB_KEYS, LABS, DataLabSession, engineering_fixture

    rows = engineering_fixture()
    assert LAB_KEYS == ('grid', 'actions', 'edit', 'visualize', 'import', 'detail', 'server', 'states')
    assert tuple(item.key for item in LABS) == LAB_KEYS
    assert len(rows) == 64
    assert rows[0]['record_id'] == 'R-000001'
    assert rows[-1]['record_id'] == 'R-000064'
    assert {'Nominal', 'Watch', 'OOS', 'Hold'} <= {row['status'] for row in rows}
    assert any(row['comment'] is None for row in rows)
    assert any(row['reviewed'] is False for row in rows)
    assert DataLabSession().summary()['records'] == 64


def test_data_lab_filter_and_summary_preserve_shared_row_contract() -> None:
    from nicegui_base.workbench.data_table_lab import DataLabSession

    session = DataLabSession()
    before = tuple(row['record_id'] for row in session.rows)
    filtered = session.filtered(status='OOS', tool='ETCH-021')
    assert filtered
    assert all(row['status'] == 'OOS' and row['tool_id'] == 'ETCH-021' for row in filtered)
    assert session.summary(filtered)['records'] == len(filtered)
    assert tuple(row['record_id'] for row in session.rows) == before


def test_provider_query_is_bounded_and_supports_filters_and_pages() -> None:
    from nicegui_base.data_table import FilterOperator, FilterSpec, TableQuery
    from nicegui_base.workbench.data_table_lab import engineering_fixture, query_provider

    result = query_provider(
        engineering_fixture(),
        TableQuery(page=2, page_size=5, search='ETCH-021', filters=(FilterSpec('status', FilterOperator.IN, ('Watch', 'OOS', 'Hold')),)),
    )
    assert len(result.rows) <= 5
    assert result.total >= len(result.rows)
    assert all('ETCH-021' in row['tool_id'] for row in result.rows)


def test_table_contract_exposes_stripes_and_normalized_layout_operations() -> None:
    from nicegui_base.data_table import DataTableSpec, PinPosition, TableColumn

    spec = DataTableSpec((TableColumn('id', 'ID', pinned=PinPosition.LEFT),), striped=True, persist_key='test')
    assert 'cui-data-table--striped' in spec.classes
    source = (ROOT / 'nicegui_base' / 'integrations' / 'nicegui_data_table.py').read_text(encoding='utf-8')
    assert 'async def set_column_pinned' in source
    assert 'async def reset_layout' in source
    assert 'async def set_filters' in source
    assert 'async def clear_sorting' in source
    assert "js_handler='() => emit()'" in source
    assert 'getSelectedRows' not in source.split("self.element.on('selectionChanged'", 1)[1].split("self.element.on(", 1)[0]
    assert "'filterType': 'text'" in source
    assert "'operator': 'OR'" in source


def test_data_page_projects_single_active_lab_not_the_old_capability_wall() -> None:
    source = (ROOT / 'nicegui_base' / 'workbench' / 'app.py').read_text(encoding='utf-8')
    assert 'render_data_table_lab()' in source
    data_page = source[source.index('def data_page'):source.index('def quality_page')]
    assert 'render_data_capability_map' not in data_page
    assert 'render_data_dock' not in data_page


def test_typed_column_contract_describes_editors_without_raw_grid_names() -> None:
    from nicegui_base.data_table import ColumnKind, TableColumn

    numeric = TableColumn('measurement', 'Measurement', ColumnKind.FLOAT, editable=True, minimum=0, maximum=100, step=0.001)
    status = TableColumn('status', 'Status', ColumnKind.STATUS, editable=True, choices=('Nominal', 'Watch', 'OOS'))
    boolean = TableColumn('reviewed', 'Reviewed', ColumnKind.BOOLEAN, editable=True)
    assert numeric.editor_spec()['kind'] == 'number'
    assert numeric.editor_spec()['minimum'] == 0
    assert status.editor_spec()['kind'] == 'select'
    assert status.editor_spec()['choices'] == ('Nominal', 'Watch', 'OOS')
    assert boolean.editor_spec()['kind'] == 'boolean'


def test_declared_table_defaults_survive_hydration_and_reset_contract_is_public() -> None:
    from nicegui_base.data_table import DataTableSpec, PinPosition, TableColumn, TableDensity
    from nicegui_base.integrations.nicegui_data_table import _stateful_table_spec

    declared = DataTableSpec(
        (TableColumn('id', 'ID', width=120, pinned=PinPosition.LEFT), TableColumn('value', 'Value', visible=True)),
        density=TableDensity.COMPACT,
        persist_key='reset-contract',
    )
    hydrated = _stateful_table_spec(declared, __import__('nicegui_base.data_table', fromlist=['TableState']).TableState(
        density=TableDensity.DENSE, visible_columns=['value'], column_order=['value', 'id'],
        column_widths={'id': 240}, pinned_right=['value'], search='old',
    ))
    assert hydrated.density is TableDensity.DENSE
    assert hydrated.columns[0].key == 'value'
    assert declared.density is TableDensity.COMPACT
    source = (ROOT / 'nicegui_base' / 'integrations' / 'nicegui_data_table.py').read_text(encoding='utf-8')
    assert 'self.default_spec = spec' in source
    assert 'declared.columns' in source


def test_row_transaction_contract_reconciles_updates_and_removals() -> None:
    source = (ROOT / 'nicegui_base' / 'integrations' / 'nicegui_data_table.py').read_text(encoding='utf-8')
    assert 'async def update_rows_by_key' in source
    assert 'async def remove_rows_by_key' in source
    transaction = source[source.index('async def apply_row_transaction'):source.index('async def _handle_column_resized_persist')]
    assert 'reconcile_selection' in transaction and 'applyTransaction' in transaction
    assert 'setDataValue' in transaction
    assert 'preserved_selection' in transaction
    assert '_sync_selection_bar' in transaction


def test_selection_actions_keep_normalized_rows_during_client_transaction() -> None:
    source = (ROOT / 'nicegui_base' / 'integrations' / 'nicegui_data_table.py').read_text(encoding='utf-8')
    assert '_selected_rows_cache' in source
    assert '_selection_restore_pending' in source
    assert 'return [row for row in self.rows if row.get(self.spec.row_key) in keys]' in source


def test_data_dock_import_is_stageable_without_mutating_active_rows() -> None:
    from nicegui_base.workbench.data_dock import DataDockModel

    model = DataDockModel(({'id': 'A', 'value': 1},), sample_name='fixture')
    result = model.stage_text('id\tvalue\nB\t2', source_name='incoming.tsv')
    assert result.ok
    assert tuple(row['id'] for row in model.rows) == ('A',)
    assert model.staged_snapshot is not None
    diff = model.schema_diff()
    assert diff['added'] == [] and diff['removed'] == []
    model.commit_stage()
    assert tuple(row['id'] for row in model.rows) == ('B',)
    model.stage_text('id\tvalue\nC\t3', source_name='cancel.tsv')
    model.discard_stage()
    assert tuple(row['id'] for row in model.rows) == ('B',)


def test_logical_provider_is_bounded_and_mathematically_valid_at_late_pages() -> None:
    from nicegui_base.data_table import FilterOperator, FilterSpec, SortDirection, SortSpec, TableQuery
    from nicegui_base.workbench.data_table_lab import LogicalEngineeringProvider

    provider = LogicalEngineeringProvider()
    last_page = (provider.total + 49) // 50
    for query in (TableQuery(page=1, page_size=50), TableQuery(page=2, page_size=50), TableQuery(page=last_page, page_size=50)):
        result = provider.query(query)
        assert result.total == provider.total
        assert result.page == query.page and result.page_size == query.page_size
        assert result.rows
    filtered = provider.query(TableQuery(search='ETCH-021', page_size=25))
    assert filtered.total > 0 and len(filtered.rows) <= 25
    assert all('ETCH-021' in row['tool_id'] for row in filtered.rows)
    sorted_page = provider.query(TableQuery(page=3, page_size=10, filters=(FilterSpec('status', FilterOperator.EQUALS, 'OOS'),), sorts=(SortSpec('record_id', SortDirection.DESC),)))
    assert sorted_page.rows and sorted_page.rows[0]['status'] == 'OOS'
    assert all(math.isfinite(float(row['measurement_nm'])) for row in sorted_page.rows)


def test_edit_specimen_uses_confirmed_mode_and_has_no_fake_actions() -> None:
    from nicegui_base.data_table import EditCommitMode
    source = (ROOT / 'nicegui_base' / 'workbench' / 'data_table_lab.py').read_text(encoding='utf-8')
    assert 'commit_mode=EditCommitMode.CONFIRMED' in source
    assert "'Save staged changes'" not in source
    assert "'Read-only example'" not in source
    assert EditCommitMode.CONFIRMED.value == 'confirmed'


def test_canonical_table_css_owns_striped_and_state_anatomy() -> None:
    from nicegui_base.data_table.css import build_data_table_css

    css = build_data_table_css()
    assert '.cui-data-table--striped .ag-row:nth-child(even)' in css
    assert '.cui-data-table .ag-row-selected' in css
    assert '.cui-data-table .ag-pinned-left-cols-container' in css
