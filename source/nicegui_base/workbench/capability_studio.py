from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .codegen import CapabilityConfiguration, code_artifact
from .data_dock import DEFAULT_ENGINEERING_SAMPLE, DataDockModel, DataDockSeverity, default_data_dock
from .models import WorkbenchEntry, WorkbenchKind
from .state_matrix import render_state_matrix


STUDIO_TABS = ('preview', 'data', 'configure', 'states', 'interactions', 'code')
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


def sample_rows_for_entry(entry: WorkbenchEntry) -> tuple[dict[str, Any], ...]:
    # One broad semiconductor-friendly fixture lets the same Data Dock demonstrate
    # tables/charts/engineering mappings without creating separate hidden datasets.
    if is_data_backed(entry):
        return tuple(dict(row) for row in DEFAULT_ENGINEERING_SAMPLE)
    return ()


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
    }.get(type_name, ColumnKind.TEXT)


def _read_upload_content(event) -> tuple[str, Any]:
    file_obj = getattr(event, 'file', None) or event
    name = str(getattr(file_obj, 'name', None) or getattr(event, 'name', None) or 'upload')
    content = getattr(file_obj, 'content', None) or getattr(event, 'content', None)
    return name, content


async def _read_all(content: Any) -> bytes:
    if content is None:
        return b''
    if isinstance(content, (bytes, bytearray, memoryview)):
        return bytes(content)
    read = getattr(content, 'read', None)
    if not callable(read):
        return b''
    value = read()
    if hasattr(value, '__await__'):
        value = await value
    return bytes(value or b'')


def render_data_dock(model: DataDockModel, *, on_change: Callable[[DataDockModel], Any] | None = None, mapping_targets: Sequence[str] = ()) -> None:
    """Render the reusable development Data Dock using governed controls/table authority."""
    from nicegui import ui
    from nicegui_base.data_table import EditableTableSpec, SelectionMode, TableColumn
    from nicegui_base.integrations.nicegui_components import Button, FileUpload, Select, TextArea, TextInput
    from nicegui_base.integrations.nicegui_data_table import EditableTable
    from nicegui_base.integrations.nicegui_layout import SegmentedControl

    content_host = ui.element('div').classes('cui-data-dock-content')
    mode = {'value': 'sample'}

    async def changed() -> None:
        if on_change is not None:
            result = on_change(model)
            if hasattr(result, '__await__'):
                await result
        render_mode()

    async def mutate(action: Callable[[], Any]) -> None:
        action()
        await changed()

    def status_strip() -> None:
        snap = model.snapshot
        with ui.element('div').classes('cui-data-dock-summary'):
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

    def render_edit_grid() -> None:
        status_strip()
        if not model.columns:
            ui.label('No columns to edit. Paste or upload data first.').classes('cui-workbench-note')
            return
        rows = [dict(row, __wb_row=index) for index, row in enumerate(model.rows)]
        columns = [TableColumn('__wb_row', '#', kind=_column_kind('integer'), visible=False)]
        columns.extend(TableColumn(column.name, column.name, kind=_column_kind(column.inferred_type), editable=True) for column in model.columns)
        spec = EditableTableSpec(tuple(columns), row_key='__wb_row', title='Development data', selection=SelectionMode.SINGLE, persist_state=False)

        async def save_edit(row, key, value):
            if key == '__wb_row':
                return
            model.edit_cell(int(row['__wb_row']), str(key), value)
            if on_change:
                result = on_change(model)
                if hasattr(result, '__await__'):
                    await result

        EditableTable(rows, columns, spec=spec, save_edit=save_edit)
        with ui.element('div').classes('cui-workbench-toolbar'):
            Button('Add row', on_click=lambda: mutate(model.add_row))
            Button('Delete last row', disabled=not bool(model.rows), on_click=lambda: mutate(lambda: model.delete_row(len(model.rows)-1)))
            Button('Undo', disabled=not model.can_undo, on_click=lambda: mutate(model.undo))
            Button('Redo', disabled=not model.can_redo, on_click=lambda: mutate(model.redo))
        ui.label('AG Grid keyboard navigation and multi-cell copy remain owned by the canonical table authority. Rectangular Ctrl/Cmd+V paste is available below.').classes('cui-workbench-note')
        paste = TextArea('Rectangular paste', placeholder='Paste cells copied from Excel here…', rows=3)
        async def apply_rectangle():
            text = str(getattr(paste.element, 'value', '') or '')
            if text.strip():
                model.rectangular_paste(0, 0, text)
                await changed()
        Button('Paste into top-left', on_click=apply_rectangle)

    def render_mapping() -> None:
        status_strip()
        ui.label('Schema & semantic roles').classes('cui-workbench-section-title')
        for column in model.columns:
            with ui.element('article').classes('cui-data-dock-column'):
                ui.label(column.name).classes('cui-workbench-card__title')
                ui.label(f'{column.inferred_type} · {column.role} · {column.confidence:.0%} confidence').classes('cui-workbench-note')
                with ui.element('div').classes('cui-data-dock-column__controls'):
                    name_input = TextInput('Column name', value=column.name)
                    type_select = Select('Type', {key:key.title() for key in ('string','integer','float','boolean','date','datetime','category','json','unknown')}, value=column.inferred_type, clearable=False)
                    role_select = Select('Semantic role', {key:key.title() for key in ('dimension','measurement','identifier','timestamp','entity','attribute')}, value=column.role, clearable=False)
                    async def apply_col(_e=None, original=column.name, n=name_input, t=type_select, r=role_select, inferred=column.inferred_type, role=column.role):
                        current_name = original
                        new_name = str(getattr(n.element, 'value', original) or original).strip()
                        if new_name != original:
                            model.rename_column(original, new_name)
                            current_name = new_name
                        model.set_column_type(current_name, str(getattr(t.element, 'value', inferred)))
                        model.set_semantic_role(current_name, str(getattr(r.element, 'value', role)))
                        await changed()
                    Button('Apply', on_click=apply_col)
        if mapping_targets:
            ui.label('Logical mapping targets').classes('cui-workbench-section-title')
            ui.label(', '.join(mapping_targets)).classes('cui-workbench-note')

    def render_paste() -> None:
        paste = TextArea('Paste data', placeholder='Paste TSV from Excel, CSV, or a JSON array of objects…', rows=12)
        result_host = ui.element('div')
        async def analyze():
            text = str(getattr(paste.element, 'value', '') or '')
            result = model.load_text(text, source_name='Pasted data')
            result_host.clear()
            with result_host:
                if result.ok:
                    ui.label(f'Detected {result.detected_format.value.upper()} · {model.snapshot.quality.rows} rows · {model.snapshot.quality.columns} columns').classes('cui-workbench-note')
                    if on_change:
                        value = on_change(model)
                        if hasattr(value, '__await__'):
                            await value
                    render_mode()
                else:
                    for issue in result.issues:
                        ui.label(issue.message).classes('cui-workbench-note')
        Button('Analyze pasted data', on_click=analyze)
        with result_host:
            ui.label('Format is detected immediately when you analyze the paste.').classes('cui-workbench-note')

    def render_upload() -> None:
        result_host = ui.element('div')
        async def uploaded(event):
            name, content = _read_upload_content(event)
            data = await _read_all(content)
            result = model.load_bytes(data, filename=name)
            result_host.clear()
            with result_host:
                if result.ok:
                    ui.label(f'Loaded {name} · {model.snapshot.quality.rows} rows').classes('cui-workbench-note')
                    if on_change:
                        value = on_change(model)
                        if hasattr(value, '__await__'):
                            await value
                    render_mode()
                else:
                    for issue in result.issues:
                        ui.label(issue.message).classes('cui-workbench-note')
        FileUpload(label='Upload CSV or JSON', accept=('.csv','.json','.tsv'), max_file_size_mb=25, on_upload=uploaded)
        with result_host:
            ui.label('Uploads use the canonical NiceGUI Base upload policy before parsing.').classes('cui-workbench-note')

    def render_mode() -> None:
        content_host.clear()
        with content_host:
            value = mode['value']
            if value == 'sample':
                with ui.element('div').classes('cui-workbench-toolbar'):
                    Button('Reset to sample', on_click=lambda: mutate(model.reset_sample))
                render_edit_grid()
            elif value == 'paste':
                render_paste()
            elif value == 'upload':
                render_upload()
            else:
                render_edit_grid()
                render_mapping()

    def mode_changed(event):
        mode['value'] = str(getattr(event, 'value', 'sample'))
        render_mode()

    SegmentedControl({'sample':'Sample','paste':'Paste','upload':'Upload','edit-map':'Edit / Map'}, value='sample', on_change=mode_changed)
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
    with ui.element('section').classes('cui-studio-header'):
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
        with ui.element('div').classes('cui-workbench-chiprow'):
            ui.label(entry.source_authority or 'Canonical NiceGUI Base authority').classes('cui-workbench-chip')
            ui.label(entry.key).classes('cui-workbench-chip')
            if entry.live_preview:
                ui.label('Live preview').classes('cui-workbench-chip')
            if entry.sample_data:
                ui.label('Sample data').classes('cui-workbench-chip')
        if entry.use_when:
            ui.label('Use when').classes('cui-workbench-section-title')
            ui.label(' · '.join(entry.use_when)).classes('cui-workbench-note')
        if entry.avoid_when:
            ui.label('Avoid when').classes('cui-workbench-section-title')
            ui.label(' · '.join(entry.avoid_when)).classes('cui-workbench-note')
        _related_entry_links(entry)


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
) -> StudioSession:
    """Render one standardized Capability Studio inside an already-open Workbench shell."""
    from nicegui import app, ui
    from nicegui_base.integrations.nicegui_components import Button, Select, TextInput
    from nicegui_base.integrations.nicegui_content import CodeViewer
    from nicegui_base.integrations.nicegui_layout import SegmentedControl, Tabs
    from nicegui_base.navigation import TabSpec

    session = StudioSession(entry, data_model or DataDockModel(sample_rows_for_entry(entry), sample_name=f'{entry.title} sample'), StudioConfigModel(entry.title))
    _header_metadata(entry)
    from .project_state import render_entry_project_actions
    render_entry_project_actions(entry)

    preview_host = ui.element('div').classes('cui-studio-preview-frame').props(f'data-theme="{session.config.theme}" data-density="{session.config.density}"')
    preview_host.style(f'max-width:{RESPONSIVE_WIDTHS[session.config.responsive_width]}px')

    def default_preview() -> None:
        if entry.kind is WorkbenchKind.ANALYTIC:
            from .app import _render_surface_preview
            _render_surface_preview(str(entry.metadata.get('surface_key')), entry.category)
        elif entry.kind is WorkbenchKind.PATTERN:
            reference = entry.metadata.get('reference_route') or entry.metadata.get('legacy_route')
            if reference:
                ui.html(f'<iframe class="cui-studio-iframe" title={json.dumps(entry.title)} src={json.dumps(str(reference))}></iframe>', sanitize=False)
            else:
                ui.label('Pattern sample is generated from the canonical page-pattern contract.').classes('cui-workbench-note')
        else:
            reference = entry.metadata.get('reference_route')
            if reference:
                ui.html(f'<iframe class="cui-studio-iframe" title={json.dumps(entry.title)} src={json.dumps(str(reference))}></iframe>', sanitize=False)
            else:
                ui.label(entry.description).classes('cui-workbench-preview-empty')

    def render_preview() -> None:
        preview_host.clear()
        preview_host.style(replace=f'max-width:{RESPONSIVE_WIDTHS[session.config.responsive_width]}px')
        with preview_host:
            ui.label(session.config.title).classes('cui-workbench-section-title')
            (preview_renderer or (lambda _session: default_preview()))(session)

    session.refresh_preview = render_preview

    tab_specs = tuple(TabSpec(tab, tab.replace('_',' ').title()) for tab in STUDIO_TABS)
    with Tabs(tab_specs, value='preview') as tabs:
        with tabs.panel('preview'):
            event_host = ui.element('div').classes('cui-studio-event-log__events')

            def render_events() -> None:
                event_host.clear()
                with event_host:
                    if not session.event_log:
                        ui.label('No events yet.').classes('cui-workbench-note')
                    else:
                        for line in reversed(session.event_log[-12:]):
                            ui.label(line).classes('cui-workbench-note')

            def log(message: str) -> None:
                session.log(message)
                render_events()

            def width_changed(event):
                value = str(getattr(event, 'value', 'desktop'))
                if value in RESPONSIVE_WIDTHS:
                    session.config.update(responsive_width=value)
                    log(f'Preview width → {value}')
                    render_preview()

            def theme_changed(event):
                value = str(getattr(event, 'value', 'system'))
                if value not in {'system','light','dark'}:
                    return
                session.config.update(theme=value)
                preview_host.props(f'data-theme="{value}"')
                log(f'Preview theme → {value}')
                render_preview()

            async def density_changed(event):
                value = str(getattr(event, 'value', 'compact'))
                if value not in {'comfortable','compact','dense'}:
                    return
                session.config.update(density=value)
                preview_host.props(f'data-density="{value}"')
                log(f'Preview density → {value}')
                render_preview()

            def refresh_preview():
                log('Preview refreshed')
                render_preview()

            def reset_preview():
                session.config.reset(title=entry.title)
                preview_host.props('data-theme="system" data-density="compact"')
                log('Configuration reset')
                render_preview()

            with ui.element('div').classes('cui-workbench-toolbar cui-studio-preview-controls'):
                Select(
                    'Preview width', {key:key.replace('_',' ').title() for key in RESPONSIVE_WIDTHS},
                    value=session.config.responsive_width, clearable=False, on_change=width_changed,
                )
                SegmentedControl({'system':'System','light':'Light','dark':'Dark'}, value=session.config.theme, on_change=theme_changed)
                SegmentedControl({'comfortable':'Comfort','compact':'Compact','dense':'Dense'}, value=session.config.density, on_change=density_changed)
                Button('Refresh', on_click=refresh_preview)
                Button('Reset', on_click=reset_preview)
            render_preview()
            with ui.element('details').classes('cui-studio-event-log'):
                with ui.element('summary').classes('cui-workbench-note').props('tabindex="0"'):
                    ui.label('Event / debug output')
                render_events()
        with tabs.panel('data'):
            if data_renderer is not None:
                data_renderer(session)
            elif is_data_backed(entry):
                def data_changed(_model):
                    session.log(f'Data revision {session.data.snapshot.revision}')
                    render_preview()
                render_data_dock(session.data, on_change=data_changed)
            else:
                ui.label('This capability does not require tabular development data.').classes('cui-workbench-note')
                ui.label('Sample mode is intentionally not fabricated for non-data-backed capabilities.').classes('cui-workbench-note')
        with tabs.panel('configure'):
            ui.label('Governed configuration').classes('cui-workbench-section-title')
            title_field = TextInput('Title', value=session.config.title)
            density = Select('Density', {'comfortable':'Comfortable','compact':'Compact','dense':'Dense'}, value=session.config.density, clearable=False)
            option_fields: dict[str, Any] = {}
            if entry.kind is WorkbenchKind.ANALYTIC:
                option_fields['measurement'] = Select(
                    'Measurement field', {name:name for name in session.data.snapshot.column_names} or {'value':'value'},
                    value=(session.data.snapshot.column_names[-1] if session.data.snapshot.column_names else 'value'), clearable=False,
                    description='Select the governed measurement/value field used by this development preview.',
                )
                option_fields['show_limits'] = Select('Limit context', {'auto':'Auto','on':'Show limits','off':'Hide limits'}, value='auto', clearable=False)
                ui.label('Analytical configuration exposes semantic fields/limits/context only; raw ECharts or Quasar props are intentionally unavailable.').classes('cui-workbench-note')
            elif entry.kind is WorkbenchKind.PATTERN:
                option_fields['content_density'] = Select('Composition density', {'focused':'Focused','balanced':'Balanced','dense':'Dense analysis'}, value='balanced', clearable=False)
                option_fields['details'] = Select('Detail treatment', {'auto':'Pattern default','inline':'Inline','drawer':'Contextual drawer'}, value='auto', clearable=False)
                ui.label('Pattern configuration changes governed composition choices; it is not a freeform pixel canvas.').classes('cui-workbench-note')
            elif str(entry.metadata.get('registry_name') or '') == 'tables' or 'table' in entry.key.casefold():
                option_fields['selection'] = Select('Selection', {'none':'None','single':'Single','multiple':'Multiple'}, value='single', clearable=False)
                option_fields['editing'] = Select('Editing', {'off':'Read only','cell':'Cell editing'}, value='off', clearable=False)
            elif entry.kind is WorkbenchKind.RECIPE:
                option_fields['optional_panels'] = Select('Optional panels', {'available':'Show when data supports','hide':'Hide optional panels'}, value='available', clearable=False)

            def apply_config():
                options = {key: getattr(control.element, 'value', None) for key, control in option_fields.items()}
                session.config.update(
                    title=str(getattr(title_field.element,'value',entry.title) or entry.title),
                    density=str(getattr(density.element,'value','compact')), options=options,
                )
                session.log(f'Configuration revision {session.config.revision}')
                render_preview()
            Button('Apply configuration', on_click=apply_config)
        with tabs.panel('states'):
            state_host = ui.element('div').classes('cui-studio-state-host')
            render_state_matrix(state_host, lambda: (preview_renderer or (lambda _session: default_preview()))(session))
        with tabs.panel('interactions'):
            ui.label('Governed interactions').classes('cui-workbench-section-title')
            if interaction_renderer:
                interaction_renderer(session)
            else:
                metadata = entry.metadata
                facts = []
                if metadata.get('linked_hover'):
                    facts.append('Linked hover')
                if metadata.get('spatial'):
                    facts.append('Spatial selection')
                facts.extend(entry.tags)
                if facts:
                    for fact in dict.fromkeys(str(value) for value in facts):
                        ui.label(f'• {fact}').classes('cui-workbench-note')
                else:
                    ui.label('No additional interaction contract is declared for this capability.').classes('cui-workbench-note')
        with tabs.panel('code'):
            code_host = ui.element('div').classes('cui-studio-code')
            def render_code() -> None:
                code_host.clear()
                artifact = code_artifact(entry, session.config.frozen(), data_columns=session.data.snapshot.column_names)
                with code_host:
                    with ui.element('div').classes('cui-workbench-toolbar'):
                        _copy_button('Copy Minimal', lambda: artifact.minimal)
                        _copy_button('Copy Production', lambda: artifact.production)
                        def add_to_starter():
                            try:
                                current = list(app.storage.tab.get('nicegui_base_workbench_starter', []))
                                current.append(artifact.fragment.to_dict())
                                app.storage.tab['nicegui_base_workbench_starter'] = current[-30:]
                                session.log('Added capability to Builder starter composition')
                            except Exception:
                                session.log('Starter composition could not be persisted in this runtime')
                        Button('Add to Starter', on_click=add_to_starter)
                        if artifact.cli_equivalent:
                            _copy_button('CLI Equivalent', lambda: artifact.cli_equivalent or '')
                        if entry.kind in {WorkbenchKind.PATTERN, WorkbenchKind.RECIPE}:
                            def download_starter():
                                from .codegen import generate_application_zip
                                data = generate_application_zip(entry, app_name=session.config.title or entry.title, config=session.config.frozen())
                                filename = (session.config.title or entry.title).lower().replace(' ', '-') + '.zip'
                                ui.download.content(data, filename)
                                session.log('Generated governed starter ZIP')
                            Button('Generate Starter ZIP', on_click=download_starter)
                    ui.label('Minimal').classes('cui-workbench-section-title')
                    CodeViewer(artifact.minimal, language='python')
                    ui.label('Production').classes('cui-workbench-section-title')
                    CodeViewer(artifact.production, language='python')
                    ui.label('Builder fragment').classes('cui-workbench-section-title')
                    CodeViewer(artifact.fragment.to_json(), language='json')
            render_code()
    return session


__all__ = [
    'RESPONSIVE_WIDTHS','STUDIO_TABS','StudioConfigModel','StudioSession','is_data_backed','render_capability_studio',
    'render_data_dock','sample_rows_for_entry','studio_session',
]
