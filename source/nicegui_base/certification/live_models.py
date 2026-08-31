from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

from nicegui_base.design.responsive import CANONICAL_VIEWPORTS
from typing import Mapping


class LiveGateStatus(str, Enum):
    PASS = 'pass'
    WARNING = 'warning'
    FAIL = 'fail'
    SKIP = 'skip'


@dataclass(frozen=True, slots=True)
class LiveGateResult:
    key: str
    label: str
    status: LiveGateStatus
    detail: str
    category: str
    required: bool = True
    duration_ms: float | None = None
    evidence: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data['status'] = self.status.value
        return data


@dataclass(frozen=True, slots=True)
class LoadProbeConfig:
    url: str
    requests: int = 100
    concurrency: int = 10
    timeout_seconds: float = 10.0
    min_success_rate: float = 0.99
    max_p95_ms: float | None = None


@dataclass(frozen=True, slots=True)
class BrowserProbeConfig:
    enabled: bool = False
    required: bool = False
    browsers: tuple[str, ...] = ('chrome', 'msedge')
    viewports: tuple[tuple[str, int, int], ...] = tuple(
        (profile.key, profile.width, profile.height) for profile in CANONICAL_VIEWPORTS.values()
    )
    timeout_ms: int = 20_000
    screenshot_dir: Path | None = None
    storage_state: Path | None = None


@dataclass(frozen=True, slots=True)
class AuthProbeConfig:
    path: str
    unauthenticated_statuses: tuple[int, ...] = (302, 401, 403)
    authenticated_status: int = 200
    required: bool = True


@dataclass(frozen=True, slots=True)
class LiveCertificationConfig:
    target_url: str
    health_path: str = '/healthz'
    readiness_path: str = '/readyz'
    websocket_path: str = '/_nicegui_ws/socket.io/?EIO=4&transport=websocket'
    timeout_seconds: float = 10.0
    expected_status: int = 200
    require_security_headers: bool = True
    expected_security_headers: tuple[str, ...] = (
        'x-content-type-options',
        'referrer-policy',
    )
    headers: Mapping[str, str] = field(default_factory=dict)
    browser: BrowserProbeConfig = field(default_factory=BrowserProbeConfig)
    auth: AuthProbeConfig | None = None
    load: LoadProbeConfig | None = None
    evidence_path: Path | None = None
    require_offline_certification: bool = True
    require_nicegui_runtime: bool = True


@dataclass(frozen=True, slots=True)
class GoldCertificationReport:
    framework_version: str
    target_url: str
    checks: tuple[LiveGateResult, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)

    @property
    def failures(self) -> tuple[LiveGateResult, ...]:
        return tuple(c for c in self.checks if c.required and c.status is LiveGateStatus.FAIL)

    @property
    def required_skips(self) -> tuple[LiveGateResult, ...]:
        return tuple(c for c in self.checks if c.required and c.status is LiveGateStatus.SKIP)

    @property
    def gold_eligible(self) -> bool:
        return not self.failures and not self.required_skips

    @property
    def summary(self) -> dict[str, int]:
        return {status.value: sum(c.status is status for c in self.checks) for status in LiveGateStatus}

    def to_dict(self) -> dict[str, object]:
        return {
            'framework_version': self.framework_version,
            'target_url': self.target_url,
            'gold_eligible': self.gold_eligible,
            'summary': self.summary,
            'checks': [c.to_dict() for c in self.checks],
            'metadata': dict(self.metadata),
        }
