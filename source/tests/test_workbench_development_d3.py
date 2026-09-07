from __future__ import annotations

import asyncio
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest


ROWS = (
    {'id': '0000', 'thickness': 0.125, 'batch': 'A', 'note': 'alpha'},
    {'id': '0001', 'thickness': 1.125, 'batch': 'B', 'note': 'alpha'},
    {'id': '0002', 'thickness': 2.125, 'batch': 'A', 'note': 'beta'},
    {'id': '0003', 'thickness': 3.125, 'batch': 'B', 'note': 'gamma'},
)

SCHEMA = (
    {'name': 'id', 'inferred_type': 'string', 'role': 'identifier', 'nullable': False, 'confidence': 1.0},
    {'name': 'thickness', 'inferred_type': 'float', 'role': 'measurement', 'nullable': False, 'confidence': 1.0},
    {'name': 'batch', 'inferred_type': 'category', 'role': 'dimension', 'nullable': False, 'confidence': 1.0},
    {'name': 'note', 'inferred_type': 'string', 'role': 'attribute', 'nullable': False, 'confidence': 1.0},
)


def _project(rows=ROWS, schema=SCHEMA, **extra):
    return {
        'name': 'D3 Semiconductor Explorer',
        'goal': 'Explore and filter measurement records',
        'pattern_key': 'data_explorer',
        'data_rows': list(rows),
        'data_schema': list(schema),
        'data_handoff_mode': 'include_development_rows',
        **extra,
    }


def test_measurement_resolution_uses_confirmed_semantics_and_preserves_null_alignment():
    from nicegui_base.workbench.preview_data import numeric_data, resolve_measurement_field

    rows = [
        {'id': 7, 'thickness': 0.125},
        {'id': 8, 'thickness': None},
        {'id': 9, 'thickness': 2.125},
    ]
    assert resolve_measurement_field(rows, schema=SCHEMA[:2]) == 'thickness'
    assert numeric_data(rows, schema=SCHEMA[:2]) == ('thickness', (0.125, None, 2.125))


def test_measurement_mapping_rejects_ambiguity_invalid_overrides_booleans_and_nonfinite_values():
    from nicegui_base.workbench.preview_data import numeric_data

    partial_schema = ({**SCHEMA[1], 'role': 'attribute'},)
    assert numeric_data(
        [{'record_id': 11, 'thickness': 0.125}, {'record_id': 12, 'thickness': 1.125}],
        schema=partial_schema,
    ) == ('thickness', (0.125, 1.125))
    ambiguous = [{'id': 'a', 'first': 1.0, 'second': 2.0}]
    with pytest.raises(ValueError, match='ambiguous'):
        numeric_data(ambiguous)
    with pytest.raises(ValueError, match='does not exist'):
        numeric_data(ROWS, field='missing')
    with pytest.raises(ValueError, match='boolean'):
        numeric_data([{'id': 'a', 'thickness': True}], field='thickness')
    with pytest.raises(ValueError, match='finite'):
        numeric_data([{'id': 'a', 'thickness': float('inf')}], field='thickness')
    assert numeric_data(ROWS, field='thickness', measurement_field='id')[0] == 'thickness'


def test_actual_chart_series_uses_thickness_values_and_keeps_257_row_endpoints():
    from nicegui_base.workbench.visual_specimens import visualization_data

    rows = tuple({'id': f'{index:04d}', 'thickness': index + 0.125} for index in range(257))
    field, labels, values = visualization_data(rows, schema=SCHEMA[:2])
    assert field == 'thickness'
    assert labels[0] == '0000' and labels[-1] == '0256'
    assert values[0] == 0.125 and values[-1] == 256.125
    assert len(values) == len(rows)


def test_handoff_confirms_identifier_measurement_and_category_without_numeric_id_fallback():
    from nicegui_base.workbench.data_handoff import build_data_handoff_plan

    plan = build_data_handoff_plan(_project())
    assert plan.row_key == 'id'
    assert plan.measurement_field == 'thickness'
    assert plan.category_field == 'batch'
    assert tuple(row['id'] for row in plan.fixture_rows) == ('0000', '0001', '0002', '0003')

    explicit = build_data_handoff_plan(_project(
        schema=(
            SCHEMA[0],
            {**SCHEMA[1], 'name': 'width'},
            {**SCHEMA[1], 'name': 'thickness'},
        ),
        data_rows=[{'id': 'a', 'width': 1.0, 'thickness': 2.0}],
        measurement_field='thickness',
    ))
    assert explicit.measurement_field == 'thickness'

    with pytest.raises(ValueError, match='Choose one measurement'):
        build_data_handoff_plan(_project(
            schema=(
                SCHEMA[0],
                {**SCHEMA[1], 'name': 'width'},
                {**SCHEMA[1], 'name': 'thickness'},
            ),
            data_rows=[{'id': 'a', 'width': 1.0, 'thickness': 2.0}],
        ))


def test_generated_renderers_receive_the_generated_measurement_and_schema_contracts():
    from nicegui_base.workbench.catalog_runtime import entries_by_key
    from nicegui_base.workbench.project_codegen import project_home_code

    entry = entries_by_key()['framework:visualizations:LineChart']
    code = project_home_code({
        **_project(),
        'placements': {'primary': [entry.key], 'data': []},
        'capability_configurations': {},
    }, {entry.key: entry})
    assert 'schema=DATA_SCHEMA' in code
    assert 'measurement_field=MEASUREMENT_FIELD' in code
    assert 'category_field=CATEGORY_FIELD' in code
    assert 'filter_state=FILTER_STATE' in code


def test_shared_provider_query_uses_analysis_context_for_combined_filters_search_clear_and_isolation():
    from nicegui_base import AnalysisContext, Comparison, ComparisonOperator, InMemoryDataSource
    from nicegui_base.workbench.provider_preview import query_provider
    from nicegui_base.workbench.visual_specimens import visualization_data

    async def scenario():
        source = InMemoryDataSource('d3', ROWS)
        first = AnalysisContext(source_key='page-one')
        second = AnalysisContext(source_key='page-two')

        async def linked(context):
            result = await query_provider(source, context)
            if result.rows:
                field, labels, values = visualization_data(
                    result.rows, schema=SCHEMA, measurement_field='thickness', category_field='id',
                )
                return result, field, labels, values
            return result, None, (), ()

        first.set_filters((Comparison('batch', ComparisonOperator.EQ, 'A'),))
        result, field, labels, values = await linked(first)
        assert result.filtered_total == 2 and [row['id'] for row in result.rows] == ['0000', '0002']
        assert field == 'thickness' and labels == ('0000', '0002') and values == (0.125, 2.125)

        first.clear_filters()
        first.set_search('alpha')
        result, field, labels, values = await linked(first)
        assert result.filtered_total == 2 and [row['id'] for row in result.rows] == ['0000', '0001']
        assert field == 'thickness' and labels == ('0000', '0001') and values == (0.125, 1.125)

        first.set_filters((Comparison('batch', ComparisonOperator.EQ, 'A'),))
        result, field, labels, values = await linked(first)
        assert result.filtered_total == 1 and [row['id'] for row in result.rows] == ['0000']
        assert field == 'thickness' and labels == ('0000',) and values == (0.125,)

        first.clear_filters()
        first.set_search('')
        result, field, labels, values = await linked(first)
        assert result.filtered_total == 4 and [row['id'] for row in result.rows] == ['0000', '0001', '0002', '0003']
        assert field == 'thickness' and labels == ('0000', '0001', '0002', '0003') and values == (0.125, 1.125, 2.125, 3.125)

        first.set_search('does-not-match')
        empty, field, labels, values = await linked(first)
        assert empty.filtered_total == 0 and empty.rows == () and field is None and labels == () and values == ()
        assert [row['id'] for row in (await query_provider(source, second)).rows] == ['0000', '0001', '0002', '0003']
        assert tuple(ROWS) == ROWS

    asyncio.run(scenario())


def test_provider_query_controller_drops_stale_completion_and_disposes():
    from nicegui_base import AnalysisContext, InMemoryDataSource
    from nicegui_base.workbench.provider_preview import ProviderQueryController

    class DelayedSource(InMemoryDataSource):
        async def query(self, query=...):
            await asyncio.sleep(0.03 if query.search == 'old' else 0.001)
            return await super().query(query)

    async def scenario():
        source = DelayedSource('d3-delayed', ROWS)
        context = AnalysisContext(source_key='page-one')
        controller = ProviderQueryController(source, debounce_seconds=0)
        context.set_search('old')
        async with asyncio.TaskGroup() as tasks:
            old = tasks.create_task(controller.load(context))
            await asyncio.sleep(0.005)
            context.set_search('alpha')
            new = tasks.create_task(controller.load(context))
        assert [row['id'] for row in new.result().rows] == ['0000', '0001']
        assert old.result() is None
        await controller.aclose()
        assert controller.closed

    asyncio.run(scenario())


def test_provider_choices_are_bounded_and_clear_preserves_live_resetters():
    from nicegui_base import AnalysisContext
    from nicegui_base.workbench.provider_preview import _bounded_choice_map, _reset_filter_state

    labels, raw, truncated = _bounded_choice_map(tuple(f'B{index}' for index in range(101)))
    assert truncated and len(raw) == 100 and '' in labels
    context = AnalysisContext(source_key='page-one')
    calls = []
    state = {'field': object(), '__resetters__': [lambda: calls.append('reset')]}
    _reset_filter_state(context, state)
    assert state['__resetters__'] and calls == ['reset'] and context.search == '' and context.filters == ()


def test_builder_review_summary_is_bounded_and_detail_is_lazy_in_rendering_source():
    from nicegui_base.workbench.builder import BuilderModel
    import nicegui_base.workbench.builder as builder

    model = BuilderModel()
    model.apply_golden_starter('record-manager')
    model.data.replace_rows([{'id': f'{index:04d}', 'value': float(index)} for index in range(5000)])
    summary = model.review_summary()
    detail = model.review_data_details(limit=20)
    assert 'data_rows' not in summary
    assert summary['data']['rows'] == 5000
    assert len(detail['rows']) == 20
    assert detail['total_rows'] == 5000
    source = Path(builder.__file__).read_text(encoding='utf-8')
    assert 'review_summary()' in source
    assert 'review_data_details' in source
    assert "ui.element('details')" in source


def test_studio_zip_materializes_mapping_and_keeps_actual_fixture_series_source():
    from nicegui_base.workbench.catalog_runtime import entries_by_key
    from nicegui_base.workbench.codegen import CapabilityConfiguration, generate_application_zip

    entry = entries_by_key()['framework:visualizations:LineChart']
    payload = generate_application_zip(
        entry,
        app_name='D3 Studio Chart',
        config=CapabilityConfiguration(title='D3 Studio Chart'),
        rows=ROWS,
        data_schema=SCHEMA,
        data_mode='include_development_rows',
    )
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        app_data = archive.read('services/app_data.py').decode()
        home = archive.read('pages/home.py').decode()
        assert 'MEASUREMENT_FIELD' in app_data and 'DATA_SCHEMA' in app_data
        assert 'services/provider_config.py' in archive.namelist()
        assert '.nicegui_base/provider_contract.json' in archive.namelist()
        assert 'measurement_field=MEASUREMENT_FIELD' in home
        assert 'thickness' in home and '3.125' in home


def test_standalone_theme_bootstrap_does_not_enter_nicegui_script_mode():
    # nicegui-base: allow-AI001
    from nicegui import core
    from nicegui_base import NiceGUIThemeAdapter

    core.reset()
    assert not core.script_mode
    NiceGUIThemeAdapter().install()
    assert not core.script_mode


def test_builder_zip_uses_the_same_data_contract_and_page_owned_provider_context():
    from nicegui_base.workbench.catalog_runtime import entries_by_key
    from nicegui_base.workbench.project_codegen import generate_project_zip

    keys = entries_by_key()
    line = 'framework:visualizations:LineChart'
    table = 'framework:tables:data_table'
    search = 'component:search_input'
    select = 'component:select'
    payload, smoke = generate_project_zip({
        **_project(),
        'name': 'D3 Builder Chart',
        'placements': {'filters': [search, select], 'primary': [line], 'data': [table]},
        'capability_configurations': {
            line: {'title': 'D3 Builder Chart', 'options': {'measurement': 'thickness', 'label_field': 'id'}},
            select: {'options': {'filter_field': 'batch'}},
        },
    }, keys)
    assert smoke.ok
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        home = archive.read('pages/home.py').decode()
        contract = json.loads(archive.read('.nicegui_base/data_contract.json'))
        assert contract['measurement_field'] == 'thickness'
        assert 'AnalysisContext' in home and 'render_provider_capability' in home
        assert 'measurement_field=MEASUREMENT_FIELD' in home and 'filter_state=FILTER_STATE' in home


def test_generated_app_data_series_has_no_index_fallback_for_invalid_measurements():
    from nicegui_base.workbench.data_handoff import materialize_data_handoff

    project = _project(rows=[{'id': '0000', 'thickness': 0.125}], schema=SCHEMA[:2])
    # The generated source is inspected without retaining fixture state in the repo.
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        manifest, _, _ = materialize_data_handoff(Path(directory), project, require_measurement=True)
        source = (Path(directory) / 'services' / 'app_data.py').read_text(encoding='utf-8')
        assert manifest['measurement_field'] == 'thickness'
        series_source = source.split('def series_values', 1)[1].split('__all__', 1)[0]
        assert 'values.append(float(index + 1))' not in series_source
        assert 'non-finite' in source and 'boolean data' in source


def test_chart_data_alternative_is_discoverable_bounded_and_full_data_view_retains_series():
    from nicegui_base import ChartDataView
    from nicegui_base.visualization.css import build_visualization_css

    source = Path(__file__).resolve().parents[1] / 'nicegui_base/integrations/nicegui_visualization.py'
    text = source.read_text(encoding='utf-8')
    css = build_visualization_css()
    assert "ui.element('details').classes('cui-chart-data-disclosure')" in text
    assert 'aria-label="Chart data alternative"' in text
    assert '.cui-chart-data-disclosure__scroll' in css and 'max-height:240px' in css
    view = ChartDataView(SimpleNamespace(series=(SimpleNamespace(label='thickness', data=tuple(range(257))),)))
    assert len(view.rows()) == 257


def test_workbench_catalog_health_is_complete_for_ready_state():
    from nicegui_base.workbench.catalog import framework_catalog_audit

    audit = framework_catalog_audit()
    assert audit.complete, audit
    assert audit.declared == audit.identified == audit.canonical_total == audit.visible == 450
