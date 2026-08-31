from pathlib import Path
import json
from nicegui_base.certification import run_certification, combined_css
from nicegui_base.version import FRAMEWORK_VERSION

def test_certification_passes_offline_except_optional_runtime():
    root=Path(__file__).parents[1]
    r=run_certification(root)
    assert r.passed, [(c.key,c.detail) for c in r.failures]
    assert r.summary['fail']==0
    assert any(c.key=='nicegui' for c in r.checks)

def test_combined_css_integrates_every_layer():
    css=combined_css()
    for token in ['--cui-', 'cui-table', 'cui-chart', 'cui-drawer', 'cui-eng']:
        assert token in css
    assert css.count('{')==css.count('}')
    assert 'https://' not in css and 'http://' not in css

def test_certification_manifest_exists_and_is_rc():
    p=Path(__file__).parents[1]/'nicegui_base/certification/certification_manifest.json'
    m=json.loads(p.read_text())
    assert m['framework_version']==FRAMEWORK_VERSION
    assert m['release_stage'] in {'release_candidate','hardened','production_gold_candidate','mac_live_visual_certification_candidate','mac_live_certification_candidate','linux_live_certification_candidate','linux_rendered_product_certification_candidate','linux_runtime_compatibility_hotfix_candidate','v1_7_production_certification_candidate','v2_0_release_candidate'}
    assert 'comprehensive_visual_review' in m['required_gates']
