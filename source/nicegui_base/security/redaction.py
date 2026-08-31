from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import PurePath
from typing import Any

DEFAULT_SECRET_KEYS = frozenset({
    'password', 'passwd', 'pwd', 'secret', 'storage_secret', 'token', 'access_token',
    'refresh_token', 'api_key', 'apikey', 'authorization', 'cookie', 'set-cookie',
    'session', 'session_id', 'client_secret', 'private_key', 'credential', 'credentials',
})

_BEARER = re.compile(r'(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+\-/]+=*')
_LONG_SECRET = re.compile(r'(?i)(token|secret|password|api[_-]?key)\s*[:=]\s*[^\s,;]+')


def is_secret_key(key: str, extra_keys: frozenset[str] = frozenset()) -> bool:
    normalized = key.strip().lower().replace('-', '_')
    return normalized in DEFAULT_SECRET_KEYS | extra_keys or any(
        marker in normalized for marker in ('password', 'secret', 'token', 'api_key', 'apikey', 'credential')
    )


def redact_text(text: str, replacement: str = '[REDACTED]') -> str:
    text = _BEARER.sub(lambda m: f'{m.group(1)} {replacement}', text)
    return _LONG_SECRET.sub(lambda m: f'{m.group(1)}={replacement}', text)


def redact(value: Any, *, extra_keys: frozenset[str] = frozenset(), replacement: str = '[REDACTED]') -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): replacement if is_secret_key(str(key), extra_keys) else redact(item, extra_keys=extra_keys, replacement=replacement)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(redact(item, extra_keys=extra_keys, replacement=replacement) for item in value)
    if isinstance(value, list):
        return [redact(item, extra_keys=extra_keys, replacement=replacement) for item in value]
    if isinstance(value, set):
        return {redact(item, extra_keys=extra_keys, replacement=replacement) for item in value}
    if isinstance(value, str):
        return redact_text(value, replacement)
    return value


def safe_filename(filename: str) -> str:
    name = PurePath(filename.replace('\\', '/')).name.strip()
    name = re.sub(r'[^A-Za-z0-9._ -]+', '_', name)
    name = re.sub(r'\s+', ' ', name).strip(' .')
    if not name or name in {'.', '..'}:
        raise ValueError('invalid filename')
    return name[:180]
