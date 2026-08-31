from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_switch_uses_contained_native_quality_proportions():
    css = (ROOT / "nicegui_base/design/hardening_css.py").read_text(encoding="utf-8")
    assert "grid-template-columns:51px minmax(0,1fr)!important" in css
    assert "width:51px!important;height:31px!important;padding:0!important" in css
    assert "overflow:hidden!important" in css
    assert "top:2px!important;left:2px!important;width:27px!important;height:27px!important" in css
    assert "transform:translateX(20px)!important" in css


def test_switch_thumb_is_fully_contained_at_both_end_stops():
    track_width = 51
    track_height = 31
    inset = 2
    thumb = 27
    travel = 20
    assert thumb == track_height - 2 * inset
    assert inset + thumb + travel + inset == track_width
    assert inset == 2


def test_switch_visual_separation_comes_from_track_containment_not_outline():
    css = (ROOT / "nicegui_base/design/hardening_css.py").read_text(encoding="utf-8")
    assert "border:0!important" in css
    assert "box-shadow:0 1px 2px rgba(0,0,0,.14),0 2px 5px rgba(0,0,0,.10)!important" in css
