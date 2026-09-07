from __future__ import annotations

import json
from contextvars import ContextVar

_DISABLED = ContextVar("nicegui_base_specimen_disabled", default=False)
from collections.abc import Callable
from typing import Any

from nicegui_base.components import ButtonIntent, DataQuality, SelectOption, StatusIntent
from nicegui_base.integrations.nicegui_components import (
    Accordion, ActionButton, Autocomplete, Button, ButtonGroup, Card, Checkbox, CheckboxGroup,
    Chip, CollapsiblePanel, Combobox, CountBadge, DataQualityBadge, DatePicker, DateRangePicker,
    DateTimePicker, Divider, FileUpload, FreshnessIndicator, IconButton, MultiSelect, NumberInput,
    Panel, RadioGroup, RangeSlider, SearchInput, Select, SeverityIndicator, Slider, SplitButton,
    StatusBadge, Switch, TextArea, TextInput, TimePicker, Well,
)
from nicegui_base.visual import Icons

EventSink = Callable[[str], None]


def _ui():
    from nicegui import ui
    return ui


def _emit(sink: EventSink | None, message: str) -> None:
    if sink is not None:
        sink(message)


def _event(sink: EventSink | None, label: str):
    def callback(event: Any = None) -> None:
        value = getattr(event, 'value', None)
        suffix = f' → {value}' if value is not None else ''
        _emit(sink, f'{label}{suffix}')
    return callback


def _choices() -> dict[str, str]:
    return {'etch': 'Etch', 'deposition': 'Deposition', 'metrology': 'Metrology'}


def _choice_specs() -> tuple[SelectOption, ...]:
    return (
        SelectOption('etch', 'Etch'),
        SelectOption('deposition', 'Deposition'),
        SelectOption('metrology', 'Metrology'),
    )


def _button_group(sink):
    with ButtonGroup():
        Button('Run', intent=ButtonIntent.PRIMARY, on_click=_event(sink, 'Run'))
        Button('Pause', on_click=_event(sink, 'Pause'))
        Button('Reset', intent=ButtonIntent.TERTIARY, on_click=_event(sink, 'Reset'))


def _split_button(sink):
    SplitButton('Export CSV', {'Export JSON': _event(sink, 'Export JSON'), 'Export PNG': _event(sink, 'Export PNG')}, icon=Icons.EXPORT, on_click=_event(sink, 'Export CSV'))


def _divider(_sink):
    ui = _ui(); ui.label('Measurement summary').classes('cui-workbench-note'); Divider(); ui.label('Run details').classes('cui-workbench-note')


def _collapsible_panel(_sink):
    ui = _ui()
    with CollapsiblePanel('Advanced settings', open=True):
        ui.label('Secondary configuration stays in context.').classes('cui-workbench-note')


def _accordion(_sink):
    ui = _ui()
    with Accordion() as accordion:
        with accordion.item('Sampling', open=True): ui.label('Every 10 wafers').classes('cui-workbench-note')
        with accordion.item('Notification'): ui.label('Alert on excursion').classes('cui-workbench-note')


def _chip(sink): Chip('Lot A12', selected=True, icon=Icons.LOT, on_click=_event(sink, 'Lot A12'))
def _count_badge(_sink): CountBadge(24)
def _severity_indicator(_sink): SeverityIndicator('High severity', intent=StatusIntent.DANGER)
def _freshness_indicator(_sink): FreshnessIndicator('Updated 2 min ago', stale=False)
def _data_quality_badge(_sink): DataQualityBadge(DataQuality.COMPLETE)
def _button(sink): Button('Run analysis', intent=ButtonIntent.PRIMARY, icon=Icons.PLAY, disabled=_DISABLED.get(), on_click=_event(sink, 'Run analysis'))
def _action_button(sink): ActionButton('Save changes', icon=Icons.SAVE, success_message='Saved', disabled=_DISABLED.get(), on_click=_event(sink, 'Save changes'))
def _icon_button(sink): IconButton(Icons.REFRESH, label='Refresh data', on_click=_event(sink, 'Refresh data'))


def _surface(_sink):
    ui = _ui()
    with ui.element('div').classes('cui-component-specimen__surface-grid'):
        with Panel(): ui.label('Panel').classes('cui-workbench-section-title'); ui.label('Primary grouped content').classes('cui-workbench-note')
        with Card(): ui.label('Card').classes('cui-workbench-section-title'); ui.label('Compact related content').classes('cui-workbench-note')
        with Well(): ui.label('Well').classes('cui-workbench-section-title'); ui.label('Inset supporting content').classes('cui-workbench-note')


def _badge(_sink):
    ui = _ui()
    with ui.element('div').classes('cui-component-specimen__row'):
        StatusBadge('Healthy', intent=StatusIntent.SUCCESS, icon=Icons.CHECK)
        StatusBadge('Warning', intent=StatusIntent.WARNING, icon=Icons.WARNING)
        StatusBadge('Excursion', intent=StatusIntent.DANGER, icon=Icons.ERROR)


def _text_input(sink): TextInput('Lot ID', value='LOT-2409', description='Canonical single-line field', clearable=True, disabled=_DISABLED.get(), on_change=_event(sink, 'Lot ID'))
def _number_input(sink): NumberInput('Upper limit', value=42.5, minimum=0, maximum=100, step=0.1, unit='nm', disabled=_DISABLED.get(), on_change=_event(sink, 'Upper limit'))
def _textarea(sink): TextArea('Engineering note', value='Investigate chamber drift.', rows=3, disabled=_DISABLED.get(), on_change=_event(sink, 'Engineering note'))
def _search_input(sink): SearchInput('Search lots', value='LOT', debounce_ms=250, disabled=_DISABLED.get(), on_change=_event(sink, 'Search lots'))
def _select(sink): Select('Process area', _choices(), value='metrology', searchable=True, disabled=_DISABLED.get(), on_change=_event(sink, 'Process area'))
def _multi_select(sink): MultiSelect('Process areas', _choices(), value=('etch', 'metrology'), on_change=_event(sink, 'Process areas'))
def _autocomplete(sink): Autocomplete('Tool', _choices(), value='metrology', on_change=_event(sink, 'Tool'))
def _combobox(sink): Combobox('Tag', _choices(), value='etch', on_change=_event(sink, 'Tag'))
def _checkbox(sink): Checkbox('Include rework lots', checked=True, description='Independent boolean choice', disabled=_DISABLED.get(), on_change=_event(sink, 'Include rework lots'))
def _checkbox_group(sink): CheckboxGroup('Signals', _choice_specs(), selected=('etch', 'metrology'), on_change=_event(sink, 'Signals'))
def _radio_group(sink): RadioGroup('Mode', _choice_specs(), selected='metrology', on_change=_event(sink, 'Mode'))
def _switch(sink): Switch('Auto refresh', checked=True, description='Applies immediately', disabled=_DISABLED.get(), on_change=_event(sink, 'Auto refresh'))
def _slider(sink): Slider('Threshold', value=65, minimum=0, maximum=100, step=5, unit='%', disabled=_DISABLED.get(), on_change=_event(sink, 'Threshold'))
def _range_slider(sink): RangeSlider('Window', low=20, high=80, minimum=0, maximum=100, step=5, unit='%', on_change=_event(sink, 'Window'))
def _date_picker(_sink): DatePicker('Effective date', value='2026-09-05')
def _date_range_picker(_sink): DateRangePicker('Analysis period', start='2026-09-01', end='2026-09-05')
def _time_picker(_sink): TimePicker('Cutoff time', value='14:30')
def _datetime_picker(_sink): DateTimePicker('Scheduled run', value='2026-09-05T14:30')
def _file_upload(sink): FileUpload(label='Upload process data', accept=('.csv', '.json'), max_file_size_mb=10, on_upload=_event(sink, 'File uploaded'))

_RENDERERS = {
    'button_group': _button_group, 'split_button': _split_button, 'divider': _divider,
    'collapsible_panel': _collapsible_panel, 'accordion': _accordion, 'chip': _chip,
    'count_badge': _count_badge, 'severity_indicator': _severity_indicator,
    'freshness_indicator': _freshness_indicator, 'data_quality_badge': _data_quality_badge,
    'button': _button, 'action_button': _action_button, 'icon_button': _icon_button,
    'surface': _surface, 'badge': _badge, 'text_input': _text_input, 'number_input': _number_input,
    'textarea': _textarea, 'search_input': _search_input, 'select': _select, 'multi_select': _multi_select,
    'autocomplete': _autocomplete, 'combobox': _combobox, 'checkbox': _checkbox,
    'checkbox_group': _checkbox_group, 'radio_group': _radio_group, 'switch': _switch,
    'slider': _slider, 'range_slider': _range_slider, 'date_picker': _date_picker,
    'date_range_picker': _date_range_picker, 'time_picker': _time_picker,
    'datetime_picker': _datetime_picker, 'file_upload': _file_upload,
}
COMPONENT_SPECIMEN_KEYS = frozenset(_RENDERERS)


def render_component_specimen(component_key: str, *, on_event: EventSink | None = None, disabled: bool = False) -> None:
    try:
        renderer = _RENDERERS[component_key]
    except KeyError as exc:
        raise KeyError(f'No Capability Studio specimen registered for component {component_key!r}') from exc
    ui = _ui()
    with ui.element('section').classes('cui-component-specimen').props(
        f'data-component-specimen={json.dumps(component_key)} aria-label={json.dumps(component_key + " interactive specimen")}'
    ):
        with ui.element('div').classes('cui-component-specimen__intro'):
            ui.label('Interactive specimen').classes('cui-workbench-chip')
            ui.label('Use the real control below; interactions are recorded in Event / debug output.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-component-specimen__stage'):
            with ui.element('div').classes('cui-component-specimen__demo').props(f'data-component-demo={json.dumps(component_key)}'):
                token = _DISABLED.set(disabled)
                try:
                    renderer(on_event)
                finally:
                    _DISABLED.reset(token)

__all__ = ['COMPONENT_SPECIMEN_KEYS', 'render_component_specimen']
