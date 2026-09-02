from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable

from .codegen import minimal_code
from .interaction_inspector import inspect_entry
from .models import WorkbenchEntry, WorkbenchKind
from .project_codegen import is_composable_entry

TOTAL_CHECKS = 10


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


def render_developer_readiness(entries: Iterable[WorkbenchEntry]) -> None:
    from nicegui import ui
    rows = readiness_rows(entries)
    complete = sum(row.complete for row in rows)
    with ui.element('section').classes('cui-workbench-section'):
        ui.label('Developer readiness matrix').classes('cui-workbench-section-title')
        ui.label('Coverage means immediately reusable by an engineer, not merely present in Python. Source evidence and executed runtime/browser evidence stay separate.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-workbench-quality-grid'):
            for label, value in (
                ('Fully source-ready', f'{complete} / {len(rows)}'),
                ('Discoverable', sum(row.discoverable for row in rows)),
                ('Live/sample preview', sum(row.preview and row.sample_data for row in rows)),
                ('Generated-code contract', sum(row.code for row in rows)),
                ('Interaction inspectable', sum(row.inspectable for row in rows)),
                ('Project composable', sum(row.project_composable for row in rows)),
            ):
                with ui.element('article').classes('cui-workbench-quality-card'):
                    ui.label(label).classes('cui-workbench-card__title')
                    ui.label(str(value)).classes('cui-workbench-chip')
        incomplete = [row for row in rows if not row.complete]
        if incomplete:
            ui.label(f'{len(incomplete)} entries still have at least one source/developer-readiness gap. Close the existing capability contract before adding duplicate APIs.').classes('cui-workbench-note')

        ui.label('Proof layers').classes('cui-workbench-section-title')
        with ui.element('div').classes('cui-workbench-quality-grid'):
            layers = (
                ('Source contract', 'AUTOMATED', 'Discoverability, preview/sample, guidance, code, inspector, state, responsive and public-constructor evidence.'),
                ('Golden starter assembly', 'AUTOMATED', 'Zero-decision starters resolve against canonical pattern/capability registries and project audit blocks invalid or duplicate composition.'),
                ('Generated ZIP', 'AUTOMATED', 'Builder blocks generation when project shape, AST, imports, public calls or composition manifest fail.'),
                ('Live startup', 'EXECUTED ON DEMAND', 'Builder launches the generated app in a fresh subprocess and HTTP-probes the rendered root before the runtime-proven download is enabled.'),
                ('Workbench routes', 'RELEASE GATE', 'Iteration patch validation launches the real Workbench and requests Home, Build, Layouts and Quality.'),
                ('Browser keyboard/focus', 'PENDING UNTIL EXECUTED', 'Requires an actual browser/device run; source inspection never promotes it to PASS.'),
                ('Human visual review', 'PENDING UNTIL REVIEWED', 'Collision, information density and visual hierarchy remain explicit human evidence.'),
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


__all__ = ['TOTAL_CHECKS','ReadinessRow','readiness_row','readiness_rows','render_developer_readiness']
