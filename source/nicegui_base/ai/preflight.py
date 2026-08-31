from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from nicegui_base.ai.validator import ValidatorConfig, validate_app
from nicegui_base.version import FRAMEWORK_VERSION


@dataclass(frozen=True, slots=True)
class AgentPreflightReport:
    root: Path
    framework_version: str
    scaffold_present: bool
    scaffold_version: str | None
    validation_errors: int
    validation_warnings: int
    issues: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.scaffold_present and self.scaffold_version == self.framework_version and self.validation_errors == 0 and self.validation_warnings == 0

    def to_dict(self) -> dict:
        return {
            'root': str(self.root),
            'framework_version': self.framework_version,
            'scaffold_present': self.scaffold_present,
            'scaffold_version': self.scaffold_version,
            'validation_errors': self.validation_errors,
            'validation_warnings': self.validation_warnings,
            'passed': self.passed,
            'issues': list(self.issues),
        }


def run_agent_preflight(root: str | Path = '.') -> AgentPreflightReport:
    root = Path(root).resolve()
    issues: list[str] = []
    required = (root / 'AGENTS.md', root / '.nicegui_base' / 'construction_manifest.json', root / '.nicegui_base' / 'framework_catalog.json')
    scaffold_present = all(path.exists() for path in required)
    scaffold_version: str | None = None
    install_manifest = root / '.nicegui_base' / 'install_manifest.json'
    if install_manifest.exists():
        try:
            scaffold_version = str(json.loads(install_manifest.read_text(encoding='utf-8')).get('framework_version') or '') or None
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            issues.append('Invalid .nicegui_base/install_manifest.json; rerun nicegui-base agent-init --overwrite.')
    if not scaffold_present:
        issues.append('Agent scaffold is incomplete; run nicegui-base agent-init .')
    if scaffold_version != FRAMEWORK_VERSION:
        issues.append(f'Agent scaffold version {scaffold_version!r} does not match installed NiceGUI Base {FRAMEWORK_VERSION!r}.')
    validation = validate_app(root, config=ValidatorConfig(warnings_as_errors=True))
    for issue in validation.issues:
        issues.append(issue.format())
    return AgentPreflightReport(
        root=root,
        framework_version=FRAMEWORK_VERSION,
        scaffold_present=scaffold_present,
        scaffold_version=scaffold_version,
        validation_errors=len(validation.errors),
        validation_warnings=len(validation.warnings),
        issues=tuple(issues),
    )


__all__ = ['AgentPreflightReport', 'run_agent_preflight']
