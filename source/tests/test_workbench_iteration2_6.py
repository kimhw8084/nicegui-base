from __future__ import annotations

import io
import json
import zipfile

import pytest


def _sample_state():
    return {
        'version': 3,
        'project': {
            'name': 'Portable App', 'goal': 'inspect process drift', 'problem_type': 'engineering analysis',
            'pattern_key': 'dashboard', 'placements': {'metrics': ['framework:content:metric_card']},
            'queued_entry_keys': [], 'data_rows': [{'tool': 'ETCH-01', 'value': 10.2}],
            'theme': 'dark', 'density': 'compact', 'revision': 3,
        },
        'favorites': ['analytics:spc_i_mr'], 'recents': [], 'history': [], 'presets': {}, 'proof_evidence': {},
    }


def test_portable_project_roundtrip_is_deterministic():
    from nicegui_base.workbench.portable_project import build_portable_project_bundle, extract_portable_project_bundle
    from nicegui_base.version import FRAMEWORK_VERSION
    state = _sample_state()
    first = build_portable_project_bundle(state, framework_version=FRAMEWORK_VERSION)
    second = build_portable_project_bundle(state, framework_version=FRAMEWORK_VERSION)
    assert first == second
    restored, proof, inspection = extract_portable_project_bundle(first, expected_framework_version=FRAMEWORK_VERSION)
    assert inspection.ok
    assert restored['project']['name'] == 'Portable App'
    assert proof == {}


def test_portable_project_rejects_sensitive_keys_and_tamper():
    from nicegui_base.workbench.portable_project import build_portable_project_bundle, inspect_portable_project_bundle
    from nicegui_base.version import FRAMEWORK_VERSION
    state = _sample_state()
    state['project']['data_rows'] = [{'password': 'should-never-export'}]
    with pytest.raises(ValueError, match='sensitive-key'):
        build_portable_project_bundle(state, framework_version=FRAMEWORK_VERSION)

    clean = build_portable_project_bundle(_sample_state(), framework_version=FRAMEWORK_VERSION)
    src = zipfile.ZipFile(io.BytesIO(clean))
    out = io.BytesIO()
    with src, zipfile.ZipFile(out, 'w') as archive:
        for name in src.namelist():
            data = src.read(name)
            if name == 'workbench_state.json':
                data += b' '
            archive.writestr(name, data)
    report = inspect_portable_project_bundle(out.getvalue(), expected_framework_version=FRAMEWORK_VERSION)
    assert not report.ok
    assert any('sha256:workbench_state.json' in item for item in report.findings)


def test_handoff_evidence_is_attached_without_duplicate_paths():
    from nicegui_base.workbench.handoff_readiness import EnvironmentReadiness, HandoffReadinessReport, attach_handoff_evidence
    base = io.BytesIO()
    with zipfile.ZipFile(base, 'w') as archive:
        archive.writestr('app.py', 'pass\n')
    env = EnvironmentReadiness(True, '3.13.0', '3.15.0', '3.0.0a8', True, ())
    report = HandoffReadinessReport('READY_RUNTIME_PROVEN_BROWSER_PENDING', 'abc', True, True, 'PENDING_BROWSER_EXECUTION', True, env, ())
    payload = attach_handoff_evidence(base.getvalue(), report)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist()))
        stored = json.loads(archive.read('.nicegui_base/handoff_readiness.json'))
        assert stored['status'] == 'READY_RUNTIME_PROVEN_BROWSER_PENDING'


def test_state_v2_migrates_to_v3_and_proof_is_bounded():
    from nicegui_base.workbench.project_state import STATE_VERSION, normalize_state
    state = normalize_state({'version': 2, 'project': {'name': 'Old State'}})
    assert STATE_VERSION >= 3
    assert state['version'] == STATE_VERSION
    assert state['proof_evidence'] == {}


def test_release_pipeline_preserves_starter_api():
    from nicegui_base.workbench.release_pipeline import build_runtime_proven_starter, finalize_generated_handoff, prove_project
    assert callable(build_runtime_proven_starter)
    assert callable(finalize_generated_handoff)
    assert callable(prove_project)


def test_project_state_source_invalidates_stale_proof_and_builder_exposes_portability():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / 'nicegui_base' / 'workbench'
    state = (root / 'project_state.py').read_text(encoding='utf-8')
    builder = (root / 'builder.py').read_text(encoding='utf-8')
    from nicegui_base.workbench.project_state import STATE_VERSION
    assert STATE_VERSION >= 3
    assert state.count("state['proof_evidence'] = {}") >= 5
    assert 'export_portable_project_bundle' in state
    assert 'import_portable_project_bundle' in state
    assert 'Portable Golden Project' in builder
    assert 'Download .ngbproj' in builder
    assert 'finalize_generated_handoff' in builder
