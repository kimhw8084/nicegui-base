import pytest
from nicegui_base.data_table import (
    ColumnKind, DataTableSpec, EditableTableSpec, FilterOperator, FilterSpec, PaginationMode, PinPosition,
    SelectionMode, ServerDataTableSpec, SortDirection, SortSpec, TableColumn, TableDensity, TablePreset, TableQuery, TableState,
)

def cols():
    return (TableColumn('tool','Tool'), TableColumn('yield','Yield',ColumnKind.PERCENT,align='right',decimals=1))

def test_column_requires_key():
    with pytest.raises(ValueError): TableColumn('','Tool')

def test_column_min_width():
    with pytest.raises(ValueError): TableColumn('a','A',min_width=20)

def test_column_width_respects_min():
    with pytest.raises(ValueError): TableColumn('a','A',width=70,min_width=80)

def test_numeric_alignment_default():
    assert TableColumn('x','X',ColumnKind.FLOAT).effective_align == 'right'

def test_status_alignment_default():
    assert TableColumn('x','X',ColumnKind.STATUS).effective_align == 'center'

def test_spec_requires_columns():
    with pytest.raises(ValueError): DataTableSpec(())

def test_duplicate_column_keys_rejected():
    with pytest.raises(ValueError): DataTableSpec((TableColumn('x','X'),TableColumn('x','Y')))

def test_persistence_key_generated():
    assert DataTableSpec(cols(),title='Tools').persist_key == 'table:Tools'

def test_master_detail_implies_expandable():
    assert DataTableSpec(cols(),master_detail=True).expandable

def test_server_mode_default():
    assert ServerDataTableSpec(cols()).pagination is PaginationMode.SERVER

def test_edit_save_mode_validation():
    with pytest.raises(ValueError): EditableTableSpec(cols(),save_mode='page')

def test_query_page_validation():
    with pytest.raises(ValueError): TableQuery(page=0)

def test_state_persisted_includes_v2_selection_identity_for_resume_contract():
    s=TableState(selected_keys={1,2}, density=TableDensity.DENSE, visible_columns=['tool'])
    out=s.to_persisted()
    assert set(out['selected_keys'])=={1,2} and out['density']=='dense' and out['version']==2

def test_preset_can_hold_sort_filter():
    p=TablePreset('Critical',sorts=(SortSpec('yield',SortDirection.ASC),),filters=(FilterSpec('status',FilterOperator.EQUALS,'Critical'),))
    assert p.name == 'Critical'
