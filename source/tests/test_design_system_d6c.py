from __future__ import annotations

from pathlib import Path

from nicegui_base.ai import validate_app, validate_python_file
from nicegui_base.design import (
    BORDER_WIDTHS, ELEVATION, INTERACTIVE_STATES, SEMANTIC_GAPS, Z_INDEX,
    build_css, build_design_system,
)


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def test_d6c_design_system_exposes_one_complete_token_authority():
    system = build_design_system()
    assert system.semantic_gaps is SEMANTIC_GAPS
    assert system.border_widths is BORDER_WIDTHS
    assert system.elevation is ELEVATION
    assert system.z_index is Z_INDEX
    assert system.interactive_states is INTERACTIVE_STATES
    assert set(system.elevation) == {'flat', 'raised', 'overlay'}
    assert set(system.z_index) == {'layer_sticky', 'sidebar', 'app_header', 'local_popup', 'overlay', 'overlay_backdrop', 'modal', 'tooltip', 'toast', 'skip_link'}


def test_d6c_css_emits_new_domains_and_semantic_helpers():
    css = build_css()
    for token in (
        '--cui-gap-page', '--cui-gap-stack', '--cui-border-width-subtle',
        '--cui-elevation-raised', '--cui-sidebar-z', '--cui-state-disabled-opacity',
        '--cui-breakpoint-phone',
    ):
        assert token in css


def test_d6c_hardening_consumes_generated_z_index_authority():
    from nicegui_base.design.hardening_css import build_hardening_css
    hardening = build_hardening_css()
    assert '--cui-sidebar-z: 500' not in hardening
    assert 'z-index:var(--cui-sidebar-z)' in hardening


def test_d6c_design_value_linter_flags_application_literals_but_accepts_tokens(tmp_path):
    bad = _write(tmp_path, 'pages/reference.py', 'CSS = ".panel { padding: 13px; color: #ff0000; }"\n')
    assert 'AI018' in {issue.code for issue in validate_python_file(bad, root=tmp_path)}

    good = _write(tmp_path, 'pages/semantic.py', 'CSS = ".panel { padding: var(--cui-gap-stack); color: var(--cui-text-primary); }"\n')
    assert 'AI018' not in {issue.code for issue in validate_python_file(good, root=tmp_path)}


def test_d6c_design_value_linter_allowlists_framework_design_files(tmp_path):
    path = _write(tmp_path, 'design/implementation.py', 'CSS = ".panel { padding: 13px; color: #ff0000; }"\n')
    assert 'AI018' not in {issue.code for issue in validate_python_file(path, root=tmp_path)}
    css = _write(tmp_path, 'design/implementation.css', '.panel { padding: 13px; color: #ff0000; }\n')
    assert validate_app(tmp_path).issues == ()


def test_d6c_reference_route_and_all_families_are_source_visible():
    app = Path(__file__).parents[1] / 'nicegui_base/workbench/app.py'
    reference = Path(__file__).parents[1] / 'nicegui_base/workbench/design_system_reference.py'
    app_text = app.read_text(encoding='utf-8')
    ref_text = reference.read_text(encoding='utf-8')
    assert "ui.page('/design')(design_system_page)" in app_text
    for family in ('spacing', 'semantic-gaps', 'radii', 'typography', 'surfaces-colors', 'borders', 'elevation', 'density', 'breakpoints', 'motion', 'z-index', 'interactive-states'):
        assert family in ref_text
