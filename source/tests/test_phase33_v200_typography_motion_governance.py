from __future__ import annotations

from pathlib import Path

from nicegui_base.design.css import build_css
from nicegui_base.design.tokens import FONT_SIZES, FONT_WEIGHTS, MOTION_DURATIONS_MS, TYPOGRAPHY
from nicegui_base.governance import run_governance
from nicegui_base.governance.typography_motion_contract import scan_typography_motion_contract

ROOT = Path(__file__).resolve().parents[1]


def test_v2_typography_and_motion_are_token_governed_across_rendered_sources():
    report = run_governance(ROOT)
    blocked = [item for item in report.findings if item.rule.startswith(('type.', 'motion.'))]
    assert not blocked, [item.to_dict() for item in blocked]


def test_v2_governance_rejects_raw_typography_and_motion_hotfixes(tmp_path: Path):
    package = tmp_path / 'nicegui_base'
    package.mkdir()
    bad = package / 'bad_css.py'
    bad.write_text("CSS='''.x{font-size:13px;line-height:18px;font-weight:650;transition:opacity 140ms ease}.y{animation:spin .7s linear}'''\n", encoding='utf-8')
    findings = scan_typography_motion_contract(tmp_path)
    rules = {item.rule for item in findings}
    assert {'type.font-size-token', 'type.line-height-token', 'type.font-weight-token', 'motion.duration-token', 'motion.easing-token'} <= rules


def test_v2_semantic_typography_hierarchy_matches_effective_product_hierarchy():
    assert TYPOGRAPHY['display']['size'] > TYPOGRAPHY['page_title']['size'] > TYPOGRAPHY['heading']['size'] > TYPOGRAPHY['subheading']['size'] > TYPOGRAPHY['body']['size']
    assert TYPOGRAPHY['page_title'] == {'size': 26, 'line': 32, 'weight': 700, 'tracking': -0.03}
    assert TYPOGRAPHY['app_identity']['size'] == 17
    assert TYPOGRAPHY['app_identity']['weight'] == 780
    assert TYPOGRAPHY['profile_name']['weight'] > TYPOGRAPHY['profile_hint']['weight']


def test_v2_css_exports_governed_scale_variables_needed_by_legacy_precision_surfaces():
    css = build_css()
    for key, value in FONT_SIZES.items():
        assert f'--cui-font-size-{key}: {value}px;' in css
    for key, value in FONT_WEIGHTS.items():
        assert f'--cui-font-weight-{key}: {value};' in css
    for key, value in MOTION_DURATIONS_MS.items():
        assert f"--cui-duration-{key.replace('_','-')}: {value}ms;" in css


def test_v2_echarts_uses_python_token_authority_instead_of_numeric_type_or_duration_literals():
    source = (ROOT / 'nicegui_base/visualization/options.py').read_text(encoding='utf-8')
    assert "'fontSize': FONT_SIZES['11']" in source
    assert "'fontWeight': FONT_WEIGHTS['650']" in source
    assert "'animationDuration': MOTION_DURATIONS_MS['chart']" in source
    assert "'animationDurationUpdate': MOTION_DURATIONS_MS['shell']" in source
