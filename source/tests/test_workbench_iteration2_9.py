from __future__ import annotations

import io
import json
import zipfile


def test_all_canonical_patterns_have_non_mutating_interaction_contracts():
    from nicegui_base.workbench.interaction_contract import action_specs_for_pattern
    patterns = ('dashboard','monitoring','data_explorer','master_detail','analysis_workspace','comparison','crud','search','settings','wizard')
    for pattern in patterns:
        actions = action_specs_for_pattern(pattern)
        assert actions, pattern
        assert len({item.key for item in actions}) == len(actions)
        assert all(not item.provider_mutation for item in actions)


def test_interaction_contract_signature_and_canonical_drift_detection():
    from nicegui_base.workbench.interaction_contract import interaction_contract_for_project, validate_interaction_contract
    contract = interaction_contract_for_project({'pattern_key':'data_explorer'})
    assert validate_interaction_contract(contract) == ()
    contract['pages'][0]['actions'][0]['label'] = 'Something else'
    findings = validate_interaction_contract(contract)
    assert 'interaction_contract:canonical_actions:home' in findings
    assert 'interaction_contract:signature_mismatch' in findings


def test_single_page_generation_wires_governed_workflow_actions():
    from nicegui_base.workbench.builder import BuilderModel
    model = BuilderModel(); model.apply_golden_starter('record-manager')
    payload, report = model.generate(); assert report.ok, report.findings
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert '.nicegui_base/interaction_contract.json' in names
        assert 'services/app_workflow.py' in names
        contract = json.loads(archive.read('.nicegui_base/interaction_contract.json'))
        assert contract['provider_mutation_policy'] == 'none'
        home = archive.read('pages/home.py').decode('utf-8')
        assert 'create_page_workflow' in home
        assert 'workflow.execute(' in home
        workflow = archive.read('services/app_workflow.py').decode('utf-8')
        assert 'NiceGUIStateServices.tab_state()' in workflow
        assert "self._set('saved_view'" in workflow
        assert 'provider data was not changed' in workflow


def test_multi_page_interaction_contract_matches_blueprint_routes_and_patterns():
    from nicegui_base.workbench.builder import BuilderModel
    model = BuilderModel(); model.apply_golden_starter('operations-dashboard')
    model.set_blueprint('engineering-control-center')
    payload, report = model.generate(); assert report.ok, report.findings
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        blueprint = json.loads(archive.read('.nicegui_base/app_blueprint.json'))
        interaction = json.loads(archive.read('.nicegui_base/interaction_contract.json'))
        assert [page['route'] for page in interaction['pages']] == blueprint['routes']
        by_route = {page['route']: page for page in interaction['pages']}
        for page in blueprint['pages']:
            assert by_route[page['route']]['pattern_key'] == page['pattern_key']
            source = archive.read(f"pages/{page['module']}.py").decode('utf-8')
            assert 'create_page_workflow' in source
            assert 'workflow.execute(' in source


def test_crud_contract_is_local_draft_only_not_provider_write():
    from nicegui_base.workbench.interaction_contract import interaction_contract_for_project
    contract = interaction_contract_for_project({'pattern_key':'crud'})
    keys = [item['key'] for item in contract['pages'][0]['actions']]
    assert 'start_draft' in keys and 'discard_draft' in keys
    assert all(not item['provider_mutation'] for item in contract['pages'][0]['actions'])
    assert not any(key in keys for key in ('delete_record','save_record','update_record','create_record'))


def test_builder_review_exposes_interaction_contract_preview():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / 'nicegui_base' / 'workbench' / 'builder.py').read_text(encoding='utf-8')
    assert 'Generated interaction workflow' in source
    assert 'interaction_contract_for_project' in source
