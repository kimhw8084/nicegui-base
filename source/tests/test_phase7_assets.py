from pathlib import Path
from nicegui_base.visual import VISUAL_ROOT, ICON_REGISTRY, ILLUSTRATION_REGISTRY, validate_visual_package

def test_manifest_assets_exist():
    for item in ICON_REGISTRY.values(): assert (VISUAL_ROOT/item.path).exists()
    for item in ILLUSTRATION_REGISTRY.values(): assert (VISUAL_ROOT/item.path).exists()

def test_visual_package_is_safe():
    assert validate_visual_package()==[]

def test_no_remote_runtime_references():
    for p in VISUAL_ROOT.rglob('*.svg'):
        t=p.read_text().lower().replace('http://www.w3.org/2000/svg','')
        assert 'http://' not in t and 'https://' not in t
        assert '<script' not in t and 'javascript:' not in t
