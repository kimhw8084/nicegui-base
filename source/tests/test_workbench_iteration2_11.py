from __future__ import annotations

import asyncio
import io
import json
import os
import zipfile
from types import SimpleNamespace

import pytest


def _builder(starter: str = 'record-manager', *, blueprint: str | None = None):
    from nicegui_base.workbench.builder import BuilderModel
    model = BuilderModel()
    model.apply_golden_starter(starter)
    if blueprint:
        model.set_blueprint(blueprint)
    return model


def test_access_contract_is_signed_and_tracks_interaction_actions() -> None:
    from nicegui_base.workbench.access_policy import access_contract_for_project, validate_access_contract
    from nicegui_base.workbench.interaction_contract import interaction_contract_for_project

    interaction = interaction_contract_for_project({'pattern_key': 'crud'})
    contract = access_contract_for_project({'pattern_key': 'crud', 'interaction_contract': interaction})
    assert validate_access_contract(contract) == ()
    assert contract['production_default'] == 'authenticated'
    assert contract['development_default'] == 'anonymous_allowed'
    assert contract['provider_mutation_policy'] == 'none'
    assert [item['key'] for item in contract['pages'][0]['actions']] == [item['key'] for item in interaction['pages'][0]['actions']]
    assert all(item['policy'] == 'inherits_page' for item in contract['pages'][0]['actions'])

    contract['pages'][0]['actions'][0]['provider_mutation'] = True
    findings = validate_access_contract(contract)
    assert any(item.startswith('access_contract:provider_mutation:') for item in findings)
    assert 'access_contract:signature_mismatch' in findings


def test_generated_single_page_has_access_boundary_and_no_secret_value(monkeypatch) -> None:
    sentinel = 'NGB211_SECRET_SENTINEL_SHOULD_NEVER_APPEAR'
    monkeypatch.setenv('NICEGUI_BASE_AUTH_ASSERTION_SECRET', sentinel)
    payload, report = _builder().generate()
    assert report.ok, report.findings
    assert sentinel.encode() not in payload
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert '.nicegui_base/access_contract.json' in names
        assert 'services/app_access.py' in names
        access = json.loads(archive.read('.nicegui_base/access_contract.json'))
        project = json.loads(archive.read('.nicegui_base/workbench_project.json'))
        assert access['contract_signature'] == project['access_contract']['contract_signature']
        assert [page['route'] for page in access['pages']] == ['/']
        app_source = archive.read('app.py').decode()
        assert "ROOT = guarded_page(RUNTIME, '/', build_page)" in app_source
        assert 'configure_runtime_access(adapter)' in app_source
        assert 'RUNTIME.run(root=ROOT)' in app_source
        env = archive.read('.env.example').decode()
        assert 'NICEGUI_BASE_ACCESS_MODE=development' in env
        assert 'NICEGUI_BASE_AUTH_PROVIDER=header' in env
        assert not any(line.strip().startswith('NICEGUI_BASE_AUTH_ASSERTION_SECRET=') for line in env.splitlines())
        generated_test = archive.read('tests/test_project_contract.py').decode()
        assert 'test_generated_access_policy' in generated_test


def test_generated_multi_page_guards_every_route() -> None:
    payload, report = _builder('spc-defense-line', blueprint='monitoring-operations').generate()
    assert report.ok, report.findings
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        access = json.loads(archive.read('.nicegui_base/access_contract.json'))
        interaction = json.loads(archive.read('.nicegui_base/interaction_contract.json'))
        assert [page['route'] for page in access['pages']] == [page['route'] for page in interaction['pages']]
        app_source = archive.read('app.py').decode()
        assert 'PAGE_BUILDERS = {' in app_source
        assert "ROOT = guarded_page(RUNTIME, '/', build_home)" in app_source
        assert 'ROUTES = {route: guarded_page(RUNTIME, route, builder) for route, builder in PAGE_BUILDERS.items()}' in app_source
        assert 'RUNTIME.run(root=ROOT, pages=ROUTES)' in app_source


def _load_generated_access_module(payload: bytes, tmp_path):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        archive.extractall(tmp_path)
    import importlib.util
    path = tmp_path / 'services' / 'app_access.py'
    spec = importlib.util.spec_from_file_location('ngb211_generated_access', path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_generated_access_runtime_is_open_in_dev_and_fail_closed_in_production(tmp_path) -> None:
    from nicegui_base import NiceGUIRuntimeAdapter
    from nicegui_base.runtime import RuntimeConfig

    payload, report = _builder().generate()
    assert report.ok, report.findings
    access = _load_generated_access_module(payload, tmp_path)

    dev = access.AccessConfig.from_env({})
    assert dev.validation_issues() == ()
    assert access.page_policy('/', dev).allow_anonymous
    dev_health = access.access_health_check(dev)
    assert dev_health.state.value == 'healthy'
    assert dev_health.metadata['assertion_secret_configured'] is False

    prod = access.AccessConfig.from_env({
        'NICEGUI_BASE_ACCESS_MODE': 'production',
        'NICEGUI_BASE_AUTH_PROVIDER': 'header',
        'NICEGUI_BASE_AUTH_TRUSTED_PROXIES': '127.0.0.1/32',
    })
    assert prod.validation_issues() == ()
    assert not access.page_policy('/', prod).allow_anonymous
    runtime = NiceGUIRuntimeAdapter(RuntimeConfig('access-test', require_storage_secret=False))
    access.configure_runtime_access(runtime, prod)
    assert runtime.auth_adapter is not None
    assert any(check.name == 'access-policy' for check in runtime.health.checks)
    report = asyncio.run(runtime.health.run())
    assert report.ready

    principal = asyncio.run(runtime.auth_adapter.authenticate({'x-auth-user': 'engineer-1'}, '127.0.0.1'))
    request = SimpleNamespace(state=SimpleNamespace(nicegui_base_principal=principal))
    assert access.require_page_access(runtime, request, '/').subject == 'engineer-1'

    anonymous = SimpleNamespace(state=SimpleNamespace())
    with pytest.raises(Exception) as exc_info:
        access.require_page_access(runtime, anonymous, '/')
    assert getattr(exc_info.value, 'status_code', None) == 401


def test_invalid_production_auth_is_not_ready_and_diagnostics_do_not_leak_secret(tmp_path) -> None:
    payload, report = _builder().generate()
    assert report.ok, report.findings
    access = _load_generated_access_module(payload, tmp_path)
    secret = 'VERY_PRIVATE_ASSERTION_VALUE_211'
    cfg = access.AccessConfig.from_env({
        'NICEGUI_BASE_ACCESS_MODE': 'production',
        'NICEGUI_BASE_AUTH_PROVIDER': 'unsupported',
        'NICEGUI_BASE_AUTH_ASSERTION_SECRET': secret,
    })
    assert cfg.validation_issues()
    health = access.access_health_check(cfg)
    assert health.state.value == 'unhealthy'
    serialized = json.dumps({'detail': health.detail, 'metadata': dict(health.metadata)}, sort_keys=True)
    assert secret not in serialized
    assert health.metadata['assertion_secret_configured'] is True


def test_builder_review_surfaces_access_policy_without_adding_security_guesses() -> None:
    from pathlib import Path
    import nicegui_base.workbench.builder as builder
    source = Path(builder.__file__).read_text(encoding='utf-8')
    assert 'Generated access & action policy' in source
    assert 'company roles/permissions remain explicit application configuration rather than generated guesses' in source
