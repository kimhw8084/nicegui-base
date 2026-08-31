from nicegui_base import ICON_REGISTRY, SvgIcon, get_icon, render_icon_svg, search_icons

# Gemma should prefer semantic keys / typed registry, never a remote URL.
print(get_icon('equipment'))  # alias -> tool
print([item.key for item in search_icons('wafer')])
print(render_icon_svg('refresh', label='Refresh data')[:120])
