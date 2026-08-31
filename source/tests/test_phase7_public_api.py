import nicegui_base as cui

def test_public_visual_api():
    for name in ['ICON_REGISTRY','ILLUSTRATION_REGISTRY','IconSize','get_icon','search_icons','render_icon_svg','validate_visual_package','SvgIcon','StateIllustration']:
        assert hasattr(cui,name), name
