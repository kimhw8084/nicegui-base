from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

ACCESS_CONTRACT_SCHEMA_VERSION = 1
SUPPORTED_AUTH_PROVIDERS = ('header',)


def _signature_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(k): v for k, v in value.items() if k != 'contract_signature'}


def _signed(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    payload['contract_signature'] = hashlib.sha256(
        json.dumps(_signature_payload(payload), sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    return payload


def access_contract_for_project(project: Mapping[str, Any]) -> dict[str, Any]:
    interaction = project.get('interaction_contract')
    if not isinstance(interaction, Mapping):
        from .interaction_contract import interaction_contract_for_project
        interaction = interaction_contract_for_project(project)
    pages: list[dict[str, Any]] = []
    for page in interaction.get('pages', ()) if isinstance(interaction, Mapping) else ():
        if not isinstance(page, Mapping):
            continue
        actions = []
        for action in page.get('actions', ()):
            if not isinstance(action, Mapping):
                continue
            actions.append({
                'key': str(action.get('key') or ''),
                'provider_mutation': bool(action.get('provider_mutation', False)),
                'policy': 'inherits_page',
            })
        pages.append({
            'route': str(page.get('route') or ''),
            'module': str(page.get('module') or ''),
            'pattern_key': str(page.get('pattern_key') or ''),
            'production_policy': 'authenticated',
            'development_policy': 'anonymous_allowed',
            'actions': actions,
        })
    return _signed({
        'schema_version': ACCESS_CONTRACT_SCHEMA_VERSION,
        'authentication_boundary': 'services.app_access:build_authentication_adapter',
        'page_guard_boundary': 'services.app_access:guarded_page',
        'action_guard_boundary': 'services.app_access:require_action_access',
        'configuration_boundary': 'services.app_access:AccessConfig.from_env',
        'supported_authentication_providers': list(SUPPORTED_AUTH_PROVIDERS),
        'development_default': 'anonymous_allowed',
        'production_default': 'authenticated',
        'authentication_required_in_production': True,
        'allow_anonymous_in_development': True,
        'authorization_model': 'nicegui_base.security.AuthorizationModel',
        'permission_model': 'application_defined',
        'provider_mutation_policy': 'none',
        'pages': pages,
    })


def validate_access_contract(value: Mapping[str, Any]) -> tuple[str, ...]:
    findings: list[str] = []
    if value.get('schema_version') != ACCESS_CONTRACT_SCHEMA_VERSION:
        findings.append('access_contract:schema_version')
    expected = {
        'authentication_boundary': 'services.app_access:build_authentication_adapter',
        'page_guard_boundary': 'services.app_access:guarded_page',
        'action_guard_boundary': 'services.app_access:require_action_access',
        'configuration_boundary': 'services.app_access:AccessConfig.from_env',
        'production_default': 'authenticated',
        'development_default': 'anonymous_allowed',
        'authorization_model': 'nicegui_base.security.AuthorizationModel',
        'permission_model': 'application_defined',
        'provider_mutation_policy': 'none',
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            findings.append(f'access_contract:{key}')
    if value.get('authentication_required_in_production') is not True:
        findings.append('access_contract:production_authentication')
    if value.get('allow_anonymous_in_development') is not True:
        findings.append('access_contract:development_anonymous')
    if tuple(value.get('supported_authentication_providers') or ()) != SUPPORTED_AUTH_PROVIDERS:
        findings.append('access_contract:supported_authentication_providers')
    pages = value.get('pages')
    if not isinstance(pages, list) or not pages:
        findings.append('access_contract:pages')
    else:
        routes: list[str] = []
        for page in pages:
            if not isinstance(page, Mapping):
                findings.append('access_contract:page_item')
                continue
            route = str(page.get('route') or '')
            routes.append(route)
            if not route.startswith('/'):
                findings.append(f'access_contract:route:{route}')
            if page.get('production_policy') != 'authenticated' or page.get('development_policy') != 'anonymous_allowed':
                findings.append(f'access_contract:page_policy:{route}')
            action_keys: list[str] = []
            for action in page.get('actions', ()):
                if not isinstance(action, Mapping):
                    findings.append(f'access_contract:action_item:{route}')
                    continue
                key = str(action.get('key') or '')
                action_keys.append(key)
                if not key:
                    findings.append(f'access_contract:action_key:{route}')
                if action.get('provider_mutation') is not False:
                    findings.append(f'access_contract:provider_mutation:{route}:{key}')
                if action.get('policy') != 'inherits_page':
                    findings.append(f'access_contract:action_policy:{route}:{key}')
            if len(action_keys) != len(set(action_keys)):
                findings.append(f'access_contract:duplicate_action:{route}')
        if len(routes) != len(set(routes)):
            findings.append('access_contract:duplicate_route')
    signature = str(value.get('contract_signature') or '')
    expected_signature = hashlib.sha256(
        json.dumps(_signature_payload(value), sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    if signature != expected_signature:
        findings.append('access_contract:signature_mismatch')
    return tuple(dict.fromkeys(findings))


def _app_access_source() -> str:
    return '''from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from fastapi import Request
from nicegui_base.diagnostics import HealthCheck, HealthResult, HealthState
from nicegui_base.security import (
    AccessPolicy, AuthorizationModel, HeaderAuthenticationAdapter, HeaderIdentityConfig,
    TrustedProxyPolicy,
)

SUPPORTED_AUTH_PROVIDERS = ('header',)


@dataclass(frozen=True, slots=True)
class AccessConfig:
    mode: str = 'development'
    provider: str = 'header'
    trusted_proxies: tuple[str, ...] = ('127.0.0.1/32', '::1/128')
    subject_header: str = 'x-auth-user'
    display_name_header: str = 'x-auth-name'
    email_header: str = 'x-auth-email'
    roles_header: str = 'x-auth-roles'
    permissions_header: str = 'x-auth-permissions'
    assertion_header: str = 'x-company-auth-assertion'
    assertion_secret: str | None = None

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> 'AccessConfig':
        env = os.environ if environ is None else environ
        mode = str(env.get('NICEGUI_BASE_ACCESS_MODE', 'development') or 'development').strip().lower()
        provider = str(env.get('NICEGUI_BASE_AUTH_PROVIDER', 'header') or 'header').strip().lower()
        trusted_raw = str(env.get('NICEGUI_BASE_AUTH_TRUSTED_PROXIES', '127.0.0.1/32,::1/128') or '')
        trusted = tuple(item.strip() for item in trusted_raw.split(',') if item.strip())
        return cls(
            mode=mode,
            provider=provider,
            trusted_proxies=trusted,
            subject_header=str(env.get('NICEGUI_BASE_AUTH_SUBJECT_HEADER', 'x-auth-user') or '').strip(),
            display_name_header=str(env.get('NICEGUI_BASE_AUTH_DISPLAY_NAME_HEADER', 'x-auth-name') or '').strip(),
            email_header=str(env.get('NICEGUI_BASE_AUTH_EMAIL_HEADER', 'x-auth-email') or '').strip(),
            roles_header=str(env.get('NICEGUI_BASE_AUTH_ROLES_HEADER', 'x-auth-roles') or '').strip(),
            permissions_header=str(env.get('NICEGUI_BASE_AUTH_PERMISSIONS_HEADER', 'x-auth-permissions') or '').strip(),
            assertion_header=str(env.get('NICEGUI_BASE_AUTH_ASSERTION_HEADER', 'x-company-auth-assertion') or '').strip(),
            assertion_secret=(str(env.get('NICEGUI_BASE_AUTH_ASSERTION_SECRET') or '') or None),
        )

    def validation_issues(self) -> tuple[str, ...]:
        issues: list[str] = []
        if self.mode not in {'development', 'production'}:
            issues.append('NICEGUI_BASE_ACCESS_MODE must be development or production')
        if self.provider not in SUPPORTED_AUTH_PROVIDERS:
            issues.append('NICEGUI_BASE_AUTH_PROVIDER must be header')
        if not self.trusted_proxies:
            issues.append('missing:NICEGUI_BASE_AUTH_TRUSTED_PROXIES')
        header_values = (
            self.subject_header, self.display_name_header, self.email_header,
            self.roles_header, self.permissions_header, self.assertion_header,
        )
        if any(not value for value in header_values):
            issues.append('authentication header names must not be empty')
        if self.provider == 'header':
            try:
                TrustedProxyPolicy(self.trusted_proxies)
            except ValueError:
                issues.append('NICEGUI_BASE_AUTH_TRUSTED_PROXIES contains an invalid network')
        return tuple(dict.fromkeys(issues))

    def public_diagnostics(self) -> dict[str, object]:
        return {
            'mode': self.mode,
            'provider': self.provider,
            'production_authentication_required': self.mode == 'production',
            'trusted_proxy_count': len(self.trusted_proxies),
            'assertion_secret_configured': bool(self.assertion_secret),
            'permission_model': 'application_defined',
            'provider_mutation_policy': 'none',
        }


ACCESS_CONFIG = AccessConfig.from_env()


def build_authentication_adapter(config: AccessConfig | None = None):
    cfg = ACCESS_CONFIG if config is None else config
    if cfg.mode == 'development':
        return None
    if cfg.validation_issues():
        return None
    identity = HeaderIdentityConfig(
        subject_header=cfg.subject_header,
        display_name_header=cfg.display_name_header,
        email_header=cfg.email_header,
        roles_header=cfg.roles_header,
        permissions_header=cfg.permissions_header,
        assertion_header=cfg.assertion_header,
        require_trusted_proxy=True,
    )
    return HeaderAuthenticationAdapter(
        identity,
        trusted_proxies=TrustedProxyPolicy(cfg.trusted_proxies),
        assertion_secret=cfg.assertion_secret,
    )


def page_policy(route: str, config: AccessConfig | None = None) -> AccessPolicy:
    cfg = ACCESS_CONFIG if config is None else config
    return AccessPolicy(allow_anonymous=cfg.mode == 'development')


def action_policy(route: str, action_id: str, config: AccessConfig | None = None) -> AccessPolicy:
    # Current generated actions are view-state/local-draft actions only. They inherit
    # page access. Add application-defined permissions here before introducing an
    # approved production write service.
    return page_policy(route, config)


def _runtime_access_config(runtime: Any, config: AccessConfig | None = None) -> AccessConfig:
    if config is not None:
        return config
    configured = getattr(runtime, '_nicegui_base_access_config', None)
    return configured if isinstance(configured, AccessConfig) else ACCESS_CONFIG


def require_page_access(runtime: Any, request: Request, route: str, config: AccessConfig | None = None):
    cfg = _runtime_access_config(runtime, config)
    return runtime.require_http(request, page_policy(route, cfg))


def require_action_access(runtime: Any, request: Request, route: str, action_id: str, config: AccessConfig | None = None):
    cfg = _runtime_access_config(runtime, config)
    return runtime.require_http(request, action_policy(route, action_id, cfg))


def guarded_page(runtime: Any, route: str, builder: Callable[[], None], config: AccessConfig | None = None):
    def page(request: Request) -> None:
        require_page_access(runtime, request, route, config)
        builder()
    page.__name__ = 'guarded_' + ('root' if route == '/' else route.strip('/').replace('/', '_').replace('-', '_'))
    return page


def access_health_check(config: AccessConfig | None = None) -> HealthResult:
    cfg = ACCESS_CONFIG if config is None else config
    issues = cfg.validation_issues()
    if issues:
        return HealthResult(
            'access-policy', HealthState.UNHEALTHY, '; '.join(issues),
            metadata=cfg.public_diagnostics(),
        )
    detail = 'development access policy active' if cfg.mode == 'development' else 'production authentication configured'
    return HealthResult('access-policy', HealthState.HEALTHY, detail, metadata=cfg.public_diagnostics())


def register_access_health(runtime: Any, config: AccessConfig | None = None) -> None:
    if any(check.name == 'access-policy' for check in runtime.health.checks):
        return
    cfg = ACCESS_CONFIG if config is None else config
    runtime.health.register(HealthCheck('access-policy', lambda: access_health_check(cfg), critical=True, timeout_seconds=2.0))


def configure_runtime_access(runtime: Any, config: AccessConfig | None = None) -> AccessConfig:
    cfg = ACCESS_CONFIG if config is None else config
    runtime.authorization = AuthorizationModel()
    runtime.auth_adapter = build_authentication_adapter(cfg)
    runtime._nicegui_base_access_config = cfg
    register_access_health(runtime, cfg)
    return cfg


__all__ = [
    'ACCESS_CONFIG','AccessConfig','SUPPORTED_AUTH_PROVIDERS','access_health_check','action_policy',
    'build_authentication_adapter','configure_runtime_access','guarded_page','page_policy',
    'register_access_health','require_action_access','require_page_access',
]
'''


def _bind_app_runtime_source(source: str) -> str:
    if 'configure_runtime_access' in source and 'guarded_page' in source:
        return source
    lines = source.splitlines()
    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith('from ') or line.startswith('import '):
            insert_at = index + 1
    lines.insert(insert_at, 'from services.app_access import configure_runtime_access, guarded_page')
    source = '\n'.join(lines) + ('\n' if source.endswith('\n') else '')
    if '    register_source_health(adapter)\n    return adapter' not in source:
        raise ValueError('generated app runtime shape is not recognized for access binding')
    source = source.replace(
        '    register_source_health(adapter)\n    return adapter',
        '    register_source_health(adapter)\n    configure_runtime_access(adapter)\n    return adapter',
        1,
    )
    blueprint = 'ROUTES = {' in source
    if blueprint:
        source = source.replace('ROUTES = {', 'PAGE_BUILDERS = {', 1)
        main_pattern = re.compile(r"def main\(\) -> None:\n    runtime\(\)\.run\(root=build_home, pages=ROUTES\)")
        replacement = (
            "RUNTIME = runtime()\n"
            "ROOT = guarded_page(RUNTIME, '/', build_home)\n"
            "ROUTES = {route: guarded_page(RUNTIME, route, builder) for route, builder in PAGE_BUILDERS.items()}\n\n"
            "def main() -> None:\n"
            "    RUNTIME.run(root=ROOT, pages=ROUTES)"
        )
    else:
        main_pattern = re.compile(r"def main\(\) -> None:\n    runtime\(\)\.run\(root=build_page\)")
        replacement = (
            "RUNTIME = runtime()\n"
            "ROOT = guarded_page(RUNTIME, '/', build_page)\n\n"
            "def main() -> None:\n"
            "    RUNTIME.run(root=ROOT)"
        )
    if not main_pattern.search(source):
        raise ValueError('generated app main shape is not recognized for access guard binding')
    return main_pattern.sub(replacement, source, count=1)


def _append_env_reference(path: Path) -> None:
    current = path.read_text(encoding='utf-8') if path.is_file() else ''
    if 'NICEGUI_BASE_ACCESS_MODE=' in current:
        return
    addition = '\n'.join([
        '',
        '# Access/authentication configuration. Development is open; production is authenticated.',
        'NICEGUI_BASE_ACCESS_MODE=development',
        'NICEGUI_BASE_AUTH_PROVIDER=header',
        'NICEGUI_BASE_AUTH_TRUSTED_PROXIES=127.0.0.1/32,::1/128',
        'NICEGUI_BASE_AUTH_SUBJECT_HEADER=x-auth-user',
        'NICEGUI_BASE_AUTH_DISPLAY_NAME_HEADER=x-auth-name',
        'NICEGUI_BASE_AUTH_EMAIL_HEADER=x-auth-email',
        'NICEGUI_BASE_AUTH_ROLES_HEADER=x-auth-roles',
        'NICEGUI_BASE_AUTH_PERMISSIONS_HEADER=x-auth-permissions',
        'NICEGUI_BASE_AUTH_ASSERTION_HEADER=x-company-auth-assertion',
        '# Secret value is runtime-only and must not be committed: NICEGUI_BASE_AUTH_ASSERTION_SECRET',
        '',
    ])
    path.write_text(current.rstrip() + '\n' + addition, encoding='utf-8')


def materialize_access_policy(root: Path, project: Mapping[str, Any]) -> tuple[dict[str, object], tuple[Path, ...], dict[str, str]]:
    contract = access_contract_for_project(project)
    findings = validate_access_contract(contract)
    if findings:
        raise ValueError('generated access contract is invalid: ' + '; '.join(findings))
    sources = {'services/app_access.py': _app_access_source()}
    written: list[Path] = []
    access_path = root / 'services' / 'app_access.py'
    access_path.parent.mkdir(parents=True, exist_ok=True)
    access_path.write_text(sources['services/app_access.py'], encoding='utf-8')
    written.append(access_path)

    meta = root / '.nicegui_base' / 'access_contract.json'
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps(contract, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    written.append(meta)

    app_path = root / 'app.py'
    if not app_path.is_file():
        raise FileNotFoundError('generated app.py is required before access binding')
    app_source = _bind_app_runtime_source(app_path.read_text(encoding='utf-8'))
    app_path.write_text(app_source, encoding='utf-8')
    sources['app.py'] = app_source
    written.append(app_path)

    env_path = root / '.env.example'
    _append_env_reference(env_path)
    written.append(env_path)

    test_path = root / 'tests' / 'test_project_contract.py'
    existing_test = test_path.read_text(encoding='utf-8') if test_path.is_file() else ''
    test_source = '''\nfrom services.app_access import AccessConfig, action_policy, page_policy\n\ndef test_generated_access_policy() -> None:\n    dev = AccessConfig.from_env({})\n    assert page_policy('/', dev).allow_anonymous\n    assert action_policy('/', 'refresh', dev).allow_anonymous\n    prod = AccessConfig.from_env({'NICEGUI_BASE_ACCESS_MODE':'production','NICEGUI_BASE_AUTH_PROVIDER':'header'})\n    assert prod.validation_issues() == ()\n    assert not page_policy('/', prod).allow_anonymous\n    assert not action_policy('/', 'refresh', prod).allow_anonymous\n'''
    if 'def test_generated_access_policy()' not in existing_test:
        test_path.write_text(existing_test.rstrip() + '\n' + test_source, encoding='utf-8')
    sources['tests/test_project_contract.py'] = test_path.read_text(encoding='utf-8')
    written.append(test_path)

    readme_path = root / 'README.md'
    if readme_path.is_file():
        readme = readme_path.read_text(encoding='utf-8').rstrip()
        if '## Access & action policy' not in readme:
            readme += (
                '\n\n## Access & action policy\n\n'
                '- Development default: anonymous access is allowed for local iteration.\n'
                '- Production mode (`NICEGUI_BASE_ACCESS_MODE=production`) is fail-closed and requires an authenticated principal before any generated page renders or queries data.\n'
                '- The generated working authentication adapter is the canonical trusted-upstream header adapter only. Configure trusted proxy networks and header names with non-secret environment values. If your company uses another identity mechanism, replace `services.app_access::build_authentication_adapter()` with the approved adapter rather than bypassing page guards.\n'
                '- No company role names or permissions are invented. `services.app_access::page_policy()` and `action_policy()` are the explicit application policy boundaries. Current generated actions inherit page access and remain view-state/local-draft only; provider mutation stays disabled.\n'
                '- `access-policy` is a critical runtime health check. Invalid production access configuration makes `/readyz` not-ready without leaking secrets.\n'
                '- `NICEGUI_BASE_AUTH_ASSERTION_SECRET` is runtime-only; it is intentionally omitted as a value from `.env.example`, generated contracts, logs, and evidence.\n'
            )
            readme_path.write_text(readme, encoding='utf-8')
        written.append(readme_path)

    return contract, tuple(dict.fromkeys(written)), sources


__all__ = [
    'ACCESS_CONTRACT_SCHEMA_VERSION','SUPPORTED_AUTH_PROVIDERS','access_contract_for_project',
    'materialize_access_policy','validate_access_contract',
]
