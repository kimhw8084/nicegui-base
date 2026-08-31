from nicegui_base.layouts import ContentWidth, LayoutSlot
from nicegui_base.patterns import PATTERN_REGISTRY, PagePattern, get_pattern


def test_all_canonical_patterns_exist():
    assert set(PATTERN_REGISTRY) == set(PagePattern)
    assert len(PATTERN_REGISTRY) == 10


def test_data_explorer_order_is_predictable():
    p = get_pattern(PagePattern.DATA_EXPLORER)
    assert p.slot_order.index(LayoutSlot.FILTERS) < p.slot_order.index(LayoutSlot.DATA)
    assert p.slot_order.index(LayoutSlot.PRIMARY) < p.slot_order.index(LayoutSlot.DATA)
    assert p.content_width is ContentWidth.WIDE


def test_workspace_is_full_width():
    assert get_pattern('analysis_workspace').content_width is ContentWidth.FULL


def test_every_pattern_has_explicit_responsive_behavior():
    for p in PATTERN_REGISTRY.values():
        assert p.desktop_behavior.strip()
        assert p.tablet_behavior.strip()
        assert p.phone_behavior.strip()


def test_every_pattern_has_header_context():
    for p in PATTERN_REGISTRY.values():
        assert LayoutSlot.HEADER in p.required_slots or LayoutSlot.HEADER in p.optional_slots


def test_semantic_page_classes_expose_allowed_slots_without_rendering():
    from nicegui_base.patterns import DataExplorerPage, WizardPage
    explorer = DataExplorerPage('Test')
    wizard = WizardPage('Test')
    assert LayoutSlot.DATA in explorer.allowed_slots
    assert LayoutSlot.DATA not in wizard.allowed_slots
