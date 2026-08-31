from pathlib import Path
from unittest.mock import patch

from nicegui_base.certification.live_preflight import run_preflight
from nicegui_base.version import FRAMEWORK_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_release_identity_is_172():
    assert bool(FRAMEWORK_VERSION) and FRAMEWORK_VERSION == __import__('nicegui_base.version', fromlist=['RELEASE_AUTHORITY']).RELEASE_AUTHORITY['framework_version']
    assert f'version = "{FRAMEWORK_VERSION}"' in (ROOT / 'pyproject.toml').read_text(encoding='utf-8')


def test_runtime_profile_makes_certification_packages_nonfatal():
    with patch('nicegui_base.certification.live_preflight._package_version') as pkg, \
         patch('nicegui_base.certification.live_preflight.discover_browsers', return_value={}), \
         patch('nicegui_base.certification.live_preflight._port_available', return_value=False), \
         patch('nicegui_base.certification.live_preflight.validate_visual_package', return_value=()), \
         patch('nicegui_base.certification.live_preflight.coverage_summary', return_value={'uncovered': [], 'covered_visual_components': 183, 'required_visual_components': 183, 'direct_visual_components': 155, 'composite_visual_components': 28}), \
         patch('nicegui_base.certification.live_preflight.load_compatibility_manifest', return_value={'nicegui_version':'3.15.0'}), \
         patch('nicegui_base.certification.live_preflight.run_installed_runtime_contract') as contract:
        def versions(name):
            return '3.15.0' if name == 'nicegui' else None
        pkg.side_effect = versions
        contract.return_value.ok = True
        contract.return_value.factories_checked = 50
        contract.return_value.calls_checked = 840
        contract.return_value.source_issues = ()
        contract.return_value.runtime_issues = ()
        checks = run_preflight(port=8080, require_browser=False, require_edge=False, require_certification_deps=False, require_port=False)
    by_key = {c.key:c for c in checks}
    assert by_key['playwright'].status == 'skip' and not by_key['playwright'].required
    assert by_key['pillow'].status == 'skip' and not by_key['pillow'].required
    assert by_key['port'].status == 'skip' and not by_key['port'].required
    assert not [c for c in checks if c.required and c.status == 'fail']


def test_certification_profile_still_requires_browser_dependencies_and_port():
    with patch('nicegui_base.certification.live_preflight._package_version') as pkg, \
         patch('nicegui_base.certification.live_preflight.discover_browsers', return_value={}), \
         patch('nicegui_base.certification.live_preflight._port_available', return_value=False), \
         patch('nicegui_base.certification.live_preflight.validate_visual_package', return_value=()), \
         patch('nicegui_base.certification.live_preflight.coverage_summary', return_value={'uncovered': [], 'covered_visual_components': 183, 'required_visual_components': 183, 'direct_visual_components': 155, 'composite_visual_components': 28}), \
         patch('nicegui_base.certification.live_preflight.load_compatibility_manifest', return_value={'nicegui_version':'3.15.0'}), \
         patch('nicegui_base.certification.live_preflight.run_installed_runtime_contract') as contract:
        def versions(name):
            return '3.15.0' if name == 'nicegui' else None
        pkg.side_effect = versions
        contract.return_value.ok = True
        contract.return_value.factories_checked = 50
        contract.return_value.calls_checked = 840
        contract.return_value.source_issues = ()
        contract.return_value.runtime_issues = ()
        checks = run_preflight(port=8080, require_browser=False, require_edge=False, require_certification_deps=True, require_port=True)
    by_key = {c.key:c for c in checks}
    assert by_key['playwright'].status == 'fail' and by_key['playwright'].required
    assert by_key['pillow'].status == 'fail' and by_key['pillow'].required
    assert by_key['port'].status == 'fail' and by_key['port'].required


def test_setup_uses_runtime_profile_and_ephemeral_smoke_port():
    for rel in ('linux_bundle/setup_linux.sh','mac_bundle/setup_mac.sh'):
        text=(ROOT/rel).read_text(encoding='utf-8')
        assert 'doctor --runtime-only --ignore-port --port 8080 --no-require-browser' in text
        assert 'runtime-smoke --output' in text
        assert '--port 8080' not in text.split('runtime-smoke',1)[1].split('\n',1)[0]


def test_run_lab_requires_its_port_but_not_browser_certification_packages():
    for rel in ('linux_bundle/run_lab.sh','mac_bundle/run_lab.sh'):
        text=(ROOT/rel).read_text(encoding='utf-8')
        assert 'doctor --runtime-only --port 8080 --no-require-browser' in text
        assert '--ignore-port' not in text
