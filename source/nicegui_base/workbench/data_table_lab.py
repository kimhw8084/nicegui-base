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


@dataclass(frozen=True, slots=True)
class VisualMetricSpec:
    key: str
    label: str
    unit: str
    valid_roles: tuple[str, ...]
    target: float | None = None
    spec_lower: float | None = None
    spec_upper: float | None = None


VISUAL_METRICS: dict[str, VisualMetricSpec] = {
    'measurement_nm': VisualMetricSpec('measurement_nm', 'Measurement', 'nm', ('trend', 'distribution', 'scatter', 'spc', 'wafer'), 50.0, 49.4, 50.6),
    'yield_pct': VisualMetricSpec('yield_pct', 'Yield', '%', ('trend', 'distribution', 'scatter', 'spc'), 95.0, 90.0, 100.0),
    'delta_nm': VisualMetricSpec('delta_nm', 'Delta', 'nm', ('trend', 'distribution', 'scatter', 'spc', 'wafer'), 0.0, -0.6, 0.6),
    'target_nm': VisualMetricSpec('target_nm', 'Target', 'nm', ('trend', 'distribution', 'scatter', 'spc', 'wafer'), 50.0, 49.4, 50.6),
}


def visual_metric(key: str) -> VisualMetricSpec:
    try:
        return VISUAL_METRICS[key]
    except KeyError as exc:
        raise ValueError(f'No governed visual metric exists for {key!r}.') from exc


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
        self._pattern_rows = tuple(_fixture_row(index) for index in range(64))
        self._index_cache: OrderedDict[tuple[Any, ...], tuple[int, ...]] = OrderedDict()

    def row_at(self, index: int) -> dict[str, Any]:
        if index < 0 or index >= self.total:
            raise IndexError(index)
        row = dict(self._pattern_rows[index % 64])
        row['record_id'] = f'P-{index + 1:06d}'
        row['lot_id'] = f'LOT-{(index // 4) + 101:06d}'
        row['wafer_id'] = f'W{(index % 25) + 1:02d}'
        return row

    @staticmethod
    def _matches_values(value_for: Callable[[str], Any], query: TableQuery) -> bool:
        if query.search:
            needle = query.search.casefold().strip()
            searchable = ('record_id', 'lot_id', 'wafer_id', 'tool_id', 'chamber_id', 'status', 'owner')
            if not any(needle in str(value_for(key) or '').casefold() for key in searchable):
                return False

        def match(expression: FilterExpression) -> bool:
            if isinstance(expression, FilterGroup):
                values = [match(item) for item in expression.filters]
                return any(values) if expression.logic is FilterLogic.OR else all(values)
            value = value_for(expression.key)
            target = expression.value
            operator = expression.operator
            if operator is FilterOperator.IN:
                return value in set(target or ())
            if operator is FilterOperator.NOT_IN:
                return value not in set(target or ())
            if operator is FilterOperator.IS_EMPTY:
                return value is None or value == ''
            if operator is FilterOperator.IS_NOT_EMPTY:
                return value is not None and value != ''
            if operator is FilterOperator.CONTAINS:
                return str(target).casefold() in str(value or '').casefold()
            if operator is FilterOperator.NOT_CONTAINS:
                return str(target).casefold() not in str(value or '').casefold()
            if operator is FilterOperator.STARTS_WITH:
                return str(value or '').casefold().startswith(str(target).casefold())
            if operator is FilterOperator.ENDS_WITH:
                return str(value or '').casefold().endswith(str(target).casefold())
            if operator is FilterOperator.EQUALS:
                return value == target
            if operator is FilterOperator.NOT_EQUALS:
                return value != target
            try:
                return {
                    FilterOperator.GT: value is not None and value > target,
                    FilterOperator.GTE: value is not None and value >= target,
                    FilterOperator.LT: value is not None and value < target,
                    FilterOperator.LTE: value is not None and value <= target,
                    FilterOperator.BETWEEN: value is not None and target <= value <= expression.value2,
                }[operator]
            except KeyError:
                raise ValueError(f'Unsupported filter operator: {operator!r}') from None
            except TypeError:
                return False

        return all(match(item) for item in query.filters)

    @classmethod
    def _matches(cls, row: Mapping[str, Any], query: TableQuery) -> bool:
        return cls._matches_values(row.get, query)

    def _matches_index(self, index: int, query: TableQuery) -> bool:
        pattern = self._pattern_rows[index % 64]

        def value_for(key: str) -> Any:
            if key == 'record_id':
                return f'P-{index + 1:06d}'
            if key == 'lot_id':
                return f'LOT-{(index // 4) + 101:06d}'
            if key == 'wafer_id':
                return f'W{(index % 25) + 1:02d}'
            return pattern.get(key)

        return self._matches_values(value_for, query)

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
            search_candidates: set[int] = set()
            for key, values in categories.items():
                matching = {value for value in values if needle in str(value).casefold()}
                if matching:
                    narrowed = bucket(key, matching)
                    if narrowed is not None:
                        search_candidates.update(narrowed)
            # Identifier/lot/wafer search is part of the same OR contract as
            # categorical search.  This scans only deterministic index strings;
            # it never materializes provider row dictionaries.
            for index in range(self.total):
                if (
                    needle in f'p-{index + 1:06d}'.casefold()
                    or needle in f'lot-{(index // 4) + 101:06d}'.casefold()
                    or needle in f'w{(index % 25) + 1:02d}'.casefold()
                ):
                    search_candidates.add(index)
            # An empty union is a conclusive no-match result. Keeping it as an
            # explicit empty candidate set avoids scanning the entire logical
            # universe for a query that cannot match any searchable field.
            candidates = search_candidates if candidates is None else candidates & search_candidates
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
        indices = [index for index in (candidate_indices if candidate_indices is not None else range(self.total)) if self._matches_index(index, query)]
        row_cache = {index: self._pattern_rows[index % 64] for index in indices}
        dynamic_keys = {'record_id', 'lot_id', 'wafer_id'}

        def sort_value(index: int, key: str) -> Any:
            if key == 'record_id':
                return f'P-{index + 1:06d}'
            if key == 'lot_id':
                return f'LOT-{(index // 4) + 101:06d}'
            if key == 'wafer_id':
                return f'W{(index % 25) + 1:02d}'
            return row_cache[index].get(key)

        for spec in reversed(query.sorts):
            if spec.key in dynamic_keys:
                present = indices[:]
                missing: list[int] = []
            else:
                present = [index for index in indices if row_cache[index].get(spec.key) is not None]
                missing = [index for index in indices if row_cache[index].get(spec.key) is None]
            try:
                present.sort(key=lambda index: sort_value(index, spec.key), reverse=spec.direction is SortDirection.DESC)
            except TypeError:
                present.sort(key=lambda index: (type(row_cache[index].get(spec.key)).__name__, str(row_cache[index].get(spec.key))), reverse=spec.direction is SortDirection.DESC)
            indices = [*present, *missing]
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


def _visual_summary(parts, rows: Sequence[Mapping[str, Any]], metric_key: str) -> None:
    """Render statistics using the selected metric's unit and population."""
    ui = parts['ui']; metric = visual_metric(metric_key)
    values = [float(row[metric.key]) for row in rows if isinstance(row.get(metric.key), (int, float)) and math.isfinite(float(row[metric.key]))]
    mean = sum(values) / len(values) if values else 0.0
    variance = sum((value - mean) ** 2 for value in values) / len(values) if values else 0.0
    unit = f' {metric.unit}' if metric.unit else ''
    with ui.element('div').classes('cui-data-lab-summary cui-data-lab-summary--visual').props('aria-label="Visual metric summary" data-visual-metric="' + metric.key + '"'):
        for key, label, value in (
            ('count', 'Records', f'{len(rows):,}'),
            ('mean', f'Mean {metric.label}', f'{mean:.3f}{unit}'),
            ('min', f'Min {metric.label}', f'{min(values):.3f}{unit}' if values else '—'),
            ('max', f'Max {metric.label}', f'{max(values):.3f}{unit}' if values else '—'),
            ('stddev', f'Std dev {metric.label}', f'{math.sqrt(variance):.3f}{unit}' if values else '—'),
        ):
            with ui.element('div').classes('cui-workbench-kpi').props(f'data-visual-stat="{key}"'):
                ui.label(value).classes('text-h6')
                ui.label(label)


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

    async def release(rows):
        await update_rows({'status': 'Nominal', 'disposition': 'Released'}, rows)
        status.set_text(f'Released {len(rows)} record(s) and updated the active grid.')

    async def assign(rows):
        await update_rows({'owner': 'M. Chen'}, rows)
        status.set_text(f'Assigned {len(rows)} record(s) to M. Chen.')

    async def hold_one(row):
        await update_rows({'status': 'Hold', 'disposition': 'Hold'}, (row,))
        status.set_text(f'Held {row.get("record_id")} through the row action menu.')

    async def release_one(row):
        await update_rows({'status': 'Nominal', 'disposition': 'Released'}, (row,))
        status.set_text(f'Released {row.get("record_id")} through the row action menu.')

    async def export_selected(rows):
        if not rows:
            status.set_text('Select at least one record before exporting.')
            return
        await table.export(rows=rows, filename='selected-engineering-records.csv')
        status.set_text(f'Exported {len(rows)} selected record(s).')

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
            BulkAction('release', 'Release selected', icon='check-circle', on_action=release,
                       enabled_when=lambda rows: any(row.get('status') in {'Hold', 'OOS', 'Watch'} for row in rows),
                       disabled_reason=lambda rows: 'Selected records are already nominal.'),
            BulkAction('assign', 'Assign selected', icon='user', on_action=assign),
            BulkAction('compare', 'Compare selected', icon='split', on_action=compare),
            BulkAction('export', 'Export selected', icon='download', on_action=export_selected),
            BulkAction('delete', 'Delete selected', icon='delete', intent='danger', on_action=delete),
        ), on_select=selected, on_view_changed=lambda snapshot: summary_update(snapshot.visible_rows),
        row_actions=(
            RowAction('inspect', 'View details', icon='info', on_action=lambda row: _open_detail(parts, row)),
            RowAction('hold-row', 'Hold row', icon='pause', intent='warning', on_action=hold_one,
                      enabled_when=lambda row: row.get('status') != 'Hold',
                      disabled_reason=lambda row: 'This record is already on Hold.'),
            RowAction('release-row', 'Release row', icon='check-circle', on_action=release_one,
                      enabled_when=lambda row: row.get('status') in {'Hold', 'OOS', 'Watch'},
                      disabled_reason=lambda row: 'Only Watch, OOS or Hold records can be released.'),
        ),
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

    async def edit_record(row: Mapping[str, Any]) -> None:
        drawer = FormDrawer(f"Edit {row.get('record_id')}", subtitle='Confirmed save · validation and rollback are framework-owned')
        with drawer:
            measurement = parts['NumberInput']('Measurement', value=float(row.get('measurement_nm') or 0), minimum=0, maximum=100, step=.001, unit='nm', required=True)
            status_input = parts['Select']('Status', {value: value for value in ('Nominal', 'Watch', 'OOS', 'Hold')}, value=row.get('status'), clearable=False)
            owner_input = parts['TextInput']('Owner', value=str(row.get('owner') or ''), required=True)
            reviewed_input = parts['Select']('Reviewed', {'true': 'Yes', 'false': 'No'}, value='true' if row.get('reviewed') else 'false', clearable=False)
            async def commit():
                try:
                    value = float(measurement.element.value)
                except (TypeError, ValueError):
                    status.set_text('Edit rejected: Measurement must be a finite number between 0 and 100 nm.')
                    return
                candidate = dict(row)
                candidate.update({'measurement_nm': value, 'delta_nm': round(value - float(candidate.get('target_nm') or 0), 3), 'status': status_input.element.value, 'owner': owner_input.element.value, 'reviewed': str(reviewed_input.element.value).lower() == 'true'})
                error = validate(candidate, 'measurement_nm', value)
                if error:
                    status.set_text(f'Edit rejected: {error}')
                    return
                for current in session.rows:
                    if current.get('record_id') == row.get('record_id'):
                        current.update(candidate)
                await table.update_rows_by_key((candidate,))
                status.set_text(f"Updated {row.get('record_id')}.")
                drawer.close()
            _button(parts, 'Save record', commit, primary=True, icon='save')
        drawer.open()

    async def duplicate_record(row: Mapping[str, Any]) -> None:
        base = dict(row)
        index = len(session.rows) + 1
        new_id = f'R-DUP-{index:03d}'
        while any(item.get('record_id') == new_id for item in session.rows):
            index += 1
            new_id = f'R-DUP-{index:03d}'
        base['record_id'] = new_id
        base['reviewed'] = False
        base['comment'] = 'Duplicated from reference action'
        session.rows.append(base)
        await table.apply_row_transaction(add=(base,))
        status.set_text(f'Duplicated {row.get("record_id")} as {new_id}.')

    async def delete_record(row: Mapping[str, Any]) -> None:
        async def confirm():
            session.rows[:] = [item for item in session.rows if item.get('record_id') != row.get('record_id')]
            await table.remove_rows_by_key((row.get('record_id'),))
            status.set_text(f'Deleted {row.get("record_id")}.')
        danger = parts['DangerConfirmDialog']('Delete engineering record', description='Only this local reference record will be removed.', on_confirm=confirm)
        danger.open()

    table = EditableTable(
        rows, columns,
        spec=EditableTableSpec(tuple(columns), row_key='record_id', title='Engineering disposition', selection=SelectionMode.SINGLE, save_mode='cell', commit_mode=EditCommitMode.CONFIRMED, persist_key='reference-data-edit'),
        validate_edit=validate, save_edit=save,
        row_actions=(
            RowAction('inspect', 'Inspect row', icon='info', on_action=lambda row: _open_detail(parts, row)),
            RowAction('edit', 'Edit record', icon='edit', on_action=edit_record),
            RowAction('duplicate', 'Duplicate record', icon='copy', on_action=duplicate_record),
            RowAction('delete', 'Delete record', icon='delete', intent='danger', on_action=delete_record),
        ),
    )

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


def _chart(parts, rows: Sequence[Mapping[str, Any]], *, kind: str = 'trend', measurement_key: str = 'measurement_nm', x_key: str = 'timestamp', y_key: str = 'yield_pct'):
    ChartPanel = parts['ChartPanel']; AxisSpec = parts['AxisSpec']; AxisType = parts['AxisType']; ChartKind = parts['ChartKind']; ChartPanelSpec = parts['ChartPanelSpec']; ChartSize = parts['ChartSize']; SeriesSpec = parts['SeriesSpec']; SpecLimits = parts['SpecLimits']
    metric = visual_metric(measurement_key)
    labels = [str(row.get('timestamp') or row.get('record_id')) for row in rows]
    values = [float(row.get(metric.key)) for row in rows if isinstance(row.get(metric.key), (int, float)) and math.isfinite(float(row.get(metric.key)))]
    metric_axis = f'{metric.label} ({metric.unit})'
    limits = SpecLimits(lower=metric.spec_lower, upper=metric.spec_upper, target=metric.target) if metric.spec_lower is not None and metric.spec_upper is not None else None
    if kind == 'distribution':
        lo = min(values) if values else 0.0
        hi = max(values) if values else 1.0
        span = max((hi - lo) / 4, .001)
        bins = tuple(f'{lo + index * span:.2f}–{lo + (index + 1) * span:.2f}' for index in range(4))
        counts = [sum(lo + bucket * span <= value < (lo + (bucket + 1) * span if bucket < 3 else hi + .001) for value in values) for bucket in range(4)]
        spec = ChartPanelSpec(f'{metric.label} distribution ({metric.unit})', 'Filtered records by the selected metric.', kind=ChartKind.BAR, size=ChartSize.STANDARD, x_axis=AxisSpec(metric_axis, AxisType.CATEGORY, categories=bins), y_axis=AxisSpec('Records', AxisType.VALUE))
        return ChartPanel((SeriesSpec('distribution', 'Records', counts, kind=ChartKind.BAR),), spec=spec, spec_limits=limits)
    if kind == 'scatter':
        x_metric = VISUAL_METRICS.get(x_key)
        y_metric = VISUAL_METRICS.get(y_key, metric)
        x_label = f'{x_metric.label} ({x_metric.unit})' if x_metric else x_key.replace('_', ' ').title()
        y_label = f'{y_metric.label} ({y_metric.unit})'
        data = [{'x': float(row.get(x_key)), 'y': float(row.get(y_metric.key))} for row in rows if isinstance(row.get(x_key), (int, float)) and isinstance(row.get(y_metric.key), (int, float)) and math.isfinite(float(row.get(x_key))) and math.isfinite(float(row.get(y_metric.key)))]
        spec = ChartPanelSpec(f'{x_label} vs {y_label}', 'Selected and filtered records stay in the same engineering population.', kind=ChartKind.SCATTER, size=ChartSize.STANDARD, x_axis=AxisSpec(x_label, AxisType.VALUE, unit=x_metric.unit if x_metric else None), y_axis=AxisSpec(y_label, AxisType.VALUE, unit=y_metric.unit))
        scatter_limits = SpecLimits(lower=y_metric.spec_lower, upper=y_metric.spec_upper, target=y_metric.target) if y_metric.spec_lower is not None and y_metric.spec_upper is not None else None
        return ChartPanel((SeriesSpec('records', 'Records', data, kind=ChartKind.SCATTER, x_key='x', y_key='y'),), spec=spec, spec_limits=scatter_limits)
    if kind == 'spc':
        center = metric.target if metric.target is not None else (sum(values) / len(values) if values else 0.0)
        spread = max(.12 if metric.unit == 'nm' else .5, (max(values) - min(values)) * .75) if values else (.3 if metric.unit == 'nm' else 1.0)
        control_limits = SpecLimits(lower=metric.spec_lower if metric.spec_lower is not None else center - spread, upper=metric.spec_upper if metric.spec_upper is not None else center + spread, target=metric.target)
        spec = ChartPanelSpec(f'SPC {metric_axis}', 'Metric-aware center, specification and control semantics.', kind=ChartKind.CONTROL, size=ChartSize.STANDARD, x_axis=AxisSpec('Timestamp', AxisType.CATEGORY, categories=labels), y_axis=AxisSpec(metric_axis, AxisType.VALUE, unit=metric.unit))
        return ChartPanel((SeriesSpec(metric.key, metric.label, values, kind=ChartKind.CONTROL, semantic_color='accent'),), spec=spec, spec_limits=control_limits, thresholds=(parts['ThresholdSpec'](center, 'Target'), parts['ThresholdSpec'](control_limits.upper, 'USL'), parts['ThresholdSpec'](control_limits.lower, 'LSL')))
    if kind == 'wafer':
        points = [((index % 7) - 3, (index // 7) - 3, float(row.get(metric.key) or 0)) for index, row in enumerate(rows[:49])]
        spec = ChartPanelSpec(f'Wafer {metric_axis} map', 'The same filtered engineering records mapped to bounded wafer coordinates.', kind=ChartKind.WAFER, size=ChartSize.STANDARD, x_axis=AxisSpec('Die X', AxisType.VALUE), y_axis=AxisSpec(metric_axis, AxisType.VALUE, unit=metric.unit))
        return ChartPanel((SeriesSpec('wafer', metric.label, points, kind=ChartKind.WAFER),), spec=spec, spec_limits=limits)
    spec = ChartPanelSpec(f'{metric_axis} trend', 'Trend X uses timestamp/record order; the selected metric owns the Y axis and limits.', kind=ChartKind.LINE, size=ChartSize.STANDARD, x_axis=AxisSpec('Timestamp', AxisType.CATEGORY, categories=labels), y_axis=AxisSpec(metric_axis, AxisType.VALUE, unit=metric.unit))
    return ChartPanel((SeriesSpec(metric.key, metric.label, values, kind=ChartKind.LINE, x_key=None, y_key=None),), spec=spec, spec_limits=limits)


def _render_visualize(parts, session: DataLabSession) -> None:
    ui = parts['ui']; SearchInput = parts['SearchInput']; SegmentedControl = parts['SegmentedControl']
    state: dict[str, Any] = {'search': '', 'chart': 'trend', 'selected': set(), 'population': tuple(session.rows), 'measurement_field': 'measurement_nm', 'x_field': 'measurement_nm', 'y_field': 'yield_pct'}
    summary_host = None
    chart_host = None
    status = None

    def active_metric_key() -> str:
        return state['y_field'] if state['chart'] == 'scatter' else state['measurement_field']

    def set_summary(rows: Sequence[Mapping[str, Any]]) -> None:
        summary_host.clear()
        with summary_host:
            _visual_summary(parts, rows, active_metric_key())

    def set_chart(rows: Sequence[Mapping[str, Any]]) -> None:
        chart_host.clear()
        with chart_host:
            chart_rows = tuple(row for row in rows if not state['selected'] or row.get('record_id') in state['selected'])
            metric = visual_metric(active_metric_key())
            if state['chart'] == 'scatter':
                x_metric = visual_metric(state['x_field'])
                y_metric = visual_metric(state['y_field'])
                mapping = f"X: {x_metric.label} ({x_metric.unit}) · Y: {y_metric.label} ({y_metric.unit})"
            else:
                mapping = f"X: Timestamp / record order · Y: {metric.label} ({metric.unit})"
            ui.label(
                f"Chart uses {'selected' if state['selected'] else 'filtered'} population · {len(chart_rows)} records · {mapping}"
            ).classes('cui-workbench-section-title').props('data-visual-contract role="status"')
            _chart(parts, chart_rows, kind=state['chart'], measurement_key=state['measurement_field'], x_key=state['x_field'], y_key=state['y_field'])
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
    with ui.element('div').classes('cui-data-lab-visual-controls'):
        async def search_changed(event) -> None:
            state['search'] = str(getattr(event, 'value', '') or '')
            state['selected'].clear()
            await table.replace_rows(session.filtered(search=state['search']))
            state['population'] = tuple(table.rows)
            set_summary(state['population']); set_chart(state['population'])
        field_options = {key: f'{metric.label} ({metric.unit})' for key, metric in VISUAL_METRICS.items()}
        async def measurement_changed(event) -> None:
            state['measurement_field'] = str(getattr(event, 'value', 'measurement_nm') or 'measurement_nm')
            # The metric selection changes both the analytical Y contract and
            # the KPI units.  Keep the summary and the chart as one governed
            # semantic update, so a Yield selection cannot retain nm stats.
            set_summary(state['population'])
            set_chart(state['population'])
        async def x_changed(event) -> None:
            state['x_field'] = str(getattr(event, 'value', 'measurement_nm') or 'measurement_nm')
            set_chart(state['population'])
        async def y_changed(event) -> None:
            state['y_field'] = str(getattr(event, 'value', 'yield_pct') or 'yield_pct')
            if state['chart'] == 'scatter':
                set_summary(state['population'])
            set_chart(state['population'])
        Select = parts['Select']
        with ui.element('div').classes('cui-data-lab-visual-control-group cui-data-lab-visual-search'):
            ui.label('Search').classes('cui-workbench-card__meta')
            SearchInput('Search linked records', placeholder='Lot, tool, chamber, status…', debounce_ms=180, on_change=search_changed)
        with ui.element('div').classes('cui-data-lab-visual-control-group cui-data-lab-visual-mapping'):
            ui.label('Field mapping').classes('cui-workbench-card__meta')
            with ui.element('div').classes('cui-data-lab-visual-mapping-controls'):
                Select('Measurement / Y', field_options, value='measurement_nm', clearable=False, on_change=measurement_changed)
                Select('X (scatter)', field_options, value='measurement_nm', clearable=False, on_change=x_changed)
                Select('Y (scatter)', field_options, value='yield_pct', clearable=False, on_change=y_changed)
        with ui.element('div').classes('cui-data-lab-visual-control-group cui-data-lab-visual-mode'):
            ui.label('Chart mode').classes('cui-workbench-card__meta')
            with ui.element('div').classes('cui-data-lab-chart-switcher'):
                async def chart_changed(event) -> None:
                    state['chart'] = str(getattr(event, 'value', 'trend') or 'trend')
                    set_summary(state['population'])
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
preview = dock.stage_text(text, source_name='incoming.tsv')
if preview.ok:
    # Inspect preview.snapshot/schema_diff() before replacing active rows.
    dock.commit_stage()
else:
    dock.discard_stage()
""", 'DataDock owns format detection, schema inference, quality issues, hardened import limits, staged preview/commit/cancel and rectangular paste.')


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
    with ui.element('div').classes('cui-data-lab-state-selector').props('aria-label="Table state selector"'):
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
