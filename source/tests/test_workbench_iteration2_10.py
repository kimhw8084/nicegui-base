from __future__ import annotations

import io
import json
import os
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path


def _generated_model(provider: str = 'none'):
    from nicegui_base.workbench.builder import BuilderModel
    from nicegui_base.workbench.data_dock import DataDockModel

    model = BuilderModel()
    model.set_goal('Explore governed production records', problem_type='generic application')
    model.data = DataDockModel((
        {'record_id': 'DEV-1', 'area': 'A', 'measurement': 10.2},
        {'record_id': 'DEV-2', 'area': 'B', 'measurement': 10.8},
    ))
    model.data.set_semantic_role('record_id', 'identifier')
    model.data.set_semantic_role('area', 'dimension')
    model.data.set_semantic_role('measurement', 'measurement')
    model.select_pattern('data_explorer')
    model.auto_compose(replace=True)
    model.set_data_handoff_mode('schema_only')
    model.set_production_provider(provider)
    return model


def _extract(payload: bytes, root: Path) -> Path:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        archive.extractall(root)
    return root


def _run_generated(root: Path, script: str, env: dict[str, str]) -> dict[str, object]:
    source_root = Path(__file__).resolve().parents[1]
    merged = os.environ.copy()
    merged.update(env)
    merged['PYTHONPATH'] = os.pathsep.join((str(root), str(source_root)))
    result = subprocess.run(
        [sys.executable, '-c', script], cwd=root, env=merged,
        text=True, capture_output=True, timeout=20, check=True,
    )
    return json.loads(result.stdout.strip())


def test_provider_contract_is_signed_bounded_and_only_claims_core_constructible_adapters():
    from nicegui_base.workbench.production_integration import provider_contract_for_project, validate_provider_contract

    contract = provider_contract_for_project({'production_provider': 'sqlite'})
    assert validate_provider_contract(contract) == ()
    assert contract['selected_provider'] == 'sqlite'
    assert contract['generated_provider_keys'] == ['csv', 'sqlite']
    assert contract['provider_boundary'] == 'services.app_data:build_source'
    assert contract['health_boundary'] == 'services.app_data:register_source_health'
    assert contract['provider_mutation_policy'] == 'none'
    assert contract['resilience']['infinite_retry'] is False
    assert all(item['secret'] is False and 'value' not in item for item in contract['configuration'])


def test_builder_provider_selection_roundtrips_and_state_v6_migrates_old_projects():
    from nicegui_base.workbench.builder import BuilderModel
    from nicegui_base.workbench.project_state import STATE_VERSION, normalize_state

    model = _generated_model('csv')
    restored = BuilderModel.from_snapshot(model.snapshot())
    assert restored.production_provider == 'csv'
    state = normalize_state({'version': 5, 'project': {'name': 'old project'}})
    assert STATE_VERSION >= 6
    assert state['version'] == STATE_VERSION
    assert state['project']['production_provider'] == 'none'


def test_generated_zip_materializes_provider_contract_env_reference_and_runtime_health_binding():
    model = _generated_model('csv')
    payload, report = model.generate()
    assert report.ok, report.findings
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert {'.nicegui_base/provider_contract.json', 'services/provider_config.py', '.env.example'} <= names
        contract = json.loads(archive.read('.nicegui_base/provider_contract.json'))
        project = json.loads(archive.read('.nicegui_base/workbench_project.json'))
        assert project['provider_contract']['contract_signature'] == contract['contract_signature']
        assert project['production_provider'] == 'csv'
        assert b'register_source_health' in archive.read('app.py')
        app_data = archive.read('services/app_data.py').decode()
        assert 'def build_source(' in app_data
        assert 'def provider_diagnostics(' in app_data
        assert 'DATA_TABLE_SPEC = ServerDataTableSpec(' in app_data
        assert "mutation_policy': 'none'" in app_data
        example = archive.read('.env.example').decode()
        assert 'NICEGUI_BASE_DATA_MODE=development' in example
        assert not any(key in example for key in ('PASSWORD=', 'TOKEN=', 'API_KEY=', 'SECRET='))
        assert '.env' in archive.read('.gitignore').decode().splitlines()


def test_generated_csv_provider_executes_real_query_and_canonical_health(tmp_path: Path):
    model = _generated_model('csv')
    payload, report = model.generate(); assert report.ok, report.findings
    root = _extract(payload, tmp_path / 'app')
    csv_path = tmp_path / 'records.csv'
    csv_path.write_text('record_id,area,measurement\nP-1,ETCH,11.2\nP-2,CVD,12.4\n', encoding='utf-8')
    result = _run_generated(root, """
import asyncio, json
from types import SimpleNamespace
from nicegui_base import Query
from nicegui_base.diagnostics import HealthRegistry
from services.app_data import SOURCE, provider_diagnostics, register_source_health
async def main():
    queried = await SOURCE.query(Query(limit=10))
    runtime = SimpleNamespace(health=HealthRegistry())
    register_source_health(runtime)
    report = await runtime.health.run()
    print(json.dumps({'provider': SOURCE.provider, 'rows': len(queried.rows), 'ready': report.ready, 'diag': await provider_diagnostics()}))
asyncio.run(main())
""", {
        'NICEGUI_BASE_DATA_MODE': 'production',
        'NICEGUI_BASE_DATA_PROVIDER': 'csv',
        'NICEGUI_BASE_DATA_CSV_PATH': str(csv_path),
    })
    assert result['provider'] == 'csv'
    assert result['rows'] == 2
    assert result['ready'] is True
    assert result['diag']['ready'] is True


def test_generated_sqlite_provider_executes_real_query(tmp_path: Path):
    model = _generated_model('sqlite')
    payload, report = model.generate(); assert report.ok, report.findings
    root = _extract(payload, tmp_path / 'app')
    db_path = tmp_path / 'records.sqlite3'
    with sqlite3.connect(db_path) as connection:
        connection.execute('CREATE TABLE records (record_id TEXT PRIMARY KEY, area TEXT, measurement REAL)')
        connection.executemany('INSERT INTO records VALUES (?, ?, ?)', [('P-1','ETCH',11.2), ('P-2','CVD',12.4)])
    result = _run_generated(root, """
import asyncio, json
from nicegui_base import Query
from services.app_data import SOURCE, provider_diagnostics
async def main():
    queried = await SOURCE.query(Query(limit=10))
    print(json.dumps({'provider': SOURCE.provider, 'rows': len(queried.rows), 'diag': await provider_diagnostics()}))
asyncio.run(main())
""", {
        'NICEGUI_BASE_DATA_MODE': 'production',
        'NICEGUI_BASE_DATA_PROVIDER': 'sqlite',
        'NICEGUI_BASE_DATA_SQLITE_PATH': str(db_path),
        'NICEGUI_BASE_DATA_SQLITE_TABLE': 'records',
    })
    assert result['provider'] == 'sqlite'
    assert result['rows'] == 2
    assert result['diag']['ready'] is True


def test_broken_provider_config_keeps_startup_diagnostic_and_readiness_safe(tmp_path: Path):
    model = _generated_model('csv')
    payload, report = model.generate(); assert report.ok, report.findings
    root = _extract(payload, tmp_path / 'app')
    secret_path = tmp_path / 'password=TOPSECRET'
    result = _run_generated(root, """
import asyncio, json
from types import SimpleNamespace
from nicegui_base.diagnostics import HealthRegistry
from services.app_data import SOURCE, provider_diagnostics, register_source_health
async def main():
    runtime = SimpleNamespace(health=HealthRegistry())
    register_source_health(runtime)
    report = await runtime.health.run()
    print(json.dumps({'provider': SOURCE.provider, 'ready': report.ready, 'report': report.to_dict(), 'diag': await provider_diagnostics()}))
asyncio.run(main())
""", {
        'NICEGUI_BASE_DATA_MODE': 'production',
        'NICEGUI_BASE_DATA_PROVIDER': 'csv',
        'NICEGUI_BASE_DATA_CSV_PATH': str(secret_path),
    })
    encoded = json.dumps(result)
    assert result['provider'] == 'unavailable'
    assert result['ready'] is False
    assert result['diag']['ready'] is False
    assert 'TOPSECRET' not in encoded
    assert '[REDACTED]' in encoded


def test_provider_numeric_config_is_bounded_and_invalid_import_remains_diagnostic(tmp_path: Path):
    model = _generated_model('csv')
    payload, report = model.generate(); assert report.ok, report.findings
    root = _extract(payload, tmp_path / 'app')
    result = _run_generated(root, """
import asyncio, json
from services.app_data import SOURCE, provider_diagnostics
async def main():
    print(json.dumps({'provider': SOURCE.provider, 'diag': await provider_diagnostics()}))
asyncio.run(main())
""", {
        'NICEGUI_BASE_DATA_MODE': 'production',
        'NICEGUI_BASE_DATA_PROVIDER': 'csv',
        'NICEGUI_BASE_DATA_RETRY_ATTEMPTS': '999999',
    })
    assert result['provider'] == 'unavailable'
    assert result['diag']['ready'] is False
    assert 'between 1 and 5' in result['diag']['reason']


def test_generated_smoke_rejects_provider_contract_tamper():
    from nicegui_base.workbench.generated_smoke import smoke_generated_zip

    payload, report = _generated_model('sqlite').generate(); assert report.ok, report.findings
    source = zipfile.ZipFile(io.BytesIO(payload)); output = io.BytesIO()
    with source, zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in source.namelist():
            data = source.read(name)
            if name == '.nicegui_base/provider_contract.json':
                contract = json.loads(data); contract['selected_provider'] = 'rest'
                data = (json.dumps(contract, indent=2, sort_keys=True) + '\n').encode()
            archive.writestr(name, data)
    tampered = smoke_generated_zip(output.getvalue())
    assert not tampered.ok
    assert 'provider_contract:selected_provider' in tampered.findings
    assert 'provider_contract:signature_mismatch' in tampered.findings


def test_server_data_table_spec_bounds_staleness_and_state_labels_without_ui():
    from nicegui_base import ServerDataTableSpec, TableColumn
    from nicegui_base.integrations.nicegui_data_table import ServerDataTable

    spec = ServerDataTableSpec((TableColumn('id', 'ID'),), empty_message='Nothing here', error_message='Load failed', stale_after_seconds=1.0)
    table = object.__new__(ServerDataTable)
    table.spec = spec; table.rows = []; table.total = 0; table.loading = True
    table.last_error = None; table._last_success_monotonic = None; table.stale = False
    assert table._footer_text() == 'Loading…'
    table.loading = False
    assert table._footer_text() == 'Nothing here'
    table.last_error = RuntimeError('boom')
    assert table._footer_text() == 'Load failed'
    table.rows = [{'id': 1}]; table.total = 1; table.stale = True
    assert table._footer_text() == 'Stale data · 1 records'
