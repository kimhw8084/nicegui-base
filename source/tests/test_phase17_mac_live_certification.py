from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from nicegui_base.certification.mac_baseline import approve_visual_baseline, verify_visual_baseline
from nicegui_base.certification.mac_browser import MacBrowserReport, RouteBrowserResult, exhaustive_scenarios, standard_scenarios
from nicegui_base.certification.mac_coverage import coverage_summary, live_component_coverage
from nicegui_base.certification.mac_lab import ROUTES
from nicegui_base.certification.visual_audit import audit_framework_visual_sources
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_phase17_identity_and_cli_contract():
    assert bool(FRAMEWORK_VERSION) and FRAMEWORK_VERSION == __import__('nicegui_base.version', fromlist=['RELEASE_AUTHORITY']).RELEASE_AUTHORITY['framework_version']
    assert NICEGUI_VERSION == '3.15.0'
    text = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert f'version = "{FRAMEWORK_VERSION}"' in text
    assert 'nicegui==3.15.0' in text
    for command in ('nicegui-base-mac-lab', 'nicegui-base-mac-preflight', 'nicegui-base-mac-certify', 'nicegui-base-mac-approve-baseline'):
        assert command in text
    assert 'mac-cert = [' in text and 'playwright' in text and 'Pillow' in text


def test_live_lab_has_unique_21_routes_and_all_ten_patterns():
    paths = [route.path for route in ROUTES]
    assert len(paths) == 21
    assert len(set(paths)) == 21
    patterns = [path for path in paths if path.startswith('/patterns/')]
    assert len(patterns) == 10
    assert set(patterns) == {
        '/patterns/dashboard', '/patterns/explorer', '/patterns/master-detail', '/patterns/crud', '/patterns/monitoring',
        '/patterns/search', '/patterns/settings', '/patterns/wizard', '/patterns/comparison', '/patterns/analysis',
    }


def test_every_public_visual_integration_has_a_live_review_route():
    valid_routes = {route.path for route in ROUTES}
    coverage = live_component_coverage()
    summary = coverage_summary()
    assert summary['required_visual_components'] >= 175
    assert summary['covered_visual_components'] == summary['required_visual_components']
    assert summary['uncovered'] == []
    assert summary['direct_visual_components'] >= 150
    assert summary['composite_visual_components'] <= 30
    assert summary['direct_visual_components'] + summary['composite_visual_components'] == summary['required_visual_components']
    assert all(item.route in valid_routes for item in coverage)
    assert all(item.coverage_kind in {'direct','composite'} for item in coverage)




def test_coverage_route_builder_map_matches_live_routes():
    from nicegui_base.certification.mac_coverage import ROUTE_BUILDERS
    assert set(ROUTE_BUILDERS) == {route.path for route in ROUTES}


def test_browser_matrices_cover_every_route_in_primary_chrome_scenarios():
    paths = {route.path for route in ROUTES}
    standard = standard_scenarios(include_edge=False)
    exhaustive = exhaustive_scenarios(include_edge=False)
    assert paths <= set(standard[0].routes)
    assert paths <= set(standard[1].routes)
    assert all(s.browser == 'chrome' for s in standard)
    assert any(s.viewport == 'phone' and s.theme == 'dark' for s in standard)
    assert any(s.width in {768, 1024} and s.theme == 'dark' for s in exhaustive)
    assert any(s.density == 'dense' for s in exhaustive)


def test_visual_audit_catches_indirect_stock_notify(tmp_path: Path):
    integrations = tmp_path / 'nicegui_base' / 'integrations'
    integrations.mkdir(parents=True)
    (integrations / 'bad.py').write_text("def render():\n    _ui().notify('stock')\n", encoding='utf-8')
    issues = audit_framework_visual_sources(tmp_path)
    assert any(issue.code == 'STOCK_NOTIFY' for issue in issues)


def test_current_integrations_have_no_forbidden_stock_visual_paths():
    assert audit_framework_visual_sources(ROOT) == ()


def test_baseline_approval_is_hash_locked_and_detects_tampering(tmp_path: Path):
    output = tmp_path / 'output'; shots = output / 'screenshots'; shots.mkdir(parents=True)
    (shots / 'chrome-desktop-light-compact__overview.png').write_bytes(b'png-one')
    report = {
        'passed': True,
        'browsers': {'chrome': 'test-browser'},
        'results': [{'status': 'pass', 'route': '/', 'scenario': 'chrome-desktop-light-compact'}],
    }
    (output / 'MAC_BROWSER_REPORT.json').write_text(json.dumps(report), encoding='utf-8')
    baseline = tmp_path / 'baseline'
    approval = approve_visual_baseline(output, baseline)
    assert approval.screenshot_count == 1
    ok, detail = verify_visual_baseline(baseline)
    assert ok and '1 approved' in detail
    (baseline / 'chrome-desktop-light-compact__overview.png').write_bytes(b'tampered')
    ok, detail = verify_visual_baseline(baseline)
    assert not ok and 'hashes differ' in detail


def test_browser_report_warns_without_baseline_but_fails_only_on_failures():
    warning = RouteBrowserResult('s', '/', 'warning', 'baseline missing')
    passed = RouteBrowserResult('s', '/controls', 'pass', 'ok')
    report = MacBrowserReport((warning, passed), {'chrome': 'x'}, None)
    assert report.passed
    failed = MacBrowserReport((RouteBrowserResult('s', '/', 'fail', 'stock visual leak'),), {'chrome': 'x'}, None)
    assert not failed.passed


def test_mac_bundle_shell_contracts_exist_and_are_executable():
    bundle = ROOT / 'mac_bundle'
    for name in ('setup_mac.sh', 'run_lab.sh', 'certify_mac.sh', 'approve_visual_baseline.sh', 'reset_lab.sh'):
        path = bundle / name
        assert path.exists()
        assert path.stat().st_mode & 0o111
    setup = (bundle / 'setup_mac.sh').read_text(encoding='utf-8')
    assert 'python3.13' in setup and 'python3.12' in setup and 'python3.11' in setup
    assert f'nicegui_base-{FRAMEWORK_VERSION}' in setup
    assert 'nicegui_base-1.5.0' not in setup
    assert 'requirements.txt' in setup and '--no-deps' in setup


class _FakeElement:
    def __init__(self, *args, **kwargs):
        self.value = kwargs.get('value')
        self.visible = True
        self.client = self
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def __call__(self, *args, **kwargs): return self
    def __await__(self):
        async def _done(): return None
        return _done().__await__()
    def __getattr__(self, _name):
        return lambda *args, **kwargs: self


class _FakeUI(_FakeElement):
    def page(self, _path):
        return lambda fn: fn
    def dark_mode(self):
        return _FakeElement()


class _Storage:
    def __init__(self):
        self.user = {}
        self.tab = {}
        self.browser = {}
        self.general = {}


class _FakeApp(_FakeElement):
    def __init__(self):
        super().__init__(); self.storage = _Storage()


def test_all_22_route_builders_construct_under_synthetic_nicegui(monkeypatch):
    # This catches invalid page slots/model combinations without claiming real browser rendering.
    fake_ui = _FakeUI(); fake_app = _FakeApp()
    nicegui = types.ModuleType('nicegui'); nicegui.ui = fake_ui; nicegui.app = fake_app
    events = types.ModuleType('nicegui.events')
    events.GenericEventArguments = type('GenericEventArguments', (), {})
    events.KeyEventArguments = type('KeyEventArguments', (), {})
    monkeypatch.setitem(sys.modules, 'nicegui', nicegui)
    monkeypatch.setitem(sys.modules, 'nicegui.events', events)
    import nicegui_base.certification.mac_lab as lab
    failures = []
    for route in lab.ROUTES:
        try:
            route.builder(None)
        except Exception as exc:
            failures.append((route.path, type(exc).__name__, str(exc)))
    assert failures == []


def test_mac_certification_child_process_uses_neutral_cwd():
    source=(ROOT/'nicegui_base/certification/mac_certify.py').read_text(encoding='utf-8')
    assert 'cwd=str(output_dir)' in source
    assert 'cwd=str(root or Path.cwd())' not in source
    assert "BASELINE_MANIFEST.json" in source


def test_sbom_includes_exact_mac_certification_dependencies():
    from nicegui_base.supply_chain import build_spdx_sbom
    packages={item['name']: item['versionInfo'] for item in build_spdx_sbom()['packages']}
    assert packages['nicegui'] == '3.15.0'
    assert packages['playwright'] == '1.62.0'
    assert packages['Pillow'] == '12.3.0'
