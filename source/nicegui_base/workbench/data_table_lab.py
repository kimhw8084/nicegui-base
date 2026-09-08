"""The bounded, single-active-lab Data & Tables reference.

This module is intentionally a projection of the public table and visualization
authorities.  It owns the reference fixture and page composition, not another
grid implementation or another persistence store.
"""
from __future__ import annotations

import asyncio
import math
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping, Sequence

from nicegui_base.data_table import (
    BulkAction, ColumnKind, DataTableSpec, EditCommitMode, EditableTableSpec, FilterExpression, FilterGroup, FilterLogic, FilterOperator, FilterSpec,
    PinPosition, RowAction, SelectionMode, ServerDataTableSpec,
    SortDirection, SortSpec, TableColumn, TableDensity, TablePreset, TableQuery, TableResult,
)
from nicegui_base.data_table.engine import TableQueryEngine


LAB_KEYS = ('grid', 'actions', 'edit', 'visualize', 'import', 'detail', 'server', 'states')


@dataclass(frozen=True, slots=True)
class DataLabSpec:
    key: str
    label: str
    purpose: str
    chips: tuple[str, ...] = ()


LABS = (
    DataLabSpec('grid', 'Grid', 'The production read-oriented grid: query, layout, views and persisted state.', ('64 records', 'Persisted view')),
    DataLabSpec('actions', 'Actions', 'Selection, row actions and safe review workflows for an operations queue.', ('Multi-select', 'Compare')),
    DataLabSpec('edit', 'Edit', 'Typed editing, validation, CRUD and a deliberate audit trail for engineering records.', ('Typed editors', 'Rollback')),
    DataLabSpec('visualize', 'Visualize', 'A linked table and governed analytical view sharing one filtered population.', ('Linked state', 'SPC')),
    DataLabSpec('import', 'Import', 'Paste or upload a bounded dataset, inspect its contract, then commit it safely.', ('Preview first', 'Quality')),
    DataLabSpec('detail', 'Detail', 'Browse lot and wafer records with a real master/detail inspection surface.', ('Drawer detail', 'Related records')),
    DataLabSpec('server', 'Server', 'The same table contract against a 250,000-record provider without loading it into the browser.', ('Paged provider', 'Stale/retry')),
    DataLabSpec('states', 'States', 'One controlled specimen for loading, empty, stale, error, read-only and restricted states.', ('State contract', 'Accessible')),
)


def _fixture_row(index: int) -> dict[str, Any]:
    tool = ('ETCH-021', 'CVD-014', 'LITHO-008', 'CMP-006')[index % 4]
    chamber = f'CH-{(index % 4) + 1}'
    status = ('Nominal', 'Nominal', 'Watch', 'Nominal', 'OOS', 'Hold', 'Nominal', 'Watch')[index % 8]
    measurement = round(49.72 + ((index * 17) % 31) / 100 - (0.38 if status == 'OOS' else 0), 3)
    target = 50.0
    timestamp = datetime(2026, 9, 7, 12, 0) - timedelta(minutes=index * 37)
    return {
        'record_id': f'R-{index + 1:03d}',
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M'),
        'lot_id': f'LOT-{(index // 4) + 101:03d}',
        'wafer_id': f'W{(index % 25) + 1:02d}',
        'tool_id': tool,
        'chamber_id': chamber,
        'product': ('N7 Logic', 'N5 SRAM', '28nm Analog')[index % 3],
        'operation': ('Etch', 'Deposition', 'Lithography', 'CMP')[index % 4],
        'recipe': f'RCP-{18 + index % 5}',
        'measurement_nm': measurement,
        'target_nm': target,
        'delta_nm': round(measurement - target, 3),
        'yield_pct': round(96.2 - (index % 7) * 0.62 - (2.4 if status == 'OOS' else 0), 1),
        'alarm_count': (index * 3) % 5 if status != 'OOS' else 4,
        'status': status,
        'owner': ('A. Kim', 'J. Park', 'M. Chen', 'S. Lee')[index % 4],
        'disposition': ('Released', 'Review', 'Hold')[index % 3] if status != 'Nominal' else 'Released',
        'reviewed': status == 'Nominal' and index % 3 != 0,
        'comment': None if index % 9 == 0 else ('Edge drift observed' if status == 'Watch' else 'Within control band'),
        'trend': tuple(round(49.55 + ((index + step) * 11 % 17) / 100, 3) for step in range(6)),
        'last_updated': timestamp.strftime('%Y-%m-%d %H:%M'),
    }


def engineering_fixture(count: int = 64) -> tuple[dict[str, Any], ...]:
    """Return the deterministic bounded fixture shared by every local lab."""
    if count < 1 or count > 250_000:
        raise ValueError('fixture count must be between 1 and 250000')
    return tuple(_fixture_row(index % 64) | {'record_id': f'R-{index + 1:06d}'} for index in range(count))


def fixture_columns(*, editable: bool = False) -> tuple[TableColumn, ...]:
    """The one governed column contract used by the local reference labs."""
    status_map = {'Nominal': 'success', 'Watch': 'warning', 'OOS': 'danger', 'Hold': 'warning'}
    return (
        TableColumn('record_id', 'Record', ColumnKind.LINK, width=112, pinned=PinPosition.LEFT, priority='high'),
        TableColumn('timestamp', 'Timestamp', ColumnKind.DATETIME, width=148, priority='high'),
        TableColumn('lot_id', 'Lot', width=100, priority='high'),
        TableColumn('wafer_id', 'Wafer', width=80, priority='high'),
        TableColumn('tool_id', 'Tool', width=100),
        TableColumn('chamber_id', 'Chamber', width=84),
        TableColumn('operation', 'Operation', width=112),
        TableColumn('recipe', 'Recipe', width=90),
        TableColumn('measurement_nm', 'Measurement', ColumnKind.FLOAT, width=118, decimals=3, unit='nm', editable=editable, required=True, minimum=0, maximum=100, step=0.001),
        TableColumn('target_nm', 'Target', ColumnKind.FLOAT, width=96, decimals=2, unit='nm', editable=editable, required=True, minimum=0, maximum=100, step=0.01),
        TableColumn('delta_nm', 'Delta', ColumnKind.FLOAT, width=92, decimals=3, unit='nm'),
        TableColumn('yield_pct', 'Yield', ColumnKind.PERCENT, width=82, decimals=1, editable=editable, minimum=0, maximum=100, step=0.1),
        TableColumn('alarm_count', 'Alarms', ColumnKind.INTEGER, width=80, editable=editable, minimum=0, step=1),
        TableColumn('status', 'Status', ColumnKind.STATUS, width=96, status_map=status_map, editable=editable, choices=('Nominal', 'Watch', 'OOS', 'Hold')),
        TableColumn('owner', 'Owner', width=96, editable=editable),
        TableColumn('reviewed', 'Reviewed', ColumnKind.BOOLEAN, width=92, editable=editable, choices=(True, False)),
        TableColumn('comment', 'Comment', width=190, editable=editable),
        TableColumn('trend', 'Trend', ColumnKind.SPARKLINE, width=108),
        TableColumn('last_updated', 'Updated', ColumnKind.DATETIME, width=148),
    )


@dataclass(slots=True)
class DataLabSession:
    rows: list[dict[str, Any]] = field(default_factory=lambda: [dict(row) for row in engineering_fixture()])
    selected_keys: set[str] = field(default_factory=set)
    active_lab: str = 'grid'
    query_revision: int = 0
    imported_snapshot: tuple[dict[str, Any], ...] | None = None

    def reset(self) -> None:
        self.rows = [dict(row) for row in engineering_fixture()]
        self.selected_keys.clear()
        self.query_revision += 1

    def selected_rows(self) -> tuple[dict[str, Any], ...]:
        return tuple(row for row in self.rows if row.get('record_id') in self.selected_keys)

    def filtered(self, *, search: str = '', status: str | None = None, tool: str | None = None, unreviewed: bool = False) -> tuple[dict[str, Any], ...]:
        needle = search.strip().casefold()
        result = []
        for row in self.rows:
            if needle and needle not in ' '.join(str(value) for value in row.values()).casefold():
                continue
            if status and row.get('status') != status:
                continue
            if tool and row.get('tool_id') != tool:
                continue
            if unreviewed and row.get('reviewed'):
                continue
            result.append(dict(row))
        return tuple(result)

    def summary(self, rows: Sequence[Mapping[str, Any]] | None = None) -> dict[str, float | int]:
        values = [float(row['measurement_nm']) for row in (rows if rows is not None else self.rows) if isinstance(row.get('measurement_nm'), (int, float))]
        yields = [float(row['yield_pct']) for row in (rows if rows is not None else self.rows) if isinstance(row.get('yield_pct'), (int, float))]
        oos = sum(row.get('status') == 'OOS' for row in (rows if rows is not None else self.rows))
        return {
            'records': len(rows if rows is not None else self.rows),
            'oos': oos,
            'mean_measurement': round(sum(values) / len(values), 3) if values else 0.0,
            'mean_yield': round(sum(yields) / len(yields), 1) if yields else 0.0,
            'min_measurement': min(values) if values else 0.0,
            'max_measurement': max(values) if values else 0.0,
        }


def query_provider(rows: Sequence[Mapping[str, Any]], query: TableQuery) -> TableResult:
    """Query the same fixture through the canonical bounded query engine."""
    engine = TableQueryEngine(rows, searchable_columns=('record_id', 'lot_id', 'wafer_id', 'tool_id', 'chamber_id', 'status', 'owner'))
    return engine.query(query)


class LogicalEngineeringProvider:
    """Deterministic 250k-record provider that materializes only requested rows."""

    def __init__(self, total: int = 250_000, *, cache_size: int = 12):
        if total < 1 or cache_size < 0:
            raise ValueError('total must be positive and cache_size must be non-negative')
        self.total = total
        self.cache_size = cache_size
        self._index_cache: OrderedDict[tuple[Any, ...], tuple[int, ...]] = OrderedDict()

    def row_at(self, index: int) -> dict[str, Any]:
        if index < 0 or index >= self.total:
            raise IndexError(index)
        row = dict(_fixture_row(index % 64))
        row['record_id'] = f'P-{index + 1:06d}'
        row['lot_id'] = f'LOT-{(index // 4) + 101:06d}'
        row['wafer_id'] = f'W{(index % 25) + 1:02d}'
        return row

    @staticmethod
    def _matches(row: Mapping[str, Any], query: TableQuery) -> bool:
        if query.search:
            needle = query.search.casefold().strip()
            searchable = ('record_id', 'lot_id', 'wafer_id', 'tool_id', 'chamber_id', 'status', 'owner')
            if not any(needle in str(row.get(key, '')).casefold() for key in searchable):
                return False

        def match(expression: FilterExpression) -> bool:
            if isinstance(expression, FilterGroup):
                values = [match(item) for item in expression.filters]
                return any(values) if expression.logic is FilterLogic.OR else all(values)
            value = row.get(expression.key)
            target = expression.value
            if expression.operator is FilterOperator.IN:
                return value in set(target or ())
            if expression.operator is FilterOperator.NOT_IN:
                return value not in set(target or ())
            if expression.operator is FilterOperator.IS_EMPTY:
                return value is None or value == ''
            if expression.operator is FilterOperator.IS_NOT_EMPTY:
                return value is not None and value != ''
            if expression.operator is FilterOperator.CONTAINS:
                return str(target).casefold() in str(value or '').casefold()
            if expression.operator is FilterOperator.EQUALS:
                return value == target
            if expression.operator is FilterOperator.NOT_EQUALS:
                return value != target
            try:
                return {
                    FilterOperator.GT: value > target,
                    FilterOperator.GTE: value >= target,
                    FilterOperator.LT: value < target,
                    FilterOperator.LTE: value <= target,
                    FilterOperator.BETWEEN: target <= value <= expression.value2,
                }.get(expression.operator, True)
            except TypeError:
                return False

        return all(match(item) for item in query.filters)

    def _candidate_indices(self, query: TableQuery) -> tuple[int, ...] | None:
        """Narrow deterministic provider queries before row materialization.

        The reference provider represents 250k records by index.  Common
        categorical filters/searches are resolved from the repeating fixture
        pattern, so a keystroke does not rebuild 250k row dictionaries.  The
        remaining predicate is still applied to generated rows for exact
        contract semantics.
        """
        categories = {
            'tool_id': ('ETCH-021', 'CVD-014', 'LITHO-008', 'CMP-006'),
            'chamber_id': tuple(f'CH-{index}' for index in range(1, 5)),
            'status': ('Nominal', 'Nominal', 'Watch', 'Nominal', 'OOS', 'Hold', 'Nominal', 'Watch'),
            'owner': ('A. Kim', 'J. Park', 'M. Chen', 'S. Lee'),
        }
        candidates: set[int] | None = None

        def bucket(key: str, values: set[Any]) -> set[int] | None:
            if key not in categories:
                return None
            if key == 'tool_id':
                offsets = {index for index, value in enumerate(categories[key]) if value in values}
                return {index for index in range(self.total) if index % 4 in offsets}
            if key == 'chamber_id':
                offsets = {index for index, value in enumerate(categories[key], start=1) if value in values}
                return {index for index in range(self.total) if (index % 4) + 1 in offsets}
            if key == 'owner':
                offsets = {index for index, value in enumerate(categories[key]) if value in values}
                return {index for index in range(self.total) if index % 4 in offsets}
            offsets = {index for index, value in enumerate(categories[key]) if value in values}
            return {index for index in range(self.total) if index % 8 in offsets}

        for expression in query.filters:
            if not isinstance(expression, FilterSpec):
                continue
            if expression.operator is FilterOperator.EQUALS:
                narrowed = bucket(expression.key, {expression.value})
            elif expression.operator is FilterOperator.IN:
                narrowed = bucket(expression.key, set(expression.value or ()))
            else:
                narrowed = None
            if narrowed is not None:
                candidates = narrowed if candidates is None else candidates & narrowed

        needle = query.search.casefold().strip()
        if needle:
            for key, values in categories.items():
                matching = {value for value in values if needle in str(value).casefold()}
                if matching:
                    narrowed = bucket(key, matching)
                    candidates = narrowed if candidates is None else candidates & narrowed
                    break
            if candidates is None and needle.startswith('p-') and needle[2:].isdigit():
                index = int(needle[2:]) - 1
                candidates = {index} if 0 <= index < self.total else set()
            if candidates is None and needle.startswith('lot-') and needle[4:].isdigit():
                start = (int(needle[4:]) - 101) * 4
                candidates = set(range(max(0, start), min(self.total, start + 4)))
            if candidates is None and needle.startswith('w') and needle[1:].isdigit():
                wafer = int(needle[1:])
                candidates = set(range(max(0, wafer - 1), self.total, 25))

        if candidates is None:
            return None
        return tuple(sorted(candidates))

    def _matching_indices(self, query: TableQuery) -> tuple[int, ...]:
        key = (query.search, tuple(repr(item) for item in query.filters), tuple((item.key, item.direction.value) for item in query.sorts))
        if key in self._index_cache:
            self._index_cache.move_to_end(key)
            return self._index_cache[key]
        candidate_indices = self._candidate_indices(query)
        indices = [index for index in (candidate_indices if candidate_indices is not None else range(self.total)) if self._matches(self.row_at(index), query)]
        for spec in reversed(query.sorts):
            indices.sort(key=lambda index: (self.row_at(index).get(spec.key) is None, self.row_at(index).get(spec.key)), reverse=spec.direction is SortDirection.DESC)
        result = tuple(indices)
        if self.cache_size:
            self._index_cache[key] = result
            self._index_cache.move_to_end(key)
            while len(self._index_cache) > self.cache_size:
                self._index_cache.popitem(last=False)
        return result

    def query(self, query: TableQuery) -> TableResult:
        if not query.search and not query.filters and not query.sorts:
            start = (query.page - 1) * query.page_size
            page = tuple(self.row_at(index) for index in range(start, min(start + query.page_size, self.total)))
            return TableResult(page, self.total, query.page, query.page_size)
        indices = self._matching_indices(query)
        start = (query.page - 1) * query.page_size
        page = tuple(self.row_at(index) for index in indices[start:start + query.page_size])
        return TableResult(page, len(indices), query.page, query.page_size)


def _ui_parts():
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import ActionButton, Button, NumberInput, SearchInput, Select, TextArea, TextInput
    from nicegui_base.integrations.nicegui_data_table import (
        DataTable, EditableTable, MasterDetailTable, ServerDataTable, TablePresetSelector,
    )
    from nicegui_base.integrations.nicegui_interactions import DangerConfirmDialog, DetailDrawer, FormDrawer
    from nicegui_base.integrations.nicegui_interactions import Spinner
    from nicegui_base.integrations.nicegui_layout import SegmentedControl
    from nicegui_base.integrations.nicegui_visualization import ChartPanel
    from nicegui_base.visualization import AxisSpec, AxisType, ChartKind, ChartPanelSpec, ChartSize, SeriesSpec, SpecLimits, ThresholdSpec
    return locals()


def _button(parts, label: str, callback=None, *, primary: bool = False, icon: str | None = None, disabled: bool = False):
    cls = parts['ActionButton'] if primary else parts['Button']
    return cls(label, on_click=callback, icon=icon, disabled=disabled).element


def _lab_intro(parts, lab: DataLabSpec) -> None:
    ui = parts['ui']
    with ui.element('header').classes('cui-data-lab-active-head').props(f'data-active-lab="{lab.key}"'):
        with ui.element('div'):
            ui.label(lab.label).classes('cui-workbench-section-title')
            ui.label(lab.purpose).classes('cui-workbench-note')
        with ui.element('div').classes('cui-chip-row'):
            for chip in lab.chips:
                ui.label(chip).classes('cui-workbench-chip')


def _api_disclosure(parts, code: str, contract: str) -> None:
    ui = parts['ui']
    with ui.element('details').classes('cui-data-lab-reference'):
        with ui.element('summary').props('tabindex="0"'):
            ui.label('Use this in an application').classes('cui-workbench-card__meta')
        ui.label(contract).classes('cui-workbench-note')
        ui.code(code, language='python').classes('cui-viewer cui-code-viewer cui-data-lab-code')


def _summary_strip(parts, session: DataLabSession, rows: Sequence[Mapping[str, Any]] | None = None, *, prefix: str = '') -> Callable[[Sequence[Mapping[str, Any]] | None], None]:
    ui = parts['ui']; summary = session.summary(rows)
    value_labels: dict[str, Any] = {}
    with ui.element('div').classes('cui-data-lab-summary').props('aria-label="Table summary"'):
        for label, value in (
            ('Records', f"{summary['records']:,}"), ('Mean measurement', f"{summary['mean_measurement']:.3f} nm"),
            ('Mean yield', f"{summary['mean_yield']:.1f}%"), ('OOS', str(summary['oos'])),
        ):
            with ui.element('div').classes('cui-workbench-kpi'):
                value_labels[label] = ui.label(value).classes('text-h6')
                ui.label(f'{prefix}{label}')

    def update(next_rows: Sequence[Mapping[str, Any]] | None = None) -> None:
        current = session.summary(next_rows)
        for label, value in (
            ('Records', f"{current['records']:,}"), ('Mean measurement', f"{current['mean_measurement']:.3f} nm"),
            ('Mean yield', f"{current['mean_yield']:.1f}%"), ('OOS', str(current['oos'])),
        ):
            value_labels[label].set_text(value)
    return update


def _make_table(parts, session: DataLabSession, *, table_cls, rows: Sequence[Mapping[str, Any]], columns=None, spec=None, **kwargs):
    columns = tuple(columns or fixture_columns())
    return table_cls(rows, columns, spec=spec, **kwargs)


def _render_grid(parts, session: DataLabSession) -> None:
    ui = parts['ui']; DataTable = parts['DataTable']; TablePresetSelector = parts['TablePresetSelector']
    columns = fixture_columns()
    presets = (
        TablePreset('Operations', visible_columns=('record_id', 'timestamp', 'lot_id', 'wafer_id', 'tool_id', 'chamber_id', 'measurement_nm', 'status', 'trend'), pinned_left=('record_id',), density=TableDensity.COMPACT, sorts=(SortSpec('timestamp', SortDirection.DESC),)),
        TablePreset('Quality review', visible_columns=('record_id', 'lot_id', 'tool_id', 'measurement_nm', 'delta_nm', 'yield_pct', 'status', 'owner', 'reviewed', 'comment'), pinned_left=('record_id',), density=TableDensity.COMFORTABLE, filters=(FilterSpec('status', FilterOperator.IN, ('Watch', 'OOS', 'Hold')),)),
        TablePreset('Process engineering', visible_columns=('record_id', 'timestamp', 'tool_id', 'chamber_id', 'recipe', 'measurement_nm', 'target_nm', 'delta_nm', 'trend'), pinned_left=('record_id',), density=TableDensity.DENSE, sorts=(SortSpec('delta_nm', SortDirection.DESC),)),
        TablePreset('Minimal', visible_columns=('record_id', 'lot_id', 'tool_id', 'status', 'measurement_nm', 'yield_pct'), pinned_left=('record_id',), density=TableDensity.COMPACT),
    )
    toolbar_host = ui.element('div').classes('cui-data-lab-toolbar')
    summary_update = _summary_strip(parts, session)
    view_status = ui.label('View: default · 64 records').classes('cui-workbench-note').props('role="status" aria-live="polite" data-grid-view-status')
    def view_changed(snapshot):
        summary_update(snapshot.visible_rows)
        active = []
        if snapshot.search: active.append(f'search “{snapshot.search}”')
        if snapshot.filters: active.append(f'{len(snapshot.filters)} filter(s)')
        if snapshot.sorts: active.append(f'{len(snapshot.sorts)} sort(s)')
        view_status.set_text(f"View: {', '.join(active) if active else 'default'} · {snapshot.displayed_count:,} records")
    table = DataTable(
        session.rows, spec=DataTableSpec(columns, row_key='record_id', title='Lot and wafer monitoring', description='Search, filter, sort and save the view you want to reuse.', selection=SelectionMode.MULTIPLE, density=TableDensity.COMPACT, persist_key='reference-data-grid', striped=True),
        row_actions=(RowAction('inspect', 'Inspect row', icon='info', on_action=lambda row: _open_detail(parts, row)),),
        on_view_changed=view_changed,
    )
    with toolbar_host:
        TablePresetSelector(presets, table=table)
        _button(parts, 'Watch / OOS', lambda: table.set_filters((FilterSpec('status', FilterOperator.IN, ('Watch', 'OOS', 'Hold')),)), icon='filter')
        _button(parts, 'Unreviewed', lambda: table.set_filters((FilterSpec('reviewed', FilterOperator.EQUALS, False),)), icon='filter')
        _button(parts, 'Clear filters', table.clear_filters, icon='close')
        _button(parts, 'Clear sorting', table.clear_sorting, icon='sort')
        _button(parts, 'Reset view', table.reset_layout, icon='refresh')
    with ui.element('div').classes('cui-data-lab-table-frame').props('data-table-lab="grid"'):
        ui.label('The grid owns search, column filters, multi-sort, column visibility, density, CSV export and user-scoped state restoration. Use the Columns and Table density actions in its toolbar.').classes('cui-workbench-note')
        table.element
    _api_disclosure(parts, """from nicegui_base import DataTable, DataTableSpec, TableColumn, SelectionMode

table = DataTable(
    records,
    spec=DataTableSpec(
        columns=(TableColumn('lot_id', 'Lot'), TableColumn('status', 'Status')),
        row_key='record_id',
        selection=SelectionMode.MULTIPLE,
        persist_key='operations-view',
    ),
)""", 'Use DataTableSpec for the row contract; table state is persisted through NiceGUI Base PreferenceService, not browser-local storage.')


def _render_detail_content(parts, row: Mapping[str, Any], related_rows: Sequence[Mapping[str, Any]] = ()) -> None:
    ui = parts['ui']
    with ui.element('div').classes('cui-data-lab-detail-grid'):
        for key in ('record_id', 'lot_id', 'wafer_id', 'tool_id', 'chamber_id', 'recipe', 'measurement_nm', 'target_nm', 'delta_nm', 'yield_pct', 'status', 'owner', 'reviewed', 'comment'):
            with ui.element('div').classes('cui-workbench-property-grid__item'):
                ui.label(key.replace('_', ' ').title()).classes('cui-workbench-card__meta')
                ui.label('—' if row.get(key) is None else str(row.get(key))).classes('cui-workbench-card__title')
    ui.label('Lot → wafer → tool/chamber context').classes('cui-workbench-section-title')
    ui.label(f"{row.get('lot_id')} → {row.get('wafer_id')} → {row.get('tool_id')} / {row.get('chamber_id')}").classes('cui-workbench-note')
    related = [item for item in related_rows if item.get('lot_id') == row.get('lot_id') and item.get('record_id') != row.get('record_id')][:4]
    ui.label('Related records').classes('cui-workbench-section-title')
    if related:
        for item in related:
            ui.label(f"{item.get('record_id')} · {item.get('wafer_id')} · {item.get('status')} · {item.get('measurement_nm')} nm").classes('cui-workbench-note')
    else:
        ui.label('No additional records in the active bounded page.').classes('cui-workbench-note')
    trend = tuple(float(value) for value in row.get('trend', ()) if isinstance(value, (int, float)) and math.isfinite(float(value)))
    if len(trend) >= 2:
        spec = parts['ChartPanelSpec']('Record measurement history', 'Bounded trend values for the selected record.', kind=parts['ChartKind'].LINE, size=parts['ChartSize'].COMPACT, x_axis=parts['AxisSpec']('Sample', parts['AxisType'].CATEGORY, categories=tuple(str(index + 1) for index in range(len(trend)))), y_axis=parts['AxisSpec']('Measurement', parts['AxisType'].VALUE, unit='nm'))
        parts['ChartPanel']((parts['SeriesSpec']('trend', 'Measurement', trend, kind=parts['ChartKind'].LINE),), spec=spec)
    ui.label('Audit trail · sample reference').classes('cui-workbench-section-title')
    with ui.element('div').classes('cui-data-lab-audit'):
        for field, old, new in (('Created', '—', row.get('timestamp')), ('Owner', 'Unassigned', row.get('owner')), ('Status', 'Nominal', row.get('status'))):
            ui.label(f'{field} · {old} → {new} · Member · {row.get("last_updated")}').classes('cui-workbench-note')


def _open_detail(parts, row: Mapping[str, Any], related_rows: Sequence[Mapping[str, Any]] = ()) -> None:
    with parts['DetailDrawer'](f"{row.get('record_id', 'Record')} detail", subtitle='Governed engineering record'):
        _render_detail_content(parts, row, related_rows)


def _render_actions(parts, session: DataLabSession) -> None:
    ui = parts['ui']; DataTable = parts['DataTable']; DangerConfirmDialog = parts['DangerConfirmDialog']
    status = ui.label('Select records to reveal the contextual bulk actions.').classes('cui-workbench-note').props('role="status" aria-live="polite" data-actions-status')

    async def selected(rows: Sequence[Mapping[str, Any]]) -> None:
        session.selected_keys = {str(row.get('record_id')) for row in rows}
        status.set_text(f'{len(rows)} selected · compare requires two or more records')

    async def update_rows(changes: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> None:
        keys = {row.get('record_id') for row in rows}
        changed_rows = []
        for row in session.rows:
            if row.get('record_id') in keys:
                row.update(changes)
                changed_rows.append(dict(row))
        if changed_rows:
            await table.update_rows_by_key(changed_rows)

    async def hold(rows):
        await update_rows({'status': 'Hold', 'disposition': 'Hold'}, rows)
        status.set_text(f'Held {len(rows)} record(s). The fixture state changed; it was not a toast-only action.')

    async def review(rows):
        await update_rows({'reviewed': True}, rows)
        status.set_text(f'Marked {len(rows)} record(s) reviewed.')

    async def compare(rows):
        if len(rows) < 2:
            status.set_text('Select at least two records before Compare selected.')
            return
        with parts['ui'].dialog().props('maximized transition-show=fade transition-hide=fade') as dialog:
            with ui.element('section').classes('cui-dialog cui-overlay-surface cui-overlay-surface--dialog'):
                ui.label('Compare selected records').classes('cui-dialog__title')
                for row in rows[:4]:
                    ui.label(f"{row.get('record_id')} · {row.get('tool_id')} · {row.get('measurement_nm')} nm · {row.get('yield_pct')}%").classes('cui-workbench-note')
                _button(parts, 'Close', dialog.close)
        dialog.open()

    async def delete(rows):
        if not rows:
            return
        async def confirm():
            keys = {row.get('record_id') for row in rows}
            session.rows[:] = [row for row in session.rows if row.get('record_id') not in keys]
            session.selected_keys.difference_update(keys)
            await table.remove_rows_by_key(tuple(keys))
            status.set_text(f'Deleted {len(rows)} record(s) from the local fixture.')
        danger = DangerConfirmDialog('Delete selected records', description='This removes only local reference rows and cannot affect a provider.', on_confirm=confirm)
        danger.open()

    summary_update = _summary_strip(parts, session)
    table = DataTable(
        session.rows,
        spec=DataTableSpec(fixture_columns(), row_key='record_id', title='Disposition queue', selection=SelectionMode.MULTIPLE, persist_key='reference-data-actions', striped=True),
        bulk_actions=(
            BulkAction('hold', 'Hold selected', icon='pause', intent='warning', on_action=hold),
            BulkAction('review', 'Mark reviewed', icon='check', on_action=review),
            BulkAction('compare', 'Compare selected', icon='split', on_action=compare),
            BulkAction('delete', 'Delete selected', icon='delete', intent='danger', on_action=delete),
        ), on_select=selected, on_view_changed=lambda snapshot: summary_update(snapshot.visible_rows),
        row_actions=(RowAction('inspect', 'View details', icon='info', on_action=lambda row: _open_detail(parts, row)),),
    )
    with ui.element('div').classes('cui-data-lab-table-frame').props('data-table-lab="actions"'):
        ui.label('Select a row or use the header checkbox. Right-click also exposes the same row actions, while View details remains available through the keyboard-accessible action cell.').classes('cui-workbench-note')
        table.element
    _api_disclosure(parts, """from nicegui_base import BulkAction, DataTable, SelectionMode

DataTable(records, selection=SelectionMode.MULTIPLE,
    bulk_actions=(BulkAction('review', 'Mark reviewed', on_action=mark_reviewed),),
    on_select=handle_selection)""", 'BulkAction and RowAction callbacks receive normalized records, never raw AG Grid event payloads.')


def _render_edit(parts, session: DataLabSession) -> None:
    ui = parts['ui']; EditableTable = parts['EditableTable']; FormDrawer = parts['FormDrawer']
    status = ui.label('Edit a typed cell or use Add record. Invalid measurement values roll back with focus restored.').classes('cui-workbench-note').props('role="status" aria-live="polite" data-edit-status')
    rows = [dict(row) for row in session.rows[:32]]
    columns = fixture_columns(editable=True)
    failure = {'next': False}

    def validate(row, key, value):
        if key in {'measurement_nm', 'target_nm'}:
            try:
                number = float(value)
            except (TypeError, ValueError):
                return 'Enter a finite numeric measurement.'
            if not math.isfinite(number) or not 0 < number < 100:
                return 'Measurement must be finite and between 0 and 100 nm.'
        if key == 'status' and value not in {'Nominal', 'Watch', 'OOS', 'Hold'}:
            return 'Choose a governed status.'
        return None

    async def save(row, key, value):
        error = validate(row, key, value)
        if error:
            raise ValueError(error)
        if failure['next']:
            failure['next'] = False
            raise RuntimeError('Deterministic save failure: the committed value was restored.')
        for current in session.rows:
            if current.get('record_id') == row.get('record_id'):
                current[key] = value
                if key == 'measurement_nm':
                    current['delta_nm'] = round(float(value) - float(current.get('target_nm') or 0), 3)
        status.set_text(f'Saved {row.get("record_id")} · {key}.')

    table = EditableTable(rows, columns, spec=EditableTableSpec(tuple(columns), row_key='record_id', title='Engineering disposition', selection=SelectionMode.SINGLE, save_mode='cell', commit_mode=EditCommitMode.CONFIRMED, persist_key='reference-data-edit'), validate_edit=validate, save_edit=save, row_actions=(RowAction('inspect', 'Inspect row', icon='info', on_action=lambda row: _open_detail(parts, row)),))

    def add_record():
        drawer = FormDrawer('Add engineering record', subtitle='Typed record form · local reference fixture')
        with drawer:
            record = {column.key: None for column in columns}
            record.update({'record_id': f'R-NEW-{len(session.rows) + 1:03d}', 'lot_id': 'LOT-NEW', 'wafer_id': 'W01', 'tool_id': 'ETCH-021', 'chamber_id': 'CH-1', 'measurement_nm': 50.0, 'target_nm': 50.0, 'yield_pct': 98.0, 'status': 'Nominal', 'owner': 'A. Kim', 'reviewed': False, 'comment': 'Added from reference form'})
            record_id = parts['TextInput']('Record ID', value=record['record_id'], required=True)
            measurement = parts['NumberInput']('Measurement', value=50.0, minimum=0.0, maximum=100.0, step=0.001, unit='nm', required=True)
            status_input = parts['Select']('Status', {'Nominal': 'Nominal', 'Watch': 'Watch', 'OOS': 'OOS', 'Hold': 'Hold'}, value='Nominal', clearable=False)
            async def commit():
                record['record_id'] = str(record_id.element.value or '').strip()
                try:
                    record['measurement_nm'] = float(measurement.element.value)
                except (TypeError, ValueError):
                    status.set_text('Add rejected: Measurement must be a finite number between 0 and 100 nm.')
                    return
                record['delta_nm'] = round(record['measurement_nm'] - 50.0, 3)
                record['status'] = str(status_input.element.value or 'Nominal')
                if not record['record_id']:
                    status.set_text('Add rejected: Record ID and a valid measurement are required.')
                    return
                if any(row.get('record_id') == record['record_id'] for row in session.rows):
                    status.set_text(f'Add rejected: Record ID {record["record_id"]} already exists.')
                    return
                if validate(record, 'measurement_nm', record['measurement_nm']):
                    status.set_text('Add rejected: Measurement must be finite and between 0 and 100 nm.')
                    return
                session.rows.append(record)
                await table.apply_row_transaction(add=(record,))
                status.set_text(f'Added {record["record_id"]}.')
                drawer.close()
            _button(parts, 'Add record', commit, primary=True, icon='add')
        drawer.open()

    with ui.element('div').classes('cui-data-lab-toolbar'):
        _button(parts, 'Add record', add_record, primary=True, icon='add')
        _button(parts, 'Force next save failure', lambda: (failure.__setitem__('next', True), status.set_text('Next cell save will fail and restore the committed value.')), icon='warning')
    with ui.element('div').classes('cui-data-lab-table-frame').props('data-table-lab="edit"'):
        table.element
    _api_disclosure(parts, """from nicegui_base import EditableTable, EditableTableSpec

EditableTable(records, columns, spec=EditableTableSpec(
    columns, save_mode='cell', commit_mode='confirmed'),
    validate_edit=validate_edit, save_edit=save_edit)""", 'Use typed TableColumn metadata plus validate_edit/save_edit for safe edits. The framework owns pending, rollback and focus restoration.')


def _chart(parts, rows: Sequence[Mapping[str, Any]], *, kind: str = 'trend'):
    ChartPanel = parts['ChartPanel']; AxisSpec = parts['AxisSpec']; AxisType = parts['AxisType']; ChartKind = parts['ChartKind']; ChartPanelSpec = parts['ChartPanelSpec']; ChartSize = parts['ChartSize']; SeriesSpec = parts['SeriesSpec']; SpecLimits = parts['SpecLimits']
    labels = [str(row.get('record_id')) for row in rows]
    if kind == 'distribution':
        bins = ('49.2–49.5', '49.5–49.8', '49.8–50.1', '50.1–50.4')
        values = [sum(49.2 + bucket * .3 <= float(row.get('measurement_nm') or 0) < 49.2 + (bucket + 1) * .3 for row in rows) for bucket in range(4)]
        spec = ChartPanelSpec('Measurement distribution', 'Filtered records by measurement band.', kind=ChartKind.BAR, size=ChartSize.STANDARD, x_axis=AxisSpec('Measurement band', AxisType.CATEGORY, categories=bins), y_axis=AxisSpec('Records', AxisType.VALUE))
        series = (SeriesSpec('distribution', 'Records', values, kind=ChartKind.BAR),)
        return ChartPanel(series, spec=spec)
    if kind == 'scatter':
        data = [{'x': float(row.get('measurement_nm') or 0), 'y': float(row.get('yield_pct') or 0)} for row in rows]
        spec = ChartPanelSpec('Measurement vs yield', 'Selected and filtered records stay in the same engineering population.', kind=ChartKind.SCATTER, size=ChartSize.STANDARD, x_axis=AxisSpec('Measurement', AxisType.VALUE, unit='nm'), y_axis=AxisSpec('Yield', AxisType.VALUE, unit='%'))
        return ChartPanel((SeriesSpec('records', 'Records', data, kind=ChartKind.SCATTER, x_key='x', y_key='y'),), spec=spec)
    if kind == 'spc':
        values = [float(row.get('measurement_nm') or 0) for row in rows]
        center = sum(values) / len(values) if values else 50.0
        spread = max(.12, (max(values) - min(values)) * .75) if values else .3
        spec = ChartPanelSpec('SPC measurement trend', 'Mean and control limits are reference fixture semantics, not a production conclusion.', kind=ChartKind.CONTROL, size=ChartSize.STANDARD, x_axis=AxisSpec('Record', AxisType.CATEGORY, categories=labels), y_axis=AxisSpec('Measurement', AxisType.VALUE, unit='nm'))
        return ChartPanel((SeriesSpec('measurement', 'Measurement', values, kind=ChartKind.CONTROL, semantic_color='accent'),), spec=spec, thresholds=(parts['ThresholdSpec'](center, 'Center'), parts['ThresholdSpec'](center + spread, 'UCL'), parts['ThresholdSpec'](center - spread, 'LCL')))
    if kind == 'wafer':
        points = [((index % 7) - 3, (index // 7) - 3, float(row.get('measurement_nm') or 0)) for index, row in enumerate(rows[:49])]
        spec = ChartPanelSpec('Wafer measurement map', 'The same filtered engineering records mapped to bounded wafer coordinates.', kind=ChartKind.WAFER, size=ChartSize.STANDARD, x_axis=AxisSpec('Die X', AxisType.VALUE), y_axis=AxisSpec('Die Y', AxisType.VALUE))
        return ChartPanel((SeriesSpec('wafer', 'Measurement', points, kind=ChartKind.WAFER),), spec=spec)
    values = [float(row.get('measurement_nm') or 0) for row in rows]
    spec = ChartPanelSpec('Measurement trend', 'Filtering the table changes this governed series.', kind=ChartKind.LINE, size=ChartSize.STANDARD, x_axis=AxisSpec('Record', AxisType.CATEGORY, categories=labels), y_axis=AxisSpec('Measurement', AxisType.VALUE, unit='nm'))
    return ChartPanel((SeriesSpec('measurement', 'Measurement', values, kind=ChartKind.LINE, x_key=None, y_key=None),), spec=spec, spec_limits=SpecLimits(lower=49.4, upper=50.6, target=50.0))


def _render_visualize(parts, session: DataLabSession) -> None:
    ui = parts['ui']; SearchInput = parts['SearchInput']; SegmentedControl = parts['SegmentedControl']
    state: dict[str, Any] = {'search': '', 'chart': 'trend', 'selected': set(), 'population': tuple(session.rows)}
    summary_host = None
    chart_host = None
    status = None

    def set_summary(rows: Sequence[Mapping[str, Any]]) -> None:
        summary_host.clear()
        with summary_host:
            _summary_strip(parts, session, rows, prefix='Filtered ')

    def set_chart(rows: Sequence[Mapping[str, Any]]) -> None:
        chart_host.clear()
        with chart_host:
            chart_rows = tuple(row for row in rows if not state['selected'] or row.get('record_id') in state['selected'])
            ui.label(f"Chart uses {'selected' if state['selected'] else 'filtered'} population · {len(chart_rows)} records").classes('cui-workbench-section-title')
            _chart(parts, chart_rows, kind=state['chart'])
        status.set_text(f"Filtered records: {len(rows)} · Selected records: {len(state['selected'])} · Chart uses {'selected' if state['selected'] else 'filtered'} population")

    async def selected(chosen: Sequence[Mapping[str, Any]]) -> None:
        state['selected'] = {row.get('record_id') for row in chosen}
        set_summary(state['population'])
        set_chart(state['population'])

    def view_changed(snapshot) -> None:
        state['population'] = tuple(snapshot.visible_rows)
        state['selected'].intersection_update(row.get('record_id') for row in state['population'])
        set_summary(state['population'])
        set_chart(state['population'])

    initial_rows = session.filtered()
    with ui.element('div').classes('cui-data-lab-toolbar'):
        async def search_changed(event) -> None:
            state['search'] = str(getattr(event, 'value', '') or '')
            state['selected'].clear()
            await table.replace_rows(session.filtered(search=state['search']))
            state['population'] = tuple(table.rows)
            set_summary(state['population']); set_chart(state['population'])
        SearchInput('Search linked records', placeholder='Lot, tool, chamber, status…', debounce_ms=180, on_change=search_changed)
        with ui.element('div').classes('cui-data-lab-chart-switcher'):
            async def chart_changed(event) -> None:
                state['chart'] = str(getattr(event, 'value', 'trend') or 'trend')
                set_chart(state['population'])
            SegmentedControl({'trend': 'Trend', 'distribution': 'Distribution', 'scatter': 'Scatter', 'spc': 'SPC', 'wafer': 'Wafer'}, value='trend', on_change=chart_changed)
    with ui.element('div').classes('cui-data-lab-visual-host'):
        summary_host = ui.element('div').classes('cui-data-lab-linked-summary')
        with ui.element('div').classes('cui-data-lab-visual-grid'):
            with ui.element('section').classes('cui-data-lab-visual-table'):
                ui.label('Linked table').classes('cui-workbench-section-title')
                table = parts['DataTable'](initial_rows, spec=DataTableSpec(fixture_columns(), row_key='record_id', selection=SelectionMode.MULTIPLE, title='Filtered engineering records', persist_state=False, striped=True), on_select=selected, on_view_changed=view_changed)
                table.element
            with ui.element('section').classes('cui-data-lab-visual-chart'):
                ui.label('Linked analytical view').classes('cui-workbench-section-title')
                chart_host = ui.element('div').classes('cui-data-lab-linked-chart')
        status = ui.label('').classes('cui-workbench-note').props('role="status" aria-live="polite" data-visualize-population')
    set_summary(initial_rows)
    set_chart(initial_rows)
    _api_disclosure(parts, """from nicegui_base import AnalysisContext, DataSourceTable, ChartPanel

# Bind a DataSourceTable and analytical panel to one AnalysisContext.
context = AnalysisContext(source_key='engineering-reference')
table = DataSourceTable(source, schema=schema, context=context)
""", 'Application-scale linked filtering belongs to AnalysisContext/DataSourceTable and the registered chart wrappers. This bounded example proves table → chart linkage; reverse chart selection is omitted because ChartPanel has no normalized point-selection callback.')


def _render_import(parts, session: DataLabSession) -> None:
    ui = parts['ui']; TextArea = parts['TextArea']; SegmentedControl = parts['SegmentedControl']; DataDockModel = __import__('nicegui_base.workbench.data_dock', fromlist=['DataDockModel']).DataDockModel
    from nicegui_base.workbench.capability_studio import render_data_dock
    model = DataDockModel(session.rows, sample_name='Shared engineering fixture')
    ui.label('Current data, paste and upload remain one DataDock contract; a parse failure never replaces the existing rows.').classes('cui-workbench-note')
    render_data_dock(model, on_change=lambda _model: _import_changed(session, model))
    _api_disclosure(parts, """from nicegui_base.workbench.data_dock import DataDockModel

dock = DataDockModel(records)
result = dock.load_text(text, filename='incoming.tsv')
if result.ok:
    rows = dock.rows
""", 'DataDock owns format detection, schema inference, quality issues, hardened import limits and rectangular paste.')


def _import_changed(session: DataLabSession, model: Any) -> None:
    session.rows = [dict(row) for row in model.rows]
    session.imported_snapshot = tuple(dict(row) for row in model.rows)


def _render_detail(parts, session: DataLabSession) -> None:
    ui = parts['ui']; MasterDetailTable = parts['MasterDetailTable']
    columns = tuple(column for column in fixture_columns() if column.key in {'record_id', 'lot_id', 'wafer_id', 'tool_id', 'chamber_id', 'measurement_nm', 'status', 'yield_pct', 'owner'})
    table = MasterDetailTable(session.rows, columns, title='Lot / wafer explorer', description='Double-click a record or use the row action to open the governed detail drawer.', row_key='record_id', selection=SelectionMode.SINGLE, spec=DataTableSpec(columns, row_key='record_id', selection=SelectionMode.SINGLE, persist_key='reference-data-detail'), row_actions=(RowAction('inspect', 'View details', icon='info', on_action=lambda row: _open_detail(parts, row, session.rows)),), detail_renderer=lambda row: _render_detail_content(parts, row, session.rows))
    with ui.element('div').classes('cui-data-lab-table-frame').props('data-table-lab="detail"'):
        table.element
    _api_disclosure(parts, """from nicegui_base import MasterDetailTable

MasterDetailTable(records, columns, row_key='record_id',
    detail_renderer=render_record_detail)""", 'MasterDetailTable owns row identity, drill-down and focus-safe DetailDrawer behavior.')


def _render_server(parts, session: DataLabSession) -> None:
    ui = parts['ui']; ServerDataTable = parts['ServerDataTable']; Select = parts['Select']; provider = LogicalEngineeringProvider()
    state: dict[str, Any] = {'mode': 'normal', 'fail_next': False, 'fail_first': False, 'first_attempt': False, 'last_success': None}
    footer = ui.label('Provider ready · logical universe 250,000 records · bounded page fetches only.').classes('cui-workbench-note').props('role="status" aria-live="polite" data-server-status')
    freshness = ui.label('Not loaded yet').classes('cui-workbench-note').props('data-server-freshness')
    async def fetch(query: TableQuery):
        if state['mode'] == 'slow':
            await asyncio.sleep(.25)
        if state['fail_first'] and not state['first_attempt']:
            state['first_attempt'] = True
            raise RuntimeError('Deterministic initial-load failure — choose Retry.')
        if state['fail_next']:
            state['fail_next'] = False
            raise RuntimeError('Deterministic provider failure — choose Retry.')
        result = provider.query(query)
        state['last_success'] = time.monotonic()
        freshness.set_text('Updated 0s ago')
        footer.set_text(f'Provider ready · {result.total:,} matching records · page {result.page} of {result.page_count} · bounded fetch')
        return result
    async def provider_error(error: BaseException) -> None:
        footer.set_text(f'Provider request failed · {error} Retry is available.')
    table = ServerDataTable(tuple(column for column in fixture_columns() if column.key not in {'trend', 'comment'}), fetch=fetch, on_error=provider_error, spec=ServerDataTableSpec(tuple(column for column in fixture_columns() if column.key not in {'trend', 'comment'}), row_key='record_id', title='Provider-backed event history', description='Only the requested page enters the browser.', page_size=10, page_size_options=(10, 25, 50), persist_key='reference-data-server', cache_pages=2, cancel_stale_requests=True, retry_attempts=1, stale_after_seconds=30), selection=SelectionMode.MULTIPLE)
    with ui.element('div').classes('cui-data-lab-toolbar'):
        async def normal():
            state['mode'] = 'normal'; footer.set_text('Normal response enabled.'); await table.refresh(force=True)
        async def slow():
            state['mode'] = 'slow'; footer.set_text('Slow response enabled · latest request wins.'); await table.refresh(force=True)
        def fail_next():
            state['fail_next'] = True; footer.set_text('The next actual provider request will fail and retain stale rows.')
        async def retry():
            try:
                await table.refresh(force=True)
                footer.set_text('Retry succeeded · stale state cleared.')
            except RuntimeError:
                footer.set_text('Provider request failed · existing rows remain stale. Retry is available.')
        async def first_load_error():
            state['fail_first'] = True; state['first_attempt'] = False
            await table.replace_rows(())
            try:
                await table.refresh(force=True)
            except RuntimeError:
                footer.set_text('Initial load failed · no cached rows. Retry is available.')
        async def page_size_changed(event):
            try:
                await table.set_page_size(int(getattr(event, 'value', 10)))
            except (TypeError, ValueError):
                footer.set_text('Page size must be 10, 25, or 50.')
        _button(parts, 'Normal response', normal)
        _button(parts, 'Slow response', slow, icon='clock')
        _button(parts, 'Fail next request', fail_next, icon='warning')
        _button(parts, 'Initial-load error', first_load_error, icon='error')
        Select('Page size', {10: '10', 25: '25', 50: '50'}, value=10, clearable=False, on_change=page_size_changed)
        _button(parts, 'Retry', retry, primary=True, icon='refresh')
    with ui.element('div').classes('cui-data-lab-table-frame').props('data-table-lab="server"'):
        table.element
    ui.label('Freshness is measured from the last successful provider response. Manual retry is deliberate; automatic retry is disabled for this read reference. Full-query export requires a provider export callback and is not represented as a browser CSV.').classes('cui-workbench-note')
    _api_disclosure(parts, """from nicegui_base import ServerDataTable, ServerDataTableSpec, TableResult

table = ServerDataTable(columns, fetch=fetch,
    spec=ServerDataTableSpec(columns, page_size=50,
        cancel_stale_requests=True, cache_pages=2))""", 'ServerDataTable owns page/query state, latest-request-wins cancellation, bounded cache, timeout/retry and stale status.')


def _render_states(parts, session: DataLabSession) -> None:
    ui = parts['ui']; SegmentedControl = parts['SegmentedControl']; DataTable = parts['DataTable']; Spinner = parts['Spinner']
    state = {'value': 'populated'}
    host = ui.element('div').classes('cui-data-lab-state-host')
    choices = {'populated': 'Populated', 'empty': 'Empty', 'no-results': 'No results', 'loading': 'Loading', 'refreshing': 'Refreshing', 'error': 'Error', 'stale': 'Stale', 'read-only': 'Read only', 'restricted': 'Restricted'}

    def render():
        host.clear()
        with host:
            value = state['value']
            if value == 'loading':
                with ui.element('section').classes('cui-table-loading').props('data-table-state="loading" role="status" aria-live="polite"'):
                    ui.label('Loading provider records…').classes('cui-workbench-section-title')
                    for _ in range(5):
                        ui.element('div').classes('cui-table-loading__row').props('aria-hidden="true"')
                return
            if value == 'empty':
                table = DataTable((), spec=DataTableSpec(tuple(column for column in fixture_columns() if column.key in {'record_id', 'tool_id', 'measurement_nm', 'status', 'owner'}), row_key='record_id', title='State specimen', selection=SelectionMode.MULTIPLE, persist_state=False, empty_message='No records are available yet. Import a dataset or connect a provider to begin.'))
                table.element
                return
            if value == 'no-results':
                table = DataTable((), spec=DataTableSpec(tuple(column for column in fixture_columns() if column.key in {'record_id', 'tool_id', 'measurement_nm', 'status', 'owner'}), row_key='record_id', title='State specimen', selection=SelectionMode.MULTIPLE, persist_state=False, empty_message='No results for the current filter.'))
                table.element
                _button(parts, 'Clear filters', lambda: state.update(value='populated') or render(), primary=True, icon='filter-clear')
                return
            if value == 'error':
                with ui.element('section').classes('cui-table-error').props('data-table-state="error" role="alert"'):
                    ui.label('Unable to load records. No stale data is being shown.').classes('cui-workbench-section-title')
                    ui.label('The governed provider can retry without remounting the surrounding reference page.').classes('cui-workbench-note')
                    _button(parts, 'Retry', lambda: state.update(value='populated') or render(), primary=True, icon='refresh')
                return
            rows = session.rows[:10]
            if value == 'stale':
                ui.label('Stale data · last successful refresh 14 s ago · Retry available').classes('cui-workbench-note').props('data-table-state="stale" role="status"')
            if value == 'refreshing':
                with ui.element('div').classes('cui-table-refreshing').props('data-table-state="refreshing" role="status"'):
                    Spinner()
                    ui.label('Refreshing in place · existing rows and selection are retained')
            read_only = value in {'read-only', 'restricted'}
            restricted = value == 'restricted'
            table = DataTable(rows, spec=DataTableSpec(tuple(column for column in fixture_columns() if column.key in {'record_id', 'tool_id', 'measurement_nm', 'status', 'owner'}), row_key='record_id', title='State specimen', selection=SelectionMode.MULTIPLE, persist_state=False, export_csv=not restricted, export_enabled=not restricted), bulk_actions=() if restricted else (), row_actions=() if read_only else (RowAction('inspect', 'View details', icon='info', on_action=lambda row: _open_detail(parts, row)),))
            if value == 'restricted':
                ui.label('Restricted policy: export, delete, owner assignment and destructive actions are unavailable for this role.').classes('cui-workbench-note').props('data-restricted-policy')
            table.element
    SegmentedControl(choices, value='populated', on_change=lambda event: (state.__setitem__('value', str(getattr(event, 'value', 'populated'))), render()))
    render()
    _api_disclosure(parts, """from nicegui_base import DataTable, EmptyState, ErrorState, PermissionDeniedState

# Keep the table mounted for refreshing/stale states; change only the state panel.
""", 'State views are part of the table contract: empty, error, stale, read-only and restricted are explicit and never inferred from color alone.')


def render_data_table_lab(*, initial_lab: str = 'grid') -> DataLabSession:
    """Render `/workbench/data` with exactly one active heavy specimen."""
    parts = _ui_parts(); ui = parts['ui']
    session = DataLabSession(active_lab=initial_lab if initial_lab in LAB_KEYS else 'grid')
    lab_map = {lab.key: lab for lab in LABS}
    with ui.element('section').classes('cui-data-lab').props('data-data-table-lab'):
        with ui.element('div').classes('cui-data-lab-intro'):
            ui.label('Production table lab').classes('cui-workbench-title')
            ui.label('The governed production reference for tables, record management, data exploration and provider-scale grids. One active lab keeps the page fast; every lab reuses the same semiconductor data contract.').classes('cui-workbench-subtitle')
        switch_host = ui.element('div').classes('cui-data-lab-switcher').props('aria-label="Data table labs"')
        active_host = ui.element('div').classes('cui-data-lab-active')

        def render_active() -> None:
            active_host.clear()
            lab = lab_map[session.active_lab]
            with active_host:
                _lab_intro(parts, lab)
                renderer = {
                    'grid': _render_grid, 'actions': _render_actions, 'edit': _render_edit,
                    'visualize': _render_visualize, 'import': _render_import, 'detail': _render_detail,
                    'server': _render_server, 'states': _render_states,
                }[session.active_lab]
                renderer(parts, session)

        async def switch(event=None) -> None:
            value = str(getattr(event, 'value', event or 'grid'))
            if value not in LAB_KEYS or value == session.active_lab:
                return
            session.active_lab = value
            await segmented.set_value(value)
            # NiceGUI serializes parent deletion and child creation as separate
            # client updates. Yield after clearing the active host so AG Grid
            # components from the previous lab cannot consume the replacement
            # update during the same websocket turn.
            active_host.clear()
            await asyncio.sleep(0)
            render_active()

        with switch_host:
            segmented = parts['SegmentedControl']({lab.key: lab.label for lab in LABS}, value=session.active_lab, on_change=switch)
        render_active()
    return session


__all__ = ['LAB_KEYS', 'LABS', 'DataLabSpec', 'DataLabSession', 'LogicalEngineeringProvider', 'engineering_fixture', 'fixture_columns', 'query_provider', 'render_data_table_lab']
