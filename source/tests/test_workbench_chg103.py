from __future__ import annotations


def test_search_specimen_filters_results_and_status_facet_from_one_record_truth() -> None:
    from nicegui_base.workbench.pattern_specimens import (
        _PATTERN_ROWS,
        _filter_pattern_records,
        _result_summary,
        _selected_record,
    )

    records = tuple(_PATTERN_ROWS)
    assert _filter_pattern_records(records, query='NO_MATCH_987') == ()
    assert _result_summary(query='NO_MATCH_987', status='all', count=0) == '0 results for “NO_MATCH_987” · Status: Any status'

    etch = _filter_pattern_records(records, query='ETCH')
    assert len(etch) == 8
    assert {row['id'] for row in etch} == {row['id'] for row in records}

    lot = _filter_pattern_records(records, query='LOT-240904')
    assert [row['id'] for row in lot] == ['LOT-240904']

    alert_etch = _filter_pattern_records(records, query='ETCH', status='alert')
    assert [row['id'] for row in alert_etch] == ['LOT-240904', 'LOT-240908']
    assert _result_summary(query='ETCH', status='alert', count=len(alert_etch)) == '2 results for “ETCH” · Status: Alert'

    selected = _selected_record(alert_etch, 'LOT-240904')
    assert selected is not None and selected['id'] == 'LOT-240904'
    assert _selected_record(alert_etch, 'LOT-240902') is None


def test_data_explorer_selection_follows_visible_rows_across_filter_transitions() -> None:
    from nicegui_base.workbench.pattern_specimens import (
        _PATTERN_ROWS,
        _filter_data_explorer_records,
        _selected_record,
    )

    records = tuple(_PATTERN_ROWS)
    filtered = _filter_data_explorer_records(records, query='LOT-240904')
    selected = _selected_record(filtered, 'LOT-240904')
    assert selected is not None and selected['id'] == 'LOT-240904'

    same_tool = _filter_data_explorer_records(records, tool='ETCH-07')
    assert _selected_record(same_tool, 'LOT-240904') is selected

    different_tool = _filter_data_explorer_records(records, tool='ETCH-03')
    assert _selected_record(different_tool, 'LOT-240904') is None


def test_render_table_forwards_selected_rows_without_regressing_generic_events(monkeypatch) -> None:
    from nicegui_base import DataTable
    from nicegui_base.workbench.visual_specimens import render_table

    data_table_module = __import__(DataTable.__module__, fromlist=['DataTable'])

    class FakeDataTable:
        def __init__(self, rows, columns, *, on_select, **kwargs):
            self.rows = rows
            self.columns = columns
            self.on_select = on_select

    monkeypatch.setattr(data_table_module, 'DataTable', FakeDataTable)
    events: list[str] = []
    selected: list[tuple[dict[str, object], ...]] = []
    row = {'id': 'LOT-240904', 'status': 'Alert'}

    table = render_table(
        'data_table',
        title='Lots',
        rows=(row,),
        on_event=events.append,
        on_select=selected.append,
    )
    table.on_select(({'id': 'LOT-240904', 'status': 'Alert', '__preview_row': 0},))

    assert events == ['Table selection changed']
    assert selected == [(row,)]

    generic_events: list[str] = []
    generic_table = render_table('data_table', title='Lots', rows=(row,), on_event=generic_events.append)
    generic_table.on_select(({'id': 'LOT-240904', 'status': 'Alert', '__preview_row': 0},))
    assert generic_events == ['Table selection changed']
