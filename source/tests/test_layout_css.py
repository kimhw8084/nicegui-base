from nicegui_base.layouts import build_layout_css


def test_layout_css_contains_shell_and_page_contracts():
    css = build_layout_css()
    for selector in ['.cui-app-header', '.cui-app-sidebar', '.cui-page', '.cui-page-header', '.cui-grid--metrics', '.cui-workspace']:
        assert selector in css


def test_layout_css_contains_all_responsive_breakpoints():
    css = build_layout_css()
    assert '@media (max-width: 1199px)' in css
    assert '@media (max-width: 899px)' in css
    assert '@media (max-width: 599px)' in css


def test_layout_css_uses_design_tokens_not_new_hardcoded_theme_colors():
    css = build_layout_css()
    assert 'var(--cui-text-primary)' in css
    assert 'var(--cui-border-subtle)' in css
    assert 'var(--cui-surface)' in css
    assert '#0A66FF' not in css


def test_layout_css_has_semantic_drawer_widths():
    css = build_layout_css()
    assert '--cui-drawer-small:' in css
    assert '--cui-drawer-medium:' in css
    assert '--cui-drawer-large:' in css
    assert '--cui-drawer-xlarge:' in css
