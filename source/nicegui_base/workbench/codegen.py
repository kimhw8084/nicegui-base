from __future__ import annotations

import ast
import io
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .models import WorkbenchEntry, WorkbenchKind


@dataclass(frozen=True, slots=True)
class CapabilityConfiguration:
    title: str | None = None
    density: str = 'compact'
    responsive_width: str = 'desktop'
    theme: str = 'system'
    options: Mapping[str, Any] = field(default_factory=dict)

    def normalized(self) -> dict[str, Any]:
        return {
            'title': self.title,
            'density': self.density,
            'responsive_width': self.responsive_width,
            'theme': self.theme,
            'options': {str(key): self.options[key] for key in sorted(self.options)},
        }


@dataclass(frozen=True, slots=True)
class StarterFragment:
    entry_key: str
    entry_kind: str
    route: str
    configuration: Mapping[str, Any]
    data_columns: tuple[str, ...] = ()
    recipe_key: str | None = None
    pattern_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'entry_key': self.entry_key,
            'entry_kind': self.entry_kind,
            'route': self.route,
            'configuration': dict(self.configuration),
            'data_columns': list(self.data_columns),
            'recipe_key': self.recipe_key,
            'pattern_key': self.pattern_key,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + '\n'


@dataclass(frozen=True, slots=True)
class CodeArtifact:
    minimal: str
    production: str
    fragment: StarterFragment
    cli_equivalent: str | None = None


_PATTERN_PAGE = {
    'dashboard': 'DashboardPage',
    'data_explorer': 'DataExplorerPage',
    'master_detail': 'MasterDetailPage',
    'crud': 'CrudPage',
    'monitoring': 'MonitoringPage',
    'search': 'SearchPage',
    'settings': 'SettingsPage',
    'wizard': 'WizardPage',
    'comparison': 'ComparisonPage',
    'analysis_workspace': 'AnalysisWorkspacePage',
}

_PATTERN_BASE_TEMPLATE = {
    'dashboard': 'dashboard',
    'data_explorer': 'data-explorer',
    'master_detail': 'analysis-workspace',
    'crud': 'crud',
    'monitoring': 'dashboard',
    'search': 'data-explorer',
    'settings': 'analysis-workspace',
    'wizard': 'analysis-workspace',
    'comparison': 'analysis-workspace',
    'analysis_workspace': 'analysis-workspace',
}


def _safe_identifier(text: str, fallback: str = 'GeneratedApp') -> str:
    words = re.findall(r'[A-Za-z0-9]+', text)
    name = ''.join(word[:1].upper() + word[1:] for word in words)
    if not name or not name[0].isalpha():
        name = fallback
    return name


def _entry_symbol(entry: WorkbenchEntry) -> str | None:
    payload = entry.metadata.get('catalog_item') if isinstance(entry.metadata, Mapping) else None
    if isinstance(payload, Mapping):
        for field in ('public_name', 'name'):
            value = payload.get(field)
            if isinstance(value, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
                return value
    key = str(entry.metadata.get('component_key') or '')
    if key:
        return ''.join(piece[:1].upper() + piece[1:] for piece in key.split('_'))
    return None


def _pattern_key(entry: WorkbenchEntry) -> str | None:
    value = entry.metadata.get('pattern_key') if isinstance(entry.metadata, Mapping) else None
    return str(value) if value else None


def _recipe_key(entry: WorkbenchEntry) -> str | None:
    value = entry.metadata.get('recipe_key') if isinstance(entry.metadata, Mapping) else None
    return str(value) if value else None


def _surface_key(entry: WorkbenchEntry) -> str | None:
    value = entry.metadata.get('surface_key') if isinstance(entry.metadata, Mapping) else None
    return str(value) if value else None


def starter_fragment(entry: WorkbenchEntry, config: CapabilityConfiguration | None = None, *, data_columns: Sequence[str] = ()) -> StarterFragment:
    config = config or CapabilityConfiguration()
    return StarterFragment(
        entry.key,
        entry.kind.value,
        entry.route,
        config.normalized(),
        tuple(str(column) for column in data_columns),
        recipe_key=_recipe_key(entry),
        pattern_key=_pattern_key(entry),
    )


def _minimal_for_pattern(entry: WorkbenchEntry, config: CapabilityConfiguration) -> str:
    key = _pattern_key(entry) or 'analysis_workspace'
    page = _PATTERN_PAGE.get(key, 'AnalysisWorkspacePage')
    title = config.title or entry.title
    common = (
        f"from nicegui_base import {page}, Button, DataTable, KeyValueItem, LayoutSlot, MetricCard, MetricStrip, PropertyGrid, SearchInput, TableColumn, TextInput\n\n"
        "ROWS = ({'id':'R-001','tool':'ETCH-01','value':10.2}, {'id':'R-002','tool':'ETCH-02','value':10.7})\n"
        "COLUMNS = (TableColumn('id','Record'), TableColumn('tool','Tool'), TableColumn('value','Value'))\n\n"
        "def _records() -> None:\n    DataTable(ROWS, COLUMNS, row_key='id', title='Records')\n\n"
        "def _summary() -> None:\n    with MetricStrip():\n        MetricCard('Records', len(ROWS))\n        MetricCard('Status', 'Ready')\n\n"
    )
    slots = {
        'dashboard': (
            "        with page.slot(LayoutSlot.METRICS):\n            _summary()\n"
            "        with page.slot(LayoutSlot.PRIMARY):\n            MetricCard('Primary signal', '10.7')\n"
        ),
        'data_explorer': (
            "        with page.slot(LayoutSlot.FILTERS):\n            SearchInput('Search records')\n"
            "        with page.slot(LayoutSlot.DATA):\n            _records()\n"
        ),
        'master_detail': (
            "        with page.slot(LayoutSlot.DATA):\n            _records()\n"
            "        with page.slot(LayoutSlot.DETAILS):\n            PropertyGrid((KeyValueItem('tool','Tool','ETCH-01'), KeyValueItem('value','Value',10.2)))\n"
        ),
        'crud': (
            "        with page.slot(LayoutSlot.ACTIONS):\n            Button('Add record')\n"
            "        with page.slot(LayoutSlot.DATA):\n            _records()\n"
        ),
        'monitoring': (
            "        with page.slot(LayoutSlot.METRICS):\n            _summary()\n"
            "        with page.slot(LayoutSlot.PRIMARY):\n            MetricCard('Health', 'Normal')\n"
        ),
        'search': (
            "        with page.slot(LayoutSlot.FILTERS):\n            SearchInput('Search')\n"
            "        with page.slot(LayoutSlot.DATA):\n            _records()\n"
        ),
        'settings': (
            "        with page.slot(LayoutSlot.NAVIGATION):\n            Button('General')\n"
            "        with page.slot(LayoutSlot.CONTENT):\n            TextInput('Application label', value='Operations')\n"
        ),
        'wizard': (
            "        with page.slot(LayoutSlot.CONTENT):\n            TextInput('Name')\n"
            "        with page.slot(LayoutSlot.ACTIONS):\n            Button('Continue')\n"
        ),
        'comparison': (
            "        with page.slot(LayoutSlot.PRIMARY):\n            with MetricStrip():\n                MetricCard('Baseline', '10.1')\n                MetricCard('Current', '10.7')\n"
        ),
        'analysis_workspace': (
            "        with page.slot(LayoutSlot.PRIMARY):\n            _records()\n"
            "        with page.slot(LayoutSlot.DETAILS):\n            MetricCard('Selected record', 'R-001')\n"
        ),
    }[key]
    return common + (
        "def build_page() -> None:\n"
        f"    with {page}({title!r}, {entry.description!r}) as page:\n"
        + slots
    )


def _minimal_for_analytic(entry: WorkbenchEntry, config: CapabilityConfiguration) -> str:
    key = _surface_key(entry) or entry.key.split(':')[-1]
    title = config.title or entry.title
    return (
        "from nicegui_base import AnalysisContext, SelectionBus, SemiconductorAnalyticalPanel\n\n"
        "CONTEXT = AnalysisContext(source_key='development')\n"
        "SELECTIONS = SelectionBus()\n\n"
        "def build_surface() -> None:\n"
        f"    with SemiconductorAnalyticalPanel({key!r}, CONTEXT, SELECTIONS, title={title!r}):\n"
        "        pass\n"
    )


def _minimal_for_recipe(entry: WorkbenchEntry, config: CapabilityConfiguration) -> str:
    key = _recipe_key(entry) or entry.key.split(':')[-1]
    return (
        "from nicegui_base import get_semiconductor_recipe\n\n"
        f"RECIPE = get_semiconductor_recipe({key!r})\n"
        "# Use create_semiconductor_recipe_runtime(...) with a governed DataSource to run it.\n"
    )


def _registry_name(entry: WorkbenchEntry) -> str:
    return str(entry.metadata.get('registry_name') or '') if isinstance(entry.metadata, Mapping) else ''


def _registry_key(entry: WorkbenchEntry) -> str:
    return str(entry.metadata.get('registry_key') or entry.metadata.get('component_key') or '') if isinstance(entry.metadata, Mapping) else ''


def _minimal_for_table(entry: WorkbenchEntry, config: CapabilityConfiguration) -> str:
    key = _registry_key(entry)
    title = config.title or entry.title
    if key == 'editable_table':
        return (
            "from nicegui_base import EditableTable, EditableTableSpec, SelectionMode, TableColumn\n\n"
            "ROWS = [\n"
            "    {'id':'R-001','tool':'ETCH-01','value':10.2},\n"
            "    {'id':'R-002','tool':'ETCH-02','value':10.7},\n"
            "]\n"
            "COLUMNS = (\n"
            "    TableColumn('id','Record'),\n"
            "    TableColumn('tool','Tool', editable=True),\n"
            "    TableColumn('value','Value', editable=True),\n"
            ")\n\n"
            "def validate_edit(row, key, value):\n"
            "    if key == 'value' and value in (None, ''):\n"
            "        return 'Value is required'\n"
            "    return None\n\n"
            "async def save_edit(row, key, value):\n"
            "    # Persist through your service boundary here.\n"
            "    return None\n\n"
            "def build_page() -> None:\n"
            f"    spec = EditableTableSpec(COLUMNS, row_key='id', title={title!r}, selection=SelectionMode.SINGLE, persist_state=True)\n"
            "    EditableTable(ROWS, COLUMNS, spec=spec, validate_edit=validate_edit, save_edit=save_edit)\n"
        )
    if key == 'server_data_table':
        return (
            "from nicegui_base import ServerDataTable, ServerDataTableSpec, TableColumn, TableQuery, TableResult\n\n"
            "COLUMNS = (TableColumn('id','Record'), TableColumn('value','Value'))\n\n"
            "async def fetch_page(query: TableQuery) -> TableResult:\n"
            "    # Delegate to a governed DataSource/service and honor query paging/filtering.\n"
            "    return TableResult(({'id':'R-001','value':10.2},), total=1, page=query.page, page_size=query.page_size)\n\n"
            "def build_page() -> None:\n"
            f"    spec = ServerDataTableSpec(COLUMNS, row_key='id', title={title!r})\n"
            "    ServerDataTable(COLUMNS, fetch=fetch_page, spec=spec)\n"
        )
    return (
        "from nicegui_base import DataTable, TableColumn\n\n"
        "ROWS = ({'id':'R-001','tool':'ETCH-01','value':10.2}, {'id':'R-002','tool':'ETCH-02','value':10.7})\n"
        "COLUMNS = (TableColumn('id','Record'), TableColumn('tool','Tool'), TableColumn('value','Value'))\n\n"
        "def build_page() -> None:\n"
        f"    DataTable(ROWS, COLUMNS, row_key='id', title={title!r})\n"
    )


def _minimal_for_visualization(entry: WorkbenchEntry, config: CapabilityConfiguration) -> str:
    key = _registry_key(entry)
    title = config.title or entry.title
    if key in {'WaferMap','WaferComparisonMap'}:
        if key == 'WaferComparisonMap':
            return (
                "from nicegui_base import WaferComparisonMap, WaferPoint\n\n"
                "AFFECTED = (WaferPoint(-1,0,10.4), WaferPoint(0,0,10.8), WaferPoint(1,0,11.1))\n"
                "CONTROL = (WaferPoint(-1,0,10.0), WaferPoint(0,0,10.1), WaferPoint(1,0,10.2))\n\n"
                f"def build_page() -> None:\n    WaferComparisonMap({title!r}, AFFECTED, CONTROL)\n"
            )
        return (
            "from nicegui_base import WaferMap, WaferPoint\n\n"
            "POINTS = (WaferPoint(-1,0,10.2), WaferPoint(0,0,10.5), WaferPoint(1,0,10.9))\n\n"
            f"def build_page() -> None:\n    WaferMap({title!r}, POINTS)\n"
        )
    if key == 'ParetoChart':
        return (
            "from nicegui_base import ParetoChart\n\n"
            f"def build_page() -> None:\n    ParetoChart({title!r}, ('Particle','Scratch','Other'), (42,21,8), (59.2,88.7,100.0))\n"
        )
    if key == 'RadialProfilePlot':
        return (
            "from nicegui_base import RadialProfilePlot\n\n"
            f"def build_page() -> None:\n    RadialProfilePlot({title!r}, (10.0,10.2,10.6,11.0), (10.0,10.1,10.2,10.3))\n"
        )
    symbol = key if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key) else 'LineChart'
    supported = {'AreaChart','BarChart','BoxPlot','ControlChart','DistributionPanel','DonutChart','Gauge','Heatmap','Histogram','LineChart','ScatterChart','StackedBarChart','TimelineChart'}
    if symbol not in supported:
        symbol = 'LineChart'
    return (
        f"from nicegui_base import AxisSpec, AxisType, SeriesSpec, {symbol}\n\n"
        "VALUES = (10.1, 10.4, 10.2, 10.8, 11.0)\n"
        "X = ('R1','R2','R3','R4','R5')\n\n"
        f"def build_page() -> None:\n    {symbol}({title!r}, (SeriesSpec('value','Value',VALUES),), x_axis=AxisSpec(kind=AxisType.CATEGORY, categories=X))\n"
    )


def _minimal_for_component_key(entry: WorkbenchEntry, config: CapabilityConfiguration) -> str | None:
    key = _registry_key(entry)
    title = config.title or entry.title
    templates = {
        'button': f"from nicegui_base import Button\n\ndef build_component() -> None:\n    Button({title!r})\n",
        'action_button': f"from nicegui_base import ActionButton\n\ndef build_component() -> None:\n    ActionButton({title!r})\n",
        'icon_button': "from nicegui_base import IconButton\n\ndef build_component() -> None:\n    IconButton('refresh', label='Refresh')\n",
        'select': f"from nicegui_base import Select\n\ndef build_component() -> None:\n    Select({title!r}, {{'a':'Option A','b':'Option B'}}, value='a')\n",
        'multi_select': f"from nicegui_base import MultiSelect\n\ndef build_component() -> None:\n    MultiSelect({title!r}, {{'a':'Option A','b':'Option B'}}, value=('a',))\n",
        'autocomplete': f"from nicegui_base import Autocomplete\n\ndef build_component() -> None:\n    Autocomplete({title!r}, {{'a':'Option A','b':'Option B'}}, value='a')\n",
        'combobox': f"from nicegui_base import Combobox\n\ndef build_component() -> None:\n    Combobox({title!r}, {{'a':'Option A','b':'Option B'}}, value='a')\n",
        'slider': f"from nicegui_base import Slider\n\ndef build_component() -> None:\n    Slider({title!r}, value=50)\n",
        'range_slider': f"from nicegui_base import RangeSlider\n\ndef build_component() -> None:\n    RangeSlider({title!r}, low=20, high=80)\n",
        'file_upload': "from nicegui_base import FileUpload\n\ndef build_component() -> None:\n    FileUpload(label='Upload data', accept=('.csv','.json'))\n",
        'button_group': "from nicegui_base import Button, ButtonGroup\n\ndef build_component() -> None:\n    with ButtonGroup():\n        Button('Run')\n        Button('Reset')\n",
        'split_button': "from nicegui_base import SplitButton\n\ndef build_component() -> None:\n    SplitButton('Export', {'CSV':lambda: None,'JSON':lambda: None})\n",
        'divider': "from nicegui_base import Divider\n\ndef build_component() -> None:\n    Divider()\n",
        'collapsible_panel': "from nicegui_base import CollapsiblePanel\n\ndef build_component() -> None:\n    with CollapsiblePanel('Advanced'):\n        pass\n",
        'accordion': "from nicegui_base import Accordion\n\ndef build_component() -> None:\n    with Accordion('Details'):\n        pass\n",
    }
    if key in templates:
        return templates[key]
    if key in {'checkbox','switch','text_input','number_input','textarea','search_input','date_picker','time_picker','datetime_picker','radio_group','checkbox_group'}:
        symbols = {
            'checkbox':'Checkbox','switch':'Switch','text_input':'TextInput','number_input':'NumberInput','textarea':'TextArea',
            'search_input':'SearchInput','date_picker':'DatePicker','time_picker':'TimePicker','datetime_picker':'DateTimePicker',
        }
        symbol = symbols.get(key)
        if symbol:
            return f"from nicegui_base import {symbol}\n\ndef build_component() -> None:\n    {symbol}({title!r})\n"
    return None


def _minimal_for_component(entry: WorkbenchEntry, config: CapabilityConfiguration) -> str:
    registry = _registry_name(entry)
    if registry == 'tables':
        return _minimal_for_table(entry, config)
    if registry == 'visualizations':
        return _minimal_for_visualization(entry, config)
    specialized = _minimal_for_component_key(entry, config)
    if specialized is not None:
        return specialized
    symbol = _entry_symbol(entry)
    title = config.title or entry.title
    if symbol:
        # Unknown signatures and export locations must not be guessed. Keep the snippet
        # import-safe and point at the packaged canonical catalog instead.
        return (
            "from nicegui_base import load_framework_catalog\n\n"
            f"CAPABILITY_KEY = {entry.key!r}\n"
            f"CAPABILITY_NAME = {symbol!r}\n"
            "CATALOG = load_framework_catalog()\n"
            f"# {title}: inspect the canonical Studio/reference for required constructor arguments before instantiation.\n"
        )
    return (
        "from nicegui_base.ai import load_framework_catalog\n\n"
        f"CAPABILITY_KEY = {entry.key!r}\n"
        "CATALOG = load_framework_catalog()\n"
    )


def minimal_code(entry: WorkbenchEntry, config: CapabilityConfiguration | None = None) -> str:
    config = config or CapabilityConfiguration()
    if entry.kind is WorkbenchKind.PATTERN:
        return _minimal_for_pattern(entry, config)
    if entry.kind is WorkbenchKind.ANALYTIC:
        return _minimal_for_analytic(entry, config)
    if entry.kind is WorkbenchKind.RECIPE:
        return _minimal_for_recipe(entry, config)
    return _minimal_for_component(entry, config)


def production_code(entry: WorkbenchEntry, config: CapabilityConfiguration | None = None) -> str:
    config = config or CapabilityConfiguration()
    body = minimal_code(entry, config)
    if entry.kind is WorkbenchKind.RECIPE:
        key = _recipe_key(entry) or entry.key.split(':')[-1]
        body = (
            "from nicegui_base import (\n"
            "    AnalysisContext, AnalysisWorkspacePage, InMemoryDataSource, LayoutSlot, MetricCard, MetricStrip,\n"
            "    NiceGUIWorkspace, RecipePanelKind, SelectionBus, SemiconductorAnalyticalPanel, WorkspaceController,\n"
            "    create_semiconductor_recipe_runtime, get_semiconductor_recipe,\n"
            ")\n\n"
            f"RECIPE = get_semiconductor_recipe({key!r})\n"
            "CONTEXT = AnalysisContext(source_key='application')\n"
            "SELECTIONS = SelectionBus()\n"
            "WORKSPACE = WorkspaceController()\n"
            "for panel in RECIPE.panels:\n"
            "    WORKSPACE.register_panel(panel.workspace_spec())\n\n"
            "ROWS = (\n"
            "    {'id':'M1','timestamp':'2026-08-31T08:00:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':-1.0,'y':0.0,'value':10.0,'sensor':'pressure','sensor_value':1.0,'bin':'PASS','count':95.0,'yield_pct':99.1,'category':'PASS','defect_class':'none'},\n"
            "    {'id':'M2','timestamp':'2026-08-31T08:01:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'B','lot':'L1','wafer':'W01','x':0.0,'y':0.0,'value':10.4,'sensor':'pressure','sensor_value':1.2,'bin':'B1','count':3.0,'yield_pct':98.7,'category':'B1','defect_class':'particle'},\n"
            ")\n\n"
            "async def prepare_runtime():\n"
            "    return await create_semiconductor_recipe_runtime(RECIPE.key, InMemoryDataSource('application', ROWS), context=CONTEXT, selections=SELECTIONS)\n\n"
            "def render_panel(panel) -> None:\n"
            "    if panel.kind is RecipePanelKind.ANALYTICAL:\n"
            "        with SemiconductorAnalyticalPanel(panel.surface_key, CONTEXT, SELECTIONS, title=panel.title, description=panel.description):\n"
            "            MetricCard('Surface', panel.surface_key.replace('_', ' '))\n"
            "    else:\n"
            "        MetricCard(panel.title, panel.kind.value.replace('_', ' ').title())\n\n"
            "def build_page() -> None:\n"
            "    with AnalysisWorkspacePage(RECIPE.application_name, RECIPE.purpose) as page:\n"
            "        with page.slot(LayoutSlot.PRIMARY):\n"
            "            with MetricStrip():\n"
            "                MetricCard('Recipe', RECIPE.application_name)\n"
            "                MetricCard('Panels', len(RECIPE.panels))\n"
            "            workspace = NiceGUIWorkspace(WORKSPACE)\n"
            "            for panel in RECIPE.panels:\n"
            "                workspace.add_panel(panel.workspace_spec(), lambda panel=panel: render_panel(panel))\n"
        )
    elif 'def build_page()' not in body:
        if 'def build_component()' in body:
            body += "\ndef build_page() -> None:\n    build_component()\n"
        elif 'def build_surface()' in body:
            body += "\ndef build_page() -> None:\n    build_surface()\n"
        else:
            body += "\ndef build_page() -> None:\n    # Constructor arguments remain capability-specific; use the Workbench Studio/reference.\n    pass\n"
    runtime = (
        "\nfrom nicegui_base import NiceGUIRuntimeAdapter, RuntimeConfig\n\n"
        "def runtime() -> NiceGUIRuntimeAdapter:\n"
        f"    return NiceGUIRuntimeAdapter(RuntimeConfig({_safe_identifier(config.title or entry.title)!r}, app_version='0.1.0', require_storage_secret=False, show_browser=False))\n\n"
        "def main() -> None:\n"
        "    runtime().run(root=build_page)\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    )
    return body.rstrip() + '\n' + runtime


def cli_equivalent(entry: WorkbenchEntry, *, app_name: str = 'My NiceGUI App') -> str | None:
    recipe = _recipe_key(entry)
    if recipe:
        return f'nicegui-base create ./my-app --name {json.dumps(app_name)} --template analysis-workspace --recipe {recipe}'
    pattern = _pattern_key(entry)
    if pattern:
        template = _PATTERN_BASE_TEMPLATE.get(pattern, 'analysis-workspace')
        return f'nicegui-base create ./my-app --name {json.dumps(app_name)} --template {template}'
    return None


def code_artifact(entry: WorkbenchEntry, config: CapabilityConfiguration | None = None, *, data_columns: Sequence[str] = ()) -> CodeArtifact:
    config = config or CapabilityConfiguration()
    return CodeArtifact(
        minimal_code(entry, config),
        production_code(entry, config),
        starter_fragment(entry, config, data_columns=data_columns),
        cli_equivalent(entry, app_name=config.title or 'My NiceGUI App'),
    )


def validate_generated_code(code: str) -> tuple[str, ...]:
    """Return deterministic source-contract findings for generated Python."""
    findings: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return (f'syntax:{exc.lineno}:{exc.msg}',)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    if not any(name == 'nicegui_base' or name.startswith('nicegui_base.') for name in imports):
        findings.append('missing_nicegui_base_import')
    if any(name == 'company_ui' or name.startswith('company_ui.') for name in imports):
        findings.append('deprecated_company_ui_import')
    if 'ui.' in code and 'nicegui import ui' in code:
        findings.append('raw_nicegui_primary_api')
    return tuple(findings)


def _zip_directory(root: Path) -> bytes:
    """Return byte-deterministic ZIP bytes for the same generated tree."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(root.rglob('*')):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.stat().st_mode & 0o111 else 0o644) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def generate_application_zip(
    entry: WorkbenchEntry,
    *,
    app_name: str,
    config: CapabilityConfiguration | None = None,
) -> bytes:
    """Generate a governed starter by delegating project ownership to create_application.

    The Workbench only replaces ``pages/home.py`` when a pattern has no direct canonical
    CLI template. The surrounding runtime, project gates and agent materials are always
    emitted by NiceGUI Base's existing project generator.
    """
    from nicegui_base.ai.project import create_application

    config = config or CapabilityConfiguration(title=app_name)
    recipe = _recipe_key(entry)
    pattern = _pattern_key(entry)
    template = 'analysis-workspace' if recipe else _PATTERN_BASE_TEMPLATE.get(pattern or '', 'analysis-workspace')
    with tempfile.TemporaryDirectory(prefix='nicegui-base-workbench-') as temp:
        root = Path(temp) / 'app'
        create_application(root, name=app_name, template=template, recipe=recipe)
        if pattern and pattern not in {'dashboard','data_explorer','crud','analysis_workspace'}:
            (root / 'pages' / 'home.py').write_text(_minimal_for_pattern(entry, config), encoding='utf-8')
        (root / '.nicegui_base' / 'workbench_fragment.json').write_text(starter_fragment(entry, config).to_json(), encoding='utf-8')
        return _zip_directory(root)


__all__ = [
    'CapabilityConfiguration','CodeArtifact','StarterFragment','cli_equivalent','code_artifact','generate_application_zip',
    'minimal_code','production_code','starter_fragment','validate_generated_code',
]
