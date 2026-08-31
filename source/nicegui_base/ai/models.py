from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ValidationSeverity(str, Enum):
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    severity: ValidationSeverity
    message: str
    path: str
    line: int = 1
    column: int = 0
    suggestion: str | None = None

    def format(self) -> str:
        where = f'{self.path}:{self.line}:{self.column}'
        suffix = f' Fix: {self.suggestion}' if self.suggestion else ''
        return f'{self.severity.value.upper()} {self.code} {where} {self.message}{suffix}'


@dataclass(frozen=True, slots=True)
class ValidationReport:
    root: Path
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)
    scanned_files: int = 0

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is ValidationSeverity.ERROR)

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is ValidationSeverity.WARNING)

    @property
    def ok(self) -> bool:
        return not self.errors

    def exit_code(self, *, warnings_as_errors: bool = False) -> int:
        if self.errors or (warnings_as_errors and self.warnings):
            return 1
        return 0

    def to_dict(self) -> dict:
        return {
            'root': str(self.root),
            'scanned_files': self.scanned_files,
            'ok': self.ok,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'issues': [
                {
                    'code': i.code, 'severity': i.severity.value, 'message': i.message,
                    'path': i.path, 'line': i.line, 'column': i.column, 'suggestion': i.suggestion,
                }
                for i in self.issues
            ],
        }


@dataclass(frozen=True, slots=True)
class AiConstructionDefinition:
    key: str
    requirement_signal: str
    preferred_api: str
    inspect_first: str
    prohibited_shortcut: str
    rationale: str
