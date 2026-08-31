import nicegui_base as c

def test_cross_phase_public_surface_is_present():
    required=['AppShell','DataExplorerPage','Button','TextInput','FilterBar','DetailDrawer','DataTable','LineChart','Icons','AsyncAction','EngineeringEntityCard','AccessPolicy','validate_app','run_certification']
    for name in required: assert hasattr(c,name),name

def test_all_ten_patterns_remain_registered(): assert len(c.PATTERN_REGISTRY)==10

def test_major_registries_are_nonempty():
    for reg in [c.COMPONENT_REGISTRY,c.INTERACTION_REGISTRY,c.TABLE_REGISTRY,c.VISUALIZATION_REGISTRY,c.ENGINEERING_REGISTRY,c.CONVENIENCE_REGISTRY,c.SECURITY_REGISTRY,c.RUNTIME_REGISTRY]: assert len(reg)>0

def test_visual_vocabulary_remains_large():
    assert len(c.ICON_REGISTRY)>=140
    assert len(c.ILLUSTRATION_REGISTRY)>=10
