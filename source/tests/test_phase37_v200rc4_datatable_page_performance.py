from __future__ import annotations

from pathlib import Path

from nicegui_base.data_table.css import build_data_table_css
from nicegui_base.certification.mac_lab_css import build_mac_lab_css

ROOT = Path(__file__).resolve().parents[1]
LAB = (ROOT / "nicegui_base/certification/mac_lab.py").read_text(encoding="utf-8")
BROWSER = (ROOT / "nicegui_base/certification/mac_browser.py").read_text(encoding="utf-8")


def test_data_lab_initially_mounts_only_primary_grid_and_defers_heavy_examples():
    block = LAB[LAB.index("def _data("):LAB.index("def _charts(")]
    assert "_deferred_lab_surface('Editable table stress test'" in block
    assert "_deferred_lab_surface('Server table stress test'" in block
    assert "_deferred_lab_surface('Master/detail stress test'" in block
    assert "Load editable table" in block and "Load server table" in block and "Load master/detail table" in block
    assert "no longer runs during the initial DataTable page load" in block
    assert block.count("_lab_table_density()") >= 4


def test_deferred_surface_is_single_mount_and_keeps_component_implementation_real():
    helper = LAB[LAB.index("def _deferred_lab_surface"):LAB.index("def _deterministic_rows")]
    assert "if mounted:" in helper and "mounted = True" in helper
    assert "with host:" in helper and "builder()" in helper
    assert "placeholder.set_visibility(False)" in helper


def test_data_route_drops_sticky_backdrop_blur_without_changing_other_lab_routes():
    css = build_mac_lab_css()
    assert ".cui-lab-route-data .cui-lab-controlbar" in css
    rule = css[css.index(".cui-lab-route-data .cui-lab-controlbar"):css.index(".cui-lab-deferred-wrap")]
    assert "backdrop-filter:none" in rule and "background:var(--cui-surface-elevated)" in rule
    assert ".cui-lab-controlbar{position:sticky" in css  # other routes preserve the existing visual contract


def test_table_shell_contains_grid_layout_work_from_rest_of_page():
    css = build_data_table_css()
    shell = css[css.index(".cui-table-shell {"):css.index(".cui-table-headline")]
    assert "contain:layout" in shell


def test_browser_certifies_initial_weight_page_frame_latency_and_on_demand_completeness():
    for token in (
        "expected exactly 1",
        "DataTable page scroll frame latency is too high",
        "page_scroll['max']>140",
        "Load editable table",
        "Load server table",
        "Load master/detail table",
        "DataTable deferred certification surfaces are incomplete after explicit load",
    ):
        assert token in BROWSER


def test_current_docs_keep_the_stable_authority_as_the_promotion_target():
    import json

    authority = json.loads((ROOT / "nicegui_base/release_authority.json").read_text(encoding="utf-8"))
    prerelease = authority["framework_version"]
    target = authority["promotion_target"]
    assert prerelease != target
    for rel in ("README.md", "mac_bundle/README.md", "linux_bundle/README.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert f"{prerelease} promotion" not in text
    assert f"{target} promotion" in (ROOT / "mac_bundle/README.md").read_text(encoding="utf-8")
