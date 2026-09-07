from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_segmented_control_is_semantic_and_deterministic() -> None:
    source = (ROOT / "source/nicegui_base/integrations/nicegui_layout.py").read_text(encoding="utf-8")
    assert "cui-segmented-control--semantic-v4" in source
    assert "role=\"radiogroup\"" in source
    assert "role=\"radio\"" in source
    assert "aria-checked" in source
    assert "aria-label={json.dumps(str(label))}" in source
    assert "window.__niceguiBaseSegmentedA11y" not in source


def test_segmented_control_preserves_change_event_contract() -> None:
    source = (ROOT / "source/nicegui_base/integrations/nicegui_layout.py").read_text(encoding="utf-8")
    assert "SimpleNamespace(value=value)" in source
    assert "inspect.isawaitable(result)" in source


def test_wave35_v2_repairs_are_preserved() -> None:
    components = (ROOT / "source/nicegui_base/integrations/nicegui_components.py").read_text(encoding="utf-8")
    content = (ROOT / "source/nicegui_base/integrations/nicegui_content.py").read_text(encoding="utf-8")
    assert components.count("self.element.props(f'aria-label={json.dumps(label)}')") >= 2
    assert "self.element.on('keydown.escape', lambda _e: self.close())" in content
