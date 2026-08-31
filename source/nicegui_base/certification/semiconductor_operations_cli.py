from __future__ import annotations

import argparse
import json
from pathlib import Path

from .semiconductor_operations import (
    SUSTAINED_OPERATIONS_EVIDENCE_ACCEPTANCE_ADAPTERS,
    load_incident_rollback_audit_manifest,
    package_incident_rollback_audit_closure,
    read_sustained_operations_evidence_acceptance,
    verify_sustained_operations_evidence_acceptance,
    write_incident_rollback_audit_closure,
    write_sustained_operations_evidence_acceptance,
)
from .semiconductor_stability import read_stable_rollback_readiness_verification


def _emit(payload: dict, fmt: str) -> None:
    if fmt == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        status = payload.get('status', 'unknown')
        identifier = payload.get('acceptance_id') or payload.get('audit_id') or ''
        print(f'{status.upper()} {identifier}')
        for item in payload.get('findings', ()):
            print(f"- {item.get('status','').upper()} {item.get('code')}: {item.get('message')}")


def sustained_operations_accept_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base sustained-operations-accept')
    parser.add_argument('readiness')
    parser.add_argument('readiness_archive')
    parser.add_argument('manifest')
    parser.add_argument('--adapter', choices=tuple(SUSTAINED_OPERATIONS_EVIDENCE_ACCEPTANCE_ADAPTERS), default='json-manifest')
    parser.add_argument('--artifact-base-dir', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    readiness = read_stable_rollback_readiness_verification(args.readiness)
    acceptance = SUSTAINED_OPERATIONS_EVIDENCE_ACCEPTANCE_ADAPTERS[args.adapter].load(
        args.manifest, readiness, args.readiness_archive, artifact_base_dir=args.artifact_base_dir,
    )
    verification = verify_sustained_operations_evidence_acceptance(
        acceptance, readiness, args.readiness_archive, base_dir=args.artifact_base_dir,
    )
    if args.output:
        write_sustained_operations_evidence_acceptance(args.output, acceptance)
    payload = acceptance.to_dict()
    payload['status'] = verification.status.value
    payload['accepted'] = verification.accepted
    payload['findings'] = [item.to_dict() for item in verification.findings]
    _emit(payload, args.format)
    return 2 if verification.status.value == 'blocked' else 0


def incident_rollback_audit_close_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base incident-rollback-audit-close')
    parser.add_argument('readiness')
    parser.add_argument('readiness_archive')
    parser.add_argument('acceptance')
    parser.add_argument('manifest')
    parser.add_argument('--artifact-base-dir', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    readiness = read_stable_rollback_readiness_verification(args.readiness)
    acceptance = read_sustained_operations_evidence_acceptance(args.acceptance)
    closure = load_incident_rollback_audit_manifest(
        args.manifest, readiness, args.readiness_archive, acceptance, artifact_base_dir=args.artifact_base_dir,
    )
    if args.output:
        write_incident_rollback_audit_closure(args.output, closure)
    package = None
    if args.package:
        package = package_incident_rollback_audit_closure(args.package, closure, artifact_base_dir=args.artifact_base_dir)
    payload = closure.to_dict()
    if package is not None:
        payload['package'] = package.to_dict()
    _emit(payload, args.format)
    return 2 if closure.status.value == 'blocked' else 0


__all__ = ['incident_rollback_audit_close_main', 'sustained_operations_accept_main']
