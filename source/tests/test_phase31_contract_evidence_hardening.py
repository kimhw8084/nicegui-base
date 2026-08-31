from __future__ import annotations

import json
from pathlib import Path

from nicegui_base.version import FRAMEWORK_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_root_authority_copies_match_packaged_authorities():
    assert _json("FRAMEWORK_CATALOG.json") == _json("nicegui_base/ai/framework_catalog.json")
    assert _json("COMPATIBILITY.json") == _json("nicegui_base/runtime/compatibility.json")


def test_current_named_evidence_cannot_masquerade_as_full_target_certification():
    cert = _json("CERTIFICATION_REPORT.json")
    clean = _json("CLEAN_INSTALL_CERTIFICATION.json")
    gold = _json("GOLD_PROMOTION_READINESS.json")
    for data in (cert, clean, gold):
        assert data["framework_version"] == FRAMEWORK_VERSION
    assert cert["release_certified"] is False
    assert cert["target_runtime_status"] == "PENDING"
    assert clean["passed"] is False
    assert clean["status"] == f"NOT_EXECUTED_FOR_{FRAMEWORK_VERSION}"
    assert gold["status"] == "BLOCKED_PENDING_TARGET_CERTIFICATION"


def test_radius_constitution_is_preserved_by_v171_visual_hotfix_layer():
    css = _text("nicegui_base/design/hardening_css.py")
    assert ".cui-eng-entity{box-sizing:border-box!important;border-radius:var(--cui-radius-surface)!important" in css
    assert ".cui-eng-property{box-sizing:border-box!important;width:100%!important;min-width:0!important;min-height:72px!important;padding:12px 13px!important;border-radius:var(--cui-radius-control)!important" in css
    assert ".cui-command-palette__item{appearance:none!important;box-sizing:border-box!important;width:100%!important;min-height:50px!important;padding:7px 10px!important;border:0!important;border-radius:var(--cui-radius-control)!important" in css
    assert ".cui-command-palette__escape,.cui-command-palette__shortcut" in css and "border-radius:var(--cui-radius-control)!important" in css
    assert ".cui-mobile-nav-drawer" in css and "border-radius:var(--cui-radius-overlay)!important" in css
    assert ".cui-dialog__confirmation" in css and "border-radius:var(--cui-radius-surface)!important" in css
    for forbidden in (
        ".cui-eng-entity{box-sizing:border-box!important;border-radius:20px!important",
        ".cui-eng-property{box-sizing:border-box!important;width:100%!important;min-width:0!important;min-height:72px!important;padding:12px 13px!important;border-radius:12px!important",
        ".cui-command-palette__item{appearance:none!important;box-sizing:border-box!important;width:100%!important;min-height:50px!important;padding:7px 10px!important;border:0!important;border-radius:11px!important",
    ):
        assert forbidden not in css


def test_14_defect_browser_certification_has_intent_level_checks():
    browser = _text("nicegui_base/certification/mac_browser.py")
    required = (
        "environment badge text contrast is below 4.5:1",
        "Company switch ON endpoint violates 51x31 / 27px / 2px containment geometry",
        "single/range slider track geometry drifted",
        "progress metric value is not externally separated from the track",
        "workflow rail is visually discontinuous",
        "profile greeting hierarchy is too weak",
        "application title lacks required 17px/750 hierarchy",
        "EngineeringEntityCard radius violates surface token",
        "EngineeringEntity property radius violates control token",
    )
    for phrase in required:
        assert phrase in browser
