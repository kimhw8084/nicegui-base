from nicegui_base.design import BREAKPOINTS, CONTROL_HEIGHTS, DENSITIES, MOTION, RADII, SPACING, TYPOGRAPHY, build_design_system


def test_spacing_is_strictly_non_decreasing():
    values = list(SPACING.values())
    assert values == sorted(values)


def test_primary_spacing_rhythm_exists():
    assert SPACING["1"] == 4
    assert SPACING["2"] == 8
    assert SPACING["4"] == 16
    assert SPACING["6"] == 24


def test_radii_are_semantic():
    # v1.5 has exactly three visible rectangle families: control, surface and overlay.
    assert RADII["xs"] == RADII["sm"] == 10
    assert RADII["md"] == 14
    assert RADII["lg"] == RADII["xl"] == 18
    assert RADII["sm"] < RADII["md"] < RADII["lg"] < RADII["pill"]


def test_touch_target_is_not_smaller_than_large_control():
    assert CONTROL_HEIGHTS["touch_target"] >= 44
    assert CONTROL_HEIGHTS["touch_target"] >= CONTROL_HEIGHTS["large"]


def test_breakpoints_ascending():
    values = list(BREAKPOINTS.values())
    assert values == sorted(values)


def test_motion_is_restrained():
    assert MOTION["instant_ms"] <= 100
    assert MOTION["standard_ms"] <= 180
    assert MOTION["emphasis_ms"] <= 240


def test_typography_has_required_roles():
    required = {"display", "page_title", "heading", "body", "label", "caption", "data", "code"}
    assert required.issubset(TYPOGRAPHY)


def test_density_modes_exist():
    assert set(DENSITIES) == {"comfortable", "compact", "dense"}


def test_design_system_is_complete():
    system = build_design_system()
    assert system.light.page
    assert system.dark.page
    assert system.typography["body"]["size"] == 13
