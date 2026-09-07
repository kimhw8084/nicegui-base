#!/usr/bin/env python3
"""Build the D6H.2 visual/reference closure candidate with the governed builder."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


CANDIDATE_ID = 'NGB-20260906-D6H.2'
DEFAULT_OUTPUT = Path('/private/tmp/ngb_d6h2_rc')


def main(argv: list[str] | None = None) -> int:
    builder_path = Path(__file__).with_name('build_release_candidate_D4.py')
    spec = importlib.util.spec_from_file_location('ngb_governed_d6h2_builder', builder_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load governed release builder: {builder_path}')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.CANDIDATE_ID = CANDIDATE_ID
    builder.DEFAULT_OUTPUT = DEFAULT_OUTPUT
    builder.OWNER_MARKER = '.ngb-d6h2-owned'
    arguments = list(argv if argv is not None else sys.argv[1:])
    if '--output' not in arguments:
        arguments.extend(['--output', str(DEFAULT_OUTPUT)])
    if '--python' not in arguments:
        arguments.extend(['--python', sys.executable])
    return int(builder.main(arguments))


if __name__ == '__main__':
    raise SystemExit(main())
