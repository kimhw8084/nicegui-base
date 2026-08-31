from nicegui_base.engineering import (
    CommonalityKind, CommonalityObservation, CommonalityTableSpec, ControlLimits,
    DistributionComparisonSpec, EngineeringEntityCardSpec, EngineeringEntityKind, EngineeringEntityRef,
    LimitBand, MeasurementPoint, ProcessTrendSpec, RcaHypothesis, RcaWorkspaceSpec,
)
from nicegui_base.data_table import SelectionMode
from nicegui_base.visualization import AxisType, ChartKind
import pytest


def test_process_trend_builds_control_chart_with_categories_and_limits():
    s=ProcessTrendSpec('CD',(MeasurementPoint('08:00',9.8),MeasurementPoint('09:00',10.2)),unit='nm',
        spec_limits=LimitBand(9,11,10),control_limits=ControlLimits(9.4,10.6,10))
    panel,series,thresholds,limits=s.chart()
    assert panel.kind is ChartKind.CONTROL and panel.x_axis.kind is AxisType.CATEGORY
    assert tuple(panel.x_axis.categories)==('08:00','09:00')
    assert tuple(series[0].data)==(9.8,10.2)
    assert {t.label for t in thresholds}=={'LCL','UCL','Center'}
    assert limits.lower==9 and limits.upper==11 and limits.target==10


def test_distribution_comparison_uses_shared_bins():
    s=DistributionComparisonSpec((1,2,3),(2,3,4),'CD')
    labels,series=s.histogram(3)
    assert len(labels)==3 and len(series)==2
    assert sum(series[0].data)==3 and sum(series[1].data)==3
    assert s.population_comparison().mean_delta==-1


def test_distribution_empty_histogram():
    labels,series=DistributionComparisonSpec((),(),'CD').histogram()
    assert labels==() and series==()


def test_commonality_table_is_semantic_and_selectable():
    o=CommonalityObservation('t','ETCH-01',CommonalityKind.TOOL,8,10,2,10)
    spec=CommonalityTableSpec((o,))
    table=spec.table_spec(); rows=spec.rows()
    assert table.selection is SelectionMode.SINGLE
    assert rows[0]['affected_rate']==80 and rows[0]['control_rate']==20
    assert 'risk_ratio' in {c.key for c in table.columns}


def test_rca_workspace_selected_key_validation():
    h=RcaHypothesis('h','Hypothesis')
    assert RcaWorkspaceSpec((h,),selected_key='h').selected_key=='h'
    with pytest.raises(ValueError): RcaWorkspaceSpec((h,),selected_key='missing')
    with pytest.raises(ValueError): RcaWorkspaceSpec((h,),candidate_limit=0)


def test_entity_card_spec_remains_generic():
    entity=EngineeringEntityRef(EngineeringEntityKind.CHAMBER,'C1')
    card=EngineeringEntityCardSpec(entity,properties=(('Recipe','R1'),))
    assert card.entity.kind is EngineeringEntityKind.CHAMBER and card.properties[0][0]=='Recipe'
