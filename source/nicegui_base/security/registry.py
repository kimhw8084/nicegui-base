from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecurityDefinition:
    key: str
    use_when: str
    rule: str


SECURITY_REGISTRY = {
    item.key: item for item in (
        SecurityDefinition('principal', 'Represent the authenticated user supplied by the company identity layer.', 'Never infer permissions from display names or UI visibility.'),
        SecurityDefinition('header_auth', 'Identity is asserted by a company reverse proxy/gateway.', 'Trust identity headers only from configured proxy networks.'),
        SecurityDefinition('access_policy', 'Protect a page, route, action, or data capability.', 'Authorization must execute server-side; hidden buttons are not authorization.'),
        SecurityDefinition('security_headers', 'Add safe baseline HTTP response headers.', 'Do not invent an untested CSP for NiceGUI; CSP is opt-in until runtime-certified.'),
        SecurityDefinition('upload_policy', 'Accept user supplied files.', 'Validate size, extension and media type; active content is rejected by default.'),
        SecurityDefinition('redaction', 'Log or diagnose request/configuration context.', 'Secrets, authorization headers, cookies, credentials and tokens must be redacted.'),
        SecurityDefinition('correlation_id', 'Trace one request/action across logs.', 'Generate server-side by default; trust incoming IDs only at a controlled boundary.'),
    )
}


def get_security_definition(key: str) -> SecurityDefinition:
    try:
        return SECURITY_REGISTRY[key]
    except KeyError as exc:
        raise KeyError(f'Unknown security definition: {key}') from exc
