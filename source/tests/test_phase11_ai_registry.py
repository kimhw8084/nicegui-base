from nicegui_base.ai import AI_CONSTRUCTION_REGISTRY, FRAMEWORK_REGISTRY_COUNTS, get_ai_construction, load_ai_manifest
from nicegui_base.version import FRAMEWORK_VERSION


def test_ai_registry_covers_major_construction_domains():
    expected = {'page_pattern','layout','component','form_filter_overlay','table','visualization','visual_asset','state_async','engineering','security_runtime'}
    assert expected <= set(AI_CONSTRUCTION_REGISTRY)
    for key in expected:
        item = get_ai_construction(key)
        assert item.preferred_api
        assert item.inspect_first
        assert item.prohibited_shortcut


def test_framework_registry_counts_are_substantial():
    assert FRAMEWORK_REGISTRY_COUNTS['components'] >= 30
    assert FRAMEWORK_REGISTRY_COUNTS['page_patterns'] == 10
    assert FRAMEWORK_REGISTRY_COUNTS['icons'] >= 140
    assert FRAMEWORK_REGISTRY_COUNTS['visualizations'] >= 20


def test_ai_manifest_contract():
    manifest = load_ai_manifest()
    assert manifest['framework_version'] == FRAMEWORK_VERSION
    assert manifest['nicegui_version'] == '3.15.0'
    assert manifest['validation_command'].startswith('python -m nicegui_base.validate')
    assert len(manifest['hard_prohibitions']) >= 8


def test_framework_catalog_machine_readable():
    from nicegui_base.ai import load_framework_catalog
    catalog = load_framework_catalog()
    assert catalog['framework_version'] == FRAMEWORK_VERSION
    assert len(catalog['registries']['icons']) >= 140
    assert len(catalog['registries']['page_patterns']) == 10
