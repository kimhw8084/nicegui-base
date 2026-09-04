from __future__ import annotations

import os
import subprocess
from importlib.resources import files
from pathlib import Path

from nicegui_base.governance.release_identity import load_release_identity

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "source/nicegui_base/workbench/app.py"


def test_wave34_release_identity_default_is_cwd_independent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    identity = load_release_identity()
    assert identity.framework_name == "nicegui-base"
    assert files("nicegui_base").joinpath("release_authority.json").is_file()


def test_wave34_explicit_release_identity_root_contract_is_preserved(tmp_path):
    package_dir = tmp_path / "nicegui_base"
    package_dir.mkdir()
    packaged = files("nicegui_base").joinpath("release_authority.json").read_text(encoding="utf-8")
    (package_dir / "release_authority.json").write_text(packaged, encoding="utf-8")
    identity = load_release_identity(tmp_path)
    assert identity.framework_name == "nicegui-base"


def test_wave34_quality_evidence_and_health_semantics_are_current():
    source = APP.read_text(encoding="utf-8")
    assert "Iteration 1 source checks" not in source
    assert "with _section('Current source checks'):" in source
    assert "'10/10 canonical generic application patterns are discoverable'" not in source
    assert "'58/58 canonical semiconductor analytical surfaces are discoverable'" not in source
    assert "'8/8 canonical semiconductor recipes are discoverable'" not in source
    assert "HealthCheck('workbench-contract', workbench_contract_health, critical=False" in source


def test_wave34_dev_test_extra_has_async_support():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'pytest>=8,<9' in pyproject
    assert 'pytest-asyncio>=0.25,<1' in pyproject


def test_wave34_repository_tracks_no_python_bytecode():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE
    ).stdout.splitlines()
    assert not [p for p in tracked if "/__pycache__/" in f"/{p}" or p.endswith((".pyc", ".pyo"))]
