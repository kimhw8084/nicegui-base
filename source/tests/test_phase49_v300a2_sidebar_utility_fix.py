from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sidebar_footer_only_renders_support_and_documentation() -> None:
    source = (ROOT / 'nicegui_base/integrations/nicegui_layout.py').read_text(encoding='utf-8')
    block = source.split('def _render_support_footer', 1)[1].split('@dataclass', 1)[0]
    assert "action('help', 'Support', on_support)" in block
    assert "action('file', 'Documentation', on_docs)" in block
    assert "action('message', 'Submit feedback', on_feedback)" not in block
    assert 'on_feedback' in block  # compatibility input remains accepted, but is non-visual


def test_compact_sidebar_footer_icons_are_hard_centered() -> None:
    css = (ROOT / 'nicegui_base/design/hardening_css.py').read_text(encoding='utf-8')
    assert "html[data-sidebar='compact'] .cui-sidebar-footer__action{position:relative!important;width:36px!important;height:36px!important" in css
    assert "left:50%!important;top:50%!important;transform:translate(-50%,-50%)!important" in css


def test_browser_gate_measures_sidebar_utility_icon_centering() -> None:
    source = (ROOT / 'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    assert "document.querySelectorAll('.cui-icon-button,.cui-sidebar-footer__action')" in source
    assert "add('ICON_NOT_CENTERED'" in source
