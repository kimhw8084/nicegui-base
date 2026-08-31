from __future__ import annotations

from math import isfinite, sqrt
from statistics import fmean, median, stdev
from typing import Iterable, Sequence

from .models import (
    CommonalityObservation, EvidenceBalance, EvidenceDirection, EvidenceItem, LimitBand,
    PopulationComparison, PopulationRole, PopulationSummary, RcaHypothesis, SpecEvaluation, SpecState,
)


def evaluate_spec(value: float | None, limits: LimitBand) -> SpecEvaluation:
    if value is None:
        return SpecEvaluation(None, SpecState.MISSING, unit=limits.unit)
    v = float(value)
    if not isfinite(v):
        raise ValueError('measurement value must be finite')
    if limits.lower_spec is not None and v < limits.lower_spec:
        return SpecEvaluation(v, SpecState.OOS_LOW, limits.lower_spec - v, _normalized(v, limits), limits.unit)
    if limits.upper_spec is not None and v > limits.upper_spec:
        return SpecEvaluation(v, SpecState.OOS_HIGH, v - limits.upper_spec, _normalized(v, limits), limits.unit)
    if limits.lower_warning is not None and v < limits.lower_warning:
        dist = None if limits.lower_spec is None else v - limits.lower_spec
        return SpecEvaluation(v, SpecState.WATCH_LOW, dist, _normalized(v, limits), limits.unit)
    if limits.upper_warning is not None and v > limits.upper_warning:
        dist = None if limits.upper_spec is None else limits.upper_spec - v
        return SpecEvaluation(v, SpecState.WATCH_HIGH, dist, _normalized(v, limits), limits.unit)
    distances = []
    if limits.lower_spec is not None: distances.append(v - limits.lower_spec)
    if limits.upper_spec is not None: distances.append(limits.upper_spec - v)
    nearest = min(distances) if distances else None
    return SpecEvaluation(v, SpecState.IN_SPEC, nearest, _normalized(v, limits), limits.unit)


def _normalized(value: float, limits: LimitBand) -> float | None:
    if limits.lower_spec is None or limits.upper_spec is None:
        return None
    return (value - limits.lower_spec) / (limits.upper_spec - limits.lower_spec)


def percentile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    if not 0 <= q <= 1:
        raise ValueError('q must be between 0 and 1')
    vals = sorted(float(v) for v in values)
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(vals) - 1)
    frac = pos - lo
    return vals[lo] * (1 - frac) + vals[hi] * frac


def summarize_population(name: str, role: PopulationRole, values: Iterable[float], *, unit: str | None = None) -> PopulationSummary:
    vals = [float(v) for v in values]
    if not all(isfinite(v) for v in vals):
        raise ValueError('population values must be finite')
    if not vals:
        return PopulationSummary(name, role, 0, None, None, None, None, None, None, None, unit)
    return PopulationSummary(
        name=name, role=role, count=len(vals), mean=fmean(vals), median=median(vals),
        stdev=stdev(vals) if len(vals) > 1 else 0.0, minimum=min(vals), maximum=max(vals),
        p10=percentile(vals, .10), p90=percentile(vals, .90), unit=unit,
    )


def compare_populations(affected: PopulationSummary, control: PopulationSummary) -> PopulationComparison:
    if affected.role is not PopulationRole.AFFECTED:
        raise ValueError('affected summary must use PopulationRole.AFFECTED')
    if control.role not in {PopulationRole.CONTROL, PopulationRole.REFERENCE}:
        raise ValueError('control summary must use CONTROL or REFERENCE role')
    mean_delta = None if affected.mean is None or control.mean is None else affected.mean - control.mean
    mean_ratio = None if affected.mean is None or control.mean in (None, 0) else affected.mean / control.mean
    smd = _standardized_mean_difference(affected, control)
    return PopulationComparison(affected, control, mean_delta, mean_ratio, smd)


def _standardized_mean_difference(a: PopulationSummary, b: PopulationSummary) -> float | None:
    if a.mean is None or b.mean is None or a.stdev is None or b.stdev is None or a.count < 2 or b.count < 2:
        return None
    denom = a.count + b.count - 2
    if denom <= 0:
        return None
    pooled_var = ((a.count - 1) * a.stdev**2 + (b.count - 1) * b.stdev**2) / denom
    if pooled_var <= 0:
        return 0.0 if a.mean == b.mean else None
    return (a.mean - b.mean) / sqrt(pooled_var)


def rank_commonalities(items: Iterable[CommonalityObservation]) -> list[CommonalityObservation]:
    def score(item: CommonalityObservation) -> tuple[float, float, int]:
        if item.interpretation.value == 'excluded':
            return (float('-inf'), float('-inf'), -1)
        enrichment = item.weighted_enrichment
        affected_rate = item.affected_rate
        return (float('-inf') if enrichment is None else enrichment,
                float('-inf') if affected_rate is None else affected_rate,
                item.affected_exposed)
    return sorted(items, key=score, reverse=True)


def evidence_balance(items: Iterable[EvidenceItem]) -> EvidenceBalance:
    support = contradiction = neutral = 0
    support_weight = contradiction_weight = 0.0
    for item in items:
        w = abs(item.signed_weight)
        if item.direction is EvidenceDirection.SUPPORTS:
            support += 1; support_weight += w
        elif item.direction is EvidenceDirection.CONTRADICTS:
            contradiction += 1; contradiction_weight += w
        else:
            neutral += 1
    return EvidenceBalance(support, contradiction, neutral, support_weight - contradiction_weight, support_weight, contradiction_weight)


def hypothesis_rank_score(hypothesis: RcaHypothesis) -> float:
    if hypothesis.explicit_rank_score is not None:
        return float(hypothesis.explicit_rank_score)
    balance = evidence_balance(hypothesis.evidence).weighted_balance
    commonality = sum(max(0.0, c.weighted_enrichment or 0.0) for c in hypothesis.commonalities)
    # Deliberately a ranking utility, not a probability or causal confidence.
    return balance + commonality


def rank_hypotheses(hypotheses: Iterable[RcaHypothesis]) -> list[RcaHypothesis]:
    return sorted(hypotheses, key=hypothesis_rank_score, reverse=True)


__all__ = [
    'compare_populations','evaluate_spec','evidence_balance','hypothesis_rank_score','percentile','rank_commonalities',
    'rank_hypotheses','summarize_population',
]
