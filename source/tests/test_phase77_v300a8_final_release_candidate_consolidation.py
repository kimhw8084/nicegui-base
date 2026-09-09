from __future__ import annotations

import hashlib
import base64
import json
import os
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from nicegui_base.governance.final_candidate import (
    AUTHORITY_CHAIN,
    audit_final_release_candidate,
    build_stable_qualification_handoff,
)
from nicegui_base.governance.release_artifacts import (
    build_deterministic_zip,
    verify_release_archive,
    verify_sha256_manifest,
    verify_wheel,
    verify_wheel_source_representation,
    write_sha256_manifest,
)
from nicegui_base.governance.release_identity import load_release_identity

ROOT = Path(__file__).resolve().parents[1]


def test_wave77_release_identity_is_single_current_wave_phase_authority():
    identity = load_release_identity(ROOT)
    assert identity.current_wave == 77
    assert identity.current_phase == 77
    assert identity.framework_version == '3.0.0a8'
    assert identity.nicegui_version == '3.15.0'


def test_wave77_source_certification_phase_floor_is_release_authority_driven():
    source = (ROOT / 'nicegui_base/governance/source_evidence.py').read_text(encoding='utf-8')
    assert 'load_release_identity(root).current_phase' in source
    assert "authority_path.is_file()" in source
    assert "max(int(manifest.get('phase', 0)), 76)" in source  # retained only as historical regression marker


def test_wave77_packaged_certification_manifest_is_phase77():
    payload = json.loads((ROOT / 'nicegui_base/certification/certification_manifest.json').read_text(encoding='utf-8'))
    assert payload['phase'] == 77
    assert payload['phase_77_v300a8_final_release_candidate_consolidation_authority_audit_stable_qualification_handoff']['stable_3_0_0_publication_performed'] is False


def test_wave77_authority_chain_has_unique_truth_domains():
    domains = [domain for item in AUTHORITY_CHAIN for domain in item['domains']]
    assert len(domains) == len(set(domains))
    assert {item['wave'] for item in AUTHORITY_CHAIN} == set(range(59, 77))


def test_wave77_audit_pre_final_has_no_errors_or_warnings():
    audit = audit_final_release_candidate(ROOT, require_final_artifacts=False)
    assert audit.status == 'PASS'
    assert audit.errors == ()
    assert audit.warnings == ()
    assert audit.target_qualification_status == 'PENDING'
    assert audit.stable_publication_status == 'NOT_PERFORMED'


def test_wave77_audit_preserves_legacy_module_exports_without_removing_them():
    audit = audit_final_release_candidate(ROOT, require_final_artifacts=False)
    finding = next(item for item in audit.findings if item.code == 'legacy_module_reexports_preserved')
    assert finding.severity == 'info'
    # The current DataTable platform adds the normalized displayed-population
    # snapshot as an intentional root API; the release contract is regenerated
    # from that current source authority.
    # The final Data & Tables closure adds four normalized root APIs for action
    # policy and export denial; the contract is intentionally regenerated for
    # this additive, backwards-compatible surface.
    assert audit.public_api_entries == 1537


def test_wave77_handoff_is_truthful_pending_not_stable_pass():
    audit = audit_final_release_candidate(ROOT, require_final_artifacts=False)
    handoff = build_stable_qualification_handoff(ROOT, audit)
    assert handoff['source_release_candidate_status'] == 'SOURCE_COMPLETE'
    assert handoff['stable_qualification_status'] == 'PENDING'
    assert handoff['stable_publication_status'] == 'NOT_PERFORMED'
    assert 'real 21-route server/WebSocket execution' in handoff['pending_external_qualification']


def test_wave77_release_sync_does_not_rewrite_historical_gold_promotion_evidence():
    source = (ROOT / 'nicegui_base/governance/release_sync.py').read_text(encoding='utf-8')
    current_block = source.split('_CURRENT_EVIDENCE_JSONS', 1)[1].split(')', 1)[0]
    assert 'GOLD_PROMOTION_READINESS.json' not in current_block


def test_wave77_release_sync_preserves_gold_bytes_on_version_sync(tmp_path: Path):
    import shutil
    from nicegui_base.governance.release_sync import sync_release_authority

    work = tmp_path / 'source'
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns('.pytest_cache', '__pycache__', '*.pyc'))
    gold = (work / 'GOLD_PROMOTION_READINESS.json').read_bytes()
    authority_path = work / 'nicegui_base/release_authority.json'
    authority = json.loads(authority_path.read_text(encoding='utf-8'))
    authority['framework_version'] = '3.0.0a99'
    authority_path.write_text(json.dumps(authority, indent=2) + '\n', encoding='utf-8')
    sync_release_authority(work)
    assert (work / 'GOLD_PROMOTION_READINESS.json').read_bytes() == gold


def test_wave77_evidence_index_classifies_gold_historical_and_browser_pending():
    audit = audit_final_release_candidate(ROOT, require_final_artifacts=False)
    hist = {item['path'] for item in audit.evidence_index['historical']}
    pending = {item['path'] for item in audit.evidence_index['pending_external']}
    assert 'GOLD_PROMOTION_READINESS.json' in hist
    assert 'BROWSER_UIUX_GATE.json' in pending
    assert 'TARGET_RUNTIME_GATE_ATTEMPT.json' in pending


def test_wave77_generated_guide_is_installed_but_framework_release_commands_are_not_misrouted_into_apps():
    from nicegui_base.ai.scaffold import GUIDE_NAMES
    assert 'FINAL_RELEASE_CANDIDATE_STABLE_QUALIFICATION_HANDOFF.md' in GUIDE_NAMES
    source = (ROOT / 'nicegui_base/ai/scaffold.py').read_text(encoding='utf-8')
    assert 'longitudinal_assurance_review_command' in source
    assert 'evidence_exception_governance_command' in source
    assert 'final_release_audit_command' not in source
    assert 'stable_qualification_handoff_command' not in source


def test_wave77_final_guide_is_packaged_and_source_mirror_matches():
    a = ROOT / 'docs/FINAL_RELEASE_CANDIDATE_STABLE_QUALIFICATION_HANDOFF.md'
    b = ROOT / 'nicegui_base/ai/guides/FINAL_RELEASE_CANDIDATE_STABLE_QUALIFICATION_HANDOFF.md'
    assert a.read_bytes() == b.read_bytes()
    assert '`SOURCE_COMPLETE` is not stable `3.0.0`' in a.read_text(encoding='utf-8')


def test_wave77_main_cli_exposes_final_audit_and_handoff_routes():
    result = subprocess.run([sys.executable, '-m', 'nicegui_base.cli', '--help'], cwd=ROOT, text=True, capture_output=True, check=True)
    assert 'final-audit' in result.stdout
    assert 'stable-qualification-handoff' in result.stdout


def test_wave77_pyproject_exposes_direct_release_tools():
    text = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert 'nicegui-base-final-audit = "nicegui_base.governance.final_candidate:audit_main"' in text
    assert 'nicegui-base-stable-handoff = "nicegui_base.governance.final_candidate:handoff_main"' in text


def test_wave77_source_manifest_roundtrip_and_exact_coverage(tmp_path: Path):
    (tmp_path / 'a.txt').write_text('a', encoding='utf-8')
    (tmp_path / 'sub').mkdir(); (tmp_path / 'sub/b.txt').write_text('b', encoding='utf-8')
    write_sha256_manifest(tmp_path)
    result = verify_sha256_manifest(tmp_path)
    assert result.passed and result.expected == result.verified == 2


def test_wave77_source_manifest_detects_tamper(tmp_path: Path):
    (tmp_path / 'a.txt').write_text('a', encoding='utf-8')
    write_sha256_manifest(tmp_path)
    (tmp_path / 'a.txt').write_text('changed', encoding='utf-8')
    result = verify_sha256_manifest(tmp_path)
    assert not result.passed
    assert result.mismatches == ('a.txt',)


def test_wave77_source_manifest_detects_unlisted_extra(tmp_path: Path):
    (tmp_path / 'a.txt').write_text('a', encoding='utf-8')
    write_sha256_manifest(tmp_path)
    (tmp_path / 'extra.txt').write_text('x', encoding='utf-8')
    result = verify_sha256_manifest(tmp_path)
    assert not result.passed
    assert result.extras == ('extra.txt',)


def test_wave77_source_manifest_rejects_unsafe_paths(tmp_path: Path):
    (tmp_path / 'SHA256SUMS.txt').write_text('0' * 64 + '  ../escape\n', encoding='utf-8')
    with pytest.raises(ValueError, match='unsafe'):
        verify_sha256_manifest(tmp_path)


def test_wave77_deterministic_zip_is_byte_identical_and_preserves_exec(tmp_path: Path):
    stage = tmp_path / 'stage'; stage.mkdir()
    script = stage / 'run.sh'; script.write_text('#!/bin/sh\necho ok\n', encoding='utf-8'); os.chmod(script, 0o755)
    (stage / 'data.txt').write_text('hello', encoding='utf-8')
    write_sha256_manifest(stage)
    a = build_deterministic_zip(stage, tmp_path / 'a.zip')
    b = build_deterministic_zip(stage, tmp_path / 'b.zip')
    assert a.read_bytes() == b.read_bytes()
    with zipfile.ZipFile(a) as archive:
        info = archive.getinfo('run.sh')
        assert ((info.external_attr >> 16) & 0o111) != 0


def test_wave77_release_artifacts_can_exclude_mutable_runtime_trees(tmp_path: Path):
    stage = tmp_path / 'stage'; stage.mkdir()
    (stage / 'README.md').write_text('immutable', encoding='utf-8')
    (stage / '.venv/bin').mkdir(parents=True)
    (stage / '.venv/bin/python').write_text('runtime', encoding='utf-8')
    (stage / '.nicegui').mkdir()
    (stage / '.nicegui/storage.json').write_text('tab state', encoding='utf-8')
    write_sha256_manifest(stage, exclude=('.venv', '.nicegui'))
    result = verify_sha256_manifest(stage, exclude=('.venv', '.nicegui'))
    assert result.passed and result.expected == result.verified == 1
    archive = build_deterministic_zip(stage, tmp_path / 'rc.zip', exclude=('.venv', '.nicegui'))
    with zipfile.ZipFile(archive) as source:
        assert set(source.namelist()) == {'README.md', 'SHA256SUMS.txt'}


def test_wave77_archive_verifier_checks_manifest_exact_coverage(tmp_path: Path):
    stage = tmp_path / 'stage'; stage.mkdir(); (stage / 'a').write_text('a')
    write_sha256_manifest(stage)
    archive = build_deterministic_zip(stage, tmp_path / 'ok.zip')
    result = verify_release_archive(archive, source_manifest_name='missing')
    assert result.passed
    assert result.manifest and result.manifest.expected == 1


def test_wave77_archive_verifier_detects_unlisted_archive_extra(tmp_path: Path):
    archive = tmp_path / 'bad.zip'
    digest = hashlib.sha256(b'a').hexdigest()
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('a', b'a')
        z.writestr('extra', b'x')
        z.writestr('SHA256SUMS.txt', f'{digest}  a\n')
    result = verify_release_archive(archive, source_manifest_name='missing')
    assert not result.passed
    assert result.manifest and result.manifest.extras == ('extra',)


def test_wave77_archive_verifier_detects_duplicate_and_unsafe_entries(tmp_path: Path):
    archive = tmp_path / 'bad.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('a', b'a'); z.writestr('a', b'b'); z.writestr('../escape', b'x')
    result = verify_release_archive(archive, manifest_name='missing', source_manifest_name='also-missing')
    assert 'a' in result.duplicate_entries
    assert '../escape' in result.unsafe_entries
    assert not result.passed


def test_wave77_current_release_wheel_is_record_and_dependency_clean():
    # The identity-refactored current wheel remains the real regression fixture
    # for the consolidated verifier.
    wheel = verify_wheel(ROOT / 'wheel/nicegui_base-3.0.0a8-py3-none-any.whl')
    assert wheel.passed
    assert wheel.metadata_name == 'nicegui-base'
    assert wheel.metadata_version == '3.0.0a8'
    assert tuple(item for item in wheel.requires_dist if 'extra ==' not in item) == ('nicegui==3.15.0',)


def test_wave77_release_artifact_helpers_add_no_runtime_dependency():
    text = (ROOT / 'nicegui_base/governance/release_artifacts.py').read_text(encoding='utf-8')
    for forbidden in ('requests', 'pandas', 'numpy', 'yaml'):
        assert f'import {forbidden}' not in text


def test_wave77_public_api_has_no_additive_root_exports_before_freeze():
    import nicegui_base
    assert len(set(nicegui_base.__all__)) == 1537
    assert 'TableViewSnapshot' in nicegui_base.__all__
    assert 'audit_final_release_candidate' not in nicegui_base.__all__
    assert 'build_stable_qualification_handoff' not in nicegui_base.__all__


def test_wave77_readme_restores_wave74_history_and_adds_wave77():
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert '## Wave 74 enterprise sustained-operations renewal + continuity' in text
    assert '## Wave 77 final release-candidate consolidation + stable qualification handoff' in text


def test_wave77_release_authority_marks_consolidation_not_new_truth_system():
    payload = json.loads((ROOT / 'nicegui_base/release_authority.json').read_text(encoding='utf-8'))
    assert payload['current_wave'] == 77
    assert 'consolidation-only' in payload['design_constitution']
    assert payload['promotion_target'] == '3.0.0'
    assert payload['release_status'] == 'ALPHA'


def test_wave77_construction_manifest_documents_no_new_authority():
    payload = json.loads((ROOT / 'AI_CONSTRUCTION_MANIFEST.json').read_text(encoding='utf-8'))
    wave = payload['wave77_final_release_candidate_consolidation']
    assert wave['authority'].startswith('No new truth authority.')
    assert 'stable `3.0.0`' not in wave['stable_qualification_rule']  # no publication claim phrasing
    assert 'Real company' in wave['stable_qualification_rule']


def test_wave77_shell_entrypoints_are_executable_in_source_tree():
    paths = sorted({*ROOT.glob('*.sh'), *ROOT.glob('*_bundle/*.sh')})
    assert paths
    assert all(stat.S_IMODE(path.stat().st_mode) & 0o111 for path in paths)


def test_wave77_final_audit_cli_pre_final_json_succeeds(capsys):
    from nicegui_base.governance.final_candidate import audit_main
    code = audit_main(['--root', str(ROOT), '--allow-pre-final', '--format', 'json'])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload['status'] == 'PASS'
    assert payload['target_qualification_status'] == 'PENDING'


def test_wave77_stable_handoff_does_not_claim_company_execution():
    handoff = build_stable_qualification_handoff(ROOT, audit_final_release_candidate(ROOT, require_final_artifacts=False))
    boundary = handoff['claim_boundary']
    assert 'cannot turn missing company/runtime/browser/human' in boundary
    assert 'does not publish stable 3.0.0' in boundary


def test_wave77_wheel_source_representation_matches_identity_refactored_source(tmp_path: Path):
    # The checked-in wheel is historical evidence and must not be rewritten when
    # source changes. Build a current-source wheel-shaped fixture for this pure
    # representation test; the D4 release test performs the real backend build.
    wheel = tmp_path / 'test-current-source-wheel.whl'
    files: dict[str, bytes] = {}
    for path in (ROOT / 'nicegui_base').rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    dist = 'nicegui_base-3.0.0a8.dist-info'
    files[f'{dist}/METADATA'] = (
        b'Metadata-Version: 2.1\nName: nicegui-base\nVersion: 3.0.0a8\n'
        b'Requires-Dist: nicegui==3.15.0\n'
    )
    files[f'{dist}/WHEEL'] = b'Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
    records = []
    for name, data in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
        records.append(f'{name},sha256={digest},{len(data)}')
    files[f'{dist}/RECORD'] = ('\n'.join(records) + f'\n{dist}/RECORD,,\n').encode()
    with zipfile.ZipFile(wheel, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    result = verify_wheel_source_representation(ROOT, wheel)
    assert result.passed
    assert result.compared_files > 0


def test_wave77_generated_application_install_manifest_does_not_point_final_framework_audit_at_app_root(tmp_path: Path):
    from nicegui_base.ai.scaffold import install_ai_materials
    install_ai_materials(tmp_path)
    payload = json.loads((tmp_path / '.nicegui_base/install_manifest.json').read_text(encoding='utf-8'))
    assert 'final_release_audit_command' not in payload
    assert 'stable_qualification_handoff_command' not in payload
    assert 'evidence_exception_governance_command' in payload


def test_wave77_release_sync_current_evidence_list_keeps_source_generated_readiness_but_not_historical_gold():
    source = (ROOT / 'nicegui_base/governance/release_sync.py').read_text(encoding='utf-8')
    block = source.split('_CURRENT_EVIDENCE_JSONS', 1)[1].split(')', 1)[0]
    assert 'LIVE_CERTIFICATION_READINESS.json' in block
    assert 'LIVE_COMPONENT_COVERAGE.json' in block
    assert 'GOLD_PROMOTION_READINESS.json' not in block


def test_wave77_certification_manifest_sync_supports_isolated_manifest_fixture(tmp_path: Path):
    from nicegui_base.governance.source_evidence import _sync_packaged_certification_manifest
    from nicegui_base.certification.mac_coverage import coverage_summary
    target = tmp_path / 'nicegui_base/certification/certification_manifest.json'
    target.parent.mkdir(parents=True)
    target.write_bytes((ROOT / 'nicegui_base/certification/certification_manifest.json').read_bytes())
    _sync_packaged_certification_manifest(tmp_path, test_count=1234, coverage=coverage_summary())
    payload = json.loads(target.read_text(encoding='utf-8'))
    assert payload['phase'] == 77
    assert payload['automated_tests'] == 1234


def test_wave77_current_portable_evidence_has_no_build_machine_path():
    for rel in ('GOVERNANCE_REPORT.json', 'SHIPPED_EXAMPLES_VALIDATION.json'):
        text = (ROOT / rel).read_text(encoding='utf-8')
        assert '/mnt/data/' not in text
