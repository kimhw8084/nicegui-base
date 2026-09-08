"""Centralized Reference Explorer identity resolution.

The Explorer is normally fronted by the company identity layer.  Development
and local review sessions can provide ``AccessKey`` and the optional
``DEPARTMENT`` environment variables without scattering environment reads
through page rendering code.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ExplorerIdentity:
    access_key: str
    role: str = 'Member'
    department: str = 'Department unavailable'
    initials: str = 'M'
    account_missing: bool = False
    department_missing: bool = False


def _safe_display(value: object, *, fallback: str, limit: int = 120) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9 ._@+\-]', '', str(value or '')).strip()
    return cleaned[:limit] or fallback


def initials_for_access_key(access_key: str) -> str:
    """Return at most two meaningful initials without exposing the full key."""
    parts = tuple(part for part in re.split(r'[._\-\s]+', access_key.strip()) if part)
    if not parts:
        return 'M'
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def resolve_explorer_identity(environ: Mapping[str, str] | None = None) -> ExplorerIdentity:
    """Resolve the display identity once for a Workbench request.

    ``AccessKey`` is the company account variable.  ``DEPARTMENT`` is the
    optional department display value for local/reference environments.
    Missing values are intentionally graceful and are only surfaced as
    diagnostics, never as an authentication decision.
    """
    values = os.environ if environ is None else environ
    raw_access_key = str(values.get('AccessKey', '') or '').strip()
    missing_account = not bool(raw_access_key)
    access_key = _safe_display(raw_access_key, fallback='Member')
    raw_department = str(
        values.get('DEPARTMENT', values.get('NICEGUI_BASE_DEPARTMENT', '')) or ''
    ).strip()
    missing_department = not bool(raw_department)
    department = _safe_display(raw_department, fallback='Department unavailable')
    return ExplorerIdentity(
        access_key=access_key,
        role='Member',
        department=department,
        initials=initials_for_access_key(access_key if not missing_account else ''),
        account_missing=missing_account,
        department_missing=missing_department,
    )


__all__ = ['ExplorerIdentity', 'initials_for_access_key', 'resolve_explorer_identity']
