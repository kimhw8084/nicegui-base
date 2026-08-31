from pathlib import Path

from nicegui_base.certification.mac_coverage import coverage_summary
from nicegui_base.integrations.nicegui_theme import build_framework_css

ROOT = Path(__file__).resolve().parents[1]


def test_production_requirements_are_company_index_runtime_only():
    runtime = (ROOT / 'requirements.txt').read_text(encoding='utf-8')
    cert = (ROOT / 'requirements-certification.txt').read_text(encoding='utf-8')
    assert 'nicegui==3.15.0' in runtime
    assert 'playwright' not in runtime.lower()
    assert 'pillow' not in runtime.lower()
    assert '-r requirements.txt' in cert
    assert 'playwright==1.62.0' in cert
    assert 'Pillow==12.3.0' in cert


def test_linux_setup_is_requirements_first_and_has_no_public_or_extra_fallback():
    setup = (ROOT / 'linux_bundle/setup_linux.sh').read_text(encoding='utf-8')
    assert 'pip install -r "$REQ"' in setup
    assert 'pip install --no-deps "$WHEEL"' in setup
    assert '$WHEEL[live-cert]' not in setup
    assert '--find-links' not in setup
    assert 'public-PyPI or bundled-wheel fallbacks' in setup
    assert setup.index('pip install -r "$REQ"') < setup.index('pip install --no-deps "$WHEEL"')
    assert setup.index('runtime-contract') < setup.index('runtime-smoke') < setup.index('SETUP COMPLETE')


def test_shell_header_and_mobile_navigation_are_company_owned():
    source = (ROOT / 'nicegui_base/integrations/nicegui_layout.py').read_text(encoding='utf-8')
    shell = source[source.index('class AppShell'):source.index('class PageHeader')]
    mobile = source[source.index('class MobileNavigationDrawer'):source.index('class UserMenu')]
    assert "ui.element('header').classes('cui-app-header')" in shell
    assert 'ui.header(' not in shell
    assert 'ui.left_drawer' not in mobile
    assert "dataset.mobileNav='open'" in mobile
    assert "dataset.mobileNav='closed'" in mobile


def test_mobile_trigger_is_not_part_of_application_title_brand():
    source = (ROOT / 'nicegui_base/integrations/nicegui_layout.py').read_text(encoding='utf-8')
    shell = source[source.index('class AppShell'):source.index('class PageHeader')]
    brand = shell[shell.index("classes('cui-shell-brand')"):shell.index("classes('cui-shell-actions')")]
    actions = shell[shell.index("classes('cui-shell-actions')"):shell.index('if self.config.navigation and self.config.sidebar')]
    assert 'cui-shell-mobile-menu' not in brand
    assert 'cui-shell-mobile-menu' in actions


def test_v17_shell_css_has_single_responsive_geometry_and_compact_footer_targets():
    css = build_framework_css()
    compact_css = css.replace(' ', '')
    assert 'COMPANY UI v1.7 PHASE 1' in css
    assert compact_css.count('--cui-shell-header-height:60px') == 1
    assert compact_css.count('--cui-shell-sidebar-width:256px') == 1
    assert compact_css.count('--cui-shell-sidebar-compact-width:64px') == 1
    assert '.cui-app-main{padding-top:var(--cui-shell-header-height)!important' in css
    assert '.cui-page-header{align-items:flex-start!important;padding:0 0 14px!important' in css
    assert "html[data-sidebar='compact'] .cui-sidebar-footer__action.q-btn{width:36px!important;height:36px!important" in css
    assert "html[data-mobile-nav='open'] .cui-mobile-nav-drawer{transform:translateX(0)!important" in css


def test_environment_badges_use_readable_surface_plus_semantic_dot():
    css = build_framework_css()
    assert '.cui-environment-badge::before' in css
    assert '.cui-environment-badge--development::before{background:var(--cui-info)' in css
    assert '.cui-environment-badge--staging::before{background:var(--cui-warning)' in css
    assert '.cui-environment-badge--production::before{background:var(--cui-success)' in css
    assert 'background:var(--cui-surface-secondary)!important;color:var(--cui-text-secondary)!important' in css


def test_shell_primitives_uses_canonical_shell_and_no_competing_mobile_action():
    source = (ROOT / 'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    section = source[source.index('def _shell_primitives'):source.index('def _overview')]
    assert "shell = _shell(" in section
    assert 'Button(\'Open mobile navigation\'' not in section
    assert 'standalone mobile-navigation demo action' in section


def test_visual_coverage_remains_complete_after_shell_architecture_change():
    summary = coverage_summary()
    assert summary['required_visual_components'] == 183
    assert summary['covered_visual_components'] == 183
    assert summary['uncovered'] == []
