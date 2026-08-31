from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class SecurityHeaders:
    content_type_options: str = 'nosniff'
    referrer_policy: str = 'no-referrer'
    frame_options: str = 'DENY'
    permissions_policy: str = 'camera=(), microphone=(), geolocation=(), payment=(), usb=()'
    cross_origin_opener_policy: str | None = None
    content_security_policy: str | None = None
    strict_transport_security: str | None = None

    def as_pairs(self) -> tuple[tuple[bytes, bytes], ...]:
        values: list[tuple[str, str | None]] = [
            ('x-content-type-options', self.content_type_options),
            ('referrer-policy', self.referrer_policy),
            ('x-frame-options', self.frame_options),
            ('permissions-policy', self.permissions_policy),
            ('cross-origin-opener-policy', self.cross_origin_opener_policy),
            ('content-security-policy', self.content_security_policy),
            ('strict-transport-security', self.strict_transport_security),
        ]
        return tuple((key.encode('latin-1'), value.encode('latin-1')) for key, value in values if value)


class SecurityHeadersMiddleware:
    """Pure ASGI middleware to avoid BaseHTTPMiddleware context propagation issues."""

    def __init__(self, app, headers: SecurityHeaders | None = None):
        self.app = app
        self.headers = headers or SecurityHeaders()

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            return await self.app(scope, receive, send)
        additions = self.headers.as_pairs()

        async def send_with_headers(message):
            if message.get('type') == 'http.response.start':
                existing = list(message.get('headers') or [])
                existing_names = {name.lower() for name, _ in existing}
                existing.extend(pair for pair in additions if pair[0].lower() not in existing_names)
                message['headers'] = existing
            await send(message)

        await self.app(scope, receive, send_with_headers)
