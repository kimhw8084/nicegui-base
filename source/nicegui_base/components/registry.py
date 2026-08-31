from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ComponentDefinition:
    key: str
    category: str
    public_name: str
    purpose: str
    preferred_for: tuple[str, ...]


_COMPONENTS = {
    'button_group': ComponentDefinition('button_group', 'actions', 'ButtonGroup', 'Group related actions without visual fragmentation', ('toolbar actions', 'mode actions')),
    'split_button': ComponentDefinition('split_button', 'actions', 'SplitButton', 'Primary action with closely related alternatives', ('export alternatives', 'run options')),
    'divider': ComponentDefinition('divider', 'surfaces', 'Divider', 'Subtle structural separation', ('sections', 'menus')),
    'collapsible_panel': ComponentDefinition('collapsible_panel', 'surfaces', 'CollapsiblePanel', 'Progressive disclosure without leaving context', ('advanced settings', 'secondary detail')),
    'accordion': ComponentDefinition('accordion', 'surfaces', 'Accordion', 'Grouped progressive disclosure', ('help', 'configuration groups')),
    'chip': ComponentDefinition('chip', 'status', 'Chip', 'Interactive compact metadata or filter value', ('filter value', 'selection')),
    'count_badge': ComponentDefinition('count_badge', 'status', 'CountBadge', 'Compact numeric count', ('notifications', 'selected count')),
    'severity_indicator': ComponentDefinition('severity_indicator', 'status', 'SeverityIndicator', 'Semantic severity with label and non-color cue', ('operational state', 'risk')),
    'freshness_indicator': ComponentDefinition('freshness_indicator', 'status', 'FreshnessIndicator', 'Data recency state', ('updated time', 'stale data')),
    'data_quality_badge': ComponentDefinition('data_quality_badge', 'status', 'DataQualityBadge', 'Data reliability/completeness state', ('partial data', 'estimated data')),
    'button': ComponentDefinition('button', 'actions', 'ButtonSpec', 'Standard user action', ('normal action', 'secondary action', 'danger action')),
    'action_button': ComponentDefinition('action_button', 'actions', 'ActionButtonSpec', 'Async-safe or stateful action', ('save', 'run analysis', 'submit')),
    'icon_button': ComponentDefinition('icon_button', 'actions', 'IconButtonSpec', 'Compact icon-only action with accessible label', ('toolbar action', 'row action')),
    'surface': ComponentDefinition('surface', 'surfaces', 'SurfaceSpec', 'Consistent content containment and interaction surface', ('panel', 'card', 'well')),
    'badge': ComponentDefinition('badge', 'status', 'BadgeSpec', 'Compact semantic status or metadata label', ('status', 'severity', 'metadata')),
    'text_input': ComponentDefinition('text_input', 'inputs', 'TextInputSpec', 'Single-line text entry', ('name', 'identifier', 'free text')),
    'number_input': ComponentDefinition('number_input', 'inputs', 'NumberInputSpec', 'Numeric entry with bounds and unit', ('threshold', 'count', 'measurement')),
    'textarea': ComponentDefinition('textarea', 'inputs', 'TextAreaSpec', 'Multi-line text entry', ('notes', 'description', 'comment')),
    'search_input': ComponentDefinition('search_input', 'inputs', 'SearchInputSpec', 'Debounced search entry', ('global search', 'table search', 'entity search')),
    'select': ComponentDefinition('select', 'inputs', 'SelectSpec', 'Single choice from known values', ('filter', 'form choice')),
    'multi_select': ComponentDefinition('multi_select', 'inputs', 'MultiSelectSpec', 'Multiple choices from known values', ('multi-filter', 'assignment')),
    'autocomplete': ComponentDefinition('autocomplete', 'inputs', 'AutocompleteSpec', 'Searchable known values', ('large option set', 'entity lookup')),
    'combobox': ComponentDefinition('combobox', 'inputs', 'ComboboxSpec', 'Search/select with optional custom value', ('tag-like entry', 'mixed known/custom choice')),
    'checkbox': ComponentDefinition('checkbox', 'inputs', 'CheckboxSpec', 'Independent boolean selection', ('multi-option form', 'enable choice')),
    'checkbox_group': ComponentDefinition('checkbox_group', 'inputs', 'CheckboxGroupSpec', 'Set of independent boolean choices', ('feature selection', 'permissions')),
    'radio_group': ComponentDefinition('radio_group', 'inputs', 'RadioGroupSpec', 'Mutually exclusive choice', ('mode selection', 'single preference')),
    'switch': ComponentDefinition('switch', 'inputs', 'SwitchSpec', 'Immediate on/off setting', ('preference toggle', 'feature enablement')),
    'slider': ComponentDefinition('slider', 'inputs', 'SliderSpec', 'Bounded continuous or stepped value', ('threshold', 'range tuning')),
    'range_slider': ComponentDefinition('range_slider', 'inputs', 'RangeSliderSpec', 'Bounded low/high selection', ('numeric filtering', 'window selection')),
    'date_picker': ComponentDefinition('date_picker', 'inputs', 'DatePickerSpec', 'Single date selection', ('effective date', 'event date')),
    'date_range_picker': ComponentDefinition('date_range_picker', 'inputs', 'DateRangePickerSpec', 'Date interval selection', ('analysis period', 'reporting window')),
    'time_picker': ComponentDefinition('time_picker', 'inputs', 'TimePickerSpec', 'Time-of-day selection', ('schedule time', 'cutoff')),
    'datetime_picker': ComponentDefinition('datetime_picker', 'inputs', 'DateTimePickerSpec', 'Date and time selection', ('timestamp', 'scheduled action')),
    'file_upload': ComponentDefinition('file_upload', 'inputs', 'FileUploadSpec', 'Validated file selection and upload', ('attachment', 'data import')),
}

COMPONENT_REGISTRY: Mapping[str, ComponentDefinition] = MappingProxyType(_COMPONENTS)


def get_component(key: str) -> ComponentDefinition:
    try:
        return COMPONENT_REGISTRY[key]
    except KeyError as exc:
        raise KeyError(f'Unknown component: {key}') from exc
