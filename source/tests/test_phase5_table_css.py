from nicegui_base.data_table import build_data_table_css

def test_table_css_has_density_contract():
    css=build_data_table_css()
    for key in ('comfortable','compact','dense'): assert f'cui-data-table--{key}' in css

def test_table_css_has_states():
    css=build_data_table_css()
    for key in ('is-selected','cui-table-empty','cui-table-loading','cui-table-expanded'): assert key in css

def test_table_css_is_responsive():
    assert '@media (max-width:899px)' in build_data_table_css()

def test_table_css_respects_reduced_motion():
    assert 'prefers-reduced-motion' in build_data_table_css()

def test_no_external_urls():
    css=build_data_table_css().lower()
    assert 'http://' not in css and 'https://' not in css

def test_braces_balanced():
    css=build_data_table_css(); assert css.count('{')==css.count('}')
