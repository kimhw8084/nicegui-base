from __future__ import annotations

import contextvars
import re
import uuid

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar('nicegui_base_correlation_id', default=None)
_SAFE_ID = re.compile(r'^[A-Za-z0-9._:-]{8,128}$')


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str | None = None) -> contextvars.Token:
    return _correlation_id.set(value or new_correlation_id())


def reset_correlation_id(token: contextvars.Token) -> None:
    _correlation_id.reset(token)


def validate_incoming_correlation_id(value: str | None) -> str | None:
    if not value or not _SAFE_ID.fullmatch(value):
        return None
    return value


class CorrelationIdMiddleware:
    def __init__(self, app, *, header_name: str = 'x-correlation-id', trust_incoming: bool = False):
        self.app = app
        self.header_name = header_name.lower()
        self.header_bytes = self.header_name.encode('latin-1')
        self.trust_incoming = trust_incoming

    async def __call__(self, scope, receive, send):
        incoming = None
        if self.trust_incoming:
            headers = {k.decode('latin-1').lower(): v.decode('latin-1') for k, v in scope.get('headers', [])}
            incoming = validate_incoming_correlation_id(headers.get(self.header_name))
        correlation_id = incoming or new_correlation_id()
        token = _correlation_id.set(correlation_id)

        async def send_with_id(message):
            if message.get('type') == 'http.response.start':
                headers = list(message.get('headers') or [])
                if not any(k.lower() == self.header_bytes for k, _ in headers):
                    headers.append((self.header_bytes, correlation_id.encode('latin-1')))
                message['headers'] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            _correlation_id.reset(token)
