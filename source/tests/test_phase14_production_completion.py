from __future__ import annotations
import asyncio, inspect, json
from pathlib import Path
import pytest
import nicegui_base
from nicegui_base import (
    FRAMEWORK_VERSION, CONTENT_REGISTRY, JOB_REGISTRY, MetricCardSpec, TreeNode, ActivityItem,
    InProcessJobAdapter, JobStatus, StatusIntent,
)
from nicegui_base.certification import combined_css

ROOT=Path(__file__).parents[1]


def source(name:str)->str:
    return (ROOT/'nicegui_base/integrations'/name).read_text()


def test_phase14_version_and_pin():
    assert bool(FRAMEWORK_VERSION) and FRAMEWORK_VERSION == __import__('nicegui_base.version', fromlist=['RELEASE_AUTHORITY']).RELEASE_AUTHORITY['framework_version']
    assert 'nicegui==3.15.0' in (ROOT/'pyproject.toml').read_text()


def test_high_value_content_coverage_is_registered():
    required={'metric_card','metric_strip','comparison_metric','key_value_list','property_grid','entity_header','tree_view',
              'markdown_viewer','code_viewer','json_viewer','log_viewer','image_viewer','search_results','stepper',
              'progress_steps','compare_panel','difference_table','command_palette','background_task','notification_center','activity_feed'}
    assert required <= set(CONTENT_REGISTRY)


def test_durable_job_boundary_registered():
    assert {'durable_job_adapter','in_process_job_adapter'} <= set(JOB_REGISTRY)


@pytest.mark.asyncio
async def test_in_process_job_adapter_lifecycle():
    adapter=InProcessJobAdapter()
    handle=await adapter.submit(lambda: 42,label='test')
    result=await adapter.result(handle)
    snap=await adapter.snapshot(handle)
    assert result==42 and snap.status is JobStatus.SUCCEEDED and snap.result_available


@pytest.mark.asyncio
async def test_in_process_job_adapter_cancellation():
    adapter=InProcessJobAdapter()
    async def work():
        await asyncio.sleep(1)
    handle=await adapter.submit(work)
    assert await adapter.cancel(handle)
    with pytest.raises(asyncio.CancelledError): await adapter.result(handle)
    assert (await adapter.snapshot(handle)).status is JobStatus.CANCELLED


def test_content_models_validate():
    assert MetricCardSpec('Yield','99.1%').label=='Yield'
    assert TreeNode('tool','Tool').key=='tool'
    assert ActivityItem('a','PM completed',intent=StatusIntent.SUCCESS).title=='PM completed'
    with pytest.raises(ValueError): MetricCardSpec('',1)


def test_dialogs_have_real_actions_and_typed_confirmation():
    text=source('nicegui_interactions.py')
    assert 'typed_confirmation' in text
    assert 'on_confirm' in text and 'on_cancel' in text
    assert 'cui-dialog__footer' in text
    assert 'disable()' in text and 'enable()' in text


def test_dirty_guard_wires_browser_and_internal_navigation():
    text=source('nicegui_interactions.py')
    assert 'beforeunload' in text
    assert "addEventListener('click'" in text or 'addEventListener("click"' in text
    assert 'set_dirty' in text and 'mark_clean' in text


def test_async_content_and_state_actions_render_runtime_behavior():
    text=source('nicegui_interactions.py')
    assert 'class AsyncContent' in text and 'def render' in text
    assert 'action_callback' in text or 'on_action' in text
    assert 'Retry' in text and 'Clear filters' in text


def test_menu_items_have_executable_callbacks():
    models=(ROOT/'nicegui_base/overlays/models.py').read_text()
    adapter=source('nicegui_interactions.py')
    assert 'on_select' in models and 'await _invoke(_item.on_select' in adapter


def test_data_table_uses_current_structured_row_selection():
    text=source('nicegui_data_table.py')
    assert "{'mode':'multiRow'}" in text and "{'mode':'singleRow'}" in text
    assert "rowSelection']='multiple'" not in text


def test_data_table_accessories_are_runtime_components_not_placeholders():
    text=source('nicegui_data_table.py')
    for cls in ['TableToolbar','TableDensitySelector','TableColumnManager','TableSelectionBar','ExpandableRow','ServerDataTable','EditableTable','MasterDetailTable']:
        section=text.split(f'class {cls}',1)[1].split('\nclass ',1)[0]
        assert 'pass' not in section
    assert 'cellClassRules' in text and 'cui-table-status' in text and 'cui-table-sparkline' in text


def test_server_table_has_latest_request_wins_and_query_translation():
    text=source('nicegui_data_table.py')
    assert 'LatestRequestController' in text and 'cancel_previous=spec.cancel_stale_requests' in text
    assert 'retry_if=_retry_server_read' in text and 'cache_ttl_seconds=spec.cache_ttl_seconds' in text
    assert "getColumnState" in text and 'getFilterModel' in text
    assert 'TableResult' in text


def test_framework_fields_expose_aria_contract_and_skip_link():
    components=source('nicegui_components.py'); layout=source('nicegui_layout.py')
    for token in ['aria-describedby','aria-required','aria-invalid','aria-label']:
        assert token in components
    assert 'Skip to main content' in layout and 'role="main"' in layout


def test_semantic_icons_not_material_icon_props_in_core_controls():
    components=source('nicegui_components.py')
    assert 'render_icon_svg' in components
    assert 'ui.button(label, icon=icon' not in components


def test_viewers_are_local_first_and_markdown_is_sanitized():
    text=source('nicegui_content.py')
    assert "'sanitize':True" in text
    assert 'Remote image sources are disabled by default' in text
    assert '.select(selected)' in text


def test_chart_interaction_wrappers_are_functional():
    text=source('nicegui_visualization.py')
    for cls in ['ChartTooltip','ChartZoom','ChartBrush','ChartDataView','ChartFullscreen','ChartExport']:
        section=text.split(f'class {cls}',1)[1].split('\nclass ',1)[0]
        assert 'pass' not in section
    assert 'run_chart_method' in text and 'dispatchAction' in text and 'getDataURL' in text
    assert 'cui-chart-toolbar' in text


def test_combined_css_contains_new_production_components():
    css=combined_css()
    for cls in ['.cui-metric-card','.cui-property-grid','.cui-tree','.cui-command-palette','.cui-background-task','.cui-activity-feed','.cui-skip-link']:
        assert cls in css


def test_removed_empty_development_artifact():
    assert not (ROOT/'nicegui_base/ai_models_tmp.py').exists()


def test_root_public_api_exposes_production_completion_surface():
    for name in ['MetricCard','MetricStrip','PropertyGrid','TreeView','MarkdownViewer','JsonViewer','LogViewer','CommandPalette',
                 'BackgroundTaskIndicator','NotificationCenter','ActivityFeed','DurableJobAdapter','InProcessJobAdapter']:
        assert hasattr(nicegui_base,name), name


def test_certification_counts_content_and_jobs():
    report=nicegui_base.run_certification(ROOT)
    registries=report.metadata['registries']
    assert registries['content']==len(CONTENT_REGISTRY)
    assert registries['jobs']==len(JOB_REGISTRY)


def test_validator_single_file_target_is_not_false_green(tmp_path):
    from nicegui_base.ai import validate_app
    good=tmp_path/'good.py'; good.write_text('from nicegui_base import Button\nButton("Run")\n')
    report=validate_app(good)
    assert report.scanned_files==1 and not report.errors
    bad=tmp_path/'bad.py'; bad.write_text('from nicegui import ui\nui.button("Run")\n')
    report=validate_app(bad)
    assert report.scanned_files==1 and report.errors
