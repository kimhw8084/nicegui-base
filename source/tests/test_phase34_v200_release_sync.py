from __future__ import annotations

import json
import shutil
from pathlib import Path

from nicegui_base.governance.release_sync import render_public_api_index, sync_release_authority

ROOT = Path(__file__).resolve().parents[1]


def test_v2_release_sync_is_installed_as_a_first_class_release_tool():
    pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert 'nicegui-base-release-sync = "nicegui_base.governance.release_sync:main"' in pyproject


def test_v2_public_api_index_is_deterministically_rendered_from_contract():
    authority = json.loads((ROOT / 'nicegui_base/release_authority.json').read_text(encoding='utf-8'))
    expected = render_public_api_index(ROOT, version=authority['framework_version'], nicegui=authority['nicegui_version'])
    assert (ROOT / 'docs/PUBLIC_API_INDEX.md').read_text(encoding='utf-8') == expected
    assert (ROOT / 'nicegui_base/ai/guides/PUBLIC_API_INDEX.md').read_text(encoding='utf-8') == expected


def test_v2_release_sync_updates_current_authorities_without_rewriting_historical_phase_evidence(tmp_path: Path):
    # Copy only the files the synchronizer owns plus the importable package.
    work = tmp_path / 'source'
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns('.pytest_cache', '__pycache__', '*.pyc'))
    authority_path = work / 'nicegui_base/release_authority.json'
    authority = json.loads(authority_path.read_text(encoding='utf-8'))
    historical = (work / 'PHASE_31_V173_CONTRACT_EVIDENCE_HARDENING_REPORT.json').read_bytes()
    authority['framework_version'] = '2.0.0rc99'
    authority_path.write_text(json.dumps(authority, indent=2) + '\n', encoding='utf-8')
    sync_release_authority(work)
    assert 'version = "2.0.0rc99"' in (work / 'pyproject.toml').read_text(encoding='utf-8')
    assert json.loads((work / 'FRAMEWORK_CATALOG.json').read_text(encoding='utf-8'))['framework_version'] == '2.0.0rc99'
    assert json.loads((work / 'nicegui_base/ai/framework_catalog.json').read_text(encoding='utf-8'))['framework_version'] == '2.0.0rc99'
    assert json.loads((work / 'CERTIFICATION_REPORT.json').read_text(encoding='utf-8'))['framework_version'] == '2.0.0rc99'
    assert 'Framework version: `2.0.0rc99`' in (work / 'docs/PUBLIC_API_INDEX.md').read_text(encoding='utf-8')
    assert (work / 'PHASE_31_V173_CONTRACT_EVIDENCE_HARDENING_REPORT.json').read_bytes() == historical


def test_v2_source_evidence_command_cannot_masquerade_as_target_certification():
    source = (ROOT / 'nicegui_base/governance/source_evidence.py').read_text(encoding='utf-8')
    assert "'release_certified': False" in source
    assert "'target_runtime_status': 'PENDING'" in source
    assert "Source PASS does not certify the final release" in source
    assert 'nicegui-base-source-certify = "nicegui_base.governance.source_evidence:main"' in (ROOT / 'pyproject.toml').read_text(encoding='utf-8')


def test_release_sync_rewrites_version_inside_underscore_delimited_status(tmp_path):
    import json
    import shutil
    from nicegui_base.governance.release_sync import sync_release_authority

    root = tmp_path / 'source'
    shutil.copytree(ROOT, root)
    authority_path = root / 'nicegui_base/release_authority.json'
    authority = json.loads(authority_path.read_text(encoding='utf-8'))
    authority['framework_version'] = '2.0.0rc99'
    authority_path.write_text(json.dumps(authority, indent=2) + '\n', encoding='utf-8')
    clean_path = root / 'CLEAN_INSTALL_CERTIFICATION.json'
    clean = json.loads(clean_path.read_text(encoding='utf-8'))
    clean['status'] = 'NOT_EXECUTED_FOR_2.0.0rc3'
    clean_path.write_text(json.dumps(clean, indent=2) + '\n', encoding='utf-8')

    sync_release_authority(root)
    updated = json.loads(clean_path.read_text(encoding='utf-8'))
    assert updated['status'] == 'NOT_EXECUTED_FOR_2.0.0rc99'


def test_release_sync_rewrites_v_prefixed_nested_authority_labels(tmp_path):
    import json
    import shutil
    from nicegui_base.governance.release_sync import sync_release_authority

    root = tmp_path / 'source'
    shutil.copytree(ROOT, root)
    authority_path = root / 'nicegui_base/release_authority.json'
    authority = json.loads(authority_path.read_text(encoding='utf-8'))
    authority['framework_version'] = '2.0.0rc99'
    authority_path.write_text(json.dumps(authority, indent=2) + '\n', encoding='utf-8')
    manifest_path = root / 'nicegui_base/certification/certification_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['hotfix_release'] = 'v2.0.0rc3 nested label'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    sync_release_authority(root)
    updated = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert updated['hotfix_release'] == 'v2.0.0rc99 nested label'
    assert '2.0.0rc99' in (root / 'README.md').read_text(encoding='utf-8')


def test_release_sync_preserves_stable_200_promotion_target(tmp_path):
    import json
    import shutil
    from nicegui_base.governance.release_sync import sync_release_authority

    root = tmp_path / 'source'
    shutil.copytree(ROOT, root)
    authority_path = root / 'nicegui_base/release_authority.json'
    authority = json.loads(authority_path.read_text(encoding='utf-8'))
    authority['framework_version'] = '2.0.0rc99'
    authority['promotion_target'] = '2.0.0'
    authority_path.write_text(json.dumps(authority, indent=2) + '\n', encoding='utf-8')
    sync_release_authority(root)
    current = json.loads(authority_path.read_text(encoding='utf-8'))
    manifest = json.loads((root / 'nicegui_base/certification/certification_manifest.json').read_text(encoding='utf-8'))
    assert current['promotion_target'] == '2.0.0'
    assert manifest['phase_32_v2_release_candidate']['final_promotion_target'] == '2.0.0'
    historical_release_doc = (root / 'docs/V200RC1_RELEASE_CANDIDATE.md').read_text(encoding='utf-8')
    assert 'Final 2.0.0 promotion' in historical_release_doc
    assert 'Final 2.0.0rc99 promotion' not in historical_release_doc
