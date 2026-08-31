from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from time import perf_counter
from typing import Any, Awaitable, Callable, Mapping


class HealthState(str, Enum):
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'


@dataclass(frozen=True, slots=True)
class HealthResult:
    name: str
    state: HealthState
    detail: str = ''
    duration_ms: float = 0.0
    critical: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HealthReport:
    state: HealthState
    checks: tuple[HealthResult, ...]
    generated_at: datetime

    @property
    def ready(self) -> bool:
        return not any(check.critical and check.state is HealthState.UNHEALTHY for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            'state': self.state.value,
            'ready': self.ready,
            'generated_at': self.generated_at.isoformat(),
            'checks': [
                {
                    'name': item.name, 'state': item.state.value, 'detail': item.detail,
                    'duration_ms': round(item.duration_ms, 3), 'critical': item.critical,
                    'metadata': dict(item.metadata),
                }
                for item in self.checks
            ],
        }


CheckCallable = Callable[[], HealthResult | bool | str | None | Awaitable[HealthResult | bool | str | None]]


@dataclass(frozen=True, slots=True)
class HealthCheck:
    name: str
    check: CheckCallable
    critical: bool = True
    timeout_seconds: float = 3.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError('health check name is required')
        if self.timeout_seconds <= 0:
            raise ValueError('timeout_seconds must be positive')


class HealthRegistry:
    def __init__(self):
        self._checks: dict[str, HealthCheck] = {}

    def register(self, check: HealthCheck) -> None:
        if check.name in self._checks:
            raise ValueError(f'duplicate health check: {check.name}')
        self._checks[check.name] = check

    @property
    def checks(self) -> tuple[HealthCheck, ...]:
        return tuple(self._checks.values())

    async def run(self) -> HealthReport:
        results = await asyncio.gather(*(self._run_one(check) for check in self._checks.values()))
        if any(item.critical and item.state is HealthState.UNHEALTHY for item in results):
            state = HealthState.UNHEALTHY
        elif any(item.state is not HealthState.HEALTHY for item in results):
            state = HealthState.DEGRADED
        else:
            state = HealthState.HEALTHY
        return HealthReport(state, tuple(results), datetime.now(timezone.utc))

    async def _run_one(self, spec: HealthCheck) -> HealthResult:
        started = perf_counter()
        try:
            if inspect.iscoroutinefunction(spec.check):
                value = await asyncio.wait_for(spec.check(), timeout=spec.timeout_seconds)
            else:
                value = await asyncio.wait_for(asyncio.to_thread(spec.check), timeout=spec.timeout_seconds)
                if inspect.isawaitable(value):
                    value = await asyncio.wait_for(value, timeout=spec.timeout_seconds)
            elapsed = (perf_counter() - started) * 1000
            if isinstance(value, HealthResult):
                return HealthResult(value.name, value.state, value.detail, elapsed, spec.critical, value.metadata)
            if value is False:
                return HealthResult(spec.name, HealthState.UNHEALTHY, 'check returned false', elapsed, spec.critical)
            if isinstance(value, str):
                return HealthResult(spec.name, HealthState.HEALTHY, value, elapsed, spec.critical)
            return HealthResult(spec.name, HealthState.HEALTHY, '', elapsed, spec.critical)
        except asyncio.TimeoutError:
            return HealthResult(spec.name, HealthState.UNHEALTHY, 'timeout', (perf_counter() - started) * 1000, spec.critical)
        except Exception as exc:  # health endpoints must report instead of crash
            return HealthResult(spec.name, HealthState.UNHEALTHY, f'{type(exc).__name__}: {exc}', (perf_counter() - started) * 1000, spec.critical)
