"""Canonical semantic DataTable example for Gemma/OpenCode."""
from nicegui_base import ColumnKind, DataTable, PinPosition, SelectionMode, TableColumn

columns = (
    TableColumn('tool', 'Tool', pinned=PinPosition.LEFT),
    TableColumn('chamber', 'Chamber'),
    TableColumn('status', 'Status', ColumnKind.STATUS),
    TableColumn('yield_pct', 'Yield', ColumnKind.PERCENT, decimals=1),
    TableColumn('recipe', 'Recipe'),
)

rows = [
    {'id': 1, 'tool': 'ETCH-021', 'chamber': 'A', 'status': 'Critical', 'yield_pct': 94.8, 'recipe': 'RCP-713'},
]

# Inside a NiceGUI page:
# DataTable(rows, columns, title='Equipment health', selection=SelectionMode.MULTIPLE)
