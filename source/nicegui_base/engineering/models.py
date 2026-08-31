from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from math import isfinite
from typing import Any, Mapping, Sequence


class EngineeringEntityKind(str, Enum):
    FAB = 'fab'
    AREA = 'area'
    TOOL = 'tool'
    CHAMBER = 'chamber'
    LOT = 'lot'
    WAFER = 'wafer'
    DIE = 'die'
    RECIPE = 'recipe'
    PROCESS_STEP = 'process_step'
    ROUTE = 'route'
    PARAMETER = 'parameter'
    MEASUREMENT = 'measurement'
    DEFECT = 'defect'
    ALARM = 'alarm'
    INVESTIGATION = 'investigation'


class EngineeringStatus(str, Enum):
    NORMAL = 'normal'
    WATCH = 'watch'
    WARNING = 'warning'
    CRITICAL = 'critical'
    UNKNOWN = 'unknown'
    OFFLINE = 'offline'
    MAINTENANCE = 'maintenance'
    HOLD = 'hold'


class SpecState(str, Enum):
    MISSING = 'missing'
    IN_SPEC = 'in_spec'
    WATCH_LOW = 'watch_low'
    WATCH_HIGH = 'watch_high'
    OOS_LOW = 'oos_low'
    OOS_HIGH = 'oos_high'


class TrendDirection(str, Enum):
    UP = 'up'
    DOWN = 'down'
    STABLE = 'stable'
    UNKNOWN = 'unknown'


class PopulationRole(str, Enum):
    AFFECTED = 'affected'
    CONTROL = 'control'
    REFERENCE = 'reference'


class CommonalityKind(str, Enum):
    TOOL = 'tool'
    CHAMBER = 'chamber'
    RECIPE = 'recipe'
    ROUTE = 'route'
    PROCESS_STEP = 'process_step'
    MATERIAL = 'material'
    SUPPLIER = 'supplier'
    TIME_WINDOW = 'time_window'
    CUSTOM = 'custom'


class CommonalityInterpretation(str, Enum):
    OBSERVED = 'observed'
    ROUTING = 'routing'
    CAUSAL_CANDIDATE = 'causal_candidate'
    CONFOUNDING = 'confounding'
    EXCLUDED = 'excluded'


class EvidenceChannel(str, Enum):
    PHYSICAL = 'physical'
    METROLOGY = 'metrology'
    SPC = 'spc'
    ALARM = 'alarm'
    PROCESS = 'process'
    ROUTING = 'routing'
    MAINTENANCE = 'maintenance'
    DEFECT = 'defect'
    YIELD = 'yield'
    LOG = 'log'
    MODEL = 'model'
    USER = 'user'


class EvidenceDirection(str, Enum):
    SUPPORTS = 'supports'
    CONTRADICTS = 'contradicts'
    NEUTRAL = 'neutral'


class EvidenceStrength(str, Enum):
    WEAK = 'weak'
    MODERATE = 'moderate'
    STRONG = 'strong'

    @property
    def weight(self) -> float:
        return {self.WEAK: 0.35, self.MODERATE: 0.65, self.STRONG: 1.0}[self]


class ConfidenceLevel(str, Enum):
    UNKNOWN = 'unknown'
    LOW = 'low'
    MODERATE = 'moderate'
    HIGH = 'high'
    VERY_HIGH = 'very_high'


class HypothesisStatus(str, Enum):
    NEW = 'new'
    INVESTIGATING = 'investigating'
    SUPPORTED = 'supported'
    CONTRADICTED = 'contradicted'
    RESOLVED = 'resolved'


@dataclass(frozen=True, slots=True)
class EngineeringEntityRef:
    kind: EngineeringEntityKind
    identifier: str
    label: str | None = None
    status: EngineeringStatus = EngineeringStatus.UNKNOWN
    secondary: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError('engineering entity identifier is required')

    @property
    def display_label(self) -> str:
        return self.label or self.identifier


@dataclass(frozen=True, slots=True)
class EngineeringEntityCardSpec:
    entity: EngineeringEntityRef
    title: str | None = None
    description: str | None = None
    properties: tuple[tuple[str, Any], ...] = ()
    show_status: bool = True
    interactive: bool = False


@dataclass(frozen=True, slots=True)
class InvestigationContextSpec:
    investigation_id: str
    hypothesis: str
    owner: str
    stage: str
    updated: str

    def __post_init__(self) -> None:
        for name, value in (('investigation_id', self.investigation_id), ('hypothesis', self.hypothesis), ('owner', self.owner), ('stage', self.stage), ('updated', self.updated)):
            if not str(value).strip():
                raise ValueError(f'{name} is required')


@dataclass(frozen=True, slots=True)
class LimitBand:
    lower_spec: float | None = None
    upper_spec: float | None = None
    target: float | None = None
    lower_warning: float | None = None
    upper_warning: float | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        vals = [v for v in (self.lower_spec, self.upper_spec, self.target, self.lower_warning, self.upper_warning) if v is not None]
        if not all(isfinite(float(v)) for v in vals):
            raise ValueError('limit values must be finite')
        if self.lower_spec is not None and self.upper_spec is not None and self.lower_spec >= self.upper_spec:
            raise ValueError('lower_spec must be less than upper_spec')
        if self.lower_warning is not None and self.lower_spec is not None and self.lower_warning < self.lower_spec:
            raise ValueError('lower_warning must not be below lower_spec')
        if self.lower_warning is not None and self.upper_spec is not None and self.lower_warning > self.upper_spec:
            raise ValueError('lower_warning must not exceed upper_spec')
        if self.upper_warning is not None and self.upper_spec is not None and self.upper_warning > self.upper_spec:
            raise ValueError('upper_warning must not exceed upper_spec')
        if self.upper_warning is not None and self.lower_spec is not None and self.upper_warning < self.lower_spec:
            raise ValueError('upper_warning must not be below lower_spec')
        if self.target is not None and self.lower_spec is not None and self.target < self.lower_spec:
            raise ValueError('target must not be below lower_spec')
        if self.target is not None and self.upper_spec is not None and self.target > self.upper_spec:
            raise ValueError('target must not exceed upper_spec')
        if self.lower_warning is not None and self.upper_warning is not None and self.lower_warning >= self.upper_warning:
            raise ValueError('lower_warning must be less than upper_warning')


@dataclass(frozen=True, slots=True)
class ControlLimits:
    lower_control: float | None = None
    upper_control: float | None = None
    centerline: float | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        if self.lower_control is not None and self.upper_control is not None and self.lower_control >= self.upper_control:
            raise ValueError('lower_control must be less than upper_control')
        if self.centerline is not None and self.lower_control is not None and self.centerline < self.lower_control:
            raise ValueError('centerline must not be below lower_control')
        if self.centerline is not None and self.upper_control is not None and self.centerline > self.upper_control:
            raise ValueError('centerline must not exceed upper_control')


@dataclass(frozen=True, slots=True)
class SpecEvaluation:
    value: float | None
    state: SpecState
    nearest_spec_distance: float | None = None
    normalized_position: float | None = None
    unit: str | None = None

    @property
    def is_oos(self) -> bool:
        return self.state in {SpecState.OOS_LOW, SpecState.OOS_HIGH}

    @property
    def is_watch(self) -> bool:
        return self.state in {SpecState.WATCH_LOW, SpecState.WATCH_HIGH}


@dataclass(frozen=True, slots=True)
class MeasurementPoint:
    x: Any
    value: float
    entity_key: str | None = None
    status: EngineeringStatus = EngineeringStatus.NORMAL
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BaselineComparison:
    current: float | None
    baseline: float | None
    unit: str | None = None
    higher_is_better: bool | None = None
    stable_tolerance: float = 0.0

    def __post_init__(self) -> None:
        if self.stable_tolerance < 0:
            raise ValueError('stable_tolerance must be >= 0')

    @property
    def delta(self) -> float | None:
        if self.current is None or self.baseline is None:
            return None
        return self.current - self.baseline

    @property
    def percent_delta(self) -> float | None:
        if self.current is None or self.baseline in (None, 0):
            return None
        return (self.current - self.baseline) / abs(self.baseline) * 100.0

    @property
    def direction(self) -> TrendDirection:
        d = self.delta
        if d is None:
            return TrendDirection.UNKNOWN
        if abs(d) <= self.stable_tolerance:
            return TrendDirection.STABLE
        return TrendDirection.UP if d > 0 else TrendDirection.DOWN

    @property
    def is_improvement(self) -> bool | None:
        if self.higher_is_better is None or self.direction in {TrendDirection.UNKNOWN, TrendDirection.STABLE}:
            return None
        return (self.direction is TrendDirection.UP) == self.higher_is_better


@dataclass(frozen=True, slots=True)
class PopulationSummary:
    name: str
    role: PopulationRole
    count: int
    mean: float | None
    median: float | None
    stdev: float | None
    minimum: float | None
    maximum: float | None
    p10: float | None
    p90: float | None
    unit: str | None = None

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError('population count must be >= 0')


@dataclass(frozen=True, slots=True)
class PopulationComparison:
    affected: PopulationSummary
    control: PopulationSummary
    mean_delta: float | None
    mean_ratio: float | None
    standardized_mean_difference: float | None


@dataclass(frozen=True, slots=True)
class CommonalityObservation:
    key: str
    label: str
    kind: CommonalityKind
    affected_exposed: int
    affected_total: int
    control_exposed: int = 0
    control_total: int = 0
    weight: float = 1.0
    interpretation: CommonalityInterpretation = CommonalityInterpretation.OBSERVED
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError('commonality key and label are required')
        for name, value in (('affected_exposed', self.affected_exposed), ('affected_total', self.affected_total), ('control_exposed', self.control_exposed), ('control_total', self.control_total)):
            if value < 0:
                raise ValueError(f'{name} must be >= 0')
        if self.affected_exposed > self.affected_total:
            raise ValueError('affected_exposed cannot exceed affected_total')
        if self.control_exposed > self.control_total:
            raise ValueError('control_exposed cannot exceed control_total')
        if self.weight < 0:
            raise ValueError('commonality weight must be >= 0')

    @property
    def affected_rate(self) -> float | None:
        return None if self.affected_total == 0 else self.affected_exposed / self.affected_total

    @property
    def control_rate(self) -> float | None:
        return None if self.control_total == 0 else self.control_exposed / self.control_total

    @property
    def rate_difference(self) -> float | None:
        if self.affected_rate is None or self.control_rate is None:
            return None
        return self.affected_rate - self.control_rate

    @property
    def risk_ratio(self) -> float | None:
        ar, cr = self.affected_rate, self.control_rate
        if ar is None or cr in (None, 0):
            return None
        return ar / cr

    @property
    def weighted_enrichment(self) -> float | None:
        d = self.rate_difference
        return None if d is None else d * self.weight


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    key: str
    title: str
    channel: EvidenceChannel
    direction: EvidenceDirection
    strength: EvidenceStrength = EvidenceStrength.MODERATE
    summary: str | None = None
    source: str | None = None
    observed_at: datetime | None = None
    confidence: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.title.strip():
            raise ValueError('evidence key and title are required')
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError('evidence confidence must be between 0 and 1')

    @property
    def signed_weight(self) -> float:
        sign = {EvidenceDirection.SUPPORTS: 1.0, EvidenceDirection.CONTRADICTS: -1.0, EvidenceDirection.NEUTRAL: 0.0}[self.direction]
        confidence = 1.0 if self.confidence is None else self.confidence
        return sign * self.strength.weight * confidence


@dataclass(frozen=True, slots=True)
class ConfidenceIndicatorSpec:
    level: ConfidenceLevel
    score: float | None = None
    basis: str | None = None
    calibrated_probability: bool = False

    def __post_init__(self) -> None:
        if self.score is not None and not 0 <= self.score <= 1:
            raise ValueError('confidence score must be between 0 and 1')

    @property
    def display(self) -> str:
        label = self.level.value.replace('_', ' ').title()
        if self.score is None or not self.calibrated_probability:
            return label
        return f'{label} ({self.score:.0%})'


@dataclass(frozen=True, slots=True)
class EvidenceBalance:
    support_count: int
    contradiction_count: int
    neutral_count: int
    weighted_balance: float
    support_weight: float
    contradiction_weight: float


@dataclass(frozen=True, slots=True)
class RcaHypothesis:
    key: str
    title: str
    description: str | None = None
    status: HypothesisStatus = HypothesisStatus.NEW
    evidence: tuple[EvidenceItem, ...] = ()
    commonalities: tuple[CommonalityObservation, ...] = ()
    confidence: ConfidenceIndicatorSpec | None = None
    explicit_rank_score: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.title.strip():
            raise ValueError('hypothesis key and title are required')


@dataclass(frozen=True, slots=True)
class EngineeringTimelineEvent:
    at: datetime
    title: str
    description: str | None = None
    status: EngineeringStatus = EngineeringStatus.UNKNOWN
    entity: EngineeringEntityRef | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


__all__ = [
    'BaselineComparison','CommonalityInterpretation','CommonalityKind','CommonalityObservation','ConfidenceIndicatorSpec',
    'ConfidenceLevel','ControlLimits','EngineeringEntityCardSpec','InvestigationContextSpec','EngineeringEntityKind','EngineeringEntityRef',
    'EngineeringStatus','EngineeringTimelineEvent','EvidenceBalance','EvidenceChannel','EvidenceDirection','EvidenceItem',
    'EvidenceStrength','HypothesisStatus','LimitBand','MeasurementPoint','PopulationComparison','PopulationRole',
    'PopulationSummary','RcaHypothesis','SpecEvaluation','SpecState','TrendDirection',
]
