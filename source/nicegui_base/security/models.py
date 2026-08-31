from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from ipaddress import ip_address, ip_network
import hmac
from typing import Any, Mapping, Protocol


class AuthMethod(str, Enum):
    ANONYMOUS = 'anonymous'
    HEADER = 'header'
    OIDC = 'oidc'
    SAML = 'saml'
    CUSTOM = 'custom'


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    display_name: str | None = None
    email: str | None = None
    roles: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()
    authenticated: bool = True
    method: AuthMethod = AuthMethod.CUSTOM
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.authenticated and not self.subject.strip():
            raise ValueError('authenticated principal requires a subject')
        if any(not item.strip() for item in self.roles | self.permissions):
            raise ValueError('roles and permissions must not contain empty values')

    @classmethod
    def anonymous(cls) -> 'Principal':
        return cls('anonymous', 'Anonymous', authenticated=False, method=AuthMethod.ANONYMOUS)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        return role in self.roles


@dataclass(frozen=True, slots=True)
class AccessPolicy:
    required_permissions: frozenset[str] = frozenset()
    any_permissions: frozenset[str] = frozenset()
    required_roles: frozenset[str] = frozenset()
    any_roles: frozenset[str] = frozenset()
    allow_anonymous: bool = False

    def __post_init__(self) -> None:
        all_values = self.required_permissions | self.any_permissions | self.required_roles | self.any_roles
        if any(not item.strip() for item in all_values):
            raise ValueError('policy entries must not be empty')


@dataclass(frozen=True, slots=True)
class AccessDecision:
    allowed: bool
    reason: str
    missing_permissions: tuple[str, ...] = ()
    missing_roles: tuple[str, ...] = ()


class AuthenticationAdapter(Protocol):
    async def authenticate(self, headers: Mapping[str, str], client_host: str | None = None) -> Principal:
        ...


@dataclass(frozen=True, slots=True)
class TrustedProxyPolicy:
    networks: tuple[str, ...] = ('127.0.0.1/32', '::1/128')

    def __post_init__(self) -> None:
        for value in self.networks:
            ip_network(value, strict=False)

    def contains(self, host: str | None) -> bool:
        if not host:
            return False
        try:
            address = ip_address(host)
        except ValueError:
            return False
        return any(address in ip_network(network, strict=False) for network in self.networks)


@dataclass(frozen=True, slots=True)
class HeaderIdentityConfig:
    subject_header: str = 'x-auth-user'
    display_name_header: str = 'x-auth-name'
    email_header: str = 'x-auth-email'
    roles_header: str = 'x-auth-roles'
    permissions_header: str = 'x-auth-permissions'
    separator: str = ','
    require_trusted_proxy: bool = True
    assertion_header: str = 'x-company-auth-assertion'

    def __post_init__(self) -> None:
        headers = (
            self.subject_header, self.display_name_header, self.email_header,
            self.roles_header, self.permissions_header, self.assertion_header,
        )
        if any(not value.strip() for value in headers):
            raise ValueError('identity header names must not be empty')
        if not self.separator:
            raise ValueError('separator must not be empty')


class HeaderAuthenticationAdapter:
    """Authenticate identity asserted by a trusted upstream reverse proxy.

    This adapter deliberately rejects spoofable identity headers from untrusted peers.
    It does not validate SAML/OIDC tokens itself; those should be terminated by the
    company identity gateway or implemented through a dedicated custom adapter.
    """

    def __init__(self, config: HeaderIdentityConfig | None = None, *, trusted_proxies: TrustedProxyPolicy | None = None, assertion_secret: str | None = None):
        self.config = config or HeaderIdentityConfig()
        self.trusted_proxies = trusted_proxies or TrustedProxyPolicy()
        self.assertion_secret = assertion_secret

    async def authenticate(self, headers: Mapping[str, str], client_host: str | None = None) -> Principal:
        normalized = {str(k).lower(): str(v) for k, v in headers.items()}
        trusted_network = self.trusted_proxies.contains(client_host)
        trusted_assertion = False
        if self.assertion_secret:
            supplied = normalized.get(self.config.assertion_header.lower(), '')
            trusted_assertion = bool(supplied) and hmac.compare_digest(supplied, self.assertion_secret)
        if self.config.require_trusted_proxy and not (trusted_network or trusted_assertion):
            return Principal.anonymous()
        subject = normalized.get(self.config.subject_header.lower(), '').strip()
        if not subject:
            return Principal.anonymous()
        roles = self._split(normalized.get(self.config.roles_header.lower()))
        permissions = self._split(normalized.get(self.config.permissions_header.lower()))
        return Principal(
            subject=subject,
            display_name=self._clean(normalized.get(self.config.display_name_header.lower())),
            email=self._clean(normalized.get(self.config.email_header.lower())),
            roles=frozenset(roles),
            permissions=frozenset(permissions),
            authenticated=True,
            method=AuthMethod.HEADER,
        )

    def _split(self, value: str | None) -> tuple[str, ...]:
        if not value:
            return ()
        return tuple(item.strip() for item in value.split(self.config.separator) if item.strip())

    @staticmethod
    def _clean(value: str | None) -> str | None:
        value = (value or '').strip()
        return value or None

class IdentityMiddleware:
    """Pure ASGI middleware which attaches `nicegui_base_principal` to scope state."""

    def __init__(self, app, adapter: AuthenticationAdapter):
        self.app = app
        self.adapter = adapter

    async def __call__(self, scope, receive, send):
        if scope.get('type') not in {'http', 'websocket'}:
            return await self.app(scope, receive, send)
        headers = {k.decode('latin-1').lower(): v.decode('latin-1') for k, v in scope.get('headers', [])}
        client = scope.get('client')
        client_host = client[0] if client else None
        principal = await self.adapter.authenticate(headers, client_host)
        state = scope.setdefault('state', {})
        state['nicegui_base_principal'] = principal
        await self.app(scope, receive, send)
