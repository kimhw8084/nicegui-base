from nicegui_base import FRAMEWORK_VERSION, NICEGUI_VERSION, PERFORMANCE_REGISTRY
from nicegui_base.integrations.nicegui_theme import build_framework_css
from nicegui_base.visualization import CrossFilterEngine, LinkedAnalysisController
from nicegui_base.visualization.models import CrossFilterBinding, ChartEvent

def test_versions():assert bool(FRAMEWORK_VERSION) and FRAMEWORK_VERSION == __import__('nicegui_base.version', fromlist=['RELEASE_AUTHORITY']).RELEASE_AUTHORITY['framework_version'] and NICEGUI_VERSION=='3.15.0'
def test_css_cached_identity():assert build_framework_css() is build_framework_css()
def test_performance_registry_count():assert len(PERFORMANCE_REGISTRY)==10
def test_crossfilter_unsubscribe():
    e=CrossFilterEngine((CrossFilterBinding('c','click','tool'),)); seen=[]; off=e.subscribe(seen.append); off(); e.dispatch(ChartEvent('c','click',value='A')); assert not seen
def test_linked_target_unsubscribe():
    e=CrossFilterEngine((CrossFilterBinding('c','click','tool'),)); c=LinkedAnalysisController(e); seen=[]; off=c.register_target('tool',seen.append); off(); c.dispatch(ChartEvent('c','click',value='A')); assert not seen
