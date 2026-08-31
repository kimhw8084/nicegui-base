import pytest
from nicegui_base.engineering import (
    CommonalityKind, CommonalityObservation, EvidenceChannel, EvidenceDirection, EvidenceItem,
    EvidenceStrength, LimitBand, PopulationRole, RcaHypothesis, SpecState,
    compare_populations, evaluate_spec, evidence_balance, hypothesis_rank_score, percentile,
    rank_commonalities, rank_hypotheses, summarize_population,
)


def test_evaluate_spec_full_state_grammar():
    limits=LimitBand(lower_spec=9,lower_warning=9.5,upper_warning=10.5,upper_spec=11,unit='nm')
    assert evaluate_spec(None,limits).state is SpecState.MISSING
    assert evaluate_spec(8.8,limits).state is SpecState.OOS_LOW
    assert evaluate_spec(9.2,limits).state is SpecState.WATCH_LOW
    assert evaluate_spec(10,limits).state is SpecState.IN_SPEC
    assert evaluate_spec(10.8,limits).state is SpecState.WATCH_HIGH
    assert evaluate_spec(11.2,limits).state is SpecState.OOS_HIGH
    assert evaluate_spec(10,limits).normalized_position==pytest.approx(.5)
    with pytest.raises(ValueError): evaluate_spec(float('nan'), limits)


def test_percentile_interpolates_and_validates():
    assert percentile([0,10],.25)==pytest.approx(2.5)
    assert percentile([], .5) is None
    with pytest.raises(ValueError): percentile([1],1.2)


def test_population_summary_and_comparison():
    affected=summarize_population('Affected',PopulationRole.AFFECTED,[11,12,13],unit='nm')
    control=summarize_population('Control',PopulationRole.CONTROL,[9,10,11],unit='nm')
    cmp=compare_populations(affected,control)
    assert affected.count==3 and affected.mean==12
    assert cmp.mean_delta==2
    assert cmp.mean_ratio==pytest.approx(1.2)
    assert cmp.standardized_mean_difference is not None and cmp.standardized_mean_difference>0


def test_population_comparison_role_validation():
    a=summarize_population('A',PopulationRole.REFERENCE,[1,2])
    b=summarize_population('B',PopulationRole.CONTROL,[1,2])
    with pytest.raises(ValueError): compare_populations(a,b)


def test_rank_commonalities_uses_enrichment_not_raw_affected_overlap_only():
    strong=CommonalityObservation('a','A',CommonalityKind.TOOL,8,10,1,10)
    routing=CommonalityObservation('b','B',CommonalityKind.TOOL,10,10,9,10)
    assert rank_commonalities([routing,strong])[0].key=='a'


def test_evidence_balance_preserves_contradictions():
    items=[
        EvidenceItem('s','support',EvidenceChannel.PHYSICAL,EvidenceDirection.SUPPORTS,EvidenceStrength.STRONG),
        EvidenceItem('c','contra',EvidenceChannel.METROLOGY,EvidenceDirection.CONTRADICTS,EvidenceStrength.MODERATE),
        EvidenceItem('n','neutral',EvidenceChannel.LOG,EvidenceDirection.NEUTRAL),
    ]
    b=evidence_balance(items)
    assert (b.support_count,b.contradiction_count,b.neutral_count)==(1,1,1)
    assert b.support_weight==1 and b.contradiction_weight==pytest.approx(.65)


def test_hypothesis_rank_is_ranking_utility_not_probability():
    h1=RcaHypothesis('h1','A',evidence=(EvidenceItem('s','support',EvidenceChannel.PHYSICAL,EvidenceDirection.SUPPORTS,EvidenceStrength.STRONG),))
    h2=RcaHypothesis('h2','B',evidence=(EvidenceItem('w','weak',EvidenceChannel.LOG,EvidenceDirection.SUPPORTS,EvidenceStrength.WEAK),))
    assert hypothesis_rank_score(h1)>hypothesis_rank_score(h2)
    assert rank_hypotheses([h2,h1])[0].key=='h1'
