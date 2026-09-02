from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable

from .codegen import minimal_code
from .models import WorkbenchEntry, WorkbenchKind
from .project_codegen import is_composable_entry


@dataclass(frozen=True, slots=True)
class ReadinessRow:
    entry_key: str
    discoverable: bool
    preview: bool
    sample_data: bool
    guidance: bool
    code: bool
    project_composable: bool

    @property
    def score(self) -> int:
        return sum((self.discoverable, self.preview, self.sample_data, self.guidance, self.code, self.project_composable))


def readiness_row(entry: WorkbenchEntry) -> ReadinessRow:
    try:
        ast.parse(minimal_code(entry))
        code = True
    except Exception:
        code = False
    guidance = bool(entry.use_when or entry.avoid_when or entry.description)
    preview = bool(entry.live_preview or entry.kind is WorkbenchKind.PATTERN)
    sample = bool(entry.sample_data or entry.kind is WorkbenchKind.PATTERN)
    return ReadinessRow(
        entry.key,
        bool(entry.route),
        preview,
        sample,
        guidance,
        code,
        is_composable_entry(entry) or entry.kind in {WorkbenchKind.PATTERN, WorkbenchKind.RECIPE},
    )


def readiness_rows(entries: Iterable[WorkbenchEntry]) -> tuple[ReadinessRow, ...]:
    return tuple(readiness_row(entry) for entry in entries)


def render_developer_readiness(entries: Iterable[WorkbenchEntry]) -> None:
    from nicegui import ui
    rows = readiness_rows(entries)
    complete = sum(row.score == 6 for row in rows)
    with ui.element('section').classes('cui-workbench-section'):
        ui.label('Developer readiness matrix').classes('cui-workbench-section-title')
        ui.label('Coverage means usable by an engineer, not merely present in Python. These six checks are intentionally stricter than registry existence.').classes('cui-workbench-note')
        with ui.element('div').classes('cui-workbench-quality-grid'):
            for label, value in (
                ('Fully ready', f'{complete} / {len(rows)}'),
                ('Discoverable', sum(row.discoverable for row in rows)),
                ('Live/sample preview', sum(row.preview and row.sample_data for row in rows)),
                ('Code contract', sum(row.code for row in rows)),
                ('Project composable', sum(row.project_composable for row in rows)),
            ):
                with ui.element('article').classes('cui-workbench-quality-card'):
                    ui.label(label).classes('cui-workbench-card__title')
                    ui.label(str(value)).classes('cui-workbench-chip')
        incomplete = [row for row in rows if row.score < 6]
        if incomplete:
            ui.label(f'{len(incomplete)} entries still have at least one developer-readiness gap; use Catalog/Studio to close them rather than adding duplicate APIs.').classes('cui-workbench-note')
        matrix_host = ui.element('div')
        from nicegui_base.integrations.nicegui_components import Button
        def load_matrix() -> None:
            from nicegui_base import DataTable, TableColumn
            matrix_host.clear()
            matrix_rows = [
                {
                    'entry_key': row.entry_key, 'score': f'{row.score}/6',
                    'discoverable': 'Yes' if row.discoverable else 'Gap',
                    'preview': 'Yes' if row.preview else 'Gap',
                    'sample_data': 'Yes' if row.sample_data else 'Gap',
                    'guidance': 'Yes' if row.guidance else 'Gap',
                    'code': 'Yes' if row.code else 'Gap',
                    'project': 'Yes' if row.project_composable else 'Gap',
                } for row in rows
            ]
            columns = (
                TableColumn('entry_key','Capability'), TableColumn('score','Score'),
                TableColumn('discoverable','Discoverable'), TableColumn('preview','Preview'),
                TableColumn('sample_data','Sample'), TableColumn('guidance','Guidance'),
                TableColumn('code','Code'), TableColumn('project','Project'),
            )
            with matrix_host:
                DataTable(matrix_rows, columns, row_key='entry_key', title='Developer readiness')
        Button('Load full readiness matrix', on_click=load_matrix)


__all__ = ['ReadinessRow','readiness_row','readiness_rows','render_developer_readiness']
