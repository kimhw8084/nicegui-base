from __future__ import annotations

import ast
import io
import sys
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from nicegui_base.workbench.data_dock import DataDockFormat, DataDockModel, detect_format, parse_data
from nicegui_base.workbench.models import WorkbenchEntry, WorkbenchKind


ROOT = Path(__file__).resolve().parents[2]
PATTERN_KEYS = (
    'dashboard','data_explorer','master_detail','crud','monitoring',
    'search','settings','wizard','comparison','analysis_workspace',
)


def _pattern_entry(key: str) -> WorkbenchEntry:
    return WorkbenchEntry(
        f'pattern:{key}', WorkbenchKind.PATTERN, key.replace('_',' ').title(), f'{key} purpose',
        f'/studio/pattern%3A{key}', 'application pattern', tags=('pattern','starter'),
        source_authority='PATTERN_REGISTRY', live_preview=True, sample_data=True,
        metadata={'pattern_key':key,'reference_route':'/patterns/'+key.replace('_','-')},
    )


def test_data_dock_detects_excel_tsv_csv_and_json():
    assert detect_format('id\tvalue\nA\t1') is DataDockFormat.TSV
    assert detect_format('id,value\nA,1') is DataDockFormat.CSV
    assert detect_format('[{"id":"A","value":1}]') is DataDockFormat.JSON
    assert detect_format('id,value\nA,1', filename='rows.tsv') is DataDockFormat.TSV


def test_data_dock_parses_excel_paste_with_schema_and_roles():
    result = parse_data('id\tvalue\ttimestamp\ttool\nA\t1.2\t2026-08-31T08:00:00\tT1\nB\t2.4\t2026-08-31T08:01:00\tT2')
    assert result.ok
    assert result.snapshot.quality.rows == 2
    columns = {item.name:item for item in result.snapshot.columns}
    assert columns['id'].role == 'identifier'
    assert columns['value'].role == 'measurement'
    assert columns['timestamp'].role == 'timestamp'
    assert columns['tool'].role == 'entity'


def test_data_dock_malformed_input_is_controlled_not_exception():
    result = parse_data('{not valid json', format_hint='json')
    assert not result.ok
    assert result.issues
    assert any(issue.severity.value == 'error' for issue in result.issues)


def test_data_dock_rectangular_paste_and_undo_redo():
    model = DataDockModel(({'id':'A','x':1,'y':2},{'id':'B','x':3,'y':4}))
    model.rectangular_paste(0, 'x', '10\t20\n30\t40')
    assert model.rows[0]['x'] == 10 and model.rows[0]['y'] == 20
    assert model.rows[1]['x'] == 30 and model.rows[1]['y'] == 40
    assert model.can_undo
    model.undo()
    assert model.rows[0]['x'] == 1 and model.rows[1]['y'] == 4
    model.redo()
    assert model.rows[0]['x'] == 10 and model.rows[1]['y'] == 40


def test_data_dock_rename_type_and_role_validation():
    model = DataDockModel(({'id':'A','value':'1.5'},))
    model.rename_column('value','measurement')
    model.set_column_type('measurement','float')
    model.set_semantic_role('measurement','measurement')
    assert model.rows[0]['measurement'] == 1.5
    column = next(item for item in model.columns if item.name == 'measurement')
    assert column.inferred_type == 'float'
    assert column.role == 'measurement'
    with pytest.raises(ValueError):
        model.set_column_type('measurement','not-a-type')


def test_studio_contract_has_all_six_tabs_and_preview_controls():
    from nicegui_base.workbench.capability_studio import STUDIO_TABS, RESPONSIVE_WIDTHS
    assert STUDIO_TABS == ('preview','data','configure','states','interactions','inspect','code')
    assert set(RESPONSIVE_WIDTHS) == {'desktop','compact','tablet','phone'}
    source = (ROOT/'source/nicegui_base/workbench/capability_studio.py').read_text()
    assert 'data-theme="{session.config.theme}" data-density="{session.config.density}"' in source
    assert "{'comfortable':'Comfortable','compact':'Compact','dense':'Dense'}" in source
    assert 'Download example ZIP' in source


def test_state_matrix_contains_all_required_gate2_states():
    from nicegui_base.workbench.state_matrix import STATE_DEMOS
    states = {item.state.value for item in STATE_DEMOS}
    assert states == {'default','loading','empty','no_results','stale','partial','error','permission','disabled'}


def test_generated_minimal_and_production_code_are_valid_for_all_10_patterns():
    from nicegui_base.workbench.codegen import CapabilityConfiguration, minimal_code, production_code, validate_generated_code
    for key in PATTERN_KEYS:
        entry = _pattern_entry(key)
        config = CapabilityConfiguration(title='Fab App')
        minimal = minimal_code(entry, config)
        production = production_code(entry, config)
        ast.parse(minimal); ast.parse(production)
        assert validate_generated_code(minimal) == ()
        assert validate_generated_code(production) == ()
        assert 'company_ui' not in minimal + production
        assert 'from nicegui import ui' not in minimal + production


def test_codegen_fragment_is_deterministic_for_same_configuration():
    from nicegui_base.workbench.codegen import CapabilityConfiguration, starter_fragment
    entry = _pattern_entry('monitoring')
    config = CapabilityConfiguration(title='Tool Monitor', density='dense', responsive_width='tablet', theme='dark', options={'b':2,'a':1})
    assert starter_fragment(entry, config, data_columns=('tool','value')).to_json() == starter_fragment(entry, config, data_columns=('tool','value')).to_json()


def test_starter_zip_writer_is_byte_deterministic_with_canonical_scaffolder_stub(monkeypatch, tmp_path):
    from nicegui_base.workbench.codegen import generate_application_zip

    project = ModuleType('nicegui_base.ai.project')
    def create_application(root, *, name, template, recipe=None):
        root = Path(root); (root/'pages').mkdir(parents=True); (root/'.nicegui_base').mkdir(parents=True)
        (root/'app.py').write_text('from pages.home import build_page\n', encoding='utf-8')
        (root/'pages'/'home.py').write_text('def build_page():\n    pass\n', encoding='utf-8')
        (root/'nicegui_base.toml').write_text(f'name={name!r}\ntemplate={template!r}\n', encoding='utf-8')
        return SimpleNamespace(root=root)
    project.create_application = create_application
    monkeypatch.setitem(sys.modules, 'nicegui_base.ai.project', project)
    entry = _pattern_entry('monitoring')
    first = generate_application_zip(entry, app_name='Monitor')
    second = generate_application_zip(entry, app_name='Monitor')
    assert first == second
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert 'app.py' in archive.namelist()
        assert 'pages/home.py' in archive.namelist()
        assert '.nicegui_base/workbench_fragment.json' in archive.namelist()


def _install_recipe_shape_stubs(monkeypatch):
    class FieldType(str, Enum):
        STRING='string'; INTEGER='integer'; FLOAT='float'; BOOLEAN='boolean'; DATE='date'; DATETIME='datetime'; CATEGORY='category'; JSON='json'; UNKNOWN='unknown'
    class FieldRole(str, Enum):
        DIMENSION='dimension'; MEASUREMENT='measurement'; IDENTIFIER='identifier'; TIMESTAMP='timestamp'; ENTITY='entity'; ATTRIBUTE='attribute'
    @dataclass(frozen=True)
    class SemanticField:
        name: str
        type: FieldType = FieldType.UNKNOWN
        role: FieldRole = FieldRole.ATTRIBUTE
        nullable: bool = True
    @dataclass(frozen=True)
    class DataSchema:
        fields: tuple
        key: str = 'default'
        revision: str|None = None
        @property
        def names(self): return tuple(field.name for field in self.fields)

    models = ModuleType('nicegui_base.data_sources.models')
    for name, value in locals().copy().items():
        if name in {'FieldType','FieldRole','SemanticField','DataSchema'}: setattr(models,name,value)
    monkeypatch.setitem(sys.modules, 'nicegui_base.data_sources.models', models)

    class Requirement:
        def __init__(self,key,candidates,roles=(),required=True): self.key=key; self.candidates=tuple(candidates); self.roles=tuple(roles); self.required=required; self.description=''
    class Panel:
        def __init__(self,panel_id,fields,required=True): self.panel_id=panel_id; self.title=panel_id.title(); self.field_requirements=tuple(fields); self.required=required; self.surface_key=None; self.kind=SimpleNamespace(value='summary')
    recipe = SimpleNamespace(
        key='test-recipe',
        field_requirements=(Requirement('metric',('value',),(FieldRole.MEASUREMENT,),True), Requirement('sensor',('sensor',),(FieldRole.ENTITY,),False)),
        filters=(), panels=(Panel('required-panel',('metric',),True),Panel('optional-panel',('sensor',),False)),
    )
    sem = ModuleType('nicegui_base.semiconductor')
    sem.get_semiconductor_recipe=lambda key: recipe if key=='test-recipe' else (_ for _ in ()).throw(KeyError(key))
    def resolve(recipe_obj, schema, *, field_overrides=None, **kwargs):
        overrides=dict(field_overrides or {}); names=set(schema.names); bindings={}; missing_required=[]; missing_optional=[]
        for req in recipe_obj.field_requirements:
            chosen=overrides.get(req.key) or next((c for c in req.candidates if c in names),None)
            if chosen: bindings[req.key]=chosen
            elif req.required: missing_required.append(req.key)
            else: missing_optional.append(req.key)
        missing=set(missing_required)|set(missing_optional)
        available=[]; unavailable=[]
        for panel in recipe_obj.panels:
            (unavailable if any(f in missing for f in panel.field_requirements) else available).append(panel.panel_id)
        return SimpleNamespace(recipe_key=recipe_obj.key,bindings=bindings,missing_required=tuple(missing_required),missing_optional=tuple(missing_optional),available_filters=(),unavailable_filters=(),available_panels=tuple(available),unavailable_panels=tuple(unavailable))
    sem.resolve_recipe_source=resolve
    monkeypatch.setitem(sys.modules, 'nicegui_base.semiconductor', sem)
    return FieldRole


def test_recipe_mapping_blocks_required_fields_and_degrades_optional_panels(monkeypatch):
    _install_recipe_shape_stubs(monkeypatch)
    from nicegui_base.workbench.recipe_mapping import RecipeMappingModel
    missing = RecipeMappingModel('test-recipe', DataDockModel(({'id':'A'},)))
    result = missing.evaluate()
    assert not result.compatible
    assert result.missing_required == ('metric',)
    with pytest.raises(ValueError): missing.confirm()

    optional = RecipeMappingModel('test-recipe', DataDockModel(({'id':'A','value':1.2},)))
    result = optional.evaluate()
    assert result.compatible
    assert result.missing_optional == ('sensor',)
    assert 'required-panel' in result.available_panels
    assert 'optional-panel' in result.unavailable_panels
    optional.confirm()
    assert optional.confirmed


def test_builder_recommendations_are_explained_and_deterministic(monkeypatch):
    import nicegui_base.workbench.builder as builder
    pattern = _pattern_entry('monitoring')
    monkeypatch.setattr(builder, 'all_entries', lambda: (pattern,))
    model = builder.BuilderModel(goal='monitor tool health alerts', problem_type='generic application')
    first = model.pattern_recommendations()
    second = model.pattern_recommendations()
    assert first == second
    assert first and first[0].entry.key == pattern.key
    assert first[0].reasons
    model.select_pattern('monitoring')
    assert model.deterministic_signature() == model.deterministic_signature()


def test_app_registers_studio_data_and_builder_routes():
    source = (ROOT/'source/nicegui_base/workbench/app.py').read_text()
    assert "ui.page('/studio/{entry_key}')(studio_page)" in source
    assert "ui.page('/build')(build_page)" in source
    assert "ui.page('/workbench/data')(data_page)" in source
    assert 'render_builder()' in source
    assert 'render_data_dock(model)' in source


def test_no_deferred_iteration2_language_or_disabled_recipe_actions_remain():
    source = (ROOT/'source/nicegui_base/workbench/app.py').read_text()
    assert 'generation remains Iteration 2' not in source
    assert 'paste/upload/map/edit workflows are the next iteration' not in source
    assert "_standard_button('Use My Data', disabled=True)" not in source
    assert "_standard_button('Generate Starter', disabled=True)" not in source
    assert 'render_recipe_mapping' in source


def _framework_entry(registry: str, key: str, public_name: str) -> WorkbenchEntry:
    return WorkbenchEntry(
        f'framework:{registry}:{key}', WorkbenchKind.REFERENCE, public_name, f'{public_name} purpose',
        f'/studio/framework%3A{registry}%3A{key}', registry.replace('_',' '),
        source_authority=f'framework_catalog:{registry}', live_preview=True, sample_data=True,
        metadata={'registry_name':registry,'registry_key':key,'catalog_item':{'_registry_key':key,'public_name':public_name}},
    )


def test_editable_table_copy_production_uses_real_governed_constructor_contract():
    from nicegui_base.workbench.codegen import minimal_code, production_code, validate_generated_code
    entry = _framework_entry('tables','editable_table','EditableTable')
    minimal = minimal_code(entry)
    production = production_code(entry)
    assert 'render_catalog_example' in minimal
    assert "CAPABILITY_KEY = 'framework:tables:editable_table'" in minimal
    assert 'PageHeader' in minimal
    assert validate_generated_code(minimal) == ()
    assert validate_generated_code(production) == ()


def test_visualization_copy_production_uses_series_and_axis_contract():
    from nicegui_base.workbench.codegen import minimal_code, production_code, validate_generated_code
    entry = _framework_entry('visualizations','LineChart','LineChart')
    minimal = minimal_code(entry)
    assert 'render_catalog_example' in minimal and 'LineChart' in minimal
    assert validate_generated_code(minimal) == ()
    assert validate_generated_code(production_code(entry)) == ()


def test_unknown_constructor_signature_is_not_guessed():
    from nicegui_base.workbench.codegen import minimal_code
    entry = _framework_entry('content','some_future_view','FutureView')
    code = minimal_code(entry)
    assert "CAPABILITY_KEY = 'framework:content:some_future_view'" in code
    assert 'render_catalog_example' in code
    assert 'from nicegui_base import FutureView' not in code
    assert 'FutureView' in code


def test_data_backed_studio_registry_families_have_sample_mode_contract():
    from nicegui_base.workbench.capability_studio import is_data_backed, studio_session
    for registry, key, name in (
        ('tables','editable_table','EditableTable'),
        ('visualizations','LineChart','LineChart'),
        ('engineering','PopulationComparisonPanel','PopulationComparisonPanel'),
    ):
        entry = _framework_entry(registry,key,name)
        assert is_data_backed(entry)
        session = studio_session(entry)
        assert session.data.snapshot.quality.rows > 0
        assert session.data.snapshot.column_names


def test_state_matrix_controller_switches_without_background_work():
    from nicegui_base.workbench.state_matrix import StateMatrixController, StudioState
    controller = StateMatrixController()
    for state in StudioState:
        assert controller.select(state) is state
    assert controller.revision == len(tuple(StudioState))
    assert not hasattr(controller, 'task')
    assert not hasattr(controller, 'timer')


def test_responsive_preview_is_one_host_not_duplicate_shells():
    source = (ROOT/'source/nicegui_base/workbench/capability_studio.py').read_text()
    assert source.count('preview_host = ui.element(\'div\').classes(\'cui-studio-preview-frame cui-studio-first-example\')') == 1
    preview = source[source.index('def render_preview()'):source.index('with Tabs(')]
    assert 'preview_host.clear()' in preview
    assert '_shell(' not in preview and 'AppShell' not in preview


def test_recipe_copy_production_is_governed_composition_and_syntax_valid():
    from nicegui_base.workbench.codegen import production_code, validate_generated_code
    entry = WorkbenchEntry(
        'recipe:fdc-tool-health', WorkbenchKind.RECIPE, 'FdcToolHealth', 'Equipment health', '/recipes/fdc-tool-health',
        'semiconductor recipe', source_authority='SEMICONDUCTOR_RECIPE_REGISTRY', sample_data=True, live_preview=True,
        metadata={'recipe_key':'fdc-tool-health'},
    )
    code = production_code(entry)
    assert 'entries_by_key' in code
    assert "CAPABILITY_KEY = 'recipe:fdc-tool-health'" in code
    assert 'entry.source_authority' in code
    assert validate_generated_code(code) == ()


def test_all_10_pattern_starters_use_pattern_specific_information_hierarchy():
    from nicegui_base.workbench.codegen import minimal_code
    for key in PATTERN_KEYS:
        code = minimal_code(_pattern_entry(key))
        assert f"CAPABILITY_KEY = 'pattern:{key}'" in code
        assert 'render_catalog_example' in code
