from __future__ import annotations

import argparse
import json
from pathlib import Path

from .semiconductor_release_audit import read_release_audit_closure
from .semiconductor_release_acceptance import (
    STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS,
    build_stable_release_promotion_closure,
    package_stable_release_promotion_closure,
    read_stable_release_evidence_acceptance,
    verify_release_audit_archive,
    verify_stable_release_evidence_acceptance,
    write_stable_release_evidence_acceptance,
    write_stable_release_promotion_closure,
)


def _emit(payload: dict, fmt: str) -> None:
    if fmt == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            print(f'{key}: {json.dumps(value, sort_keys=True, ensure_ascii=False)}')
        else:
            print(f'{key}: {value}')


def release_evidence_accept_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base release-evidence-accept')
    parser.add_argument('audit')
    parser.add_argument('audit_archive')
    parser.add_argument('manifest')
    parser.add_argument('--adapter', choices=tuple(STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS), default='json-manifest')
    parser.add_argument('--artifact-base-dir', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)
    audit = read_release_audit_closure(args.audit)
    archive_verification = verify_release_audit_archive(args.audit_archive, expected_audit=audit)
    adapter = STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS[args.adapter]
    acceptance = adapter.load(args.manifest, audit, args.audit_archive, artifact_base_dir=args.artifact_base_dir)
    verification = verify_stable_release_evidence_acceptance(
        acceptance, audit=audit, audit_archive_path=args.audit_archive, base_dir=args.artifact_base_dir,
    )
    if args.output:
        write_stable_release_evidence_acceptance(args.output, acceptance)
    _emit({'acceptance': acceptance.to_dict(), 'verification': verification.to_dict(), 'audit_archive': archive_verification.to_dict()}, args.format)
    if not archive_verification.verified or verification.blocked:
        return 1
    return 0 if verification.accepted else 2


def promotion_close_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base promotion-close')
    parser.add_argument('audit')
    parser.add_argument('audit_archive')
    parser.add_argument('acceptance')
    parser.add_argument('--artifact-base-dir', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)
    audit = read_release_audit_closure(args.audit)
    acceptance = read_stable_release_evidence_acceptance(args.acceptance)
    closure = build_stable_release_promotion_closure(
        audit, args.audit_archive, acceptance, artifact_base_dir=args.artifact_base_dir,
    )
    if args.output:
        write_stable_release_promotion_closure(args.output, closure)
    package = None
    if args.package:
        package = package_stable_release_promotion_closure(args.package, closure, artifact_base_dir=args.artifact_base_dir)
    payload = {'closure': closure.to_dict()}
    if package is not None:
        payload['package'] = package.to_dict()
    _emit(payload, args.format)
    if closure.status.value == 'closed':
        return 0
    return 1 if closure.status.value == 'blocked' else 2


__all__ = ['promotion_close_main', 'release_evidence_accept_main']
