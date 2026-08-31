from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

@dataclass(frozen=True, slots=True)
class TableDefinition:
    key:str; public_name:str; purpose:str; use_when:tuple[str,...]; avoid_when:tuple[str,...]=()

_ITEMS={
 'data_table':TableDefinition('data_table','DataTable','General interactive enterprise data grid',('most tabular data','selection/filtering/export')),
 'server_data_table':TableDefinition('server_data_table','ServerDataTable','Server-driven grid for large datasets',('100k+ source rows','database-backed pagination')),
 'editable_table':TableDefinition('editable_table','EditableTable','Opt-in validated table editing',('small structured edits','admin maintenance'),('complex multi-field workflows',)),
 'master_detail_table':TableDefinition('master_detail_table','MasterDetailTable','Expand a record into rich contextual detail',('compact drilldown','nested process history')),
 'table_toolbar':TableDefinition('table_toolbar','TableToolbar','Canonical table search/columns/density/export/refresh controls',('interactive tables',)),
 'selection_bar':TableDefinition('selection_bar','TableSelectionBar','Bulk actions for selected rows',('multi-select actions',)),
}
TABLE_REGISTRY: Mapping[str,TableDefinition]=MappingProxyType(_ITEMS)
def get_table(key:str)->TableDefinition:
    if key not in TABLE_REGISTRY: raise KeyError(f'Unknown table pattern: {key}')
    return TABLE_REGISTRY[key]
__all__=['TableDefinition','TABLE_REGISTRY','get_table']
