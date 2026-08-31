"""NiceGUI Base semantic-layout example using only governed public components."""

from nicegui_base import (
    AxisSpec, AxisType, Breadcrumb, ColumnKind, DataExplorerPage, DataTable,
    DataTableSpec, FilterBar, FilterBarSpec, Icons, LayoutSlot, LineChart,
    MetricCard, MetricStrip, NavItem, NavigationModel, NavSection,
    NiceGUIRuntimeAdapter, RuntimeConfig, SeriesSpec, StatusIntent, TableColumn,
    TrendDirection,
)

navigation = NavigationModel((
    NavSection('workspace', 'Workspace', (
        NavItem('equipment', 'Equipment Health', '/equipment', icon=Icons.TOOL),
        NavItem('investigations', 'Investigations', '/investigations', icon=Icons.SEARCH),
    )),
    NavSection('operations', 'Operations', (
        NavItem('monitoring', 'Live Monitoring', '/monitoring', icon=Icons.CHART_LINE),
        NavItem('settings', 'Settings', '/settings', icon=Icons.SETTINGS),
    )),
))

_ROWS = (
    {'tool': 'ETCH-01', 'state': 'Running', 'affected_lots': 1},
    {'tool': 'ETCH-02', 'state': 'Watch', 'affected_lots': 3},
    {'tool': 'CVD-04', 'state': 'Running', 'affected_lots': 0},
)


def build_page() -> None:
    from nicegui_base import AppShell
    with AppShell('Process Intelligence', navigation, active_route='/equipment', environment='prod'):
        with DataExplorerPage(
            'Equipment Health',
            'Current excursion exposure and affected material.',
            breadcrumbs=(Breadcrumb('Manufacturing'), Breadcrumb('Equipment Health')),
        ) as page:
            with page.slot(LayoutSlot.FILTERS):
                with FilterBar(FilterBarSpec(title='Analysis filters')):
                    pass
            with page.slot(LayoutSlot.METRICS):
                with MetricStrip():
                    MetricCard('Affected lots', 4, intent=StatusIntent.WARNING, icon=Icons.LOT)
                    MetricCard('Critical tools', 1, intent=StatusIntent.WARNING, icon=Icons.TOOL)
                    MetricCard('Excursions', 2, delta='-1', trend=TrendDirection.DOWN, icon=Icons.EXCURSION)
                    MetricCard('Median response', '8 min', icon=Icons.CLOCK)
            with page.slot(LayoutSlot.PRIMARY):
                LineChart(
                    'Exposure trend',
                    (SeriesSpec('affected', 'Affected lots', (1, 2, 2, 4, 3), smooth=True),),
                    x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=('06:00', '09:00', '12:00', '15:00', '18:00')),
                )
            with page.slot(LayoutSlot.DATA):
                DataTable(
                    _ROWS,
                    spec=DataTableSpec(
                        title='Equipment state',
                        row_key='tool',
                        columns=(
                            TableColumn('tool', 'Tool'),
                            TableColumn('state', 'State', kind=ColumnKind.STATUS),
                            TableColumn('affected_lots', 'Affected lots', kind=ColumnKind.INTEGER),
                        ),
                    ),
                )


def main() -> None:
    NiceGUIRuntimeAdapter(RuntimeConfig('Process Intelligence', show_browser=False)).run(root=build_page)


if __name__ in {'__main__', '__mp_main__'}:
    main()
