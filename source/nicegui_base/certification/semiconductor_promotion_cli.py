from __future__ import annotations

import argparse
import json
from pathlib import Path

from .semiconductor_promotion import (
    PromotionRehearsalKind,
    build_promotion_rehearsal,
    build_stable_promotion_candidate,
    load_enterprise_target_evidence,
    package_stable_promotion_candidate,
    read_promotion_rehearsal,
    write_promotion_candidate,
    write_promotion_rehearsal,
)


def promotion_candidate_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='nicegui-base promotion-candidate',
        description='Assimilate enterprise semiconductor target evidence into a deterministic stable-promotion candidate without inventing missing PASS evidence.',
    )
    parser.add_argument('evidence', nargs='+', help='Target-evidence JSON bundle(s) produced by the existing evidence authority.')
    parser.add_argument('--provider', help='Expected provider key; required when evidence does not identify exactly one provider.')
    parser.add_argument('--base-dir', type=Path, help='Base directory used to verify relative evidence artifact paths.')
    parser.add_argument('--operational-readiness', action='append', default=[], help='Operational-readiness JSON report; repeat for multiple recipes.')
    parser.add_argument('--require-recipe', action='append', default=[], help='Recipe required for stable promotion; repeat as needed.')
    parser.add_argument('--rehearsal', action='append', default=[], help='Recorded promotion-rehearsal JSON; repeat as needed.')
    parser.add_argument('--target-version', default=None, help='Release target version; defaults to the stable release-channel policy.')
    parser.add_argument('--output', type=Path, help='Write the promotion candidate JSON.')
    parser.add_argument('--package', type=Path, help='Write a deterministic promotion-candidate ZIP package.')
    parser.add_argument('--artifact-base-dir', type=Path, help='Base directory for copying hash-verified evidence artifacts into the package.')
    parser.add_argument('--no-artifact-bytes', action='store_true', help='Package manifests/evidence only; do not copy external artifact bytes.')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)

    evidence = load_enterprise_target_evidence(
        args.evidence,
        operational_readiness_paths=args.operational_readiness,
        provider=args.provider,
        required_recipe_keys=args.require_recipe,
        base_dir=args.base_dir,
    )
    rehearsals = tuple(read_promotion_rehearsal(path) for path in args.rehearsal)
    candidate = build_stable_promotion_candidate(evidence, rehearsals=rehearsals, target_version=args.target_version)
    if args.output:
        write_promotion_candidate(args.output, candidate)
    package = None
    if args.package:
        package = package_stable_promotion_candidate(
            args.package,
            candidate,
            artifact_base_dir=args.artifact_base_dir if args.artifact_base_dir is not None else args.base_dir,
            include_verified_artifacts=not args.no_artifact_bytes,
        )
    payload = {'candidate': candidate.to_dict(), 'package': None if package is None else package.to_dict()}
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(f'Promotion candidate: {candidate.candidate_id}')
        print(f'Channel: {candidate.channel} -> {candidate.target_version}')
        print(f'Enterprise evidence: {candidate.evidence.decision.status.value.upper()}')
        print(f'Release-channel candidate: {candidate.status.value.upper()}')
        for gap in candidate.gaps:
            print(f'[{gap.severity.value.upper():7}] {gap.category}/{gap.code}: {gap.message}')
        if package is not None:
            print(f'Package: {package.path} sha256={package.sha256}')
    if candidate.release_channel_ready:
        return 0
    return 1 if candidate.status.value == 'blocked' else 2


def promotion_rehearse_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='nicegui-base promotion-rehearse',
        description='Record a provider-neutral operational rehearsal against the canonical semiconductor runbook. Rehearsal completion never changes target certification gates.',
    )
    parser.add_argument('recipe')
    parser.add_argument('kind', choices=tuple(item.value for item in PromotionRehearsalKind))
    parser.add_argument('--completed', action='append', default=[], help='Canonical runbook step successfully rehearsed; repeat as needed.')
    parser.add_argument('--failed', action='append', default=[], help='Canonical runbook step that failed rehearsal; repeat as needed.')
    parser.add_argument('--note', action='append', default=[])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)

    report = build_promotion_rehearsal(
        args.recipe, args.kind, completed_step_keys=args.completed, failed_step_keys=args.failed, notes=args.note,
    )
    if args.output:
        write_promotion_rehearsal(args.output, report)
    if args.format == 'json':
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(f'{report.recipe_key} / {report.kind.value}: {report.status.value.upper()}')
        if report.remaining_step_keys:
            print('Remaining: ' + ', '.join(report.remaining_step_keys))
        if report.failed_step_keys:
            print('Failed: ' + ', '.join(report.failed_step_keys))
        print('Target gate status: unchanged by rehearsal')
    if report.status.value == 'pass':
        return 0
    return 1 if report.status.value == 'blocked' else 2


__all__ = ['promotion_candidate_main', 'promotion_rehearse_main']
