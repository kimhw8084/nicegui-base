from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from enum import Enum
from collections.abc import Collection
from typing import Any, Callable, Iterable, Mapping, Sequence, TypeAlias


class ColumnKind(str, Enum):
    TEXT='text'; INTEGER='integer'; FLOAT='float'; PERCENT='percent'; DATE='date'; DATETIME='datetime'; DURATION='duration'
    STATUS='status'; BOOLEAN='boolean'; LINK='link'; ACTION='action'; SPARKLINE='sparkline'; CUSTOM='custom'

class TableDensity(str, Enum):
    COMFORTABLE='comfortable'; COMPACT='compact'; DENSE='dense'

class SelectionMode(str, Enum):
    NONE='none'; SINGLE='single'; MULTIPLE='multiple'

class PaginationMode(str, Enum):
    CLIENT='client'; SERVER='server'; INFINITE='infinite'

class SortDirection(str, Enum):
    ASC='asc'; DESC='desc'

class FilterOperator(str, Enum):
    CONTAINS='contains'; EQUALS='equals'; NOT_EQUALS='not_equals'; STARTS_WITH='starts_with'; ENDS_WITH='ends_with'
    GT='gt'; GTE='gte'; LT='lt'; LTE='lte'; IN='in'; NOT_IN='not_in'; BETWEEN='between'; IS_EMPTY='is_empty'; IS_NOT_EMPTY='is_not_empty'
    NOT_CONTAINS='not_contains'

class PinPosition(str, Enum):
    LEFT='left'; RIGHT='right'; NONE='none'

class EditCommitMode(str, Enum):
    OPTIMISTIC='optimistic'; CONFIRMED='confirmed'


class ExportDisabledError(RuntimeError):
    """Raised when an application attempts export from a restricted table."""


@dataclass(frozen=True, slots=True)
class ActionState:
    """The normalized, fail-closed policy result shared by table action surfaces."""

    visible: bool = True
    enabled: bool = True
    disabled_reason: str | None = None


def _evaluate_predicate(predicate: Callable[..., Any] | None, value: Any, *, default: bool) -> tuple[bool, str | None]:
    if predicate is None:
        return default, None
    try:
        result = bool(predicate(value))
    except Exception:
        # A policy callback is an authorization boundary. A broken predicate must
        # not accidentally expose or invoke the action.
        return False, 'Action policy could not be evaluated.'
    return result, None

@dataclass(frozen=True, slots=True)
class ConditionalRule:
    operator: FilterOperator
    value: Any | None = None
    value2: Any | None = None
    intent: str = 'neutral'

@dataclass(frozen=True, slots=True)
class TableColumn:
    key: str
    label: str
    kind: ColumnKind = ColumnKind.TEXT
    width: int | None = None
    min_width: int = 80
    max_width: int | None = None
    sortable: bool = True
    filterable: bool = True
    resizable: bool = True
    visible: bool = True
    pinned: PinPosition = PinPosition.NONE
    align: str | None = None
    decimals: int | None = None
    unit: str | None = None
    tooltip: str | None = None
    editable: bool = False
    required: bool = False
    rules: tuple[ConditionalRule, ...] = ()
    priority: str = 'normal'
    status_map: Mapping[str, str] = field(default_factory=dict)
    # Editing metadata stays semantic; integrations translate it to the
    # installed grid/editor implementation.
    editor: str | None = None
    choices: tuple[Any, ...] = ()
    minimum: float | int | None = None
    maximum: float | int | None = None
    step: float | int | None = None
    placeholder: str | None = None

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError('TableColumn requires non-empty key and label')
        if self.min_width < 40:
            raise ValueError('min_width must be >= 40')
        if self.width is not None and self.width < self.min_width:
            raise ValueError('width cannot be below min_width')
        if self.max_width is not None and self.max_width < self.min_width:
            raise ValueError('max_width cannot be below min_width')
        if self.decimals is not None and not 0 <= self.decimals <= 12:
            raise ValueError('decimals must be between 0 and 12')
        if self.align not in (None, 'left', 'center', 'right'):
            raise ValueError('align must be left, center, right, or None')
        if self.priority not in {'high', 'normal', 'low'}:
            raise ValueError('priority must be high, normal, or low')
        allowed_intents = {'neutral', 'info', 'success', 'warning', 'danger'}
        if any(intent not in allowed_intents for intent in self.status_map.values()):
            raise ValueError('status_map contains unsupported intent')
        if self.editor is not None and self.editor not in {'text', 'number', 'select', 'boolean', 'date', 'datetime'}:
            raise ValueError('editor must be a semantic text, number, select, boolean, date, or datetime editor')
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError('minimum cannot exceed maximum')
        if self.step is not None and self.step <= 0:
            raise ValueError('step must be positive')

    def editor_spec(self) -> dict[str, Any]:
        """Return the normalized semantic editor contract for this column."""
        if self.editor is not None:
            kind = self.editor
        elif self.kind in {ColumnKind.INTEGER, ColumnKind.FLOAT, ColumnKind.PERCENT, ColumnKind.DURATION}:
            kind = 'number'
        elif self.kind is ColumnKind.BOOLEAN:
            kind = 'boolean'
        elif self.kind is ColumnKind.STATUS or self.choices:
            kind = 'select'
        elif self.kind is ColumnKind.DATE:
            kind = 'date'
        elif self.kind is ColumnKind.DATETIME:
            kind = 'datetime'
        else:
            kind = 'text'
        choices = self.choices
        if kind == 'select' and not choices and self.status_map:
            choices = tuple(self.status_map)
        if kind == 'boolean' and not choices:
            choices = (True, False)
        return {
            'kind': kind,
            'choices': tuple(choices),
            'minimum': self.minimum,
            'maximum': self.maximum,
            'step': self.step,
            'placeholder': self.placeholder,
        }

    @property
    def effective_align(self) -> str:
        if self.align: return self.align
        if self.kind in {ColumnKind.INTEGER, ColumnKind.FLOAT, ColumnKind.PERCENT, ColumnKind.DURATION}: return 'right'
        if self.kind in {ColumnKind.BOOLEAN, ColumnKind.STATUS, ColumnKind.ACTION}: return 'center'
        return 'left'

@dataclass(frozen=True, slots=True)
class SortSpec:
    key: str
    direction: SortDirection = SortDirection.ASC

class FilterLogic(str, Enum):
    AND='and'; OR='or'

@dataclass(frozen=True, slots=True)
class FilterSpec:
    key: str
    operator: FilterOperator
    value: Any | None = None
    value2: Any | None = None

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError('FilterSpec.key cannot be empty')
        if self.operator in {FilterOperator.IN, FilterOperator.NOT_IN}:
            if isinstance(self.value, (str, bytes, bytearray, Mapping)) or not isinstance(self.value, Collection):
                raise TypeError(f'{self.operator.value} requires a non-string collection')
        if self.operator is FilterOperator.BETWEEN and (self.value is None or self.value2 is None):
            raise ValueError('between requires value and value2')
        if self.operator not in {FilterOperator.IS_EMPTY, FilterOperator.IS_NOT_EMPTY} and self.value is None:
            raise ValueError(f'{self.operator.value} requires value')

@dataclass(frozen=True, slots=True)
class FilterGroup:
    logic: FilterLogic
    filters: tuple['FilterExpression', ...]

    def __post_init__(self) -> None:
        if not self.filters:
            raise ValueError('FilterGroup requires at least one child filter')

FilterExpression: TypeAlias = FilterSpec | FilterGroup

def _filter_to_persisted(item: FilterExpression, safe_value: Callable[[Any], Any]) -> dict[str, Any]:
    if isinstance(item, FilterGroup):
        return {'kind':'group','logic':item.logic.value,'filters':[_filter_to_persisted(child, safe_value) for child in item.filters]}
    return {'kind':'filter','key':item.key,'operator':item.operator.value,'value':safe_value(item.value),'value2':safe_value(item.value2)}

def _filter_from_persisted(item: Mapping[str, Any], known: set[str], filterable: Mapping[str, bool]) -> FilterExpression | None:
    if item.get('kind') == 'group' or ('filters' in item and 'logic' in item):
        try: logic = FilterLogic(str(item.get('logic','and')).lower())
        except ValueError: return None
        children=[]
        for raw in item.get('filters', ()) or ():
            if isinstance(raw, Mapping):
                child=_filter_from_persisted(raw, known, filterable)
                if child is not None: children.append(child)
        return FilterGroup(logic, tuple(children)) if children else None
    key=str(item.get('key',''))
    if key not in known or not filterable.get(key, False): return None
    try:
        operator=FilterOperator(item.get('operator'))
        return FilterSpec(key, operator, item.get('value'), item.get('value2'))
    except (TypeError, ValueError):
        return None

@dataclass(frozen=True, slots=True)
class TableQuery:
    page: int = 1
    page_size: int = 50
    search: str = ''
    sorts: tuple[SortSpec, ...] = ()
    filters: tuple[FilterExpression, ...] = ()

    def __post_init__(self) -> None:
        if self.page < 1: raise ValueError('page must be >= 1')
        if self.page_size < 1 or self.page_size > 10000: raise ValueError('page_size must be 1..10000')

@dataclass(frozen=True, slots=True)
class TableResult:
    rows: tuple[Mapping[str, Any], ...]
    total: int
    page: int = 1
    page_size: int = 50

    @property
    def page_count(self) -> int:
        return max(1, (self.total + self.page_size - 1) // self.page_size)


@dataclass(frozen=True, slots=True)
class TableViewSnapshot:
    """Normalized client-visible table state for linked summaries and charts."""
    displayed_count: int
    total_count: int
    visible_rows: tuple[Mapping[str, Any], ...] = ()
    selected_keys: frozenset[Any] = frozenset()
    search: str = ''
    filters: tuple[FilterExpression, ...] = ()
    sorts: tuple[SortSpec, ...] = ()

@dataclass(frozen=True, slots=True)
class TablePreset:
    name: str
    visible_columns: tuple[str, ...] = ()
    column_order: tuple[str, ...] = ()
    column_widths: Mapping[str, int] = field(default_factory=dict)
    pinned_left: tuple[str, ...] = ()
    pinned_right: tuple[str, ...] = ()
    density: TableDensity = TableDensity.COMPACT
    sorts: tuple[SortSpec, ...] = ()
    filters: tuple[FilterExpression, ...] = ()
    search: str = ''
    page: int = 1
    page_size: int | None = None
    scroll_row_index: int = 0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError('TablePreset requires a non-empty name')
        if self.page < 1:
            raise ValueError('TablePreset page must be >= 1')
        if self.page_size is not None and self.page_size < 1:
            raise ValueError('TablePreset page_size must be >= 1')
        if self.scroll_row_index < 0:
            raise ValueError('TablePreset scroll_row_index must be >= 0')

@dataclass(slots=True)
class TableState:
    density: TableDensity = TableDensity.COMPACT
    search: str = ''
    selected_keys: set[Any] = field(default_factory=set)
    expanded_keys: set[Any] = field(default_factory=set)
    visible_columns: list[str] = field(default_factory=list)
    column_order: list[str] = field(default_factory=list)
    column_widths: dict[str, int] = field(default_factory=dict)
    pinned_left: list[str] = field(default_factory=list)
    pinned_right: list[str] = field(default_factory=list)
    sorts: list[SortSpec] = field(default_factory=list)
    filters: list[FilterExpression] = field(default_factory=list)
    page: int = 1
    page_size: int = 50
    scroll_row_index: int = 0

    @staticmethod
    def _safe_value(value: Any) -> Any:
        """Return a JSON-safe value or ``None`` for unsupported filter payloads.

        NiceGUI user storage is JSON-backed. Silently stringifying arbitrary
        domain objects could restore a filter with different semantics, so an
        unsupported value is intentionally reset instead of being guessed.
        """
        try:
            json.dumps(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return value

    @staticmethod
    def _safe_row_key(value: Any) -> Any | None:
        return value if value is None or isinstance(value, (str, int, float, bool)) else None

    def reconcile_selection(self, valid_keys: Iterable[Any]) -> set[Any]:
        """Drop selections whose exact row identity no longer exists.

        Exact equality/type semantics are deliberate: selection must never
        migrate from row ``1`` to row ``"1"`` after a refresh/schema change.
        """
        valid = {(type(key), key) for key in valid_keys if self._safe_row_key(key) is not None}
        previous = set(self.selected_keys)
        self.selected_keys = {key for key in previous if (type(key), key) in valid}
        return previous - self.selected_keys

    def to_persisted(self, columns: Sequence[TableColumn] | None = None) -> dict[str, Any]:
        selected = [self._safe_row_key(key) for key in self.selected_keys]
        expanded = [self._safe_row_key(key) for key in self.expanded_keys]
        return {
            'version': 2,
            'column_keys': [column.key for column in columns] if columns is not None else list(self.column_order),
            'density': self.density.value,
            'search': self.search,
            'selected_keys': [key for key in selected if key is not None],
            'expanded_keys': [key for key in expanded if key is not None],
            'visible_columns': list(self.visible_columns),
            'column_order': list(self.column_order),
            'column_widths': dict(self.column_widths),
            'pinned_left': list(self.pinned_left),
            'pinned_right': list(self.pinned_right),
            'sorts': [{'key': s.key, 'direction': s.direction.value} for s in self.sorts],
            'filters': [_filter_to_persisted(item, self._safe_value) for item in self.filters],
            'page': max(1, int(self.page)),
            'page_size': self.page_size,
            'scroll_row_index': max(0, int(self.scroll_row_index)),
        }

    @classmethod
    def from_persisted(cls, payload: Mapping[str, Any] | None, columns: Sequence[TableColumn], *,
                       default_density: TableDensity = TableDensity.COMPACT, default_page_size: int = 50) -> 'TableState':
        """Load persisted state while safely migrating column-schema changes."""
        data = dict(payload or {})
        known = [column.key for column in columns]
        known_set = set(known)
        by_key = {column.key: column for column in columns}
        previous_schema_source = data.get('column_keys') or data.get('column_order') or known
        previous_schema = {str(key) for key in previous_schema_source if str(key) in known_set}

        try: density = TableDensity(data.get('density', default_density.value))
        except (TypeError, ValueError): density = default_density

        stored_visible = [str(key) for key in data.get('visible_columns', ()) if str(key) in known_set]
        if stored_visible:
            visible = list(dict.fromkeys(stored_visible))
            # Newly introduced columns inherit their declared visibility rather than
            # being accidentally hidden by an older persisted schema.
            visible.extend(column.key for column in columns if column.visible and column.key not in previous_schema and column.key not in visible)
        else:
            visible = [column.key for column in columns if column.visible]

        stored_order = [str(key) for key in data.get('column_order', ()) if str(key) in known_set]
        order = list(dict.fromkeys((*stored_order, *known)))

        widths: dict[str, int] = {}
        for key, raw in dict(data.get('column_widths', {}) or {}).items():
            key = str(key)
            if key not in known_set:
                continue
            try: width = int(raw)
            except (TypeError, ValueError): continue
            column = by_key[key]
            width = max(column.min_width, width)
            if column.max_width is not None: width = min(column.max_width, width)
            widths[key] = width

        def pins(name: str, position: PinPosition) -> list[str]:
            stored = [str(key) for key in data.get(name, ()) if str(key) in known_set]
            values = list(dict.fromkeys(stored))
            for column in columns:
                if column.pinned is position and column.key not in previous_schema and column.key not in values:
                    values.append(column.key)
            return values

        pinned_left = pins('pinned_left', PinPosition.LEFT)
        left_set = set(pinned_left)
        pinned_right = [key for key in pins('pinned_right', PinPosition.RIGHT) if key not in left_set]

        sorts: list[SortSpec] = []
        seen_sort: set[str] = set()
        for item in data.get('sorts', ()) or ():
            if not isinstance(item, Mapping): continue
            key = str(item.get('key', ''))
            if key not in known_set or key in seen_sort or not by_key[key].sortable: continue
            try: direction = SortDirection(item.get('direction', 'asc'))
            except (TypeError, ValueError): continue
            seen_sort.add(key); sorts.append(SortSpec(key, direction))

        filters: list[FilterExpression] = []
        filterable = {key: column.filterable for key, column in by_key.items()}
        for item in data.get('filters', ()) or ():
            if not isinstance(item, Mapping): continue
            parsed = _filter_from_persisted(item, known_set, filterable)
            if parsed is not None: filters.append(parsed)

        selected = {key for raw in data.get('selected_keys', ()) or () if (key := cls._safe_row_key(raw)) is not None}
        expanded = {key for raw in data.get('expanded_keys', ()) or () if (key := cls._safe_row_key(raw)) is not None}
        try: page = max(1, int(data.get('page', 1)))
        except (TypeError, ValueError): page = 1
        try: page_size = int(data.get('page_size', default_page_size))
        except (TypeError, ValueError): page_size = default_page_size
        if not 1 <= page_size <= 10000: page_size = default_page_size
        try: scroll = max(0, int(data.get('scroll_row_index', 0)))
        except (TypeError, ValueError): scroll = 0

        return cls(
            density=density, search=str(data.get('search', '') or ''), selected_keys=selected, expanded_keys=expanded,
            visible_columns=visible, column_order=order, column_widths=widths,
            pinned_left=pinned_left, pinned_right=pinned_right, sorts=sorts, filters=filters,
            page=page, page_size=page_size, scroll_row_index=scroll,
        )

@dataclass(frozen=True, slots=True)
class DataTableSpec:
    columns: tuple[TableColumn, ...]
    row_key: str = 'id'
    title: str | None = None
    description: str | None = None
    density: TableDensity = TableDensity.COMPACT
    selection: SelectionMode = SelectionMode.NONE
    pagination: PaginationMode = PaginationMode.CLIENT
    page_size: int = 50
    page_size_options: tuple[int, ...] = (25, 50, 100, 250)
    searchable: bool = True
    column_manager: bool = True
    density_control: bool = True
    export_csv: bool = True
    export_enabled: bool = True
    copy_enabled: bool = True
    refresh_enabled: bool = True
    persist_state: bool = True
    persist_key: str | None = None
    striped: bool = False
    sticky_header: bool = True
    expandable: bool = False
    master_detail: bool = False
    editable: bool = False
    empty_message: str = 'No records'
    error_message: str = 'Unable to load records'

    def __post_init__(self) -> None:
        if not self.columns: raise ValueError('DataTableSpec requires at least one column')
        keys=[c.key for c in self.columns]
        if len(keys) != len(set(keys)): raise ValueError('Column keys must be unique')
        if self.page_size < 1: raise ValueError('page_size must be >= 1')
        if self.persist_state and not self.persist_key:
            object.__setattr__(self, 'persist_key', f'table:{self.title or self.row_key}')
        if self.master_detail and not self.expandable:
            object.__setattr__(self, 'expandable', True)

    @property
    def classes(self) -> str:
        striped = ' cui-data-table--striped' if self.striped else ''
        return f'cui-data-table cui-data-table--{self.density.value}{striped}'

@dataclass(frozen=True, slots=True)
class ServerDataTableSpec(DataTableSpec):
    pagination: PaginationMode = PaginationMode.SERVER
    cache_pages: int = 2
    cancel_stale_requests: bool = True
    cache_ttl_seconds: float = 15.0
    request_timeout_seconds: float | None = 30.0
    retry_attempts: int = 2
    retry_base_delay_seconds: float = 0.15
    stale_after_seconds: float | None = 120.0

    def __post_init__(self) -> None:
        DataTableSpec.__post_init__(self)
        if self.cache_pages < 0:
            raise ValueError('cache_pages must be >= 0')
        if self.cache_pages and self.cache_ttl_seconds <= 0:
            raise ValueError('cache_ttl_seconds must be > 0 when cache_pages is enabled')
        if self.request_timeout_seconds is not None and self.request_timeout_seconds <= 0:
            raise ValueError('request_timeout_seconds must be > 0 or None')
        if self.retry_attempts < 1:
            raise ValueError('retry_attempts must be >= 1')
        if self.retry_base_delay_seconds < 0:
            raise ValueError('retry_base_delay_seconds must be >= 0')
        if self.stale_after_seconds is not None and self.stale_after_seconds <= 0:
            raise ValueError('stale_after_seconds must be > 0 or None')

@dataclass(frozen=True, slots=True)
class EditableTableSpec(DataTableSpec):
    editable: bool = True
    save_mode: str = 'row'
    commit_mode: EditCommitMode = EditCommitMode.OPTIMISTIC
    restore_focus_on_error: bool = True

    def __post_init__(self) -> None:
        DataTableSpec.__post_init__(self)
        if self.save_mode not in {'cell','row','batch'}:
            raise ValueError('save_mode must be cell, row, or batch')

@dataclass(frozen=True, slots=True)
class BulkAction:
    key: str
    label: str
    icon: str | None = None
    intent: str = 'secondary'
    requires_selection: bool = True
    on_action: Callable[[Sequence[Mapping[str, Any]]], Any] | None = field(default=None, compare=False, repr=False)
    visible_when: Callable[[Sequence[Mapping[str, Any]]], bool] | None = field(default=None, compare=False, repr=False)
    enabled_when: Callable[[Sequence[Mapping[str, Any]]], bool] | None = field(default=None, compare=False, repr=False)
    disabled_reason: Callable[[Sequence[Mapping[str, Any]]], str | None] | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError('BulkAction requires key and label')

@dataclass(frozen=True, slots=True)
class RowAction:
    key: str
    label: str
    icon: str | None = None
    intent: str = 'secondary'
    on_action: Callable[[Mapping[str, Any]], Any] | None = field(default=None, compare=False, repr=False)
    visible_when: Callable[[Mapping[str, Any]], bool] | None = field(default=None, compare=False, repr=False)
    enabled_when: Callable[[Mapping[str, Any]], bool] | None = field(default=None, compare=False, repr=False)
    disabled_reason: Callable[[Mapping[str, Any]], str | None] | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError('RowAction requires key and label')


def resolve_row_action_state(action: RowAction, row: Mapping[str, Any]) -> ActionState:
    visible, policy_error = _evaluate_predicate(action.visible_when, row, default=True)
    if not visible:
        return ActionState(False, False, None)
    enabled, enabled_error = _evaluate_predicate(action.enabled_when, row, default=True)
    reason = policy_error or enabled_error
    if not enabled and reason is None and action.disabled_reason is not None:
        try:
            reason = action.disabled_reason(row)
        except Exception:
            reason = 'Action policy could not be evaluated.'
    return ActionState(True, enabled, reason)


def resolve_bulk_action_state(action: BulkAction, rows: Sequence[Mapping[str, Any]]) -> ActionState:
    visible, policy_error = _evaluate_predicate(action.visible_when, rows, default=True)
    if not visible:
        return ActionState(False, False, None)
    if action.requires_selection and not rows:
        return ActionState(True, False, 'Select at least one record.')
    enabled, enabled_error = _evaluate_predicate(action.enabled_when, rows, default=True)
    reason = policy_error or enabled_error
    if not enabled and reason is None and action.disabled_reason is not None:
        try:
            reason = action.disabled_reason(rows)
        except Exception:
            reason = 'Action policy could not be evaluated.'
    return ActionState(True, enabled, reason)

__all__ = [
    'ColumnKind','TableDensity','SelectionMode','PaginationMode','SortDirection','FilterOperator','FilterLogic','PinPosition','EditCommitMode','ExportDisabledError','ActionState',
    'ConditionalRule','TableColumn','SortSpec','FilterSpec','FilterGroup','FilterExpression','TableQuery','TableResult','TableViewSnapshot','TablePreset','TableState',
    'DataTableSpec','ServerDataTableSpec','EditableTableSpec','BulkAction','RowAction','resolve_row_action_state','resolve_bulk_action_state',
]
