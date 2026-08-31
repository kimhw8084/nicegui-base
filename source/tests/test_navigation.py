import pytest

from nicegui_base.navigation import Breadcrumb, NavigationModel, NavItem, NavSection, TabSpec


def test_nav_item_requires_semantic_id_and_route_or_children():
    with pytest.raises(ValueError):
        NavItem('Bad ID', 'Bad', '/bad')
    with pytest.raises(ValueError):
        NavItem('empty', 'Empty')


def test_routes_must_be_absolute():
    with pytest.raises(ValueError):
        NavItem('tools', 'Tools', 'tools')
    with pytest.raises(ValueError):
        Breadcrumb('Tools', 'tools')


def test_nested_navigation_and_route_index():
    nav = NavigationModel((NavSection('analysis', 'Analysis', (
        NavItem('health', 'Equipment Health', '/health', icon='monitor_heart'),
        NavItem('rca', 'RCA', children=(NavItem('cases', 'Cases', '/rca/cases'),)),
    )),))
    assert set(nav.route_index()) == {'/health', '/rca/cases'}


def test_duplicate_routes_are_rejected_by_route_index():
    nav = NavigationModel((NavSection('a', None, (
        NavItem('one', 'One', '/same'), NavItem('two', 'Two', '/same'),
    )),))
    with pytest.raises(ValueError):
        nav.route_index()


def test_tab_validation_and_defaults():
    tab = TabSpec('overview', 'Overview')
    assert tab.lazy is True and tab.disabled is False
    with pytest.raises(ValueError):
        TabSpec('bad/tab', 'Bad')
    with pytest.raises(ValueError):
        TabSpec('valid', 'Valid', url_segment='nested/path')
