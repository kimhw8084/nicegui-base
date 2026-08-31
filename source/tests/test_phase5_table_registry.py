import pytest
from nicegui_base.data_table import TABLE_REGISTRY, get_table

def test_registry_has_required_patterns():
    assert {'data_table','server_data_table','editable_table','master_detail_table','table_toolbar','selection_bar'} <= set(TABLE_REGISTRY)

def test_get_table(): assert get_table('data_table').public_name=='DataTable'

def test_unknown_table():
    with pytest.raises(KeyError): get_table('does_not_exist')
