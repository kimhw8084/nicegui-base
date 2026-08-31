from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .models import AccessDecision, AccessPolicy, Principal


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    name: str
    permissions: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError('role name is required')


@dataclass(slots=True)
class AuthorizationModel:
    roles: Mapping[str, RoleDefinition] = field(default_factory=dict)

    def effective_permissions(self, principal: Principal) -> frozenset[str]:
        permissions = set(principal.permissions)
        for role in principal.roles:
            definition = self.roles.get(role)
            if definition:
                permissions.update(definition.permissions)
        return frozenset(permissions)

    def check(self, principal: Principal, policy: AccessPolicy) -> AccessDecision:
        if not principal.authenticated and not policy.allow_anonymous:
            return AccessDecision(False, 'authentication_required')
        if not principal.authenticated and policy.allow_anonymous:
            return AccessDecision(True, 'anonymous_allowed')

        effective = self.effective_permissions(principal)
        missing_permissions = tuple(sorted(policy.required_permissions - effective))
        missing_roles = tuple(sorted(policy.required_roles - principal.roles))
        if missing_permissions or missing_roles:
            return AccessDecision(False, 'required_access_missing', missing_permissions, missing_roles)
        if policy.any_permissions and not (policy.any_permissions & effective):
            return AccessDecision(False, 'any_permission_required', tuple(sorted(policy.any_permissions)))
        if policy.any_roles and not (policy.any_roles & principal.roles):
            return AccessDecision(False, 'any_role_required', missing_roles=tuple(sorted(policy.any_roles)))
        return AccessDecision(True, 'allowed')

    def require(self, principal: Principal, policy: AccessPolicy) -> Principal:
        decision = self.check(principal, policy)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        return principal
