import nicegui_base


def test_phase2_public_api_imports_without_nicegui_installed():
    expected = [
        'AppShell', 'AppHeader', 'AppSidebar', 'MobileNavigationDrawer', 'UserMenu',
        'Page', 'PageHeader', 'Section', 'Stack', 'Grid', 'ResponsiveGrid', 'DashboardGrid',
        'MasterDetailLayout', 'SplitPane', 'ResizablePanel', 'ScrollablePanel', 'StickyPanel',
        'FullScreenWorkspace', 'PagePattern', 'NavigationModel', 'Tabs', 'SegmentedControl',
        'DashboardPage', 'DataExplorerPage', 'MasterDetailPage', 'CrudPage', 'MonitoringPage',
        'SearchPage', 'SettingsPage', 'WizardPage', 'ComparisonPage', 'AnalysisWorkspacePage',
    ]
    for name in expected:
        assert hasattr(nicegui_base, name), name
