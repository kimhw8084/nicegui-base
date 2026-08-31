from __future__ import annotations

import argparse
import json
from pathlib import Path

from nicegui_base.ai import ValidatorConfig, validate_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Validate an application against NiceGUI Base construction laws.')
    parser.add_argument('path', nargs='?', default='.', help='Application root to scan (default: current directory)')
    parser.add_argument('--warnings-as-errors', action='store_true', help='Return non-zero when warnings are present')
    parser.add_argument('--quiet', action='store_true', help='Print summary only')
    parser.add_argument('--format', choices=('text','json'), default='text', help='Output format')
    args = parser.parse_args(argv)
    config = ValidatorConfig(warnings_as_errors=args.warnings_as_errors)
    report = validate_app(Path(args.path), config=config)
    if args.format == 'json':
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        if not args.quiet:
            for issue in report.issues:
                print(issue.format())
        print(f'NiceGUI Base validation: {report.scanned_files} files, {len(report.errors)} errors, {len(report.warnings)} warnings.')
    return report.exit_code(warnings_as_errors=args.warnings_as_errors)


if __name__ == '__main__':
    raise SystemExit(main())
