from __future__ import annotations

import ast
import io
import json
import zipfile


def test_project_history_signature_ignores_revision_and_diff_is_structural():
    from nicegui_base.workbench.project_history import diff_projects, project_signature
    before = {'name':'A','pattern_key':'dashboard','placements':{'primary':['x']},'data_rows':[{'a':1}],'revision':1}
    after = {'name':'A','pattern_key':'dashboard','placements':{'primary':['y']},'data_rows':[{'a':1},{'a':2}],'revision':99}
    assert project_signature(before) == project_signature({**before, 'revision': 77})
    diff = diff_projects(before, after)
    assert diff.changed
    assert diff.added == (('primary', 'y'),)
    assert diff.removed == (('primary', 'x'),)
    assert (diff.data_rows_before, diff.data_rows_after) == (1, 2)


def test_history_is_bounded_deduplicated_and_presets_are_sanitized():
    from nicegui_base.workbench.project_history import normalize_history, normalize_presets, preset_name, push_history
    snapshot = {'name':'A','goal':'monitor','pattern_key':'dashboard','placements':{'primary':['x']}}
    history = push_history([], snapshot, label='first')
    history = push_history(history, snapshot, label='duplicate')
    assert len(history) == 1
    assert normalize_history([{'snapshot': None}, *history]) == history
    assert preset_name('  Chamber   drift  ') == 'Chamber drift'
    normalized = normalize_presets({'Good': snapshot, '': snapshot})
    assert set(normalized) == {'Good'}
    assert normalized['Good']['placements'] == snapshot['placements']


def test_browser_contract_v2_keeps_browser_proof_truthful():
    from nicegui_base.workbench.browser_contract import BASE_CHECKS, build_browser_acceptance_contract, validate_browser_acceptance_contract
    contract = build_browser_acceptance_contract({'pattern_key':'dashboard','placements':{'primary':['x']}})
    assert contract['schema_version'] == 2
    assert contract['status'] == 'PENDING_BROWSER_EXECUTION'
    assert set(BASE_CHECKS) <= set(contract['automated_checks'])
    assert contract['runner']['path'] == 'tools/browser_acceptance.py'
    assert contract['manual_checks']
    assert validate_browser_acceptance_contract(contract) == ()


def test_generated_browser_runner_is_valid_python_and_backend_absence_is_not_exception():
    from nicegui_base.workbench.browser_acceptance_runner import generated_browser_runner_source
    source = generated_browser_runner_source()
    ast.parse(source)
    assert 'run_browser_acceptance_file' in source
    assert 'SKIPPED_BROWSER_BACKEND_UNAVAILABLE' in source


def test_generated_zip_includes_browser_runner_for_schema_v2():
    from nicegui_base.workbench.builder import BuilderModel
    model = BuilderModel()
    model.apply_golden_starter('record-manager')
    payload, report = model.generate()
    assert report.ok, report.findings
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert 'tools/browser_acceptance.py' in names
        contract = json.loads(archive.read('.nicegui_base/browser_acceptance.json'))
        assert contract['schema_version'] == 2
        ast.parse(archive.read('tools/browser_acceptance.py').decode('utf-8'))


def test_release_pipeline_can_use_injected_live_smoke_without_network_or_browser():
    from nicegui_base.workbench.release_pipeline import build_runtime_proven_starter
    from nicegui_base.workbench.runtime_proof import LiveSmokeReport, RouteProof
    def fake_live(payload: bytes, *, timeout_seconds: float):
        assert payload and timeout_seconds > 0
        return LiveSmokeReport(True, (), (RouteProof('/', 200, 1, True, ''),), 1, 0)
    result = build_runtime_proven_starter('record-manager', live_smoke=fake_live)
    assert result.ok
    assert result.audit.status in {'READY', 'READY WITH WARNINGS'}
    assert result.source_ok


def test_builder_exposes_project_memory_and_one_click_release():
    from pathlib import Path
    source = Path(__file__).resolve().parents[1] / 'nicegui_base' / 'workbench' / 'builder.py'
    text = source.read_text(encoding='utf-8')
    assert 'Project presets & history' in text
    assert 'Generate project' in text
    assert 'Download starter ZIP (local startup checked)' in text
    assert 'restore_project_revision' in text
    assert 'save_project_preset' in text
