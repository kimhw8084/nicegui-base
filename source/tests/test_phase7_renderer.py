import pytest
from nicegui_base.visual import IconSize, render_icon_svg, render_illustration_svg

def test_icon_renderer_sizes_and_accessibility():
    s=render_icon_svg('refresh',size=IconSize.SM,label='Refresh data')
    assert 'width="16"' in s and 'aria-label="Refresh data"' in s and 'role="img"' in s

def test_decorative_icon_is_hidden():
    assert 'aria-hidden="true"' in render_icon_svg('search')

def test_illustration_renderer():
    assert 'cui-illustration' in render_illustration_svg('no-data',label='No data')

def test_unknown_icon_is_clear_error():
    with pytest.raises(KeyError,match='Unknown icon'): render_icon_svg('definitely-not-an-icon')
