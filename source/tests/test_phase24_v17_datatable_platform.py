from __future__ import annotations

from pathlib import Path

from nicegui_base.data_table import ColumnKind, TableColumn
from nicegui_base.data_table.css import build_data_table_css
from nicegui_base.integrations.nicegui_data_table import SparklineCell, _column_def

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'nicegui_base/integrations/nicegui_data_table.py').read_text(encoding='utf-8')
BROWSER = (ROOT / 'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')


def test_phase24_search_is_company_owned_native_input_not_quasar_field():
    toolbar = SOURCE[SOURCE.index('class TableToolbar'):SOURCE.index('class TableDensitySelector')]
    assert "ui.element('input').classes('cui-table-search__input')" in toolbar
    assert 'type="search"' in toolbar
    assert 'js_handler=\'e => emit(e.target.value)\'' in toolbar
    assert 'ui.input(' not in toolbar


def test_phase24_toolbar_is_one_consistent_action_grammar():
    for label in ('Columns', 'Export', 'Refresh'):
        assert label in SOURCE
    assert SOURCE.count("classes('cui-table-tool-button')") >= 4
    css = build_data_table_css()
    assert '.cui-table-toolbar__actions' in css
    assert '.cui-table-tool-button' in css
    assert 'height:34px' in css


def test_phase24_density_contract_is_exactly_44_38_34_everywhere():
    assert "_DENSITY_ROWS = {'comfortable':44,'compact':38,'dense':34}" in SOURCE
    css = build_data_table_css()
    assert '--cui-table-row-comfortable: 44px' in css
    assert '--cui-table-row-compact: 38px' in css
    assert '--cui-table-row-dense: 34px' in css
    assert '44 px rows' not in SOURCE  # generated from one canonical dictionary, not duplicated literals


def test_phase24_grid_preserves_virtualized_fast_path():
    for token in ("'rowBuffer': 10", "'debounceVerticalScrollbar': False", "'cacheQuickFilter': True", "'suppressColumnMoveAnimation': True", "'suppressScrollOnNewData': True", "'animateRows': False"):
        assert token in SOURCE
    assert "run_grid_method('setGridOption','quickFilterText'" in SOURCE
    assert "run_grid_method('setGridOption','rowData'" in SOURCE
    assert "run_grid_method('setGridOption','rowHeight'" in SOURCE
    assert 'self.element.update()' not in SOURCE



def test_phase24_grid_scroll_path_never_debounces_or_animates_row_hover():
    # Scroll input must move the rendered viewport immediately. A tiny row buffer plus
    # AG Grid vertical-scroll debouncing created a visible "catch-up" delay on trackpads.
    assert "'debounceVerticalScrollbar': False" in SOURCE
    assert "'rowBuffer': 10" in SOURCE
    css = build_data_table_css()
    row_rule = css[css.index('.cui-data-table .ag-row {'):css.index('.cui-data-table .ag-row-hover')]
    assert 'transition:' not in row_rule

def test_phase24_search_updates_filtered_record_count_without_grid_remount():
    assert 'async def _sync_displayed_count' in SOURCE
    assert "run_grid_method('getDisplayedRowCount')" in SOURCE
    assert "return f'{shown:,} of {total:,} records'" in SOURCE
    set_search = SOURCE[SOURCE.index('    async def set_search(self, value:str):'):SOURCE.index('    async def refresh(self):')]
    assert '.update()' not in set_search


def test_phase24_column_manager_uses_company_checkbox_anatomy():
    block = SOURCE[SOURCE.index('class TableColumnManager'):SOURCE.index('class TableSelectionBar')]
    assert "ui.element('input').classes('cui-table-column-option__native')" in block
    assert "js_handler='e => emit(e.target.checked)'" in block
    assert 'ui.checkbox(' not in block
    css = build_data_table_css()
    assert '.cui-table-column-option__check' in css
    assert ':checked + .cui-table-column-option__check' in css


def test_phase24_numeric_formatting_and_svg_sparklines_are_semantic():
    percent = _column_def(TableColumn('yield', 'Yield', ColumnKind.PERCENT, decimals=1))
    floating = _column_def(TableColumn('value', 'Value', ColumnKind.FLOAT, decimals=3, unit='nm'))
    assert ':valueFormatter' in percent and '%' in percent[':valueFormatter']
    assert 'toFixed(3)' in floating[':valueFormatter'] and 'nm' in floating[':valueFormatter']
    renderer = SparklineCell.renderer()
    assert '<svg class="cui-table-sparkline"' in renderer
    assert '<polyline' in renderer and '<circle' in renderer
    assert "bars='▁▂▃" not in renderer


def test_phase24_row_actions_render_as_icon_plus_label_buttons():
    assert 'cui-table-row-action__icon' in SOURCE
    assert 'role="button"' in SOURCE
    assert "render_icon_svg(action.icon or 'more'" in SOURCE
    css = build_data_table_css()
    assert '.cui-table-row-action__icon' in (ROOT/'nicegui_base/design/hardening_css.py').read_text()


def test_phase24_global_density_errors_are_not_silently_swallowed():
    block = SOURCE[SOURCE.index('async def apply_all_table_density'):SOURCE.index('def _js_literal')]
    assert 'failures:' in block
    assert 'raise RuntimeError' in block
    assert 'except Exception:\n            continue' not in block


def test_phase24_low_priority_header_and_saved_view_paths_are_real():
    assert "'headerClass': header_class" in SOURCE
    preset = SOURCE[SOURCE.index('class TablePresetSelector'):SOURCE.index('__all__=')]
    assert "classes('cui-table-tool-button cui-table-view-button')" in preset
    # Presets now delegate one complete deterministic state transition to the
    # canonical DataTable authority, which also clears omitted sorting/filter
    # state and synchronizes persistence/UI controls without remounting.
    assert 'await self.table.apply_view_state(target, name=preset.name)' in preset
    assert 'sorts=list(preset.sorts)' in preset
    assert 'ui.select(' not in preset


def test_phase24_browser_certification_proves_filter_density_actions_and_no_remount():
    for token in (
        "el.dataset.cuiPhase4Probe='stable'",
        'table search remounted AG Grid root',
        'Dense table mode did not materially reduce row height',
        'table density change remounted AG Grid root',
        'Inspect row action did not open inspector',
        'table search did not expose filtered record count',
        'table quick filter exceeded 900ms interaction budget',
        'table density change exceeded 700ms interaction budget',
        'table vertical scroll did not render later rows within 350ms',
        'table vertical scroll exceeded 350ms responsiveness budget',
    ):
        assert token in BROWSER
