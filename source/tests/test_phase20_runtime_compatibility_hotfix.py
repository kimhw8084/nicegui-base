from __future__ import annotations

from pathlib import Path

from nicegui_base.certification.live_lab import ROUTES
from nicegui_base.certification.nicegui_runtime_contract import iter_ui_factory_calls, scan_source_contract
from nicegui_base.certification.runtime_smoke import ERROR_PATTERNS
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_phase20_identity_and_exact_runtime_pin():
    assert bool(FRAMEWORK_VERSION) and FRAMEWORK_VERSION == __import__('nicegui_base.version', fromlist=['RELEASE_AUTHORITY']).RELEASE_AUTHORITY['framework_version']
    assert NICEGUI_VERSION == '3.15.0'
    pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert f'version = "{FRAMEWORK_VERSION}"' in pyproject
    assert '"nicegui==3.15.0"' in pyproject


def test_mobile_navigation_is_company_owned_and_does_not_depend_on_left_drawer():
    source = (ROOT / 'nicegui_base/integrations/nicegui_layout.py').read_text(encoding='utf-8')
    start = source.index('class MobileNavigationDrawer')
    end = source.index('class UserMenu', start)
    body = source[start:end]
    assert "dataset.mobileNav='open'" in body
    assert "dataset.mobileNav='closed'" in body
    assert 'ui.left_drawer' not in body
    assert 'self.element.open' not in body
    assert 'self.element.close' not in body


def test_echart_updates_mutate_read_only_options_and_native_fullscreen_is_not_awaited():
    source = (ROOT / 'nicegui_base/integrations/nicegui_visualization.py').read_text(encoding='utf-8')
    assert 'self.element.options=' not in source.replace(' ', '')
    assert 'self.element.options.clear()' in source
    assert 'self.element.options.update(options)' in source
    assert 'await ui.fullscreen.enter()' not in source
    assert 'await ui.fullscreen.toggle()' not in source


def test_source_contract_is_clean_and_covers_all_direct_nicegui_factories():
    assert scan_source_contract(ROOT) == ()
    calls = tuple(iter_ui_factory_calls(ROOT))
    factories = {factory for _, _, factory, _ in calls}
    assert len(calls) >= 700
    assert len(factories) >= 50
    assert {'echart', 'select', 'aggrid', 'upload', 'dialog', 'menu', 'context_menu'} <= factories
    assert 'left_drawer' not in factories


def test_source_contract_detects_read_only_echart_assignment(tmp_path: Path):
    package = tmp_path / 'nicegui_base' / 'integrations'
    package.mkdir(parents=True)
    (package / 'nicegui_visualization.py').write_text('def bad(self, options):\n    self.element.options = options\n', encoding='utf-8')
    issues = scan_source_contract(tmp_path)
    assert any(issue.code == 'ECHART_OPTIONS_ASSIGNMENT' for issue in issues)


def test_linux_setup_requires_runtime_contract_and_real_all_route_smoke_before_success():
    source = (ROOT / 'linux_bundle/setup_linux.sh').read_text(encoding='utf-8')
    assert f"nicegui_base-{FRAMEWORK_VERSION}-*.whl" in source
    contract = source.index('runtime-contract')
    doctor = source.index('doctor --runtime-only --ignore-port --port 8080 --no-require-browser')
    smoke = source.index('runtime-smoke')
    complete = source.index('SETUP COMPLETE')
    assert contract < doctor < smoke < complete


def test_platform_cli_exposes_runtime_contract_and_smoke_commands():
    cli = (ROOT / 'nicegui_base/cli.py').read_text(encoding='utf-8')
    pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    assert "sub.add_parser('runtime-contract'" in cli
    assert "sub.add_parser('runtime-smoke'" in cli
    assert 'nicegui-base-runtime-contract' in pyproject
    assert 'nicegui-base-runtime-smoke' in pyproject


def test_runtime_smoke_covers_all_routes_and_scans_high_value_python_failures():
    assert len(ROUTES) == 21
    assert len({route.path for route in ROUTES}) == 21
    assert 'AttributeError:' in ERROR_PATTERNS
    assert 'TypeError:' in ERROR_PATTERNS
    assert 'RuntimeError:' in ERROR_PATTERNS
    assert 'Exception in ASGI application' in ERROR_PATTERNS
    source = (ROOT / 'nicegui_base/certification/runtime_smoke.py').read_text(encoding='utf-8')
    assert "TemporaryDirectory(prefix='nicegui-base-runtime-smoke-')" in source
    assert "'/healthz', '/readyz'" in source
    assert "route.path for route in ROUTES" in source
