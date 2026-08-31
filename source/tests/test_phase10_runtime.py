import json
import pytest

from nicegui_base.runtime import CompatibilityManifest, ProxyConfig, RuntimeConfig, RuntimeEnvironment
from nicegui_base.version import FRAMEWORK_VERSION


def test_proxy_config_normalizes_root_path():
    assert ProxyConfig(True,('10.0.0.1',),'/apps/tool/').normalized_root_path=='/apps/tool'
    with pytest.raises(ValueError): ProxyConfig(True,('10.0.0.1',),'apps')
    with pytest.raises(ValueError): ProxyConfig(True,(),'/apps')


def test_runtime_config_rejects_debug_prod_and_bad_paths():
    with pytest.raises(ValueError): RuntimeConfig('A', environment=RuntimeEnvironment.PROD, debug=True)
    with pytest.raises(ValueError): RuntimeConfig('A', health_path='health')


def test_runtime_run_kwargs_secure_production_cookie_and_root_path():
    cfg=RuntimeConfig('Tool', environment=RuntimeEnvironment.PROD, proxy=ProxyConfig(True,('10.0.0.1',),'/tool'))
    kw=cfg.nicegui_run_kwargs({'NICEGUI_BASE_STORAGE_SECRET':'secret'})
    assert kw['storage_secret']=='secret'
    assert kw['session_middleware_kwargs']['https_only'] is True
    assert kw['session_middleware_kwargs']['same_site']=='strict'
    assert kw['root_path']=='/tool' and kw['proxy_headers'] is True and kw['forwarded_allow_ips']=='10.0.0.1'
    assert kw['workers']==1 and kw['fastapi_docs'] is False and kw['endpoint_documentation']=='none'


def test_storage_secret_is_fail_closed_when_required():
    cfg=RuntimeConfig('Tool')
    with pytest.raises(RuntimeError): cfg.resolve_storage_secret({})


def test_multi_replica_requires_shared_storage_warning():
    cfg=RuntimeConfig('Tool', expected_replicas=2)
    issues=cfg.validate_environment({'NICEGUI_BASE_STORAGE_SECRET':'x'})
    assert 'multi_replica_without_shared_storage' in issues
    assert 'multi_replica_without_shared_storage' not in cfg.validate_environment({'NICEGUI_BASE_STORAGE_SECRET':'x','NICEGUI_REDIS_URL':'redis://x'})


def test_from_env_is_centralized():
    cfg=RuntimeConfig.from_env('Tool', environ={
        'NICEGUI_BASE_ENVIRONMENT':'qa','NICEGUI_BASE_PORT':'9000','NICEGUI_BASE_PROXY_ENABLED':'true',
        'NICEGUI_BASE_TRUSTED_PROXIES':'10.0.0.1,10.0.0.2','NICEGUI_BASE_ROOT_PATH':'/tool'
    })
    assert cfg.environment is RuntimeEnvironment.QA and cfg.port==9000 and cfg.proxy.enabled and cfg.proxy.normalized_root_path=='/tool'


def test_compatibility_manifest_is_machine_readable(tmp_path):
    m=CompatibilityManifest(); data=json.loads(m.to_json())
    assert data['framework_version']==FRAMEWORK_VERSION and data['nicegui_version']=='3.15.0'
    assert data['external_cdn_required'] is False and data['max_nicegui_workers_per_process']==1
    path=m.write(tmp_path/'compat.json'); assert json.loads(path.read_text())['root_path_supported'] is True


def test_multi_replica_requires_session_affinity_confirmation():
    cfg=RuntimeConfig('Tool', expected_replicas=2)
    env={'NICEGUI_BASE_STORAGE_SECRET':'x','NICEGUI_REDIS_URL':'redis://x'}
    assert 'multi_replica_without_session_affinity_confirmation' in cfg.validate_environment(env)
    env['NICEGUI_BASE_SESSION_AFFINITY_CONFIRMED']='true'
    assert 'multi_replica_without_session_affinity_confirmation' not in cfg.validate_environment(env)


def test_samesite_none_requires_secure_cookie():
    with pytest.raises(ValueError): RuntimeConfig('Tool', same_site='none', secure_session_cookie=False)
