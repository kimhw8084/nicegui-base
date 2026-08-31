"""Phase 10 canonical runtime/security composition.

This example is intentionally data-source agnostic. Company-specific SSO or gateway
headers are wired through the authentication adapter; business pages still perform
server-side access checks before rendering protected content or querying data.
"""
import os

from nicegui_base import (
    AccessPolicy, AuthorizationModel, HeaderAuthenticationAdapter, HealthCheck, HealthRegistry,
    NiceGUIRuntimeAdapter, ProxyConfig, RoleDefinition, RuntimeConfig, RuntimeEnvironment,
    TrustedProxyPolicy,
)

runtime_config = RuntimeConfig(
    app_name='Equipment Health',
    app_version='1.0.0',
    environment=RuntimeEnvironment.PROD,
    proxy=ProxyConfig(enabled=True, trusted_proxies=('10.20.0.0/16',), root_path='/equipment-health'),
)

auth = HeaderAuthenticationAdapter(
    trusted_proxies=TrustedProxyPolicy(('10.20.0.0/16',)),
    assertion_secret=os.environ['NICEGUI_BASE_AUTH_ASSERTION_SECRET'],
)

authorization = AuthorizationModel({
    'engineer': RoleDefinition('engineer', frozenset({'equipment.read', 'analysis.run'})),
    'admin': RoleDefinition('admin', frozenset({'equipment.read', 'analysis.run', 'equipment.admin'})),
})

health = HealthRegistry()
health.register(HealthCheck('process', lambda: True))

runtime = NiceGUIRuntimeAdapter(runtime_config, health=health, auth_adapter=auth, authorization=authorization)
ENGINEER_POLICY = AccessPolicy(required_permissions=frozenset({'equipment.read'}))

# In a real NiceGUI page accepting FastAPI Request, call this before rendering/querying:
# principal = runtime.require_http(request, ENGINEER_POLICY)
#
# Then start with the secret available through NICEGUI_BASE_STORAGE_SECRET:
# runtime.run(root=create_app)
