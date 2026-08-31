from __future__ import annotations

from pathlib import Path

from .accessibility_contract import scan_accessibility_contract
from .css_contract import scan_geometry_contract
from .models import GovernanceFinding, GovernanceReport
from .public_api import scan_public_api_contract
from .release_contract import scan_release_contract
from .typography_motion_contract import scan_typography_motion_contract
from nicegui_base.ai.validator import validate_app


def run_governance(root: str | Path = '.') -> GovernanceReport:
    source_root = Path(root).resolve()
    validation = validate_app(source_root)
    validation_findings = tuple(
        GovernanceFinding(
            rule=f'application.{issue.code.lower()}', path=issue.path, detail=issue.message,
            line=issue.line, severity='error',
        )
        for issue in validation.issues if issue.severity.value == 'error'
    )
    findings = (
        *scan_release_contract(source_root),
        *scan_accessibility_contract(source_root),
        *scan_geometry_contract(source_root),
        *scan_typography_motion_contract(source_root),
        *scan_public_api_contract(source_root),
        *validation_findings,
    )
    return GovernanceReport(source_root, tuple(findings))
