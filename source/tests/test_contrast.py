from nicegui_base.design.contrast import contrast_ratio
from nicegui_base.design.tokens import DARK, LIGHT


def test_light_primary_text_wcag_aa():
    assert contrast_ratio(LIGHT.text_primary, LIGHT.surface) >= 4.5


def test_light_secondary_text_wcag_aa():
    assert contrast_ratio(LIGHT.text_secondary, LIGHT.surface) >= 4.5


def test_light_tertiary_text_wcag_aa():
    assert contrast_ratio(LIGHT.text_tertiary, LIGHT.surface) >= 4.5


def test_dark_primary_text_wcag_aa():
    assert contrast_ratio(DARK.text_primary, DARK.surface) >= 4.5


def test_dark_secondary_text_wcag_aa():
    assert contrast_ratio(DARK.text_secondary, DARK.surface) >= 4.5


def test_dark_tertiary_text_wcag_aa():
    assert contrast_ratio(DARK.text_tertiary, DARK.surface) >= 4.5


def test_light_accent_text_on_surface_wcag_aa():
    assert contrast_ratio(LIGHT.accent, LIGHT.surface) >= 4.5


def test_dark_accent_text_on_surface_wcag_aa():
    assert contrast_ratio(DARK.accent, DARK.surface) >= 4.5
