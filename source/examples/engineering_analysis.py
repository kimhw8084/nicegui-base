"""Phase 9 semantic example: reusable engineering/RCA contracts without application-specific data access."""
from nicegui_base import (
    CommonalityInterpretation, CommonalityKind, CommonalityObservation,
    ConfidenceIndicatorSpec, ConfidenceLevel, ControlLimits,
    DistributionComparisonSpec, EngineeringEntityCardSpec, EngineeringEntityKind,
    EngineeringEntityRef, EngineeringStatus, EvidenceChannel, EvidenceDirection,
    EvidenceItem, EvidenceStrength, LimitBand, MeasurementPoint, ProcessTrendSpec,
    RcaHypothesis, evaluate_spec, evidence_balance, rank_commonalities,
)


tool = EngineeringEntityRef(
    EngineeringEntityKind.TOOL,
    'ETCH-021',
    label='ETCH-021',
    status=EngineeringStatus.WARNING,
    secondary='Etch Bay · Chamber B',
)
entity_card = EngineeringEntityCardSpec(tool, properties=(('Chamber', 'B'), ('Recipe', 'RCP-913')))

limits = LimitBand(lower_spec=9.0, lower_warning=9.3, target=10.0, upper_warning=10.7, upper_spec=11.0, unit='nm')
measurement = evaluate_spec(10.82, limits)

trend = ProcessTrendSpec(
    'Critical Dimension',
    points=(MeasurementPoint('08:00', 10.1), MeasurementPoint('09:00', 10.4), MeasurementPoint('10:00', 10.82)),
    unit='nm',
    spec_limits=limits,
    control_limits=ControlLimits(lower_control=9.5, centerline=10.0, upper_control=10.5, unit='nm'),
)

population = DistributionComparisonSpec(
    affected_values=(10.5, 10.7, 10.8, 10.9),
    control_values=(9.8, 10.0, 10.1, 10.2),
    parameter='Critical Dimension',
    unit='nm',
)

commonalities = rank_commonalities([
    CommonalityObservation('ch-b', 'Chamber B', CommonalityKind.CHAMBER, 18, 20, 2, 20, interpretation=CommonalityInterpretation.CAUSAL_CANDIDATE),
    CommonalityObservation('route-x', 'Route X', CommonalityKind.ROUTE, 20, 20, 18, 20, interpretation=CommonalityInterpretation.ROUTING),
])

evidence = (
    EvidenceItem('physical', 'Residue signature matches affected wafers', EvidenceChannel.PHYSICAL, EvidenceDirection.SUPPORTS, EvidenceStrength.STRONG, confidence=.9),
    EvidenceItem('control', 'One control lot shows a mild similar drift', EvidenceChannel.METROLOGY, EvidenceDirection.CONTRADICTS, EvidenceStrength.MODERATE, confidence=.8),
)
hypothesis = RcaHypothesis(
    'chamber-b-instability',
    'Chamber B process instability',
    evidence=evidence,
    commonalities=tuple(commonalities),
    confidence=ConfidenceIndicatorSpec(ConfidenceLevel.HIGH, .78, basis='Evidence synthesis', calibrated_probability=False),
)

if __name__ == '__main__':
    print(entity_card.entity.display_label, measurement.state.value)
    print(population.population_comparison())
    print([c.label for c in commonalities])
    print(evidence_balance(hypothesis.evidence))
