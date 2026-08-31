from __future__ import annotations

import argparse
import json
from pathlib import Path

from .semiconductor_longitudinal import (
    build_longitudinal_operational_assurance_dossier,
    build_operational_assurance_renewal_ledger,
    package_longitudinal_operational_assurance_dossier,
    read_operational_assurance_renewal_ledger,
    write_longitudinal_operational_assurance_dossier,
    write_operational_assurance_renewal_ledger,
)


def _emit(payload: dict, fmt: str) -> None:
    if fmt == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return
    identifier = payload.get('ledger_id') or payload.get('dossier_id') or ''
    print(f"{str(payload.get('status','unknown')).upper()} {identifier}")
    for item in payload.get('findings', ()):
        print(f"- {str(item.get('status','')).upper()} {item.get('code')}: {item.get('message')}")


def operational_assurance_ledger_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base operational-assurance-ledger')
    parser.add_argument('continuity_packages', nargs='+')
    parser.add_argument('--now')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    ledger = build_operational_assurance_renewal_ledger(args.continuity_packages, now=args.now)
    if args.output:
        write_operational_assurance_renewal_ledger(args.output, ledger)
    _emit(ledger.to_dict(), args.format)
    return 2 if ledger.status.value == 'blocked' else 0


def longitudinal_assurance_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base longitudinal-assurance')
    parser.add_argument('ledger')
    parser.add_argument('--now')
    parser.add_argument('--review-reference')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    ledger = read_operational_assurance_renewal_ledger(args.ledger)
    dossier = build_longitudinal_operational_assurance_dossier(ledger, now=args.now, review_reference=args.review_reference)
    if args.output:
        write_longitudinal_operational_assurance_dossier(args.output, dossier)
    package = None
    if args.package:
        package = package_longitudinal_operational_assurance_dossier(args.package, dossier, now=args.now)
    payload = dossier.to_dict()
    if package is not None:
        payload['package'] = package.to_dict()
    _emit(payload, args.format)
    return 2 if dossier.status.value == 'blocked' else 0


__all__ = ['longitudinal_assurance_main', 'operational_assurance_ledger_main']
