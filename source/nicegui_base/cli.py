from __future__ import annotations
import argparse,sys
from pathlib import Path


def main()->int:
    p=argparse.ArgumentParser(prog='nicegui-base',description='NiceGUI Base template and framework tools')
    sub=p.add_subparsers(dest='command',required=True)
    d=sub.add_parser('doctor',help='Run platform/runtime/browser preflight');d.add_argument('--port',type=int,default=8080);d.add_argument('--require-edge',action='store_true');d.add_argument('--no-require-browser',action='store_true',help='Do not require Chrome/Chromium');d.add_argument('--runtime-only',action='store_true',help='Production-runtime profile: Playwright/Pillow are optional');d.add_argument('--ignore-port',action='store_true',help='Do not require the requested port to be free');d.add_argument('--format',choices=('text','json'),default='text')
    l=sub.add_parser('lab',help='Run the live reference/certification laboratory');l.add_argument('--host',default='127.0.0.1');l.add_argument('--port',type=int,default=8080);l.add_argument('--show',action='store_true')
    c=sub.add_parser('certify',help='Run live runtime/browser/geometry certification');c.add_argument('--output',type=Path,default=Path('certification_output'));c.add_argument('--baseline',type=Path,default=Path('visual_baseline'));c.add_argument('--root',type=Path,default=Path.cwd());c.add_argument('--port',type=int,default=8080);c.add_argument('--exhaustive',action='store_true');c.add_argument('--no-edge',action='store_true');c.add_argument('--require-edge',action='store_true');c.add_argument('--require-baseline',action='store_true');c.add_argument('--format',choices=('text','json'),default='text')
    a=sub.add_parser('approve-baseline',help='Approve the last passing screenshot set after human review');a.add_argument('--output',type=Path,default=Path('certification_output'));a.add_argument('--baseline',type=Path,default=Path('visual_baseline'));a.add_argument('--force',action='store_true')
    rc=sub.add_parser('runtime-contract',help='Verify exact installed NiceGUI API compatibility');rc.add_argument('--format',choices=('text','json'),default='text')
    rs=sub.add_parser('runtime-smoke',help='Start real NiceGUI server and smoke every live route without a browser');rs.add_argument('--output',type=Path,default=Path('certification_output/runtime_smoke'));rs.add_argument('--port',type=int,default=0);rs.add_argument('--format',choices=('text','json'),default='text')
    ai_init=sub.add_parser('agent-init',help='Install coding-agent guidance and golden examples');ai_init.add_argument('path',nargs='?',default='.');ai_init.add_argument('--overwrite',action='store_true')
    ai_ctx=sub.add_parser('agent-context',help='Build compact task-specific coding-agent context');ai_ctx.add_argument('task');ai_ctx.add_argument('--format',choices=('text','json'),default='text');ai_ctx.add_argument('--output',type=Path)
    ai_check=sub.add_parser('agent-check',help='Run fail-closed coding-agent preflight');ai_check.add_argument('path',nargs='?',default='.');ai_check.add_argument('--format',choices=('text','json'),default='text')
    create=sub.add_parser('create',help='Create a governed NiceGUI Base application starter');create.add_argument('path');create.add_argument('--name',required=True);create.add_argument('--template',choices=('dashboard','data-explorer','crud','analysis-workspace','responsive-operations','async-workflow'),default='analysis-workspace');create.add_argument('--recipe');create.add_argument('--variant');create.add_argument('--overwrite',action='store_true')
    create_pattern=sub.add_parser('create-pattern',help='Create an application from a canonical registered pattern');create_pattern.add_argument('path');create_pattern.add_argument('--name',required=True);create_pattern.add_argument('--pattern',required=True);create_pattern.add_argument('--overwrite',action='store_true')
    create_recipe=sub.add_parser('create-recipe',help='Create an application from a canonical semiconductor recipe');create_recipe.add_argument('path');create_recipe.add_argument('--name',required=True);create_recipe.add_argument('--recipe',required=True);create_recipe.add_argument('--variant');create_recipe.add_argument('--overwrite',action='store_true')
    recipes=sub.add_parser('recipes',help='List or recommend semiconductor application recipes');recipes.add_argument('intent',nargs='?');recipes.add_argument('--format',choices=('text','json'),default='text')
    catalog_search=sub.add_parser('catalog-search',help='Search the canonical catalog for a component, pattern, recipe or visualization');catalog_search.add_argument('query',nargs='?');catalog_search.add_argument('--limit',type=int,default=20);catalog_search.add_argument('--intent');catalog_search.add_argument('--data-shape');catalog_search.add_argument('--domain');catalog_search.add_argument('--related-to');catalog_search.add_argument('--format',choices=('text','json'),default='text')
    recommend_pattern=sub.add_parser('recommend-pattern',help='Recommend a canonical page pattern for a requirement');recommend_pattern.add_argument('requirement');recommend_pattern.add_argument('--format',choices=('text','json'),default='text')
    recommend_visualization=sub.add_parser('recommend-visualization',help='Recommend registered analytical visualizations for intent and schema');recommend_visualization.add_argument('intent');recommend_visualization.add_argument('--schema',action='append',default=[]);recommend_visualization.add_argument('--domain');recommend_visualization.add_argument('--limit',type=int,default=5);recommend_visualization.add_argument('--format',choices=('text','json'),default='text')
    scaffold_plan=sub.add_parser('scaffold-plan',help='Print canonical scaffold commands without writing files');scaffold_plan.add_argument('requirement');scaffold_plan.add_argument('--format',choices=('text','json'),default='text')
    catalog_audit=sub.add_parser('catalog-audit',help='Validate canonical catalog completeness and family coverage');catalog_audit.add_argument('--format',choices=('text','json'),default='text')
    agent_benchmark=sub.add_parser('agent-benchmark',help='Score deterministic agent discovery and scaffold choices');agent_benchmark.add_argument('manifest',type=Path);agent_benchmark.add_argument('--no-materialize',action='store_true');agent_benchmark.add_argument('--format',choices=('text','json'),default='text')
    provider_init=sub.add_parser('provider-init',help='Create a provider-neutral semiconductor adapter SDK starter');provider_init.add_argument('path');provider_init.add_argument('--key',required=True);provider_init.add_argument('--class-name',default='CompanySemiconductorAdapter');provider_init.add_argument('--recipe',action='append');provider_init.add_argument('--profile',choices=('development','production'),default='production');provider_init.add_argument('--overwrite',action='store_true')
    provider_check=sub.add_parser('provider-check',help='Run bounded semiconductor adapter conformance and optional benchmark');provider_check.add_argument('adapter');provider_check.add_argument('--recipe',action='append');provider_check.add_argument('--fixtures');provider_check.add_argument('--profile',choices=('development','production'),default='production');provider_check.add_argument('--benchmark-profile',choices=('development-smoke','provider-rc'));provider_check.add_argument('--output',type=Path);provider_check.add_argument('--format',choices=('text','json'),default='text')
    target_qualify=sub.add_parser('target-qualify',help='Aggregate target evidence and evaluate stable semiconductor promotion readiness');target_qualify.add_argument('evidence',nargs='+');target_qualify.add_argument('--provider');target_qualify.add_argument('--base-dir',type=Path);target_qualify.add_argument('--operational-readiness',action='append');target_qualify.add_argument('--require-recipe',action='append');target_qualify.add_argument('--qualification-output',type=Path);target_qualify.add_argument('--decision-output',type=Path);target_qualify.add_argument('--format',choices=('text','json'),default='text')
    promotion_candidate=sub.add_parser('promotion-candidate',help='Build/package deterministic enterprise stable-promotion candidate');promotion_candidate.add_argument('evidence',nargs='+');promotion_candidate.add_argument('--provider');promotion_candidate.add_argument('--base-dir',type=Path);promotion_candidate.add_argument('--operational-readiness',action='append');promotion_candidate.add_argument('--require-recipe',action='append');promotion_candidate.add_argument('--rehearsal',action='append');promotion_candidate.add_argument('--target-version');promotion_candidate.add_argument('--output',type=Path);promotion_candidate.add_argument('--package',type=Path);promotion_candidate.add_argument('--artifact-base-dir',type=Path);promotion_candidate.add_argument('--no-artifact-bytes',action='store_true');promotion_candidate.add_argument('--format',choices=('text','json'),default='text')
    promotion_rehearse=sub.add_parser('promotion-rehearse',help='Record operational promotion/rollback/incident/evidence-capture rehearsal');promotion_rehearse.add_argument('recipe');promotion_rehearse.add_argument('kind',choices=('promotion','rollback','incident','evidence-capture'));promotion_rehearse.add_argument('--completed',action='append');promotion_rehearse.add_argument('--failed',action='append');promotion_rehearse.add_argument('--note',action='append');promotion_rehearse.add_argument('--output',type=Path);promotion_rehearse.add_argument('--format',choices=('text','json'),default='text')
    target_intake=sub.add_parser('target-intake',help='Import target execution artifacts into canonical semiconductor evidence');target_intake.add_argument('evidence');target_intake.add_argument('manifest');target_intake.add_argument('--adapter',choices=('json-manifest',),default='json-manifest');target_intake.add_argument('--artifact-base-dir',type=Path);target_intake.add_argument('--intake-output',type=Path);target_intake.add_argument('--output',type=Path);target_intake.add_argument('--format',choices=('text','json'),default='text')
    promotion_handoff=sub.add_parser('promotion-handoff',help='Create verified provider-neutral stable-promotion operational handoff');promotion_handoff.add_argument('candidate');promotion_handoff.add_argument('candidate_package');promotion_handoff.add_argument('--adapter',choices=('file-package',),default='file-package');promotion_handoff.add_argument('--change-reference');promotion_handoff.add_argument('--output',type=Path);promotion_handoff.add_argument('--package',type=Path);promotion_handoff.add_argument('--format',choices=('text','json'),default='text')
    promotion_operation=sub.add_parser('promotion-operation',help='Capture hash-bound operational evidence against a promotion handoff');promotion_operation.add_argument('handoff');promotion_operation.add_argument('recipe');promotion_operation.add_argument('kind',choices=('promotion','rollback','incident','evidence-capture'));promotion_operation.add_argument('--completed',action='append');promotion_operation.add_argument('--failed',action='append');promotion_operation.add_argument('--evidence',action='append');promotion_operation.add_argument('--note',action='append');promotion_operation.add_argument('--output',type=Path);promotion_operation.add_argument('--format',choices=('text','json'),default='text')
    execution_adapter_qualify=sub.add_parser('execution-adapter-qualify',help='Verify artifact-backed qualification for an approved external promotion execution adapter');execution_adapter_qualify.add_argument('manifest');execution_adapter_qualify.add_argument('--adapter',choices=('json-manifest',),default='json-manifest');execution_adapter_qualify.add_argument('--artifact-base-dir',type=Path);execution_adapter_qualify.add_argument('--output',type=Path);execution_adapter_qualify.add_argument('--format',choices=('text','json'),default='text')
    release_audit=sub.add_parser('release-audit',help='Close release-channel audit from verified handoff, adapter qualification and operation evidence');release_audit.add_argument('handoff');release_audit.add_argument('qualification');release_audit.add_argument('operations',nargs='*');release_audit.add_argument('--artifact-base-dir',type=Path);release_audit.add_argument('--output',type=Path);release_audit.add_argument('--package',type=Path);release_audit.add_argument('--format',choices=('text','json'),default='text')
    release_evidence_accept=sub.add_parser('release-evidence-accept',help='Import artifact-backed external acceptance for an exact Wave 69 audit package');release_evidence_accept.add_argument('audit');release_evidence_accept.add_argument('audit_archive');release_evidence_accept.add_argument('manifest');release_evidence_accept.add_argument('--adapter',choices=('json-manifest',),default='json-manifest');release_evidence_accept.add_argument('--artifact-base-dir',type=Path);release_evidence_accept.add_argument('--output',type=Path);release_evidence_accept.add_argument('--format',choices=('text','json'),default='text')
    promotion_close=sub.add_parser('promotion-close',help='Build documentary stable-promotion evidence closure from canonical audit and accepted external evidence');promotion_close.add_argument('audit');promotion_close.add_argument('audit_archive');promotion_close.add_argument('acceptance');promotion_close.add_argument('--artifact-base-dir',type=Path);promotion_close.add_argument('--output',type=Path);promotion_close.add_argument('--package',type=Path);promotion_close.add_argument('--format',choices=('text','json'),default='text')
    publication_intake=sub.add_parser('release-publication-intake',help='Import artifact-backed external stable release publication evidence against an exact Wave 70 closure');publication_intake.add_argument('closure');publication_intake.add_argument('closure_archive');publication_intake.add_argument('manifest');publication_intake.add_argument('--adapter',choices=('json-manifest',),default='json-manifest');publication_intake.add_argument('--artifact-base-dir',type=Path);publication_intake.add_argument('--output',type=Path);publication_intake.add_argument('--format',choices=('text','json'),default='text')
    post_verify=sub.add_parser('post-promotion-verify',help='Verify post-promotion evidence against exact closure and publication identities');post_verify.add_argument('closure');post_verify.add_argument('closure_archive');post_verify.add_argument('publication');post_verify.add_argument('manifest');post_verify.add_argument('--artifact-base-dir',type=Path);post_verify.add_argument('--output',type=Path);post_verify.add_argument('--package',type=Path);post_verify.add_argument('--format',choices=('text','json'),default='text')
    stability_intake=sub.add_parser('post-release-stability-intake',help='Import artifact-backed production health/incident evidence against an exact Wave 71 post-promotion package');stability_intake.add_argument('post_verification');stability_intake.add_argument('post_promotion_archive');stability_intake.add_argument('manifest');stability_intake.add_argument('--adapter',choices=('json-manifest',),default='json-manifest');stability_intake.add_argument('--artifact-base-dir',type=Path);stability_intake.add_argument('--output',type=Path);stability_intake.add_argument('--format',choices=('text','json'),default='text')
    rollback_verify=sub.add_parser('rollback-readiness-verify',help='Verify rollback readiness against exact Wave 71 post-promotion and Wave 72 stability identities');rollback_verify.add_argument('post_verification');rollback_verify.add_argument('post_promotion_archive');rollback_verify.add_argument('stability');rollback_verify.add_argument('manifest');rollback_verify.add_argument('--artifact-base-dir',type=Path);rollback_verify.add_argument('--output',type=Path);rollback_verify.add_argument('--package',type=Path);rollback_verify.add_argument('--format',choices=('text','json'),default='text')
    sustained_accept=sub.add_parser('sustained-operations-accept',help='Import artifact-backed sustained-operations acceptance against an exact Wave 72 rollback-readiness package');sustained_accept.add_argument('readiness');sustained_accept.add_argument('readiness_archive');sustained_accept.add_argument('manifest');sustained_accept.add_argument('--adapter',choices=('json-manifest',),default='json-manifest');sustained_accept.add_argument('--artifact-base-dir',type=Path);sustained_accept.add_argument('--output',type=Path);sustained_accept.add_argument('--format',choices=('text','json'),default='text')
    incident_audit=sub.add_parser('incident-rollback-audit-close',help='Close incident/rollback audit from exact Wave 72 readiness and accepted sustained-operations evidence');incident_audit.add_argument('readiness');incident_audit.add_argument('readiness_archive');incident_audit.add_argument('acceptance');incident_audit.add_argument('manifest');incident_audit.add_argument('--artifact-base-dir',type=Path);incident_audit.add_argument('--output',type=Path);incident_audit.add_argument('--package',type=Path);incident_audit.add_argument('--format',choices=('text','json'),default='text')
    renewal=sub.add_parser('operations-evidence-renew',help='Import artifact-backed sustained-operations renewal evidence against an exact Wave 73 audit package');renewal.add_argument('audit');renewal.add_argument('audit_archive');renewal.add_argument('manifest');renewal.add_argument('--adapter',choices=('json-manifest',),default='json-manifest');renewal.add_argument('--artifact-base-dir',type=Path);renewal.add_argument('--now');renewal.add_argument('--output',type=Path);renewal.add_argument('--format',choices=('text','json'),default='text')
    continuity=sub.add_parser('operational-assurance-continuity',help='Build operational-assurance continuity dossier from exact Wave 73 audit and Wave 74 renewal evidence');continuity.add_argument('audit');continuity.add_argument('audit_archive');continuity.add_argument('renewal');continuity.add_argument('--artifact-base-dir',type=Path);continuity.add_argument('--now');continuity.add_argument('--output',type=Path);continuity.add_argument('--package',type=Path);continuity.add_argument('--format',choices=('text','json'),default='text')
    ledger=sub.add_parser('operational-assurance-ledger',help='Build deterministic longitudinal ledger from exact Wave 74 continuity packages');ledger.add_argument('continuity_packages',nargs='+');ledger.add_argument('--now');ledger.add_argument('--output',type=Path);ledger.add_argument('--format',choices=('text','json'),default='text')
    longitudinal=sub.add_parser('longitudinal-assurance',help='Build/package longitudinal operational-assurance dossier from a Wave 75 renewal ledger');longitudinal.add_argument('ledger');longitudinal.add_argument('--now');longitudinal.add_argument('--review-reference');longitudinal.add_argument('--output',type=Path);longitudinal.add_argument('--package',type=Path);longitudinal.add_argument('--format',choices=('text','json'),default='text')
    review=sub.add_parser('longitudinal-assurance-review',help='Record artifact-backed external review decisions against an exact Wave 75 longitudinal package');review.add_argument('dossier');review.add_argument('dossier_archive');review.add_argument('manifest');review.add_argument('--adapter',choices=('json-manifest',),default='json-manifest');review.add_argument('--artifact-base-dir',type=Path);review.add_argument('--now');review.add_argument('--output',type=Path);review.add_argument('--format',choices=('text','json'),default='text')
    exception_governance=sub.add_parser('evidence-exception-governance',help='Govern bounded evidence exceptions without changing Wave 75 evidence truth');exception_governance.add_argument('review');exception_governance.add_argument('--artifact-base-dir',type=Path);exception_governance.add_argument('--now');exception_governance.add_argument('--output',type=Path);exception_governance.add_argument('--package',type=Path);exception_governance.add_argument('--format',choices=('text','json'),default='text')
    final_audit=sub.add_parser('final-audit',help='Audit final release-candidate consolidation and authority consistency');final_audit.add_argument('--root',type=Path,default=Path.cwd());final_audit.add_argument('--output',type=Path);final_audit.add_argument('--allow-pre-final',action='store_true');final_audit.add_argument('--format',choices=('text','json'),default='text')
    stable_handoff=sub.add_parser('stable-qualification-handoff',help='Write truthful stable-qualification handoff without inventing target PASS');stable_handoff.add_argument('--root',type=Path,default=Path.cwd());stable_handoff.add_argument('--output',type=Path,default=Path('STABLE_QUALIFICATION_HANDOFF.json'));stable_handoff.add_argument('--format',choices=('text','json'),default='text')
    gate=sub.add_parser('gate',help='Run application architecture/test/dependency gates');gate.add_argument('path',nargs='?',default='.');gate.add_argument('--release',action='store_true');gate.add_argument('--format',choices=('text','json'),default='text')
    args=p.parse_args()
    if args.command=='doctor':
        from nicegui_base.certification.live_preflight import main as cmd
        argv=['nicegui-base doctor','--port',str(args.port),'--format',args.format]+(['--require-edge'] if args.require_edge else [])+(['--no-require-browser'] if args.no_require_browser else [])+(['--runtime-only'] if args.runtime_only else [])+(['--ignore-port'] if args.ignore_port else [])
    elif args.command=='lab':
        from nicegui_base.certification.live_lab_cli import main as cmd
        argv=['nicegui-base lab','--host',args.host,'--port',str(args.port)]+(['--show'] if args.show else [])
    elif args.command=='runtime-contract':
        from nicegui_base.certification.nicegui_runtime_contract import main as cmd
        argv=['nicegui-base runtime-contract','--format',args.format]
    elif args.command=='runtime-smoke':
        from nicegui_base.certification.runtime_smoke import main as cmd
        argv=['nicegui-base runtime-smoke','--output',str(args.output),'--port',str(args.port),'--format',args.format]
    elif args.command=='agent-init':
        from nicegui_base.ai_cli import init_main as cmd
        argv=['nicegui-base agent-init',str(args.path)]+(['--overwrite'] if args.overwrite else [])
    elif args.command=='agent-context':
        from nicegui_base.ai_cli import context_main as cmd
        argv=['nicegui-base agent-context',args.task,'--format',args.format]+(['--output',str(args.output)] if args.output else [])
    elif args.command=='agent-check':
        from nicegui_base.ai_cli import check_main as cmd
        argv=['nicegui-base agent-check',str(args.path),'--format',args.format]
    elif args.command=='create':
        from nicegui_base.ai_cli import create_main as cmd
        argv=['nicegui-base create',str(args.path),'--name',args.name,'--template',args.template]+(['--recipe',args.recipe] if args.recipe else [])+(['--variant',args.variant] if args.variant else [])+(['--overwrite'] if args.overwrite else [])
    elif args.command=='create-pattern':
        from nicegui_base.ai_cli import create_pattern_main as cmd
        argv=['nicegui-base create-pattern',str(args.path),'--name',args.name,'--pattern',args.pattern]+(['--overwrite'] if args.overwrite else [])
    elif args.command=='create-recipe':
        from nicegui_base.ai_cli import create_recipe_main as cmd
        argv=['nicegui-base create-recipe',str(args.path),'--name',args.name,'--recipe',args.recipe]+(['--variant',args.variant] if args.variant else [])+(['--overwrite'] if args.overwrite else [])
    elif args.command=='recipes':
        from nicegui_base.ai_cli import recipes_main as cmd
        argv=['nicegui-base recipes']+([args.intent] if args.intent else [])+['--format',args.format]
    elif args.command=='catalog-search':
        from nicegui_base.ai_cli import catalog_search_main as cmd
        argv=['nicegui-base catalog-search']+([args.query] if args.query else [])+['--limit',str(args.limit)]+(['--intent',args.intent] if args.intent else [])+(['--data-shape',args.data_shape] if args.data_shape else [])+(['--domain',args.domain] if args.domain else [])+(['--related-to',args.related_to] if args.related_to else [])+['--format',args.format]
    elif args.command=='recommend-pattern':
        from nicegui_base.ai_cli import recommend_pattern_main as cmd
        argv=['nicegui-base recommend-pattern',args.requirement,'--format',args.format]
    elif args.command=='recommend-visualization':
        from nicegui_base.ai_cli import recommend_visualization_main as cmd
        argv=['nicegui-base recommend-visualization',args.intent]+sum((['--schema',value] for value in args.schema),[])+(['--domain',args.domain] if args.domain else [])+['--limit',str(args.limit),'--format',args.format]
    elif args.command=='scaffold-plan':
        from nicegui_base.ai_cli import scaffold_plan_main as cmd
        argv=['nicegui-base scaffold-plan',args.requirement,'--format',args.format]
    elif args.command=='catalog-audit':
        from nicegui_base.ai_cli import catalog_audit_main as cmd
        argv=['nicegui-base catalog-audit','--format',args.format]
    elif args.command=='agent-benchmark':
        from nicegui_base.ai_cli import benchmark_main as cmd
        argv=['nicegui-base agent-benchmark',str(args.manifest)]+(['--no-materialize'] if args.no_materialize else [])+['--format',args.format]
    elif args.command=='provider-init':
        from nicegui_base.semiconductor.provider_cli import provider_init_main as cmd
        argv=['nicegui-base provider-init',str(args.path),'--key',args.key,'--class-name',args.class_name,'--profile',args.profile]+sum((['--recipe',item] for item in (args.recipe or [])),[])+(['--overwrite'] if args.overwrite else [])
    elif args.command=='provider-check':
        from nicegui_base.semiconductor.provider_cli import provider_check_main as cmd
        argv=['nicegui-base provider-check',args.adapter,'--profile',args.profile,'--format',args.format]+sum((['--recipe',item] for item in (args.recipe or [])),[])+(['--fixtures',args.fixtures] if args.fixtures else [])+(['--benchmark-profile',args.benchmark_profile] if args.benchmark_profile else [])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='target-qualify':
        from nicegui_base.certification.semiconductor_target_cli import target_qualify_main as cmd
        argv=['nicegui-base target-qualify',*args.evidence,'--format',args.format]+(['--provider',args.provider] if args.provider else [])+(['--base-dir',str(args.base_dir)] if args.base_dir else [])+sum((['--operational-readiness',item] for item in (args.operational_readiness or [])),[])+sum((['--require-recipe',item] for item in (args.require_recipe or [])),[])+(['--qualification-output',str(args.qualification_output)] if args.qualification_output else [])+(['--decision-output',str(args.decision_output)] if args.decision_output else [])
    elif args.command=='promotion-candidate':
        from nicegui_base.certification.semiconductor_promotion_cli import promotion_candidate_main as cmd
        argv=['nicegui-base promotion-candidate',*args.evidence,'--format',args.format]+(['--provider',args.provider] if args.provider else [])+(['--base-dir',str(args.base_dir)] if args.base_dir else [])+sum((['--operational-readiness',item] for item in (args.operational_readiness or [])),[])+sum((['--require-recipe',item] for item in (args.require_recipe or [])),[])+sum((['--rehearsal',item] for item in (args.rehearsal or [])),[])+(['--target-version',args.target_version] if args.target_version else [])+(['--output',str(args.output)] if args.output else [])+(['--package',str(args.package)] if args.package else [])+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--no-artifact-bytes'] if args.no_artifact_bytes else [])
    elif args.command=='promotion-rehearse':
        from nicegui_base.certification.semiconductor_promotion_cli import promotion_rehearse_main as cmd
        argv=['nicegui-base promotion-rehearse',args.recipe,args.kind,'--format',args.format]+sum((['--completed',item] for item in (args.completed or [])),[])+sum((['--failed',item] for item in (args.failed or [])),[])+sum((['--note',item] for item in (args.note or [])),[])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='target-intake':
        from nicegui_base.certification.semiconductor_execution_cli import target_intake_main as cmd
        argv=['nicegui-base target-intake',args.evidence,args.manifest,'--adapter',args.adapter,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--intake-output',str(args.intake_output)] if args.intake_output else [])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='promotion-handoff':
        from nicegui_base.certification.semiconductor_execution_cli import promotion_handoff_main as cmd
        argv=['nicegui-base promotion-handoff',args.candidate,args.candidate_package,'--adapter',args.adapter,'--format',args.format]+(['--change-reference',args.change_reference] if args.change_reference else [])+(['--output',str(args.output)] if args.output else [])+(['--package',str(args.package)] if args.package else [])
    elif args.command=='promotion-operation':
        from nicegui_base.certification.semiconductor_execution_cli import promotion_operation_main as cmd
        argv=['nicegui-base promotion-operation',args.handoff,args.recipe,args.kind,'--format',args.format]+sum((['--completed',item] for item in (args.completed or [])),[])+sum((['--failed',item] for item in (args.failed or [])),[])+sum((['--evidence',item] for item in (args.evidence or [])),[])+sum((['--note',item] for item in (args.note or [])),[])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='execution-adapter-qualify':
        from nicegui_base.certification.semiconductor_release_audit_cli import execution_adapter_qualify_main as cmd
        argv=['nicegui-base execution-adapter-qualify',args.manifest,'--adapter',args.adapter,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='release-audit':
        from nicegui_base.certification.semiconductor_release_audit_cli import release_audit_main as cmd
        argv=['nicegui-base release-audit',args.handoff,args.qualification,*args.operations,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--output',str(args.output)] if args.output else [])+(['--package',str(args.package)] if args.package else [])
    elif args.command=='release-evidence-accept':
        from nicegui_base.certification.semiconductor_release_acceptance_cli import release_evidence_accept_main as cmd
        argv=['nicegui-base release-evidence-accept',args.audit,args.audit_archive,args.manifest,'--adapter',args.adapter,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='promotion-close':
        from nicegui_base.certification.semiconductor_release_acceptance_cli import promotion_close_main as cmd
        argv=['nicegui-base promotion-close',args.audit,args.audit_archive,args.acceptance,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--output',str(args.output)] if args.output else [])+(['--package',str(args.package)] if args.package else [])
    elif args.command=='release-publication-intake':
        from nicegui_base.certification.semiconductor_publication_cli import release_publication_intake_main as cmd
        argv=['nicegui-base release-publication-intake',args.closure,args.closure_archive,args.manifest,'--adapter',args.adapter,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='post-promotion-verify':
        from nicegui_base.certification.semiconductor_publication_cli import post_promotion_verify_main as cmd
        argv=['nicegui-base post-promotion-verify',args.closure,args.closure_archive,args.publication,args.manifest,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--output',str(args.output)] if args.output else [])+(['--package',str(args.package)] if args.package else [])
    elif args.command=='post-release-stability-intake':
        from nicegui_base.certification.semiconductor_stability_cli import post_release_stability_intake_main as cmd
        argv=['nicegui-base post-release-stability-intake',args.post_verification,args.post_promotion_archive,args.manifest,'--adapter',args.adapter,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='rollback-readiness-verify':
        from nicegui_base.certification.semiconductor_stability_cli import rollback_readiness_verify_main as cmd
        argv=['nicegui-base rollback-readiness-verify',args.post_verification,args.post_promotion_archive,args.stability,args.manifest,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--output',str(args.output)] if args.output else [])+(['--package',str(args.package)] if args.package else [])
    elif args.command=='sustained-operations-accept':
        from nicegui_base.certification.semiconductor_operations_cli import sustained_operations_accept_main as cmd
        argv=['nicegui-base sustained-operations-accept',args.readiness,args.readiness_archive,args.manifest,'--adapter',args.adapter,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='incident-rollback-audit-close':
        from nicegui_base.certification.semiconductor_operations_cli import incident_rollback_audit_close_main as cmd
        argv=['nicegui-base incident-rollback-audit-close',args.readiness,args.readiness_archive,args.acceptance,args.manifest,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--output',str(args.output)] if args.output else [])+(['--package',str(args.package)] if args.package else [])
    elif args.command=='operations-evidence-renew':
        from nicegui_base.certification.semiconductor_continuity_cli import operations_evidence_renew_main as cmd
        argv=['nicegui-base operations-evidence-renew',args.audit,args.audit_archive,args.manifest,'--adapter',args.adapter,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--now',args.now] if args.now else [])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='operational-assurance-continuity':
        from nicegui_base.certification.semiconductor_continuity_cli import operational_assurance_continuity_main as cmd
        argv=['nicegui-base operational-assurance-continuity',args.audit,args.audit_archive,args.renewal,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--now',args.now] if args.now else [])+(['--output',str(args.output)] if args.output else [])+(['--package',str(args.package)] if args.package else [])
    elif args.command=='operational-assurance-ledger':
        from nicegui_base.certification.semiconductor_longitudinal_cli import operational_assurance_ledger_main as cmd
        argv=['nicegui-base operational-assurance-ledger',*args.continuity_packages,'--format',args.format]+(['--now',args.now] if args.now else [])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='longitudinal-assurance':
        from nicegui_base.certification.semiconductor_longitudinal_cli import longitudinal_assurance_main as cmd
        argv=['nicegui-base longitudinal-assurance',args.ledger,'--format',args.format]+(['--now',args.now] if args.now else [])+(['--review-reference',args.review_reference] if args.review_reference else [])+(['--output',str(args.output)] if args.output else [])+(['--package',str(args.package)] if args.package else [])
    elif args.command=='longitudinal-assurance-review':
        from nicegui_base.certification.semiconductor_longitudinal_review_cli import longitudinal_assurance_review_main as cmd
        argv=['nicegui-base longitudinal-assurance-review',args.dossier,args.dossier_archive,args.manifest,'--adapter',args.adapter,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--now',args.now] if args.now else [])+(['--output',str(args.output)] if args.output else [])
    elif args.command=='evidence-exception-governance':
        from nicegui_base.certification.semiconductor_longitudinal_review_cli import evidence_exception_governance_main as cmd
        argv=['nicegui-base evidence-exception-governance',args.review,'--format',args.format]+(['--artifact-base-dir',str(args.artifact_base_dir)] if args.artifact_base_dir else [])+(['--now',args.now] if args.now else [])+(['--output',str(args.output)] if args.output else [])+(['--package',str(args.package)] if args.package else [])
    elif args.command=='final-audit':
        from nicegui_base.governance.final_candidate import audit_main as cmd
        argv=['nicegui-base final-audit','--root',str(args.root),'--format',args.format]+(['--output',str(args.output)] if args.output else [])+(['--allow-pre-final'] if args.allow_pre_final else [])
    elif args.command=='stable-qualification-handoff':
        from nicegui_base.governance.final_candidate import handoff_main as cmd
        argv=['nicegui-base stable-qualification-handoff','--root',str(args.root),'--output',str(args.output),'--format',args.format]
    elif args.command=='gate':
        from nicegui_base.ai_cli import gate_main as cmd
        argv=['nicegui-base gate',str(args.path),'--format',args.format]+(['--release'] if args.release else [])
    elif args.command=='certify':
        from nicegui_base.certification.live_certify import main as cmd
        argv=['nicegui-base certify','--output',str(args.output),'--baseline',str(args.baseline),'--root',str(args.root),'--port',str(args.port),'--format',args.format]
        if args.exhaustive:argv.append('--exhaustive')
        if args.no_edge:argv.append('--no-edge')
        if args.require_edge:argv.append('--require-edge')
        if args.require_baseline:argv.append('--require-baseline')
    else:
        from nicegui_base.certification.live_baseline import main as cmd
        argv=['nicegui-base approve-baseline','--output',str(args.output),'--baseline',str(args.baseline)]+(['--force'] if args.force else [])
    old=sys.argv;sys.argv=argv
    try:return cmd()
    finally:sys.argv=old

if __name__=='__main__':raise SystemExit(main())
