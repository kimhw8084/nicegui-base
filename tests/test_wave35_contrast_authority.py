from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "source/nicegui_base/integrations/nicegui_components.py"
LAYOUT = ROOT / "source/nicegui_base/integrations/nicegui_layout.py"
COMPONENT_CSS = ROOT / "source/nicegui_base/components/css.py"
LAYOUT_CSS = ROOT / "source/nicegui_base/layouts/css.py"
TOKENS = ROOT / "source/nicegui_base/design/tokens.py"

def _ui_button_calls(path: Path):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    return [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "button"
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "ui"
    ]

def _hex_luminance(value: str) -> float:
    value = value.lstrip("#")
    rgb = [int(value[i:i+2], 16) / 255 for i in (0, 2, 4)]
    def linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = [linear(c) for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_hex_luminance(a), _hex_luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)

def test_company_owned_buttons_do_not_request_quasar_primary() -> None:
    for path in (COMPONENTS, LAYOUT):
        text = path.read_text(encoding="utf-8")
        calls = _ui_button_calls(path)
        assert calls
        for call in calls:
            colors = [kw for kw in call.keywords if kw.arg == "color"]
            if not colors:
                raise AssertionError(ast.get_source_segment(text, call))
            value = colors[0].value
            if isinstance(value, ast.Constant):
                assert value.value != "primary", ast.get_source_segment(text, call)

def test_zero_argument_ui_button_is_valid_after_normalization() -> None:
    source = LAYOUT.read_text(encoding="utf-8")
    assert "ui.button(color=None)" in source
    ast.parse(source)

def test_quasar_primary_compatibility_bridge_uses_semantic_roles() -> None:
    source = COMPONENT_CSS.read_text(encoding="utf-8")
    assert "WAVE35_CONTRAST_AUTHORITY_V19" in source
    assert ".q-btn.bg-primary.text-white" in source
    assert "background: var(--cui-accent) !important" in source
    assert "color: var(--cui-text-inverse) !important" in source
    assert ".q-btn.text-primary:not(.bg-primary)" in source
    assert "color: var(--cui-accent-hover) !important" in source

def test_shell_contrast_roles_are_semantic() -> None:
    source = LAYOUT_CSS.read_text(encoding="utf-8")
    assert "color: var(--cui-accent-hover)" in source
    assert ".cui-user-menu-trigger" in source
    assert "background: var(--cui-surface-secondary)" in source
    assert "color: var(--cui-text-primary)" in source

def test_governed_light_contrast_pairs_clear_45() -> None:
    assert _contrast("#707076", "#F7F7F9") >= 4.5
    assert _contrast("#707076", "#F5F5F7") >= 4.5
    assert _contrast("#0064C8", "#E8F2FF") >= 4.5
    assert _contrast("#0071E3", "#FFFFFF") >= 4.5
    source = TOKENS.read_text(encoding="utf-8")
    assert 'text_tertiary="#707076"' in source

def test_governed_dark_primary_pair_is_readable() -> None:
    assert _contrast("#5EA6FF", "#0F0F11") >= 4.5
