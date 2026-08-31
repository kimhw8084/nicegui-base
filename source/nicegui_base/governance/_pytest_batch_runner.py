from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def run(root: Path, *, batches: int = 6, report: Path | None = None) -> int:
    root = root.resolve()
    test_files = sorted((root / 'tests').glob('test_*.py'))
    if not test_files:
        print('No pytest files found', file=sys.stderr)
        return 5
    batch_size = max(1, (len(test_files) + batches - 1) // batches)
    results: list[dict[str, object]] = []
    started_all = time.perf_counter()
    for index, offset in enumerate(range(0, len(test_files), batch_size), start=1):
        batch = test_files[offset:offset + batch_size]
        rel = [str(path.relative_to(root)) for path in batch]
        print(f'=== NiceGUI Base pytest batch {index} ({len(batch)} files) ===', flush=True)
        started = time.perf_counter()
        env = dict(os.environ)
        env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        completed = subprocess.run(
            [sys.executable, '-m', 'pytest', '-q', '-p', 'pytest_asyncio.plugin', *rel],
            cwd=root,
            check=False,
            env=env,
        )
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        results.append({
            'batch': index,
            'files': rel,
            'returncode': completed.returncode,
            'duration_ms': elapsed,
        })
        if completed.returncode:
            status = 'FAIL'
            break
    else:
        status = 'PASS'

    payload = {
        'status': status,
        'python': sys.version.split()[0],
        'test_files': len(test_files),
        'batches_requested': batches,
        'batches_executed': len(results),
        'duration_ms': round((time.perf_counter() - started_all) * 1000, 1),
        'results': results,
    }
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    return 0 if status == 'PASS' else int(results[-1]['returncode'])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run NiceGUI Base pytest files in fresh deterministic process batches.')
    parser.add_argument('--root', default='.')
    parser.add_argument('--batches', type=int, default=6)
    parser.add_argument('--report')
    args = parser.parse_args(argv)
    report = Path(args.report).resolve() if args.report else None
    return run(Path(args.root), batches=max(1, args.batches), report=report)


if __name__ == '__main__':
    raise SystemExit(main())
