from __future__ import annotations

import argparse
import json

from .engine import run_governance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Enforce NiceGUI Base v2 release/design/public-API contracts.')
    parser.add_argument('--root', default='.')
    parser.add_argument('--json', action='store_true', dest='as_json')
    args = parser.parse_args(argv)
    report = run_governance(args.root)
    if args.as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        for finding in report.findings:
            location = f'{finding.path}:{finding.line}' if finding.line else finding.path
            print(f'[{finding.severity.upper():7}] {finding.rule:<28} {location} — {finding.detail}')
        print(f'Governance: {"PASS" if report.passed else "FAIL"} · {len(report.errors)} errors · {len(report.warnings)} warnings')
    return 0 if report.passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
