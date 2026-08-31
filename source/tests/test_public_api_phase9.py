import nicegui_base as cui


def test_phase9_public_model_and_analytics_surface():
    expected=['EngineeringEntityRef','EngineeringStatus','LimitBand','SpecEvaluation','evaluate_spec','BaselineComparison',
              'PopulationSummary','compare_populations','CommonalityObservation','rank_commonalities','EvidenceItem',
              'evidence_balance','ConfidenceIndicatorSpec','RcaHypothesis','rank_hypotheses','ENGINEERING_REGISTRY']
    for name in expected: assert hasattr(cui,name), name


def test_phase9_public_rendering_surface():
    expected=['EngineeringEntityCard','EngineeringStatusBadge','SpecLimitIndicator','OutOfSpecIndicator','BaselineComparisonView',
              'ConfidenceIndicator','EvidenceCard','CommonalityTable','EngineeringProcessTrend','PopulationComparisonPanel',
              'RcaEvidencePanel','EngineeringTimeline']
    for name in expected: assert hasattr(cui,name), name
