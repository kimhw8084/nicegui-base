from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping


def _legacy_env_name(name: str) -> str | None:
    if name.startswith('NICEGUI_BASE_'):
        return 'COMPANY_UI_' + name[len('NICEGUI_BASE_'):]
    return None


def _env_get(env: Mapping[str, str], name: str, default: str | None = None) -> str | None:
    value = env.get(name)
    if value is not None:
        return value
    legacy = _legacy_env_name(name)
    if legacy is not None and legacy in env:
        return env.get(legacy)
    return default


class RuntimeEnvironment(str, Enum):
    DEV = 'dev'
    TEST = 'test'
    QA = 'qa'
    PROD = 'prod'


@dataclass(frozen=True, slots=True)
class ProxyConfig:
    enabled: bool = False
    trusted_proxies: tuple[str, ...] = ('127.0.0.1', '::1')
    root_path: str = ''

    def __post_init__(self) -> None:
        if self.root_path and not self.root_path.startswith('/'):
            raise ValueError('root_path must start with /')
        if self.root_path not in {'', '/'} and self.root_path.endswith('/'):
            object.__setattr__(self, 'root_path', self.root_path.rstrip('/'))
        if self.enabled and not self.trusted_proxies:
            raise ValueError('trusted_proxies are required when proxy mode is enabled')

    @property
    def normalized_root_path(self) -> str:
        return '' if self.root_path == '/' else self.root_path


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    app_name: str
    app_version: str = '0.1.0'
    environment: RuntimeEnvironment = RuntimeEnvironment.DEV
    host: str = '0.0.0.0'
    port: int = 8080
    title: str | None = None
    show_browser: bool = False
    reload: bool = False
    storage_secret_env: str = 'NICEGUI_BASE_STORAGE_SECRET'
    require_storage_secret: bool = True
    secure_session_cookie: bool | None = None
    same_site: str = 'strict'
    session_max_age: int | None = None
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    health_path: str = '/healthz'
    readiness_path: str = '/readyz'
    diagnostics_path: str = '/diagnostics'
    diagnostics_enabled: bool = False
    debug: bool = False
    log_level: str = 'info'
    expected_replicas: int = 1
    redis_url_env: str = 'NICEGUI_REDIS_URL'
    session_affinity_confirmed_env: str = 'NICEGUI_BASE_SESSION_AFFINITY_CONFIRMED'
    extra_env: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.app_name.strip():
            raise ValueError('app_name is required')
        if not (1 <= self.port <= 65535):
            raise ValueError('port must be between 1 and 65535')
        if self.same_site.lower() not in {'lax', 'strict', 'none'}:
            raise ValueError('same_site must be lax, strict, or none')
        for path in (self.health_path, self.readiness_path, self.diagnostics_path):
            if not path.startswith('/'):
                raise ValueError('runtime endpoint paths must start with /')
        if self.expected_replicas < 1:
            raise ValueError('expected_replicas must be at least 1')
        if self.environment is RuntimeEnvironment.PROD and self.debug:
            raise ValueError('debug must be disabled in production')
        if self.session_max_age is not None and self.session_max_age <= 0:
            raise ValueError('session_max_age must be positive')
        if self.same_site.lower() == 'none' and not self.effective_secure_cookie:
            raise ValueError('SameSite=None requires a secure session cookie')

    @property
    def effective_secure_cookie(self) -> bool:
        if self.secure_session_cookie is not None:
            return self.secure_session_cookie
        return self.environment is RuntimeEnvironment.PROD

    def resolve_storage_secret(self, environ: Mapping[str, str] | None = None) -> str | None:
        env = os.environ if environ is None else environ
        secret = _env_get(env, self.storage_secret_env)
        if self.require_storage_secret and not secret:
            raise RuntimeError(f'missing required storage secret environment variable: {self.storage_secret_env}')
        return secret

    def validate_environment(self, environ: Mapping[str, str] | None = None) -> tuple[str, ...]:
        env = os.environ if environ is None else environ
        issues: list[str] = []
        if self.require_storage_secret and not _env_get(env, self.storage_secret_env):
            issues.append(f'missing:{self.storage_secret_env}')
        if self.environment is RuntimeEnvironment.PROD and not self.effective_secure_cookie:
            issues.append('production_cookie_not_secure')
        if self.expected_replicas > 1 and not env.get(self.redis_url_env):
            issues.append('multi_replica_without_shared_storage')
        if self.expected_replicas > 1 and (_env_get(env, self.session_affinity_confirmed_env, '') or '').lower() not in {'1','true','yes'}:
            issues.append('multi_replica_without_session_affinity_confirmation')
        if self.proxy.enabled and self.host in {'127.0.0.1', 'localhost'}:
            issues.append('proxy_mode_bound_to_loopback')
        return tuple(issues)

    def nicegui_run_kwargs(self, environ: Mapping[str, str] | None = None) -> dict[str, object]:
        secret = self.resolve_storage_secret(environ)
        session_kwargs: dict[str, object] = {
            'same_site': self.same_site.lower(),
            'https_only': self.effective_secure_cookie,
        }
        if self.session_max_age is not None:
            session_kwargs['max_age'] = self.session_max_age
        kwargs: dict[str, object] = {
            'host': self.host,
            'port': self.port,
            'title': self.title or self.app_name,
            'show': self.show_browser,
            'reload': self.reload,
            'uvicorn_logging_level': self.log_level,
            'storage_secret': secret,
            'session_middleware_kwargs': session_kwargs,
            'fastapi_docs': False,
            'endpoint_documentation': 'none',
            'prod_js': True,
            'markdown': False,
            'show_welcome_message': False,
            'server_header': False,
            'root_path': self.proxy.normalized_root_path,
            'workers': 1,
        }
        if self.proxy.enabled:
            kwargs['proxy_headers'] = True
            kwargs['forwarded_allow_ips'] = ','.join(self.proxy.trusted_proxies)
        return kwargs

    @classmethod
    def from_env(cls, app_name: str, *, prefix: str = 'NICEGUI_BASE_', environ: Mapping[str, str] | None = None) -> 'RuntimeConfig':
        env = os.environ if environ is None else environ
        get = lambda suffix, default=None: _env_get(env, prefix + suffix, default)
        environment = RuntimeEnvironment((get('ENVIRONMENT', 'dev') or 'dev').lower())
        proxy_enabled = (get('PROXY_ENABLED', 'false') or 'false').lower() in {'1', 'true', 'yes'}
        trusted_raw = get('TRUSTED_PROXIES', '127.0.0.1,::1') or '127.0.0.1,::1'
        trusted = tuple(item.strip() for item in trusted_raw.split(',') if item.strip())
        proxy = ProxyConfig(proxy_enabled, trusted, get('ROOT_PATH', '') or '')
        return cls(
            app_name=app_name,
            app_version=get('APP_VERSION', '0.1.0') or '0.1.0',
            environment=environment,
            host=get('HOST', '0.0.0.0') or '0.0.0.0',
            port=int(get('PORT', '8080') or '8080'),
            proxy=proxy,
            diagnostics_enabled=(get('DIAGNOSTICS_ENABLED', 'false') or 'false').lower() in {'1', 'true', 'yes'},
            debug=(get('DEBUG', 'false') or 'false').lower() in {'1', 'true', 'yes'},
            expected_replicas=int(get('EXPECTED_REPLICAS', '1') or '1'),
        )
