from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "source/nicegui_base/integrations/nicegui_components.py"

def _source() -> str:
    return COMPONENTS.read_text(encoding="utf-8")

def _file_upload() -> ast.ClassDef:
    text = _source()
    tree = ast.parse(text)
    nodes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FileUpload"]
    assert len(nodes) == 1
    return nodes[0]

def test_file_upload_focusable_shell_has_accessible_name() -> None:
    source = _source()
    assert "WAVE35_FILE_UPLOAD_A11Y_V16" in source
    assert "shell_label = f'{label} upload area'" in source
    assert 'role="group" tabindex="0" aria-label=' in source

def test_file_upload_names_generated_browse_action() -> None:
    cls = _file_upload()
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_install_accessibility_bridge")
    source = ast.get_source_segment(_source(), method) or ""
    assert "input.closest('[role=\"button\"]')" in source
    assert "browse.setAttribute('aria-label'" in source
    assert "browse.setAttribute('title'" in source

def test_file_upload_installs_accessibility_bridge_once() -> None:
    cls = _file_upload()
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    calls = [
        n for n in ast.walk(init)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "_install_accessibility_bridge"
    ]
    assert len(calls) == 1
