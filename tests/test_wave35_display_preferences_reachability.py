from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "source/nicegui_base/workbench/app.py"

def _display_control_bar() -> ast.FunctionDef:
    text = APP.read_text(encoding="utf-8")
    tree = ast.parse(text)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_display_control_bar"]
    assert len(nodes) == 1
    return nodes[0]

def test_display_preferences_are_reachable_and_return_the_trigger() -> None:
    fn = _display_control_bar()
    body = fn.body
    return_indices = [
        i for i, n in enumerate(body)
        if isinstance(n, ast.Return)
        and isinstance(n.value, ast.Name)
        and n.value.id == "trigger"
    ]
    assert return_indices == [len(body) - 1]
    assert any(isinstance(n, ast.Call) and getattr(n.func, 'id', '') == 'sync_theme' for n in ast.walk(fn))

def test_display_preferences_are_menu_owned_and_accessible() -> None:
    source = APP.read_text(encoding="utf-8")
    assert "cui-workbench-preferences-trigger" in source
    assert 'aria-label="Open appearance preferences"' in source
    assert "cui-workbench-display-controls" in source
    assert "WAVE35_DISPLAY_PREFERENCES_REACHABILITY_V13" in source
