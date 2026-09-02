from __future__ import annotations

import importlib.metadata
import io
import json
import os
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

EXPECTED_NICEGUI_VERSION = '3.15.0'


@dataclass(frozen=True, slots=True)
class EnvironmentReadiness:
    ok: bool
    python: str
    nicegui: str
    framework: str
    temp_writable: bool
    findings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            'ok': self.ok,
            'python': self.python,
            'nicegui': self.nicegui,
            'framework': self.framework,
            'temp_writable': self.temp_writable,
            'findings': list(self.findings),
        }


@dataclass(frozen=True, slots=True)
class HandoffReadinessReport:
    status: str
    project_signature: str
    source_ok: bool
    runtime_ok: bool | None
    browser_status: str
    portable_integrity: bool
    environment: EnvironmentReadiness
    findings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.status in {'READY_RUNTIME_PROVEN_BROWSER_PENDING', 'READY_BROWSER_PROVEN'}

    def to_dict(self) -> dict[str, object]:
        return {
            'schema_version': 1,
            'status': self.status,
            'project_signature': self.project_signature,
            'source_ok': self.source_ok,
            'runtime_ok': self.runtime_ok,
            'browser_status': self.browser_status,
            'portable_integrity': self.portable_integrity,
            'environment': self.environment.to_dict(),
            'findings': list(self.findings),
        }


def environment_readiness() -> EnvironmentReadiness:
    findings: list[str] = []
    py = '.'.join(str(item) for item in sys.version_info[:3])
    if not ((3, 11) <= sys.version_info[:2] < (3, 14)):
        findings.append(f'python:{py}:requires>=3.11,<3.14')
    try:
        nicegui = importlib.metadata.version('nicegui')
    except importlib.metadata.PackageNotFoundError:
        nicegui = ''
        findings.append('nicegui:not_installed')
    if nicegui and nicegui != EXPECTED_NICEGUI_VERSION:
        findings.append(f'nicegui:{nicegui}:expected={EXPECTED_NICEGUI_VERSION}')
    try:
        from nicegui_base.version import FRAMEWORK_VERSION
        framework = str(FRAMEWORK_VERSION)
    except Exception as exc:
        framework = ''
        findings.append(f'framework:{type(exc).__name__}')
    temp_writable = False
    try:
        with tempfile.NamedTemporaryFile(prefix='nicegui-base-readiness-', delete=True) as handle:
            handle.write(b'proof')
            handle.flush()
            temp_writable = os.path.exists(handle.name)
    except OSError as exc:
        findings.append(f'temp:{type(exc).__name__}')
    return EnvironmentReadiness(not findings, py, nicegui, framework, temp_writable, tuple(dict.fromkeys(findings)))


def evaluate_handoff_readiness(
    project: Mapping[str, Any], *, source_ok: bool, source_findings: Sequence[str] = (),
    audit_blocking: Sequence[Any] = (), live: Any | None = None, browser: Any | None = None,
    portable_integrity: bool = True,
) -> HandoffReadinessReport:
    from .project_history import project_signature
    env = environment_readiness()
    findings = [str(item) for item in source_findings if str(item)]
    findings.extend(str(getattr(item, 'message', item)) for item in audit_blocking)
    if not portable_integrity:
        findings.append('portable_project:integrity_failed')
    runtime_ok = None if live is None else bool(getattr(live, 'ok', False))
    if live is not None and not runtime_ok:
        findings.extend(str(item) for item in getattr(live, 'findings', ()) if str(item))
    browser_status = str(getattr(browser, 'status', 'PENDING_BROWSER_EXECUTION') if browser is not None else 'PENDING_BROWSER_EXECUTION')
    browser_ok = bool(getattr(browser, 'ok', False)) if browser is not None else False

    if findings or not source_ok or audit_blocking or not portable_integrity:
        status = 'BLOCKED'
    elif runtime_ok is False:
        status = 'BLOCKED'
    elif runtime_ok is None:
        status = 'READY_SOURCE_PROVEN_RUNTIME_PENDING'
    elif browser_ok:
        status = 'READY_BROWSER_PROVEN'
    else:
        status = 'READY_RUNTIME_PROVEN_BROWSER_PENDING'

    # Environment findings describe the machine executing Workbench. They are blocking only
    # when source/runtime work has not already demonstrated a viable environment.
    if not env.ok and runtime_ok is not True:
        status = 'BLOCKED'
        findings.extend(env.findings)

    return HandoffReadinessReport(
        status,
        project_signature(project),
        bool(source_ok),
        runtime_ok,
        browser_status,
        bool(portable_integrity),
        env,
        tuple(dict.fromkeys(findings)),
    )


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, default=str) + '\n').encode('utf-8')


def attach_handoff_evidence(payload: bytes, report: HandoffReadinessReport, *, live: Any | None = None, browser: Any | None = None) -> bytes:
    source = io.BytesIO(bytes(payload))
    output = io.BytesIO()
    with zipfile.ZipFile(source) as incoming:
        bad = incoming.testzip()
        if bad:
            raise ValueError(f'Cannot attach evidence to corrupt generated ZIP: {bad}')
        names = incoming.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Cannot attach evidence to ZIP with duplicate paths.')
        replacements: dict[str, bytes] = {
            '.nicegui_base/handoff_readiness.json': _json_bytes(report.to_dict()),
        }
        if live is not None:
            live_payload = live.to_dict() if hasattr(live, 'to_dict') else live
            replacements['.nicegui_base/runtime_evidence.json'] = _json_bytes(live_payload)
        if browser is not None:
            browser_payload = browser.to_dict() if hasattr(browser, 'to_dict') else browser
            replacements['.nicegui_base/browser_acceptance_evidence.json'] = _json_bytes(browser_payload)
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in sorted(set(names) | set(replacements)):
                data = replacements[name] if name in replacements else incoming.read(name)
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, data)
    return output.getvalue()


__all__ = [
    'EXPECTED_NICEGUI_VERSION', 'EnvironmentReadiness', 'HandoffReadinessReport',
    'attach_handoff_evidence', 'environment_readiness', 'evaluate_handoff_readiness',
]
