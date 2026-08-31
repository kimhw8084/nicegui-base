from nicegui_base.visualization import CATEGORICAL, chart_theme, stable_series_color

def test_stable_series_color_is_deterministic():
    assert stable_series_color('TOOL-01')==stable_series_color('TOOL-01')

def test_palette_has_multiple_distinct_colors():
    assert len(CATEGORICAL)>=8 and len(set(CATEGORICAL))==len(CATEGORICAL)

def test_light_dark_chart_themes_derive_from_design_tokens():
    light=chart_theme('light'); dark=chart_theme('dark')
    assert light.text_primary != dark.text_primary
    assert light.accent != dark.accent
    assert light.background=='transparent'
