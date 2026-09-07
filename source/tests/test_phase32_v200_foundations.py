from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from nicegui_base import CANONICAL_VIEWPORTS, FRAMEWORK_VERSION, RELEASE_STATUS
from nicegui_base.certification.mac_browser import exhaustive_scenarios
from nicegui_base.governance import run_governance
from nicegui_base.governance.public_api import export_digest, public_api_snapshot
from nicegui_base.services import Command, CommandRegistry

ROOT = Path(__file__).resolve().parents[1]


def test_v2_release_authority_is_single_runtime_version_source():
    authority = json.loads((ROOT / 'nicegui_base/release_authority.json').read_text(encoding='utf-8'))
    assert authority['framework_version'] == FRAMEWORK_VERSION
    assert authority['nicegui_version'] == '3.15.0'
    assert RELEASE_STATUS == authority['release_status']
    assert FRAMEWORK_VERSION not in (ROOT / 'nicegui_base/version.py').read_text(encoding='utf-8')


def test_v2_governance_passes_current_source_tree():
    report = run_governance(ROOT)
    assert report.passed, [item.to_dict() for item in report.findings]


def test_v2_geometry_is_token_governed_across_dom_css_producers():
    from nicegui_base.design.css import build_css

    report = run_governance(ROOT)
    assert not [item for item in report.findings if item.rule in {'geometry.radius-token', 'geometry.single-token-authority'}]
    css = build_css().replace(' ', '')
    for token in ('--cui-radius-micro:5px', '--cui-radius-inner:8px', '--cui-radius-control:10px', '--cui-radius-surface:14px', '--cui-radius-overlay:18px', '--cui-radius-circle:50%'):
        assert token in css
    constitution = (ROOT / 'nicegui_base/design/constitution_css.py').read_text(encoding='utf-8')
    for token in ('--cui-radius-control:', '--cui-radius-surface:', '--cui-radius-overlay:'):
        assert token not in constitution


def test_v2_public_api_contract_is_signature_aware_and_deterministic():
    contract = json.loads((ROOT / 'PUBLIC_API_CONTRACT.json').read_text(encoding='utf-8'))
    snapshot = public_api_snapshot()
    assert contract['schema_version'] == 3
    assert contract['symbols'] == snapshot
    assert contract['sha256'] == export_digest(snapshot)
    command_params = [p['name'] for p in contract['symbols']['Command']['callable']['parameters']]
    assert command_params[-3:] == ['description', 'enabled', 'visible']


def test_command_registry_fuzzy_context_and_disabled_contract():
    registry = CommandRegistry()
    registry.register(Command('open-settings', 'Open Settings', lambda: 'ok', keywords=('preferences',)))
    registry.register(Command('admin-only', 'Admin Console', lambda: None, visible=False))
    registry.register(Command('locked', 'Locked Action', lambda: None, enabled=False))
    assert registry.search('stng')[0].key == 'open-settings'
    assert not any(item.key == 'admin-only' for item in registry.search('admin'))
    assert registry.search('locked')[0].key == 'locked'
    with pytest.raises(PermissionError):
        registry.execute('locked')


def test_command_registry_records_recent_only_after_successful_sync_and_async_execution():
    registry = CommandRegistry(recent_limit=2)
    registry.register(Command('one', 'One', lambda: 1))
    async def two():
        await asyncio.sleep(0)
        return 2
    registry.register(Command('two', 'Two', two))
    registry.execute('one')
    assert [item.key for item in registry.recent] == ['one']
    assert asyncio.run(registry.execute('two')) == 2
    assert [item.key for item in registry.recent] == ['two', 'one']


def test_v2_command_palette_keyboard_contract_is_present():
    source = (ROOT / 'nicegui_base/integrations/nicegui_content.py').read_text(encoding='utf-8')
    region = source[source.index('class CommandPalette:'):source.index('class BackgroundTaskIndicator:')]
    for token in ("key == 'Escape'", "key == 'ArrowDown'", "key == 'ArrowUp'", 'aria-disabled=', 'self.registry.execute(c.key)'):
        assert token in region


def test_v2_canonical_responsive_matrix_covers_six_required_widths():
    widths = [profile.width for profile in CANONICAL_VIEWPORTS.values()]
    assert widths == [390, 430, 768, 1024, 1280, 1440]
    exhaustive_widths = {scenario.width for scenario in exhaustive_scenarios(include_edge=False)}
    assert set(widths) <= exhaustive_widths


def test_v2_current_named_evidence_remains_truthfully_pending_until_target_certification():
    cert = json.loads((ROOT / 'CERTIFICATION_REPORT.json').read_text(encoding='utf-8'))
    clean = json.loads((ROOT / 'CLEAN_INSTALL_CERTIFICATION.json').read_text(encoding='utf-8'))
    assert cert['framework_version'] == FRAMEWORK_VERSION
    assert cert['release_certified'] is False and cert['target_runtime_status'] == 'PENDING'
    assert clean['passed'] is False and clean['status'] == f'NOT_EXECUTED_FOR_{FRAMEWORK_VERSION}'


def test_v2_modal_surfaces_have_programmatic_names_and_descriptions():
    interactions = (ROOT / 'nicegui_base/integrations/nicegui_interactions.py').read_text(encoding='utf-8')
    drawer = interactions[interactions.index('class _Drawer'):interactions.index('class DetailDrawer')]
    dialog = interactions[interactions.index('class Dialog'):interactions.index('class ConfirmDialog')]
    layout = (ROOT / 'nicegui_base/integrations/nicegui_layout.py').read_text(encoding='utf-8')
    app_info = layout[layout.index('class AppInfoDialog'):layout.index('class SegmentedControl')]
    for region in (drawer, dialog, app_info):
        assert 'aria-labelledby=' in region
        assert 'aria-describedby=' in region
        assert '.props(f\'id="{self.' in region or "props(f'id=\"{self." in region


def test_v2_global_layering_is_token_governed():
    report = run_governance(ROOT)
    assert not [item for item in report.findings if item.rule == 'geometry.layer-token']
    from nicegui_base.design.css import build_css
    authority = build_css().replace(' ', '')
    css = (ROOT / 'nicegui_base/design/hardening_css.py').read_text(encoding='utf-8').replace(' ', '')
    for token in ('--cui-layer-sticky:100', '--cui-app-header-z:600', '--cui-modal-z:3100', '--cui-toast-z:4000', '--cui-skip-link-z:4100'):
        assert token in authority
    assert all(f'z-index:var({token})' in css for token in ('--cui-layer-sticky', '--cui-app-header-z', '--cui-modal-z', '--cui-toast-z'))


def test_v2_platform_bundles_preserve_established_macos_linux_gate_separation():
    assert not (ROOT / 'windows_bundle').exists()
    for platform, setup_name in (('mac', 'setup_mac.sh'), ('linux', 'setup_linux.sh')):
        bundle = ROOT / f'{platform}_bundle'
        assert bundle.exists()
        setup = (bundle / setup_name).read_text(encoding='utf-8')
        run = (bundle / 'run_lab.sh').read_text(encoding='utf-8')
        cert_name = 'certify_mac.sh' if platform == 'mac' else 'certify_linux.sh'
        cert = (bundle / cert_name).read_text(encoding='utf-8')
        assert 'doctor --runtime-only --ignore-port --port 8080 --no-require-browser' in setup
        assert 'runtime-smoke --output' in setup
        assert 'doctor --runtime-only --port 8080 --no-require-browser' in run
        assert '--require-baseline' in cert


def test_v2_native_control_interaction_contract_is_state_complete():
    from nicegui_base import RangeSliderSpec, SliderSpec
    with pytest.raises(ValueError):
        SliderSpec(label='Bad', value=1, step=0)
    with pytest.raises(ValueError):
        RangeSliderSpec(label='Bad', low=1, high=2, step=0)
    source = (ROOT / 'nicegui_base/integrations/nicegui_components.py').read_text(encoding='utf-8')
    interactive = source[source.index('class InteractiveCard'):source.index('class StatusBadge')]
    checkbox_group = source[source.index('class CheckboxGroup'):source.index('class RadioGroup')]
    slider = source[source.index('class Slider:'):source.index('class RangeSlider:')]
    range_slider = source[source.index('class RangeSlider:'):source.index('class _NativeTemporalField')]
    assert "keydown.space" in interactive and "keydown.enter" in interactive
    assert 'disabled: bool = False, on_change:' in checkbox_group
    assert "self.control.on('change', on_change)" in slider
    assert "self.low_control.on('change', on_change)" in range_slider
    assert "self.high_control.on('change', on_change)" in range_slider
    assert 'Number(lo.value)>Number(hi.value)' in range_slider
    assert 'Number(hi.value)<Number(lo.value)' in range_slider
    assert '-step' not in range_slider and '+step' not in range_slider


def test_v2_browser_certification_has_no_phantom_routes():
    from nicegui_base.certification.mac_browser import KEY_ROUTES
    from nicegui_base.certification.mac_lab import ROUTES
    registered = {route.path for route in ROUTES}
    assert set(KEY_ROUTES) <= registered
    assert '/feedback' not in KEY_ROUTES
    source = (ROOT / 'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    assert "elif route=='/feedback'" not in source


def test_v2_certification_includes_korean_and_mixed_content_torture_fixture():
    lab = (ROOT / 'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    browser = (ROOT / 'nicegui_base/certification/mac_browser.py').read_text(encoding='utf-8')
    assert 'cui-v2-i18n-stress' in lab
    assert '설비 이상 분석' in lab
    assert "elif route=='/states':" in browser
    assert 'mixed Korean/English stress content overflowed its governed surface' in browser
