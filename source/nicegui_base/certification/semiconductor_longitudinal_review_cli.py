from __future__ import annotations

import argparse
import json
from pathlib import Path

from .semiconductor_longitudinal import read_longitudinal_operational_assurance_dossier
from .semiconductor_longitudinal_review import (
    LONGITUDINAL_ASSURANCE_REVIEW_ADAPTERS,
    build_evidence_exception_governance_dossier,
    package_evidence_exception_governance_dossier,
    read_longitudinal_assurance_review_record,
    write_evidence_exception_governance_dossier,
    write_longitudinal_assurance_review_record,
)


def _emit(payload: dict, fmt: str) -> None:
    if fmt == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def longitudinal_assurance_review_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog='nicegui-base longitudinal-assurance-review')
    p.add_argument('dossier'); p.add_argument('dossier_archive'); p.add_argument('manifest')
    p.add_argument('--adapter', default='json-manifest', choices=sorted(LONGITUDINAL_ASSURANCE_REVIEW_ADAPTERS))
    p.add_argument('--artifact-base-dir'); p.add_argument('--now'); p.add_argument('--output'); p.add_argument('--format', choices=('text','json'), default='text')
    args = p.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)
    dossier = read_longitudinal_operational_assurance_dossier(args.dossier)
    record = LONGITUDINAL_ASSURANCE_REVIEW_ADAPTERS[args.adapter].load(
        args.manifest, dossier, args.dossier_archive, artifact_base_dir=args.artifact_base_dir, now=args.now,
    )
    if args.output: write_longitudinal_assurance_review_record(args.output, record)
    _emit(record.to_dict(), args.format)
    return 2 if record.status.value == 'blocked' else (1 if record.status.value == 'pending' else 0)


def evidence_exception_governance_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog='nicegui-base evidence-exception-governance')
    p.add_argument('review'); p.add_argument('--artifact-base-dir'); p.add_argument('--now'); p.add_argument('--output'); p.add_argument('--package'); p.add_argument('--format', choices=('text','json'), default='text')
    args = p.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)
    review = read_longitudinal_assurance_review_record(args.review)
    dossier = build_evidence_exception_governance_dossier(review, artifact_base_dir=args.artifact_base_dir, now=args.now)
    package = None
    if args.output: write_evidence_exception_governance_dossier(args.output, dossier)
    if args.package:
        package = package_evidence_exception_governance_dossier(args.package, dossier, artifact_base_dir=args.artifact_base_dir, now=args.now)
    payload = dossier.to_dict()
    if package is not None: payload['package'] = package.to_dict()
    _emit(payload, args.format)
    return 2 if dossier.status.value == 'blocked' else (1 if dossier.status.value == 'pending' else 0)


__all__ = ['evidence_exception_governance_main', 'longitudinal_assurance_review_main']
