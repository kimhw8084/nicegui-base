"""Canonical integrated application. Run in a NiceGUI 3.15.0 environment."""
from nicegui_base import (
    AppShell, DataExplorerPage, LayoutSlot, FilterBar, FilterBarSpec, FilterDefinition, FilterKind,
    DataTable, TableColumn, ColumnKind, SelectionMode, TableDensity,
    LineChart, SeriesSpec, AxisSpec, AxisType, SpecLimits,
)

def build_app():
    shell=AppShell('Equipment Health')
    with shell:
        with DataExplorerPage('Equipment Health','Integrated certification scenario') as page:
            with page.slot(LayoutSlot.FILTERS):
                FilterBar(FilterBarSpec(filters=(
                    FilterDefinition('area','Area',FilterKind.SELECT,options=('ETCH','CVD','CMP')),
                    FilterDefinition('tool','Tool',FilterKind.SELECT),
                    FilterDefinition('period','Period',FilterKind.DATE_RANGE),
                )))
            with page.slot(LayoutSlot.PRIMARY):
                LineChart('Excursions',(
                    SeriesSpec('excursions','Excursions',(2,5,3,8,4,6)),
                ),x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Mon','Tue','Wed','Thu','Fri','Sat')),
                   spec_limits=SpecLimits(upper=7))
            with page.slot(LayoutSlot.DATA):
                DataTable(
                    rows=(
                        {'id':'ETCH-021','status':'Critical','excursions':8,'yield':96.4},
                        {'id':'ETCH-014','status':'Watch','excursions':4,'yield':98.1},
                    ),
                    columns=(
                        TableColumn('id','Tool',ColumnKind.TEXT),
                        TableColumn('status','Status',ColumnKind.STATUS),
                        TableColumn('excursions','Excursions',ColumnKind.INTEGER),
                        TableColumn('yield','Yield',ColumnKind.PERCENT),
                    ),selection=SelectionMode.SINGLE,density=TableDensity.COMPACT,title='Affected equipment')
    return shell
