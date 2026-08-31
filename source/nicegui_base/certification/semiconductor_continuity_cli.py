from __future__ import annotations

import argparse
import json
from pathlib import Path

from .semiconductor_continuity import (
    SUSTAINED_OPERATIONS_EVIDENCE_RENEWAL_ADAPTERS,
    build_operational_assurance_continuity_dossier,
    package_operational_assurance_continuity_dossier,
    read_sustained_operations_evidence_renewal,
    verify_incident_rollback_audit_archive,
    verify_sustained_operations_evidence_renewal,
    write_operational_assurance_continuity_dossier,
    write_sustained_operations_evidence_renewal,
)
from .semiconductor_operations import read_incident_rollback_audit_closure


def _emit(payload: dict, fmt: str) -> None:
    if fmt == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        status = payload.get('status', 'unknown')
        identifier = payload.get('renewal_id') or payload.get('continuity_id') or ''
        print(f'{status.upper()} {identifier}')
        freshness = payload.get('freshness')
        if isinstance(freshness, dict):
            print(f"- FRESHNESS {str(freshness.get('status','unknown')).upper()}: {freshness.get('message','')}")
        for item in payload.get('findings', ()):
            print(f"- {item.get('status','').upper()} {item.get('code')}: {item.get('message')}")


def operations_evidence_renew_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base operations-evidence-renew')
    parser.add_argument('audit')
    parser.add_argument('audit_archive')
    parser.add_argument('manifest')
    parser.add_argument('--adapter', choices=tuple(SUSTAINED_OPERATIONS_EVIDENCE_RENEWAL_ADAPTERS), default='json-manifest')
    parser.add_argument('--artifact-base-dir', type=Path)
    parser.add_argument('--now')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    closure = read_incident_rollback_audit_closure(args.audit)
    renewal = SUSTAINED_OPERATIONS_EVIDENCE_RENEWAL_ADAPTERS[args.adapter].load(
        args.manifest, closure, args.audit_archive, artifact_base_dir=args.artifact_base_dir,
    )
    verification = verify_sustained_operations_evidence_renewal(
        renewal, closure, args.audit_archive, base_dir=args.artifact_base_dir, now=args.now,
    )
    archive_verification = verify_incident_rollback_audit_archive(args.audit_archive, expected_closure=closure)
    if args.output:
        write_sustained_operations_evidence_renewal(args.output, renewal)
    payload = renewal.to_dict()
    payload['status'] = verification.status.value
    payload['renewed'] = verification.renewed
    payload['freshness'] = verification.freshness.to_dict()
    payload['findings'] = [item.to_dict() for item in verification.findings]
    payload['wave73_archive_verification'] = archive_verification.to_dict()
    _emit(payload, args.format)
    return 2 if verification.status.value == 'blocked' else 0


def operational_assurance_continuity_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base operational-assurance-continuity')
    parser.add_argument('audit')
    parser.add_argument('audit_archive')
    parser.add_argument('renewal')
    parser.add_argument('--artifact-base-dir', type=Path)
    parser.add_argument('--now')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    closure = read_incident_rollback_audit_closure(args.audit)
    renewal = read_sustained_operations_evidence_renewal(args.renewal)
    dossier = build_operational_assurance_continuity_dossier(
        closure, args.audit_archive, renewal, artifact_base_dir=args.artifact_base_dir, now=args.now,
    )
    if args.output:
        write_operational_assurance_continuity_dossier(args.output, dossier)
    package = None
    if args.package:
        package = package_operational_assurance_continuity_dossier(
            args.package, dossier, artifact_base_dir=args.artifact_base_dir, now=args.now,
        )
    payload = dossier.to_dict()
    if package is not None:
        payload['package'] = package.to_dict()
    _emit(payload, args.format)
    return 2 if dossier.status.value == 'blocked' else 0


__all__ = ['operational_assurance_continuity_main', 'operations_evidence_renew_main']
