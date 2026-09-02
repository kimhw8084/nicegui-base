from __future__ import annotations

from pathlib import Path

from nicegui_base.workbench.builder import BuilderModel
from nicegui_base.workbench.catalog import all_entries
from nicegui_base.workbench.coverage_matrix import TOTAL_CHECKS, readiness_row
from nicegui_base.workbench.data_dock import DataDockModel
from nicegui_base.workbench.interaction_inspector import inspect_entry
from nicegui_base.workbench.models import WorkbenchKind
from nicegui_base.workbench.runtime_proof import run_generated_live_smoke


def test_data_dock_rectangular_paste_targets_selected_cell_and_extends_rows() -> None:
    model = DataDockModel(({'id':'R1','a':1,'b':2}, {'id':'R2','a':3,'b':4}))
    model.rectangular_paste(1, 'b', '40\n50')
    assert model.rows[1]['b'] == 40
    assert len(model.rows) == 3
    assert model.rows[2]['b'] == 50
    assert model.rows[2]['a'] is None


def test_interaction_inspector_binds_real_public_component_signature() -> None:
    entries = all_entries()
    entry = next(item for item in entries if item.kind is WorkbenchKind.COMPONENT and (item.metadata.get('component_key') or item.metadata.get('registry_key')) == 'button')
    report = inspect_entry(entry)
    assert report.public_symbol == 'Button'
    assert report.signature
    assert any(item.key == 'constructor' and item.status == 'PROVEN' for item in report.evidence)
    assert any(name == 'on_click' for name in report.callbacks)


def test_pattern_interaction_inspector_has_all_device_contracts() -> None:
    entry = next(item for item in all_entries() if item.kind is WorkbenchKind.PATTERN and item.metadata.get('pattern_key') == 'analysis_workspace')
    report = inspect_entry(entry)
    assert len(report.responsive_contract) == 3
    assert report.responsive_contract[0].startswith('Desktop')
    assert report.responsive_contract[1].startswith('Tablet')
    assert report.responsive_contract[2].startswith('Phone')


def test_readiness_matrix_is_stricter_than_iteration_2_2() -> None:
    entry = next(item for item in all_entries() if item.kind is WorkbenchKind.PATTERN)
    row = readiness_row(entry)
    assert TOTAL_CHECKS == 10
    assert 0 <= row.score <= TOTAL_CHECKS
    assert row.inspectable
    assert row.state_proof
    assert row.responsive_proof


def test_live_smoke_refuses_bad_zip_before_starting_process() -> None:
    report = run_generated_live_smoke(b'not a zip')
    assert not report.ok
    assert report.routes == ()
    assert any(item.startswith('static:bad_zip') for item in report.findings)


def test_builder_requires_live_runtime_proof_before_runtime_proven_download() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / 'nicegui_base' / 'workbench' / 'builder.py').read_text(encoding='utf-8')
    assert 'run_generated_live_smoke' in source
    assert 'Download runtime-proven starter ZIP' in source
    assert "live is not None and live.ok" in source


def test_capability_studio_wires_interaction_inspector_and_selected_cell_clipboard() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / 'nicegui_base' / 'workbench' / 'capability_studio.py').read_text(encoding='utf-8')
    assert "'inspect'" in source
    assert 'render_interaction_inspector(entry, session)' in source
    assert "table.element.on('cellClicked', select_cell)" in source
    assert 'navigator.clipboard.readText()' in source
    assert "model.rectangular_paste(selected['row'], selected['column'], text)" in source


def test_layout_studio_renders_simultaneous_device_proof() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / 'nicegui_base' / 'workbench' / 'layout_studio.py').read_text(encoding='utf-8')
    assert "render_device(definition, 'desktop'" in source
    assert "render_device(definition, 'tablet'" in source
    assert "render_device(definition, 'phone'" in source
    assert '_pattern_checks(definition)' in source


def test_builder_generation_still_passes_source_smoke() -> None:
    model = BuilderModel(app_name='Iteration 23 Smoke', goal='monitor process health')
    model.select_pattern('dashboard')
    payload, report = model.generate()
    assert payload
    assert report.ok, report.findings
