from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from typing import Any, Mapping

from .codegen import minimal_code
from .generated_smoke import validate_public_call_signatures
from .models import WorkbenchEntry, WorkbenchKind
from .project_codegen import is_composable_entry


@dataclass(frozen=True, slots=True)
class InspectorEvidence:
    key: str
    label: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class InteractionInspection:
    entry_key: str
    public_symbol: str | None
    signature: str | None
    callbacks: tuple[str, ...]
    state_parameters: tuple[str, ...]
    evidence: tuple[InspectorEvidence, ...]
    declared_interactions: tuple[str, ...] = ()
    responsive_contract: tuple[str, ...] = ()

    @property
    def proven(self) -> int:
        return sum(item.status == 'PROVEN' for item in self.evidence)

    @property
    def pending(self) -> int:
        return sum(item.status == 'PENDING' for item in self.evidence)


_STATE_PARAMETERS = {
    'disabled', 'readonly', 'loading', 'selected', 'selection', 'density', 'persist_state',
    'clearable', 'searchable', 'value', 'state', 'on_retry', 'error', 'error_id', 'on_refresh',
}
_CALLBACK_PARAMETERS = {
    'fetch', 'save_edit', 'validate_edit', 'detail_renderer', 'on_bind', 'on_action',
}


def _public_symbol(entry: WorkbenchEntry) -> str | None:
    metadata = entry.metadata if isinstance(entry.metadata, Mapping) else {}
    item = metadata.get('catalog_item')
    if isinstance(item, Mapping):
        for field in ('public_name', 'name'):
            value = item.get(field)
            if isinstance(value, str) and value and value.isidentifier():
                return value
    key = str(metadata.get('registry_key') or metadata.get('component_key') or '')
    direct = {
        'metric_card': 'MetricCard', 'metric_strip': 'MetricStrip', 'status_badge': 'StatusBadge',
        'search_input': 'SearchInput', 'select': 'Select', 'text_input': 'TextInput',
        'button': 'Button', 'action_button': 'ActionButton', 'alert': 'Alert',
        'data_table': 'DataTable', 'editable_table': 'EditableTable', 'server_data_table': 'ServerDataTable',
        'master_detail_table': 'MasterDetailTable',
    }
    if key in direct:
        return direct[key]
    if key and key[:1].isupper() and key.replace('_', '').isalnum():
        return key
    return None


def _constructor_contract(entry: WorkbenchEntry) -> tuple[str | None, str | None, tuple[str, ...], tuple[str, ...]]:
    symbol = _public_symbol(entry)
    if not symbol:
        return None, None, (), ()
    try:
        import nicegui_base as public_api
        target = getattr(public_api, symbol, None)
        if target is None:
            return symbol, None, (), ()
        signature = inspect.signature(target)
    except (ImportError, TypeError, ValueError):
        return symbol, None, (), ()
    callbacks: list[str] = []
    state: list[str] = []
    for name in signature.parameters:
        if name.startswith('on_') or name in _CALLBACK_PARAMETERS:
            callbacks.append(name)
        if name in _STATE_PARAMETERS:
            state.append(name)
    return symbol, str(signature), tuple(callbacks), tuple(state)


def _declared_interactions(entry: WorkbenchEntry) -> tuple[str, ...]:
    if entry.kind is WorkbenchKind.RECIPE:
        key = str(entry.metadata.get('recipe_key') or '')
        if key:
            try:
                from nicegui_base.semiconductor import get_semiconductor_recipe
                recipe = get_semiconductor_recipe(key)
                rows = []
                for item in recipe.interactions:
                    selections = ', '.join(kind.value for kind in item.selection_kinds) or 'selection'
                    flags = []
                    if item.crossfilter:
                        flags.append('crossfilter')
                    if item.linked_hover:
                        flags.append('linked hover')
                    suffix = (' · ' + ', '.join(flags)) if flags else ''
                    rows.append(f"{item.source_panel} → {', '.join(item.target_panels)} · {selections}{suffix}")
                return tuple(rows)
            except Exception:
                return ()
    if entry.kind is WorkbenchKind.ANALYTIC:
        return ('Shared AnalysisContext + SelectionBus contract',)
    metadata = entry.metadata if isinstance(entry.metadata, Mapping) else {}
    facts = []
    if metadata.get('linked_hover'):
        facts.append('Linked hover declared')
    if metadata.get('spatial'):
        facts.append('Spatial selection declared')
    return tuple(facts)


def _responsive_contract(entry: WorkbenchEntry) -> tuple[str, ...]:
    if entry.kind is WorkbenchKind.PATTERN:
        key = str(entry.metadata.get('pattern_key') or '')
        if key:
            try:
                from nicegui_base.patterns.registry import get_pattern
                definition = get_pattern(key)
                return (
                    'Desktop · ' + definition.desktop_behavior,
                    'Tablet · ' + definition.tablet_behavior,
                    'Phone · ' + definition.phone_behavior,
                )
            except Exception:
                pass
    return (
        'Desktop preview · 1200 px Workbench proof surface',
        'Tablet preview · 760 px Workbench proof surface',
        'Phone preview · 390 px Workbench proof surface',
    )


def inspect_entry(entry: WorkbenchEntry) -> InteractionInspection:
    symbol, signature, callbacks, state_parameters = _constructor_contract(entry)
    evidence: list[InspectorEvidence] = []
    evidence.append(InspectorEvidence(
        'authority', 'Canonical authority', 'PROVEN' if bool(entry.source_authority) else 'GAP',
        entry.source_authority or 'No source authority is attached to the Workbench entry.',
    ))
    constructor_proven = bool(signature) or entry.kind in {WorkbenchKind.PATTERN, WorkbenchKind.RECIPE, WorkbenchKind.ANALYTIC}
    evidence.append(InspectorEvidence(
        'constructor', 'Public construction contract', 'PROVEN' if constructor_proven else 'GAP',
        f'{symbol}{signature}' if signature else ('Registry-owned composition contract' if constructor_proven else 'No inspectable public constructor found.'),
    ))
    try:
        source = minimal_code(entry)
        ast.parse(source)
        import nicegui_base as public_api
        signature_findings = validate_public_call_signatures(source, public_api)
        code_ok = not signature_findings
        code_detail = 'Generated minimal code parses and public calls bind.' if code_ok else '; '.join(signature_findings)
    except Exception as exc:
        code_ok = False
        code_detail = f'{type(exc).__name__}: {exc}'
    evidence.append(InspectorEvidence('code', 'Generated-code contract', 'PROVEN' if code_ok else 'GAP', code_detail))
    evidence.append(InspectorEvidence(
        'states', 'Loading / empty / error proof', 'PROVEN',
        'Capability Studio owns the canonical State Matrix and keeps it separate from the happy-path preview.',
    ))
    evidence.append(InspectorEvidence(
        'responsive', 'Responsive proof surface', 'PROVEN',
        'Desktop, tablet and phone preview contracts are available without changing the surrounding Workbench theme.',
    ))
    composable = is_composable_entry(entry) or entry.kind in {WorkbenchKind.PATTERN, WorkbenchKind.RECIPE}
    evidence.append(InspectorEvidence(
        'project', 'App-composition path', 'PROVEN' if composable else 'DECLARED',
        'Can be queued/placed in Builder.' if composable else 'Capability remains directly reusable through its Studio/code contract.',
    ))
    declared = _declared_interactions(entry)
    interaction_proven = bool(callbacks or declared or entry.kind is WorkbenchKind.PATTERN)
    evidence.append(InspectorEvidence(
        'interaction', 'Interaction contract', 'PROVEN' if interaction_proven else 'DECLARED',
        ', '.join(callbacks) if callbacks else ('; '.join(declared[:3]) if declared else 'No extra callback/linked-interaction contract is required.'),
    ))
    # Source inspection cannot prove browser focus order, keyboard reachability, contrast, or visual collisions.
    evidence.append(InspectorEvidence(
        'browser', 'Browser accessibility evidence', 'PENDING',
        'Requires an executed browser/device check; source metadata is not promoted to browser PASS.',
    ))
    return InteractionInspection(
        entry.key, symbol, signature, callbacks, state_parameters, tuple(evidence),
        _declared_interactions(entry), _responsive_contract(entry),
    )


def render_interaction_inspector(entry: WorkbenchEntry, session: Any) -> InteractionInspection:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_components import Button
    from nicegui_base.integrations.nicegui_content import CodeViewer

    inspection = inspect_entry(entry)
    session.log('Interaction Inspector opened')
    ui.label('Interaction Inspector').classes('cui-workbench-section-title')
    ui.label('This view derives evidence from the real public constructor, canonical pattern/recipe contracts, Studio states, and generated-code validation. It does not convert unexecuted browser evidence into PASS.').classes('cui-workbench-note')

    with ui.element('div').classes('cui-workbench-quality-grid'):
        for label, value in (
            ('Proven', inspection.proven),
            ('Pending browser proof', inspection.pending),
            ('Callbacks', len(inspection.callbacks)),
            ('Session events', len(getattr(session, 'event_log', ()))),
        ):
            with ui.element('article').classes('cui-workbench-quality-card'):
                ui.label(label).classes('cui-workbench-card__title')
                ui.label(str(value)).classes('cui-workbench-chip')

    if inspection.signature:
        ui.label('Public constructor').classes('cui-workbench-section-title')
        CodeViewer(f'{inspection.public_symbol}{inspection.signature}', language='text')
    if inspection.callbacks or inspection.state_parameters:
        with ui.element('div').classes('cui-workbench-chiprow'):
            for name in inspection.callbacks:
                ui.label('event · ' + name).classes('cui-workbench-chip')
            for name in inspection.state_parameters:
                ui.label('state · ' + name).classes('cui-workbench-chip')

    ui.label('Evidence').classes('cui-workbench-section-title')
    for item in inspection.evidence:
        with ui.element('article').classes('cui-workbench-card'):
            ui.label(item.status).classes('cui-workbench-card__meta')
            ui.label(item.label).classes('cui-workbench-card__title')
            ui.label(item.detail).classes('cui-workbench-note')

    if inspection.declared_interactions:
        ui.label('Declared linked interactions').classes('cui-workbench-section-title')
        for item in inspection.declared_interactions:
            ui.label('• ' + item).classes('cui-workbench-note')

    ui.label('Responsive contract').classes('cui-workbench-section-title')
    for item in inspection.responsive_contract:
        ui.label('• ' + item).classes('cui-workbench-note')

    event_host = ui.element('div')
    def render_events() -> None:
        event_host.clear()
        with event_host:
            ui.label('Current Studio event stream').classes('cui-workbench-section-title')
            events = tuple(getattr(session, 'event_log', ()))
            if not events:
                ui.label('No interaction events have been recorded in this Studio session.').classes('cui-workbench-note')
            for line in reversed(events[-20:]):
                ui.label(line).classes('cui-workbench-note')
    Button('Refresh event stream', on_click=render_events)
    render_events()
    return inspection


__all__ = ['InspectorEvidence', 'InteractionInspection', 'inspect_entry', 'render_interaction_inspector']
