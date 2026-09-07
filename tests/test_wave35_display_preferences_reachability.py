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

def test_display_preference_reconciliation_is_reachable() -> None:
    fn = _display_control_bar()
    body = fn.body
    reconcile_index = next(
        i for i, n in enumerate(body)
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "reconcile_initial_theme"
    )
    timer_index = next(
        i for i, n in enumerate(body)
        if isinstance(n, ast.If)
        and any(
            isinstance(x, ast.Call)
            and isinstance(x.func, ast.Attribute)
            and x.func.attr == "timer"
            for x in ast.walk(n)
        )
    )
    return_indices = [
        i for i, n in enumerate(body)
        if isinstance(n, ast.Return)
        and isinstance(n.value, ast.Name)
        and n.value.id == "trigger"
    ]
    assert return_indices == [len(body) - 1]
    assert reconcile_index < timer_index < return_indices[0]

def test_display_preferences_are_menu_owned_and_accessible() -> None:
    source = APP.read_text(encoding="utf-8")
    assert "cui-workbench-preferences-trigger" in source
    assert 'aria-label="Open display preferences"' in source
    assert "cui-workbench-display-controls" in source
    assert "WAVE35_DISPLAY_PREFERENCES_REACHABILITY_V13" in source
