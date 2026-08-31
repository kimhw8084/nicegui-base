from nicegui_base import build_interaction_css


def test_interaction_css_contains_all_major_systems():
    css = build_interaction_css()
    for token in ('cui-form', 'cui-filter-bar', 'cui-alert', 'cui-toast', 'cui-state-view', 'cui-drawer', 'cui-dialog', 'cui-menu'):
        assert token in css


def test_interaction_css_uses_design_tokens():
    css = build_interaction_css()
    assert 'var(--cui-surface)' in css
    assert 'var(--cui-motion-overlay)' in css
    assert 'prefers-reduced-motion' in css


def test_mobile_overlay_transformation_is_encoded():
    css = build_interaction_css()
    assert '@media(max-width:599px)' in css
    assert 'width:100vw!important' in css
