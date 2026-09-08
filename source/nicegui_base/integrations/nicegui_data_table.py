from __future__ import annotations

import asyncio
import html
import inspect
import json
import time
import weakref
from contextlib import AbstractContextManager
from dataclasses import replace
from typing import Any, Callable, Mapping, Sequence

from nicegui_base.data_table import (
    BulkAction, ColumnKind, ConditionalRule, DataTableSpec, EditCommitMode, EditableTableSpec, FilterExpression, FilterGroup, FilterLogic, FilterOperator, FilterSpec,
    PinPosition, RowAction, SelectionMode, ServerDataTableSpec, SortDirection, SortSpec, TableColumn,
    TableDensity, TablePreset, TableQuery, TableResult, TableState,
)
from nicegui_base.data_table.engine import export_csv as _export_csv_text
from nicegui_base.async_tools import LatestRequestController
from nicegui_base.performance import LifecycleScope, RetryPolicy
from nicegui_base.services import PreferenceService
from nicegui_base.visual import render_icon_svg


def _ui():
    try:
        from nicegui import ui
    except ImportError as exc:
        raise RuntimeError('NiceGUI is required to render NiceGUI Base components') from exc
    return ui


async def _invoke(callback: Callable[..., Any] | None, *args) -> Any:
    if callback is None:
        return None
    value = callback(*args)
    if inspect.isawaitable(value):
        return await value
    return value


def _icon(ui, key: str, *, label: str | None = None, size: str = 'xs'):
    return ui.html(render_icon_svg(key, size=size, label=label), sanitize=False).classes('cui-svg-icon-host')

_ACTIVE_TABLES: 'weakref.WeakSet[DataTable]' = weakref.WeakSet()
_DENSITY_ROWS = {'comfortable':44,'compact':38,'dense':34}

async def apply_all_table_density(density: str) -> None:
    if density not in _DENSITY_ROWS:
        return
    failures: list[str] = []
    for table in tuple(_ACTIVE_TABLES):
        try:
            await table.set_density(TableDensity(density))
        except Exception as exc:
            failures.append(f'{type(table).__name__}: {type(exc).__name__}: {exc}')
    if failures:
        raise RuntimeError('NiceGUI Base table density update failed: ' + ' | '.join(failures))


def _js_literal(value: Any) -> str:
    return json.dumps(value, separators=(',', ':'))


def _freeze_filter_key(item: FilterExpression) -> tuple[Any, ...]:
    if isinstance(item, FilterGroup):
        return ('group', item.logic.value, tuple(_freeze_filter_key(child) for child in item.filters))
    return ('filter', item.key, item.operator.value, repr(item.value), repr(item.value2))

def _table_query_key(query: TableQuery) -> tuple[Any, ...]:
    """Hashable request key resilient to nested filters and container values."""
    return (
        query.page, query.page_size, query.search,
        tuple((item.key, item.direction.value) for item in query.sorts),
        tuple(_freeze_filter_key(item) for item in query.filters),
    )


def _retry_server_read(exc: BaseException) -> bool:
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


def _default_table_preferences() -> PreferenceService | None:
    """Resolve NiceGUI Base's governed NiceGUI user preference store when usable."""
    try:
        from nicegui_base.integrations.nicegui_state import NiceGUIStateServices
        return NiceGUIStateServices.user_preferences()
    except Exception:
        # Applications without a storage_secret can still render tables; explicit
        # PreferenceService injection remains available in those environments.
        return None


def _register_client_delete(ui: Any, callback: Callable[..., Any]) -> bool:
    """Register a NiceGUI client-deletion hook when a real client context exists.

    Synthetic construction tests intentionally provide only factory stubs. The
    lifecycle contract should remain inert there rather than making route
    construction depend on a browser client that does not exist.
    """
    context=getattr(ui,'context',None)
    client=getattr(context,'client',None)
    on_delete=getattr(client,'on_delete',None)
    if callable(on_delete):
        on_delete(callback)
        return True
    return False

async def _deferred_lifecycle_call(callback: Callable[[], Any]) -> None:
    """Run startup work on the next loop turn without creating a slot-owned Timer."""
    await asyncio.sleep(0)
    value = callback()
    if inspect.isawaitable(value):
        await value


def _schedule_scope_task(scope: LifecycleScope, awaitable, *, name: str) -> asyncio.Task[Any] | None:
    """Schedule lifecycle work when a running loop exists; remain inert in static construction."""
    try:
        return scope.create_task(awaitable, name=name)
    except RuntimeError:
        close = getattr(awaitable, 'close', None)
        if callable(close):
            close()
        return None



def _ag_operator(raw_type: Any) -> FilterOperator | None:
    return {
        'contains': FilterOperator.CONTAINS, 'notContains': FilterOperator.NOT_CONTAINS,
        'equals': FilterOperator.EQUALS, 'notEqual': FilterOperator.NOT_EQUALS,
        'greaterThan': FilterOperator.GT, 'greaterThanOrEqual': FilterOperator.GTE,
        'lessThan': FilterOperator.LT, 'lessThanOrEqual': FilterOperator.LTE,
        'startsWith': FilterOperator.STARTS_WITH, 'endsWith': FilterOperator.ENDS_WITH,
        'inRange': FilterOperator.BETWEEN, 'blank': FilterOperator.IS_EMPTY,
        'notBlank': FilterOperator.IS_NOT_EMPTY,
    }.get(raw_type)


def _filter_leaf_from_grid(key: str, raw: Mapping[str, Any]) -> FilterSpec | None:
    if raw.get('filterType') == 'set' or isinstance(raw.get('values'), (list, tuple, set)):
        values = raw.get('values') or ()
        return FilterSpec(key, FilterOperator.IN, tuple(values))
    operator = _ag_operator(raw.get('type'))
    if operator is None:
        return None
    if operator in {FilterOperator.IS_EMPTY, FilterOperator.IS_NOT_EMPTY}:
        return FilterSpec(key, operator)
    return FilterSpec(key, operator, raw.get('filter'), raw.get('filterTo'))


def _filter_expression_from_grid(key: str, raw: Mapping[str, Any]) -> FilterExpression | None:
    conditions = raw.get('conditions')
    if not isinstance(conditions, Sequence) or isinstance(conditions, (str, bytes, bytearray)):
        conditions = [raw[name] for name in ('condition1', 'condition2') if isinstance(raw.get(name), Mapping)]
    if conditions:
        children = tuple(
            child for condition in conditions
            if isinstance(condition, Mapping)
            if (child := _filter_expression_from_grid(key, condition)) is not None
        )
        if not children:
            return None
        if len(children) == 1:
            return children[0]
        logic = FilterLogic.OR if str(raw.get('operator', 'AND')).upper() == 'OR' else FilterLogic.AND
        return FilterGroup(logic, children)
    return _filter_leaf_from_grid(key, raw)


def _filter_specs_from_grid_model(model: Mapping[str, Any]) -> list[FilterExpression]:
    filters: list[FilterExpression] = []
    for key, raw in model.items():
        if not isinstance(raw, Mapping):
            continue
        parsed = _filter_expression_from_grid(str(key), raw)
        if parsed is not None:
            filters.append(parsed)
    return filters


def _leaf_to_grid(item: FilterSpec) -> dict[str, Any] | None:
    if item.operator in {FilterOperator.IN, FilterOperator.NOT_IN}:
        # AG Grid's set filter has no portable native NOT_IN representation.
        # Community AG Grid does not provide the Enterprise set-filter module.
        # Represent IN as an OR of exact text predicates so the same public
        # filter contract works without a proprietary runtime.
        if item.operator is FilterOperator.NOT_IN:
            return None
        values = item.value if isinstance(item.value, (list, tuple, set)) else (item.value,)
        conditions = [{'filterType': 'text', 'type': 'equals', 'filter': value} for value in values]
        if len(conditions) == 1:
            return conditions[0]
        return {'filterType': 'text', 'operator': 'OR', 'conditions': conditions}
    type_map = {
        FilterOperator.CONTAINS: 'contains', FilterOperator.NOT_CONTAINS: 'notContains',
        FilterOperator.EQUALS: 'equals', FilterOperator.NOT_EQUALS: 'notEqual',
        FilterOperator.STARTS_WITH: 'startsWith', FilterOperator.ENDS_WITH: 'endsWith',
        FilterOperator.GT: 'greaterThan', FilterOperator.GTE: 'greaterThanOrEqual',
        FilterOperator.LT: 'lessThan', FilterOperator.LTE: 'lessThanOrEqual',
        FilterOperator.BETWEEN: 'inRange', FilterOperator.IS_EMPTY: 'blank',
        FilterOperator.IS_NOT_EMPTY: 'notBlank',
    }
    filter_type = type_map.get(item.operator)
    if filter_type is None:
        return None
    value: dict[str, Any] = {'type': filter_type}
    if item.operator not in {FilterOperator.IS_EMPTY, FilterOperator.IS_NOT_EMPTY}:
        value['filter'] = item.value
    if item.operator is FilterOperator.BETWEEN:
        value['filterTo'] = item.value2
    return value


def _expression_to_grid(item: FilterExpression) -> tuple[str, dict[str, Any]] | None:
    if isinstance(item, FilterSpec):
        value = _leaf_to_grid(item)
        return (item.key, value) if value is not None else None
    converted = [entry for child in item.filters if (entry := _expression_to_grid(child)) is not None]
    if not converted:
        return None
    keys = {key for key, _ in converted}
    if len(keys) != 1:
        # AG Grid stores filter models per column; cross-column groups are a
        # server query concern and cannot be represented losslessly in the UI model.
        return None
    key = converted[0][0]
    conditions = [value for _, value in converted]
    return key, {'operator': item.logic.value.upper(), 'conditions': conditions}


def _filter_model_from_specs(filters: Sequence[FilterExpression]) -> dict[str, dict[str, Any]]:
    model: dict[str, dict[str, Any]] = {}
    per_key: dict[str, list[dict[str, Any]]] = {}
    for item in filters:
        converted = _expression_to_grid(item)
        if converted is None:
            continue
        key, value = converted
        per_key.setdefault(key, []).append(value)
    for key, values in per_key.items():
        model[key] = values[0] if len(values) == 1 else {'operator': 'AND', 'conditions': values}
    return model


def _stateful_table_spec(spec: DataTableSpec, state: TableState) -> DataTableSpec:
    """Apply persisted column geometry to immutable table definitions pre-mount."""
    by_key = {column.key: column for column in spec.columns}
    ordered_keys = [key for key in state.column_order if key in by_key]
    ordered_keys.extend(key for key in by_key if key not in ordered_keys)
    left = set(state.pinned_left); right = set(state.pinned_right)
    columns: list[TableColumn] = []
    for key in ordered_keys:
        column = by_key[key]
        pin = PinPosition.LEFT if key in left else PinPosition.RIGHT if key in right else PinPosition.NONE
        columns.append(replace(
            column,
            visible=key in set(state.visible_columns),
            width=state.column_widths.get(key, column.width),
            pinned=pin,
        ))
    page_size = state.page_size if state.page_size in spec.page_size_options else spec.page_size
    return replace(spec, columns=tuple(columns), density=state.density, page_size=page_size)


def _rule_expression(rule: ConditionalRule) -> str:
    v = _js_literal(rule.value); v2 = _js_literal(rule.value2)
    op = rule.operator
    if op is FilterOperator.IS_EMPTY: return "x == null || x === ''"
    if op is FilterOperator.IS_NOT_EMPTY: return "x != null && x !== ''"
    if op is FilterOperator.EQUALS: return f'x === {v}'
    if op is FilterOperator.NOT_EQUALS: return f'x !== {v}'
    if op is FilterOperator.GT: return f'x > {v}'
    if op is FilterOperator.GTE: return f'x >= {v}'
    if op is FilterOperator.LT: return f'x < {v}'
    if op is FilterOperator.LTE: return f'x <= {v}'
    if op is FilterOperator.BETWEEN: return f'x >= {v} && x <= {v2}'
    if op is FilterOperator.CONTAINS: return f"String(x ?? '').toLowerCase().includes(String({v}).toLowerCase())"
    if op is FilterOperator.STARTS_WITH: return f"String(x ?? '').toLowerCase().startsWith(String({v}).toLowerCase())"
    if op is FilterOperator.ENDS_WITH: return f"String(x ?? '').toLowerCase().endsWith(String({v}).toLowerCase())"
    if op is FilterOperator.IN: return f'{v}.includes(x)'
    return 'false'


class ConditionalCellFormatter:
    """Compile semantic conditional rules into AG Grid class rules."""
    INTENT_CLASSES = {
        'success': 'cui-table-cell--success', 'warning': 'cui-table-cell--warning', 'danger': 'cui-table-cell--danger',
    }

    @classmethod
    def class_rules(cls, rules: Sequence[ConditionalRule]) -> dict[str, str]:
        result: dict[str, str] = {}
        for rule in rules:
            css_class = cls.INTENT_CLASSES.get(rule.intent)
            if css_class:
                result[css_class] = _rule_expression(rule)
        return result


class StatusCell:
    DEFAULT_MAP = {
        'normal': 'success', 'complete': 'success', 'success': 'success', 'ready': 'success', 'healthy': 'success',
        'watch': 'warning', 'warning': 'warning', 'partial': 'warning', 'delayed': 'warning', 'stale': 'warning',
        'critical': 'danger', 'error': 'danger', 'oos': 'danger', 'failed': 'danger', 'unavailable': 'danger',
        'info': 'info', 'maintenance': 'info', 'offline': 'neutral', 'unknown': 'neutral',
    }

    @classmethod
    def renderer(cls, status_map: Mapping[str, str] | None = None) -> str:
        mapping = {**cls.DEFAULT_MAP, **{str(k).lower(): v for k, v in (status_map or {}).items()}}
        js_map = _js_literal(mapping)
        return f'''params => {{
          if (params.value == null || params.value === '') return '<span class="is-muted">—</span>';
          const raw=String(params.value); const key=raw.toLowerCase(); const map={js_map};
          const intent=map[key] || 'neutral';
          return `<span class="cui-table-status cui-table-status--${{intent}}">${{raw.replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}</span>`;
        }}'''


class SparklineCell:
    @staticmethod
    def renderer() -> str:
        return r'''params => {
          const a=Array.isArray(params.value)?params.value:[];
          const vals=a.map(Number).filter(Number.isFinite);
          if(vals.length<2) return '<span class="is-muted">—</span>';
          const lo=Math.min(...vals), hi=Math.max(...vals), span=(hi-lo)||1;
          const w=76,h=22,p=2;
          const pts=vals.map((v,i)=>{
            const x=p+(i/(vals.length-1))*(w-p*2);
            const y=h-p-((v-lo)/span)*(h-p*2);
            return `${x.toFixed(1)},${y.toFixed(1)}`;
          }).join(' ');
          const last=pts.split(' ').at(-1).split(',');
          const label=`Trend ${vals.map(v=>v.toFixed(2)).join(', ')}`;
          return `<svg class="cui-table-sparkline" viewBox="0 0 ${w} ${h}" role="img" aria-label="${label}"><polyline points="${pts}" fill="none" vector-effect="non-scaling-stroke"/><circle cx="${last[0]}" cy="${last[1]}" r="2"/></svg>`;
        }'''


def _column_def(c: TableColumn) -> dict[str, Any]:
    cell_classes: list[str] = []
    if c.effective_align == 'right': cell_classes.append('is-numeric')
    elif c.effective_align == 'center': cell_classes.append('is-center')
    header_class = 'cui-priority-low' if c.priority == 'low' else ''
    if c.priority == 'low': cell_classes.append('cui-priority-low')
    d: dict[str, Any] = {
        'field': c.key,
        'headerName': c.label,
        'sortable': c.sortable,
        'filter': c.filterable,
        'resizable': c.resizable,
        'hide': not c.visible,
        'minWidth': c.min_width,
        'editable': c.editable,
        'headerTooltip': c.tooltip or c.label,
        'cellClass': ' '.join(cell_classes),
        'headerClass': header_class,
    }
    if c.width is not None: d['width'] = c.width
    if c.max_width is not None: d['maxWidth'] = c.max_width
    if c.pinned is not PinPosition.NONE: d['pinned'] = c.pinned.value
    class_rules = ConditionalCellFormatter.class_rules(c.rules) if c.rules else {}
    if c.editable:
        class_rules['cui-table-cell--pending'] = "Array.isArray(data?.__cui_pending_fields) && data.__cui_pending_fields.includes(colDef.field)"
    if class_rules: d['cellClassRules'] = class_rules
    if c.kind is ColumnKind.BOOLEAN:
        # Text-equivalent values do not justify a DOM cell renderer; keep the virtualized cell cheap.
        d[':valueFormatter'] = "params => params.value == null ? '—' : (params.value ? 'Yes' : 'No')"
    elif c.kind is ColumnKind.STATUS:
        d[':cellRenderer'] = StatusCell.renderer(c.status_map)
    elif c.kind is ColumnKind.SPARKLINE:
        d[':cellRenderer'] = SparklineCell.renderer()
    elif c.kind in {ColumnKind.INTEGER, ColumnKind.FLOAT, ColumnKind.PERCENT, ColumnKind.DURATION}:
        decimals = c.decimals if c.decimals is not None else (0 if c.kind is ColumnKind.INTEGER else 2)
        suffix = '%' if c.kind is ColumnKind.PERCENT else (f' {c.unit}' if c.unit else '')
        d[':valueFormatter'] = f"params => params.value == null || params.value === '' ? '—' : (Number(params.value).toFixed({decimals}) + {_js_literal(suffix)})"
    return d


class TableToolbar:
    """Company-owned engineering toolbar: one native search field plus one action cluster."""
    def __init__(self, table: 'DataTable | None' = None, *, searchable: bool=True, columns: bool=True,
                 density: bool=True, export: bool=True, refresh: bool=True):
        self.table=table; self.searchable=searchable; self.columns=columns; self.density=density; self.export=export; self.refresh=refresh
        self.element=None; self.search_input=None; self.density_selector=None; self.column_manager=None
        if table is not None: self.render()

    def render(self):
        ui=_ui(); table=self.table
        with ui.element('div').classes('cui-table-toolbar').props('role="toolbar" aria-label="Table controls"') as self.element:
            if self.searchable:
                with ui.element('label').classes('cui-table-search'):
                    ui.html(render_icon_svg('search', size='xs', label=None), sanitize=False).classes('cui-table-search__icon').props('aria-hidden="true"')
                    self.search_input=ui.element('input').classes('cui-table-search__input').props('type="search" autocomplete="off" spellcheck="false" placeholder="Search records" aria-label="Search table"')
                    if table.search:
                        self.search_input.props(f'value="{html.escape(table.search, quote=True)}"')
                    async def search_changed(e):
                        value = e.args if isinstance(getattr(e,'args',None), str) else ''
                        await table.set_search(value)
                    self.search_input.on('input', search_changed, throttle=.18, leading_events=False, trailing_events=True, js_handler='e => emit(e.target.value)')
                    ui.html('<kbd class="cui-table-search__shortcut" aria-hidden="true">/</kbd>', sanitize=False)
            with ui.element('div').classes('cui-table-toolbar__actions'):
                if self.columns: self.column_manager=TableColumnManager(table.spec.columns, table=table)
                if self.density: self.density_selector=TableDensitySelector(table.spec.density, table=table)
                if self.export:
                    async def do_export(e=None): await _invoke(table.export)
                    button=ui.button(on_click=do_export).props('flat no-caps aria-label="Export CSV"').classes('cui-table-tool-button')
                    with button: _icon(ui,'download',size='xs'); ui.label('Export')
                if self.refresh:
                    async def do_refresh(e=None): await _invoke(table.refresh)
                    button=ui.button(on_click=do_refresh).props('flat no-caps aria-label="Refresh table"').classes('cui-table-tool-button')
                    with button: _icon(ui,'refresh',size='xs'); ui.label('Refresh')
        return self.element


class TableDensitySelector:
    def __init__(self, density: TableDensity = TableDensity.COMPACT, *, table: 'DataTable | None'=None):
        self.density=density; self.table=table; self.element=None; self.label=None
        if table is not None:
            ui=_ui(); button=ui.button().props('flat no-caps aria-label="Table density"').classes('cui-table-tool-button')
            with button:
                _icon(ui,'density',size='xs')
                self.label=ui.label(density.value.title()).classes('cui-table-tool-button__label')
                with ui.menu().classes('cui-menu cui-table-density-menu cui-overlay-surface cui-overlay-surface--popover'):
                    ui.label('Row density').classes('cui-menu-heading')
                    for choice in TableDensity:
                        async def choose(e=None, c=choice):
                            await table.set_density(c)
                        with ui.button(on_click=choose).props('flat no-caps').classes('cui-menu-item cui-table-density-option'):
                            with ui.element('span').classes('cui-table-density-option__copy'):
                                ui.label(choice.value.title())
                                ui.label(f'{_DENSITY_ROWS[choice.value]} px rows').classes('cui-table-density-option__meta')
            self.element=button

    def set_value(self, density: TableDensity) -> None:
        self.density=density
        if self.label is not None: self.label.set_text(density.value.title())


class TableColumnManager:
    def __init__(self, columns: Sequence[TableColumn], *, table: 'DataTable | None'=None):
        self.columns=tuple(columns); self.table=table; self.element=None; self.controls: dict[str, Any] = {}
        if table is not None:
            ui=_ui(); button=ui.button().props('flat no-caps aria-label="Choose columns"').classes('cui-table-tool-button')
            with button:
                _icon(ui,'columns',size='xs'); ui.label('Columns')
                with ui.menu().classes('cui-menu cui-column-menu cui-overlay-surface cui-overlay-surface--popover'):
                    ui.label('Visible columns').classes('cui-menu-heading')
                    with ui.element('div').classes('cui-table-column-list'):
                        for column in self.columns:
                            with ui.element('label').classes('cui-table-column-option'):
                                props='type="checkbox"'
                                if column.visible: props += ' checked'
                                control=ui.element('input').classes('cui-table-column-option__native').props(props)
                                self.controls[column.key]=control
                                async def change(e, c=column):
                                    checked=bool(getattr(e,'args',False))
                                    await table.set_column_visible(c.key,checked)
                                control.on('change', change, js_handler='e => emit(e.target.checked)')
                                ui.element('span').classes('cui-table-column-option__check').props('aria-hidden="true"')
                                ui.label(column.label).classes('cui-table-column-option__label')
                    ui.separator().classes('cui-menu-separator')
                    async def auto_size(e=None): await _invoke(table.auto_size_columns)
                    ui.button('Auto-size columns', on_click=auto_size).props('flat no-caps').classes('cui-menu-item')
            self.element=button

    def set_visible(self, key: str, visible: bool) -> None:
        control=self.controls.get(key)
        if control is None: return
        control.props(add='checked' if visible else None, remove=None if visible else 'checked')


class TableSelectionBar:
    def __init__(self, actions: Sequence[BulkAction]=(), *, table: 'DataTable | None'=None):
        self.actions=tuple(actions); self.table=table; self.element=None; self.count_label=None
        if table is not None:
            ui=_ui()
            with ui.element('div').classes('cui-table-selection-bar') as self.element:
                self.count_label=ui.label('0 selected').classes('cui-table-selection-count')
                for action in self.actions:
                    async def run(e=None, a=action):
                        rows=await table.selected_rows(); await _invoke(a.on_action, rows)
                    btn=ui.button(on_click=run).props('flat dense no-caps').classes(f'cui-button cui-button--{action.intent} cui-control--small')
                    with btn:
                        if action.icon: _icon(ui,action.icon,size='xs')
                        ui.label(action.label)
                ui.element('div').classes('cui-table-toolbar__spacer')
                async def clear_selection(e=None): await _invoke(table.deselect_all)
                clear=ui.button(on_click=clear_selection).props('flat round aria-label="Clear selection"').classes('cui-icon-button')
                with clear: _icon(ui,'close',label='Clear selection')
            self.element.set_visibility(False)

    def update_count(self, count:int) -> None:
        if self.count_label is not None:
            self.count_label.set_text(f'{count} selected')
        if self.element is not None:
            self.element.set_visibility(count>0)


class TableRowActions:
    def __init__(self, actions: Sequence[RowAction]=()): self.actions=tuple(actions)


class TableContextMenu(TableRowActions):
    """Executable row context menu for DataTable records."""
    def __init__(self, actions: Sequence[RowAction]=()):
        super().__init__(actions); self.row: Mapping[str,Any] | None=None; self.menu=None
        if actions:
            ui=_ui(); self.menu=ui.context_menu().classes('cui-menu cui-table-context-menu')
            with self.menu:
                for action in self.actions:
                    async def run(e=None, a=action):
                        if self.row is not None: await _invoke(a.on_action,self.row)
                        self.menu.close()
                    with ui.button(on_click=run).props('flat dense no-caps').classes(f'cui-menu-item cui-menu-item--{action.intent}'):
                        if action.icon: _icon(ui,action.icon,size='xs')
                        ui.label(action.label)
    def open_for(self,row:Mapping[str,Any]):
        # ui.context_menu is opened client-side at the actual pointer position;
        # the AG Grid event only supplies the row payload used by its actions.
        self.row=row



class ExpandableRow(AbstractContextManager):
    def __init__(self, title: str='Details', *, open: bool=False):
        self.element=_ui().expansion(title, value=open).classes('cui-table-expanded')
    def __enter__(self): self.element.__enter__(); return self
    def __exit__(self, exc_type, exc, tb): return self.element.__exit__(exc_type, exc, tb)


class DataTable:
    def __init__(self, rows: Sequence[Mapping[str, Any]] | None = None, columns: Sequence[TableColumn] | None = None, *,
                 spec: DataTableSpec | None = None, title: str | None = None, description: str | None = None,
                 row_key: str='id', selection: SelectionMode=SelectionMode.NONE, density: TableDensity=TableDensity.COMPACT,
                 expandable: bool=False, master_detail: bool=False, bulk_actions: Sequence[BulkAction]=(),
                 row_actions: Sequence[RowAction]=(), on_select: Callable[...,Any] | None=None,
                 on_row_double_click: Callable[...,Any] | None=None, on_cell_value_changed: Callable[...,Any] | None=None,
                 on_refresh: Callable[...,Any] | None=None, show_toolbar: bool=True,
                 preferences: PreferenceService | None=None):
        if spec is None:
            if not columns: raise ValueError('columns are required when spec is not supplied')
            spec=DataTableSpec(tuple(columns), row_key=row_key, title=title, description=description, selection=selection,
                               density=density, expandable=expandable, master_detail=master_detail)
        self.preferences = preferences if preferences is not None else (_default_table_preferences() if spec.persist_state else None)
        payload: Mapping[str, Any] | None = None
        if spec.persist_state and self.preferences is not None and spec.persist_key:
            try:
                payload = self.preferences.load().table_states.get(spec.persist_key)
            except Exception:
                payload = None
        self.state = TableState.from_persisted(payload, spec.columns, default_density=spec.density, default_page_size=spec.page_size)
        if spec.persist_state:
            spec = _stateful_table_spec(spec, self.state)
        else:
            self.state = TableState.from_persisted(None, spec.columns, default_density=spec.density, default_page_size=spec.page_size)
        self.spec=spec; self.bulk_actions=tuple(bulk_actions); self.row_actions=tuple(row_actions)
        self.rows=list(rows or []); self.on_select=on_select; self.on_refresh=on_refresh; self.search=self.state.search; self.displayed_count=len(self.rows)
        self._persist_task: asyncio.Task[None] | None = None
        self._lifecycle = LifecycleScope()
        self._restoring_state=False
        self._closed=False
        self._validate_row_identities(self.rows)
        ui=_ui()
        with ui.element('section').classes('cui-table-shell') as self.container:
            if spec.title or spec.description:
                with ui.element('div').classes('cui-table-headline'):
                    with ui.element('div'):
                        if spec.title: ui.label(spec.title).classes('cui-table-title')
                        if spec.description: ui.label(spec.description).classes('cui-table-description')
            if show_toolbar and any((spec.searchable,spec.column_manager,spec.density_control,spec.export_csv,spec.refresh_enabled)):
                self.toolbar=TableToolbar(self, searchable=spec.searchable, columns=spec.column_manager,
                                          density=spec.density_control, export=spec.export_csv, refresh=spec.refresh_enabled)
            else: self.toolbar=None
            self.selection_bar=TableSelectionBar(self.bulk_actions, table=self) if self.bulk_actions else None
            self.context_menu=TableContextMenu(self.row_actions) if self.row_actions else None
            col_defs=[_column_def(c) for c in spec.columns]
            for action in self.row_actions:
                icon_html=render_icon_svg(action.icon or 'more', size='xs', label=None)
                safe_label=html.escape(action.label, quote=True)
                action_html=f'<span class="cui-table-row-action" role="button" aria-label="{safe_label}"><span class="cui-table-row-action__icon">{icon_html}</span><span>{safe_label}</span></span>'
                col_defs.append({
                    'colId': f'__action_{action.key}', 'headerName':'', 'sortable':False, 'filter':False,
                    'resizable':False, 'width': max(72, min(124, len(action.label)*8+42)), 'pinned':'right',
                    'suppressHeaderMenuButton':True, 'suppressMovable':True,
                    'cellClass':'cui-table-action-cell', ':cellRenderer': f"() => {_js_literal(action_html)}",
                })
            row_selection = None
            if spec.selection is SelectionMode.MULTIPLE: row_selection={'mode':'multiRow'}
            elif spec.selection is SelectionMode.SINGLE: row_selection={'mode':'singleRow'}
            options={
                'columnDefs': col_defs,
                'rowData': self.rows,
                # AG Grid's identity contract is a string even when the application
                # uses an integer row ordinal internally for edit/undo bookkeeping.
                ':getRowId': f"params => String(params.data[{_js_literal(spec.row_key)}])",
                'animateRows': False,
                # Smooth-scroll contract: keep enough pre-rendered rows for fast trackpad/wheel
                # movement and never defer the viewport until scrolling settles. AG Grid's
                # vertical-scroll debounce is intentionally disabled for NiceGUI Base.
                'rowBuffer': 10,
                'debounceVerticalScrollbar': False,
                'cacheQuickFilter': True,
                'suppressColumnMoveAnimation': True,
                'suppressScrollOnNewData': True,
                'enableCellTextSelection': True,
                'pagination': spec.pagination.value == 'client',
                'paginationPageSize': spec.page_size,
                'tooltipShowDelay': 350,
                'rowHeight': _DENSITY_ROWS[spec.density.value],
                'headerHeight': _DENSITY_ROWS[spec.density.value] + 2,
                'defaultColDef': {'resizable': True, 'sortable': True, 'filter': True},
                'stopEditingWhenCellsLoseFocus': True,
                'preventDefaultOnContextMenu': bool(self.row_actions),
            }
            if self.search: options['quickFilterText'] = self.search
            if self.state.filters: options['filterModel'] = _filter_model_from_specs(self.state.filters)
            if self.state.sorts:
                sort_map={item.key:(item.direction.value,index) for index,item in enumerate(self.state.sorts)}
                for column in col_defs:
                    key=column.get('field')
                    if key in sort_map:
                        column['sort'],column['sortIndex']=sort_map[key]
            if row_selection is not None:
                options['rowSelection']=row_selection
            # Small reference fixtures should end at their content; large datasets
            # retain the virtualized viewport and bounded production height.
            content_sized = len(self.rows) <= 12
            if content_sized:
                options['domLayout'] = 'autoHeight'
            table_style = 'height:auto;min-height:0' if content_sized else 'height:min(62vh,620px);min-height:360px'
            table_classes = f'{spec.classes} cui-data-table--content-sized' if content_sized else spec.classes
            self.element=ui.aggrid(options, auto_size_columns=False).classes(table_classes).style(table_style)
            with ui.element('div').classes('cui-table-footer') as self.footer:
                self.footer_label=ui.label(self._footer_text()).classes('cui-table-footer-label').props('aria-live=polite')
                ui.element('div').classes('cui-table-footer__spacer')
                self.footer_density_label=ui.label(self._density_text()).classes('cui-table-footer-density')
        # AG Grid event objects contain circular references (the grid API points
        # back to its bean context). Emit only the normalized payload needed by
        # the framework callbacks so selection/actions never create a browser
        # JSON serialization error.
        # The NiceGUI AG Grid wrapper already exposes a server-side grid API;
        # emit no raw event payload here and let _handle_selection_changed read
        # the normalized selected rows through that API. This avoids forwarding
        # AG Grid's circular context object over the websocket.
        self.element.on('selectionChanged', self._handle_selection_changed,
                        js_handler='() => emit()')
        self.element.on(
            'cellClicked', self._handle_cell_clicked,
            js_handler="e => emit({colId: e.colId || e.column?.getColId?.() || '', data: e.data || {}})",
        )
        self.element.on('cellContextMenu', self._handle_context_menu,
                        js_handler='e => emit({data: e.data || {}})')
        # These lifecycle events are used only as invalidation signals. Do not
        # forward AG Grid's raw event object (which includes circular context).
        self.element.on('filterChanged', self._sync_displayed_count, js_handler='() => emit()')
        self.element.on('filterChanged', self._schedule_persist_state, js_handler='() => emit()')
        self.element.on('sortChanged', self._schedule_persist_state, js_handler='() => emit()')
        self.element.on('columnMoved', self._schedule_persist_state, js_handler='() => emit()')
        self.element.on('columnPinned', self._schedule_persist_state, js_handler='() => emit()')
        self.element.on('columnVisible', self._schedule_persist_state, js_handler='() => emit()')
        self.element.on('columnResized', self._handle_column_resized_persist, js_handler='e => emit({finished: e.finished !== false})')
        self.element.on('paginationChanged', self._schedule_persist_state, js_handler='() => emit()')
        self.element.on('bodyScrollEnd', self._schedule_persist_state, js_handler='() => emit()')
        if on_row_double_click:
            self.element.on('rowDoubleClicked', on_row_double_click, js_handler='e => emit({data: e.data || {}})')
        if on_cell_value_changed:
            self.element.on(
                'cellValueChanged', on_cell_value_changed,
                js_handler="e => emit({data: e.data || {}, colId: e.colId || '', newValue: e.newValue, oldValue: e.oldValue, rowIndex: e.rowIndex})",
            )
        if spec.persist_state:
            _schedule_scope_task(
                self._lifecycle,
                _deferred_lifecycle_call(self._restore_runtime_state),
                name='nicegui-base-table-restore',
            )
        _register_client_delete(ui,self.aclose)
        _ACTIVE_TABLES.add(self)

    def _validate_row_identities(self, rows: Sequence[Mapping[str, Any]]) -> None:
        if self.spec.selection is SelectionMode.NONE:
            return
        seen: dict[str, Any] = {}
        for row in rows:
            key = row.get(self.spec.row_key)
            if key is None:
                raise ValueError(f'selectable DataTable rows require non-null {self.spec.row_key!r} identity')
            grid_id = str(key)
            if grid_id in seen and (type(seen[grid_id]), seen[grid_id]) != (type(key), key):
                raise ValueError(f'row identities {seen[grid_id]!r} and {key!r} collide after AG Grid string coercion')
            if grid_id in seen:
                raise ValueError(f'duplicate row identity {key!r}')
            seen[grid_id] = key

    def _footer_text(self) -> str:
        total=len(self.rows); shown=min(self.displayed_count,total)
        return f'{shown:,} of {total:,} records' if self.search or shown != total else f'{total:,} records'

    def _density_text(self) -> str:
        return f'{self.spec.density.value.title()} · {_DENSITY_ROWS[self.spec.density.value]} px'

    def _sync_footer(self) -> None:
        if self.footer_label is not None: self.footer_label.set_text(self._footer_text())
        if getattr(self,'footer_density_label',None) is not None: self.footer_density_label.set_text(self._density_text())

    async def _sync_displayed_count(self, event=None) -> None:
        try:
            count=await self.element.run_grid_method('getDisplayedRowCount')
            if count is not None: self.displayed_count=int(count)
        except Exception:
            self.displayed_count=len(self.rows)
        self._sync_footer()

    async def _handle_selection_changed(self, event=None):
        rows=await self.selected_rows()
        current_keys={row.get(self.spec.row_key) for row in self.rows}
        selected_now={row.get(self.spec.row_key) for row in rows}
        if self.spec.pagination.value == 'server':
            # Server paging only exposes one page at a time. Update selection for
            # identities on this page without discarding valid off-page choices.
            self.state.selected_keys.difference_update(current_keys)
            self.state.selected_keys.update(selected_now)
        else:
            self.state.selected_keys=set(selected_now)
        if self.selection_bar: self.selection_bar.update_count(len(rows))
        if not self._restoring_state:
            self._schedule_persist_state()
        else:
            return
        await _invoke(self.on_select, rows)

    async def _handle_cell_clicked(self, event):
        args=getattr(event,'args',{}) or {}; col=args.get('colId') or args.get('column',{}).get('colId')
        if not col or not str(col).startswith('__action_'): return
        key=str(col)[len('__action_'):]; row=args.get('data') or {}
        action=next((a for a in self.row_actions if a.key==key),None)
        if action: await _invoke(action.on_action,row)

    async def _handle_context_menu(self,event):
        if not self.context_menu:return
        row=(getattr(event,'args',{}) or {}).get('data') or {}
        self.context_menu.open_for(row)

    async def selected_rows(self): return await self.element.get_selected_rows()
    async def deselect_all(self):
        self.state.selected_keys.clear()
        result=await self.element.run_grid_method('deselectAll')
        self._schedule_persist_state()
        return result
    async def select_all(self): return await self.element.run_grid_method('selectAll')
    async def auto_size_columns(self): return await self.element.run_grid_method('autoSizeAllColumns')
    async def export(self, filename: str='table.csv'):
        """Export currently loaded rows through NiceGUI Base's hardened CSV serializer.

        This deliberately avoids AG Grid's direct CSV export because that path
        bypasses spreadsheet-formula injection protection.
        """
        csv_text = _export_csv_text(self.rows, self.spec.columns)
        result = _ui().download(csv_text.encode('utf-8-sig'), filename=filename, media_type='text/csv')
        if inspect.isawaitable(result):
            return await result
        return result

    async def set_density(self, density: TableDensity):
        self.spec=replace(self.spec,density=density)
        self.state.density=density
        row_height=_DENSITY_ROWS[density.value]
        old_classes=' '.join(f'cui-data-table--{d.value}' for d in TableDensity if d is not density)
        self.element.classes(remove=old_classes, add=f'cui-data-table--{density.value}')
        # AG Grid can update these dimensions in place. Avoiding element.update()
        # prevents a density choice from remounting/jiggling an otherwise tiny table.
        try:
            await self.element.run_grid_method('setGridOption','rowHeight',row_height)
            await self.element.run_grid_method('setGridOption','headerHeight',row_height+2)
            await self.element.run_grid_method('resetRowHeights')
            await self.element.run_grid_method('refreshHeader')
        except Exception:
            self.element.options['rowHeight']=row_height
            self.element.options['headerHeight']=row_height+2
            raise
        self._sync_footer()
        if self.toolbar is not None and self.toolbar.density_selector is not None:
            self.toolbar.density_selector.set_value(density)
        self._schedule_persist_state()

    async def set_column_visible(self, key:str, visible:bool):
        result=await self.element.run_grid_method('setColumnsVisible',[key],visible)
        if self.toolbar is not None and self.toolbar.column_manager is not None:
            self.toolbar.column_manager.set_visible(key,visible)
        self._schedule_persist_state()
        return result

    async def set_column_pinned(self, key: str, position: PinPosition = PinPosition.NONE):
        """Pin one governed column without exposing the underlying grid API."""
        if key not in {column.key for column in self.spec.columns}:
            raise KeyError(key)
        await self.element.run_grid_method('applyColumnState', {
            'state': [{'colId': key, 'pinned': None if position is PinPosition.NONE else position.value}],
            'applyOrder': False,
        })
        self._schedule_persist_state()

    async def set_filters(self, filters: Sequence[FilterExpression] = ()):
        """Apply normalized table filters and preserve them through user preferences."""
        known = {column.key for column in self.spec.columns}
        if any(item.key not in known for item in filters if isinstance(item, FilterSpec)):
            raise KeyError('filter references an unknown table column')
        self.state.filters = list(filters)
        await self.element.run_grid_method('setFilterModel', _filter_model_from_specs(filters))
        await self._sync_displayed_count()
        self._schedule_persist_state()

    async def clear_filters(self):
        return await self.set_filters(())

    async def clear_sorting(self):
        await self.element.run_grid_method('applyColumnState', {
            'state': [{'colId': column.key, 'sort': None, 'sortIndex': None} for column in self.spec.columns],
            'applyOrder': False,
        })
        self.state.sorts.clear()
        self._schedule_persist_state()

    async def reset_layout(self):
        """Restore visibility, order, widths and pinning from the declared spec."""
        state = []
        for index, column in enumerate(self.spec.columns):
            state.append({
                'colId': column.key,
                'hide': not column.visible,
                'pinned': None if column.pinned is PinPosition.NONE else column.pinned.value,
                'width': column.width,
                'sort': None,
                'sortIndex': None,
                'order': index,
            })
        await self.element.run_grid_method('applyColumnState', {'state': state, 'applyOrder': True})
        await self.clear_filters()
        self.search = ''
        self.state.search = ''
        await self.element.run_grid_method('setGridOption', 'quickFilterText', '')
        self._schedule_persist_state()

    async def set_search(self, value:str):
        self.search=value or ''
        self.state.search=self.search
        await self.element.run_grid_method('setGridOption','quickFilterText',self.search)
        await self._sync_displayed_count()
        self._schedule_persist_state()

    async def refresh(self):
        if self.on_refresh is not None:
            result=await _invoke(self.on_refresh)
            if result is not None:
                await self.replace_rows(result)
        else:
            await self.element.run_grid_method('refreshCells', {'force': False})

    async def replace_rows(self, rows: Sequence[Mapping[str,Any]]) -> None:
        """Replace client rows without remounting the AG Grid component.

        Density, filtering and server refreshes should not make a 50-row grid visibly
        jiggle. The grid API preserves DOM/column state and updates only row data.
        """
        next_rows=list(rows); self._validate_row_identities(next_rows)
        self.rows=next_rows; self.displayed_count=len(self.rows); self.element.options['rowData']=self.rows
        if self.spec.pagination.value != 'server':
            self.state.reconcile_selection(row.get(self.spec.row_key) for row in self.rows)
        await self.element.run_grid_method('setGridOption','rowData',self.rows)
        await self._restore_selection()
        self._sync_footer()
        self._schedule_persist_state()

    def update_rows(self, rows: Sequence[Mapping[str,Any]]) -> asyncio.Task[None]:
        """Schedule the canonical async row replacement without dropping its awaitable.

        Kept for source compatibility with older callers. New async code should
        ``await replace_rows(...)`` directly. The returned Task can also be awaited.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as exc:
            raise RuntimeError('DataTable.update_rows requires a running event loop; use await replace_rows(...)') from exc
        return loop.create_task(self.replace_rows(rows))

    async def _handle_column_resized_persist(self, event=None) -> None:
        args=getattr(event,'args',{}) or {}
        if args.get('finished', True):
            self._schedule_persist_state()

    def _schedule_persist_state(self, event=None) -> None:
        if self._closed or self._restoring_state or not self.spec.persist_state or self.preferences is None or not self.spec.persist_key:
            return
        if self._persist_task is not None and not self._persist_task.done():
            self._persist_task.cancel()
        try:
            self._persist_task=asyncio.get_running_loop().create_task(self._persist_state_after_delay())
        except RuntimeError:
            self._persist_task=None

    async def _persist_state_after_delay(self) -> None:
        try:
            await asyncio.sleep(.12)
            await self.persist_state()
        except asyncio.CancelledError:
            return

    async def capture_state(self) -> TableState:
        """Capture live AG Grid state without remounting the component."""
        try:
            column_states=await self.element.run_grid_method('getColumnState') or []
        except Exception:
            column_states=[]
        try:
            filter_model=await self.element.run_grid_method('getFilterModel') or {}
        except Exception:
            filter_model={}
        known={column.key for column in self.spec.columns}
        order=[]; visible=[]; widths={}; left=[]; right=[]; sorts=[]
        for item in column_states:
            key=str(item.get('colId',''))
            if key not in known:
                continue
            order.append(key)
            if not item.get('hide',False): visible.append(key)
            try:
                if item.get('width') is not None: widths[key]=int(item['width'])
            except (TypeError,ValueError):
                pass
            if item.get('pinned')=='left': left.append(key)
            elif item.get('pinned')=='right': right.append(key)
            if item.get('sort') in {'asc','desc'}:
                sorts.append((int(item.get('sortIndex') or 0),SortSpec(key,SortDirection(item['sort']))))
        sorts.sort(key=lambda pair:pair[0])
        try:
            selected=await self.selected_rows() if self.spec.selection is not SelectionMode.NONE else []
        except Exception:
            selected=[]
        current_keys={row.get(self.spec.row_key) for row in self.rows}
        selected_now={row.get(self.spec.row_key) for row in selected}
        if self.spec.pagination.value=='server':
            selected_keys=set(self.state.selected_keys); selected_keys.difference_update(current_keys); selected_keys.update(selected_now)
            page=getattr(getattr(self,'query',None),'page',self.state.page)
            page_size=getattr(getattr(self,'query',None),'page_size',self.spec.page_size)
        else:
            selected_keys=selected_now
            try: page=int(await self.element.run_grid_method('paginationGetCurrentPage'))+1
            except Exception: page=self.state.page
            try: page_size=int(await self.element.run_grid_method('paginationGetPageSize'))
            except Exception: page_size=self.spec.page_size
        try: scroll=max(0,int(await self.element.run_grid_method('getFirstDisplayedRowIndex') or 0))
        except Exception: scroll=self.state.scroll_row_index
        self.state=TableState(
            density=self.spec.density, search=self.search, selected_keys=selected_keys,
            expanded_keys=set(self.state.expanded_keys), visible_columns=visible or [c.key for c in self.spec.columns if c.visible],
            column_order=order or [c.key for c in self.spec.columns], column_widths=widths,
            pinned_left=left, pinned_right=right, sorts=[item for _,item in sorts],
            filters=_filter_specs_from_grid_model(filter_model), page=max(1,int(page)), page_size=max(1,int(page_size)),
            scroll_row_index=scroll,
        )
        if self.spec.pagination.value!='server':
            self.state.reconcile_selection(row.get(self.spec.row_key) for row in self.rows)
        return self.state

    async def persist_state(self) -> TableState:
        state=await self.capture_state()
        if self.preferences is not None and self.spec.persist_key:
            self.preferences.save_table_state(self.spec.persist_key,state.to_persisted(self.spec.columns))
        return state

    async def _restore_selection(self) -> None:
        if self.spec.selection is SelectionMode.NONE or not self.state.selected_keys:
            return
        selected={(type(key),key) for key in self.state.selected_keys}
        for row in self.rows:
            key=row.get(self.spec.row_key)
            if (type(key),key) in selected:
                try:
                    await self.element.run_row_method(str(key),'setSelected',True,False)
                except Exception:
                    continue

    async def _restore_runtime_state(self) -> None:
        if self._closed:
            return
        self._restoring_state=True
        try:
            if self.spec.pagination.value!='server':
                self.state.reconcile_selection(row.get(self.spec.row_key) for row in self.rows)
            if self.state.filters:
                await self.element.run_grid_method('setFilterModel',_filter_model_from_specs(self.state.filters))
            if self.search:
                await self.element.run_grid_method('setGridOption','quickFilterText',self.search)
            if self.spec.pagination.value=='client' and self.state.page>1:
                await self.element.run_grid_method('paginationGoToPage',self.state.page-1)
            await self._restore_selection()
            if self.state.scroll_row_index>0:
                await self.element.run_grid_method('ensureIndexVisible',self.state.scroll_row_index,'top')
            await self._sync_displayed_count()
        except Exception:
            # Persisted UI state is convenience data. A stale browser/grid contract
            # must safely reset rather than prevent the table from rendering.
            self.state=TableState.from_persisted(None,self.spec.columns,default_density=self.spec.density,default_page_size=self.spec.page_size)
        finally:
            self._restoring_state=False

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed=True
        await self._lifecycle.aclose()
        if self._persist_task is not None and not self._persist_task.done():
            self._persist_task.cancel()
            try:
                await self._persist_task
            except asyncio.CancelledError:
                pass
        self._persist_task = None
        _ACTIVE_TABLES.discard(self)


class ServerDataTable(DataTable):
    """Server-paged table with cancellation, coalescing, retry and page cache."""
    def __init__(self, columns: Sequence[TableColumn], *, fetch: Callable[[TableQuery], Any],
                 spec: ServerDataTableSpec | None=None, query: TableQuery | None=None, **kwargs):
        if fetch is None: raise ValueError('ServerDataTable requires fetch(query)')
        spec=spec or ServerDataTableSpec(tuple(columns), title=kwargs.pop('title', None), description=kwargs.pop('description', None),
                                         selection=kwargs.pop('selection', SelectionMode.NONE), density=kwargs.pop('density', TableDensity.COMPACT))
        self.fetch=fetch; self.query=query or TableQuery(page_size=spec.page_size)
        self.total=0; self.loading=False
        self.last_error: BaseException | None = None
        self._last_success_monotonic: float | None = None
        self.stale = False
        retry=RetryPolicy(attempts=spec.retry_attempts,base_delay_seconds=spec.retry_base_delay_seconds,
                          max_delay_seconds=max(spec.retry_base_delay_seconds, min(2.0, spec.retry_base_delay_seconds * 4)),jitter=0.0)
        self._requests=LatestRequestController(
            timeout=spec.request_timeout_seconds,
            retry_policy=retry if spec.retry_attempts > 1 else None,
            cache_size=spec.cache_pages,
            cache_ttl_seconds=spec.cache_ttl_seconds,
            cancel_previous=spec.cancel_stale_requests,
        )
        super().__init__([], spec=spec, on_refresh=self._refresh_from_toolbar, **kwargs)
        if query is None:
            self.query=TableQuery(
                page=self.state.page, page_size=self.spec.page_size, search=self.state.search,
                sorts=tuple(self.state.sorts), filters=tuple(self.state.filters),
            )
        # AG Grid filter/sort changes are translated back into the server query.
        self.element.on('sortChanged', self._grid_query_changed, js_handler='() => emit()')
        self.element.on('filterChanged', self._grid_query_changed, js_handler='() => emit()')
        ui=_ui()
        with self.footer:
            self.page_label=ui.label('Page 1').classes('cui-table-page-label')
            prev=ui.button(on_click=self.previous_page).props('flat round aria-label="Previous page"').classes('cui-icon-button')
            with prev: _icon(ui,'arrow-left',label='Previous page')
            nxt=ui.button(on_click=self.next_page).props('flat round aria-label="Next page"').classes('cui-icon-button')
            with nxt: _icon(ui,'arrow-right',label='Next page')
        _schedule_scope_task(
            self._lifecycle,
            _deferred_lifecycle_call(self.refresh),
            name='nicegui-base-server-table-initial-refresh',
        )

    @property
    def is_stale(self) -> bool:
        if self.stale:
            return True
        threshold = self.spec.stale_after_seconds
        if threshold is None or self._last_success_monotonic is None:
            return False
        return (time.monotonic() - self._last_success_monotonic) >= threshold

    def _footer_text(self) -> str:
        if self.loading and not self.rows:
            return 'Loading…'
        if self.last_error is not None:
            return f'Stale data · {self.total:,} records' if self.rows else self.spec.error_message
        if not self.rows and not self.loading:
            return self.spec.empty_message
        prefix = 'Stale data · ' if self.is_stale else ''
        return f'{prefix}{self.total:,} records'

    async def _refresh_from_toolbar(self): return await self.refresh(force=True)

    async def set_search(self, value:str):
        next_search=value or ''
        if next_search != self.query.search:
            self.state.selected_keys.clear()
        self.search=next_search; self.state.search=next_search
        self.query=replace(self.query,search=next_search,page=1)
        self._schedule_persist_state()
        return await self.refresh()

    async def set_query(self, query:TableQuery): self.query=query; return await self.refresh()
    async def set_page(self,page:int): self.query=replace(self.query,page=max(1,page)); return await self.refresh()
    async def previous_page(self): return await self.set_page(max(1,self.query.page-1))
    async def next_page(self):
        pages=max(1,(self.total+self.query.page_size-1)//self.query.page_size)
        return await self.set_page(min(pages,self.query.page+1))

    async def _grid_query_changed(self, event=None):
        try:
            states=await self.element.run_grid_method('getColumnState') or []
            model=await self.element.run_grid_method('getFilterModel') or {}
        except Exception:
            return
        sorts=[]
        for state in states:
            if state.get('sort') in {'asc','desc'}:
                sorts.append(SortSpec(state.get('colId'),SortDirection(state['sort'])))
        filters=_filter_specs_from_grid_model(model)
        if tuple(filters) != self.query.filters:
            # A server-side filter changes the result universe. Preserve no
            # off-page selection whose identity can no longer be proven valid.
            self.state.selected_keys.clear()
        self.query=replace(self.query,sorts=tuple(sorts),filters=tuple(filters),page=1)
        await self.refresh()

    async def refresh(self, query:TableQuery | None=None, *, force:bool=False):
        if query is not None: self.query=query
        request_query=self.query
        request_key=_table_query_key(request_query)
        self.loading=True
        self._sync_footer()
        try:
            result=await self._requests.run(
                request_key,
                lambda: _invoke(self.fetch,request_query),
                refresh=force,
                retry_if=_retry_server_read,
            )
            if result is None: return None
            if isinstance(result,TableResult): normalized=result
            elif isinstance(result,tuple) and len(result)==2:
                normalized=TableResult(tuple(result[0]),int(result[1]),request_query.page,request_query.page_size)
            else:
                raise TypeError('fetch(query) must return TableResult or (rows, total)')
            next_rows=list(normalized.rows); self._validate_row_identities(next_rows)
            self.total=normalized.total; self.rows=next_rows; self.displayed_count=len(self.rows)
            self.last_error=None; self.stale=False; self._last_success_monotonic=time.monotonic()
            self.element.options['rowData']=self.rows
            await self.element.run_grid_method('setGridOption','rowData',self.rows)
            await self._restore_selection()
            self._sync_footer()
            if hasattr(self,'page_label'): self.page_label.set_text(f'Page {normalized.page} of {normalized.page_count}')
            self.state.page=normalized.page; self.state.page_size=normalized.page_size
            self._schedule_persist_state()
            return normalized
        except Exception as exc:
            self.last_error=exc; self.stale=bool(self.rows)
            self._sync_footer()
            raise
        finally:
            if not self._requests.running:
                self.loading=False
                self._sync_footer()

    async def aclose(self) -> None:
        if getattr(self, '_closed', False):
            return
        await self._requests.aclose()
        await super().aclose()
        await super().aclose()


class EditableTable(DataTable):
    """Editable grid with per-cell save ownership and deterministic rollback.

    Each cell owns a monotonically increasing revision. An older save completion can
    never overwrite or roll back a newer edit to the same cell. Pending state is
    carried as row metadata for CSS-only rendering, avoiding custom DOM renderers.
    """
    _PENDING_FIELDS_KEY='__cui_pending_fields'

    def __init__(self, rows: Sequence[Mapping[str,Any]], columns: Sequence[TableColumn], *, spec: EditableTableSpec | None=None,
                 validate_edit: Callable[[Mapping[str,Any],str,Any], str | None] | None=None,
                 save_edit: Callable[[Mapping[str,Any],str,Any], Any] | None=None, **kwargs):
        spec=spec or EditableTableSpec(tuple(columns), title=kwargs.pop('title', None), description=kwargs.pop('description', None))
        self.validate_edit=validate_edit; self.save_edit=save_edit
        self._edit_revisions: dict[tuple[type,Any,str],int]={}
        super().__init__(rows, spec=spec, **kwargs)
        self.element.on('cellValueChanged', self._handle_edit)

    def _cell_identity(self, row: Mapping[str,Any], key: str) -> tuple[type,Any,str]:
        row_id=row.get(self.spec.row_key)
        return (type(row_id),row_id,str(key))

    def _find_row_index(self, row_id: Any) -> int | None:
        identity=(type(row_id),row_id)
        for index,current in enumerate(self.rows):
            candidate=current.get(self.spec.row_key)
            if (type(candidate),candidate)==identity:
                return index
        return None

    def _with_pending(self, row: Mapping[str,Any], key: str, pending: bool) -> dict[str,Any]:
        result=dict(row); fields={str(item) for item in result.get(self._PENDING_FIELDS_KEY,())}
        if pending: fields.add(str(key))
        else: fields.discard(str(key))
        if fields: result[self._PENDING_FIELDS_KEY]=sorted(fields)
        else: result.pop(self._PENDING_FIELDS_KEY,None)
        return result

    @classmethod
    def _public_edit_row(cls, row: Mapping[str,Any]) -> dict[str,Any]:
        result=dict(row); result.pop(cls._PENDING_FIELDS_KEY,None); return result

    @staticmethod
    def _edit_error_message(exc: BaseException, key: str) -> str:
        field_errors=getattr(exc,'field_errors',None)
        if isinstance(field_errors,Mapping) and key in field_errors:
            value=field_errors[key]
            if isinstance(value,(list,tuple)): return '; '.join(str(item) for item in value)
            return str(value)
        return str(exc) or type(exc).__name__

    @staticmethod
    def _event_row_index(args: Mapping[str,Any]) -> int | None:
        value=args.get('rowIndex')
        if value is None and isinstance(args.get('node'),Mapping): value=args['node'].get('rowIndex')
        try: return int(value) if value is not None else None
        except (TypeError,ValueError): return None

    async def _set_grid_row(self, row: Mapping[str,Any]) -> None:
        row_id=row.get(self.spec.row_key)
        await self.element.run_row_method(str(row_id),'setData',dict(row))

    async def _restore_edit_focus(self, row_index: int | None, key: str) -> None:
        if not self.spec.restore_focus_on_error or row_index is None: return
        try: await self.element.run_grid_method('setFocusedCell',row_index,key)
        except Exception:
            return

    async def _handle_edit(self,event):
        args=getattr(event,'args',{}) or {}; event_row=dict(args.get('data') or {}); key=args.get('colId'); new=args.get('newValue'); old=args.get('oldValue')
        if not key: return
        row_id=event_row.get(self.spec.row_key); index=self._find_row_index(row_id)
        if index is None: return
        cell=self._cell_identity(event_row,str(key)); revision=self._edit_revisions.get(cell,0)+1; self._edit_revisions[cell]=revision
        row_index=self._event_row_index(args)
        base=dict(self.rows[index]); candidate=dict(event_row or base); candidate[key]=new
        pending=self._with_pending(candidate,str(key),True)
        self.rows[index]=pending
        await self._set_grid_row(self._with_pending({**pending, key:(old if self.spec.commit_mode is EditCommitMode.CONFIRMED else new)},str(key),True))
        try:
            error=self.validate_edit(self._public_edit_row(candidate),str(key),new) if self.validate_edit else None
            if inspect.isawaitable(error): error=await error
            if error: raise ValueError(str(error))
            await _invoke(self.save_edit,self._public_edit_row(candidate),str(key),new)
        except Exception as exc:
            if self._edit_revisions.get(cell)!=revision:
                return
            rollback=self._with_pending({**base,key:old},str(key),False); self.rows[index]=rollback
            await self._set_grid_row(rollback)
            await self._restore_edit_focus(row_index,str(key))
            from nicegui_base.integrations.nicegui_feedback_runtime import show_company_toast
            show_company_toast(_ui(), self._edit_error_message(exc,str(key)), intent='danger')
            return
        if self._edit_revisions.get(cell)!=revision:
            return
        committed=self._with_pending(candidate,str(key),False); self.rows[index]=committed
        await self._set_grid_row(committed)


class MasterDetailTable(DataTable):
    """Community-compatible master/detail: row drilldown opens a NiceGUI Base DetailDrawer."""
    def __init__(self, rows, columns, *, detail_renderer: Callable[[Mapping[str,Any]],Any], detail_title: Callable[[Mapping[str,Any]],str] | None=None, **kwargs):
        if detail_renderer is None: raise ValueError('MasterDetailTable requires detail_renderer')
        self.detail_renderer=detail_renderer; self.detail_title=detail_title
        kwargs['expandable']=True; kwargs['master_detail']=True
        super().__init__(rows, columns, on_row_double_click=self._open_detail, **kwargs)

    def _open_detail(self,event):
        from nicegui_base.integrations.nicegui_interactions import DetailDrawer
        row=(getattr(event,'args',{}) or {}).get('data') or {}
        title=self.detail_title(row) if self.detail_title else str(row.get(self.spec.row_key,'Details'))
        with DetailDrawer(title): self.detail_renderer(row)


class TablePresetSelector:
    """Named engineering views rendered as a compact Company menu, not a stock select."""
    def __init__(self, presets: Sequence[TablePreset], *, table: DataTable | None=None, on_select:Callable[[TablePreset],Any] | None=None):
        self.presets=tuple(presets); self.table=table; self.element=None; self.label=None; self.active:TablePreset | None=None
        if table is not None and self.presets:
            ui=_ui(); self.active=self.presets[0]
            button=ui.button().props('flat no-caps aria-label="Table view"').classes('cui-table-tool-button cui-table-view-button')
            with button:
                _icon(ui,'grid',size='xs')
                self.label=ui.label(self.active.name).classes('cui-table-tool-button__label')
                with ui.menu().classes('cui-menu cui-table-view-menu cui-overlay-surface cui-overlay-surface--popover'):
                    ui.label('Saved views').classes('cui-menu-heading')
                    for preset in self.presets:
                        async def choose(e=None, p=preset):
                            await self.apply(p); await _invoke(on_select,p)
                        with ui.button(on_click=choose).props('flat no-caps').classes('cui-menu-item cui-table-view-option'):
                            ui.label(preset.name)
                            ui.label(preset.density.value.title()).classes('cui-table-view-option__meta')
            self.element=button

    async def apply(self,preset:TablePreset):
        if self.table is None:return
        self.active=preset
        if self.label is not None:self.label.set_text(preset.name)
        await self.table.set_density(preset.density)
        visible=set(preset.visible_columns)
        if visible:
            for c in self.table.spec.columns: await self.table.set_column_visible(c.key,c.key in visible)
        # Pinning/sort state are applied in one Grid API transaction so view changes do not jiggle columns.
        sort_map={item.key:item.direction.value for item in preset.sorts}
        state=[]
        for c in self.table.spec.columns:
            item={'colId':c.key}
            if c.key in preset.pinned_left:item['pinned']='left'
            elif c.key in preset.pinned_right:item['pinned']='right'
            elif preset.pinned_left or preset.pinned_right:item['pinned']=None
            if c.key in sort_map:item['sort']=sort_map[c.key]
            elif preset.sorts:item['sort']=None
            state.append(item)
        if preset.pinned_left or preset.pinned_right or preset.sorts:
            await self.table.element.run_grid_method('applyColumnState',{'state':state,'applyOrder':False})
        await self.table.set_filters(preset.filters)


__all__=[
    'DataTable','ServerDataTable','EditableTable','MasterDetailTable','TableToolbar','TableDensitySelector','TableColumnManager',
    'TableSelectionBar','TableRowActions','TableContextMenu','ExpandableRow','TablePresetSelector','ConditionalCellFormatter','StatusCell','SparklineCell','apply_all_table_density'
]
