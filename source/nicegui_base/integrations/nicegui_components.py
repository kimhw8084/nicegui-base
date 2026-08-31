from __future__ import annotations

import inspect
from contextlib import AbstractContextManager
from itertools import count
from typing import Any, Callable, Iterable, Sequence

from nicegui_base.security import UploadPolicy

from nicegui_base.visual import render_icon_svg

from nicegui_base.components import (
    ActionButtonSpec, AutocompleteSpec, BadgeSpec, ButtonIntent, ButtonSpec, CheckboxGroupSpec,
    CheckboxSpec, ComboboxSpec, ComponentSize, DatePickerSpec, DateRangePickerSpec, DateTimePickerSpec,
    FileUploadSpec, IconButtonSpec, MultiSelectSpec, NumberInputSpec, RadioGroupSpec, RangeSliderSpec,
    SearchInputSpec, SelectOption, SelectSpec, SliderSpec, StatusIntent, SurfaceSpec, SurfaceVariant,
    SwitchSpec, TextAreaSpec, TextInputSpec, TimePickerSpec,
)


_FIELD_IDS = count(1)


def _ui():
    try:
        from nicegui import ui
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('NiceGUI is required to render nicegui_base components.') from exc
    return ui


def _props_for_disabled(disabled: bool, readonly: bool = False) -> str:
    parts: list[str] = []
    if disabled:
        parts.append('disable')
    if readonly:
        parts.append('readonly')
    return ' '.join(parts)


class Button:
    def __init__(self, label: str, *, intent: ButtonIntent = ButtonIntent.SECONDARY,
                 size: ComponentSize = ComponentSize.MEDIUM, icon: str | None = None,
                 disabled: bool = False, full_width: bool = False,
                 on_click: Callable[..., Any] | None = None) -> None:
        self.spec = ButtonSpec(label, intent=intent, size=size, icon=icon, disabled=disabled, full_width=full_width)
        ui = _ui()
        if icon:
            self.element = ui.button(on_click=on_click).props('no-caps unelevated').classes(self.spec.classes)
            with self.element:
                ui.html(render_icon_svg(icon, size='sm'), sanitize=False).classes('cui-svg-icon-host')
                ui.label(label)
        else:
            self.element = ui.button(label, on_click=on_click).props('no-caps unelevated').classes(self.spec.classes)
        if disabled:
            self.element.disable()


class ActionButton(Button):
    def __init__(self, label: str, *, intent: ButtonIntent = ButtonIntent.PRIMARY,
                 size: ComponentSize = ComponentSize.MEDIUM, icon: str | None = None,
                 disabled: bool = False, loading: bool = False, full_width: bool = False,
                 success_message: str | None = None, error_message: str | None = None,
                 on_click: Callable[..., Any] | None = None) -> None:
        self.action_spec = ActionButtonSpec(label, intent=intent, size=size, icon=icon, disabled=disabled,
                                             loading=loading, full_width=full_width,
                                             success_message=success_message, error_message=error_message)
        self.spec = self.action_spec
        ui = _ui()
        self.element = ui.button(on_click=on_click).props('no-caps unelevated').classes(self.spec.classes)
        with self.element:
            if loading:
                ui.element('span').classes('cui-button__spinner').props('aria-hidden="true"')
            elif icon:
                ui.html(render_icon_svg(icon, size='sm'), sanitize=False).classes('cui-svg-icon-host')
            ui.label(label).classes('cui-button__label')
        if disabled or loading:
            self.element.disable()


class IconButton:
    def __init__(self, icon: str, *, label: str, intent: ButtonIntent = ButtonIntent.GHOST,
                 size: ComponentSize = ComponentSize.MEDIUM, disabled: bool = False,
                 selected: bool = False, on_click: Callable[..., Any] | None = None) -> None:
        self.spec = IconButtonSpec(icon, label, intent=intent, size=size, disabled=disabled, selected=selected)
        ui = _ui()
        self.element = ui.button(on_click=on_click).props(f'flat round aria-label="{label}"').classes(self.spec.classes)
        with self.element:
            ui.html(render_icon_svg(icon, size='sm', label=label), sanitize=False).classes('cui-svg-icon-host')
        from nicegui_base.integrations.nicegui_interactions import Tooltip
        self.tooltip = Tooltip(label); self.tooltip.attach(self.element)
        if disabled:
            self.element.disable()


class _SurfaceContext(AbstractContextManager):
    def __init__(self, spec: SurfaceSpec):
        self.spec = spec
        self.element = _ui().element('section').classes(spec.classes)

    def __enter__(self):
        self.element.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self.element.__exit__(exc_type, exc, tb)


class Panel(_SurfaceContext):
    def __init__(self, *, interactive: bool = False, selected: bool = False):
        super().__init__(SurfaceSpec(SurfaceVariant.PANEL, interactive=interactive, selected=selected))


class Card(_SurfaceContext):
    def __init__(self, *, interactive: bool = False, selected: bool = False):
        super().__init__(SurfaceSpec(SurfaceVariant.CARD, interactive=interactive, selected=selected))


class Well(_SurfaceContext):
    def __init__(self):
        super().__init__(SurfaceSpec(SurfaceVariant.WELL))


class InteractiveCard(_SurfaceContext):
    def __init__(self, *, selected: bool = False, on_click: Callable[..., Any] | None = None):
        self.selected = selected
        super().__init__(SurfaceSpec(SurfaceVariant.INTERACTIVE, interactive=True, selected=selected))
        self.element.props(f'role="button" tabindex="0" aria-pressed="{str(selected).lower()}"')
        async def activate(e=None):
            self.selected = not self.selected
            if self.selected:
                self.element.classes(add='is-selected')
            else:
                self.element.classes(remove='is-selected')
            self.element.props(f'aria-pressed="{str(self.selected).lower()}"')
            if on_click is not None:
                result = on_click(e)
                if hasattr(result, '__await__'):
                    await result
        self.element.on('click', activate)
        self.element.on('keydown.enter', activate)
        self.element.on('keydown.space', activate)


class StatusBadge:
    def __init__(self, label: str, *, intent: StatusIntent = StatusIntent.NEUTRAL, icon: str | None = None):
        self.spec = BadgeSpec(label=label, intent=intent, icon=icon)
        ui = _ui()
        with ui.element('span').classes(self.spec.classes) as self.element:
            if icon:
                ui.html(render_icon_svg(icon, size='xs'), sanitize=False).classes('cui-svg-icon-host')
            ui.label(label)


class Tag:
    """Compact metadata tag distinct from status/health badges."""
    def __init__(self, label: str, *, intent: StatusIntent = StatusIntent.NEUTRAL, icon: str | None = None):
        if not label.strip():
            raise ValueError('Tag label cannot be empty')
        self.label = label; self.intent = intent; self.icon = icon
        ui = _ui()
        with ui.element('span').classes(f'cui-tag cui-tag--{intent.value}') as self.element:
            if icon:
                ui.html(render_icon_svg(icon, size='xs'), sanitize=False).classes('cui-svg-icon-host')
            ui.label(label)


class _FieldRenderer:
    spec: Any

    def _begin_field(self):
        ui = _ui()
        n = next(_FIELD_IDS)
        self.field_id = f'cui-field-{n}'
        self.label_id = f'{self.field_id}-label'
        self.description_id = f'{self.field_id}-description'
        self.error_id = f'{self.field_id}-error'
        container = ui.column().classes('cui-field').props(f'role="group" aria-labelledby="{self.label_id}"')
        container.__enter__()
        with ui.element('div').classes('cui-field-label-row'):
            with ui.element('div'):
                ui.label(self.spec.label).classes('cui-field-label').props(f'id="{self.label_id}"')
                if getattr(self.spec, 'required', False):
                    ui.label('*').classes('cui-field-required').props('aria-hidden="true"')
        return container

    def _accessibility_props(self, *, suffix: str | None = None) -> str:
        label = self.spec.label if suffix is None else f'{self.spec.label} {suffix}'
        desc_ids: list[str] = []
        if getattr(self.spec, 'description', None):
            desc_ids.append(self.description_id)
        if getattr(self.spec, 'error', None):
            desc_ids.append(self.error_id)
        props = [f'aria-label="{label}"']
        if desc_ids:
            props.append(f'aria-describedby="{" ".join(desc_ids)}"')
        if getattr(self.spec, 'required', False):
            props.append('aria-required="true"')
        if getattr(self.spec, 'error', None):
            props.append('aria-invalid="true"')
        return ' '.join(props)

    def _end_field(self, container):
        ui = _ui()
        if getattr(self.spec, 'description', None):
            ui.label(self.spec.description).classes('cui-field-description').props(f'id="{self.description_id}"')
        if getattr(self.spec, 'error', None):
            ui.label(self.spec.error).classes('cui-field-error').props(f'id="{self.error_id}" role="alert"')
        container.__exit__(None, None, None)


class TextInput(_FieldRenderer):
    def __init__(self, label: str, *, value: str | None = None, placeholder: str | None = None,
                 description: str | None = None, error: str | None = None, required: bool = False,
                 disabled: bool = False, readonly: bool = False, clearable: bool = False,
                 password: bool = False, leading_icon: str | None = None,
                 on_change: Callable[..., Any] | None = None):
        self.spec = TextInputSpec(label=label, value=value, placeholder=placeholder, description=description,
                                  error=error, required=required, disabled=disabled, readonly=readonly,
                                  clearable=clearable, password=password, leading_icon=leading_icon)
        ui = _ui(); c = self._begin_field()
        props = ['outlined', 'dense', 'hide-bottom-space']
        if clearable: props.append('clearable')
        if password: props.append('type=password')
        extra = _props_for_disabled(disabled, readonly)
        if extra: props.append(extra)
        props.append(self._accessibility_props())
        self.element = ui.input(value=value, placeholder=placeholder, on_change=on_change).props(' '.join(props)).classes(self.spec.classes)
        self._end_field(c)


class PasswordInput(TextInput):
    def __init__(self, label: str = 'Password', **kwargs):
        super().__init__(label, password=True, **kwargs)


class NumberInput(_FieldRenderer):
    def __init__(self, label: str, *, value: float | None = None, minimum: float | None = None,
                 maximum: float | None = None, step: float | None = None, unit: str | None = None,
                 description: str | None = None, error: str | None = None, required: bool = False,
                 disabled: bool = False, readonly: bool = False, on_change: Callable[..., Any] | None = None):
        self.spec = NumberInputSpec(label=label, value=value, minimum=minimum, maximum=maximum, step=step, unit=unit,
                                    description=description, error=error, required=required, disabled=disabled, readonly=readonly)
        ui = _ui(); c = self._begin_field()
        props = ['outlined', 'dense', 'hide-bottom-space', 'type=number']
        if minimum is not None: props.append(f'min={minimum}')
        if maximum is not None: props.append(f'max={maximum}')
        if step is not None: props.append(f'step={step}')
        extra = _props_for_disabled(disabled, readonly)
        if extra: props.append(extra)
        props.append(self._accessibility_props())
        self.element = ui.number(value=value, min=minimum, max=maximum, step=step, on_change=on_change).props(' '.join(props)).classes(self.spec.classes)
        if unit: self.element.props(f'suffix="{unit}"')
        self._end_field(c)


class TextArea(_FieldRenderer):
    def __init__(self, label: str, *, value: str | None = None, placeholder: str | None = None,
                 rows: int = 4, description: str | None = None, error: str | None = None,
                 required: bool = False, disabled: bool = False, readonly: bool = False,
                 on_change: Callable[..., Any] | None = None):
        self.spec = TextAreaSpec(label=label, value=value, placeholder=placeholder, rows=rows, description=description,
                                 error=error, required=required, disabled=disabled, readonly=readonly)
        ui = _ui(); c = self._begin_field(); props = ['outlined', 'dense', 'hide-bottom-space', 'type=textarea', f'rows={rows}']
        extra = _props_for_disabled(disabled, readonly)
        if extra: props.append(extra)
        props.append(self._accessibility_props())
        self.element = ui.textarea(value=value, placeholder=placeholder, on_change=on_change).props(' '.join(props)).classes(self.spec.classes)
        self._end_field(c)


class SearchInput(TextInput):
    def __init__(self, label: str = 'Search', *, debounce_ms: int = 250, shortcut: str | None = '/', **kwargs):
        self.search_spec = SearchInputSpec(label=label, debounce_ms=debounce_ms, shortcut=shortcut,
                                           value=kwargs.get('value'), placeholder=kwargs.get('placeholder'))
        super().__init__(label, leading_icon='search', clearable=True, **kwargs)
        self.spec = self.search_spec
        self.element.props(f'debounce={debounce_ms}')


def _option_map(options: Sequence[SelectOption]) -> dict[str, str]:
    return {o.value: o.label for o in options if not o.disabled}


class Select(_FieldRenderer):
    def __init__(self, label: str, options: Sequence[SelectOption] | dict[str, str], *, value: str | Sequence[str] | None = None,
                 description: str | None = None, error: str | None = None, required: bool = False,
                 disabled: bool = False, readonly: bool = False, clearable: bool = True, searchable: bool = False,
                 on_change: Callable[..., Any] | None = None, _multiple: bool = False):
        normalized = tuple(SelectOption(k, v) for k, v in options.items()) if isinstance(options, dict) else tuple(options)
        self.spec = SelectSpec(label=label, value=None if _multiple else value, options=normalized, description=description, error=error,
                               required=required, disabled=disabled, readonly=readonly, clearable=clearable, searchable=searchable)
        ui = _ui(); c = self._begin_field()
        props = ['outlined', 'dense', 'options-dense', 'hide-bottom-space']
        extra = _props_for_disabled(disabled, readonly)
        if extra: props.append(extra)
        props.append(self._accessibility_props())
        # NiceGUI owns dict option value/label mapping. Raw Quasar emit-value / map-options
        # double-transform NiceGUI's internal option representation and can make a menu
        # look open while its choices fail to update the Python value.
        self.element = ui.select(
            options=_option_map(normalized), value=list(value or ()) if _multiple else value,
            on_change=on_change, with_input=searchable, multiple=_multiple, clearable=clearable,
        ).props(' '.join(props)).classes(self.spec.classes + ' cui-select')
        if _multiple:
            self.element.props('use-chips').classes(add='cui-multi-select')
        self._end_field(c)


class MultiSelect(Select):
    def __init__(self, label: str, options: Sequence[SelectOption] | dict[str, str], *, value: Sequence[str] = (), **kwargs):
        normalized = tuple(SelectOption(k, v) for k, v in options.items()) if isinstance(options, dict) else tuple(options)
        super().__init__(label, normalized, value=tuple(value), _multiple=True, **kwargs)
        self.spec = MultiSelectSpec(label=label, value=tuple(value), options=normalized,
                                    description=kwargs.get('description'), error=kwargs.get('error'),
                                    required=kwargs.get('required', False), disabled=kwargs.get('disabled', False),
                                    readonly=kwargs.get('readonly', False), clearable=kwargs.get('clearable', True),
                                    searchable=kwargs.get('searchable', False))


class Autocomplete(Select):
    def __init__(self, label: str, options: Sequence[SelectOption] | dict[str, str], **kwargs):
        normalized = tuple(SelectOption(k, v) for k, v in options.items()) if isinstance(options, dict) else tuple(options)
        super().__init__(label, normalized, searchable=True, **kwargs)
        self.spec = AutocompleteSpec(label=label, options=normalized, value=kwargs.get('value'),
                                     description=kwargs.get('description'), error=kwargs.get('error'),
                                     required=kwargs.get('required', False), disabled=kwargs.get('disabled', False),
                                     readonly=kwargs.get('readonly', False))


class Combobox(Autocomplete):
    def __init__(self, label: str, options: Sequence[SelectOption] | dict[str, str], **kwargs):
        normalized = tuple(SelectOption(k, v) for k, v in options.items()) if isinstance(options, dict) else tuple(options)
        super().__init__(label, normalized, **kwargs)
        self.spec = ComboboxSpec(label=label, options=normalized, value=kwargs.get('value'),
                                 description=kwargs.get('description'), error=kwargs.get('error'),
                                 required=kwargs.get('required', False), disabled=kwargs.get('disabled', False),
                                 readonly=kwargs.get('readonly', False))
        self.element.props('new-value-mode=add-unique')


class _NativeChoice:
    input_type = 'checkbox'
    role: str | None = None

    def _render(self, label: str, checked: bool, description: str | None, disabled: bool,
                on_change: Callable[..., Any] | None, *, name: str | None = None, value: str | None = None,
                extra_class: str = ''):
        ui = _ui()
        self.element = ui.element('label').classes(f'cui-choice-row {extra_class}'.strip())
        with self.element:
            props = [f'type="{self.input_type}"']
            if name: props.append(f'name="{name}"')
            if value is not None: props.append(f'value="{value}"')
            if checked: props.append('checked')
            if disabled: props.append('disabled')
            if self.role: props.append(f'role="{self.role}"')
            self.control = ui.element('input').classes('cui-choice-native').props(' '.join(props))
            if on_change is not None:
                self.control.on('change', on_change)
            self._render_visual(ui)
            with ui.element('span').classes('cui-choice-copy'):
                ui.label(label).classes('cui-choice-label')
                if description:
                    ui.label(description).classes('cui-choice-help')
        return self.element

    def _render_visual(self, ui: Any) -> None:
        ui.element('span').classes('cui-choice-visual').props('aria-hidden="true"')


class Checkbox(_NativeChoice):
    def __init__(self, label: str, *, checked: bool = False, description: str | None = None,
                 disabled: bool = False, on_change: Callable[..., Any] | None = None):
        self.spec = CheckboxSpec(label=label, checked=checked, description=description, disabled=disabled)
        self._render(label, checked, description, disabled, on_change, extra_class='cui-choice-row--checkbox')


class CheckboxGroup:
    def __init__(self, label: str, options: Sequence[SelectOption], *, selected: Sequence[str] = (),
                 disabled: bool = False, on_change: Callable[..., Any] | None = None):
        self.spec = CheckboxGroupSpec(label=label, options=options, selected=selected, disabled=disabled)
        ui = _ui(); gid = f'cui-choice-group-{next(_FIELD_IDS)}'
        group_props = f'aria-labelledby="{gid}"' + (' aria-disabled="true"' if disabled else '')
        self.element = ui.element('fieldset').classes('cui-choice-group').props(group_props)
        with self.element:
            ui.label(label).classes('cui-field-label cui-choice-group__label').props(f'id="{gid}"')
            with ui.element('div').classes('cui-choice-group__options'):
                for option in options:
                    item = _NativeChoice()
                    item._render(option.label, option.value in selected, option.description, disabled or option.disabled, on_change,
                                 value=option.value, extra_class='cui-choice-row--checkbox')


class RadioGroup:
    def __init__(self, label: str, options: Sequence[SelectOption], *, selected: str | None = None,
                 on_change: Callable[..., Any] | None = None):
        self.spec = RadioGroupSpec(label=label, options=options, selected=selected)
        ui = _ui(); gid = f'cui-choice-group-{next(_FIELD_IDS)}'; name = f'{gid}-native'
        self.element = ui.element('fieldset').classes('cui-choice-group').props(f'aria-labelledby="{gid}"')
        with self.element:
            ui.label(label).classes('cui-field-label cui-choice-group__label').props(f'id="{gid}"')
            with ui.element('div').classes('cui-choice-group__options'):
                for option in options:
                    item = _NativeChoice(); item.input_type = 'radio'
                    item._render(option.label, option.value == selected, option.description, option.disabled, on_change,
                                 name=name, value=option.value, extra_class='cui-choice-row--radio')
        self.control = self.element


class Switch(_NativeChoice):
    role = 'switch'

    def _render_visual(self, ui: Any) -> None:
        # A real track/thumb DOM pair gives us deterministic 2px endpoint seating.
        # Do not collapse this back into a pseudo-element: disabled/zoom/DPR states
        # must preserve exactly the same geometry as the enabled switch.
        with ui.element('span').classes('cui-choice-visual cui-switch-track').props('aria-hidden="true"'):
            ui.element('span').classes('cui-switch-thumb')

    def __init__(self, label: str, *, checked: bool = False, description: str | None = None,
                 disabled: bool = False, on_change: Callable[..., Any] | None = None):
        self.spec = SwitchSpec(label=label, checked=checked, description=description, disabled=disabled)
        self._render(label, checked, description, disabled, on_change, extra_class='cui-choice-row--switch')


class Slider:
    def __init__(self, label: str, *, value: float, minimum: float = 0, maximum: float = 100,
                 step: float = 1, unit: str | None = None, disabled: bool = False,
                 on_change: Callable[..., Any] | None = None):
        self.spec = SliderSpec(label=label, value=value, minimum=minimum, maximum=maximum, step=step, unit=unit, disabled=disabled)
        ui = _ui(); self.element = ui.element('div').classes('cui-slider-field')
        with self.element:
            with ui.element('div').classes('cui-slider-head'):
                ui.label(label).classes('cui-field-label')
                self.value_label = ui.label(f'{value:g}{unit or ""}').classes('cui-slider-value')
            props = f'type="range" min="{minimum}" max="{maximum}" step="{step}" value="{value}" aria-label="{label}"'
            if disabled: props += ' disabled'
            pct = (value - minimum) / (maximum - minimum) * 100
            safe_unit = (unit or '').replace('\"','')
            props += f" oninput=\"this.style.setProperty('--pct',((this.value-this.min)/(this.max-this.min)*100)+'%');this.closest('.cui-slider-field').querySelector('.cui-slider-value').textContent=this.value+'{safe_unit}'\""
            self.control = ui.element('input').classes('cui-native-slider').props(props).style(f'--pct:{pct:.4f}%')
            if on_change is not None:
                self.control.on('change', on_change)
            with ui.element('div').classes('cui-slider-meta'):
                ui.label(f'{minimum:g}{unit or ""}'); ui.label(f'{maximum:g}{unit or ""}')


class RangeSlider:
    """Company-owned dual-handle range input.

    Two native range inputs share one track. This deliberately avoids Quasar's
    slider DOM so single-value and range sliders cannot drift apart visually.
    """
    def __init__(self, label: str, *, low: float, high: float, minimum: float = 0, maximum: float = 100,
                 step: float = 1, unit: str | None = None, disabled: bool = False,
                 on_change: Callable[..., Any] | None = None):
        self.spec = RangeSliderSpec(label=label, low=low, high=high, minimum=minimum, maximum=maximum, step=step, unit=unit, disabled=disabled)
        ui = _ui(); self.element = ui.element('div').classes('cui-slider-field cui-range-field')
        span = maximum - minimum
        low_pct = (low - minimum) / span * 100
        high_pct = (high - minimum) / span * 100
        safe_unit = (unit or '').replace('"', '').replace("'", '')
        with self.element:
            with ui.element('div').classes('cui-slider-head'):
                ui.label(label).classes('cui-field-label')
                self.value_label = ui.label(f'{low:g}–{high:g}{unit or ""}').classes('cui-slider-value')
            with ui.element('div').classes('cui-native-range').style(f'--low-pct:{low_pct:.4f}%;--high-pct:{high_pct:.4f}%') as self.control:
                ui.element('div').classes('cui-native-range__track').props('aria-hidden="true"')
                script = f"""const box=this.closest('.cui-native-range');
const lo=box.querySelector('[data-cui-range-handle=low]');
const hi=box.querySelector('[data-cui-range-handle=high]');
if(this===lo && Number(lo.value)>Number(hi.value)) lo.value=hi.value;
if(this===hi && Number(hi.value)<Number(lo.value)) hi.value=lo.value;
const min=Number(this.min), max=Number(this.max), range=max-min;
const lv=Number(lo.value), hv=Number(hi.value);
box.style.setProperty('--low-pct',((lv-min)/range*100)+'%');
box.style.setProperty('--high-pct',((hv-min)/range*100)+'%');
box.closest('.cui-range-field').querySelector('.cui-slider-value').textContent=lv.toLocaleString(undefined,{{maximumFractionDigits:6}})+'–'+hv.toLocaleString(undefined,{{maximumFractionDigits:6}})+'{safe_unit}';""".replace('\n',' ')
                common = f'type="range" min="{minimum}" max="{maximum}" step="{step}"'
                disabled_prop = ' disabled' if disabled else ''
                self.low_control = ui.element('input').classes('cui-native-range__input cui-native-range__input--low').props(
                    f'{common} value="{low}" data-cui-range-handle="low" aria-label="{label} lower bound"{disabled_prop} oninput="{script}"'
                )
                self.high_control = ui.element('input').classes('cui-native-range__input cui-native-range__input--high').props(
                    f'{common} value="{high}" data-cui-range-handle="high" aria-label="{label} upper bound"{disabled_prop} oninput="{script}"'
                )
                if on_change is not None:
                    self.low_control.on('change', on_change)
                    self.high_control.on('change', on_change)
            with ui.element('div').classes('cui-slider-meta'):
                ui.label(f'{minimum:g}{unit or ""}'); ui.label(f'{maximum:g}{unit or ""}')

class _NativeTemporalField(_FieldRenderer):
    input_type = 'date'
    spec_type = DatePickerSpec

    def __init__(self, label: str, *, value: str | None = None, description: str | None = None,
                 error: str | None = None, required: bool = False, disabled: bool = False, readonly: bool = False):
        self.spec = self.spec_type(label=label, value=value, description=description, error=error,
                                   required=required, disabled=disabled, readonly=readonly)
        ui = _ui(); c = self._begin_field(); props = ['outlined', 'dense', 'hide-bottom-space', f'type={self.input_type}']
        extra = _props_for_disabled(disabled, readonly)
        if extra: props.append(extra)
        props.append(self._accessibility_props())
        self.element = ui.input(value=value).props(' '.join(props)).classes(self.spec.classes)
        self._end_field(c)


class DatePicker(_NativeTemporalField):
    input_type = 'date'; spec_type = DatePickerSpec


class TimePicker(_NativeTemporalField):
    input_type = 'time'; spec_type = TimePickerSpec


class DateTimePicker(_NativeTemporalField):
    input_type = 'datetime-local'; spec_type = DateTimePickerSpec


class DateRangePicker:
    def __init__(self, label: str, *, start: str | None = None, end: str | None = None,
                 description: str | None = None, required: bool = False, disabled: bool = False):
        self.spec = DateRangePickerSpec(label=label, start=start, end=end, description=description, required=required, disabled=disabled)
        ui = _ui(); self.element = ui.column().classes('cui-field cui-field-width--wide')
        with self.element:
            ui.label(label + (' *' if required else '')).classes('cui-field-label')
            with ui.row().classes('cui-date-range-row'):
                self.start = ui.input(value=start).props(f'outlined dense hide-bottom-space type=date aria-label="{label} start date"').classes(self.spec.classes)
                self.end = ui.input(value=end).props(f'outlined dense hide-bottom-space type=date aria-label="{label} end date"').classes(self.spec.classes)
            if description: ui.label(description).classes('cui-field-description')
        if disabled:
            self.start.disable(); self.end.disable()


class FileUpload:
    def __init__(self, *, label: str = 'Upload files', accept: Sequence[str] = (), multiple: bool = False,
                 max_file_size_mb: int = 25, max_files: int = 1, disabled: bool = False,
                 upload_policy: UploadPolicy | None = None,
                 on_upload: Callable[..., Any] | None = None):
        self.spec = FileUploadSpec(label=label, accept=accept, multiple=multiple, max_file_size_mb=max_file_size_mb,
                                   max_files=max_files, disabled=disabled)
        self.upload_policy = upload_policy or UploadPolicy(max_bytes=max_file_size_mb * 1024 * 1024)
        if self.upload_policy.max_bytes > max_file_size_mb * 1024 * 1024:
            raise ValueError('upload_policy.max_bytes cannot exceed max_file_size_mb')
        self._on_upload = on_upload
        self._closed = False
        ui = _ui(); self.container = ui.element('section').classes('cui-upload-shell').props('tabindex="0"')
        with self.container:
            with ui.element('div').classes('cui-upload-shell__copy'):
                ui.label(label).classes('cui-field-label')
                ui.label('Click to browse, drag files here, or paste from the clipboard with Ctrl+V / Cmd+V.').classes('cui-field-description')
            props = []
            if multiple: props.append('multiple')
            if accept: props.append(f'accept={",".join(accept)}')
            props.append(f'aria-label="{label}"')
            self.element = ui.upload(on_upload=self._handle_upload, max_file_size=self.upload_policy.max_bytes,
                                     max_files=max_files).props(' '.join(props)).classes('cui-upload')
        if disabled:
            self.element.disable(); self.container.props('aria-disabled="true"')
        else:
            self._install_paste_bridge(ui)
        context=getattr(ui, 'context', None); client=getattr(context, 'client', None); on_delete=getattr(client, 'on_delete', None)
        if callable(on_delete): on_delete(self.dispose)

    @staticmethod
    def _metadata(event: Any) -> tuple[str, int, str | None, Any]:
        file_obj = getattr(event, 'file', None) or event
        name = str(getattr(file_obj, 'name', None) or getattr(event, 'name', None) or getattr(file_obj, 'filename', None) or 'upload')
        media_type = getattr(file_obj, 'content_type', None) or getattr(event, 'content_type', None) or getattr(file_obj, 'type', None)
        size = getattr(file_obj, 'size', None) or getattr(event, 'size', None)
        content = getattr(file_obj, 'content', None) or getattr(event, 'content', None)
        if isinstance(content, (bytes, bytearray, memoryview)):
            size = len(content) if size is None else size
        if size is None and hasattr(content, 'seek') and hasattr(content, 'tell'):
            position=content.tell(); content.seek(0, 2); size=content.tell(); content.seek(position)
        if size is None:
            raise ValueError('upload size metadata is required')
        return name, int(size), str(media_type) if media_type else None, content

    @staticmethod
    async def _head(content: Any, limit: int = 65536) -> bytes:
        if content is None: return b''
        if isinstance(content, (bytes, bytearray, memoryview)): return bytes(content[:limit])
        read=getattr(content, 'read', None)
        if not callable(read): return b''
        position=getattr(content, 'tell', lambda: None)()
        value=read(limit)
        if inspect.isawaitable(value): value=await value
        if position is not None and callable(getattr(content, 'seek', None)):
            restored=content.seek(position)
            if inspect.isawaitable(restored): await restored
        return bytes(value or b'')

    async def _handle_upload(self, event: Any) -> Any:
        name, size, media_type, content = self._metadata(event)
        head = await self._head(content)
        self.upload_policy.validate_content(name, size, media_type, head)
        if self._on_upload is None: return None
        result=self._on_upload(event)
        return await result if inspect.isawaitable(result) else result

    def _install_paste_bridge(self, ui: Any) -> None:
        raw_id = getattr(self.element, 'id', None)
        eid = raw_id if isinstance(raw_id, int) else None
        if eid is None: return
        ui.run_javascript(f"""(() => {{
          const uploader=getHtmlElement({eid}); if(!uploader || uploader.dataset.cuiPasteReady) return;
          uploader.dataset.cuiPasteReady='true';
          const shell=uploader.closest('.cui-upload-shell'); if(!shell) return;
          const onPaste = e => {{
            const incoming=[...(e.clipboardData?.files || [])]; if(!incoming.length) return;
            const input=uploader.querySelector('input[type=\"file\"]'); if(!input) return;
            const transfer=new DataTransfer(); incoming.forEach(file=>transfer.items.add(file));
            input.files=transfer.files; input.dispatchEvent(new Event('change',{{bubbles:true}}));
            e.preventDefault();
          }};
          const cleanup = () => {{ shell.removeEventListener('paste', onPaste); window.removeEventListener('pagehide', cleanup); delete uploader.__cuiPasteCleanup; delete uploader.dataset.cuiPasteReady; }};
          shell.addEventListener('paste', onPaste); window.addEventListener('pagehide', cleanup, {{once:true}}); uploader.__cuiPasteCleanup=cleanup;
        }})()""")

    def dispose(self, *_) -> None:
        if self._closed: return
        self._closed=True
        raw_id=getattr(self.element, 'id', None)
        if isinstance(raw_id, int):
            _ui().run_javascript(f"(() => {{ const el=getHtmlElement({raw_id}); el?.__cuiPasteCleanup?.(); }})()")


class ButtonGroup(AbstractContextManager):
    def __init__(self):
        self.element = _ui().element('div').classes('cui-button-group')
    def __enter__(self):
        self.element.__enter__(); return self
    def __exit__(self, exc_type, exc, tb):
        return self.element.__exit__(exc_type, exc, tb)


class SplitButton:
    def __init__(self, label: str, options: dict[str, Callable[[], None]], *, icon: str | None = None,
                 on_click: Callable[..., Any] | None = None, intent: ButtonIntent = ButtonIntent.PRIMARY):
        if not options:
            raise ValueError('SplitButton requires at least one alternate action')
        ui = _ui(); self.element = ui.element('div').classes('cui-split-button')
        with self.element:
            self.primary = Button(label, icon=icon, intent=intent, on_click=on_click).element
            menu_trigger = IconButton('more-horizontal', label='More actions', intent=intent)
            with menu_trigger.element:
                with ui.menu().classes('cui-menu cui-overlay-surface cui-overlay-surface--popover'):
                    for option_label, callback in options.items():
                        ui.button(option_label, on_click=callback).props('flat dense no-caps').classes('cui-menu-item')


class Divider:
    def __init__(self):
        self.element = _ui().element('hr').classes('cui-divider')


class CollapsiblePanel(AbstractContextManager):
    def __init__(self, title: str, *, open: bool = False):
        self.title = title; self.open = open; self.expansion = None
    def __enter__(self):
        self.expansion = _ui().expansion(self.title, value=self.open).props('duration=140').classes('cui-collapsible')
        self.expansion.__enter__(); return self
    def __exit__(self, exc_type, exc, tb):
        return self.expansion.__exit__(exc_type, exc, tb)


class Accordion(AbstractContextManager):
    """Single-open accordion group; ``Accordion(title)`` remains compatible."""
    def __init__(self, title: str | None = None, *, open: bool = False, multiple: bool = False):
        self.title=title; self.open=open; self.multiple=multiple; self._container=None; self._single=None; self._group=f'cui-accordion-{next(_FIELD_IDS)}'

    def __enter__(self):
        if self.title is not None:
            self._single=_ui().expansion(self.title, value=self.open).props('duration=140').classes('cui-collapsible cui-accordion__item')
            if not self.multiple: self._single.props(f'group={self._group}')
            self._single.__enter__(); return self
        self._container=_ui().element('div').classes('cui-accordion'); self._container.__enter__(); return self

    def item(self, title: str, *, open: bool = False):
        item=_ui().expansion(title, value=open).props('duration=140').classes('cui-collapsible cui-accordion__item')
        if not self.multiple: item.props(f'group={self._group}')
        return item

    def __exit__(self, exc_type, exc, tb):
        target=self._single or self._container
        return target.__exit__(exc_type, exc, tb) if target is not None else False


class Chip:
    def __init__(self, label: str, *, selected: bool = False, removable: bool = False, icon: str | None = None,
                 on_click: Callable[..., Any] | None = None):
        from nicegui_base.components import ChipSpec
        self.spec = ChipSpec(label, selected=selected, removable=removable, icon=icon)
        ui = _ui(); self.element = ui.button(on_click=on_click).props('flat no-caps dense').classes(self.spec.classes)
        with self.element:
            if icon: ui.html(render_icon_svg(icon, size='xs'), sanitize=False).classes('cui-svg-icon-host')
            ui.label(label)


class CountBadge:
    def __init__(self, count: int, *, maximum: int = 999):
        from nicegui_base.components import CountBadgeSpec
        self.spec = CountBadgeSpec(count, maximum)
        self.element = _ui().label(self.spec.display).classes('cui-count-badge')


class SeverityIndicator:
    def __init__(self, label: str, *, intent: StatusIntent):
        self.label = label; self.intent = intent
        self.element = _ui().label(label).classes(f'cui-semantic-indicator cui-semantic-indicator--{intent.value}')


class FreshnessIndicator:
    def __init__(self, label: str, *, stale: bool = False):
        from nicegui_base.components import FreshnessIndicatorSpec
        self.spec = FreshnessIndicatorSpec(label, stale=stale)
        self.element = _ui().label(label).classes(f'cui-semantic-indicator cui-semantic-indicator--{self.spec.intent.value}')


class DataQualityBadge:
    def __init__(self, quality):
        from nicegui_base.components import DataQualityBadgeSpec
        self.spec = DataQualityBadgeSpec(quality)
        self.badge = StatusBadge(quality.value.replace('_', ' ').title(), intent=self.spec.intent)
        self.element = self.badge.element
