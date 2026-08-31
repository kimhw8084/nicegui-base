from nicegui_base import DataExplorerPage, Icons, PagePattern, get_pattern
from examples.phase11_app.services.equipment import load_equipment


def page_contract(area: str = 'ETCH') -> dict:
    """Framework-compliant page composition contract without rendering NiceGUI in tests."""
    rows = load_equipment(area)
    return {
        'pattern': get_pattern(PagePattern.DATA_EXPLORER).pattern.value,
        'page_class': DataExplorerPage.__name__,
        'refresh_icon': Icons.REFRESH,
        'row_count': len(rows),
    }
