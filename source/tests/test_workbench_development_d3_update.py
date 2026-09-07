from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest


def _update_module():
    path = Path(__file__).resolve().parents[2] / 'tools' / 'apply_development_D3.py'
    spec = importlib.util.spec_from_file_location('apply_development_D3', path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture_root(tmp_path: Path, module) -> Path:
    root = tmp_path / 'repo'
    for relative, marker in module.CONTRACT_MARKERS.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(marker + '\n', encoding='utf-8')
    identity = root / module.TARGETS[0]
    identity.parent.mkdir(parents=True, exist_ok=True)
    identity.write_bytes(module.D3_IDENTITY.replace(b'NGB-20260905-D3', b'NGB-20260905-D2').replace(b'Development update D3', b'Development update D2'))
    runtime = root / module.TARGETS[1]
    runtime.parent.mkdir(parents=True, exist_ok=True)
    source = (Path(__file__).resolve().parents[2] / module.TARGETS[1]).read_bytes()
    runtime.write_bytes(source.replace(b'nicegui-base-runtime-bundle-D3', b'nicegui-base-runtime-bundle-D2'))
    (root / '.nicegui_base').mkdir(parents=True, exist_ok=True)
    return root


def test_d3_update_is_idempotent_backed_up_conflict_safe_and_exactly_rollbackable(tmp_path):
    module = _update_module()
    root = _fixture_root(tmp_path, module)
    identity_before = (root / module.TARGETS[0]).read_bytes()
    runtime_before = (root / module.TARGETS[1]).read_bytes()

    applied = module.apply(root)
    assert applied['status'] == 'applied'
    backup = root / applied['backup_directory']
    assert (backup / module.TARGETS[0]).read_bytes() == identity_before
    assert (backup / module.TARGETS[1]).read_bytes() == runtime_before
    assert module.apply(root)['status'] == 'already_applied'

    (root / module.TARGETS[0]).write_text('unexpected local edit\n', encoding='utf-8')
    with pytest.raises(module.UpdateConflict, match='conflict'):
        module.apply(root)
    (root / module.TARGETS[0]).write_bytes(module.D3_IDENTITY)

    rolled_back = module.rollback(root)
    assert rolled_back['status'] == 'rolled_back'
    assert (root / module.TARGETS[0]).read_bytes() == identity_before
    assert (root / module.TARGETS[1]).read_bytes() == runtime_before
    assert module.rollback(root)['status'] == 'already_rolled_back'
    assert hashlib.sha256((root / module.TARGETS[0]).read_bytes()).hexdigest() == module.D2_SHA256[module.TARGETS[0]]
