from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_button_wrappers_publish_explicit_accessible_names() -> None:
    source = (ROOT / "source/nicegui_base/integrations/nicegui_components.py").read_text(encoding="utf-8")
    assert "self.element.props(f'aria-label={json.dumps(label)}')" in source
    # One contract in Button and one in ActionButton.
    assert source.count("self.element.props(f'aria-label={json.dumps(label)}')") >= 2


def test_command_palette_has_escape_keyboard_contract() -> None:
    source = (ROOT / "source/nicegui_base/integrations/nicegui_content.py").read_text(encoding="utf-8")
    assert "self.element.on('keydown.escape', lambda _e: self.close())" in source


def test_wave35_canonical_viewports_are_still_governed() -> None:
    from nicegui_base.design.responsive import CANONICAL_VIEWPORTS
    expected = {
        "phone-compact": (390, 844),
        "tablet-narrow": (768, 1024),
        "desktop-compact": (1280, 900),
        "desktop-wide": (1440, 1000),
    }
    for key, dims in expected.items():
        profile = CANONICAL_VIEWPORTS[key]
        assert (profile.width, profile.height) == dims
