from nicegui_base import Icons, Illustrations, get_icon

def test_static_icon_keys_match_registry():
    assert Icons.REFRESH.value == 'refresh'
    assert Icons.WAFER_MAP.value == 'wafer-map'
    assert get_icon(Icons.TOOL).key == 'tool'

def test_static_illustration_keys():
    assert Illustrations.NO_DATA.value == 'no-data'
    assert Illustrations.PERMISSION_DENIED.value == 'permission-denied'
