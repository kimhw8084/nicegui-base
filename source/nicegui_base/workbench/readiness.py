from __future__ import annotations

import json
import sys
import urllib.request
from typing import Any, Mapping

EXPECTED_PRODUCT = 'nicegui-base'
EXPECTED_APPLICATION = 'workbench'
try:
    from nicegui_base.version import FRAMEWORK_VERSION as EXPECTED_VERSION
except ImportError:  # pragma: no cover - supports isolated source inspection only
    EXPECTED_VERSION = '3.0.0a8'



def identity_problem(payload: Mapping[str, Any], *, version: str = EXPECTED_VERSION) -> str | None:
    expected = {
        'product': EXPECTED_PRODUCT,
        'application': EXPECTED_APPLICATION,
        'version': version,
        'ready': True,
    }
    mismatches = [f"{key}={payload.get(key)!r} (expected {value!r})" for key, value in expected.items() if payload.get(key) != value]
    return '; '.join(mismatches) if mismatches else None


def identity_is_ready(payload: Mapping[str, Any], *, version: str = EXPECTED_VERSION) -> bool:
    return (
        payload.get('product') == EXPECTED_PRODUCT
        and payload.get('application') == EXPECTED_APPLICATION
        and payload.get('version') == version
        and payload.get('ready') is True
    )


def fetch_identity(url: str, *, timeout: float = 0.35) -> Mapping[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f'Workbench identity endpoint returned HTTP {response.status}')
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise TypeError('Workbench identity endpoint did not return an object')
    return payload


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print('usage: python -m nicegui_base.workbench.readiness <identity-url>', file=sys.stderr)
        return 2
    try:
        payload = fetch_identity(args[0])
    except Exception as exc:
        print(f'not ready: {exc}', file=sys.stderr)
        return 1
    problem = identity_problem(payload)
    if problem is not None:
        print(f'not ready: {problem}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
