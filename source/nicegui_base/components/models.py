from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Sequence


class ComponentSize(str, Enum):
    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE = 'large'


class ButtonIntent(str, Enum):
    PRIMARY = 'primary'
    SECONDARY = 'secondary'
    TERTIARY = 'tertiary'
    GHOST = 'ghost'
    DANGER = 'danger'


class SurfaceVariant(str, Enum):
    PANEL = 'panel'
    CARD = 'card'
    INTERACTIVE = 'interactive'
    WELL = 'well'
    OUTLINED = 'outlined'


class StatusIntent(str, Enum):
    NEUTRAL = 'neutral'
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    DANGER = 'danger'


class ControlState(str, Enum):
    DEFAULT = 'default'
    ERROR = 'error'
    SUCCESS = 'success'
    READONLY = 'readonly'


class InputWidth(str, Enum):
    AUTO = 'auto'
    MEDIUM = 'medium'
    WIDE = 'wide'
    FULL = 'full'


class DatePrecision(str, Enum):
    DATE = 'date'
    MONTH = 'month'
    YEAR = 'year'


@dataclass(frozen=True, slots=True)
class ButtonSpec:
    label: str
    intent: ButtonIntent = ButtonIntent.SECONDARY
    size: ComponentSize = ComponentSize.MEDIUM
    icon: str | None = None
    disabled: bool = False
    loading: bool = False
    full_width: bool = False
    aria_label: str | None = None

    def __post_init__(self) -> None:
        if not self.label.strip() and not self.aria_label:
            raise ValueError('ButtonSpec requires a visible label or aria_label')

    @property
    def classes(self) -> str:
        parts = ['cui-button', f'cui-button--{self.intent.value}', f'cui-control--{self.size.value}']
        if self.loading:
            parts.append('is-loading')
        if self.full_width:
            parts.append('is-full-width')
        return ' '.join(parts)


@dataclass(frozen=True, slots=True)
class IconButtonSpec:
    icon: str
    label: str
    intent: ButtonIntent = ButtonIntent.GHOST
    size: ComponentSize = ComponentSize.MEDIUM
    disabled: bool = False
    selected: bool = False

    def __post_init__(self) -> None:
        if not self.icon.strip() or not self.label.strip():
            raise ValueError('IconButtonSpec requires icon and accessible label')

    @property
    def classes(self) -> str:
        parts = ['cui-icon-button', f'cui-icon-button--{self.intent.value}', f'cui-control--{self.size.value}']
        if self.selected:
            parts.append('is-selected')
        return ' '.join(parts)


@dataclass(frozen=True, slots=True)
class ActionButtonSpec(ButtonSpec):
    success_message: str | None = None
    error_message: str | None = None
    prevent_duplicate: bool = True


@dataclass(frozen=True, slots=True)
class SurfaceSpec:
    variant: SurfaceVariant = SurfaceVariant.PANEL
    interactive: bool = False
    selected: bool = False
    title: str | None = None

    @property
    def classes(self) -> str:
        parts = ['cui-surface', f'cui-surface--{self.variant.value}']
        if self.interactive or self.variant is SurfaceVariant.INTERACTIVE:
            parts.append('is-interactive')
        if self.selected:
            parts.append('is-selected')
        return ' '.join(parts)


@dataclass(frozen=True, slots=True)
class BadgeSpec:
    label: str
    intent: StatusIntent = StatusIntent.NEUTRAL
    icon: str | None = None
    subtle: bool = True

    @property
    def classes(self) -> str:
        return f"cui-badge cui-badge--{self.intent.value}{' cui-badge--subtle' if self.subtle else ''}"


@dataclass(frozen=True, slots=True)
class FieldSpec:
    label: str
    value: object | None = None
    placeholder: str | None = None
    description: str | None = None
    error: str | None = None
    required: bool = False
    disabled: bool = False
    readonly: bool = False
    size: ComponentSize = ComponentSize.MEDIUM
    width: InputWidth = InputWidth.AUTO
    leading_icon: str | None = None
    trailing_icon: str | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError('Field label must not be empty')
        if self.disabled and self.readonly:
            raise ValueError('Field cannot be both disabled and readonly')

    @property
    def state(self) -> ControlState:
        if self.error:
            return ControlState.ERROR
        if self.readonly:
            return ControlState.READONLY
        return ControlState.DEFAULT

    @property
    def classes(self) -> str:
        return ' '.join([
            'cui-field-control',
            f'cui-control--{self.size.value}',
            f'cui-field-control--{self.state.value}',
            f'cui-field-width--{self.width.value}',
        ])


@dataclass(frozen=True, slots=True)
class TextInputSpec(FieldSpec):
    clearable: bool = False
    password: bool = False
    maxlength: int | None = None


@dataclass(frozen=True, slots=True)
class NumberInputSpec(FieldSpec):
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        FieldSpec.__post_init__(self)
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError('minimum cannot exceed maximum')


@dataclass(frozen=True, slots=True)
class TextAreaSpec(FieldSpec):
    rows: int = 4
    maxlength: int | None = None

    def __post_init__(self) -> None:
        FieldSpec.__post_init__(self)
        if self.rows < 2:
            raise ValueError('TextAreaSpec rows must be >= 2')


@dataclass(frozen=True, slots=True)
class SearchInputSpec(FieldSpec):
    debounce_ms: int = 250
    clearable: bool = True
    shortcut: str | None = '/'

    def __post_init__(self) -> None:
        FieldSpec.__post_init__(self)
        if self.debounce_ms < 0:
            raise ValueError('debounce_ms must be >= 0')


@dataclass(frozen=True, slots=True)
class SelectOption:
    value: str
    label: str
    description: str | None = None
    disabled: bool = False


@dataclass(frozen=True, slots=True)
class SelectSpec(FieldSpec):
    options: Sequence[SelectOption] = field(default_factory=tuple)
    clearable: bool = True
    searchable: bool = False


@dataclass(frozen=True, slots=True)
class MultiSelectSpec(SelectSpec):
    max_selected: int | None = None


@dataclass(frozen=True, slots=True)
class AutocompleteSpec(SelectSpec):
    searchable: bool = True
    min_chars: int = 1


@dataclass(frozen=True, slots=True)
class ComboboxSpec(SelectSpec):
    searchable: bool = True
    allow_custom: bool = True


@dataclass(frozen=True, slots=True)
class CheckboxSpec:
    label: str
    checked: bool = False
    description: str | None = None
    disabled: bool = False
    indeterminate: bool = False


@dataclass(frozen=True, slots=True)
class CheckboxGroupSpec:
    label: str
    options: Sequence[SelectOption]
    selected: Sequence[str] = field(default_factory=tuple)
    disabled: bool = False


@dataclass(frozen=True, slots=True)
class RadioGroupSpec:
    label: str
    options: Sequence[SelectOption]
    selected: str | None = None
    disabled: bool = False


@dataclass(frozen=True, slots=True)
class SwitchSpec:
    label: str
    checked: bool = False
    description: str | None = None
    disabled: bool = False


@dataclass(frozen=True, slots=True)
class SliderSpec:
    label: str
    value: float
    minimum: float = 0
    maximum: float = 100
    step: float = 1
    unit: str | None = None
    disabled: bool = False

    def __post_init__(self) -> None:
        if self.minimum >= self.maximum:
            raise ValueError('minimum must be less than maximum')
        if self.step <= 0:
            raise ValueError('step must be positive')
        if not (self.minimum <= self.value <= self.maximum):
            raise ValueError('value outside slider bounds')


@dataclass(frozen=True, slots=True)
class RangeSliderSpec:
    label: str
    low: float
    high: float
    minimum: float = 0
    maximum: float = 100
    step: float = 1
    unit: str | None = None
    disabled: bool = False

    def __post_init__(self) -> None:
        if self.minimum >= self.maximum or self.low > self.high:
            raise ValueError('invalid range slider bounds')
        if self.step <= 0:
            raise ValueError('step must be positive')
        if self.low < self.minimum or self.high > self.maximum:
            raise ValueError('range outside slider bounds')


@dataclass(frozen=True, slots=True)
class DatePickerSpec(FieldSpec):
    precision: DatePrecision = DatePrecision.DATE


@dataclass(frozen=True, slots=True)
class DateRangePickerSpec(FieldSpec):
    start: str | None = None
    end: str | None = None


@dataclass(frozen=True, slots=True)
class TimePickerSpec(FieldSpec):
    use_24_hour: bool = True


@dataclass(frozen=True, slots=True)
class DateTimePickerSpec(FieldSpec):
    use_24_hour: bool = True


@dataclass(frozen=True, slots=True)
class FileUploadSpec:
    label: str = 'Upload files'
    accept: Sequence[str] = field(default_factory=tuple)
    multiple: bool = False
    max_file_size_mb: int = 25
    max_files: int = 1
    disabled: bool = False

    def __post_init__(self) -> None:
        if self.max_file_size_mb <= 0 or self.max_files <= 0:
            raise ValueError('upload limits must be positive')
        if not self.multiple and self.max_files != 1:
            raise ValueError('max_files must be 1 when multiple=False')

class DataQuality(str, Enum):
    COMPLETE = 'complete'
    PARTIAL = 'partial'
    DELAYED = 'delayed'
    ESTIMATED = 'estimated'
    UNAVAILABLE = 'unavailable'


@dataclass(frozen=True, slots=True)
class ChipSpec:
    label: str
    selected: bool = False
    removable: bool = False
    icon: str | None = None

    @property
    def classes(self) -> str:
        return 'cui-chip' + (' is-selected' if self.selected else '')


@dataclass(frozen=True, slots=True)
class CountBadgeSpec:
    count: int
    maximum: int = 999

    def __post_init__(self) -> None:
        if self.count < 0 or self.maximum < 1:
            raise ValueError('invalid count badge values')

    @property
    def display(self) -> str:
        return f'{self.maximum}+' if self.count > self.maximum else str(self.count)


@dataclass(frozen=True, slots=True)
class FreshnessIndicatorSpec:
    label: str
    stale: bool = False

    @property
    def intent(self) -> StatusIntent:
        return StatusIntent.WARNING if self.stale else StatusIntent.NEUTRAL


@dataclass(frozen=True, slots=True)
class DataQualityBadgeSpec:
    quality: DataQuality

    @property
    def intent(self) -> StatusIntent:
        return {
            DataQuality.COMPLETE: StatusIntent.SUCCESS,
            DataQuality.PARTIAL: StatusIntent.WARNING,
            DataQuality.DELAYED: StatusIntent.WARNING,
            DataQuality.ESTIMATED: StatusIntent.INFO,
            DataQuality.UNAVAILABLE: StatusIntent.DANGER,
        }[self.quality]
