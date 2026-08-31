import nicegui_base

def test_phase5_public_surface_is_complete():
    expected={
      'DataTable','ServerDataTable','EditableTable','MasterDetailTable','TableColumn','TableToolbar','TableDensitySelector',
      'TableColumnManager','TableSelectionBar','TableRowActions','TableContextMenu','ExpandableRow','TablePresetSelector',
      'ConditionalCellFormatter','StatusCell','SparklineCell','DataTableSpec','ServerDataTableSpec','EditableTableSpec',
      'TableDensity','SelectionMode','PaginationMode','FilterOperator','TableQuery','TableResult','TableState','TablePreset',
      'apply_query','format_cell','export_csv','build_data_table_css','TABLE_REGISTRY'
    }
    missing=sorted(n for n in expected if not hasattr(nicegui_base,n)); assert not missing,missing
