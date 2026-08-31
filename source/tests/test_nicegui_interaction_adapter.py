import inspect

from nicegui_base.integrations import nicegui_interactions


def test_adapter_does_not_import_nicegui_at_module_import_time():
    source = inspect.getsource(nicegui_interactions)
    assert 'from nicegui import ui' in source
    assert 'def _ui()' in source


def test_adapter_exposes_semantic_drawer_families():
    for name in ('DetailDrawer','FormDrawer','FilterDrawer','InspectorDrawer','ActivityDrawer','ResponsiveDrawer'):
        assert hasattr(nicegui_interactions, name)


def test_adapter_exposes_semantic_state_families():
    for name in ('EmptyState','NoResultsState','ErrorState','PermissionDeniedState','NotFoundState','OfflineState'):
        assert hasattr(nicegui_interactions, name)
