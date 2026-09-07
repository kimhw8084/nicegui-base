from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from nicegui_base.version import FRAMEWORK_VERSION

GUIDE_NAMES = (
    'AI_RULES.md',
    'COMPONENT_CATALOG.md',
    'LAYOUT_RULES.md',
    'APP_PATTERNS.md',
    'RECIPES.md',
    'ANTI_PATTERNS.md',
    'ICON_CATALOG.md',
    'VISUAL_RESOURCE_GUIDE.md',
    'TROUBLESHOOTING.md',
    'PERFORMANCE_GUIDE.md',
    'ZERO_STOCK_NICEGUI_VISUAL_LAWS.md',
    'VALIDATOR_RULES.md',
    'AI_QUICKSTART.md',
    'AGENT_WORKFLOW.md',
    'OPENCODE_GEMMA_BOOTSTRAP.md',
    'SEMICONDUCTOR_APPLICATION_RECIPES.md',
    'SEMICONDUCTOR_RUNTIME_ONBOARDING.md',
    'SEMICONDUCTOR_PRODUCTION_RUNTIME.md',
    'SEMICONDUCTOR_PROVIDER_SDK_RC.md',
    'SEMICONDUCTOR_TARGET_CERTIFICATION.md',
    'SEMICONDUCTOR_STABLE_PROMOTION_CANDIDATE.md',
    'SEMICONDUCTOR_TARGET_EXECUTION_OPERATIONAL_HANDOFF.md',
    'SEMICONDUCTOR_PROMOTION_EXECUTION_ADAPTER_RELEASE_AUDIT.md',
    'SEMICONDUCTOR_STABLE_RELEASE_EVIDENCE_ACCEPTANCE_PROMOTION_CLOSURE.md',
    'SEMICONDUCTOR_RELEASE_PUBLICATION_POST_PROMOTION_VERIFICATION.md',
    'SEMICONDUCTOR_POST_RELEASE_STABILITY_ROLLBACK_READINESS.md',
    'SEMICONDUCTOR_SUSTAINED_OPERATIONS_INCIDENT_ROLLBACK_AUDIT.md',
    'SEMICONDUCTOR_SUSTAINED_OPERATIONS_RENEWAL_CONTINUITY.md',
    'SEMICONDUCTOR_OPERATIONAL_ASSURANCE_RENEWAL_LEDGER.md',
    'SEMICONDUCTOR_LONGITUDINAL_ASSURANCE_REVIEW_EXCEPTION_GOVERNANCE.md',
    'FINAL_RELEASE_CANDIDATE_STABLE_QUALIFICATION_HANDOFF.md',
)



GOLDEN_EXAMPLE_NAMES = (
    'golden_dashboard.py', 'golden_data_explorer.py', 'golden_crud.py', 'golden_analysis_workspace.py', 'README.md',
)


def read_ai_guide(name: str) -> str:
    if name != 'AGENTS.md' and name not in GUIDE_NAMES:
        raise KeyError(f'Unknown AI guide {name!r}; allowed: AGENTS.md, {", ".join(GUIDE_NAMES)}')
    return files('nicegui_base.ai').joinpath('guides', name).read_text(encoding='utf-8')


def install_ai_materials(destination: str | Path, *, overwrite: bool = False) -> tuple[Path, ...]:
    """Install the agent contract into an application workspace.

    AGENTS.md is placed at the workspace root; detailed guides are placed under
    docs/nicegui_base/. Machine-readable construction/catalog JSON is copied to
    .nicegui_base/ so coding agents can inspect it without importing Python.
    """
    dest = Path(destination)
    docs = dest / 'docs' / 'nicegui_base'
    meta = dest / '.nicegui_base'
    docs.mkdir(parents=True, exist_ok=True)
    meta.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def write(target: Path, content: str) -> None:
        if target.exists() and not overwrite:
            return
        target.write_text(content, encoding='utf-8')
        written.append(target)

    write(dest/'AGENTS.md', read_ai_guide('AGENTS.md'))
    for name in GUIDE_NAMES:
        write(docs/name, read_ai_guide(name))
    package = files('nicegui_base.ai')
    write(meta/'construction_manifest.json', package.joinpath('construction_manifest.json').read_text(encoding='utf-8'))
    write(meta/'framework_catalog.json', package.joinpath('framework_catalog.json').read_text(encoding='utf-8'))
    golden = package.joinpath('templates', 'golden')
    example_dir = dest / 'examples' / 'nicegui_base'
    example_dir.mkdir(parents=True, exist_ok=True)
    for name in GOLDEN_EXAMPLE_NAMES:
        write(example_dir/name, golden.joinpath(name).read_text(encoding='utf-8'))
    write(meta/'install_manifest.json', json.dumps({
        'framework': 'nicegui-base', 'framework_version': FRAMEWORK_VERSION,
        'golden_examples': [f'examples/nicegui_base/{name}' for name in GOLDEN_EXAMPLE_NAMES if name.endswith('.py')],
        'create_command': 'nicegui-base create <path> --name <name> --template <template> [--recipe <semiconductor-recipe>] [--variant <recipe-variant>]',
        'recipe_discovery_command': 'nicegui-base recipes [intent]',
        'catalog_search_command': 'nicegui-base catalog-search "<intent>" --format json',
        'pattern_recommendation_command': 'nicegui-base recommend-pattern "<requirement>" --format json',
        'visualization_recommendation_command': 'nicegui-base recommend-visualization "<intent>" --schema <field> --format json',
        'scaffold_plan_command': 'nicegui-base scaffold-plan "<requirement>" --format json',
        'catalog_audit_command': 'nicegui-base catalog-audit --format json',
        'agent_benchmark_command': 'nicegui-base agent-benchmark agent_tasks/manifest.json --format json',
        'provider_init_command': 'nicegui-base provider-init <path> --key <adapter-key>',
        'provider_check_command': 'nicegui-base provider-check <module:adapter> --recipe <recipe> --profile production',
        'target_qualify_command': 'nicegui-base target-qualify <evidence.json> --operational-readiness <readiness.json>',
        'promotion_candidate_command': 'nicegui-base promotion-candidate <evidence.json> --operational-readiness <readiness.json> --package <candidate.zip>',
        'promotion_rehearse_command': 'nicegui-base promotion-rehearse <recipe> <promotion|rollback|incident|evidence-capture>',
        'target_intake_command': 'nicegui-base target-intake <evidence.json> <execution-manifest.json> --output <merged-evidence.json>',
        'promotion_handoff_command': 'nicegui-base promotion-handoff <candidate.json> <candidate.zip> --package <handoff.zip>',
        'promotion_operation_command': 'nicegui-base promotion-operation <handoff.json> <recipe> <kind>',
        'release_evidence_accept_command': 'nicegui-base release-evidence-accept <audit.json> <audit.zip> <acceptance-manifest.json>',
        'promotion_close_command': 'nicegui-base promotion-close <audit.json> <audit.zip> <acceptance.json>',
        'release_publication_intake_command': 'nicegui-base release-publication-intake <closure.json> <closure.zip> <publication-manifest.json>',
        'post_promotion_verify_command': 'nicegui-base post-promotion-verify <closure.json> <closure.zip> <publication.json> <verification-manifest.json>',
        'post_release_stability_intake_command': 'nicegui-base post-release-stability-intake <post-verification.json> <post-promotion.zip> <stability-manifest.json>',
        'rollback_readiness_verify_command': 'nicegui-base rollback-readiness-verify <post-verification.json> <post-promotion.zip> <stability.json> <rollback-manifest.json>',
        'sustained_operations_accept_command': 'nicegui-base sustained-operations-accept <readiness.json> <readiness.zip> <acceptance-manifest.json>',
        'incident_rollback_audit_close_command': 'nicegui-base incident-rollback-audit-close <readiness.json> <readiness.zip> <acceptance.json> <audit-manifest.json>',
        'operations_evidence_renew_command': 'nicegui-base operations-evidence-renew <audit.json> <audit.zip> <renewal-manifest.json>',
        'operational_assurance_continuity_command': 'nicegui-base operational-assurance-continuity <audit.json> <audit.zip> <renewal.json>',
        'operational_assurance_ledger_command': 'nicegui-base operational-assurance-ledger <wave74.zip> [<wave74.zip> ...]',
        'longitudinal_assurance_command': 'nicegui-base longitudinal-assurance <ledger.json> --package <wave75.zip>',
        'longitudinal_assurance_review_command': 'nicegui-base longitudinal-assurance-review <dossier.json> <wave75.zip> <review-manifest.json>',
        'evidence_exception_governance_command': 'nicegui-base evidence-exception-governance <review.json> --package <wave76.zip>',
        'agent_context_command': 'nicegui-base agent-context <task>',
        'agent_check_command': 'nicegui-base agent-check .',
        'application_gate_command': 'nicegui-base gate .',
        'runtime_check_command': 'nicegui-base gate . --release',
        'generated_files': [str(p.relative_to(dest)) for p in written],
    }, indent=2, sort_keys=True) + '\n')
    return tuple(written)
