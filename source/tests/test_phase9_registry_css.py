import re
from nicegui_base.design.css import build_css
from nicegui_base.engineering import ENGINEERING_REGISTRY, build_engineering_css, get_engineering


def test_engineering_registry_covers_core_phase9_surface():
    expected={'EngineeringEntityCard','EngineeringStatusBadge','SpecLimitIndicator','OutOfSpecIndicator','BaselineComparison',
              'ProcessTrendSpec','DistributionComparisonSpec','PopulationComparisonPanel','CommonalityTable','EvidenceCard',
              'ConfidenceIndicator','RcaEvidencePanel','RcaWorkspaceSpec','EngineeringTimeline'}
    assert expected <= ENGINEERING_REGISTRY.keys()
    assert get_engineering('CommonalityTable').category=='analysis'


def test_engineering_css_uses_only_defined_design_variables():
    design=build_css(); engineering=build_engineering_css()
    defined=set(re.findall(r'(--cui-[\w-]+)\s*:',design))
    used=set(re.findall(r'var\((--cui-[\w-]+)\)',engineering))
    assert used-defined == set()
    assert '.cui-evidence--contradicts' in engineering and '.cui-spec--oos_high' in engineering


def test_theme_adapter_installs_engineering_css():
    source=open('nicegui_base/integrations/nicegui_theme.py').read()
    assert 'build_engineering_css' in source
