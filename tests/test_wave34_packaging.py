from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_wave34_setuptools_uses_source_layout():
    with (ROOT / "pyproject.toml").open("rb") as handle:
        payload = tomllib.load(handle)
    setuptools = payload["tool"]["setuptools"]
    assert setuptools["package-dir"][""] == "source"
    finder = setuptools["packages"]["find"]
    assert finder["where"] == ["source"]
    assert "nicegui_base*" in finder["include"]
    assert "company_ui" in finder["include"]


def test_wave34_source_layout_contains_both_packages():
    assert (ROOT / "source/nicegui_base/__init__.py").is_file()
    assert (ROOT / "source/company_ui/__init__.py").is_file()
    assert (ROOT / "source/nicegui_base/release_authority.json").is_file()
