from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_switch_uses_real_track_and_thumb_dom():
    source = (ROOT / "nicegui_base/integrations/nicegui_components.py").read_text(encoding="utf-8")
    region = source[source.index("class Switch"):source.index("class Slider")]
    assert "cui-choice-visual cui-switch-track" in region
    assert "cui-switch-thumb" in region
    assert "::after" not in region


def test_switch_css_has_one_owner_and_no_24px_edge_flush_override():
    hardening = (ROOT / "nicegui_base/design/hardening_css.py").read_text(encoding="utf-8")
    base = (ROOT / "nicegui_base/components/css.py").read_text(encoding="utf-8")
    normalization = (ROOT / "nicegui_base/integrations/visual_normalization.py").read_text(encoding="utf-8")
    assert hardening.count("/* Native switch — canonical geometry contract.") == 1
    assert "transform:translateX(20px)!important" in hardening
    assert "transform:translateX(24px)!important" not in hardening
    assert ".cui-switch-track" not in base
    assert "q-toggle__track" not in normalization
    assert "q-toggle__thumb" not in normalization


def test_disabled_switch_keeps_off_geometry_and_only_changes_appearance():
    css = (ROOT / "nicegui_base/design/hardening_css.py").read_text(encoding="utf-8")
    assert ".cui-choice-row:has(.cui-choice-native:disabled) .cui-switch-track" in css
    disabled_tail = css[css.index(".cui-choice-row:has(.cui-choice-native:disabled)"):]
    assert "translateX" not in disabled_tail.split("/* Dual native range", 1)[0]


def test_raw_nicegui_switch_and_toggle_are_validator_controls():
    validator = (ROOT / "nicegui_base/ai/validator.py").read_text(encoding="utf-8")
    assert "'switch'" in validator
    assert "'toggle'" in validator


def test_reference_gallery_uses_supported_checked_parameter():
    for rel in ("nicegui_base/certification/apps.py", "examples/component_gallery.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "Switch('Auto refresh', value=True)" not in text
        assert "Switch('Auto refresh',value=True)" not in text
        assert "checked=True" in text
