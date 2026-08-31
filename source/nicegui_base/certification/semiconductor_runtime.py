from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from nicegui_base.semiconductor.conformance import AdapterConformanceReport
from nicegui_base.semiconductor.runtime_experience import RuntimePerformanceReport


class TargetGateStatus(str, Enum):
    PASS = 'pass'
    FAIL = 'fail'
    PENDING = 'pending'


@dataclass(frozen=True, slots=True)
class TargetRuntimeGate:
    key: str
    label: str
    status: TargetGateStatus
    evidence: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip() or not self.evidence.strip():
            raise ValueError('target runtime gate key, label and evidence must not be empty')
        object.__setattr__(self, 'metadata', MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class SemiconductorTargetRuntimeCertification:
    recipe_key: str
    gates: tuple[TargetRuntimeGate, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'gates', tuple(self.gates))
        keys = [item.key for item in self.gates]
        if len(keys) != len(set(keys)):
            raise ValueError('target runtime certification contains duplicate gate keys')

    @property
    def promotable(self) -> bool:
        return bool(self.gates) and all(item.status is TargetGateStatus.PASS for item in self.gates)

    @property
    def pending(self) -> tuple[TargetRuntimeGate, ...]:
        return tuple(item for item in self.gates if item.status is TargetGateStatus.PENDING)

    @property
    def failed(self) -> tuple[TargetRuntimeGate, ...]:
        return tuple(item for item in self.gates if item.status is TargetGateStatus.FAIL)

    def to_dict(self) -> dict[str, Any]:
        return {
            'recipe_key': self.recipe_key,
            'promotable': self.promotable,
            'gates': [
                {'key': item.key, 'label': item.label, 'status': item.status.value, 'evidence': item.evidence, 'metadata': dict(item.metadata)}
                for item in self.gates
            ],
        }


def build_semiconductor_target_runtime_certification(
    recipe_key: str,
    *,
    adapter_conformance: AdapterConformanceReport | None = None,
    performance: RuntimePerformanceReport | None = None,
    installed_nicegui_pass: bool | None = None,
    server_websocket_pass: bool | None = None,
    browser_pass: bool | None = None,
    human_visual_baseline_pass: bool | None = None,
) -> SemiconductorTargetRuntimeCertification:
    """Assemble target-environment evidence without converting missing execution into PASS."""
    def external(key: str, label: str, value: bool | None, evidence: str) -> TargetRuntimeGate:
        status = TargetGateStatus.PENDING if value is None else (TargetGateStatus.PASS if value else TargetGateStatus.FAIL)
        return TargetRuntimeGate(key, label, status, evidence)

    gates: list[TargetRuntimeGate] = []
    if adapter_conformance is None:
        gates.append(TargetRuntimeGate('company_adapter', 'Approved company adapter conformance', TargetGateStatus.PENDING, 'No target company adapter conformance report was supplied.'))
    else:
        gates.append(TargetRuntimeGate(
            'company_adapter', 'Approved company adapter conformance',
            TargetGateStatus.PASS if adapter_conformance.passed else TargetGateStatus.FAIL,
            'Provider-neutral bounded adapter conformance report supplied.',
            {'source_key': adapter_conformance.source_key, 'provider': adapter_conformance.provider, 'errors': tuple(item.code for item in adapter_conformance.errors)},
        ))
    if performance is None:
        gates.append(TargetRuntimeGate('fab_scale_pushdown', 'Representative fab-scale pushdown/performance', TargetGateStatus.PENDING, 'No representative target-source runtime performance report was supplied.'))
    else:
        gates.append(TargetRuntimeGate(
            'fab_scale_pushdown', 'Representative fab-scale pushdown/performance',
            TargetGateStatus.PASS if performance.passed else TargetGateStatus.FAIL,
            'Bounded runtime performance/pushdown report supplied.',
            {'source_key': performance.source_key, 'provider': performance.provider, 'errors': tuple(item.code for item in performance.errors)},
        ))
    gates.extend((
        external('installed_nicegui', 'Installed NiceGUI 3.15.0', installed_nicegui_pass, 'Must execute against the installed target-environment NiceGUI version.'),
        external('server_websocket', 'Real server/WebSocket lifecycle', server_websocket_pass, 'Must execute a real target-environment server/WebSocket smoke.'),
        external('supported_browser', 'Supported corporate browser', browser_pass, 'Must execute the current source in a supported corporate browser.'),
        external('human_visual_baseline', 'Human visual baseline', human_visual_baseline_pass, 'Must be explicitly approved from current-source target-environment renders.'),
    ))
    return SemiconductorTargetRuntimeCertification(recipe_key, tuple(gates))


__all__ = [
    'SemiconductorTargetRuntimeCertification','TargetGateStatus','TargetRuntimeGate',
    'build_semiconductor_target_runtime_certification',
]
