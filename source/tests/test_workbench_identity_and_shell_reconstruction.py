from __future__ import annotations


def test_access_key_identity_uses_account_initials_and_department(monkeypatch):
    from nicegui_base.workbench.identity import resolve_explorer_identity

    monkeypatch.setenv('AccessKey', 'haewon.kim')
    monkeypatch.setenv('DEPARTMENT', 'Semiconductor Engineering')
    identity = resolve_explorer_identity()
    assert identity.access_key == 'haewon.kim'
    assert identity.initials == 'HK'
    assert identity.role == 'Member'
    assert identity.department == 'Semiconductor Engineering'
    assert not identity.account_missing


def test_missing_access_key_is_safe_and_deterministic(monkeypatch):
    from nicegui_base.workbench.identity import resolve_explorer_identity

    monkeypatch.delenv('AccessKey', raising=False)
    monkeypatch.delenv('DEPARTMENT', raising=False)
    identity = resolve_explorer_identity()
    assert identity.access_key == 'Member'
    assert identity.initials == 'M'
    assert identity.role == 'Member'
    assert identity.department == 'Department unavailable'
    assert identity.account_missing and identity.department_missing


def test_identity_sanitizes_display_and_limits_initials(monkeypatch):
    from nicegui_base.workbench.identity import initials_for_access_key, resolve_explorer_identity

    assert initials_for_access_key('one.two-three four') == 'OF'
    assert initials_for_access_key('operator') == 'O'
    monkeypatch.setenv('AccessKey', '  alice-bob  ')
    identity = resolve_explorer_identity()
    assert '/' not in identity.access_key
    assert identity.initials == 'AB'


def test_reference_shell_promotes_settings_and_keeps_legacy_aliases():
    from nicegui_base.workbench.app import workbench_navigation

    items = tuple(item for section in workbench_navigation().sections for item in section.items)
    routes = {item.route for item in items}
    labels = {item.label for item in items}
    assert '/settings' in routes
    assert 'Settings' in labels
    assert '/quality' not in routes
    source = __import__('pathlib').Path(__file__).parents[1].joinpath('nicegui_base/workbench/app.py').read_text()
    assert "ui.page('/patterns/settings')(_settings_compatibility_page)" in source
    assert "ui.page('/layouts')(layout_studio_page)" in source
    assert "ui.page('/applications')(applications_page)" in source
