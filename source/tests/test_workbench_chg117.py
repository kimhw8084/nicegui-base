from __future__ import annotations

import asyncio
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_data_explorer_redraw_keeps_one_governed_table_and_authored_key() -> None:
    source = (ROOT / 'nicegui_base/workbench/pattern_specimens.py').read_text(encoding='utf-8')
    block = source[source.index("elif key == 'data_explorer'"):source.index("elif key == 'master_detail'")]

    assert block.count('render_table(') == 1
    assert 'def draw_explorer' not in block
    assert 'await table.replace_rows(selected)' in block
    assert "table.set_title(f'Lot records ({len(selected)})')" in block
    assert "row_key='id'" in block
    assert "title=f'Lot records ({len(visible_records())})'" in block


def test_data_table_title_updates_without_remounting() -> None:
    from nicegui_base import DataTable, DataTableSpec, TableColumn

    class FakeLabel:
        def __init__(self) -> None:
            self.text = ''

        def set_text(self, text: str) -> None:
            self.text = text

    table = object.__new__(DataTable)
    table.spec = DataTableSpec((TableColumn('id', 'ID'),), title='Lots (1)', persist_state=False)
    table.title_label = FakeLabel()

    table.set_title('Lots (8)')

    assert table.spec.title == 'Lots (8)'
    assert table.title_label.text == 'Lots (8)'


def test_render_table_preserves_authored_identity_and_default_preview_contract(monkeypatch) -> None:
    from nicegui_base import DataTable
    from nicegui_base.workbench.visual_specimens import preview_table_data, render_table

    data_table_module = __import__(DataTable.__module__, fromlist=['DataTable'])

    class FakeDataTable:
        def __init__(self, rows, columns, *, on_select, **kwargs):
            self.rows = rows
            self.columns = columns
            self.on_select = on_select
            self.row_key = kwargs['row_key']

    monkeypatch.setattr(data_table_module, 'DataTable', FakeDataTable)
    row = {'id': 'LOT-240904', 'status': 'Alert'}
    selected: list[tuple[dict[str, object], ...]] = []

    stable_data, stable_key = preview_table_data((row,), row_key='id')
    assert stable_key == 'id'
    assert stable_data == [row]
    assert '__preview_row' not in stable_data[0]

    table = render_table('data_table', title='Lots', rows=(row,), row_key='id', on_select=selected.append)
    assert table.row_key == 'id'
    table.on_select((dict(row),))
    assert selected == [(row,)]

    generic_data, generic_key = preview_table_data((row,))
    assert generic_key == '__preview_row'
    assert generic_data[0]['__preview_row'] == 0


def _make_replace_rows_table(rows):
    from nicegui_base import DataTable, DataTableSpec, SelectionMode, TableColumn, TableState

    class FakeElement:
        def __init__(self, initial_rows):
            self.options = {'rowData': list(initial_rows)}
            self.selected_keys: set[str] = set()
            self.calls: list[tuple[str, tuple[object, ...]]] = []

        async def run_grid_method(self, method, *args):
            self.calls.append((method, args))
            if method == 'setGridOption' and args[0] == 'rowData':
                self.options['rowData'] = list(args[1])
            elif method == 'deselectAll':
                self.selected_keys.clear()
            elif method == 'getDisplayedRowCount':
                return len(self.options['rowData'])
            return None

    spec = DataTableSpec(
        (TableColumn('id', 'ID'), TableColumn('status', 'Status')),
        row_key='id', selection=SelectionMode.SINGLE, persist_state=False,
    )
    table = object.__new__(DataTable)
    table.spec = spec
    table.rows = list(rows)
    table.state = TableState()
    table.element = FakeElement(rows)
    table.displayed_count = len(rows)
    table.search = ''
    table._selected_rows_cache = ()
    table._selection_restore_until = 0.0
    table._selection_restore_pending = False
    table._suppress_callbacks = False
    table._closed = True
    table._restoring_state = False
    table._view_apply_until = 0.0
    table.preferences = None
    table.on_view_changed = None
    table.selection_bar = None
    table.row_actions = ()
    table.footer_label = None
    table.footer_density_label = None

    async def restore_selection():
        table.element.selected_keys = set(table.state.selected_keys)

    table._restore_selection = restore_selection
    return table


def test_data_explorer_selection_preserves_clears_and_requires_explicit_reselection() -> None:
    from nicegui_base.workbench.pattern_specimens import (
        _PATTERN_ROWS,
        _filter_data_explorer_records,
        _selected_record,
    )

    records = tuple(_PATTERN_ROWS)
    state = {'query': 'LOT-240904', 'tool': 'all', 'selected_id': 'LOT-240904'}
    visible = _filter_data_explorer_records(records, query=state['query'], tool=state['tool'])
    table = _make_replace_rows_table(visible)
    selected = _selected_record(visible, state['selected_id'])
    assert selected is not None
    table.state.selected_keys = {selected['id']}
    table._selected_rows_cache = (dict(selected),)
    table.element.selected_keys = {selected['id']}
    mounted_element = table.element

    def explicit_select(row):
        state['selected_id'] = row['id']
        table.state.selected_keys = {row['id']}
        table._selected_rows_cache = (dict(row),)
        table.element.selected_keys = {row['id']}

    def redraw(*, query: str, tool: str = 'all'):
        state['query'] = query
        state['tool'] = tool
        next_rows = _filter_data_explorer_records(records, query=query, tool=tool)
        if _selected_record(next_rows, state['selected_id']) is None:
            state['selected_id'] = None
        asyncio.run(table.replace_rows(next_rows))
        detail = _selected_record(next_rows, state['selected_id'])
        actual = tuple(row for row in table.rows if row['id'] in table.element.selected_keys)
        return detail, actual

    detail, actual = redraw(query='LOT')
    assert detail is not None and detail['id'] == 'LOT-240904'
    assert tuple(row['id'] for row in actual) == ('LOT-240904',)
    assert table.element is mounted_element
    assert table.state.selected_keys == {'LOT-240904'}

    detail, actual = redraw(query='LOT-240905')
    assert detail is None
    assert state['selected_id'] is None
    assert actual == ()
    assert table.state.selected_keys == set()

    detail, actual = redraw(query='LOT')
    assert detail is None
    assert actual == ()
    assert table.state.selected_keys == set()

    explicit_select(_selected_record(_filter_data_explorer_records(records, query='LOT'), 'LOT-240904'))
    detail, actual = redraw(query='LOT')
    assert detail is not None and detail['id'] == 'LOT-240904'
    assert tuple(row['id'] for row in actual) == ('LOT-240904',)

    detail, actual = redraw(query='LOT', tool='ETCH-07')
    assert detail is not None and detail['id'] == 'LOT-240904'
    assert tuple(row['id'] for row in actual) == ('LOT-240904',)

    detail, actual = redraw(query='LOT', tool='ETCH-03')
    assert detail is None
    assert state['selected_id'] is None
    assert actual == ()
    assert table.state.selected_keys == set()

    detail, actual = redraw(query='LOT', tool='all')
    assert detail is None
    assert actual == ()

    explicit_select(_selected_record(_filter_data_explorer_records(records, query='LOT'), 'LOT-240904'))
    detail, actual = redraw(query='LOT', tool='all')
    assert detail is not None and detail['id'] == 'LOT-240904'
    assert tuple(row['id'] for row in actual) == ('LOT-240904',)
