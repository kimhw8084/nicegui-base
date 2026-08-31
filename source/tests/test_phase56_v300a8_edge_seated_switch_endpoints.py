from pathlib import Path


def _css() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "nicegui_base/design/hardening_css.py").read_text(encoding="utf-8").replace(" ", "")


def test_superseded_edge_flush_switch_is_replaced_by_two_pixel_endpoint_seating() -> None:
    css = _css()
    assert "width:51px!important;height:31px!important;padding:0!important" in css
    assert "top:2px!important;left:2px!important;width:27px!important;height:27px!important" in css
    assert "transform:translateX(0)!important" in css
    assert "transform:translateX(20px)!important" in css
    assert "transform:translateX(24px)!important" not in css


def test_switch_preserves_two_pixel_containment_at_both_endpoints() -> None:
    track_w, track_h = 51, 31
    thumb_w, thumb_h = 27, 27
    inset = 2
    travel = track_w - thumb_w - (2 * inset)
    assert travel == 20
    assert (track_h - thumb_h) / 2 == inset
    assert inset + thumb_w + travel + inset == track_w
