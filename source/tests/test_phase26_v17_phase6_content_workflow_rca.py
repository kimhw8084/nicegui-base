from __future__ import annotations

from pathlib import Path

import nicegui_base
from nicegui_base.certification.mac_coverage import coverage_summary
from nicegui_base.design.hardening_css import build_hardening_css
from nicegui_base.engineering import InvestigationContextSpec

ROOT=Path(__file__).resolve().parents[1]


def test_phase6_public_investigation_context_contract():
    spec=InvestigationContextSpec('EXC-1','Chamber degradation','Process Eng','Evidence review','2m ago')
    assert spec.investigation_id=='EXC-1'
    assert hasattr(nicegui_base,'InvestigationContextBar')
    assert 'InvestigationContextBar' in nicegui_base.__all__
    registry=(ROOT/'nicegui_base/engineering/registry.py').read_text(encoding='utf-8')
    assert 'InvestigationContextBar' in registry


def test_workflow_progress_uses_dedicated_centered_rail_anatomy():
    source=(ROOT/'nicegui_base/integrations/nicegui_content.py').read_text(encoding='utf-8')
    css=build_hardening_css()
    assert "classes('cui-progress-step__rail')" in source
    assert "classes('cui-progress-step__copy')" in source
    assert '.cui-progress-step__rail{position:relative!important;display:grid!important;place-items:center!important' in css
    assert '.cui-progress-step__marker{position:relative!important;z-index:1!important;width:30px!important;height:30px!important' in css
    assert '.cui-progress-step__rail::after' in css


def test_image_viewer_exposes_observable_zoom_pan_fit_state():
    source=(ROOT/'nicegui_base/integrations/nicegui_content.py').read_text(encoding='utf-8')
    theme=(ROOT/'nicegui_base/integrations/nicegui_theme.py').read_text(encoding='utf-8')
    css=build_hardening_css()
    for token in ('data-cui-image-viewer=true','cui-image-viewer__zoom','cui-image-viewer__mode','Wheel to zoom · drag to pan · double-click to fit'):
        assert token in source
    assert 'data-cui-spatial-scale="1.000"' in source
    assert "host.dataset.cuiSpatialScale" in theme
    assert "host.dataset.cuiSpatialX" in theme and "host.dataset.cuiSpatialY" in theme
    assert "CustomEvent('cui-spatial-change'" in theme
    assert 'stateOf(id)' in theme
    assert '.cui-image-viewer__viewport{position:relative!important;height:390px!important' in css


def test_synthetic_evidence_is_nonempty_and_clipped_to_wafer_boundary():
    lab=(ROOT/'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    assert 'ImageViewer(_synthetic_inspection_image()' in lab
    assert 'inspection-wafer-clip' in lab
    assert 'clip-path="url(#inspection-wafer-clip)"' in lab
    assert 'Wafer 12 · CD residual' in lab
    assert 'Lower-right excursion cluster' in lab


def test_rca_metadata_uses_contained_three_column_context_geometry():
    css=build_hardening_css()
    source=(ROOT/'nicegui_base/integrations/nicegui_engineering.py').read_text(encoding='utf-8')
    lab=(ROOT/'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    assert '.cui-eng-entity{overflow:hidden!important;container-type:inline-size!important;}' in css
    assert '.cui-eng-property-grid{grid-template-columns:repeat(3,minmax(0,1fr))!important' in css
    assert 'contain:layout paint!important' in css
    assert 'class InvestigationContextBar' in source
    assert "InvestigationContextBar(InvestigationContextSpec('EXC-1042'" in lab
    for token in ('Tool / chamber','ETCH-021 / CH-3','Recipe','Last PM','Lots affected'):
        assert token in lab


def test_browser_certification_measures_phase6_interactions_and_containment():
    source=(ROOT/'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    for phrase in (
        'workflow marker content is not optically centered',
        'Image Viewer Zoom in did not change inspect scale',
        'Image Viewer drag did not pan zoomed evidence',
        'Image Viewer Fit did not restore scale',
        'RCA investigation context strip missing',
        'RCA metadata property escaped EngineeringEntityCard bounds',
    ):
        assert phrase in source


def test_phase6_visual_coverage_is_complete():
    summary=coverage_summary()
    assert summary['required_visual_components']==185
    assert summary['covered_visual_components']==185
    assert summary['direct_visual_components']==157
    assert summary['composite_visual_components']==28
    assert summary['uncovered']==[]
