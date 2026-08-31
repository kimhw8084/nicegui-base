from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from nicegui_base.version import FRAMEWORK_VERSION

from .mac_browser import screenshot_manifest


@dataclass(frozen=True, slots=True)
class BaselineApproval:
    framework_version: str
    approved_at_utc: str
    screenshot_count: int
    source_report_sha256: str
    screenshots: dict[str, str]
    browsers: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            'framework_version': self.framework_version,
            'approved_at_utc': self.approved_at_utc,
            'screenshot_count': self.screenshot_count,
            'source_report_sha256': self.source_report_sha256,
            'screenshots': dict(sorted(self.screenshots.items())),
            'browsers': dict(sorted(self.browsers.items())),
        }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approve_visual_baseline(output_dir: Path, baseline_dir: Path, *, force: bool = False) -> BaselineApproval:
    report_path = output_dir / 'LIVE_BROWSER_REPORT.json'
    if not report_path.exists():
        report_path = output_dir / 'MAC_BROWSER_REPORT.json'
    screenshots_dir = output_dir / 'screenshots'
    if not report_path.exists():
        raise FileNotFoundError(f'browser report not found: {report_path}')
    if not screenshots_dir.exists():
        raise FileNotFoundError(f'screenshot directory not found: {screenshots_dir}')
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if not report.get('passed'):
        raise RuntimeError('cannot approve a visual baseline from a failing browser certification run')
    failures = [item for item in report.get('results', []) if item.get('status') == 'fail']
    if failures:
        raise RuntimeError(f'cannot approve baseline with {len(failures)} failing browser result(s)')
    source_hashes = screenshot_manifest(screenshots_dir)
    if not source_hashes:
        raise RuntimeError('no screenshots were produced by browser certification')
    manifest_path = baseline_dir / 'BASELINE_MANIFEST.json'
    if manifest_path.exists() and not force:
        raise FileExistsError(f'baseline already exists at {baseline_dir}; pass --force only after intentional visual re-approval')
    baseline_dir.mkdir(parents=True, exist_ok=True)
    for old in baseline_dir.glob('*.png'):
        old.unlink()
    for name in source_hashes:
        shutil.copy2(screenshots_dir / name, baseline_dir / name)
    approval = BaselineApproval(
        framework_version=FRAMEWORK_VERSION,
        approved_at_utc=datetime.now(timezone.utc).isoformat(),
        screenshot_count=len(source_hashes),
        source_report_sha256=_sha256(report_path),
        screenshots=screenshot_manifest(baseline_dir),
        browsers={str(k): str(v) for k, v in report.get('browsers', {}).items()},
    )
    payload = approval.to_dict()
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    digest = _sha256(manifest_path)
    (baseline_dir / 'BASELINE_MANIFEST.json.sha256').write_text(f'{digest}  BASELINE_MANIFEST.json\n', encoding='utf-8')
    return approval


def verify_visual_baseline(baseline_dir: Path) -> tuple[bool, str]:
    manifest_path = baseline_dir / 'BASELINE_MANIFEST.json'
    if not manifest_path.exists():
        return False, 'approved baseline manifest is missing'
    try:
        payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    except Exception as exc:
        return False, f'baseline manifest is invalid JSON: {exc}'
    if payload.get('framework_version') != FRAMEWORK_VERSION:
        return False, f"baseline framework version {payload.get('framework_version')!r} does not match {FRAMEWORK_VERSION}"
    expected = payload.get('screenshots')
    if not isinstance(expected, dict) or not expected:
        return False, 'baseline manifest contains no screenshots'
    actual = screenshot_manifest(baseline_dir)
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        changed = sorted(name for name in set(expected) & set(actual) if expected[name] != actual[name])
        return False, f'baseline screenshot hashes differ; missing={missing[:5]}, extra={extra[:5]}, changed={changed[:5]}'
    return True, f'{len(actual)} approved baseline screenshots verified'


def main() -> int:
    p = argparse.ArgumentParser(description='Approve the current NiceGUI Base live screenshots as the visual regression baseline')
    p.add_argument('--output', type=Path, default=Path('certification_output'))
    p.add_argument('--baseline', type=Path, default=Path('visual_baseline'))
    p.add_argument('--force', action='store_true', help='Replace an existing baseline after intentional human visual approval')
    args = p.parse_args()
    try:
        approval = approve_visual_baseline(args.output, args.baseline, force=args.force)
    except Exception as exc:
        print(f'Baseline approval: FAIL — {exc}')
        return 1
    print(f'Baseline approval: PASS — {approval.screenshot_count} screenshots approved for NiceGUI Base {approval.framework_version}')
    print(f'Manifest: {args.baseline / "BASELINE_MANIFEST.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


__all__ = ['BaselineApproval', 'approve_visual_baseline', 'verify_visual_baseline']
