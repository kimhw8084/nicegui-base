from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .codegen import CapabilityConfiguration, code_artifact
from .data_dock import DEFAULT_ENGINEERING_SAMPLE, DataDockModel, DataDockParseResult, DataDockSeverity, default_data_dock
from .models import WorkbenchEntry, WorkbenchKind
from .state_matrix import render_state_matrix


STUDIO_TABS = ('preview', 'usage', 'data', 'configure', 'states', 'interactions', 'inspect', 'code')
RESPONSIVE_WIDTHS = {
    'desktop': 1200,
    'compact': 980,
    'tablet': 760,
    'phone': 390,
}


@dataclass(slots=True)
class StudioConfigModel:
    title: str
    density: str = 'compact'
    responsive_width: str = 'desktop'
    theme: str = 'system'
    options: dict[str, Any] = field(default_factory=dict)
    revision: int = 0

    def update(self, **changes: Any) -> None:
        for key, value in changes.items():
            if key == 'options':
                self.options.update(dict(value))
            elif hasattr(self, key):
                setattr(self, key, value)
            else:
                self.options[key] = value
        self.revision += 1

    def reset(self, *, title: str) -> None:
        self.title = title
        self.density = 'compact'
        self.responsive_width = 'desktop'
        self.theme = 'system'
        self.options.clear()
        self.revision += 1

    def frozen(self) -> CapabilityConfiguration:
        return CapabilityConfiguration(
            title=self.title, density=self.density, responsive_width=self.responsive_width,
            theme=self.theme, options=dict(self.options),
        )


@dataclass(slots=True)
class StudioSession:
    entry: WorkbenchEntry
    data: DataDockModel
    config: StudioConfigModel
    event_log: list[str] = field(default_factory=list)
    refresh_preview: Callable[[], None] | None = None

    def log(self, message: str) -> None:
        self.event_log.append(str(message))
        del self.event_log[:-30]


_DATA_REGISTRIES = {'tables', 'visualizations', 'engineering', 'data_sources', 'analysis'}
_INTERACTIVE_COMPONENTS = frozenset({
    'button', 'action_button', 'button_group', 'icon_button', 'text_input', 'number_input',
    'textarea', 'search_input', 'select', 'combobox', 'autocomplete', 'multi_select',
    'checkbox', 'checkbox_group', 'radio_group', 'switch', 'slider', 'range_slider',
    'date_picker', 'date_range_picker', 'datetime_picker', 'time_picker', 'file_upload',
    'data_table', 'accordion', 'collapsible_panel',
})


def is_data_backed(entry: WorkbenchEntry) -> bool:
    if entry.kind in {WorkbenchKind.ANALYTIC, WorkbenchKind.RECIPE}:
        return True
    if entry.kind is WorkbenchKind.PATTERN:
        return str(entry.metadata.get('pattern_key')) in {'dashboard','data_explorer','master_detail','crud','monitoring','comparison','analysis_workspace'}
    registry = str(entry.metadata.get('registry_name') or '')
    if registry in _DATA_REGISTRIES:
        return True
    key = entry.key.casefold()
    return any(token in key for token in ('table','chart','plot','map','trend','distribution','metric','analysis'))


def studio_tabs_for_entry(entry: WorkbenchEntry, *, data_renderer=None, interaction_renderer=None) -> tuple[str, ...]:
    """Return only tabs that teach a capability the entry actually supports.

    The tab contract is deliberately computed from the same registry metadata used
    by the renderer.  This prevents empty Data/Interactions panels from becoming a
    second, misleading catalog surface.
    """
    tabs = ['preview', 'usage']
    if data_renderer is not None or is_data_backed(entry):
        tabs.append('data')
    component_key = str(entry.metadata.get('component_key') or '')
    from .catalog_runtime import supported_options
    if supported_options(entry) or component_key in _INTERACTIVE_COMPONENTS:
        tabs.append('configure')
    if (component_key in _INTERACTIVE_COMPONENTS or entry.metadata.get('states')) and len(entry.reference_contract.states) >= 2:
        tabs.append('states')
    if interaction_renderer is not None or component_key in _INTERACTIVE_COMPONENTS:
        tabs.append('interactions')
    tabs.extend(('inspect', 'code'))
    return tuple(dict.fromkeys(tabs))


def sample_rows_for_entry(entry: WorkbenchEntry) -> tuple[dict[str, Any], ...]:
    # One broad semiconductor-friendly fixture lets the same Data Dock demonstrate
    # tables/charts/engineering mappings without creating separate hidden datasets.
    if is_data_backed(entry):
        if entry.kind is WorkbenchKind.ANALYTIC:
            from .analytic_specimens import canonical_fixture_for_surface
            surface_key = str(entry.metadata.get('surface_key') or '')
            return tuple(dict(row) for row in canonical_fixture_for_surface(surface_key))
        return tuple(dict(row) for row in DEFAULT_ENGINEERING_SAMPLE)
    return ()


def default_studio_options(entry: WorkbenchEntry) -> dict[str, Any]:
    """Seed reference sessions from the canonical contract, never a guessed column."""
    if entry.kind is WorkbenchKind.ANALYTIC:
        from .analytic_specimens import CANONICAL_MEASUREMENT_FIELDS
        surface_key = str(entry.metadata.get('surface_key') or '')
        field = CANONICAL_MEASUREMENT_FIELDS.get(surface_key)
        return {'measurement': field} if field else {}
    return {}


def studio_session(entry: WorkbenchEntry) -> StudioSession:
    rows = sample_rows_for_entry(entry)
    model = DataDockModel(rows, sample_name=f'{entry.title} sample') if rows else DataDockModel((), sample_name='No sample data')
    return StudioSession(entry, model, StudioConfigModel(entry.title))


def _column_kind(type_name: str):
    from nicegui_base.data_table import ColumnKind
    return {
        'integer': ColumnKind.INTEGER,
        'float': ColumnKind.FLOAT,
        'boolean': ColumnKind.BOOLEAN,
        'datetime': ColumnKind.DATETIME,
        'date': ColumnKind.DATETIME,
        'json': ColumnKind.CUSTOM,
        'unknown': ColumnKind.CUSTOM,
    }.get(type_name, ColumnKind.TEXT)


def _read_upload_content(event) -> tuple[str, Any]:
    from nicegui_base.integrations.upload_io import upload_parts
    name, _media, content = upload_parts(event)
    return name, content


async def _read_all(content: Any) -> bytes:
    from nicegui_base.integrations.upload_io import read_upload_bytes
    from .preview_data import MAX_PROJECT_BYTES
    return await read_upload_bytes(content, max_bytes=MAX_PROJECT_BYTES)


def render_data_capability_map() -> None:
    """Introduce the canonical table lab with a truthful interaction contract."""
    from nicegui import ui

    supported = (
        ('Find & filter', 'global search, column filters, sort, no-results, refresh', 'search'),
        ('Edit safely', 'inline editing, validation, add/delete, undo and redo', 'editing'),
        ('Select & act', 'single selection, row actions, export, density and visible columns', 'selection'),
        ('Paste & import', 'rectangular clipboard paste plus CSV, TSV and JSON upload', 'paste'),
        ('Understand schema', 'types, semantic roles, missing values and duplicate checks', 'schema'),
        ('Bounded data', 'pagination, responsive overflow and canonical empty/error states', 'bounded'),
    )
    with ui.element('section').classes('cui-data-dock-capability-map').props('data-data-capability-map'):
        with ui.element('div').classes('cui-data-dock-capability-head'):
            ui.label('Enterprise Data Table Lab').classes('cui-workbench-section-title')
            ui.label('Use the live table below to learn the canonical DataTable and DataDock contracts. Each capability card names a real interaction in this lab, not a decorative promise.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-data-dock-capability-grid'):
            for title, description, key in supported:
                with ui.element('article').classes('cui-data-dock-capability-card').props(f'data-data-capability="{key}"'):
                    ui.label(title).classes('cui-workbench-card__title')
                    ui.label(description).classes('cui-workbench-note')
        with ui.element('details').classes('cui-data-dock-unsupported'):
            with ui.element('summary').props('tabindex="0"'):
                ui.label('Provider-scale extensions').classes('cui-workbench-card__meta')
            ui.label('Server-backed reads, stale-request cancellation, permissions, expandable master/detail, and grouping remain available through the reusable table APIs for application pages; this bounded local lab keeps one editable dataset fast and legible.').classes('cui-workbench-note')


def render_data_dock(model: DataDockModel, *, on_change: Callable[[DataDockModel], Any] | None = None, mapping_targets: Sequence[str] = ()) -> None:
    """Render the reusable example-data playground and data-contract demonstrator."""
    from nicegui import ui
    from nicegui_base.data_table import BulkAction, EditableTableSpec, PinPosition, RowAction, SelectionMode, TableColumn
    from nicegui_base.integrations.nicegui_components import ActionButton, Button, FileUpload, Select, TextArea, TextInput
    from nicegui_base.integrations.nicegui_data_table import EditableTable
    from nicegui_base.integrations.nicegui_layout import SegmentedControl

    dock_status = ui.label('').classes('cui-workbench-note').props('role=\"status\" aria-live=\"polite\" data-dock-status')
    mode = {'value': 'review'}
    mode_host = ui.element('div').classes('cui-workbench-toolbar cui-data-dock-modebar')
    content_host = ui.element('div').classes('cui-data-dock-content')
    quality_host = ui.element('div').classes('cui-data-dock-quality-results')

    async def changed() -> None:
        if on_change is not None:
            result = on_change(model)
            if hasattr(result, '__await__'):
                await result
        render_mode()

    async def mutate(action: Callable[[], Any]) -> None:
        try:
            action()
            await changed()
            dock_status.set_text('Data updated.')
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            dock_status.set_text(f'Change rejected: {exc}')

    def status_strip() -> None:
        snap = model.snapshot
        with ui.element('div').classes('cui-data-dock-summary').props(f'data-dock-rows="{snap.quality.rows}" data-dock-columns="{snap.quality.columns}" data-dock-revision="{snap.revision}"'):
            for value, label in (
                (snap.quality.rows, 'rows'), (snap.quality.columns, 'columns'),
                (snap.quality.missing_cells, 'missing cells'), (snap.quality.duplicate_rows, 'duplicate rows'),
            ):
                with ui.element('div').classes('cui-workbench-kpi'):
                    ui.label(str(value)).classes('text-h6')
                    ui.label(label)
        errors = [issue for issue in snap.quality.issues if issue.severity is DataDockSeverity.ERROR]
        warnings = [issue for issue in snap.quality.issues if issue.severity is DataDockSeverity.WARNING]
        if errors or warnings:
            with ui.element('div').classes('cui-data-dock-issues'):
                for issue in (*errors, *warnings[:5]):
                    ui.label(f'{issue.severity.value.upper()} · {issue.message}').classes('cui-workbench-note')

        def show_quality(kind: str) -> None:
            quality_host.clear()
            with quality_host:
                if kind == 'missing':
                    findings = [(index + 1, column.name) for index, row in enumerate(model.rows) for column in model.columns if row.get(column.name) in (None, '')]
                    ui.label(f'Missing values · {len(findings)} cells').classes('cui-workbench-section-title')
                    for row_index, column in findings[:40]:
                        ui.label(f'Row {row_index} · {column}').classes('cui-workbench-note')
                    if not findings:
                        ui.label('No missing values in the active dataset.').classes('cui-workbench-note')
                elif kind == 'duplicates':
                    seen: dict[str, int] = {}
                    for row in model.rows:
                        key = json.dumps(row, sort_keys=True, default=str)
                        seen[key] = seen.get(key, 0) + 1
                    duplicates = [count for count in seen.values() if count > 1]
                    ui.label(f'Duplicate rows · {sum(count - 1 for count in duplicates)} repeated row(s)').classes('cui-workbench-section-title')
                    ui.label('Duplicate detection uses the full normalized row value.').classes('cui-workbench-note')
                else:
                    issues = model.snapshot.quality.issues
                    ui.label(f'Quality issues · {len(issues)}').classes('cui-workbench-section-title')
                    for issue in issues[:40]:
                        ui.label(f'{issue.severity.value.upper()} · {issue.message}').classes('cui-workbench-note').props('role="alert"' if issue.severity is DataDockSeverity.ERROR else '')

        def show_profile(event=None) -> None:
            column = str(getattr(event, 'value', '') or '')
            if not column:
                return
            profile = model.profile_column(column)
            quality_host.clear()
            with quality_host:
                ui.label(f'Column profile · {column}').classes('cui-workbench-section-title')
                ui.label(' · '.join(f'{key}: {value}' for key, value in profile.items() if key != 'top_values')).classes('cui-workbench-note')
                if profile.get('top_values'):
                    ui.label('Top values · ' + ' · '.join(f'{value} ({count})' for value, count in profile['top_values'])).classes('cui-workbench-note')

        with ui.element('div').classes('cui-data-dock-quality-actions'):
            Button('Show missing', on_click=lambda: show_quality('missing'))
            Button('Show duplicates', on_click=lambda: show_quality('duplicates'))
            Button('Show issues', on_click=lambda: show_quality('issues'))
            Select('Profile column', {column.name: column.name for column in model.columns}, value=model.columns[0].name if model.columns else None, clearable=True, on_change=show_profile)
        with quality_host:
            ui.label('Quality findings and bounded column profiles appear here.').classes('cui-workbench-note')

    def render_edit_grid() -> None:
        if not model.columns:
            ui.label('No columns to edit. Paste or upload data first.').classes('cui-workbench-note')
            return
        row_key = '__wb_row'
        while row_key in model.snapshot.column_names:
            row_key += '_'
        rows = [{**row, row_key:index} for index, row in enumerate(model.rows)]
        columns = [TableColumn(row_key, '#', kind=_column_kind('integer'), visible=False, pinned=PinPosition.LEFT)]
        columns.extend(TableColumn(column.name, column.name, kind=_column_kind(column.inferred_type), editable=True) for column in model.columns)
        selected_rows: list[Mapping[str, Any]] = []

        async def remove_selected(rows: Sequence[Mapping[str, Any]]) -> None:
            indexes = sorted({int(row.get(row_key, -1)) for row in rows if str(row.get(row_key, '')).isdigit()}, reverse=True)
            for index in indexes:
                if 0 <= index < len(model.rows):
                    model.delete_row(index)
            if indexes:
                await changed()
                dock_status.set_text(f'Deleted {len(indexes)} selected row(s); use Undo to restore them.')

        def inspect_row(row: Mapping[str, Any]) -> None:
            dock_status.set_text('Selected row · ' + ' · '.join(f'{key}={value}' for key, value in row.items() if key != row_key)[:240])

        async def selected(rows: Sequence[Mapping[str, Any]]) -> None:
            selected_rows[:] = rows

        spec = EditableTableSpec(tuple(columns), row_key=row_key, title='Example data', selection=SelectionMode.MULTIPLE, persist_state=False)

        async def save_edit(row, key, value):
            if key == row_key:
                return
            try:
                model.edit_cell(int(row[row_key]), str(key), value)
            except (ValueError, TypeError, IndexError, KeyError) as exc:
                dock_status.set_text(f'Edit rejected: {exc}')
                raise
            if on_change:
                result = on_change(model)
                if hasattr(result, '__await__'):
                    await result

        table = EditableTable(
            rows, columns, spec=spec, save_edit=save_edit, on_select=selected,
            bulk_actions=(BulkAction('delete', 'Delete selected', icon='delete', intent='danger', on_action=remove_selected),),
            row_actions=(RowAction('inspect', 'Inspect row', icon='info', on_action=inspect_row),),
        )
        selected = {'row': 0, 'column': model.columns[0].name}
        target_label = ui.label(f"Paste target · row 1 · {selected['column']}").classes('cui-workbench-note')
        clipboard_status = ui.label('Select any editable cell, then paste from the clipboard or use the fallback box.').classes('cui-workbench-note')

        def select_cell(event) -> None:
            args = getattr(event, 'args', {}) or {}
            row_index = args.get('rowIndex')
            node = args.get('node')
            if row_index is None and isinstance(node, Mapping):
                row_index = node.get('rowIndex')
            data = args.get('data')
            if row_index is None and isinstance(data, Mapping):
                row_index = data.get(row_key)
            column = args.get('colId')
            column_payload = args.get('column')
            if column is None and isinstance(column_payload, Mapping):
                column = column_payload.get('colId')
            try:
                row_index = int(row_index)
            except (TypeError, ValueError):
                return
            column = str(column or '')
            if column not in model.snapshot.column_names:
                return
            selected['row'] = max(0, row_index)
            selected['column'] = column
            target_label.set_text(f"Paste target · row {selected['row'] + 1} · {selected['column']}")

        table.element.on('cellClicked', select_cell)
        with ui.element('div').classes('cui-workbench-toolbar'):
            Button('Add row', on_click=lambda: mutate(model.add_row))
            Button('Delete selected row', disabled=not bool(model.rows), on_click=lambda: mutate(lambda: model.delete_row(min(selected['row'], len(model.rows)-1))))
            Button('Undo', disabled=not model.can_undo, on_click=lambda: mutate(model.undo))
            Button('Redo', disabled=not model.can_redo, on_click=lambda: mutate(model.redo))

        async def apply_rectangle() -> None:
            text = str(getattr(paste.element, 'value', '') or '')
            if not text.strip():
                clipboard_status.set_text('Paste cells into the fallback box first.')
                return
            try:
                model.rectangular_paste(selected['row'], selected['column'], text)
            except (ValueError, TypeError, IndexError) as exc:
                clipboard_status.set_text(f'Paste rejected: {exc}')
                return
            clipboard_status.set_text(f"Applied pasted cells at row {selected['row'] + 1} · {selected['column']}")
            await changed()

        async def paste_clipboard() -> None:
            try:
                text = await ui.run_javascript('navigator.clipboard.readText()')
            except Exception as exc:
                clipboard_status.set_text(f'Clipboard access unavailable: {type(exc).__name__}. Open the fallback paste box below.')
                return
            text = str(text or '')
            if not text.strip():
                clipboard_status.set_text('Clipboard contains no tabular text. Open the fallback paste box if browser permission is restricted.')
                return
            try:
                model.rectangular_paste(selected['row'], selected['column'], text)
            except (ValueError, TypeError, IndexError) as exc:
                clipboard_status.set_text(f'Paste rejected: {exc}')
                return
            clipboard_status.set_text(f"Pasted clipboard at row {selected['row'] + 1} · {selected['column']}")
            await changed()

        with ui.element('div').classes('cui-workbench-toolbar'):
            ActionButton('Paste clipboard at selected cell', on_click=paste_clipboard)
            ui.label('Excel: select a destination cell, copy a rectangular range, then paste. Rows grow automatically; schema columns stay governed.').classes('cui-workbench-note')
        with ui.element('details').classes('cui-data-dock-fallback'):
            with ui.element('summary').props('tabindex="0"'):
                ui.label('Clipboard permission fallback').classes('cui-workbench-note')
            paste = TextArea('Paste cells', placeholder='Fallback: paste a rectangular selection copied from Excel…', rows=3)
            Button('Apply fallback paste at selected cell', on_click=apply_rectangle)

    def render_mapping() -> None:
        for column in model.columns:
            with ui.element('article').classes('cui-data-dock-column').props('data-dock-column=' + json.dumps(column.name)):
                ui.label(column.name).classes('cui-workbench-card__title')
                ui.label(f'{column.inferred_type} · {column.role} · {column.confidence:.0%} confidence').classes('cui-workbench-note')
                with ui.element('div').classes('cui-data-dock-column__controls'):
                    name_input = TextInput('Column name', value=column.name)
                    name_input.element.props('data-schema-name=' + json.dumps(column.name))
                    type_select = Select('Type', {key:key.title() for key in ('string','integer','float','boolean','date','datetime','category','json','unknown')}, value=column.inferred_type, clearable=False)
                    role_select = Select('Semantic role', {key:key.title() for key in ('dimension','measurement','identifier','timestamp','entity','attribute')}, value=column.role, clearable=False)
                    async def apply_col(_e=None, original=column.name, n=name_input, t=type_select, r=role_select, inferred=column.inferred_type, role=column.role):
                        try:
                            model.configure_column(original,
                                name=str(getattr(n.element, 'value', original) or original).strip(),
                                type_name=str(getattr(t.element, 'value', inferred)),
                                role=str(getattr(r.element, 'value', role)))
                            await changed()
                            dock_status.set_text('Schema updated.')
                        except (ValueError, TypeError, KeyError) as exc:
                            dock_status.set_text(f'Schema change rejected: {exc}')
                    Button('Apply', on_click=apply_col)
        if mapping_targets:
            ui.label('Logical mapping targets').classes('cui-workbench-section-title')
            ui.label(', '.join(mapping_targets)).classes('cui-workbench-note')

    def render_paste() -> None:
        paste = TextArea('Paste data', placeholder='Paste TSV from Excel, CSV, or a JSON array of objects…', rows=12)
        result_host = ui.element('div')

        async def commit_preview() -> None:
            try:
                snapshot = model.commit_stage()
            except (ValueError, TypeError) as exc:
                dock_status.set_text(f'Import rejected: {exc}')
                return
            dock_status.set_text(f'Imported {snapshot.quality.rows} rows · {snapshot.quality.columns} columns')
            mode['value'] = 'review'
            if on_change:
                value = on_change(model)
                if hasattr(value, '__await__'):
                    await value
            render_mode_selector(); render_mode()

        def discard_preview() -> None:
            model.discard_stage()
            dock_status.set_text('Import preview discarded; active data was unchanged.')
            mode['value'] = 'review'
            render_mode_selector(); render_mode()

        def preview(result: DataDockParseResult) -> None:
            result_host.clear()
            with result_host:
                if not result.ok or result.snapshot is None:
                    for issue in result.issues:
                        ui.label(issue.message).classes('cui-workbench-note').props('role=alert')
                    return
                snap = result.snapshot; diff = model.schema_diff(snap)
                with ui.element('section').classes('cui-data-dock-import-preview').props('data-import-preview'):
                    ui.label('Import preview · active data is unchanged').classes('cui-workbench-section-title')
                    ui.label(f'{result.detected_format.value.upper() if result.detected_format else "DATA"} · {snap.quality.rows:,} rows · {snap.quality.columns} columns').classes('cui-workbench-note')
                    ui.label(f'Quality · {snap.quality.missing_cells:,} missing cells · {snap.quality.duplicate_rows:,} duplicate rows · {len(snap.quality.issues)} issues').classes('cui-workbench-note')
                    ui.label(f"Schema diff · +{len(diff['added'])} added · −{len(diff['removed'])} removed · {len(diff['changed'])} type changes").classes('cui-workbench-note')
                    if diff['added']: ui.label('Added: ' + ', '.join(diff['added'])).classes('cui-workbench-note')
                    if diff['removed']: ui.label('Removed: ' + ', '.join(diff['removed'])).classes('cui-workbench-note')
                    if diff['changed']:
                        ui.label('Changed: ' + ', '.join(f"{item['column']} ({item['from']} → {item['to']})" for item in diff['changed'])).classes('cui-workbench-note')
                    with ui.element('div').classes('cui-workbench-toolbar'):
                        ActionButton('Confirm import', on_click=commit_preview)
                        Button('Cancel', on_click=discard_preview)

        async def analyze():
            text = str(getattr(paste.element, 'value', '') or '')
            result = model.stage_text(text, source_name='Pasted data')
            dock_status.set_text(f'Preview ready · active data remains at {model.snapshot.quality.rows} rows' if result.ok else f'Import rejected: {result.issues[0].message if result.issues else "invalid data"}')
            preview(result)
        ActionButton('Preview import', on_click=analyze)
        with result_host:
            ui.label('Format is detected when previewing; confirmation is required to replace active data.').classes('cui-workbench-note')

    def render_upload() -> None:
        result_host = ui.element('div')
        async def commit_preview() -> None:
            try:
                snapshot = model.commit_stage()
            except (ValueError, TypeError) as exc:
                dock_status.set_text(f'Import rejected: {exc}')
                return
            dock_status.set_text(f'Imported {snapshot.quality.rows} rows from staged upload')
            mode['value'] = 'review'
            if on_change:
                value = on_change(model)
                if hasattr(value, '__await__'):
                    await value
            render_mode_selector(); render_mode()

        def discard_preview() -> None:
            model.discard_stage()
            dock_status.set_text('Upload preview discarded; active data was unchanged.')
            mode['value'] = 'review'
            render_mode_selector(); render_mode()

        def preview(result: DataDockParseResult, name: str) -> None:
            result_host.clear()
            with result_host:
                if not result.ok or result.snapshot is None:
                    for issue in result.issues:
                        ui.label(issue.message).classes('cui-workbench-note').props('role=alert')
                    return
                snap = result.snapshot; diff = model.schema_diff(snap)
                with ui.element('section').classes('cui-data-dock-import-preview').props('data-import-preview'):
                    ui.label(f'Upload preview · {name} · active data is unchanged').classes('cui-workbench-section-title')
                    ui.label(f'{snap.quality.rows:,} rows · {snap.quality.columns} columns · +{len(diff["added"])} / −{len(diff["removed"])} fields').classes('cui-workbench-note')
                    ui.label(f'Quality · {snap.quality.missing_cells:,} missing cells · {snap.quality.duplicate_rows:,} duplicate rows · {len(snap.quality.issues)} issues').classes('cui-workbench-note')
                    with ui.element('div').classes('cui-workbench-toolbar'):
                        ActionButton('Confirm import', on_click=commit_preview)
                        Button('Cancel', on_click=discard_preview)

        async def uploaded(event):
            name, content = _read_upload_content(event)
            try:
                data = await _read_all(content)
                result = model.stage_bytes(data, filename=name)
            except (ValueError, TypeError) as exc:
                dock_status.set_text(f'Import rejected: {exc}')
                return
            dock_status.set_text(f'Preview ready · {name} · active data remains at {model.snapshot.quality.rows} rows' if result.ok else f'Import rejected: {result.issues[0].message if result.issues else "invalid data"}')
            preview(result, name)
        from nicegui_base.security import UploadPolicy
        policy = UploadPolicy(max_bytes=2 * 1024 * 1024, allowed_extensions=frozenset({'.csv','.tsv','.json'}), allowed_media_types=frozenset({'text/csv','text/tab-separated-values','text/plain','application/json','application/octet-stream'}))
        FileUpload(label='Upload CSV, TSV, or JSON', accept=('.csv','.json','.tsv'), max_file_size_mb=2, upload_policy=policy, on_upload=uploaded, auto_upload=True)
        with result_host:
            ui.label('Uploads use the canonical NiceGUI Base upload policy before parsing.').classes('cui-workbench-note')

    def render_mode() -> None:
        content_host.clear()
        with content_host:
            value = mode['value']
            if value == 'paste':
                ui.label('Paste from Excel, CSV text, or a JSON array. Format detection and schema inference happen when the data is loaded.').classes('cui-workbench-note')
                render_paste()
            elif value == 'upload':
                ui.label('Upload a development dataset; successful imports return directly to the editable review workspace.').classes('cui-workbench-note')
                render_upload()
            else:
                snap = model.snapshot
                status_strip()
                with ui.element('div').classes('cui-workbench-toolbar cui-data-dock-review-tools'):
                    ui.label(f"Source · {snap.source_name or 'Untitled'} · {snap.source_format.value.upper()}").classes('cui-workbench-chip')
                    Button('Reset engineering sample', on_click=lambda: mutate(model.reset_sample))
                render_edit_grid()
                uncertain = sum(1 for column in model.columns if column.confidence < 0.7)
                with ui.element('details').classes('cui-workbench-section cui-data-dock-schema'):
                    with ui.element('summary').props('tabindex="0"'):
                        ui.label(f'Schema & semantic roles · {len(model.columns)} fields').classes('cui-workbench-section-title')
                        if uncertain:
                            ui.label(f'{uncertain} need review').classes('cui-workbench-chip')
                    ui.label('Expand only when you need to rename fields, correct inferred types, or confirm semantic roles.').classes('cui-workbench-note')
                    render_mapping()

    def mode_changed(event):
        value = str(getattr(event, 'value', 'review') or 'review')
        if value not in {'review','paste','upload'}:
            return
        mode['value'] = value
        render_mode()

    def render_mode_selector() -> None:
        mode_host.clear()
        with mode_host:
            ui.label('Example data playground').classes('cui-workbench-card__meta')
            SegmentedControl(
                {'review':'Inspect & edit','paste':'Paste example','upload':'Upload example'},
                value=mode['value'], on_change=mode_changed,
            )
            ui.label('Inspect the supplied example first; paste or upload only to demonstrate a new data contract.').classes('cui-workbench-note')

    render_mode_selector()
    render_mode()


def _related_entry_links(entry: WorkbenchEntry) -> None:
    from nicegui import ui
    if not entry.related_keys:
        return
    from .catalog import all_entries
    lookup = {item.key:item for item in all_entries()}
    ui.label('Related capabilities').classes('cui-workbench-section-title')
    with ui.element('div').classes('cui-workbench-chiprow'):
        for key in entry.related_keys:
            target = lookup.get(key)
            if target:
                ui.link(target.title, target.route).classes('cui-workbench-chip')


def _header_metadata(entry: WorkbenchEntry) -> None:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_content import CodeViewer
    contract = entry.reference_contract
    with ui.element('section').classes('cui-studio-header cui-studio-header--compact'):
        with ui.element('div').classes('cui-workbench-card__meta'):
            ui.label(entry.kind.value)
            if entry.category:
                ui.label('•')
                ui.label(entry.category)
            if entry.maturity:
                ui.label('•')
                ui.label(entry.maturity)
        ui.label(entry.title).classes('cui-workbench-title')
        ui.label(entry.description).classes('cui-workbench-subtitle')
        # The live specimen is the proof; a badge repeating that fact adds no
        # decision value to the first layer of the reference page.
        with ui.element('div').classes('cui-studio-decision-grid'):
            if entry.reference_contract.best_for:
                with ui.element('div').classes('cui-studio-decision-card'):
                    ui.label('Best for').classes('cui-workbench-card__meta')
                    ui.label(' · '.join(entry.reference_contract.best_for[:2])).classes('cui-workbench-note')
            if entry.reference_contract.avoid_for:
                with ui.element('div').classes('cui-studio-decision-card'):
                    ui.label('Avoid when').classes('cui-workbench-card__meta')
                    ui.label(' · '.join(entry.reference_contract.avoid_for[:1])).classes('cui-workbench-note')
        with ui.element('details').classes('cui-studio-reference-contract').props('data-reference-contract'):
            with ui.element('summary').props('tabindex="0"'):
                ui.label('Advanced contract · configuration, data, accessibility, and authority').classes('cui-workbench-section-title')
            ui.label(f'Authority · {entry.source_authority or "canonical NiceGUI Base registry"} · {entry.key}').classes('cui-workbench-note')
            ui.label('Live example' if contract.live_example else 'Explicit nonvisual variant').classes('cui-workbench-chip')
            if contract.nonvisual_variant:
                ui.label(contract.nonvisual_variant).classes('cui-workbench-note')
            for label, values in (
                ('Variants', contract.variants), ('Configuration', contract.configuration),
                ('Data / input contract', contract.data_contract), ('States', contract.states),
                ('Responsive behavior', contract.responsive_behavior), ('Accessibility', contract.accessibility),
                ('Best for', contract.best_for), ('Avoid for', contract.avoid_for),
                ('Requires', contract.requires), ('Produces', contract.produces),
                ('Alternatives', contract.alternatives), ('Complements', contract.complements),
                ('Domain tags', contract.domain_tags),
            ):
                ui.label(label).classes('cui-workbench-card__meta')
                ui.label(' · '.join(values)).classes('cui-workbench-note')
            ui.label(f'Example proof · {contract.example_proof}').classes('cui-workbench-note')
            CodeViewer(contract.recommended_code, language='python')
        _related_entry_links(entry)



_SECURITY_SPECIMEN_HINTS = ('auth','access','permission','policy','security','role','trusted','csrf','identity')
_RUNTIME_SPECIMEN_HINTS = ('cache','retry','health','runtime','async','lifecycle','provider','timeout','circuit')
_PERFORMANCE_SPECIMEN_HINTS = ('performance','debounce','throttle','batch','memo','virtual','lazy')
_DATA_SPECIMEN_HINTS = ('data_source','datasource','sql','sqlite','csv','query','schema','connector')


def studio_specimen_mode(entry: WorkbenchEntry) -> str:
    from .catalog_runtime import describe_entry
    return str(describe_entry(entry)['mode'])


def _render_contract_specimen(entry: WorkbenchEntry, mode: str) -> None:
    from nicegui import ui
    title = {
        'data': 'Data contract specimen',
        'security': 'Security contract specimen',
        'performance': 'Performance behavior specimen',
        'runtime': 'Runtime behavior specimen',
        'recipe': 'Composed recipe specimen',
        'component': 'Component contract specimen',
    }.get(mode, 'Capability contract specimen')
    registry = str(entry.metadata.get('registry_name') or '').replace('_', ' ').strip()
    with ui.element('section').classes('cui-studio-contract-specimen'):
        ui.label(title).classes('cui-workbench-section-title')
        ui.label(entry.description).classes('cui-workbench-note')
        with ui.element('div').classes('cui-studio-contract-specimen__meta'):
            if registry:
                ui.label(registry.title()).classes('cui-workbench-chip')
            if entry.category:
                ui.label(entry.category).classes('cui-workbench-chip')
            ui.label('Data-backed' if is_data_backed(entry) else 'No tabular data required').classes('cui-workbench-chip')
        authority = entry.source_authority or 'Canonical NiceGUI Base authority'
        ui.label(f'Authority · {authority}').classes('cui-workbench-note')
        if mode in {'runtime','security','performance','data'}:
            ui.label('Use the sections shown for this capability: live preview first, then only the data, controls, behavior, reference, and code contracts it actually supports.').classes('cui-workbench-note')

def _copy_button(label: str, text_supplier: Callable[[], str]):
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button
    def copy():
        ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(text_supplier())})')
    return Button(label, on_click=copy).element


def render_capability_studio(
    entry: WorkbenchEntry,
    *,
    preview_renderer: Callable[[StudioSession], None] | None = None,
    interaction_renderer: Callable[[StudioSession], None] | None = None,
    data_renderer: Callable[[StudioSession], None] | None = None,
    data_model: DataDockModel | None = None,
    active_route: str = '/catalog',
    reference_only: bool = True,
) -> StudioSession:
    """Render a reference session; legacy project handoff is opt-in only."""
    from nicegui import app, ui
    from nicegui_base.integrations.nicegui_components import Button, Select, TextInput
    from nicegui_base.integrations.nicegui_content import CodeViewer
    from nicegui_base.integrations.nicegui_layout import Tabs
    from nicegui_base.navigation import TabSpec
    from .catalog_runtime import describe_entry, example_rows, render_catalog_example, supported_options
    from .preview_data import checked_rows

    info = describe_entry(entry)
    session = StudioSession(
        entry,
        data_model if data_model is not None else DataDockModel(sample_rows_for_entry(entry), sample_name=f'{entry.title} sample'),
        StudioConfigModel(entry.title, options=default_studio_options(entry)),
    )
    draft_note = ''
    draft_state = {'token': None, 'dirty': False}
    export_policy = {'mode': 'schema_only'}
    if not reference_only:
        from .studio_state import DRAFT_STORAGE_KEY, draft_payload, restore_draft, token, save_draft as store_draft, remove_draft
        saved = app.storage.user.get(DRAFT_STORAGE_KEY, {})
        draft = saved.get(entry.key) if isinstance(saved, Mapping) else None
        draft_state['token'] = token(draft)
        if draft is not None and data_model is None:
            try:
                restored_data, cfg, export_mode = restore_draft(draft, title=entry.title)
                session.data = restored_data
                session.config = StudioConfigModel(cfg['title'], density=cfg['density'], responsive_width=cfg['responsive_width'], theme=cfg['theme'], options=cfg['options'])
                export_policy['mode'] = export_mode
                draft_note = 'Saved development draft restored (data and schema).'
            except (ValueError, TypeError, KeyError):
                draft_note = 'The saved draft could not be restored. Its original saved value was not changed.'
    # The live specimen is scoped to Preview so States/Code/Inspect never repeat
    # a large hidden-context preview above the selected tab.
    preview_host = None
    _header_metadata(entry)
    with ui.element('div').classes('cui-studio-status-row'):
        if reference_only:
            ui.label('Reference example · governed sample data stays on this page and never modifies a project.').classes('cui-workbench-note').props('role=\"status\" data-reference-example')
        else:
            from .project_state import render_entry_project_actions
            render_entry_project_actions(entry)
        draft_status = ui.label(
            draft_note or ('Draft not saved. Save explicitly before reloading.' if not reference_only else 'Live example is ready.')
        ).classes('cui-workbench-note').props('role=\"status\" aria-live=\"polite\" data-draft-status')
    callbacks: dict[str, Any] = {}
    controls: dict[str, Any] = {}
    syncing = {'value': False}
    code_revision = {'value': 0}

    def log(message: str) -> None:
        session.log(message)
        if callbacks.get('events'):
            callbacks['events']()

    def options() -> dict[str, Any]:
        return {**session.config.options, 'density': session.config.density}

    def default_preview() -> None:
        render_catalog_example(
            entry.key,
            title=session.config.title,
            rows=session.data.serializable_rows(),
            options=options(),
            on_event=log,
            show_reference=True,
            schema=session.data.schema_metadata(),
        )

    def render_preview() -> None:
        preview_host.clear()
        preview_host.style(replace=f'max-width:{RESPONSIVE_WIDTHS[session.config.responsive_width]}px')
        preview_host.props(f'data-theme="{session.config.theme}" data-density="{session.config.density}"')
        with preview_host:
            if info['mode'] not in {'pattern', 'analytical_sample', 'analytical_data'}:
                ui.label(session.config.title).classes('cui-workbench-section-title').props('data-preview-title')
            try:
                if preview_renderer:
                    preview_renderer(session)
                else:
                    default_preview()
            except ValueError as exc:
                from nicegui_base import Alert, FeedbackIntent
                Alert('Measurement mapping required', message=str(exc), intent=FeedbackIntent.WARNING)
        code_revision['value'] += 1
        if callbacks.get('code'):
            callbacks['code']()

    session.refresh_preview = render_preview

    def sync_controls() -> None:
        syncing['value'] = True
        try:
            values = {'title':session.config.title, 'density':session.config.density, 'theme':session.config.theme, 'width':session.config.responsive_width}
            values.update(session.config.options)
            for key, control in controls.items():
                value_key = {'preview_theme': 'theme', 'preview_density': 'density'}.get(key, key)
                if value_key in values:
                    control.element.set_value(values[value_key])
        finally:
            syncing['value'] = False

    def mark_dirty(_event=None):
        if syncing['value']: return
        draft_state['dirty'] = True
        draft_status.set_text('Unsaved reference changes; use the explicit export action if you want a runnable example.' if reference_only else 'Unsaved changes. Save draft before reloading.')

    tab_names = studio_tabs_for_entry(entry, data_renderer=data_renderer, interaction_renderer=interaction_renderer)
    with Tabs(tuple(TabSpec(tab, tab.title()) for tab in tab_names), value='preview') as tabs:
        def panel(tab_id: str):
            # Keep the shared rendering path simple while omitting unsupported tab
            # buttons.  Omitted panels are inert and hidden; they never become a
            # second visible reference surface.
            if tab_id in tab_names:
                return tabs.panel(tab_id)
            return ui.element('div').classes('cui-studio-omitted-panel').style('display:none')

        with tabs.panel('preview'):
            preview_host = ui.element('div').classes('cui-studio-preview-frame cui-studio-first-example').props(
                f'data-specimen="{info["mode"]}" data-reference-example-host'
            )
            with ui.element('div').classes('cui-workbench-toolbar cui-studio-preview-controls'):
                def width_changed(event):
                    if syncing['value']: return
                    value=str(event.value)
                    if value in RESPONSIVE_WIDTHS:
                        session.config.update(responsive_width=value); mark_dirty(); render_preview()
                controls['width']=Select('Preview width',{k:k.title() for k in RESPONSIVE_WIDTHS},value=session.config.responsive_width,clearable=False,on_change=width_changed)
                def theme_changed(event):
                    if syncing['value']:
                        return
                    value = str(getattr(event, 'value', 'system'))
                    if value in {'system', 'light', 'dark'}:
                        session.config.update(theme=value); mark_dirty(); render_preview()
                controls['preview_theme']=Select('Specimen theme', {'system':'System','light':'Light','dark':'Dark'}, value=session.config.theme, clearable=False, on_change=theme_changed)
                def density_changed(event):
                    if syncing['value']:
                        return
                    value = str(getattr(event, 'value', 'compact'))
                    if value in {'comfortable', 'compact', 'dense'}:
                        session.config.update(density=value); mark_dirty(); render_preview()
                controls['preview_density']=Select('Specimen density', {'comfortable':'Comfort','compact':'Compact','dense':'Dense'}, value=session.config.density, clearable=False, on_change=density_changed)
                Button('Refresh preview',on_click=render_preview)
                def reset():
                    session.config.reset(title=entry.title)
                    for key in supported_options(entry):
                        session.config.options[key] = False if key=='disabled' else ('single' if key=='selection' else '')
                    sync_controls();mark_dirty();log('Configuration reset');render_preview()
                Button('Reset configuration',on_click=reset)
                if not reference_only:
                    def save_draft():
                        try:
                            apply_config()
                            payload = draft_payload(session.data, session.config.frozen().normalized(), export_mode=export_policy['mode'])
                            draft_state['token'] = store_draft(app.storage.user, entry.key, payload, expected=draft_state['token'])
                            draft_state['dirty'] = False
                            draft_status.set_text('Draft saved: data, schema, configuration, and export policy.')
                            log('Development draft saved for this user')
                        except (ValueError, TypeError) as exc:
                            draft_status.set_text(f'Draft not saved: {exc}')
                    Button('Save draft',on_click=save_draft)
                    def delete_draft():
                        try:
                            remove_draft(app.storage.user, entry.key, expected=draft_state['token'])
                            draft_state['token'] = None
                            draft_state['dirty'] = True
                            draft_status.set_text('Saved draft removed. Current work remains open and unsaved.')
                        except ValueError as exc:
                            draft_status.set_text(f'Draft not removed: {exc}')
                    Button('Remove saved draft',on_click=delete_draft)
            if draft_note: ui.label(draft_note).classes('cui-workbench-note')
            ui.label('Examples operate on local development data. No production provider is changed.').classes('cui-workbench-note')
            if not reference_only:
                with ui.element('details').classes('cui-studio-event-log'):
                    with ui.element('summary'):
                        ui.label('Event / debug output')
                    event_host=ui.element('div').classes('cui-studio-event-log__events').props('aria-live="polite"')
                def render_events():
                    event_host.clear()
                    with event_host:
                        for line in reversed(session.event_log[-12:] or ['No events yet.']):
                            ui.label(line).classes('cui-workbench-note')
                callbacks['events']=render_events
                render_events()
            render_preview()
        with tabs.panel('usage'):
            ui.label('When to use').classes('cui-workbench-section-title')
            ui.label(' · '.join(entry.reference_contract.best_for or entry.use_when or (entry.description,))).classes('cui-workbench-note')
            ui.label('When to avoid').classes('cui-workbench-section-title')
            ui.label(' · '.join(entry.reference_contract.avoid_for or entry.avoid_when or ('Use a different registered authority when the data or interaction contract does not fit.',))).classes('cui-workbench-note')
            ui.label('Responsive and accessibility contract').classes('cui-workbench-section-title')
            ui.label(' · '.join((*entry.reference_contract.responsive_behavior[:2], *entry.reference_contract.accessibility[:2]))).classes('cui-workbench-note')
        with panel('data'):
            if data_renderer:
                data_renderer(session)
            elif info['uses_rows']:
                ui.label('Up to 5,000 rows / 2 MiB per example session. Larger datasets belong in a provider; imports never silently truncate rows.').classes('cui-workbench-note')
                def data_changed(_model):
                    measurement = controls.get('measurement')
                    if measurement is not None:
                        names = {'':'Automatic'}
                        names.update({n:n for n in session.data.snapshot.column_names})
                        current = session.config.options.get('measurement', '')
                        if current not in names:
                            current = ''
                            session.config.options['measurement'] = ''
                        measurement.element.set_options(names, value=current)
                    mark_dirty();log(f'Data revision {session.data.snapshot.revision}');render_preview()
                render_data_dock(session.data,on_change=data_changed)
            else:
                ui.label('This reference example does not accept tabular data. Its sample dataset or integration contract is described in Preview.').classes('cui-workbench-note')
        with panel('configure'):
            controls['title']=TextInput('Title',value=session.config.title)
            controls['title'].element.props('data-config-title')
            controls['density']=Select('Density',{'comfortable':'Comfortable','compact':'Compact','dense':'Dense'},value=session.config.density,clearable=False)
            for key in supported_options(entry):
                if key=='disabled':
                    controls[key]=Select('Disabled',{False:'Enabled',True:'Disabled'},value=session.config.options.get(key,False),clearable=False)
                elif key=='selection':
                    controls[key]=Select('Selection',{'none':'None','single':'Single','multiple':'Multiple'},value=session.config.options.get(key,'single'),clearable=False)
                elif key=='measurement':
                    names={'':'Automatic'};names.update({n:n for n in session.data.snapshot.column_names})
                    controls[key]=Select('Measurement field',names,value=session.config.options.get(key,''),clearable=False)
            def apply_config():
                session.config.update(title=str(controls['title'].element.value or entry.title), density=str(controls['density'].element.value),
                                      options={key:controls[key].element.value for key in supported_options(entry)})
                mark_dirty();log(f'Configuration revision {session.config.revision}');render_preview()
            for control in controls.values():
                control.element.on_value_change(mark_dirty)
            Button('Apply configuration',on_click=apply_config)
            ui.label('Only settings connected to this renderer are exposed. Global appearance is controlled by Preferences.').classes('cui-workbench-note')
        with panel('states'):
            host=ui.element('div').classes('cui-studio-state-host')
            def render_state_preview() -> None:
                try:
                    if preview_renderer:
                        preview_renderer(session)
                    else:
                        default_preview()
                except ValueError as exc:
                    from nicegui_base import Alert, FeedbackIntent
                    Alert('Measurement mapping required', message=str(exc), intent=FeedbackIntent.WARNING)
            render_state_matrix(host, render_state_preview)
        with panel('interactions'):
            if interaction_renderer:
                interaction_renderer(session)
            else:
                ui.label('Use the actual control in Preview. Actions appear in Event / debug output.').classes('cui-workbench-note')
                if not info['runnable']:
                    ui.label('This entry is an integration reference, not an interactive widget.').classes('cui-workbench-note')
        with tabs.panel('inspect'):
            from .interaction_inspector import render_interaction_inspector
            render_interaction_inspector(entry,session)
        with tabs.panel('code'):
            from .public_examples import production_example_code
            with ui.element('section').classes('cui-studio-public-code'):
                ui.label('Production public API').classes('cui-workbench-section-title')
                ui.label(
                    'Use this in application code. It imports the stable nicegui_base public surface; '
                    'the Reference Explorer harness is available below only for reproducing this reference session.'
                ).classes('cui-workbench-note')
                _copy_button('Copy Public API', lambda: production_example_code(entry))
                CodeViewer(production_example_code(entry), language='python')

            with ui.element('details').classes('cui-studio-harness-details'):
                with ui.element('summary').props('tabindex="0"'):
                    ui.label('Reference Explorer harness · advanced / reproducibility')
                ui.label(
                    'Open only when you need the Explorer-specific runtime, export policy, or reproducibility payload. '
                    'Normal application code should use the public API example above.'
                ).classes('cui-workbench-note')
                export_select = Select(
                    'Reference harness data policy',
                    {
                        'schema_only': 'Schema only (synthetic values)',
                        'include_development_rows': 'Include current development rows',
                    },
                    value=export_policy['mode'],
                    clearable=False,
                )
                export_select.element.props('data-export-policy')

                def export_changed(event):
                    export_policy['mode'] = event.value
                    mark_dirty()

                export_select.element.on_value_change(export_changed)
                code_host = ui.element('div').classes('cui-studio-code')

                def artifact():
                    return code_artifact(
                        entry,
                        session.config.frozen(),
                        data_columns=session.data.snapshot.column_names,
                        rows=session.data.serializable_rows(),
                    )

                def render_code():
                    code_host.clear()
                    try:
                        current = artifact()
                    except ValueError as exc:
                        with code_host:
                            ui.label(f'Cannot export: {exc}').props('role="alert"')
                        return

                    with code_host:
                        ui.label(
                            f'Current configuration revision {session.config.revision} · '
                            f'data revision {session.data.snapshot.revision}'
                        ).classes('cui-workbench-note').props('data-code-revision')
                        with ui.element('div').classes('cui-workbench-toolbar'):
                            _copy_button('Copy Explorer Harness', lambda: artifact().minimal)
                            _copy_button(
                                'Copy Reference Runtime' if info['runnable'] else 'Copy Integration Reference',
                                lambda: artifact().production,
                            )
                            if info['runnable']:
                                async def download():
                                    import asyncio
                                    from .codegen import generate_application_zip
                                    config = session.config.frozen()
                                    rows = session.data.serializable_rows()
                                    schema = session.data.schema_metadata()
                                    mode = export_policy['mode']
                                    try:
                                        payload = await asyncio.to_thread(
                                            generate_application_zip,
                                            entry,
                                            app_name=config.title or entry.title,
                                            config=config,
                                            rows=rows,
                                            data_schema=schema,
                                            data_mode=mode,
                                        )
                                        ui.download.content(payload, 'nicegui-base-example.zip')
                                        log(
                                            f'Reference harness ZIP generated ({mode}); '
                                            'install/run with the included bootstrap.py'
                                        )
                                    except (ValueError, RuntimeError) as exc:
                                        draft_status.set_text(f'Export failed: {exc}')

                                Button('Download reference harness ZIP', on_click=download)
                        CodeViewer(current.minimal, language='python')
                        ui.label(
                            'Reference runtime example — not the production public API shown above'
                            if info['runnable']
                            else 'Integration reference — no blank GUI is generated'
                        ).classes('cui-workbench-note')
                        CodeViewer(current.production, language='python')
                        CodeViewer(current.fragment.to_json(), language='json')

                callbacks['code'] = render_code
                render_code()
    return session


__all__ = [
    'RESPONSIVE_WIDTHS','STUDIO_TABS','StudioConfigModel','StudioSession','is_data_backed','render_capability_studio',
    'render_data_dock','sample_rows_for_entry','studio_session',
]
