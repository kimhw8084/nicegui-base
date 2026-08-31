from __future__ import annotations

from pathlib import Path

from nicegui_base.design.css import build_css
from nicegui_base.design.tokens import LAYOUT_METRICS, RESPONSIVE_LAYOUT_METRICS
from nicegui_base.governance import run_governance
from nicegui_base.version import FRAMEWORK_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_v2_base_layout_metrics_preserve_final_effective_v173_geometry():
    assert LAYOUT_METRICS['shell_header_height'] == 60
    assert LAYOUT_METRICS['shell_sidebar_width'] == 256
    assert LAYOUT_METRICS['shell_sidebar_compact_width'] == 64
    assert LAYOUT_METRICS['page_gutter'] == 20
    assert LAYOUT_METRICS['control_height'] == 38
    assert (LAYOUT_METRICS['control_small'], LAYOUT_METRICS['control_medium'], LAYOUT_METRICS['control_large']) == (30, 34, 40)
    assert LAYOUT_METRICS['control_padding_x'] == 14
    assert LAYOUT_METRICS['icon_button_size'] == 38


def test_v2_responsive_layout_metrics_preserve_effective_cascade_not_dead_declarations():
    assert dict(RESPONSIVE_LAYOUT_METRICS['tablet']) == {'page_gutter': 16}
    assert dict(RESPONSIVE_LAYOUT_METRICS['phone']) == {'surface_padding': 16, 'overlay_edge_gap': 10}
    css = build_css().replace(' ', '')
    assert '@media(max-width:899px)' in css and '--cui-page-gutter:16px' in css
    assert '@media(max-width:599px)' in css and '--cui-surface-padding:16px' in css and '--cui-overlay-edge-gap:10px' in css


def test_v2_core_layout_and_density_tokens_have_one_declaration_authority():
    report = run_governance(ROOT)
    findings = [item for item in report.findings if item.rule == 'geometry.single-token-authority']
    assert not findings, [item.to_dict() for item in findings]


def test_v2_downstream_css_layers_consume_but_do_not_redeclare_core_authority():
    downstream = [
        ROOT / 'nicegui_base/layouts/css.py',
        ROOT / 'nicegui_base/components/css.py',
        ROOT / 'nicegui_base/design/constitution_css.py',
        ROOT / 'nicegui_base/design/hardening_css.py',
    ]
    protected = (
        '--cui-shell-header-height:', '--cui-shell-sidebar-width:',
        '--cui-shell-sidebar-compact-width:', '--cui-page-gutter:',
        '--cui-surface-padding:', '--cui-control-padding-x:', '--cui-icon-button-size:',
        '--cui-control-small:', '--cui-control-medium:', '--cui-control-large:', '--cui-overlay-edge-gap:',
    )
    for path in downstream:
        text = path.read_text(encoding='utf-8')
        assert not [token for token in protected if token in text], path


def test_v2_density_authority_keeps_compact_as_default_visual_contract():
    css = build_css().replace(' ', '')
    assert '--cui-control-height:38px' in css
    assert "[data-density='compact']" in css
    compact = css.split("[data-density='compact']", 1)[1].split('}', 1)[0]
    for fragment in ('--cui-control-height:38px', '--cui-control-small:30px', '--cui-control-medium:34px', '--cui-control-large:40px', '--cui-icon-button-size:38px', '--cui-control-padding-x:14px', '--cui-surface-padding:20px'):
        assert fragment in compact


def test_v2_packaged_certification_manifest_is_regenerated_from_current_source():
    import json
    from nicegui_base.certification.engine import combined_css

    manifest = json.loads((ROOT / 'nicegui_base/certification/certification_manifest.json').read_text(encoding='utf-8'))
    assert manifest['framework_version'] == FRAMEWORK_VERSION
    assert manifest['phase'] >= 35
    assert manifest['phase_35_v2_source_completion']['single_layout_density_token_authority'] is True
    assert manifest['combined_css_bytes'] == len(combined_css().encode('utf-8'))
