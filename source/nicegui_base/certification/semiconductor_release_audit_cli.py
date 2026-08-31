from __future__ import annotations

import argparse
import json
from pathlib import Path

from .semiconductor_execution import read_promotion_operation_record, read_promotion_operational_handoff
from .semiconductor_release_audit import (
    PROMOTION_EXECUTION_ADAPTER_QUALIFICATION_ADAPTERS,
    PromotionExecutionAdapterQualificationStatus,
    ReleaseAuditStatus,
    build_release_audit_closure,
    package_release_audit_closure,
    read_promotion_execution_adapter_qualification,
    verify_promotion_execution_adapter_qualification,
    write_promotion_execution_adapter_qualification,
    write_release_audit_closure,
)


def execution_adapter_qualify_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='nicegui-base execution-adapter-qualify',
        description='Import and verify artifact-backed qualification for an approved external promotion execution adapter. No deployment is performed.',
    )
    parser.add_argument('manifest')
    parser.add_argument('--adapter', choices=tuple(PROMOTION_EXECUTION_ADAPTER_QUALIFICATION_ADAPTERS), default='json-manifest')
    parser.add_argument('--artifact-base-dir', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)

    qualification = PROMOTION_EXECUTION_ADAPTER_QUALIFICATION_ADAPTERS[args.adapter].load(
        args.manifest, artifact_base_dir=args.artifact_base_dir,
    )
    verification = verify_promotion_execution_adapter_qualification(qualification)
    if args.output:
        write_promotion_execution_adapter_qualification(args.output, qualification)
    payload = {'qualification': qualification.to_dict(), 'verification': verification.to_dict()}
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(f'Execution adapter qualification: {qualification.qualification_id}')
        print(f'Adapter: {qualification.adapter_key}@{qualification.adapter_version}')
        print(f'Status: {verification.status.value.upper()}')
        for finding in verification.findings:
            print(f'[{finding.status.value.upper():9}] {finding.code}: {finding.message}')
        print('Deployment performed: NO')
    if verification.status is PromotionExecutionAdapterQualificationStatus.QUALIFIED:
        return 0
    return 1 if verification.status is PromotionExecutionAdapterQualificationStatus.BLOCKED else 2


def release_audit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='nicegui-base release-audit',
        description='Build final release-channel audit diagnostics from a verified Wave 68 handoff, qualified external execution adapter and operation evidence. Audit closure is not promotion approval.',
    )
    parser.add_argument('handoff')
    parser.add_argument('qualification')
    parser.add_argument('operations', nargs='*')
    parser.add_argument('--artifact-base-dir', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)

    handoff = read_promotion_operational_handoff(args.handoff)
    qualification = read_promotion_execution_adapter_qualification(args.qualification)
    records = tuple(read_promotion_operation_record(item) for item in args.operations)
    closure = build_release_audit_closure(
        handoff, qualification, records, artifact_base_dir=args.artifact_base_dir,
    )
    if args.output:
        write_release_audit_closure(args.output, closure)
    package = None
    if args.package and closure.status is not ReleaseAuditStatus.BLOCKED:
        package = package_release_audit_closure(args.package, closure, artifact_base_dir=args.artifact_base_dir)
    payload = {'audit': closure.to_dict(), 'package': None if package is None else package.to_dict()}
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(f'Release audit: {closure.audit_id}')
        print(f'Status: {closure.status.value.upper()}')
        print(f'Handoff: {closure.handoff.status.value.upper()}')
        print(f'Operation records: {len(closure.operation_records)}')
        for finding in closure.findings:
            print(f'[{finding.status.value.upper():7}] {finding.code}: {finding.message}')
        if package is not None:
            print(f'Audit package: {package.path} sha256={package.sha256}')
        print('Candidate status: unchanged')
        print('Target gate status: unchanged')
        print('Promotion approval inferred: NO')
    if closure.status is ReleaseAuditStatus.CLOSED:
        return 0
    return 1 if closure.status is ReleaseAuditStatus.BLOCKED else 2


__all__ = ['execution_adapter_qualify_main', 'release_audit_main']
