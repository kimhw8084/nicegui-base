from pathlib import Path

def test_adapter_uses_local_renderer_only():
    p=Path('nicegui_base/integrations/nicegui_visual_assets.py').read_text()
    assert 'render_icon_svg' in p and 'ui.html' in p
    assert 'http://' not in p and 'https://' not in p
