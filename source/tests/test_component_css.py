import re
from nicegui_base import build_component_css
from nicegui_base.design import build_css


def test_component_css_contains_required_button_states():
    css = build_component_css()
    for token in ['cui-button--primary', 'cui-button--secondary', 'cui-button--tertiary', 'cui-button--ghost', 'cui-button--danger', 'is-loading']:
        assert token in css


def test_component_css_contains_field_states():
    css = build_component_css()
    for token in ['cui-field-control--error', 'cui-field-control--readonly', 'is-disabled', 'focus-visible']:
        assert token in css


def test_component_css_contains_surface_states():
    css = build_component_css()
    for token in ['cui-surface--panel', 'cui-surface--card', 'cui-surface--well', 'cui-surface--interactive', 'is-selected']:
        assert token in css


def test_component_css_contains_status_intents():
    css = build_component_css()
    for token in ['cui-badge--neutral', 'cui-badge--info', 'cui-badge--success', 'cui-badge--warning', 'cui-badge--danger']:
        assert token in css


def test_component_css_has_coarse_pointer_touch_target():
    css = build_component_css()
    assert '@media (pointer: coarse)' in css
    assert 'min-height: 44px' in css


def test_component_css_contains_density_modes():
    # Density is a design-system authority in v2; component CSS consumes its
    # variables instead of redeclaring a second density constitution.
    css = build_css()
    for density in ['comfortable', 'compact', 'dense']:
        assert f"[data-density='{density}']" in css
    component_css = build_component_css()
    assert '--cui-control-medium:' not in component_css
    assert '--cui-control-small:' not in component_css


def test_component_css_does_not_embed_hex_colors():
    css = build_component_css()
    assert not re.search(r'#[0-9a-fA-F]{3,8}', css)


def test_component_css_uses_design_tokens_for_visuals():
    css = build_component_css()
    for token in ['--cui-accent', '--cui-border-default', '--cui-radius-sm', '--cui-motion-fast', '--cui-text-primary']:
        assert token in css


def test_component_css_contains_extended_phase3_components():
    css = build_component_css()
    for token in ['cui-button-group','cui-split-button','cui-divider','cui-collapsible','cui-chip','cui-count-badge','cui-semantic-indicator']:
        assert token in css
