from nicegui_base.design.css import build_css


def test_css_contains_light_dark_system_support():
    css = build_css()
    assert "data-theme='light'" in css
    assert "data-theme='dark'" in css
    assert "data-theme='system'" in css


def test_css_contains_nicegui_variables():
    css = build_css()
    assert "--nicegui-default-padding" in css
    assert "--nicegui-default-gap" in css


def test_css_contains_reduced_motion():
    assert "prefers-reduced-motion" in build_css()


def test_css_contains_density_modes():
    css = build_css()
    for mode in ("comfortable", "compact", "dense"):
        assert f"data-density='{mode}'" in css


def test_css_contains_semantic_tokens_not_component_specific_classes():
    css = build_css()
    for token in ("--cui-page", "--cui-surface", "--cui-text-primary", "--cui-accent", "--cui-danger"):
        assert token in css
