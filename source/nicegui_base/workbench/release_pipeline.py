from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .catalog import all_entries
from .data_dock import DataDockModel, default_data_dock
from .project_audit import ProjectAudit, audit_project
from .project_codegen import generate_project_zip
from .runtime_proof import LiveSmokeReport, run_generated_live_smoke
from .starter_kits import StarterResolution, get_golden_starter, resolve_starter


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

    @property
    def ok(self) -> bool:
        return self.source_ok and not self.audit.blocking and self.live is not None and self.live.ok


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
        'data_rows': list(data.serializable_rows())[:200],
        'theme': 'system',
        'density': 'compact',
        'revision': 0,
    }
    return project, resolution, data


def build_runtime_proven_starter(starter_key: str, *, rows: Sequence[Mapping[str, Any]] = (), timeout_seconds: float = 25.0, live_smoke=run_generated_live_smoke) -> RuntimeProvenStarterPackage:
    project, resolution, data = _project_from_starter(starter_key, rows)
    entries = all_entries()
    audit = audit_project(project, entries, data_model=data)
    if audit.blocking:
        raise ValueError(f'{starter_key}: project audit blocked generation: {[item.message for item in audit.blocking]}')
    lookup = {entry.key: entry for entry in entries}
    payload, source = generate_project_zip(project, lookup)
    live = live_smoke(payload, timeout_seconds=timeout_seconds) if source.ok else None
    return RuntimeProvenStarterPackage(
        starter_key, project, resolution, audit, payload, source.ok, tuple(source.findings), live,
    )


__all__ = ['RuntimeProvenStarterPackage', 'build_runtime_proven_starter']
