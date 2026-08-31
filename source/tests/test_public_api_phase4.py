import nicegui_base


def test_phase4_public_surface_is_complete():
    expected = {
        'Form','FormField','FormSection','FormActions','ValidationSummary','DirtyStateGuard',
        'FilterBar','FilterChip','AdvancedFilterDrawer','FilterPresetSelector','SavedFilterView',
        'DetailDrawer','FormDrawer','FilterDrawer','InspectorDrawer','ActivityDrawer','ResponsiveDrawer',
        'Dialog','ConfirmDialog','DangerConfirmDialog','FormDialog','PreviewDialog','FullScreenDialog',
        'Tooltip','Popover','DropdownMenu','ActionMenu','ContextMenu','Toast','Alert','Banner','ValidationMessage',
        'ProgressBar','Spinner','Skeleton','AsyncContent','EmptyState','NoResultsState','ErrorState',
        'PermissionDeniedState','NotFoundState','OfflineState','build_interaction_css',
    }
    missing = sorted(name for name in expected if not hasattr(nicegui_base, name))
    assert not missing, missing
