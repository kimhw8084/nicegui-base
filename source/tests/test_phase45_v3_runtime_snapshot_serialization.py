from __future__ import annotations

import json

import pytest

from nicegui_base import Aggregation, ApplicationRuntime, Dataset, Dimension, FilterClause, FilterOperation, Metric, StateKey
from nicegui_base.runtime import deserialize_application_snapshot, serialize_application_snapshot
from nicegui_base.workspace import PanelSpec

pytestmark = pytest.mark.asyncio


async def test_v3_application_snapshot_json_roundtrip_restores_runtime_state_layout_and_data_sessions():
    runtime = ApplicationRuntime()
    runtime.data.register(Dataset(
        'd',
        ({'id': 1, 'region': 'APAC', 'value': 10}, {'id': 2, 'region': 'US', 'value': 20}),
        row_key='id', dimensions=(Dimension('region'),), metrics=(Metric('value', aggregation=Aggregation.SUM),),
    ))
    app_key = StateKey[str]('tenant', default='default'); runtime.state.set(app_key, 'fab-1')
    workspace = runtime.open_workspace('analysis'); workspace.layout.register_panel(PanelSpec('chart', metadata={'title': '수율'}))
    session = workspace.open_data_session('d'); session.set_filter(FilterClause('region', FilterOperation.EQUALS, 'APAC'))
    encoded = serialize_application_snapshot(runtime.snapshot())
    assert json.loads(encoded)['schema_version'] == 1 and '수율' in encoded

    clone = ApplicationRuntime(); clone.data.register(runtime.data.datasets['d'])
    await clone.restore(deserialize_application_snapshot(encoded))
    assert clone.state.get(app_key) == 'fab-1'
    assert clone.workspaces['analysis'].data_sessions['default'].metric('value') == 10.0
    assert clone.workspaces['analysis'].layout.panels['chart'].metadata['title'] == '수율'
    await runtime.aclose(); await clone.aclose()


async def test_v3_application_snapshot_json_rejects_unknown_schema_versions():
    with pytest.raises(ValueError, match='unsupported runtime snapshot schema'):
        deserialize_application_snapshot('{"schema_version":99,"state":{"revision":0,"values":{}},"workspaces":[]}')
