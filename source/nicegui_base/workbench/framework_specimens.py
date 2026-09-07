from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from nicegui_base.content import (
    ActivityItem,
    ComparisonItem,
    KeyValueItem,
    SearchResultSpec,
    StepSpec,
    StepState,
    TreeNode,
    TrendDirection,
)
from nicegui_base.feedback import FeedbackIntent, ToastSpec
from nicegui_base.integrations.nicegui_components import Button
from nicegui_base.integrations.nicegui_content import (
    ActivityFeed,
    BackgroundTaskIndicator,
    CodeViewer,
    CommandPalette,
    ComparePanel,
    ComparisonMetric,
    DifferenceTable,
    EntityHeader,
    ImageViewer,
    JsonViewer,
    KeyValueList,
    LogViewer,
    MarkdownViewer,
    MetricCard,
    MetricStrip,
    NotificationCenter,
    ProgressSteps,
    PropertyGrid,
    SearchResults,
    Stepper,
    TreeView,
)
from nicegui_base.services import Command, CommandRegistry
from nicegui_base.components import StatusIntent
from nicegui_base.visual import Icons

EventSink = Callable[[str], None]


def _ui():
    from nicegui import ui
    return ui


def _event(sink: EventSink | None, message: str):
    def callback(*_args, **_kwargs) -> None:
        if sink is not None:
            sink(message)
    return callback


def _properties() -> tuple[KeyValueItem, ...]:
    return (
        KeyValueItem('lot', 'Lot', 'L260142', copyable=True),
        KeyValueItem('wafer', 'Wafer', 'W12'),
        KeyValueItem('tool', 'Tool', 'ETCH-021'),
        KeyValueItem('recipe', 'Recipe', 'ETCH_R18'),
        KeyValueItem('value', 'Mean CD', '42.18 nm'),
        KeyValueItem('status', 'Status', 'Watch'),
    )


def _steps() -> tuple[StepSpec, ...]:
    return (
        StepSpec('scope', 'Scope population', state=StepState.COMPLETE),
        StepSpec('compare', 'Compare controls', state=StepState.COMPLETE),
        StepSpec('evidence', 'Review evidence', state=StepState.ACTIVE),
        StepSpec('close', 'Close investigation'),
    )


def _image_data() -> str:
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="300" viewBox="0 0 720 300">
    <rect width="720" height="300" rx="18" fill="#F4F6F9"/>
    <circle cx="180" cy="150" r="98" fill="#D9E5F3" stroke="#718096" stroke-width="2"/>
    <circle cx="215" cy="178" r="18" fill="#D85C55"/><circle cx="235" cy="195" r="12" fill="#F1B55D"/>
    <circle cx="195" cy="205" r="9" fill="#D85C55"/><circle cx="150" cy="112" r="8" fill="#4C89D9"/>
    <text x="330" y="105" font-family="Arial,sans-serif" font-size="24" font-weight="700" fill="#17202C">Wafer 12 · CD residual</text>
    <text x="330" y="143" font-family="Arial,sans-serif" font-size="16" fill="#5E6978">ETCH-021 / CH-3 · ETCH_R18</text>
    <text x="330" y="190" font-family="Arial,sans-serif" font-size="14" font-weight="700" fill="#6B7685">OBSERVED SIGNATURE</text>
    <text x="330" y="220" font-family="Arial,sans-serif" font-size="17" fill="#17202C">Lower-right excursion cluster</text>
    </svg>'''
    return 'data:image/svg+xml;charset=utf-8,' + quote(svg)


def _metric_card(sink: EventSink | None) -> None:
    MetricCard('Mean CD', '42.18 nm', delta='+2.12 nm vs baseline', trend=TrendDirection.UP,
               intent=StatusIntent.DANGER, icon=Icons.CHART_LINE, on_click=_event(sink, 'Metric selected'))


def _metric_strip(_sink: EventSink | None) -> None:
    with MetricStrip():
        MetricCard('Affected', '84 wafers', intent=StatusIntent.DANGER)
        MetricCard('Controls', '215 wafers', intent=StatusIntent.SUCCESS)
        MetricCard('Confidence', 'High', intent=StatusIntent.SUCCESS)
        MetricCard('Contradictions', 1, intent=StatusIntent.WARNING)


def _comparison_metric(_sink: EventSink | None) -> None:
    ComparisonMetric('Mean CD', '42.18 nm', baseline='40.06 nm', delta='+2.12 nm', intent=StatusIntent.DANGER)


def _key_value_list(sink: EventSink | None) -> None:
    KeyValueList(_properties()[:4], on_copy=lambda item: _event(sink, f'Copied {item.label}')())


def _property_grid(_sink: EventSink | None) -> None:
    PropertyGrid(_properties())


def _entity_header(_sink: EventSink | None) -> None:
    EntityHeader('ETCH-021 / CH-3', subtitle='Critical etch chamber investigation', entity_type='Chamber',
                 status='Watch', status_intent=StatusIntent.WARNING, icon=Icons.CHAMBER,
                 metadata=(KeyValueItem('area', 'Area', 'ETCH'), KeyValueItem('recipe', 'Recipe', 'ETCH_R18')))


def _tree_view(sink: EventSink | None) -> None:
    TreeView((TreeNode('fab', 'Fab 1', (
        TreeNode('etch', 'ETCH', (TreeNode('tool14', 'ETCH-014'), TreeNode('tool21', 'ETCH-021'))),
        TreeNode('cvd', 'CVD'),
    )),), selected='tool21', on_select=_event(sink, 'Tree selection changed'))


def _markdown_viewer(_sink: EventSink | None) -> None:
    MarkdownViewer('### Investigation note\n- Strong edge signature\n- **CH-3** commonality\n- Contradiction retained')


def _code_viewer(_sink: EventSink | None) -> None:
    CodeViewer("query = {'tool': 'ETCH-021', 'status': 'watch'}", language='python')


def _json_viewer(_sink: EventSink | None) -> None:
    JsonViewer({'tool': 'ETCH-021', 'chamber': 'CH-3', 'recipe': 'ETCH_R18', 'values': [40.1, 41.2, 42.0]})


def _log_viewer(_sink: EventSink | None) -> None:
    LogViewer(('09:31:04 query started', '09:31:04 320 records scanned', '09:31:05 completed in 184 ms'))


def _image_viewer(_sink: EventSink | None) -> None:
    ImageViewer(_image_data(), alt='Synthetic wafer residual evidence', caption='Wafer 12 · CD residual evidence')


def _search_results(sink: EventSink | None) -> None:
    SearchResults((
        SearchResultSpec('r1', 'ETCH-021 / CH-3', 'Chamber · Watch', 'Strong affected/control enrichment', Icons.CHAMBER),
        SearchResultSpec('r2', 'Recipe ETCH_R18', 'Recipe', 'Applied to 84 affected wafers', Icons.RECIPE),
    ), on_select=lambda item: _event(sink, f'Selected {item.title}')())


def _stepper(_sink: EventSink | None) -> None:
    ui = _ui()
    with Stepper(_steps(), value='evidence') as stepper:
        with stepper.step('scope'):
            ui.label('Scope affected population and choose matched controls.')
        with stepper.step('compare'):
            ui.label('Compare route, tool, chamber, recipe and material commonalities.')
        with stepper.step('evidence'):
            ui.label('Assess supporting and contradicting evidence.')
        with stepper.step('close'):
            ui.label('Document the final disposition and evidence basis.')


def _progress_steps(_sink: EventSink | None) -> None:
    ProgressSteps(_steps())


def _compare_panel(_sink: EventSink | None) -> None:
    ui = _ui()
    with ComparePanel() as panel:
        with panel.side('Affected'):
            ui.label('42.18 nm · ETCH-021 / CH-3')
        with panel.side('Control'):
            ui.label('40.06 nm · ETCH-014 / CH-2')


def _difference_table(_sink: EventSink | None) -> None:
    DifferenceTable((
        ComparisonItem('tool', 'Tool', 'ETCH-021', 'ETCH-014', changed=True),
        ComparisonItem('recipe', 'Recipe', 'ETCH_R18', 'ETCH_R18', changed=False),
        ComparisonItem('chamber', 'Chamber', 'CH-3', 'CH-2', changed=True),
        ComparisonItem('cd', 'Mean CD', '42.18', '39.96', delta='+2.22', changed=True),
    ), left_label='Affected', right_label='Control')


def _command_palette(sink: EventSink | None) -> None:
    registry = CommandRegistry()
    registry.register(Command('search', 'Search measurements', _event(sink, 'Search command executed'),
                              shortcut='⌘K', keywords=('find', 'table')))
    registry.register(Command('rca', 'Open RCA workspace', _event(sink, 'RCA command executed'), shortcut='⌘R'))
    palette = CommandPalette(registry)
    Button('Open command palette', icon=Icons.SEARCH, on_click=palette.open)


def _background_task(_sink: EventSink | None) -> None:
    BackgroundTaskIndicator('Re-indexing measurement population', progress=.63, detail='63,004 / 100,000 rows')


def _notification_center(_sink: EventSink | None) -> None:
    NotificationCenter((
        ToastSpec('CD warning threshold exceeded', FeedbackIntent.WARNING, 4000),
        ToastSpec('Control population refreshed', FeedbackIntent.SUCCESS, 3000),
    ))


def _activity_feed(_sink: EventSink | None) -> None:
    ActivityFeed((
        ActivityItem('a1', 'Investigation opened', '09:28', 'Affected population scoped', Icons.RCA, StatusIntent.INFO, 'Process Engineer'),
        ActivityItem('a2', 'Control population updated', '09:31', '215 matched wafers', Icons.CONTROL_POPULATION, StatusIntent.SUCCESS, 'System'),
    ))


_CONTENT_RENDERERS = {
    'metric_card': _metric_card,
    'metric_strip': _metric_strip,
    'comparison_metric': _comparison_metric,
    'key_value_list': _key_value_list,
    'property_grid': _property_grid,
    'entity_header': _entity_header,
    'tree_view': _tree_view,
    'markdown_viewer': _markdown_viewer,
    'code_viewer': _code_viewer,
    'json_viewer': _json_viewer,
    'log_viewer': _log_viewer,
    'image_viewer': _image_viewer,
    'search_results': _search_results,
    'stepper': _stepper,
    'progress_steps': _progress_steps,
    'compare_panel': _compare_panel,
    'difference_table': _difference_table,
    'command_palette': _command_palette,
    'background_task': _background_task,
    'notification_center': _notification_center,
    'activity_feed': _activity_feed,
}

FRAMEWORK_CONTENT_SPECIMEN_KEYS = frozenset(_CONTENT_RENDERERS)


def render_framework_specimen(registry_name: str, registry_key: str, *, on_event: EventSink | None = None) -> None:
    if registry_name != 'content':
        raise KeyError(f'No direct framework specimen renderer for registry {registry_name!r}')
    try:
        renderer = _CONTENT_RENDERERS[registry_key]
    except KeyError as exc:
        raise KeyError(f'No content specimen registered for {registry_key!r}') from exc
    ui = _ui()
    with ui.element('section').classes('cui-framework-specimen').props(
        f'data-framework-specimen="{registry_key}" aria-label="{registry_key} interactive specimen"'
    ):
        with ui.element('div').classes('cui-framework-specimen__intro'):
            ui.label('Interactive specimen').classes('cui-workbench-chip')
            ui.label('This is the real NiceGUI Base content control, rendered directly in Studio.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-framework-specimen__stage'):
            with ui.element('div').classes('cui-framework-specimen__demo').props(f'data-framework-demo="{registry_key}"'):
                renderer(on_event)


__all__ = ['FRAMEWORK_CONTENT_SPECIMEN_KEYS', 'render_framework_specimen']
