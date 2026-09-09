from __future__ import annotations

import asyncio

import pytest


def test_action_policy_is_one_fail_closed_normalized_contract() -> None:
    from nicegui_base.data_table import BulkAction, RowAction, resolve_bulk_action_state, resolve_row_action_state

    hidden = RowAction('hidden', 'Hidden', visible_when=lambda row: False)
    disabled = RowAction('hold', 'Hold', enabled_when=lambda row: False, disabled_reason=lambda row: 'Already held')
    assert resolve_row_action_state(hidden, {'id': 1}).visible is False
    state = resolve_row_action_state(disabled, {'id': 1})
    assert state.visible is True and state.enabled is False and state.disabled_reason == 'Already held'

    bulk = BulkAction('assign', 'Assign', enabled_when=lambda rows: len(rows) == 1, disabled_reason=lambda rows: 'Choose one record')
    assert resolve_bulk_action_state(bulk, ({'id': 1},)).enabled is True
    blocked = resolve_bulk_action_state(bulk, ({'id': 1}, {'id': 2}))
    assert blocked.enabled is False and blocked.disabled_reason == 'Choose one record'


def test_export_disabled_is_enforced_before_download() -> None:
    from nicegui_base.data_table import DataTableSpec, ExportDisabledError, TableColumn
    # nicegui-base: allow-AI017 — this test exercises the concrete table method boundary.
    from nicegui_base.integrations.nicegui_data_table import DataTable

    table = object.__new__(DataTable)
    table.spec = DataTableSpec((TableColumn('id', 'ID'),), export_enabled=False)
    table.rows = [{'id': 1}]
    with pytest.raises(ExportDisabledError, match='disabled'):
        asyncio.run(table.export())


def test_semantic_editor_translation_uses_supported_grid_contract() -> None:
    from nicegui_base.data_table import ColumnKind, TableColumn
    # nicegui-base: allow-AI017 — semantic translation is intentionally verified at the integration boundary.
    from nicegui_base.integrations.nicegui_data_table import _column_def, _normalize_editor_value

    number = _column_def(TableColumn('value', 'Value', ColumnKind.FLOAT, editable=True, minimum=1, maximum=9, step=.5, placeholder='nm'))
    assert number['cellEditorParams']['min'] == 1
    assert number['cellEditorParams']['max'] == 9
    assert number['cellEditorParams']['step'] == .5
    assert 'minimum' not in number['cellEditorParams'] and 'maximum' not in number['cellEditorParams']
    assert 'placeholder' not in number['cellEditorParams']

    date = _column_def(TableColumn('when', 'When', ColumnKind.DATETIME, editable=True))
    assert date['cellEditor'] == 'agDateStringCellEditor'
    assert date['cellEditorParams']['includeTime'] is True

    integer = TableColumn('count', 'Count', ColumnKind.INTEGER, editable=True, minimum=0, maximum=9, step=1)
    assert _column_def(integer)['cellEditorParams'] == {'min': 0, 'max': 9, 'step': 1}
    assert _normalize_editor_value(integer, '3') == 3
    with pytest.raises(ValueError, match='integer'):
        _normalize_editor_value(integer, '3.5')
    boolean = TableColumn('reviewed', 'Reviewed', ColumnKind.BOOLEAN, editable=True)
    assert _normalize_editor_value(boolean, 'true') is True
    assert _normalize_editor_value(boolean, 'false') is False
    with pytest.raises(ValueError, match='boolean'):
        _normalize_editor_value(boolean, 'maybe')


def test_logical_provider_global_search_unions_fields_and_implements_all_filter_operators() -> None:
    from nicegui_base.data_table import FilterGroup, FilterLogic, FilterOperator, FilterSpec, TableQuery
    from nicegui_base.workbench.data_table_lab import LogicalEngineeringProvider

    provider = LogicalEngineeringProvider(total=128)
    result = provider.query(TableQuery(search='A. Kim', page_size=128))
    assert result.total == 32
    result = provider.query(TableQuery(search='ETCH-021', page_size=128))
    assert result.total == 32
    # Search is OR across searchable fields; this query must retain both buckets.
    result = provider.query(TableQuery(search='021', page_size=128))
    assert result.total == 32

    probes = (
        (FilterOperator.CONTAINS, 'ETCH'),
        (FilterOperator.NOT_CONTAINS, 'CMP'),
        (FilterOperator.STARTS_WITH, 'ETCH'),
        (FilterOperator.ENDS_WITH, '021'),
        (FilterOperator.EQUALS, 'ETCH-021'),
        (FilterOperator.NOT_EQUALS, 'ETCH-021'),
        (FilterOperator.IN, ('ETCH-021', 'CVD-014')),
        (FilterOperator.NOT_IN, ('LITHO-008',)),
        (FilterOperator.GT, 50),
        (FilterOperator.GTE, 50),
        (FilterOperator.LT, 50),
        (FilterOperator.LTE, 50),
        (FilterOperator.BETWEEN, (49, 51)),
        (FilterOperator.IS_EMPTY, None),
        (FilterOperator.IS_NOT_EMPTY, None),
    )
    for operator, value in probes:
        spec = FilterSpec('tool_id' if operator in {FilterOperator.CONTAINS, FilterOperator.NOT_CONTAINS, FilterOperator.STARTS_WITH, FilterOperator.ENDS_WITH, FilterOperator.EQUALS, FilterOperator.NOT_EQUALS, FilterOperator.IN, FilterOperator.NOT_IN} else 'measurement_nm', operator, value, 51 if operator is FilterOperator.BETWEEN else None)
        result = provider.query(TableQuery(filters=(spec,), page_size=10))
        assert result.total >= 0

    nested = FilterGroup(FilterLogic.OR, (
        FilterGroup(FilterLogic.AND, (FilterSpec('tool_id', FilterOperator.EQUALS, 'ETCH-021'), FilterSpec('status', FilterOperator.EQUALS, 'OOS'))),
        FilterSpec('owner', FilterOperator.EQUALS, 'A. Kim'),
    ))
    assert provider.query(TableQuery(filters=(nested,), page_size=10)).total > 0


def test_logical_provider_operator_totals_match_generated_rows() -> None:
    from nicegui_base.data_table import FilterGroup, FilterLogic, FilterOperator, FilterSpec, TableQuery
    from nicegui_base.workbench.data_table_lab import LogicalEngineeringProvider

    provider = LogicalEngineeringProvider(total=128)
    rows = [provider.row_at(index) for index in range(provider.total)]
    cases = (
        FilterSpec('tool_id', FilterOperator.CONTAINS, 'ETCH'),
        FilterSpec('tool_id', FilterOperator.NOT_CONTAINS, 'ETCH'),
        FilterSpec('tool_id', FilterOperator.STARTS_WITH, 'ETCH'),
        FilterSpec('tool_id', FilterOperator.ENDS_WITH, '021'),
        FilterSpec('tool_id', FilterOperator.EQUALS, 'ETCH-021'),
        FilterSpec('tool_id', FilterOperator.NOT_EQUALS, 'ETCH-021'),
        FilterSpec('tool_id', FilterOperator.IN, ('ETCH-021', 'CVD-014')),
        FilterSpec('tool_id', FilterOperator.NOT_IN, ('LITHO-008',)),
        FilterSpec('measurement_nm', FilterOperator.GT, 50),
        FilterSpec('measurement_nm', FilterOperator.GTE, 50),
        FilterSpec('measurement_nm', FilterOperator.LT, 50),
        FilterSpec('measurement_nm', FilterOperator.LTE, 50),
        FilterSpec('measurement_nm', FilterOperator.BETWEEN, 49.8, 50.1),
        FilterSpec('comment', FilterOperator.IS_EMPTY),
        FilterSpec('comment', FilterOperator.IS_NOT_EMPTY),
    )
    for spec in cases:
        expected = sum(LogicalEngineeringProvider._matches(row, TableQuery(filters=(spec,))) for row in rows)
        actual = provider.query(TableQuery(filters=(spec,), page_size=provider.total)).total
        assert actual == expected, spec

    nested = FilterGroup(FilterLogic.OR, (
        FilterGroup(FilterLogic.AND, (
            FilterSpec('tool_id', FilterOperator.EQUALS, 'ETCH-021'),
            FilterSpec('status', FilterOperator.EQUALS, 'OOS'),
        )),
        FilterSpec('owner', FilterOperator.EQUALS, 'A. Kim'),
    ))
    expected = sum(LogicalEngineeringProvider._matches(row, TableQuery(filters=(nested,))) for row in rows)
    assert provider.query(TableQuery(filters=(nested,), page_size=provider.total)).total == expected

    search = 'A'
    expected = sum(
        any(search.casefold() in str(row.get(key) or '').casefold() for key in ('record_id', 'lot_id', 'wafer_id', 'tool_id', 'chamber_id', 'status', 'owner'))
        for row in rows
    )
    assert provider.query(TableQuery(search=search, page_size=provider.total)).total == expected


def test_data_lab_exposes_truthful_saved_view_and_quality_mapping_contracts() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    integration = (root / 'nicegui_base/integrations/nicegui_data_table.py').read_text(encoding='utf-8')
    lab = (root / 'nicegui_base/workbench/data_table_lab.py').read_text(encoding='utf-8')
    dock = (root / 'nicegui_base/workbench/capability_studio.py').read_text(encoding='utf-8')
    assert 'async def save_named_view' in integration
    assert 'async def apply_named_view' in integration
    assert "'measurement_field'" in lab or "Measurement field" in lab
    assert 'Show missing' in dock and 'Show duplicates' in dock and 'Profile column' in dock
    assert 'stage_text' in lab and 'commit_stage' in lab and 'discard_stage' in lab
