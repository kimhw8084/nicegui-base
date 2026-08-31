from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class RuntimeDefinition:
    key: str
    use_when: str
    rule: str

RUNTIME_REGISTRY = {item.key: item for item in (
    RuntimeDefinition('runtime_config', 'Configure host/port/environment/session/proxy settings.', 'Use typed RuntimeConfig; do not scatter environment-variable reads throughout apps.'),
    RuntimeDefinition('root_path', 'Deploy under a reverse-proxy subpath.', 'Set one normalized root_path and certify HTTP + websocket + static asset routing together.'),
    RuntimeDefinition('proxy_headers', 'Honor forwarded client/protocol information.', 'Enable only with an explicit trusted-proxy allowlist.'),
    RuntimeDefinition('health', 'Expose liveness/readiness for operations.', 'Health is minimal; detailed diagnostics require authorization.'),
    RuntimeDefinition('runtime_doctor', 'Validate a workstation/server before deployment.', 'Treat failed error-severity checks as a release blocker.'),
    RuntimeDefinition('compatibility_manifest', 'Record certified versions and deployment assumptions.', 'Applications do not select their own NiceGUI version.'),
)}

def get_runtime_definition(key: str) -> RuntimeDefinition:
    try: return RUNTIME_REGISTRY[key]
    except KeyError as exc: raise KeyError(f'Unknown runtime definition: {key}') from exc
