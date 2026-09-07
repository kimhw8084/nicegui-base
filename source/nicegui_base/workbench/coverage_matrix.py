from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable

from .codegen import minimal_code
from .interaction_inspector import inspect_entry
from .models import WorkbenchEntry, WorkbenchKind
from .project_codegen import is_composable_entry

TOTAL_CHECKS = 10
GOLDEN_READINESS_KINDS = frozenset({WorkbenchKind.ANALYTIC, WorkbenchKind.PATTERN, WorkbenchKind.RECIPE})


@dataclass(frozen=True, slots=True)
class ReadinessRow:
    entry_key: str
    discoverable: bool
    preview: bool
    sample_data: bool
    guidance: bool
    code: bool
    project_composable: bool
    inspectable: bool
    state_proof: bool
    responsive_proof: bool
    public_contract: bool

    @property
    def score(self) -> int:
        return sum((
            self.discoverable, self.preview, self.sample_data, self.guidance, self.code,
            self.project_composable, self.inspectable, self.state_proof,
            self.responsive_proof, self.public_contract,
        ))

    @property
    def complete(self) -> bool:
        return self.score == TOTAL_CHECKS


def readiness_row(entry: WorkbenchEntry) -> ReadinessRow:
    try:
        ast.parse(minimal_code(entry))
        code = True
    except Exception:
        code = False
    guidance = bool(entry.use_when or entry.avoid_when or entry.description)
    preview = bool(entry.live_preview or entry.kind is WorkbenchKind.PATTERN)
    sample = bool(entry.sample_data or entry.kind is WorkbenchKind.PATTERN)
    inspection = inspect_entry(entry)
    public_contract = any(item.key == 'constructor' and item.status == 'PROVEN' for item in inspection.evidence)
    return ReadinessRow(
        entry.key,
        bool(entry.route),
        preview,
        sample,
        guidance,
        code,
        is_composable_entry(entry) or entry.kind in {WorkbenchKind.PATTERN, WorkbenchKind.RECIPE},
        bool(inspection.evidence),
        any(item.key == 'states' and item.status == 'PROVEN' for item in inspection.evidence),
        bool(inspection.responsive_contract),
        public_contract,
    )


def readiness_rows(entries: Iterable[WorkbenchEntry]) -> tuple[ReadinessRow, ...]:
    return tuple(readiness_row(entry) for entry in entries)


def golden_readiness_entries(entries: Iterable[WorkbenchEntry]) -> tuple[WorkbenchEntry, ...]:
    """Return the promoted runnable reference denominator.

    The 34 reusable component contracts have their own complete component-detail
    evidence gate. They are framework primitives rather than sample-backed domain
    applications, so including their optional state-proof score in the Golden
    sample denominator would report a misleading partial result.
    """
    return tuple(entry for entry in entries if entry.kind in GOLDEN_READINESS_KINDS)


def render_developer_readiness(entries: Iterable[WorkbenchEntry]) -> None:
    from nicegui import ui
    entries = tuple(entries)
    rows = readiness_rows(entries)
    promoted_entries = golden_readiness_entries(entries)
    promoted_keys = {entry.key for entry in promoted_entries}
    reference_rows = tuple(row for entry, row in zip(entries, rows, strict=True) if entry.key in promoted_keys)
    complete = sum(row.complete for row in reference_rows)
    with ui.element('section').classes('cui-workbench-section'):
        ui.label('Golden reference readiness').classes('cui-workbench-section-title')
        ui.label(f'Promoted sample-backed surfaces are evaluated as live, reusable authorities ({len(reference_rows)} entries). The 34 framework component contracts are excluded from this application/sample denominator and are reviewed through their component-detail evidence gate.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-workbench-quality-grid'):
            for label, value in (
                ('Golden promoted contracts', f'{complete} / {len(reference_rows)}'),
                ('Golden discoverability', f'{sum(row.discoverable for row in reference_rows)} / {len(reference_rows)}'),
                ('Golden live examples', f'{sum(row.preview for row in reference_rows)} / {len(reference_rows)}'),
                ('Golden sample-backed', f'{sum(row.sample_data for row in reference_rows)} / {len(reference_rows)}'),
                ('Golden generated code', f'{sum(row.code for row in reference_rows)} / {len(reference_rows)}'),
                ('Golden responsive', f'{sum(row.responsive_proof for row in reference_rows)} / {len(reference_rows)}'),
            ):
                with ui.element('article').classes('cui-workbench-quality-card'):
                    ui.label(label).classes('cui-workbench-card__title')
                    ui.label(str(value)).classes('cui-workbench-chip')
        ui.label('Proof layers').classes('cui-workbench-section-title')
        with ui.element('div').classes('cui-workbench-quality-grid'):
            layers = (
                ('Source contract', 'AUTOMATED', 'Discoverability, preview/sample, guidance, code, inspector, state, responsive and public-constructor evidence.'),
                ('Golden starter assembly', 'AUTOMATED', 'Deterministic starters resolve against canonical pattern, recipe, and component registries.'),
                ('Generated app', 'AUTOMATED', 'Project audit checks shape, AST, imports, public calls, and composition manifest before startup.'),
                ('Live startup', 'EXECUTED ON DEMAND', 'A generated app launches in a fresh subprocess and is probed before distribution.'),
                ('Reference Explorer routes', 'RELEASE GATE', 'The live reference routes are requested from the installed candidate.'),
                ('Browser keyboard/focus', 'PENDING UNTIL EXECUTED', 'Requires an actual browser/device run; source inspection never promotes it to PASS.'),
                ('Visual review gate', 'RECORDED WITH EVIDENCE', 'Screenshots and geometry evidence record information density, hierarchy, and interaction review.'),
            )
            for label, status, detail in layers:
                with ui.element('article').classes('cui-workbench-quality-card'):
                    ui.label(status).classes('cui-workbench-card__meta')
                    ui.label(label).classes('cui-workbench-card__title')
                    ui.label(detail).classes('cui-workbench-note')

        matrix_host = ui.element('div')
        from nicegui_base.integrations.nicegui_components import Button
        def load_matrix() -> None:
            from nicegui_base import DataTable, TableColumn
            matrix_host.clear()
            matrix_rows = [
                {
                    'entry_key': row.entry_key, 'score': f'{row.score}/{TOTAL_CHECKS}',
                    'discoverable': 'Yes' if row.discoverable else 'Gap',
                    'preview': 'Yes' if row.preview else 'Gap',
                    'sample_data': 'Yes' if row.sample_data else 'Gap',
                    'guidance': 'Yes' if row.guidance else 'Gap',
                    'code': 'Yes' if row.code else 'Gap',
                    'project': 'Yes' if row.project_composable else 'Gap',
                    'inspect': 'Yes' if row.inspectable else 'Gap',
                    'states': 'Yes' if row.state_proof else 'Gap',
                    'responsive': 'Yes' if row.responsive_proof else 'Gap',
                    'public_contract': 'Yes' if row.public_contract else 'Gap',
                } for row in rows
            ]
            columns = (
                TableColumn('entry_key','Capability'), TableColumn('score','Score'),
                TableColumn('discoverable','Discoverable'), TableColumn('preview','Preview'),
                TableColumn('sample_data','Sample'), TableColumn('guidance','Guidance'),
                TableColumn('code','Code'), TableColumn('project','Project'),
                TableColumn('inspect','Inspector'), TableColumn('states','States'),
                TableColumn('responsive','Responsive'), TableColumn('public_contract','Public contract'),
            )
            with matrix_host:
                DataTable(matrix_rows, columns, row_key='entry_key', title='Developer readiness')
        Button('Load full readiness matrix', on_click=load_matrix)


__all__ = ['GOLDEN_READINESS_KINDS','TOTAL_CHECKS','ReadinessRow','golden_readiness_entries','readiness_row','readiness_rows','render_developer_readiness']
