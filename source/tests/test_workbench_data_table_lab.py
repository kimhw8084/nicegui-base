from __future__ import annotations

from pathlib import Path


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
