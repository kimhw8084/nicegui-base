from datetime import datetime
import pytest

from nicegui_base.engineering import (
    BaselineComparison, CommonalityInterpretation, CommonalityKind, CommonalityObservation,
    ConfidenceIndicatorSpec, ConfidenceLevel, EngineeringEntityKind, EngineeringEntityRef,
    EngineeringStatus, EvidenceChannel, EvidenceDirection, EvidenceItem, EvidenceStrength,
    LimitBand, PopulationRole, PopulationSummary, RcaHypothesis, SpecState, TrendDirection,
)


def test_entity_requires_identifier_and_display_label():
    entity=EngineeringEntityRef(EngineeringEntityKind.TOOL,'ETCH-01',status=EngineeringStatus.NORMAL)
    assert entity.display_label=='ETCH-01'
    with pytest.raises(ValueError): EngineeringEntityRef(EngineeringEntityKind.TOOL,' ')


def test_limit_band_validation():
    LimitBand(lower_spec=9,lower_warning=9.5,upper_warning=10.5,upper_spec=11,target=10)
    with pytest.raises(ValueError): LimitBand(lower_spec=11,upper_spec=10)
    with pytest.raises(ValueError): LimitBand(lower_spec=9,lower_warning=8.5)
    with pytest.raises(ValueError): LimitBand(upper_spec=11,upper_warning=11.5)
    with pytest.raises(ValueError): LimitBand(lower_spec=9,upper_spec=11,target=12)


def test_baseline_direction_and_semantics():
    c=BaselineComparison(11,10,unit='nm',higher_is_better=False)
    assert c.delta==1 and c.percent_delta==10
    assert c.direction is TrendDirection.UP and c.is_improvement is False
    assert BaselineComparison(10.01,10,stable_tolerance=.02).direction is TrendDirection.STABLE


def test_commonality_rates_are_descriptive_not_causal():
    c=CommonalityObservation('t1','ETCH-01',CommonalityKind.TOOL,8,10,2,10,interpretation=CommonalityInterpretation.ROUTING)
    assert c.affected_rate==.8 and c.control_rate==.2
    assert c.rate_difference==pytest.approx(.6) and c.risk_ratio==4
    assert c.interpretation is CommonalityInterpretation.ROUTING


def test_commonality_zero_control_rate_does_not_invent_infinite_ratio():
    c=CommonalityObservation('t1','ETCH-01',CommonalityKind.TOOL,8,10,0,10)
    assert c.risk_ratio is None


def test_evidence_signed_weight_and_confidence_bounds():
    e=EvidenceItem('e','Physical fail',EvidenceChannel.PHYSICAL,EvidenceDirection.SUPPORTS,EvidenceStrength.STRONG,confidence=.8)
    assert e.signed_weight==pytest.approx(.8)
    c=EvidenceItem('c','Counterexample',EvidenceChannel.METROLOGY,EvidenceDirection.CONTRADICTS,EvidenceStrength.MODERATE,confidence=.5)
    assert c.signed_weight<0
    with pytest.raises(ValueError): EvidenceItem('x','bad',EvidenceChannel.MODEL,EvidenceDirection.NEUTRAL,confidence=1.1)


def test_confidence_percentage_only_when_explicitly_calibrated():
    q=ConfidenceIndicatorSpec(ConfidenceLevel.HIGH,.82,calibrated_probability=False)
    assert q.display=='High'
    p=ConfidenceIndicatorSpec(ConfidenceLevel.HIGH,.82,calibrated_probability=True)
    assert p.display=='High (82%)'


def test_hypothesis_requires_identity():
    evidence=(EvidenceItem('e','Alarm',EvidenceChannel.ALARM,EvidenceDirection.SUPPORTS),)
    assert RcaHypothesis('h','Chamber instability',evidence=evidence).key=='h'
    with pytest.raises(ValueError): RcaHypothesis('','bad')
