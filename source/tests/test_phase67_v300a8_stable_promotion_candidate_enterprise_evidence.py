from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nicegui_base import (
    FRAMEWORK_VERSION,
    NICEGUI_VERSION,
    EnterpriseTargetEvidenceSet,
    OperationalReadinessCheck,
    OperationalReadinessState,
    PromotionCandidateStatus,
    PromotionFindingSeverity,
    PromotionRehearsalKind,
    PromotionRehearsalStatus,
    SEMICONDUCTOR_RELEASE_CHANNEL_POLICIES,
    SemiconductorOperationalReadiness,
    SemiconductorTargetEvidenceBundle,
    SemiconductorTargetRuntimeCertification,
    StablePromotionCandidate,
    TargetEnvironmentFingerprint,
    TargetGateStatus,
    TargetRuntimeGate,
    assimilate_enterprise_target_evidence,
    build_promotion_rehearsal,
    build_stable_promotion_candidate,
    capture_target_evidence_artifact,
    enterprise_target_evidence_set_from_dict,
    package_stable_promotion_candidate,
    promotion_candidate_from_dict,
    promotion_candidate_gaps,
    promotion_rehearsal_from_dict,
    read_enterprise_target_evidence_set,
    read_promotion_candidate,
    read_promotion_rehearsal,
    with_promotion_rehearsal,
    write_enterprise_target_evidence_set,
    write_promotion_candidate,
    write_promotion_rehearsal,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def make_bundle(tmp_path: Path, *, recipe='spc-monitor', provider='sqlite', source_key='target', traced=True, pending_gate: str | None = None, fail_gate: str | None = None):
    gate_defs=(
        ('company_adapter','Approved company adapter conformance'),
        ('fab_scale_pushdown','Representative fab-scale pushdown/performance'),
        ('installed_nicegui','Installed NiceGUI 3.15.0'),
        ('server_websocket','Real server/WebSocket lifecycle'),
        ('supported_browser','Supported corporate browser'),
        ('human_visual_baseline','Human visual baseline'),
        ('provider_benchmark','Governed representative provider benchmark'),
    )
    gates=[]
    for key,label in gate_defs:
        status=TargetGateStatus.FAIL if key==fail_gate else (TargetGateStatus.PENDING if key==pending_gate else TargetGateStatus.PASS)
        gates.append(TargetRuntimeGate(key,label,status,f'{key} evidence'))
    artifacts=[]
    if traced:
        for key in ('installed_nicegui','server_websocket','supported_browser','human_visual_baseline'):
            path=tmp_path/f'{recipe}-{key}.json'; path.write_text(json.dumps({'gate':key,'pass':True})+'\n')
            artifacts.append(capture_target_evidence_artifact(path,key=key,description=f'{key} target evidence'))
    return SemiconductorTargetEvidenceBundle(
        recipe,
        SemiconductorTargetRuntimeCertification(recipe,tuple(gates)),
        TargetEnvironmentFingerprint('3.12.0','enterprise-test','3.15.0','python'),
        tuple(artifacts),
        {'profile_key':'provider-rc','provider':provider,'source_key':source_key,'passed':True},
        {'provider':provider,'source_key':source_key,'passed':True},
        {'provider':provider,'source_key':source_key,'passed':True},
        {'framework_version':FRAMEWORK_VERSION,'nicegui_required':NICEGUI_VERSION},
        _iso_now(),1,
    )


def ready_ops(recipe='spc-monitor',provider='sqlite',source_key='target'):
    check=OperationalReadinessCheck('all','All operational gates',OperationalReadinessState.READY,'Operational gates passed.',required_for_run=True,required_for_release=True)
    return SemiconductorOperationalReadiness(recipe,source_key,provider,(check,))


def complete_rehearsals(recipe='spc-monitor'):
    reports=[]
    for kind in PromotionRehearsalKind:
        pending=build_promotion_rehearsal(recipe,kind)
        reports.append(build_promotion_rehearsal(recipe,kind,completed_step_keys=pending.required_step_keys))
    return tuple(reports)


def make_evidence(tmp_path: Path, *, pending_gate=None, fail_gate=None):
    return assimilate_enterprise_target_evidence(
        (make_bundle(tmp_path,pending_gate=pending_gate,fail_gate=fail_gate),),
        operational_readiness=(ready_ops(),),provider='sqlite',required_recipe_keys=('spc-monitor',),
    )


def test_wave67_assimilation_reuses_wave66_qualification_and_decision(tmp_path: Path):
    evidence=make_evidence(tmp_path)
    assert isinstance(evidence,EnterpriseTargetEvidenceSet)
    assert evidence.provider=='sqlite'
    assert evidence.qualification.provider=='sqlite'
    assert evidence.decision.qualification_id==evidence.qualification.qualification_id
    assert evidence.decision.promotable


def test_wave67_evidence_set_id_is_deterministic_across_input_order(tmp_path: Path):
    b1=make_bundle(tmp_path,recipe='spc-monitor',source_key='a')
    b2=make_bundle(tmp_path,recipe='yield-loss',source_key='b')
    o1=ready_ops('spc-monitor',source_key='a')
    o2=ready_ops('yield-loss',source_key='b')
    a=assimilate_enterprise_target_evidence((b1,b2),operational_readiness=(o1,o2),provider='sqlite')
    b=assimilate_enterprise_target_evidence((b2,b1),operational_readiness=(o2,o1),provider='sqlite')
    assert a.evidence_set_id==b.evidence_set_id


def test_wave67_assimilation_rejects_duplicate_operational_reports(tmp_path: Path):
    bundle=make_bundle(tmp_path)
    with pytest.raises(ValueError,match='duplicate operational readiness'):
        assimilate_enterprise_target_evidence((bundle,),operational_readiness=(ready_ops(),ready_ops()),provider='sqlite')


def test_wave67_assimilation_mapping_keys_must_match_recipe(tmp_path: Path):
    with pytest.raises(ValueError,match='does not match report recipe'):
        assimilate_enterprise_target_evidence((make_bundle(tmp_path),),operational_readiness={'other':ready_ops()},provider='sqlite')


def test_wave67_missing_target_gate_stays_pending(tmp_path: Path):
    evidence=make_evidence(tmp_path,pending_gate='supported_browser')
    assert evidence.decision.pending
    candidate=build_stable_promotion_candidate(evidence,rehearsals=complete_rehearsals())
    assert candidate.status is PromotionCandidateStatus.PENDING
    assert any(g.code=='target_gate_pending' for g in candidate.gaps)


def test_wave67_failed_target_gate_blocks_candidate(tmp_path: Path):
    evidence=make_evidence(tmp_path,fail_gate='server_websocket')
    candidate=build_stable_promotion_candidate(evidence,rehearsals=complete_rehearsals())
    assert candidate.status is PromotionCandidateStatus.BLOCKED
    assert any(g.severity is PromotionFindingSeverity.ERROR for g in candidate.gaps)


def test_wave67_promotable_evidence_without_rehearsals_is_candidate_pending(tmp_path: Path):
    candidate=build_stable_promotion_candidate(make_evidence(tmp_path))
    assert candidate.evidence.decision.promotable
    assert candidate.status is PromotionCandidateStatus.PENDING
    assert sum(g.code=='promotion_rehearsal_missing' for g in candidate.gaps)==4


def test_wave67_complete_rehearsals_make_complete_evidence_channel_ready(tmp_path: Path):
    candidate=build_stable_promotion_candidate(make_evidence(tmp_path),rehearsals=complete_rehearsals())
    assert candidate.status is PromotionCandidateStatus.READY
    assert candidate.release_channel_ready
    assert candidate.gaps==()


def test_wave67_rehearsal_is_derived_from_canonical_runbook_and_never_changes_target_gates():
    report=build_promotion_rehearsal('spc-monitor',PromotionRehearsalKind.INCIDENT)
    assert report.required_step_keys==('incident','provider-failure','release-evidence')
    assert report.status is PromotionRehearsalStatus.PENDING
    assert report.to_dict()['affects_target_gate_status'] is False


def test_wave67_rehearsal_pass_requires_every_required_step():
    plan=build_promotion_rehearsal('spc-monitor','rollback')
    partial=build_promotion_rehearsal('spc-monitor','rollback',completed_step_keys=(plan.required_step_keys[0],))
    complete=build_promotion_rehearsal('spc-monitor','rollback',completed_step_keys=plan.required_step_keys)
    assert partial.status is PromotionRehearsalStatus.PENDING
    assert complete.status is PromotionRehearsalStatus.PASS


def test_wave67_failed_rehearsal_blocks_candidate_even_when_target_evidence_passes(tmp_path: Path):
    reports=list(complete_rehearsals())
    reports[0]=build_promotion_rehearsal('spc-monitor',reports[0].kind,failed_step_keys=(reports[0].required_step_keys[0],))
    candidate=build_stable_promotion_candidate(make_evidence(tmp_path),rehearsals=reports)
    assert candidate.status is PromotionCandidateStatus.BLOCKED
    assert any(g.code=='promotion_rehearsal_failed' for g in candidate.gaps)


def test_wave67_rehearsal_rejects_unknown_steps_and_overlap():
    with pytest.raises(ValueError): build_promotion_rehearsal('spc-monitor','promotion',completed_step_keys=('invented',))
    with pytest.raises(ValueError): build_promotion_rehearsal('spc-monitor','promotion',completed_step_keys=('startup',),failed_step_keys=('startup',))


def test_wave67_rehearsal_rejects_unknown_recipe():
    with pytest.raises(KeyError): build_promotion_rehearsal('unknown','promotion')


def test_wave67_with_rehearsal_replaces_same_recipe_kind_deterministically(tmp_path: Path):
    candidate=build_stable_promotion_candidate(make_evidence(tmp_path))
    plan=build_promotion_rehearsal('spc-monitor','promotion')
    c1=with_promotion_rehearsal(candidate,plan)
    passed=build_promotion_rehearsal('spc-monitor','promotion',completed_step_keys=plan.required_step_keys)
    c2=with_promotion_rehearsal(c1,passed)
    assert len(c2.rehearsals)==1
    assert c2.rehearsals[0].status is PromotionRehearsalStatus.PASS
    assert c2.candidate_id!=c1.candidate_id


def test_wave67_candidate_id_is_deterministic_for_same_evidence_and_rehearsals(tmp_path: Path):
    evidence=make_evidence(tmp_path)
    reports=complete_rehearsals()
    a=build_stable_promotion_candidate(evidence,rehearsals=reports)
    b=build_stable_promotion_candidate(evidence,rehearsals=tuple(reversed(reports)))
    assert a.candidate_id==b.candidate_id


def test_wave67_candidate_rejects_rehearsal_for_unqualified_recipe(tmp_path: Path):
    report=build_promotion_rehearsal('yield-loss','promotion')
    with pytest.raises(ValueError,match='belong to the candidate evidence set'):
        build_stable_promotion_candidate(make_evidence(tmp_path),rehearsals=(report,))


def test_wave67_release_channel_registry_is_additive_and_stable_only():
    assert SEMICONDUCTOR_RELEASE_CHANNEL_POLICIES['stable'].promotion_policy.key=='stable'
    assert SEMICONDUCTOR_RELEASE_CHANNEL_POLICIES['stable'].target_version=='3.0.0'


def test_wave67_unknown_release_channel_rejected(tmp_path: Path):
    with pytest.raises(KeyError): build_stable_promotion_candidate(make_evidence(tmp_path),channel='invented')


def test_wave67_gap_diagnostics_are_actionable_and_deduplicated(tmp_path: Path):
    candidate=build_stable_promotion_candidate(make_evidence(tmp_path,pending_gate='supported_browser'))
    gaps=promotion_candidate_gaps(candidate)
    assert gaps
    assert all(g.category and g.message and g.remediation for g in gaps)
    assert candidate.next_actions==tuple(dict.fromkeys(g.remediation for g in gaps if g.remediation))


def test_wave67_evidence_set_roundtrip_and_tamper_detection(tmp_path: Path):
    evidence=make_evidence(tmp_path)
    payload=evidence.to_dict()
    restored=enterprise_target_evidence_set_from_dict(payload)
    assert restored.evidence_set_id==evidence.evidence_set_id
    payload['evidence_set_id']='0'*64
    with pytest.raises(ValueError,match='id does not match'):
        enterprise_target_evidence_set_from_dict(payload)


def test_wave67_evidence_set_file_roundtrip(tmp_path: Path):
    evidence=make_evidence(tmp_path)
    path=write_enterprise_target_evidence_set(tmp_path/'enterprise.json',evidence)
    assert read_enterprise_target_evidence_set(path).evidence_set_id==evidence.evidence_set_id


def test_wave67_rehearsal_roundtrip_and_status_tamper_detection(tmp_path: Path):
    report=complete_rehearsals()[0]
    assert promotion_rehearsal_from_dict(report.to_dict()).status is PromotionRehearsalStatus.PASS
    path=write_promotion_rehearsal(tmp_path/'rehearsal.json',report)
    assert read_promotion_rehearsal(path).kind==report.kind
    payload=report.to_dict(); payload['status']='blocked'
    with pytest.raises(ValueError,match='status does not match'):
        promotion_rehearsal_from_dict(payload)


def test_wave67_candidate_roundtrip_and_tamper_detection(tmp_path: Path):
    candidate=build_stable_promotion_candidate(make_evidence(tmp_path),rehearsals=complete_rehearsals())
    restored=promotion_candidate_from_dict(candidate.to_dict())
    assert restored.candidate_id==candidate.candidate_id
    payload=candidate.to_dict(); payload['candidate_id']='f'*64
    with pytest.raises(ValueError,match='id does not match'):
        promotion_candidate_from_dict(payload)


def test_wave67_candidate_file_roundtrip(tmp_path: Path):
    candidate=build_stable_promotion_candidate(make_evidence(tmp_path),rehearsals=complete_rehearsals())
    path=write_promotion_candidate(tmp_path/'candidate.json',candidate)
    restored=read_promotion_candidate(path)
    assert restored.release_channel_ready


def test_wave67_candidate_package_is_deterministic_and_manifested(tmp_path: Path):
    candidate=build_stable_promotion_candidate(make_evidence(tmp_path),rehearsals=complete_rehearsals())
    p1=package_stable_promotion_candidate(tmp_path/'candidate-a.zip',candidate)
    p2=package_stable_promotion_candidate(tmp_path/'candidate-b.zip',candidate)
    assert p1.sha256==p2.sha256
    with zipfile.ZipFile(p1.path) as z:
        names=set(z.namelist())
        assert {'candidate.json','MANIFEST.sha256','README.md','evidence/provider_qualification.json','diagnostics/promotion_gaps.json'}<=names
        manifest=z.read('MANIFEST.sha256').decode()
        for line in manifest.strip().splitlines():
            digest,name=line.split('  ',1)
            assert hashlib.sha256(z.read(name)).hexdigest()==digest


def test_wave67_candidate_package_includes_only_hash_verified_artifacts(tmp_path: Path):
    evidence=make_evidence(tmp_path)
    candidate=build_stable_promotion_candidate(evidence)
    package=package_stable_promotion_candidate(tmp_path/'candidate.zip',candidate)
    assert len(package.included_artifacts)==4
    assert package.omitted_artifacts==()
    Path(evidence.qualification.bundles[0].artifacts[0].path).write_text('tampered')
    # Existing qualification remains a frozen evidence statement; packaging independently refuses changed bytes.
    package2=package_stable_promotion_candidate(tmp_path/'candidate-tampered.zip',candidate)
    assert len(package2.included_artifacts)==3
    assert len(package2.omitted_artifacts)==1


def test_wave67_package_can_intentionally_omit_external_artifact_bytes(tmp_path: Path):
    candidate=build_stable_promotion_candidate(make_evidence(tmp_path))
    package=package_stable_promotion_candidate(tmp_path/'no-artifacts.zip',candidate,include_verified_artifacts=False)
    assert package.included_artifacts==()
    with zipfile.ZipFile(package.path) as z:
        assert not any(name.startswith('artifacts/') for name in z.namelist())


def test_wave67_package_pending_candidate_does_not_claim_pass(tmp_path: Path):
    candidate=build_stable_promotion_candidate(make_evidence(tmp_path,pending_gate='supported_browser'))
    package=package_stable_promotion_candidate(tmp_path/'pending.zip',candidate)
    assert package.status is PromotionCandidateStatus.PENDING
    with zipfile.ZipFile(package.path) as z:
        readme=z.read('README.md').decode()
        assert 'Candidate status: `pending`' in readme
        assert 'never changes target gate status' in readme


def test_wave67_public_root_exports_new_contracts():
    import nicegui_base
    for name in (
        'EnterpriseTargetEvidenceSet','StablePromotionCandidate','PromotionRehearsalReport','PromotionCandidatePackage',
        'assimilate_enterprise_target_evidence','build_stable_promotion_candidate','package_stable_promotion_candidate',
    ):
        assert hasattr(nicegui_base,name),name


def test_wave67_no_new_mandatory_dependency():
    pyproject=Path(__file__).parents[1]/'pyproject.toml'
    text=pyproject.read_text()
    dependency_block=text.split('dependencies = [',1)[1].split(']',1)[0]
    assert 'nicegui==3.15.0' in dependency_block
    assert dependency_block.count('"')==2


def _write_cli_inputs(tmp_path: Path):
    from nicegui_base import write_operational_readiness, write_semiconductor_target_evidence
    bundle=make_bundle(tmp_path)
    evidence=write_semiconductor_target_evidence(tmp_path/'target-evidence.json',bundle)
    ops=write_operational_readiness(tmp_path/'ops.json',ready_ops())
    rehearsals=[]
    for report in complete_rehearsals():
        rehearsals.append(write_promotion_rehearsal(tmp_path/f'{report.kind.value}.json',report))
    return evidence,ops,tuple(rehearsals)


def test_wave67_promotion_candidate_cli_ready_and_packages_complete_inputs(tmp_path: Path,capsys):
    from nicegui_base.certification.semiconductor_promotion_cli import promotion_candidate_main
    evidence,ops,rehearsals=_write_cli_inputs(tmp_path)
    argv=['nicegui-base promotion-candidate',str(evidence),'--provider','sqlite','--operational-readiness',str(ops),'--require-recipe','spc-monitor']
    for path in rehearsals: argv += ['--rehearsal',str(path)]
    argv += ['--output',str(tmp_path/'candidate.json'),'--package',str(tmp_path/'candidate.zip'),'--format','json']
    rc=promotion_candidate_main(argv)
    payload=json.loads(capsys.readouterr().out)
    assert rc==0
    assert payload['candidate']['status']=='ready'
    assert Path(payload['package']['path']).is_file()


def test_wave67_promotion_candidate_cli_pending_when_rehearsals_missing(tmp_path: Path,capsys):
    from nicegui_base.certification.semiconductor_promotion_cli import promotion_candidate_main
    evidence,ops,_=_write_cli_inputs(tmp_path)
    rc=promotion_candidate_main(['nicegui-base promotion-candidate',str(evidence),'--provider','sqlite','--operational-readiness',str(ops),'--format','json'])
    payload=json.loads(capsys.readouterr().out)
    assert rc==2
    assert payload['candidate']['status']=='pending'
    assert any(item['code']=='promotion_rehearsal_missing' for item in payload['candidate']['gaps'])


def test_wave67_promotion_rehearse_cli_pending_plan_does_not_claim_target_pass(tmp_path: Path,capsys):
    from nicegui_base.certification.semiconductor_promotion_cli import promotion_rehearse_main
    rc=promotion_rehearse_main(['nicegui-base promotion-rehearse','spc-monitor','incident','--output',str(tmp_path/'incident.json'),'--format','json'])
    payload=json.loads(capsys.readouterr().out)
    assert rc==2
    assert payload['status']=='pending'
    assert payload['affects_target_gate_status'] is False


def test_wave67_promotion_rehearse_cli_pass_requires_explicit_completed_steps(tmp_path: Path,capsys):
    from nicegui_base.certification.semiconductor_promotion_cli import promotion_rehearse_main
    plan=build_promotion_rehearsal('spc-monitor','evidence-capture')
    rc=promotion_rehearse_main(['nicegui-base promotion-rehearse','spc-monitor','evidence-capture','--completed',plan.required_step_keys[0],'--format','json'])
    payload=json.loads(capsys.readouterr().out)
    assert rc==0 and payload['status']=='pass'


def test_wave67_top_level_cli_dispatch_contains_new_commands():
    text=(Path(__file__).parents[1]/'nicegui_base'/'cli.py').read_text()
    assert "sub.add_parser('promotion-candidate'" in text
    assert "sub.add_parser('promotion-rehearse'" in text
    assert "semiconductor_promotion_cli" in text


def test_wave67_generated_recipe_starter_contains_candidate_and_package_helpers(tmp_path: Path):
    from nicegui_base.ai.project import create_application
    root=tmp_path/'generated'
    create_application(root,name='Wave67 Generated',recipe='spc-monitor')
    helper=(root/'services'/'release_evidence.py').read_text()
    assert 'assemble_stable_promotion_candidate' in helper
    assert 'package_release_candidate' in helper
    assert 'assimilate_enterprise_target_evidence' in helper
    compile(helper,str(root/'services'/'release_evidence.py'),'exec')


def test_wave67_ui_exports_candidate_panel_without_rendering():
    import nicegui_base
    assert hasattr(nicegui_base,'SemiconductorPromotionCandidatePanel')


def test_wave67_package_sanitizes_untrusted_artifact_entry_names(tmp_path: Path):
    bundle=make_bundle(tmp_path)
    artifact=bundle.artifacts[0]
    malicious=replace(artifact,key='../escape')
    bundle=replace(bundle,artifacts=(malicious,*bundle.artifacts[1:]))
    # Gate traceability changes because key no longer maps to installed_nicegui, so the candidate is pending, but packaging stays safe.
    evidence=assimilate_enterprise_target_evidence((bundle,),operational_readiness=(ready_ops(),),provider='sqlite')
    candidate=build_stable_promotion_candidate(evidence)
    package=package_stable_promotion_candidate(tmp_path/'safe.zip',candidate)
    with zipfile.ZipFile(package.path) as z:
        assert all('..' not in Path(name).parts for name in z.namelist())


def test_wave67_custom_promotion_policy_persists_tamper_evidently(tmp_path: Path):
    from nicegui_base import PromotionPolicy
    policy=PromotionPolicy(require_operational_release_ready=False,required_recipe_keys=('spc-monitor',))
    evidence=assimilate_enterprise_target_evidence((make_bundle(tmp_path),),provider='sqlite',required_recipe_keys=('spc-monitor',),promotion_policy=policy)
    payload=evidence.to_dict()
    assert payload['promotion_policy']['require_operational_release_ready'] is False
    restored=enterprise_target_evidence_set_from_dict(payload)
    assert restored.promotion_policy.require_operational_release_ready is False
    payload['promotion_policy']['require_runtime_version_match']=False
    with pytest.raises(ValueError,match='id does not match'):
        enterprise_target_evidence_set_from_dict(payload)


def test_wave67_candidate_package_manifest_covers_readme_and_all_non_manifest_entries(tmp_path: Path):
    candidate=build_stable_promotion_candidate(make_evidence(tmp_path))
    package=package_stable_promotion_candidate(tmp_path/'manifest.zip',candidate)
    with zipfile.ZipFile(package.path) as z:
        manifest={line.split('  ',1)[1] for line in z.read('MANIFEST.sha256').decode().strip().splitlines()}
        expected=set(z.namelist())-{'MANIFEST.sha256'}
        assert manifest==expected
