from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Mapping, Sequence


class ValidationSeverity(str, Enum):
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    field: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    code: str | None = None

    def __post_init__(self) -> None:
        if not self.field.strip() or not self.message.strip():
            raise ValueError('ValidationIssue requires field and message')


Validator = Callable[[object | None], str | None]


@dataclass(frozen=True, slots=True)
class FieldValidation:
    field: str
    validators: Sequence[Validator] = field(default_factory=tuple)

    def validate(self, value: object | None) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []
        for validator in self.validators:
            message = validator(value)
            if message:
                issues.append(ValidationIssue(self.field, message))
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class FormSpec:
    key: str
    title: str | None = None
    description: str | None = None
    submit_label: str = 'Save'
    cancel_label: str = 'Cancel'
    dirty_guard: bool = True
    validate_on: str = 'hybrid'

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError('FormSpec key must not be empty')
        if self.validate_on not in {'submit', 'blur', 'live', 'hybrid'}:
            raise ValueError('validate_on must be submit, blur, live, or hybrid')




@dataclass(frozen=True, slots=True)
class FormFieldSpec:
    key: str
    label: str
    description: str | None = None
    required: bool = False
    error: str | None = None
    full_width: bool = False

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError('FormFieldSpec requires key and label')

    @property
    def classes(self) -> str:
        return 'cui-form-field' + (' is-full' if self.full_width else '') + (' has-error' if self.error else '')


@dataclass(frozen=True, slots=True)
class FormSectionSpec:
    title: str
    description: str | None = None
    collapsible: bool = False
    default_open: bool = True

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError('FormSectionSpec title must not be empty')


@dataclass(frozen=True, slots=True)
class FormActionsSpec:
    primary_label: str = 'Save'
    secondary_label: str = 'Cancel'
    destructive_label: str | None = None
    sticky: bool = False
    align: str = 'end'

    def __post_init__(self) -> None:
        if self.align not in {'start', 'center', 'end', 'between'}:
            raise ValueError('Unsupported action alignment')


@dataclass(frozen=True, slots=True)
class FormState:
    values: Mapping[str, object | None] = field(default_factory=dict)
    initial_values: Mapping[str, object | None] = field(default_factory=dict)
    issues: Sequence[ValidationIssue] = field(default_factory=tuple)
    submitting: bool = False
    submitted: bool = False

    @property
    def dirty(self) -> bool:
        return dict(self.values) != dict(self.initial_values)

    @property
    def valid(self) -> bool:
        return not any(issue.severity is ValidationSeverity.ERROR for issue in self.issues)


@dataclass(frozen=True, slots=True)
class DirtyStateGuardSpec:
    enabled: bool = True
    message: str = 'You have unsaved changes. Leave without saving?'


@dataclass(frozen=True, slots=True)
class ValidationSummarySpec:
    issues: Sequence[ValidationIssue]
    title: str = 'Please review the highlighted fields'

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity is ValidationSeverity.ERROR)
