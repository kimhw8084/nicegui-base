from __future__ import annotations

import argparse
import json
from pathlib import Path

from .semiconductor_execution import (
    PROMOTION_OPERATIONAL_HANDOFF_ADAPTERS,
    TARGET_EXECUTION_INTAKE_ADAPTERS,
    PromotionHandoffStatus,
    PromotionOperationStatus,
    TargetExecutionIntakeStatus,
    apply_target_execution_intake,
    build_promotion_operation_record,
    capture_promotion_operation_evidence,
    package_promotion_operational_handoff,
    read_promotion_operational_handoff,
    verify_promotion_operation_record,
    verify_target_execution_intake,
    write_promotion_operation_record,
    write_promotion_operational_handoff,
    write_target_execution_intake,
)
from .semiconductor_evidence import read_semiconductor_target_evidence, write_semiconductor_target_evidence
from .semiconductor_promotion import read_promotion_candidate


def target_intake_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='nicegui-base target-intake',
        description='Import provider-neutral target execution artifacts into the existing semiconductor evidence authority without inventing PASS evidence.',
    )
    parser.add_argument('evidence', help='Existing canonical semiconductor target-evidence JSON bundle.')
    parser.add_argument('manifest', help='Provider-neutral target-execution intake manifest JSON.')
    parser.add_argument('--adapter', choices=tuple(TARGET_EXECUTION_INTAKE_ADAPTERS), default='json-manifest')
    parser.add_argument('--artifact-base-dir', type=Path, help='Base directory containing manifest-referenced execution artifacts.')
    parser.add_argument('--intake-output', type=Path, help='Persist the normalized, hash-bound execution intake.')
    parser.add_argument('--output', type=Path, help='Write the safely merged canonical target-evidence bundle.')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)

    bundle = read_semiconductor_target_evidence(args.evidence)
    intake = TARGET_EXECUTION_INTAKE_ADAPTERS[args.adapter].load(args.manifest, artifact_base_dir=args.artifact_base_dir)
    verification = verify_target_execution_intake(intake)
    if args.intake_output:
        write_target_execution_intake(args.intake_output, intake)
    merged = None
    error = None
    if not verification.blocked:
        merged = apply_target_execution_intake(bundle, intake)
        if args.output:
            write_semiconductor_target_evidence(args.output, merged)
    else:
        error = 'Blocked target execution intake was not applied to canonical evidence.'
    payload = {
        'intake': intake.to_dict(),
        'verification': verification.to_dict(),
        'merged_evidence': None if merged is None else merged.to_dict(),
        'error': error,
    }
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(f'Target execution intake: {intake.intake_id}')
        print(f'Intake status: {verification.status.value.upper()}')
        for finding in verification.findings:
            print(f'[{finding.status.value.upper():8}] {finding.code}: {finding.message}')
        if merged is not None:
            print(f'Canonical evidence promotable: {"YES" if merged.promotable else "NO"}')
            if args.output:
                print(f'Merged evidence: {args.output}')
        if error:
            print(error)
    if verification.status is TargetExecutionIntakeStatus.BLOCKED:
        return 1
    if verification.status is TargetExecutionIntakeStatus.PENDING:
        return 2
    return 0


def promotion_handoff_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='nicegui-base promotion-handoff',
        description='Bind a stable-promotion candidate to its verified package and create a provider-neutral operational handoff envelope; no deployment is performed.',
    )
    parser.add_argument('candidate', help='Wave 67 stable-promotion candidate JSON.')
    parser.add_argument('candidate_package', help='Wave 67 candidate ZIP package to verify and bind.')
    parser.add_argument('--adapter', choices=tuple(PROMOTION_OPERATIONAL_HANDOFF_ADAPTERS), default='file-package')
    parser.add_argument('--change-reference', help='Optional company change/ticket reference. It is metadata only and is never treated as approval.')
    parser.add_argument('--output', type=Path, help='Write operational handoff JSON.')
    parser.add_argument('--package', type=Path, help='Write deterministic operational handoff ZIP.')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)

    candidate = read_promotion_candidate(args.candidate)
    handoff = PROMOTION_OPERATIONAL_HANDOFF_ADAPTERS[args.adapter].prepare(
        candidate, args.candidate_package, change_reference=args.change_reference,
    )
    if args.output:
        write_promotion_operational_handoff(args.output, handoff)
    package = None
    if args.package and handoff.candidate_archive.verified:
        package = package_promotion_operational_handoff(args.package, handoff)
    payload = {'handoff': handoff.to_dict(), 'package': None if package is None else package.to_dict()}
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(f'Operational handoff: {handoff.handoff_id}')
        print(f'Candidate: {handoff.candidate.candidate_id}')
        print(f'Candidate archive: {"VERIFIED" if handoff.candidate_archive.verified else "BLOCKED"}')
        print(f'Handoff status: {handoff.status.value.upper()}')
        for action in handoff.next_actions:
            print(f'- {action}')
        if package is not None:
            print(f'Handoff package: {package.path} sha256={package.sha256}')
        print('Deployment performed: NO')
    if handoff.status is PromotionHandoffStatus.READY:
        return 0
    return 1 if handoff.status is PromotionHandoffStatus.BLOCKED else 2


def _parse_operation_evidence(value: str, *, recipe_key: str):
    parts = value.split('=', 2)
    if len(parts) != 3 or not all(part.strip() for part in parts):
        raise argparse.ArgumentTypeError('operation evidence must use STEP=EVIDENCE_KEY=PATH')
    step_key, evidence_key, path = parts
    return capture_promotion_operation_evidence(path, recipe_key=recipe_key, step_key=step_key, evidence_key=evidence_key)


def promotion_operation_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='nicegui-base promotion-operation',
        description='Capture hash-bound operational evidence against a Wave 68 handoff and canonical Wave 67 runbook. This never changes candidate or target-gate status.',
    )
    parser.add_argument('handoff', help='Operational handoff JSON.')
    parser.add_argument('recipe')
    parser.add_argument('kind', choices=('promotion', 'rollback', 'incident', 'evidence-capture'))
    parser.add_argument('--completed', action='append', default=[])
    parser.add_argument('--failed', action='append', default=[])
    parser.add_argument('--evidence', action='append', default=[], metavar='STEP=EVIDENCE_KEY=PATH')
    parser.add_argument('--note', action='append', default=[])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)

    handoff = read_promotion_operational_handoff(args.handoff)
    captured = tuple(_parse_operation_evidence(value, recipe_key=args.recipe) for value in args.evidence)
    record = build_promotion_operation_record(
        handoff, args.recipe, args.kind,
        completed_step_keys=args.completed, failed_step_keys=args.failed, evidence=captured, notes=args.note,
    )
    verification = verify_promotion_operation_record(record)
    if args.output:
        write_promotion_operation_record(args.output, record)
    payload = {'record': record.to_dict(), 'verification': verification.to_dict()}
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(f'Promotion operation record: {record.operation_id}')
        print(f'{record.recipe_key} / {record.kind.value}: {verification.status.value.upper()}')
        if record.missing_evidence:
            print('Missing evidence: ' + ', '.join(record.missing_evidence))
        for error in verification.errors:
            print(f'BLOCKED: {error}')
        print('Candidate status: unchanged')
        print('Target gate status: unchanged')
    if verification.status is PromotionOperationStatus.PASS:
        return 0
    return 1 if verification.status is PromotionOperationStatus.BLOCKED else 2


__all__ = ['promotion_handoff_main', 'promotion_operation_main', 'target_intake_main']
