from __future__ import annotations

from .preview_data import checked_rows

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .catalog import all_entries
from .data_dock import DataDockModel, default_data_dock
from .generated_smoke import GeneratedSmokeReport
from .handoff_readiness import HandoffReadinessReport, attach_handoff_evidence, evaluate_handoff_readiness
from .project_audit import ProjectAudit, audit_project
from .project_codegen import generate_project_zip
from .runtime_proof import LiveSmokeReport, run_generated_live_smoke
from .starter_kits import StarterResolution, get_golden_starter, resolve_starter


@dataclass(frozen=True, slots=True)
class ProvenProjectPackage:
    project: Mapping[str, Any]
    audit: ProjectAudit
    payload: bytes
    source: GeneratedSmokeReport
    live: LiveSmokeReport | None
    readiness: HandoffReadinessReport

    @property
    def ok(self) -> bool:
        return self.readiness.ok and self.source.ok and self.live is not None and self.live.ok


@dataclass(frozen=True, slots=True)
class RuntimeProvenStarterPackage:
    starter_key: str
    project: Mapping[str, Any]
    resolution: StarterResolution
    audit: ProjectAudit
    payload: bytes
    source_ok: bool
    source_findings: tuple[str, ...]
    live: LiveSmokeReport | None
    readiness: HandoffReadinessReport

    @property
    def ok(self) -> bool:
        return self.readiness.ok and self.source_ok and not self.audit.blocking and self.live is not None and self.live.ok


def _project_data(project: Mapping[str, Any]) -> DataDockModel:
    rows = project.get('data_rows') if isinstance(project.get('data_rows'), (list, tuple)) else ()
    valid = [dict(row) for row in rows if isinstance(row, Mapping)]
    return DataDockModel(valid, sample_name='Project data') if valid else default_data_dock()


def finalize_generated_handoff(
    project: Mapping[str, Any], payload: bytes, source: GeneratedSmokeReport, live: LiveSmokeReport | None,
    *, browser: Any | None = None, audit_blocking: Sequence[Any] = (), portable_integrity: bool = True,
) -> tuple[bytes, HandoffReadinessReport]:
    readiness = evaluate_handoff_readiness(
        project,
        source_ok=source.ok,
        source_findings=source.findings,
        audit_blocking=audit_blocking,
        live=live,
        browser=browser,
        portable_integrity=portable_integrity,
    )
    final_payload = attach_handoff_evidence(payload, readiness, live=live, browser=browser)
    from .generated_smoke import smoke_generated_zip
    post = smoke_generated_zip(final_payload)
    if not post.ok:
        readiness = evaluate_handoff_readiness(
            project, source_ok=False, source_findings=(*source.findings, *post.findings),
            audit_blocking=audit_blocking, live=live, browser=browser, portable_integrity=portable_integrity,
        )
        final_payload = attach_handoff_evidence(payload, readiness, live=live, browser=browser)
    return final_payload, readiness


def prove_project(
    project: Mapping[str, Any], *, data_model: DataDockModel | None = None, timeout_seconds: float = 25.0,
    live_smoke=run_generated_live_smoke,
) -> ProvenProjectPackage:
    entries = all_entries()
    data = data_model or _project_data(project)
    audit = audit_project(project, entries, data_model=data)
    if audit.blocking:
        messages = [item.message for item in audit.blocking]
        raise ValueError(f'project audit blocked generation: {messages}')
    lookup = {entry.key: entry for entry in entries}
    payload, source = generate_project_zip(project, lookup)
    live = live_smoke(payload, timeout_seconds=timeout_seconds) if source.ok else None
    final_payload, readiness = finalize_generated_handoff(
        project, payload, source, live, audit_blocking=audit.blocking,
    )
    return ProvenProjectPackage(project, audit, final_payload, source, live, readiness)


def _project_from_starter(starter_key: str, rows: Sequence[Mapping[str, Any]] = ()) -> tuple[dict[str, Any], StarterResolution, DataDockModel]:
    spec = get_golden_starter(starter_key)
    data = DataDockModel(rows, sample_name='Quick-build data') if rows else default_data_dock()
    entries = all_entries()
    resolution = resolve_starter(spec, entries, data_model=data)
    if resolution.unresolved:
        raise ValueError(f'{starter_key}: unresolved required intents: {resolution.unresolved}')
    project = {
        'name': spec.title.replace('/', '-').replace('\\', '-').strip(),
        'goal': spec.goal,
        'problem_type': spec.problem_type,
        'pattern_key': resolution.pattern_key,
        'placements': {slot: list(keys) for slot, keys in resolution.placements.items()},
        'queued_entry_keys': [],
        'data_rows': checked_rows(data.serializable_rows()),
        'theme': 'system',
        'density': 'compact',
        'revision': 0,
    }
    return project, resolution, data


def build_runtime_proven_starter(
    starter_key: str, *, rows: Sequence[Mapping[str, Any]] = (), timeout_seconds: float = 25.0,
    live_smoke=run_generated_live_smoke,
) -> RuntimeProvenStarterPackage:
    project, resolution, data = _project_from_starter(starter_key, rows)
    package = prove_project(project, data_model=data, timeout_seconds=timeout_seconds, live_smoke=live_smoke)
    return RuntimeProvenStarterPackage(
        starter_key,
        project,
        resolution,
        package.audit,
        package.payload,
        package.source.ok,
        tuple(package.source.findings),
        package.live,
        package.readiness,
    )


__all__ = [
    'ProvenProjectPackage', 'RuntimeProvenStarterPackage', 'build_runtime_proven_starter',
    'finalize_generated_handoff', 'prove_project',
]
