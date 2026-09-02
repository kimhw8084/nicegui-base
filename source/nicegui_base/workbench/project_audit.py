from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from .project_codegen import is_composable_entry


class AuditSeverity(str, Enum):
    INFO = 'info'
    WARNING = 'warning'
    BLOCKING = 'blocking'


@dataclass(frozen=True, slots=True)
class ProjectFinding:
    code: str
    severity: AuditSeverity
    message: str
    slot: str | None = None
    entry_key: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectAudit:
    findings: tuple[ProjectFinding, ...]
    required_slots: tuple[str, ...]
    explicit_required_slots: tuple[str, ...]
    placed_capabilities: int

    @property
    def blocking(self) -> tuple[ProjectFinding, ...]:
        return tuple(item for item in self.findings if item.severity is AuditSeverity.BLOCKING)

    @property
    def warnings(self) -> tuple[ProjectFinding, ...]:
        return tuple(item for item in self.findings if item.severity is AuditSeverity.WARNING)

    @property
    def status(self) -> str:
        if self.blocking:
            return 'BLOCKED'
        if self.warnings:
            return 'READY WITH WARNINGS'
        return 'READY'



def _registry(entry: Any) -> str:
    return str(getattr(entry, 'metadata', {}).get('registry_name') or '')


def _registry_key(entry: Any) -> str:
    metadata = getattr(entry, 'metadata', {})
    return str(metadata.get('registry_key') or metadata.get('component_key') or '')


def _kind(entry: Any) -> str:
    return getattr(getattr(entry, 'kind', None), 'value', str(getattr(entry, 'kind', '')))


def _slot_preference(entry: Any) -> tuple[str, ...]:
    registry = _registry(entry)
    key = _registry_key(entry)
    if registry == 'tables':
        return ('data', 'details', 'content', 'primary')
    if registry == 'visualizations' or _kind(entry) == 'analytic':
        return ('primary', 'secondary', 'content', 'data')
    if key in {'metric_card', 'metric_strip', 'status_badge', 'alert'}:
        return ('metrics', 'primary', 'details', 'content')
    if key in {'search_input', 'select'}:
        return ('filters', 'navigation', 'content')
    if key == 'text_input':
        return ('content', 'details')
    if key in {'button', 'action_button'}:
        return ('actions', 'content')
    return ()


def audit_project(project: Mapping[str, Any], entries: Iterable[Any], *, data_model: Any | None = None) -> ProjectAudit:
    from nicegui_base.patterns.registry import get_pattern

    findings: list[ProjectFinding] = []
    lookup = {str(getattr(entry, 'key', '')): entry for entry in entries}
    pattern_key = str(project.get('pattern_key') or '')
    if not pattern_key:
        return ProjectAudit((ProjectFinding('missing_pattern', AuditSeverity.BLOCKING, 'Choose an application pattern.'),), (), (), 0)
    try:
        definition = get_pattern(pattern_key)
    except Exception:
        return ProjectAudit((ProjectFinding('invalid_pattern', AuditSeverity.BLOCKING, f'Unknown application pattern: {pattern_key!r}.'),), (), (), 0)

    allowed = tuple(slot.value for slot in definition.slot_order if slot.value != 'header')
    allowed_set = set(allowed)
    required = tuple(slot.value for slot in definition.required_slots if slot.value != 'header')
    placements = project.get('placements') if isinstance(project.get('placements'), Mapping) else {}
    seen: dict[str, str] = {}
    placed = 0

    for raw_slot, raw_keys in placements.items():
        slot = str(raw_slot)
        if slot not in allowed_set:
            findings.append(ProjectFinding('invalid_slot', AuditSeverity.BLOCKING, f'{slot!r} is not allowed by the {pattern_key} pattern.', slot=slot))
            continue
        if not isinstance(raw_keys, Sequence) or isinstance(raw_keys, (str, bytes, bytearray)):
            findings.append(ProjectFinding('invalid_slot_payload', AuditSeverity.BLOCKING, f'{slot!r} placement data is not a capability list.', slot=slot))
            continue
        for raw_key in raw_keys:
            key = str(raw_key)
            placed += 1
            if key in seen:
                findings.append(ProjectFinding('duplicate_capability', AuditSeverity.BLOCKING, f'{key} is placed in both {seen[key]} and {slot}.', slot=slot, entry_key=key))
                continue
            seen[key] = slot
            entry = lookup.get(key)
            if entry is None:
                findings.append(ProjectFinding('missing_capability', AuditSeverity.BLOCKING, f'Placed capability {key!r} no longer exists in the canonical catalog.', slot=slot, entry_key=key))
                continue
            if not is_composable_entry(entry):
                findings.append(ProjectFinding('not_composable', AuditSeverity.BLOCKING, f'{entry.title} is discoverable but is not a supported generated-project capability.', slot=slot, entry_key=key))
                continue
            preferred = _slot_preference(entry)
            if preferred and slot not in preferred:
                findings.append(ProjectFinding('unusual_slot', AuditSeverity.WARNING, f'{entry.title} is usually more effective in {", ".join(preferred[:3])} than {slot}.', slot=slot, entry_key=key))

    explicit_required = tuple(slot for slot in required if placements.get(slot))
    for slot in required:
        if not placements.get(slot):
            findings.append(ProjectFinding('required_slot_fallback', AuditSeverity.WARNING, f'Required slot {slot!r} has no explicit capability; generation will use the canonical safe fallback.', slot=slot))

    columns = tuple(getattr(data_model, 'columns', ()) or ()) if data_model is not None else ()
    roles = {str(getattr(column, 'role', '')) for column in columns}
    if seen and any((_kind(lookup[key]) == 'analytic' or _registry(lookup[key]) == 'visualizations') for key in seen if key in lookup):
        if not columns:
            findings.append(ProjectFinding('no_development_data', AuditSeverity.WARNING, 'Analytical capabilities are placed but no development schema is available to validate semantic fit.'))
        elif 'measurement' not in roles:
            findings.append(ProjectFinding('no_measurement_role', AuditSeverity.WARNING, 'Analytical capabilities are placed but no column is mapped to the measurement semantic role.'))
    if pattern_key in {'data_explorer', 'crud', 'master_detail', 'search'} and not any(_registry(lookup[key]) == 'tables' for key in seen if key in lookup):
        findings.append(ProjectFinding('table_recommended', AuditSeverity.WARNING, f'{pattern_key.replace("_", " ").title()} normally benefits from an explicit canonical table capability.'))
    if pattern_key == 'monitoring':
        keys = {_registry_key(lookup[key]) for key in seen if key in lookup}
        if not keys & {'status_badge', 'alert'}:
            findings.append(ProjectFinding('health_signal_recommended', AuditSeverity.WARNING, 'Monitoring pages should lead with a status badge or alert so critical state is visible before charts.'))
    if pattern_key == 'crud' and not any(_registry_key(lookup[key]) in {'button', 'action_button'} for key in seen if key in lookup):
        findings.append(ProjectFinding('crud_action_recommended', AuditSeverity.WARNING, 'CRUD pages should expose an explicit governed action control.'))
    if placed > 12:
        findings.append(ProjectFinding('composition_density', AuditSeverity.WARNING, f'{placed} capabilities are placed. Prefer progressive disclosure rather than putting every capability on one page.'))
    if placed == 0:
        findings.append(ProjectFinding('empty_composition', AuditSeverity.WARNING, 'No reusable capabilities are explicitly placed; use Auto-compose or a Golden Starter to reduce manual setup.'))

    return ProjectAudit(tuple(findings), required, explicit_required, placed)


__all__ = ['AuditSeverity', 'ProjectAudit', 'ProjectFinding', 'audit_project']
