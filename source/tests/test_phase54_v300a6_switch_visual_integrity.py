from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_switch_thumb_keeps_full_visual_edge_at_both_end_stops():
    css = (ROOT / "nicegui_base/design/hardening_css.py").read_text(encoding="utf-8")
    assert "overflow:hidden!important" in css
    assert "top:2px!important;left:2px!important" in css
    assert "width:27px!important;height:27px!important" in css
    assert "transform:translateX(20px)!important" in css
    assert "transform:translateX(24px)!important" not in css

def test_switch_has_one_canonical_css_owner_and_real_thumb_dom():
    base = (ROOT / "nicegui_base/components/css.py").read_text(encoding="utf-8")
    hardened = (ROOT / "nicegui_base/design/hardening_css.py").read_text(encoding="utf-8")
    components = (ROOT / "nicegui_base/integrations/nicegui_components.py").read_text(encoding="utf-8")
    assert "/* Switch */" not in base
    assert hardened.count("/* Native switch — canonical geometry contract.") == 1
    assert "classes('cui-choice-visual cui-switch-track')" in components
    assert "classes('cui-switch-thumb')" in components
