from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_reference_app_has_21_product_routes_and_no_visible_certification_page():
    lab = (ROOT / "nicegui_base/certification/mac_lab.py").read_text(encoding="utf-8")
    coverage = (ROOT / "nicegui_base/certification/mac_coverage.py").read_text(encoding="utf-8")
    assert "NavSection('quality', 'QUALITY'" in lab
    assert "NavItem('certification'" not in lab
    assert "LabRoute('/certification'" not in lab
    assert "def _certification" not in lab
    assert "'/certification': '_certification'" not in coverage
    assert lab.count("LabRoute(") == 21
    assert "Certification coverage" not in lab
    assert "table certification" not in lab
    assert "Live Certification" not in lab

def test_native_switch_uses_standard_end_stop_geometry_and_track_focus():
    css = (ROOT / "nicegui_base/design/hardening_css.py").read_text(encoding="utf-8")
    assert "width:51px!important;height:31px!important;padding:0!important" in css
    assert "top:2px!important;left:2px!important;width:27px!important;height:27px!important" in css
    assert "transform:translateX(20px)!important" in css
    assert ".cui-choice-row--switch:has(.cui-choice-native:focus-visible) .cui-switch-track" in css

def test_current_agent_contract_has_no_release_gate_or_visible_certification_guidance():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8").casefold()
    manifest = (ROOT / "nicegui_base/ai/construction_manifest.json").read_text(encoding="utf-8").casefold()
    registry = (ROOT / "nicegui_base/ai/registry.py").read_text(encoding="utf-8").casefold()
    generated_agents = (ROOT / "nicegui_base/ai/guides/AGENTS.md").read_text(encoding="utf-8").casefold()
    forbidden = ("your approval is a release gate", "company production gold", "gold promotion", "nicegui-base-gold-certify")
    for phrase in forbidden:
        assert phrase not in agents
        assert phrase not in manifest
        assert phrase not in registry
        assert phrase not in generated_agents
    assert "certification" not in generated_agents
    scaffold = (ROOT / "nicegui_base/ai/scaffold.py").read_text(encoding="utf-8")
    for legacy_guide in (
        "COMPANY_CERTIFICATION_CHECKLIST.md",
        "GOLD_PROMOTION_HARNESS.md",
        "V17_FINAL_CERTIFICATION_AND_DEPLOYMENT.md",
        "LIVE_CERTIFICATION_GUIDE.md",
        "MAC_LIVE_CERTIFICATION_GUIDE.md",
    ):
        assert f"'{legacy_guide}'" not in scaffold
