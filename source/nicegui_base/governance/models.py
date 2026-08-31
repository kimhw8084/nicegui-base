from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GovernanceFinding:
    rule: str
    path: str
    detail: str
    line: int | None = None
    severity: str = 'error'

    def to_dict(self) -> dict[str, object]:
        return {
            'rule': self.rule,
            'path': self.path,
            'line': self.line,
            'severity': self.severity,
            'detail': self.detail,
        }


@dataclass(frozen=True, slots=True)
class GovernanceReport:
    root: Path
    findings: tuple[GovernanceFinding, ...] = field(default_factory=tuple)

    @property
    def errors(self) -> tuple[GovernanceFinding, ...]:
        return tuple(item for item in self.findings if item.severity == 'error')

    @property
    def warnings(self) -> tuple[GovernanceFinding, ...]:
        return tuple(item for item in self.findings if item.severity == 'warning')

    @property
    def passed(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            'root': str(self.root),
            'passed': self.passed,
            'summary': {'errors': len(self.errors), 'warnings': len(self.warnings)},
            'findings': [item.to_dict() for item in self.findings],
        }
