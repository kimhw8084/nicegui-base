from pathlib import Path
import nicegui_base
from nicegui_base.version import FRAMEWORK_VERSION

ROOT=Path(__file__).resolve().parents[1]


def test_phase10_public_api_available():
    for name in ['RuntimeConfig','ProxyConfig','CompatibilityManifest','Principal','AccessPolicy','AuthorizationModel','HeaderAuthenticationAdapter','SecurityHeaders','UploadPolicy','HealthRegistry','RuntimeDoctor','NiceGUIRuntimeAdapter','SECURITY_REGISTRY','RUNTIME_REGISTRY']:
        assert hasattr(nicegui_base,name), name


def test_runtime_adapter_uses_supported_nicegui_run_security_hooks():
    text=(ROOT/'nicegui_base/integrations/nicegui_runtime.py').read_text()
    cfg=(ROOT/'nicegui_base/runtime/config.py').read_text()
    assert 'session_middleware_kwargs' in cfg and "'https_only'" in cfg and "'same_site'" in cfg
    assert "'root_path'" in cfg and "'proxy_headers'" in cfg and "'forwarded_allow_ips'" in cfg
    assert 'workers' in cfg and 'NiceGUIRuntimeAdapter' in text


def test_security_adapter_does_not_use_app_storage_for_authentication():
    text=(ROOT/'nicegui_base/integrations/nicegui_runtime.py').read_text() + (ROOT/'nicegui_base/security/models.py').read_text()
    assert 'app.storage.user' not in text and 'localStorage' not in text
    assert 'IdentityMiddleware' in text and 'nicegui_base_principal' in text


def test_csp_is_not_invented_by_default():
    text=(ROOT/'nicegui_base/security/headers.py').read_text()
    assert "content_security_policy: str | None = None" in text


def test_project_version_and_nicegui_pin():
    text=(ROOT/'pyproject.toml').read_text()
    assert f'version = "{FRAMEWORK_VERSION}"' in text and 'nicegui==3.15.0' in text
