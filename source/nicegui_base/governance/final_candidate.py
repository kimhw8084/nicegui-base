from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from nicegui_base.ai.scaffold import GUIDE_NAMES
from .public_api import export_digest, public_api_snapshot
from .release_artifacts import sha256_file, verify_wheel, verify_wheel_source_representation
from .release_identity import ReleaseIdentity, load_release_identity


AUTHORITY_CHAIN: tuple[dict[str, Any], ...] = (
    {'wave': 59, 'owner': 'DataSource', 'domains': ('data-query', 'provider-query-pushdown')},
    {'wave': 60, 'owner': 'AnalysisContext/SelectionBus/workspace', 'domains': ('shared-analysis-state', 'selection', 'workspace-persistence')},
    {'wave': 61, 'owner': 'semiconductor semantic analytics', 'domains': ('semiconductor-semantics', 'semiconductor-analytics')},
    {'wave': 62, 'owner': 'semiconductor recipe factory', 'domains': ('application-recipes',)},
    {'wave': 63, 'owner': 'recipe runtime/onboarding/variants', 'domains': ('recipe-runtime', 'schema-onboarding', 'recipe-variants')},
    {'wave': 64, 'owner': 'provider conformance/runtime experience', 'domains': ('provider-conformance', 'runtime-experience', 'performance-targets')},
    {'wave': 65, 'owner': 'provider SDK/setup/portable evidence', 'domains': ('provider-sdk', 'setup-workflow', 'portable-target-evidence')},
    {'wave': 66, 'owner': 'target qualification/stable promotion truth', 'domains': ('target-qualification', 'stable-promotion-decision', 'evidence-freshness', 'operational-readiness')},
    {'wave': 67, 'owner': 'promotion candidate/evidence assimilation', 'domains': ('promotion-candidate', 'candidate-evidence-assimilation', 'promotion-rehearsal')},
    {'wave': 68, 'owner': 'target execution intake/operational handoff', 'domains': ('target-execution-intake', 'promotion-operational-handoff', 'operation-evidence')},
    {'wave': 69, 'owner': 'execution adapter qualification/release audit', 'domains': ('execution-adapter-qualification', 'release-audit-closure')},
    {'wave': 70, 'owner': 'release acceptance/documentary closure', 'domains': ('release-evidence-acceptance', 'documentary-promotion-closure')},
    {'wave': 71, 'owner': 'publication/post-promotion verification', 'domains': ('publication-evidence', 'post-promotion-verification')},
    {'wave': 72, 'owner': 'post-release stability/rollback readiness', 'domains': ('post-release-stability', 'rollback-readiness')},
    {'wave': 73, 'owner': 'sustained operations/incident rollback audit', 'domains': ('sustained-operations-acceptance', 'incident-rollback-audit')},
    {'wave': 74, 'owner': 'renewal/continuity', 'domains': ('operations-evidence-renewal', 'operational-assurance-continuity')},
    {'wave': 75, 'owner': 'longitudinal renewal ledger', 'domains': ('longitudinal-renewal-ledger', 'longitudinal-assurance-dossier')},
    {'wave': 76, 'owner': 'external review/exception governance', 'domains': ('longitudinal-review', 'evidence-exception-governance')},
)

CURRENT_SOURCE_EVIDENCE = (
    'CERTIFICATION_REPORT.json', 'TEST_REPORT.json', 'GOVERNANCE_REPORT.json',
    'SHIPPED_EXAMPLES_VALIDATION.json', 'LIVE_COMPONENT_COVERAGE.json',
    'PUBLIC_API_CONTRACT.json',
)
HISTORICAL_OR_EXTERNAL_EVIDENCE = (
    'GOLD_PROMOTION_READINESS.json', 'BROWSER_UIUX_GATE.json', 'CLEAN_INSTALL_CERTIFICATION.json',
    'TARGET_RUNTIME_GATE_ATTEMPT.json',
)
RELEASE_MIRROR_PAIRS = (
    ('FRAMEWORK_CATALOG.json', 'nicegui_base/ai/framework_catalog.json'),
    ('AI_CONSTRUCTION_MANIFEST.json', 'nicegui_base/ai/construction_manifest.json'),
    ('COMPATIBILITY.json', 'nicegui_base/runtime/compatibility.json'),
    ('docs/PUBLIC_API_INDEX.md', 'nicegui_base/ai/guides/PUBLIC_API_INDEX.md'),
)


@dataclass(frozen=True, slots=True)
class FinalAuditFinding:
    code: str
    severity: str
    message: str
    remediation: str = ''
    paths: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'severity': self.severity, 'message': self.message, 'remediation': self.remediation, 'paths': list(self.paths)}


@dataclass(frozen=True, slots=True)
class FinalReleaseCandidateAudit:
    identity: ReleaseIdentity
    status: str
    findings: tuple[FinalAuditFinding, ...]
    authority_chain: tuple[dict[str, Any], ...]
    evidence_index: dict[str, Any]
    public_api_entries: int
    public_api_sha256: str
    wheel_sha256: str | None
    source_complete: bool
    target_qualification_status: str = 'PENDING'
    stable_publication_status: str = 'NOT_PERFORMED'
    diagnostic_only: bool = True

    @property
    def errors(self) -> tuple[FinalAuditFinding, ...]:
        return tuple(item for item in self.findings if item.severity == 'error')

    @property
    def warnings(self) -> tuple[FinalAuditFinding, ...]:
        return tuple(item for item in self.findings if item.severity == 'warning')

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1, 'diagnostic_only': self.diagnostic_only,
            'identity': self.identity.to_dict(), 'status': self.status,
            'source_complete': self.source_complete, 'target_qualification_status': self.target_qualification_status,
            'stable_publication_status': self.stable_publication_status,
            'summary': {'errors': len(self.errors), 'warnings': len(self.warnings)},
            'public_api_entries': self.public_api_entries, 'public_api_sha256': self.public_api_sha256,
            'wheel_sha256': self.wheel_sha256, 'authority_chain': list(self.authority_chain),
            'evidence_index': self.evidence_index, 'findings': [item.to_dict() for item in self.findings],
        }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError(f'{path} must contain a JSON object')
    return payload


def _authority_chain_findings() -> list[FinalAuditFinding]:
    seen: dict[str, int] = {}; findings: list[FinalAuditFinding] = []
    for entry in AUTHORITY_CHAIN:
        for domain in entry['domains']:
            if domain in seen:
                findings.append(FinalAuditFinding('authority_duplicate_owner', 'error', f'{domain!r} is owned by both Wave {seen[domain]} and Wave {entry["wave"]}.', 'Keep one canonical owner per truth domain.'))
            seen[domain] = int(entry['wave'])
    return findings


def _evidence_index(root: Path, identity: ReleaseIdentity) -> dict[str, Any]:
    current: list[dict[str, str]] = []
    historical: list[dict[str, str]] = []
    pending_external: list[dict[str, str]] = []
    for rel in CURRENT_SOURCE_EVIDENCE:
        if (root / rel).is_file(): current.append({'path': rel, 'classification': 'CURRENT_SOURCE_GENERATED'})
    latest = (
        f'PHASE_{identity.current_phase}_V300A8_FINAL_RELEASE_CANDIDATE_CONSOLIDATION_AUTHORITY_AUDIT_STABLE_QUALIFICATION_HANDOFF_REPORT.json',
        f'PUBLIC_API_COMPATIBILITY_WAVE{identity.current_wave}.json',
        f'PYTEST_BATCH_REPORT_WAVE{identity.current_wave}.json',
        f'WHEEL_VERIFICATION_WAVE{identity.current_wave}.json',
    )
    for rel in latest:
        if (root / rel).is_file(): current.append({'path': rel, 'classification': 'CURRENT_RELEASE_AUTHORITY'})
    for rel in HISTORICAL_OR_EXTERNAL_EVIDENCE:
        if not (root / rel).is_file(): continue
        if rel in {'BROWSER_UIUX_GATE.json', 'CLEAN_INSTALL_CERTIFICATION.json', 'TARGET_RUNTIME_GATE_ATTEMPT.json'}:
            pending_external.append({'path': rel, 'classification': 'PENDING_OR_STALE_EXTERNAL_ENVIRONMENT'})
        else:
            historical.append({'path': rel, 'classification': 'HISTORICAL_ONLY'})
    for path in sorted(root.glob('PHASE_*_REPORT.json')):
        if path.name.startswith(f'PHASE_{identity.current_phase}_'): continue
        historical.append({'path': path.name, 'classification': 'HISTORICAL_PHASE_EVIDENCE'})
    return {'current': current, 'pending_external': pending_external, 'historical': historical}


def _check_batch_report(root: Path, identity: ReleaseIdentity, findings: list[FinalAuditFinding]) -> None:
    path = root / f'PYTEST_BATCH_REPORT_WAVE{identity.current_wave}.json'
    if not path.exists():
        findings.append(FinalAuditFinding('batch_report_missing', 'error', f'{path.name} is missing.', 'Run the final fresh-process estate and freeze its batch report.', (path.name,))); return
    payload = _load_json(path)
    if payload.get('status') != 'PASS':
        findings.append(FinalAuditFinding('batch_report_not_pass', 'error', f'{path.name} is not PASS.', 'Rerun the complete regression estate.', (path.name,)))
        return
    results = payload.get('results')
    expected = [str(p.relative_to(root)) for p in sorted((root / 'tests').glob('test_*.py'))]
    actual: list[str] = []
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict): actual.extend(str(value) for value in item.get('files', ()))
    if actual != expected:
        findings.append(FinalAuditFinding('batch_report_coverage_drift', 'error', f'Final batch report covers {len(actual)}/{len(expected)} test files in deterministic order.', 'Regenerate the batch report from the current source tree.', (path.name,)))


def _check_shell_modes(root: Path, findings: list[FinalAuditFinding]) -> None:
    shell_paths = sorted({*root.glob('*.sh'), *root.glob('*_bundle/*.sh')})
    missing_exec = [str(path.relative_to(root)) for path in shell_paths if not (stat.S_IMODE(path.stat().st_mode) & 0o111)]
    if missing_exec:
        findings.append(FinalAuditFinding('shell_executable_mode_lost', 'error', f'{len(missing_exec)} shipped shell entrypoints are not executable.', 'Restore executable modes from the authoritative package and preserve them in ZIP external attributes.', tuple(missing_exec)))


def _check_guides(root: Path, findings: list[FinalAuditFinding]) -> None:
    package_guides = root / 'nicegui_base/ai/guides'
    missing = [name for name in GUIDE_NAMES if not (package_guides / name).is_file()]
    if missing:
        findings.append(FinalAuditFinding('generated_guide_inventory_drift', 'error', f'{len(missing)} generated-app guides are missing from package data.', 'Synchronize GUIDE_NAMES with packaged guides.', tuple(missing)))
    scaffold = (root / 'nicegui_base/ai/scaffold.py').read_text(encoding='utf-8')
    required_commands = ('longitudinal_assurance_review_command', 'evidence_exception_governance_command')
    missing_commands = [item for item in required_commands if item not in scaffold]
    if missing_commands:
        findings.append(FinalAuditFinding('generated_command_inventory_drift', 'error', 'Generated-app install metadata is missing current release commands.', 'Synchronize generated command metadata with the canonical CLI.', tuple(missing_commands)))
    framework_cli = (root / 'nicegui_base/cli.py').read_text(encoding='utf-8')
    pyproject = (root / 'pyproject.toml').read_text(encoding='utf-8')
    if "sub.add_parser('final-audit'" not in framework_cli or "sub.add_parser('stable-qualification-handoff'" not in framework_cli or 'nicegui-base-final-audit' not in pyproject or 'nicegui-base-stable-handoff' not in pyproject:
        findings.append(FinalAuditFinding('framework_release_cli_drift', 'error', 'Framework final-audit/stable-handoff tools are not fully routed.', 'Keep final release tooling on the framework CLI rather than generated application workspaces.', ('nicegui_base/cli.py', 'pyproject.toml')))



def _check_current_evidence_portability(root: Path, findings: list[FinalAuditFinding]) -> None:
    root_text = str(root)
    for rel in ('GOVERNANCE_REPORT.json', 'SHIPPED_EXAMPLES_VALIDATION.json'):
        path = root / rel
        if not path.is_file():
            findings.append(FinalAuditFinding('current_evidence_missing', 'error', f'{rel} is missing.', 'Regenerate current source evidence.', (rel,)))
            continue
        text = path.read_text(encoding='utf-8')
        if root_text in text or '/mnt/data/' in text:
            findings.append(FinalAuditFinding('current_evidence_build_path_leak', 'error', f'{rel} contains a build-machine absolute path.', 'Normalize evidence roots to portable relative labels before package freeze.', (rel,)))

def audit_final_release_candidate(root: str | Path = '.', *, require_final_artifacts: bool = True) -> FinalReleaseCandidateAudit:
    root = Path(root).resolve(); identity = load_release_identity(root); findings = _authority_chain_findings()
    contract = _load_json(root / 'PUBLIC_API_CONTRACT.json'); snapshot = public_api_snapshot(); api_digest = export_digest(snapshot)
    if contract.get('symbols') != snapshot or contract.get('sha256') != api_digest:
        findings.append(FinalAuditFinding('public_api_contract_drift', 'error', 'PUBLIC_API_CONTRACT.json does not match the importable root API.', 'Run nicegui-base-release-sync after intentional API changes.', ('PUBLIC_API_CONTRACT.json',)))
    if int(contract.get('export_count', -1)) != len(snapshot):
        findings.append(FinalAuditFinding('public_api_count_drift', 'error', 'Stored public API export_count is inconsistent.', 'Regenerate the public API contract.', ('PUBLIC_API_CONTRACT.json',)))
    module_exports = [name for name in snapshot if snapshot[name].get('kind') == 'module']
    if module_exports:
        findings.append(FinalAuditFinding('legacy_module_reexports_preserved', 'info', f'{len(module_exports)} legacy root module re-exports remain frozen for compatibility; Wave 77 does not remove them.', 'Consider deprecation only in a future major-version decision.', tuple(module_exports[:24])))

    cert_manifest = _load_json(root / 'nicegui_base/certification/certification_manifest.json')
    if int(cert_manifest.get('phase', -1)) != identity.current_phase:
        findings.append(FinalAuditFinding('certification_phase_drift', 'error', f'Certification manifest phase={cert_manifest.get("phase")!r}; release authority phase={identity.current_phase}.', 'Run source certification after release identity synchronization.', ('nicegui_base/certification/certification_manifest.json', 'nicegui_base/release_authority.json')))
    phase_report = root / f'PHASE_{identity.current_phase}_V300A8_FINAL_RELEASE_CANDIDATE_CONSOLIDATION_AUTHORITY_AUDIT_STABLE_QUALIFICATION_HANDOFF_REPORT.json'
    compat = root / f'PUBLIC_API_COMPATIBILITY_WAVE{identity.current_wave}.json'
    if require_final_artifacts:
        for path, code in ((phase_report, 'phase_report_missing'), (compat, 'compatibility_report_missing')):
            if not path.is_file(): findings.append(FinalAuditFinding(code, 'error', f'{path.name} is missing.', 'Generate final Wave release authorities before packaging.', (path.name,)))
        _check_batch_report(root, identity, findings)

    for left, right in RELEASE_MIRROR_PAIRS:
        a = root / left; b = root / right
        if not a.is_file() or not b.is_file() or a.read_bytes() != b.read_bytes():
            findings.append(FinalAuditFinding('release_mirror_drift', 'error', f'Release mirror mismatch: {left} <> {right}.', 'Regenerate mirrors from the canonical source.', (left, right)))
    _check_shell_modes(root, findings); _check_guides(root, findings)
    _check_current_evidence_portability(root, findings)

    release_sync = (root / 'nicegui_base/governance/release_sync.py').read_text(encoding='utf-8')
    if "'GOLD_PROMOTION_READINESS.json'" in release_sync.split('_CURRENT_EVIDENCE_JSONS', 1)[1].split(')', 1)[0]:
        findings.append(FinalAuditFinding('historical_evidence_rewritten_by_release_sync', 'error', 'release-sync still rewrites historical GOLD_PROMOTION_READINESS evidence.', 'Historical execution/promotion/browser evidence must never be made to look current by identity synchronization.', ('nicegui_base/governance/release_sync.py', 'GOLD_PROMOTION_READINESS.json')))

    wheel_sha: str | None = None
    if require_final_artifacts:
        wheel_paths = [root / 'wheel/nicegui_base-3.0.0a8-py3-none-any.whl', root / 'dist/nicegui_base-3.0.0a8-py3-none-any.whl']
        existing = [path for path in wheel_paths if path.is_file()]
        if len(existing) != len(wheel_paths):
            findings.append(FinalAuditFinding('wheel_copy_missing', 'error', 'Final wheel must exist in both wheel/ and dist/.', 'Rebuild and copy the post-sync wheel before checksum freeze.', tuple(str(p.relative_to(root)) for p in wheel_paths)))
        elif existing[0].read_bytes() != existing[1].read_bytes():
            findings.append(FinalAuditFinding('wheel_copy_mismatch', 'error', 'wheel/ and dist/ contain different wheel bytes.', 'Use one frozen post-sync wheel in both locations.', tuple(str(p.relative_to(root)) for p in wheel_paths)))
        else:
            wheel = verify_wheel(existing[0]); wheel_sha = wheel.sha256
            production_requires = tuple(item for item in wheel.requires_dist if 'extra ==' not in item)
            if not wheel.passed or wheel.metadata_name != 'nicegui-base' or wheel.metadata_version != identity.framework_version or production_requires != (f'nicegui=={identity.nicegui_version}',):
                findings.append(FinalAuditFinding('wheel_integrity_or_metadata_drift', 'error', 'Final wheel RECORD/metadata/runtime pin is inconsistent with release identity.', 'Rebuild the wheel from the synchronized certified source.', (str(existing[0].relative_to(root)),)))
            representation = verify_wheel_source_representation(root, existing[0])
            if not representation.passed:
                paths = tuple((*representation.mismatches[:12], *representation.missing_from_wheel[:12], *representation.missing_from_source[:12]))
                findings.append(FinalAuditFinding('wheel_source_representation_drift', 'error', f'Final wheel does not represent the synchronized source/package data ({len(representation.mismatches)} changed, {len(representation.missing_from_wheel)} missing from wheel, {len(representation.missing_from_source)} missing from source).', 'Rebuild the wheel only after all source certification, documentation and release-sync mutations are complete.', paths))

    errors = [item for item in findings if item.severity == 'error']
    status = 'PASS' if not errors else 'BLOCKED'
    return FinalReleaseCandidateAudit(
        identity=identity, status=status, findings=tuple(findings), authority_chain=AUTHORITY_CHAIN,
        evidence_index=_evidence_index(root, identity), public_api_entries=len(snapshot), public_api_sha256=api_digest,
        wheel_sha256=wheel_sha, source_complete=not errors, target_qualification_status='PENDING', stable_publication_status='NOT_PERFORMED',
    )


def write_final_release_candidate_audit(path: str | Path, audit: FinalReleaseCandidateAudit) -> Path:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit.to_dict(), indent=2, sort_keys=True) + '\n', encoding='utf-8'); return path


def build_stable_qualification_handoff(root: str | Path = '.', audit: FinalReleaseCandidateAudit | None = None) -> dict[str, Any]:
    root = Path(root).resolve(); audit = audit or audit_final_release_candidate(root)
    pending = [
        'installed NiceGUI 3.15.0 target-runtime contract', 'real 21-route server/WebSocket execution',
        'approved company provider/data qualification and fab-scale benchmark', 'supported corporate browser/publisher execution',
        'human visual baseline where required', 'approved reviewer/authority/reference evidence where applicable',
        'real deployment/publication/monitoring/incident/rollback evidence where applicable',
    ]
    return {
        'schema_version': 1, 'diagnostic_only': True, 'framework': audit.identity.framework_name,
        'framework_version': audit.identity.framework_version, 'nicegui_version': audit.identity.nicegui_version,
        'wave': audit.identity.current_wave, 'promotion_target': audit.identity.promotion_target,
        'source_release_candidate_status': 'SOURCE_COMPLETE' if audit.status == 'PASS' else 'BLOCKED',
        'stable_qualification_status': 'PENDING' if audit.status == 'PASS' else 'BLOCKED',
        'stable_publication_status': 'NOT_PERFORMED', 'audit_public_api_entries': audit.public_api_entries,
        'audit_public_api_sha256': audit.public_api_sha256, 'audit_wheel_sha256': audit.wheel_sha256,
        'pending_external_qualification': pending,
        'claim_boundary': 'Wave 77 consolidates and audits the source-complete release candidate only. It cannot turn missing company/runtime/browser/human/reviewer/deployment/publication/operations evidence into PASS and does not publish stable 3.0.0.',
        'next_action': 'Run setup.sh and certify.sh in the approved target environment, then feed only real captured artifacts into the existing Waves 64–76 qualification authorities.',
    }


def write_stable_qualification_handoff(path: str | Path, handoff: dict[str, Any]) -> Path:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(handoff, indent=2, sort_keys=True) + '\n', encoding='utf-8'); return path


def audit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Audit the final NiceGUI Base release candidate without inventing target evidence.')
    parser.add_argument('--root', default='.'); parser.add_argument('--output', type=Path); parser.add_argument('--format', choices=('text', 'json'), default='text')
    parser.add_argument('--allow-pre-final', action='store_true', help='Do not require final Wave reports/wheel while developing the consolidation wave.')
    args = parser.parse_args(argv); audit = audit_final_release_candidate(args.root, require_final_artifacts=not args.allow_pre_final)
    if args.output: write_final_release_candidate_audit(args.output, audit)
    if args.format == 'json': print(json.dumps(audit.to_dict(), indent=2, sort_keys=True))
    else:
        print(f'Final release-candidate audit: {audit.status} · {len(audit.errors)} errors · {len(audit.warnings)} warnings')
        print(f'Framework {audit.identity.framework_version} Wave {audit.identity.current_wave} · API {audit.public_api_entries} · target qualification {audit.target_qualification_status}')
        for item in audit.findings:
            print(f'[{item.severity.upper():7}] {item.code}: {item.message}')
    return 0 if audit.status == 'PASS' else 1


def handoff_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Write a truthful stable-qualification handoff from the final source-complete release candidate.')
    parser.add_argument('--root', default='.'); parser.add_argument('--output', type=Path, default=Path('STABLE_QUALIFICATION_HANDOFF.json')); parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv); audit = audit_final_release_candidate(args.root); handoff = build_stable_qualification_handoff(args.root, audit); write_stable_qualification_handoff(args.output, handoff)
    if args.format == 'json': print(json.dumps(handoff, indent=2, sort_keys=True))
    else: print(f"Stable qualification handoff: {handoff['stable_qualification_status']} · source {handoff['source_release_candidate_status']} · {args.output}")
    return 0 if audit.status == 'PASS' else 1


__all__ = [
    'AUTHORITY_CHAIN', 'FinalAuditFinding', 'FinalReleaseCandidateAudit', 'audit_final_release_candidate',
    'write_final_release_candidate_audit', 'build_stable_qualification_handoff', 'write_stable_qualification_handoff',
    'audit_main', 'handoff_main',
]
