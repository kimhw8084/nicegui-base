"""Provider-backed rendering for generated project placements.

The page owns one ``AnalysisContext`` and every provider-backed output reads that
context. Filter controls only mutate the context; they never mutate the source rows.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

from nicegui_base.async_tools import LatestRequestController
from nicegui_base.data_sources import Comparison, ComparisonOperator, In, Query
from nicegui_base.performance import LifecycleScope

from .catalog_runtime import describe_entry, entries_by_key, render_catalog_example
from .preview_data import MAX_PROJECT_ROWS

MAX_FILTER_CHOICES = 100
PROVIDER_DEBOUNCE_SECONDS = 0.15


def _schema_metadata(schema: Any) -> tuple[dict[str, str], ...]:
    fields = getattr(schema, 'fields', schema)
    if isinstance(fields, Mapping):
        fields = fields.get('fields', ())
    if not isinstance(fields, (list, tuple)):
        return ()
    result: list[dict[str, str]] = []
    for field in fields:
        if isinstance(field, Mapping):
            name = str(field.get('name') or '').strip()
            role = str(getattr(field.get('role'), 'value', field.get('role') or '')).casefold()
            type_name = str(getattr(field.get('type') or field.get('inferred_type'), 'value', field.get('type') or field.get('inferred_type') or '')).casefold()
        else:
            name = str(getattr(field, 'name', '') or '').strip()
            role = str(getattr(getattr(field, 'role', ''), 'value', getattr(field, 'role', '')) or '').casefold()
            type_name = str(getattr(getattr(field, 'type', ''), 'value', getattr(field, 'type', '')) or '').casefold()
        if name:
            result.append({'name': name, 'role': role, 'type': type_name})
    return tuple(result)


def configured_filter_field(schema: Any, options: Mapping[str, Any] | None = None) -> str | None:
    """Select the configured categorical dataset field for a provider control."""
    options = options or {}
    metadata = _schema_metadata(schema)
    names = tuple(item['name'] for item in metadata)
    explicit = next(
        (str(options[key]).strip() for key in ('filter_field', 'category_field', 'label_field')
         if options.get(key) is not None and str(options.get(key)).strip()),
        None,
    )
    if explicit:
        if explicit not in names:
            raise ValueError(f'Configured filter field {explicit!r} does not exist in the dataset.')
        return explicit
    for item in metadata:
        if item['role'] in {'dimension', 'entity'} and item['name'] not in {'id', 'record_id', 'key'}:
            return item['name']
    for item in metadata:
        if item['type'] in {'string', 'category'} and item['name'] not in {'id', 'record_id', 'key'}:
            return item['name']
    return None


def _bounded_choice_map(values: Sequence[Any], *, limit: int = MAX_FILTER_CHOICES) -> tuple[dict[str, str], dict[str, Any], bool]:
    labels: dict[str, str] = {'': 'All values'}
    raw_values: dict[str, Any] = {}
    seen: set[str] = set()
    for value in values:
        if value in (None, ''):
            continue
        label = str(value)
        if label in seen:
            continue
        if len(seen) >= limit:
            return labels, raw_values, True
        seen.add(label)
        key = label
        suffix = 2
        while key in raw_values:
            key = f'{label} ({suffix})'
            suffix += 1
        labels[key] = label
        raw_values[key] = value
    return labels, raw_values, False


async def query_provider(source, context, *, limit: int = MAX_PROJECT_ROWS, search_fields: Sequence[str] = ()):
    """Run one bounded provider read through the page-owned context."""
    query = context.query(Query(limit=limit, search_fields=tuple(search_fields)))
    return await source.query(query)


class ProviderQueryController:
    """Debounced, latest-request-wins reads for one generated output surface."""

    def __init__(self, source, *, limit: int = MAX_PROJECT_ROWS + 1, debounce_seconds: float = PROVIDER_DEBOUNCE_SECONDS):
        if limit < 1:
            raise ValueError('provider query limit must be >= 1')
        self.source = source
        self.limit = limit
        self.debounce_seconds = max(0.0, float(debounce_seconds))
        self.requests = LatestRequestController(timeout=getattr(source, 'timeout_seconds', 30.0), cache_size=0)
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    async def load(self, context, *, search_fields: Sequence[str] = ()):
        if self._closed:
            raise RuntimeError('ProviderQueryController is closed')
        query = context.query(Query(limit=self.limit, search_fields=tuple(search_fields)))
        if self.debounce_seconds:
            await asyncio.sleep(self.debounce_seconds)
        key = (context.source_key, context.revision, repr(query))
        return await self.requests.run(key, lambda: self.source.query(query))

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self.requests.aclose()


def _reset_filter_state(context, filter_state: dict[str, Any]) -> None:
    resetters = tuple(filter_state.get('__resetters__', ()))
    filter_state.clear()
    filter_state['__resetters__'] = list(resetters)
    context.set_filters(())
    context.set_search('')
    for reset in resetters:
        reset()


def _apply_filter_state(context, filter_state: dict[str, Any]) -> None:
    context.set_filters(tuple(value for key, value in filter_state.items() if not key.startswith('__')))


def _render_filter_control(entry_key, source, context, *, schema, options, filter_state):
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button, Combobox, MultiSelect, SearchInput, Select

    entry = entries_by_key()[entry_key]
    component_key = str(entry.metadata.get('component_key') or '')
    options = dict(options or {})
    resetters = filter_state.setdefault('__resetters__', [])

    if component_key == 'search_input':
        control = SearchInput(
            'Search records', value=context.search, debounce_ms=180,
            placeholder='Search current data',
            on_change=lambda event: context.set_search(str(getattr(event, 'value', '') or '')),
        )
        control.element.props('data-provider-filter="search"')
        resetters.append(lambda: control.element.set_value(''))
        Button('Clear filters', on_click=lambda: _reset_filter_state(context, filter_state)).element.props('data-provider-clear')
        return control

    if component_key not in {'select', 'multi_select', 'combobox'}:
        return render_catalog_example(entry_key, title=entry.title, options=options)

    field = configured_filter_field(schema, options)
    if field is None:
        ui.label('No categorical dataset field is configured for this filter.').classes('cui-workbench-note').props('role="alert"')
        return
    label = field.replace('_', ' ').title()
    current = filter_state.get(field)
    current_value = getattr(current, 'value', None) if component_key != 'multi_select' else ()
    if component_key == 'multi_select':
        control = MultiSelect(f'Filter by {label}', {'': 'All values'}, value=(), clearable=True, searchable=True)
    elif component_key == 'combobox':
        control = Combobox(f'Filter by {label}', {'': 'All values'}, value=current_value, clearable=True)
    else:
        control = Select(f'Filter by {label}', {'': 'All values'}, value=current_value, clearable=True, searchable=True)
    control.element.props(f'data-provider-filter="{field}"')
    raw_by_key: dict[str, Any] = {}
    choice_scope = LifecycleScope()
    client = getattr(getattr(ui, 'context', None), 'client', None)
    on_delete = getattr(client, 'on_delete', None)
    if callable(on_delete):
        on_delete(choice_scope.aclose)

    def changed(event=None):
        value = getattr(event, 'value', None)
        if component_key == 'multi_select':
            selected = tuple(raw_by_key[key] for key in (value or ()) if key in raw_by_key)
            if selected:
                filter_state[field] = In(field, selected)
            else:
                filter_state.pop(field, None)
        else:
            if value in (None, '') or value not in raw_by_key:
                filter_state.pop(field, None)
            else:
                filter_state[field] = Comparison(field, ComparisonOperator.EQ, raw_by_key[value])
        _apply_filter_state(context, filter_state)

    control.element.on_value_change(changed)
    resetters.append(lambda: control.element.set_value(() if component_key == 'multi_select' else ''))
    Button('Clear filters', on_click=lambda: _reset_filter_state(context, filter_state)).element.props('data-provider-clear')

    async def populate_choices():
        try:
            result = await source.distinct(field, Query())
            if choice_scope.closed:
                return
            labels, raw_by_key_local, truncated = _bounded_choice_map(result.values)
            raw_by_key.update(raw_by_key_local)
            control.element.set_options(labels, value=() if component_key == 'multi_select' else '')
            if truncated and not choice_scope.closed:
                ui.label(f'First {MAX_FILTER_CHOICES} values shown; narrow the provider query for more choices.').classes('cui-workbench-note')
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if choice_scope.closed:
                return
            from nicegui_base.security import redact_text
            ui.label('Filter choices unavailable: ' + redact_text(str(exc))).classes('cui-workbench-note').props('role="alert"')

    choice_awaitable = populate_choices()
    try:
        choice_scope.create_task(
            choice_awaitable,
            name='nicegui-base-provider-filter-choices',
        )
    except RuntimeError:
        # Static construction without an event loop: keep the control renderable
        # and do not leak an un-awaited coroutine.
        close_coro = getattr(choice_awaitable, 'close', None)
        if callable(close_coro):
            close_coro()
    return control


def render_provider_capability(
    entry_key,
    source,
    context,
    *,
    title=None,
    options=None,
    schema=None,
    measurement_field=None,
    category_field=None,
    filter_state=None,
):
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button

    entry = entries_by_key()[entry_key]
    info = describe_entry(entry)
    options = dict(options or {})
    filter_state = filter_state if filter_state is not None else {}
    component_key = str(entry.metadata.get('component_key') or '')
    if component_key in {'search_input', 'select', 'multi_select', 'combobox'}:
        return _render_filter_control(
            entry_key, source, context, schema=schema, options=options, filter_state=filter_state,
        )
    if not info['uses_rows']:
        return render_catalog_example(entry_key, title=title, options=options)

    host = ui.element('div').classes('cui-provider-capability w-full').props(f'data-provider-capability="{entry_key}"')
    state = {'generation': 0, 'closed': False}
    scope = LifecycleScope()
    controller = ProviderQueryController(source)
    scope.register(controller.aclose, key='provider-query-controller')

    def message(text: str, *, alert: bool = False) -> None:
        host.clear()
        with host:
            ui.label(text).classes('cui-workbench-note').props('role="alert"' if alert else 'role="status"')

    async def refresh() -> None:
        state['generation'] += 1
        generation = state['generation']
        message('Loading current provider data…')
        try:
            search_fields = tuple(item['name'] for item in _schema_metadata(schema))
            result = await controller.load(context, search_fields=search_fields)
            if result is None or state['closed'] or generation != state['generation']:
                return
            if result.filtered_total > MAX_PROJECT_ROWS:
                message(
                    f'{result.filtered_total:,} rows match. Narrow filters to {MAX_PROJECT_ROWS:,} or fewer to render this bounded example. No sample was silently substituted.',
                    alert=True,
                )
                return
            host.clear()
            with host:
                render_catalog_example(
                    entry_key,
                    title=title,
                    rows=result.rows,
                    options=options,
                    schema=schema,
                    measurement_field=measurement_field,
                    category_field=category_field,
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if not state['closed'] and generation == state['generation']:
                from nicegui_base.security import redact_text
                message('Could not render provider data: ' + redact_text(str(exc)), alert=True)

    def schedule(_context=None) -> None:
        if state['closed']:
            return
        awaitable = refresh()
        try:
            scope.create_task(awaitable, name='nicegui-base-provider-render')
        except RuntimeError:
            close_coro = getattr(awaitable, 'close', None)
            if callable(close_coro):
                close_coro()

    unsubscribe = context.watch(schedule)

    async def close(*_):
        if state['closed']:
            return
        state['closed'] = True
        unsubscribe()
        await scope.aclose()

    ui.context.client.on_delete(close)
    Button('Refresh provider data', on_click=schedule)
    schedule()
    return host


__all__ = [
    'MAX_FILTER_CHOICES', 'PROVIDER_DEBOUNCE_SECONDS', 'ProviderQueryController',
    'configured_filter_field', 'query_provider', 'render_provider_capability',
]
