from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Mapping

from nicegui_base.runtime import CompatibilityManifest, RuntimeConfig
from nicegui_base.visual import validate_visual_package


@dataclass(frozen=True, slots=True)
class DoctorFinding:
    code: str
    ok: bool
    message: str
    severity: str = 'error'


@dataclass(frozen=True, slots=True)
class DoctorReport:
    findings: tuple[DoctorFinding, ...]

    @property
    def ok(self) -> bool:
        return not any((not item.ok) and item.severity == 'error' for item in self.findings)

    def to_dict(self) -> dict[str, object]:
        return {'ok': self.ok, 'findings': [item.__dict__ if hasattr(item, '__dict__') else {
            'code': item.code, 'ok': item.ok, 'message': item.message, 'severity': item.severity
        } for item in self.findings]}


class RuntimeDoctor:
    def __init__(self, config: RuntimeConfig, *, manifest: CompatibilityManifest | None = None):
        self.config = config
        self.manifest = manifest or CompatibilityManifest()

    def run(self, environ: Mapping[str, str] | None = None) -> DoctorReport:
        env = os.environ if environ is None else environ
        findings: list[DoctorFinding] = []
        py = sys.version_info
        findings.append(DoctorFinding('PYTHON_VERSION', (3, 11) <= py[:2] < (3, 14), f'Python {py.major}.{py.minor}.{py.micro}'))
        try:
            ng = metadata.version('nicegui')
            findings.append(DoctorFinding('NICEGUI_VERSION', ng == self.manifest.nicegui_version, f'NiceGUI {ng}; expected {self.manifest.nicegui_version}'))
        except metadata.PackageNotFoundError:
            findings.append(DoctorFinding('NICEGUI_VERSION', False, 'NiceGUI is not installed in this runtime'))
        env_issues = self.config.validate_environment(env)
        findings.append(DoctorFinding('RUNTIME_ENV', not env_issues, 'runtime configuration valid' if not env_issues else ', '.join(env_issues)))
        visual_issues = validate_visual_package()
        findings.append(DoctorFinding('VISUAL_ASSETS', not visual_issues, f'{len(visual_issues)} visual asset issue(s)'))
        if self.config.expected_replicas > 1:
            shared = bool(env.get(self.config.redis_url_env))
            findings.append(DoctorFinding('SHARED_STORAGE', shared, 'shared Redis storage configured' if shared else 'multi-instance deployment requires shared persistence'))
        findings.append(DoctorFinding('NICEGUI_WORKERS', True, 'NiceGUI process worker count fixed at 1; scale with application instances'))
        return DoctorReport(tuple(findings))
