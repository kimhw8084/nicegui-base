"""Canonical application-pattern specimens built from governed production APIs."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any


PATTERN_CLASSES = {
    'dashboard': 'DashboardPage',
    'data_explorer': 'DataExplorerPage',
    'master_detail': 'MasterDetailPage',
    'crud': 'CrudPage',
    'monitoring': 'MonitoringPage',
    'search': 'SearchPage',
    'settings': 'SettingsPage',
    'wizard': 'WizardPage',
    'comparison': 'ComparisonPage',
    'analysis_workspace': 'AnalysisWorkspacePage',
}


# Machine-readable anatomy is also exposed in the rendered DOM. Browser acceptance
# checks use these stable semantic names instead of accepting a mounted page shell.
PATTERN_SEMANTIC_ANATOMY: dict[str, tuple[str, ...]] = {
    'dashboard': ('kpis', 'trend', 'exceptions'),
    'data_explorer': ('filters', 'primary_table', 'selected_detail'),
    'master_detail': ('master', 'selected_detail'),
    'crud': ('create', 'read', 'update', 'delete', 'validation'),
    'monitoring': ('status_kpis', 'health_trend', 'alerts', 'supporting_data'),
    'search': ('query', 'facets', 'results', 'selected_context', 'empty_state'),
    'settings': ('section_navigation', 'settings_form', 'dirty_state', 'save', 'reset', 'validation'),
    'wizard': ('progress', 'back', 'next', 'validation', 'review'),
    'comparison': ('populations', 'delta', 'comparison_visual', 'aligned_evidence'),
    'analysis_workspace': ('analysis_filters', 'primary_visual', 'supporting_table', 'selected_inspector'),
}


_PATTERN_ROWS = (
    {'id': 'LOT-240901', 'tool': 'ETCH-03', 'chamber': 'A', 'recipe': 'POLY-7', 'thickness': 101.2, 'status': 'Normal'},
    {'id': 'LOT-240902', 'tool': 'ETCH-03', 'chamber': 'B', 'recipe': 'POLY-7', 'thickness': 102.1, 'status': 'Review'},
    {'id': 'LOT-240903', 'tool': 'ETCH-07', 'chamber': 'A', 'recipe': 'OX-2', 'thickness': 99.7, 'status': 'Normal'},
    {'id': 'LOT-240904', 'tool': 'ETCH-07', 'chamber': 'B', 'recipe': 'OX-2', 'thickness': 104.8, 'status': 'Alert'},
    {'id': 'LOT-240905', 'tool': 'ETCH-03', 'chamber': 'A', 'recipe': 'POLY-7', 'thickness': 100.5, 'status': 'Normal'},
    {'id': 'LOT-240906', 'tool': 'ETCH-11', 'chamber': 'C', 'recipe': 'VIA-4', 'thickness': 98.9, 'status': 'Review'},
    {'id': 'LOT-240907', 'tool': 'ETCH-11', 'chamber': 'C', 'recipe': 'VIA-4', 'thickness': 103.4, 'status': 'Normal'},
    {'id': 'LOT-240908', 'tool': 'ETCH-07', 'chamber': 'A', 'recipe': 'OX-2', 'thickness': 105.6, 'status': 'Alert'},
)


def _records(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    incoming = [dict(row) for row in rows]
    required = {'id', 'tool', 'chamber', 'recipe', 'thickness', 'status'}
    return incoming if len(incoming) >= 6 and all(required <= set(row) for row in incoming) else [dict(row) for row in _PATTERN_ROWS]


def render_pattern(key: str, *, title: str, rows: Sequence[Mapping[str, Any]], on_event: Callable[[str], Any] | None = None):
    """Render one bounded, pattern-specific reference composition.

    Examples deliberately keep state local: they teach governed composition without
    mutating an application provider or masquerading as production conclusions.
    """
    if key not in PATTERN_CLASSES:
        raise KeyError(key)

    from nicegui import ui
    from nicegui_base import patterns
    from nicegui_base.components import ButtonIntent, StatusIntent
    from nicegui_base.content import ComparisonItem, KeyValueItem, SearchResultSpec, StepSpec, StepState, TrendDirection
    from nicegui_base.integrations.nicegui_components import Button, SearchInput, Select, Switch, TextInput
    from nicegui_base.integrations.nicegui_content import (
        ComparePanel,
        ComparisonMetric,
        DifferenceTable,
        MetricCard,
        MetricStrip,
        ProgressSteps,
        PropertyGrid,
        SearchResults,
    )
    from nicegui_base.integrations.nicegui_interactions import DangerConfirmDialog, Form, FormActions, FormField, FormSection
    from nicegui_base.integrations.nicegui_visualization import BarChart, LineChart
    from nicegui_base.layouts import LayoutSlot
    from nicegui_base.visualization import AxisSpec, AxisType, ChartSize, SeriesSpec
    from .visual_specimens import render_table

    records = _records(rows)
    emit = on_event or (lambda _message: None)

    def region(name: str, *, classes: str = ''):
        return ui.element('section').classes(f'cui-reference-region {classes}'.strip()).props(
            f'data-pattern-region="{name}" aria-label="{name.replace("_", " ").title()}"'
        )

    def trend_chart(chart_title: str, values: Sequence[float], *, label: str = 'Thickness'):
        return LineChart(
            chart_title,
            (SeriesSpec('trend', label, tuple(values)),),
            size=ChartSize.COMPACT,
            x_axis=AxisSpec(label='Lot sequence', kind=AxisType.CATEGORY, categories=tuple(row['id'] for row in records[: len(values)])),
            y_axis=AxisSpec(label=label, unit='nm'),
        )

    page_class = getattr(patterns, PATTERN_CLASSES[key])
    description = {
        'dashboard': 'At-a-glance process performance with trends and exceptions.',
        'data_explorer': 'Filter records, inspect the governed table, and retain selected context.',
        'master_detail': 'Browse lots while the selected lot remains visible beside the master list.',
        'crud': 'Create, read, update, validate, and safely delete managed records.',
        'monitoring': 'Lead with operational health, trend, alerts, and supporting evidence.',
        'search': 'Query and refine entity results without making an empty state the default.',
        'settings': 'Navigate settings, edit governed fields, validate, save, and reset local state.',
        'wizard': 'Complete a bounded task with progress, validation, review, Back, and Next.',
        'comparison': 'Align two populations and make deltas and evidence immediately comparable.',
        'analysis_workspace': 'Keep analysis controls, visualization, records, and selected context together.',
    }[key]

    with page_class(title, description) as page:
        page._page.element.props(  # PatternPage owns this root; annotate its governed anatomy for acceptance.
            f'data-pattern-semantic="{key}" data-pattern-regions="{" ".join(PATTERN_SEMANTIC_ANATOMY[key])}"'
        )

        if key == 'dashboard':
            with page.slot(LayoutSlot.METRICS):
                with region('kpis'), MetricStrip():
                    MetricCard('Lots today', 128, delta='+6%', trend=TrendDirection.UP, description='Across three qualified tools')
                    MetricCard('In control', '96.9%', delta='+0.8 pp', trend=TrendDirection.UP, intent=StatusIntent.SUCCESS)
                    MetricCard('Open exceptions', 3, description='Two require engineer review', intent=StatusIntent.WARNING)
            with page.slot(LayoutSlot.PRIMARY):
                with region('trend'):
                    trend_chart('Thickness trend — last eight lots', [float(row['thickness']) for row in records])
            with page.slot(LayoutSlot.DATA):
                with region('exceptions'):
                    render_table('data_table', title='Recent exceptions', rows=[row for row in records if row['status'] != 'Normal'][:4], on_event=on_event)

        elif key == 'data_explorer':
            state = {'query': '', 'tool': 'all'}
            host_ref: dict[str, Any] = {}

            def draw_explorer():
                host = host_ref.get('host')
                if host is None:
                    return
                selected = [row for row in records if (state['tool'] == 'all' or row['tool'] == state['tool']) and state['query'] in str(row).casefold()]
                host.clear()
                with host:
                    render_table('data_table', title=f'Lot records ({len(selected)})', rows=selected, on_event=on_event)

            with page.slot(LayoutSlot.FILTERS):
                with region('filters'):
                    with ui.row().classes('cui-filter-bar'):
                        SearchInput('Search lots', value='LOT', on_change=lambda event: (state.update(query=str(event.value or '').casefold()), draw_explorer()))
                        Select('Tool', {'all': 'All tools', 'ETCH-03': 'ETCH-03', 'ETCH-07': 'ETCH-07', 'ETCH-11': 'ETCH-11'}, value='all', on_change=lambda event: (state.update(tool=str(event.value or 'all')), draw_explorer()))
            with page.slot(LayoutSlot.DATA):
                with region('primary_table'):
                    host_ref['host'] = ui.element('div').classes('w-full')
                    draw_explorer()
            with page.slot(LayoutSlot.DETAILS):
                with region('selected_detail'):
                    ui.label('Selected lot').classes('cui-section-title')
                    PropertyGrid(tuple(KeyValueItem(str(name), str(name).replace('_', ' ').title(), value) for name, value in records[1].items()))

        elif key == 'master_detail':
            with page.slot(LayoutSlot.FILTERS):
                SearchInput('Find lot or tool', value='ETCH')
            with page.slot(LayoutSlot.DATA):
                with region('master'):
                    render_table('data_table', title='Master lots', rows=records[:6], on_event=on_event)
            with page.slot(LayoutSlot.DETAILS):
                with region('selected_detail'):
                    ui.label('LOT-240902').classes('cui-section-title')
                    ui.label('Selected from the master list').classes('cui-workbench-note')
                    PropertyGrid(tuple(KeyValueItem(str(name), str(name).replace('_', ' ').title(), value) for name, value in records[1].items()))
                    Button('Open lot history', intent=ButtonIntent.SECONDARY, on_click=lambda: emit('Opened selected lot history'))

        elif key == 'crud':
            local = [dict(row) for row in records[:5]]
            table_host_ref: dict[str, Any] = {}
            status_ref: dict[str, Any] = {}

            def draw_crud():
                table_host = table_host_ref.get('host')
                if table_host is None:
                    return
                table_host.clear()
                with table_host:
                    render_table('data_table', title=f'Managed recipes ({len(local)})', rows=local, on_event=on_event)

            def create_record():
                local.append({'id': f'LOT-NEW-{len(local) + 1}', 'tool': 'ETCH-03', 'chamber': 'A', 'recipe': 'DRAFT', 'thickness': 100.0, 'status': 'Draft'})
                draw_crud()
                if status_ref.get('status'): status_ref['status'].set_text('Draft record created locally')
                emit('Draft record created')

            def delete_record():
                if local:
                    local.pop(0)
                draw_crud()
                if status_ref.get('status'): status_ref['status'].set_text('Selected record deleted from local specimen')
                emit('Record deleted')

            delete_dialog = DangerConfirmDialog(
                'Delete selected recipe?',
                description='This reference requires explicit confirmation before the local destructive action.',
                typed_confirmation='DELETE',
                on_confirm=delete_record,
            )
            with page.slot(LayoutSlot.FILTERS):
                SearchInput('Search managed recipes', value='POLY')
            with page.slot(LayoutSlot.ACTIONS):
                with region('create'):
                    with ui.row().classes('cui-action-row'):
                        Button('Create recipe', intent=ButtonIntent.PRIMARY, on_click=create_record)
                        Button('Delete selected…', intent=ButtonIntent.DANGER, on_click=delete_dialog.open)
            with page.slot(LayoutSlot.DATA):
                with region('read'):
                    table_host_ref['host'] = ui.element('div').classes('w-full')
                    draw_crud()
            with page.slot(LayoutSlot.DETAILS):
                with region('update'):
                    ui.label('Edit selected recipe').classes('cui-section-title')
                    form = Form('recipe-editor', title='Edit selected recipe')
                    with form:
                        with FormSection('Recipe identity', description='Required fields validate before saving.'):
                            with FormField('name', 'Recipe name', required=True):
                                name = TextInput('Recipe name', value='POLY-7', required=True)
                            with region('validation'):
                                TextInput('Qualified owner', value='', required=True, error='Owner is required before qualification.')
                            Select('Status', {'draft': 'Draft', 'qualified': 'Qualified'}, value='draft')
                        FormActions(primary_label='Save changes', secondary_label='Reset', form=form, on_primary=lambda: (status_ref['status'].set_text(f'Saved {name.element.value} locally'), emit('Recipe updated')), on_secondary=lambda: status_ref['status'].set_text('Form reset to saved values'))
                    status_ref['status'] = ui.label('No unsaved changes').classes('cui-workbench-note')
                with region('delete'):
                    ui.label('Destructive actions use the governed typed-confirmation dialog.').classes('cui-workbench-note')

        elif key == 'monitoring':
            with page.slot(LayoutSlot.METRICS):
                with region('status_kpis'), MetricStrip():
                    MetricCard('Fleet health', '11 / 12', intent=StatusIntent.WARNING, description='One chamber requires review')
                    MetricCard('Active alarms', 2, intent=StatusIntent.DANGER, description='Both acknowledged')
                    MetricCard('Data freshness', '18 s', intent=StatusIntent.SUCCESS, description='Within 60 s objective')
            with page.slot(LayoutSlot.PRIMARY):
                with region('health_trend'):
                    trend_chart('Chamber pressure health — last eight samples', [2.1, 2.2, 2.15, 2.4, 2.35, 2.8, 2.55, 2.3], label='Pressure')
            with page.slot(LayoutSlot.SECONDARY):
                with region('alerts'):
                    ui.label('Active alerts').classes('cui-section-title')
                    SearchResults((
                        SearchResultSpec('ALM-1042', 'Pressure drift', 'ETCH-07 · Chamber B', 'Above warning limit for three consecutive samples.', status='warning'),
                        SearchResultSpec('ALM-1046', 'Endpoint delay', 'ETCH-11 · Chamber C', 'Median endpoint shifted +4.2 seconds.', status='warning'),
                    ))
            with page.slot(LayoutSlot.DATA):
                with region('supporting_data'):
                    render_table('data_table', title='Affected recent lots', rows=[records[3], records[5], records[7]], on_event=on_event)

        elif key == 'search':
            results = tuple(
                SearchResultSpec(str(row['id']), str(row['id']), f"{row['tool']} · Chamber {row['chamber']}", f"{row['recipe']} · {row['thickness']} nm · {row['status']}")
                for row in records[:5]
            )
            with page.slot(LayoutSlot.FILTERS):
                with region('query'):
                    SearchInput('Search lots, tools, or recipes', value='ETCH', placeholder='e.g. chamber drift')
                with region('facets'):
                    Select('Status facet', {'all': 'Any status', 'normal': 'Normal', 'review': 'Review', 'alert': 'Alert'}, value='all')
            with page.slot(LayoutSlot.DATA):
                with region('results'):
                    ui.label('5 representative results for “ETCH”').classes('cui-section-title')
                    SearchResults(results, on_select=lambda result: emit(f'Selected {result.key}'))
                with region('empty_state'):
                    ui.label('No-result behavior').classes('cui-property__label')
                    ui.label('A cleared, actionable empty state appears only when a query has no matches.').classes('cui-workbench-note')
            with page.slot(LayoutSlot.DETAILS):
                with region('selected_context'):
                    ui.label('Selected result context').classes('cui-section-title')
                    PropertyGrid((
                        KeyValueItem('id', 'Lot', records[0]['id']),
                        KeyValueItem('tool', 'Tool', records[0]['tool']),
                        KeyValueItem('recipe', 'Recipe', records[0]['recipe']),
                        KeyValueItem('status', 'Disposition', records[0]['status']),
                    ))

        elif key == 'settings':
            save_state_ref: dict[str, Any] = {}
            with page.slot(LayoutSlot.NAVIGATION):
                with region('section_navigation'):
                    ui.label('Settings sections').classes('cui-section-title')
                    for item in ('Data refresh', 'Notifications', 'Display defaults'):
                        Button(item, intent=ButtonIntent.GHOST, full_width=True, on_click=lambda _e=None, name=item: emit(f'Opened {name}'))
            with page.slot(LayoutSlot.CONTENT):
                with region('settings_form'):
                    form = Form('monitoring-settings', title='Monitoring defaults')
                    with form:
                        with FormSection('Data refresh', description='These values apply to this local specimen only.'):
                            endpoint = TextInput('Provider endpoint', value='fab-metrics', required=True, description='Service alias; credentials remain server-side.')
                            Select('Refresh interval', {'30': '30 seconds', '60': '1 minute', '300': '5 minutes'}, value='60')
                            Switch('Pause refresh when tab is hidden', checked=True)
                        with region('validation'):
                            TextInput('Escalation group', value='', error='Choose an escalation group before enabling paging.')
                            Switch('Enable paging', checked=False, disabled=True, description='Disabled until an escalation group is valid.')
                    form.bind_dirty(endpoint.element)
                with region('dirty_state'):
                    save_state_ref['status'] = ui.label('Saved configuration · no local changes').classes('cui-workbench-note')
            with page.slot(LayoutSlot.ACTIONS):
                with region('save'):
                    Button('Save settings', intent=ButtonIntent.PRIMARY, on_click=lambda: (form.mark_clean(), save_state_ref['status'].set_text('Settings saved locally'), emit('Settings saved')))
                with region('reset'):
                    Button('Reset changes', on_click=lambda: (form.mark_clean(), save_state_ref['status'].set_text('Changes reset to saved values'), emit('Settings reset')))

        elif key == 'wizard':
            steps = (
                StepSpec('scope', 'Scope', 'Choose data and purpose', StepState.COMPLETE),
                StepSpec('mapping', 'Map fields', 'Confirm engineering semantics', StepState.ACTIVE),
                StepSpec('review', 'Review', 'Validate before creation', StepState.UPCOMING),
            )
            with page.slot(LayoutSlot.NAVIGATION):
                with region('progress'):
                    ProgressSteps(steps)
            with page.slot(LayoutSlot.CONTENT):
                with region('validation'):
                    ui.label('Step 2 · Map engineering fields').classes('cui-section-title')
                    Select('Measurement', {'thickness': 'Thickness (nm)', 'pressure': 'Pressure (mTorr)'}, value='thickness', required=True)
                    Select('Entity identifier', {'id': 'Lot ID'}, value='id', required=True)
                    ui.label('Both required mappings are valid.').classes('cui-workbench-note')
                with region('review'):
                    ui.label('Review preview').classes('cui-property__label')
                    PropertyGrid((KeyValueItem('rows', 'Rows', 8), KeyValueItem('measurement', 'Measurement', 'Thickness (nm)'), KeyValueItem('pattern', 'Pattern', 'Analysis workspace')))
            with page.slot(LayoutSlot.ACTIONS):
                with region('back'):
                    Button('Back', on_click=lambda: emit('Wizard moved back'))
                with region('next'):
                    Button('Next: Review', intent=ButtonIntent.PRIMARY, on_click=lambda: emit('Wizard advanced to review'))

        elif key == 'comparison':
            baseline = [99.8, 100.1, 100.4, 99.9]
            current = [101.2, 102.1, 101.7, 102.4]
            with page.slot(LayoutSlot.FILTERS):
                with region('populations'):
                    Select('Baseline', {'golden': 'Golden tool · ETCH-03'}, value='golden')
                    Select('Comparison', {'candidate': 'Candidate tool · ETCH-07'}, value='candidate')
            with page.slot(LayoutSlot.METRICS):
                with region('delta'), MetricStrip():
                    ComparisonMetric('Mean thickness', '101.85 nm', baseline='100.05 nm', delta='+1.80 nm', intent=StatusIntent.WARNING)
                    ComparisonMetric('Within spec', '75%', baseline='100%', delta='−25 pp', intent=StatusIntent.DANGER)
            with page.slot(LayoutSlot.PRIMARY):
                with region('comparison_visual'):
                    BarChart(
                        'Aligned population means',
                        (SeriesSpec('baseline', 'Golden tool', baseline), SeriesSpec('current', 'Candidate tool', current)),
                        size=ChartSize.COMPACT,
                        x_axis=AxisSpec(label='Matched run', kind=AxisType.CATEGORY, categories=('1', '2', '3', '4')),
                        y_axis=AxisSpec(label='Thickness', unit='nm'),
                    )
            with page.slot(LayoutSlot.SECONDARY):
                with ComparePanel():
                    with region('aligned_evidence'):
                        DifferenceTable((
                            ComparisonItem('mean', 'Mean', '100.05 nm', '101.85 nm', '+1.80 nm'),
                            ComparisonItem('range', 'Range', '0.6 nm', '1.2 nm', '+0.6 nm'),
                            ComparisonItem('spec', 'Within spec', '100%', '75%', '−25 pp'),
                        ), left_label='Golden', right_label='Candidate')

        elif key == 'analysis_workspace':
            with page.slot(LayoutSlot.FILTERS):
                with region('analysis_filters'):
                    with ui.row().classes('cui-filter-bar'):
                        Select('Tool', {'ETCH-03': 'ETCH-03', 'ETCH-07': 'ETCH-07'}, value='ETCH-03')
                        Select('Measurement', {'thickness': 'Thickness'}, value='thickness')
                        SearchInput('Find lot', value='LOT-24')
            with page.slot(LayoutSlot.PRIMARY):
                with region('primary_visual'):
                    trend_chart('Thickness investigation', [float(row['thickness']) for row in records])
            with page.slot(LayoutSlot.DATA):
                with region('supporting_table'):
                    render_table('data_table', title='Linked lot records', rows=records, on_event=on_event)
            with page.slot(LayoutSlot.DETAILS):
                with region('selected_inspector'):
                    ui.label('Selected excursion').classes('cui-section-title')
                    PropertyGrid((
                        KeyValueItem('lot', 'Lot', records[3]['id']),
                        KeyValueItem('tool', 'Tool / chamber', f"{records[3]['tool']} / {records[3]['chamber']}"),
                        KeyValueItem('value', 'Thickness', f"{records[3]['thickness']} nm"),
                        KeyValueItem('status', 'Disposition', records[3]['status']),
                    ))
                    Button('Open investigation', intent=ButtonIntent.SECONDARY, on_click=lambda: emit('Opened investigation'))

    return page
