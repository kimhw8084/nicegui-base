from __future__ import annotations

import json
from pathlib import Path

from nicegui_base.certification.mac_browser import REFERENCE_ROUTES, standard_scenarios
from nicegui_base.certification.mac_lab import ROUTES
from nicegui_base.supply_chain import CERTIFICATION_DEPENDENCIES, RUNTIME_DEPENDENCIES, build_spdx_sbom
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_v17_final_identity_and_company_index_runtime_requirements():
    assert bool(FRAMEWORK_VERSION) and FRAMEWORK_VERSION == __import__('nicegui_base.version', fromlist=['RELEASE_AUTHORITY']).RELEASE_AUTHORITY['framework_version']
    assert NICEGUI_VERSION == '3.15.0'
    runtime = [line.strip() for line in (ROOT/'requirements.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    assert runtime == ['nicegui==3.15.0']
    cert = (ROOT/'requirements-certification.txt').read_text()
    assert '-r requirements.txt' in cert
    assert 'playwright==1.62.0' in cert and 'Pillow==12.3.0' in cert


def test_setup_is_company_index_only_and_requires_runtime_proof_before_success():
    source=(ROOT/'linux_bundle/setup_linux.sh').read_text()
    assert 'pip install -r "$REQ"' in source
    assert 'pip install --no-deps "$WHEEL"' in source
    assert 'public-PyPI or bundled-wheel fallbacks' in source
    assert 'files.pythonhosted.org' not in source and 'pypi.org/project' not in source
    assert source.index('runtime-contract') < source.index('doctor --runtime-only --ignore-port --port 8080 --no-require-browser') < source.index('runtime-smoke') < source.index('SETUP COMPLETE')


def test_standard_browser_matrix_covers_all_routes_desktop_and_phone_and_all_reference_apps_tablet():
    routes=tuple(r.path for r in ROUTES)
    assert len(routes)==21 and len(set(routes))==21
    scenarios=standard_scenarios(include_edge=False)
    desktop=next(s for s in scenarios if s.browser=='chrome' and s.viewport=='desktop' and s.density=='compact')
    phone=next(s for s in scenarios if s.browser=='chrome' and s.viewport=='phone')
    tablet=next(s for s in scenarios if s.browser=='chrome' and s.viewport=='tablet')
    assert desktop.routes == routes
    assert phone.routes == routes
    assert set(REFERENCE_ROUTES) <= set(tablet.routes)
    assert len(REFERENCE_ROUTES)==10


def test_final_certification_manifest_declares_v17_release_gates():
    data=json.loads((ROOT/'nicegui_base/certification/certification_manifest.json').read_text())
    assert data['framework_version']==FRAMEWORK_VERSION
    assert data['phase']>=32
    assert data['release_stage']=='v2_0_release_candidate'
    gates=set(data['required_gates'])
    for gate in {
        'production_requirements_company_index_only','installed_nicegui_runtime_contract','real_22_route_server_smoke',
        'full_22_route_desktop_browser_matrix','full_22_route_phone_browser_matrix','tablet_reference_application_matrix',
        'live_183_visual_component_coverage','clean_install','ai_seed_install','immutable_bundle_hash_inventory','zip_roundtrip_integrity',
        'human_visual_baseline_approval',
    }:
        assert gate in gates


def test_sbom_separates_production_and_certification_dependencies():
    assert RUNTIME_DEPENDENCIES == {'nicegui':'3.15.0'}
    assert CERTIFICATION_DEPENDENCIES == {'playwright':'1.62.0','Pillow':'12.3.0'}
    sbom=build_spdx_sbom()
    rels=sbom['relationships']
    assert any(r['relationshipType']=='DEPENDS_ON' and r['relatedSpdxElement']=='SPDXRef-Package-nicegui' for r in rels)
    optional=[r for r in rels if r['relationshipType']=='OPTIONAL_DEPENDENCY_OF']
    assert len(optional)==2


def test_historical_final_release_guide_is_preserved_but_not_seeded_to_current_agents():
    source=(ROOT/'docs/V17_FINAL_CERTIFICATION_AND_DEPLOYMENT.md').read_text()
    embedded=(ROOT/'nicegui_base/ai/guides/V17_FINAL_CERTIFICATION_AND_DEPLOYMENT.md').read_text()
    scaffold=(ROOT/'nicegui_base/ai/scaffold.py').read_text()
    assert source == embedded
    assert "'V17_FINAL_CERTIFICATION_AND_DEPLOYMENT.md'" not in scaffold
    assert 'SETUP COMPLETE' in source and 'all 22 routes' in source
