from nicegui_base.visual import ICON_REGISTRY, ICON_ALIASES, ILLUSTRATION_REGISTRY, get_icon, search_icons

def test_large_semantic_coverage():
    assert len(ICON_REGISTRY) >= 110
    assert len(ILLUSTRATION_REGISTRY) >= 10
    assert len([i for i in ICON_REGISTRY.values() if i.domain=='semiconductor']) >= 28

def test_aliases_are_resolvable():
    assert get_icon('reload').key=='refresh'
    assert get_icon('equipment').key=='tool'
    assert get_icon('out-of-spec').key=='oos'

def test_search_domain():
    hits=search_icons('wafer',domain='semiconductor')
    assert {x.key for x in hits} >= {'wafer','wafer-map'}

def test_alias_targets_exist():
    assert all(v in ICON_REGISTRY for v in ICON_ALIASES.values())
