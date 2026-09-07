#!/usr/bin/env python3
"""Outcome-based verifier and finalizer for the installed D4 candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'source'
CANDIDATE_ID = 'NGB-20260905-D4'
OWNER_MARKER = '.ngb-d4-owned'
BUNDLE_RUNTIME_EXCLUDES = ('.venv', '.nicegui')


def _env() -> dict[str, str]:
    env = dict(os.environ)
    for key in tuple(env):
        if key in {'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'VIRTUAL_ENV'} or key.startswith(('NICEGUI_', 'COMPANY_UI_')):
            env.pop(key, None)
    env.update(PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    return env


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + '\n', encoding='utf-8')


def _run(command: list[str | Path], *, cwd: Path, log: Path, input_text: str | None = None, timeout: int = 900) -> None:
    result = subprocess.run([str(item) for item in command], cwd=cwd, env=_env(), input=input_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=timeout)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'command failed ({result.returncode}); see {log}')


def _extract(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    root = target.resolve()
    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            relative = Path(info.filename)
            if relative.is_absolute() or '..' in relative.parts:
                raise RuntimeError(f'unsafe generated archive entry: {info.filename}')
            destination = (target / relative).resolve()
            destination.relative_to(root)
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read(info.filename))


def _generate_exports(qual_python: Path, evidence: Path) -> dict:
    root = evidence / 'exports'
    if root.exists():
        if not (root / OWNER_MARKER).is_file():
            raise RuntimeError(f'refusing to replace unowned export evidence: {root}')
        shutil.rmtree(root)
    root.mkdir(parents=True)
    (root / OWNER_MARKER).write_text(CANDIDATE_ID + '\n', encoding='utf-8')
    script = '''
import sys
from pathlib import Path
from nicegui_base.workbench.catalog_runtime import entries_by_key
from nicegui_base.workbench.codegen import CapabilityConfiguration, generate_application_zip
from nicegui_base.workbench.project_codegen import generate_project_zip

out = Path(sys.argv[1])
rows = [
    {'id': '0000', 'thickness': .125, 'batch': 'A', 'note': 'alpha'},
    {'id': '0001', 'thickness': 1.125, 'batch': 'B', 'note': 'alpha'},
    {'id': '0002', 'thickness': 2.125, 'batch': 'A', 'note': 'beta'},
    {'id': '0003', 'thickness': 3.125, 'batch': 'B', 'note': 'gamma'},
]
schema = [
    {'name': 'id', 'inferred_type': 'string', 'role': 'identifier', 'nullable': False, 'confidence': 1.0},
    {'name': 'thickness', 'inferred_type': 'float', 'role': 'measurement', 'nullable': False, 'confidence': 1.0},
    {'name': 'batch', 'inferred_type': 'category', 'role': 'dimension', 'nullable': False, 'confidence': 1.0},
    {'name': 'note', 'inferred_type': 'string', 'role': 'attribute', 'nullable': False, 'confidence': 1.0},
]
keys = entries_by_key()
line = keys['framework:visualizations:LineChart']
studio = generate_application_zip(line, app_name='D4 Studio Chart', config=CapabilityConfiguration(title='D4 Studio Chart', options={'measurement': 'thickness', 'label_field': 'id'}), rows=rows, data_schema=schema, data_mode='include_development_rows')
(out / 'studio.zip').write_bytes(studio)
builder, smoke = generate_project_zip({
    'name': 'D4 Builder Chart', 'goal': 'inspect thickness by batch', 'problem_type': 'engineering analysis',
    'pattern_key': 'dashboard', 'placements': {
        'filters': ['component:search_input', 'component:select'],
        'primary': ['framework:visualizations:LineChart'], 'data': ['framework:tables:data_table'],
    }, 'data_rows': rows, 'data_schema': schema, 'data_source_name': 'D4 synthetic fixture',
    'data_handoff_mode': 'include_development_rows', 'capability_configurations': {
        'framework:visualizations:LineChart': {'title': 'D4 Builder Chart', 'options': {'measurement': 'thickness', 'label_field': 'id'}},
        'component:select': {'options': {'filter_field': 'batch'}},
    },
}, keys)
if not smoke.ok:
    raise SystemExit('builder source smoke failed: ' + repr(smoke.findings))
(out / 'builder.zip').write_bytes(builder)
'''
    generator = evidence / 'generate_exports.py'
    generator.write_text(script, encoding='utf-8')
    _run([qual_python, '-I', generator, root], cwd=evidence, log=evidence / 'generate_exports.log')
    result: dict[str, Any] = {}
    for kind in ('studio', 'builder'):
        archive = root / f'{kind}.zip'
        extracted = root / kind
        _extract(archive, extracted)
        with zipfile.ZipFile(archive) as source:
            required = {'app.py', 'bootstrap.py', 'services/app_data.py', '.nicegui_base/runtime_bundle.json'}
            missing = sorted(required - set(source.namelist()))
            if missing:
                raise RuntimeError(f'{kind} export missing {missing}')
        _run([qual_python, 'bootstrap.py', '--setup', '--check', '--output', extracted / 'bootstrap_proof.json'], cwd=extracted, log=root / f'{kind}_bootstrap.log', timeout=1200)
        proof = json.loads((extracted / 'bootstrap_proof.json').read_text(encoding='utf-8'))
        if not proof.get('passed') or int(proof.get('verified_files', 0)) != 551:
            raise RuntimeError(f'{kind} bundled provenance failed: {proof}')
        result[kind] = {'archive': str(archive), 'sha256': _sha(archive), 'bootstrap': proof}
    summary = {'candidate_id': CANDIDATE_ID, 'status': 'PASS', 'fixture': {'rows': 4, 'measurement': 'thickness', 'identifier': 'id', 'category': 'batch'}, 'exports': result}
    _write_json(evidence / 'GENERATED_EXPORTS_SUMMARY.json', summary)
    return summary


def _static_checks(bundle: Path, archive: Path) -> dict:
    sys.path.insert(0, str(REPO / 'tools'))
    sys.path.insert(0, str(SOURCE))
    from build_release_candidate_D4 import sha256_bytes, source_manifest, verify_wheel_sources
    from nicegui_base.governance.release_artifacts import verify_release_archive, verify_sha256_manifest, verify_wheel

    wheels = sorted((bundle / 'wheel').glob('nicegui_base-*.whl'))
    if len(wheels) != 1:
        raise RuntimeError(f'expected one RC wheel, found {wheels}')
    wheel = wheels[0]
    wheel_report = verify_wheel(wheel)
    if not wheel_report.passed:
        raise RuntimeError(f'candidate wheel RECORD failed: {wheel_report}')
    source_report = verify_wheel_sources(SOURCE, wheel)
    if not source_report['passed']:
        raise RuntimeError(f'candidate wheel/source mismatch: {source_report}')
    source_authority = json.loads((bundle / 'SOURCE_PACKAGE_SHA256.json').read_text(encoding='utf-8'))
    current = source_manifest(SOURCE)
    current_hash = sha256_bytes(json.dumps(current, sort_keys=True).encode())
    if source_authority.get('files') != current or source_authority.get('source_state_sha256') != current_hash:
        raise RuntimeError('source package changed after candidate build')
    manifest = verify_sha256_manifest(bundle, exclude=BUNDLE_RUNTIME_EXCLUDES)
    if not manifest.passed:
        raise RuntimeError(f'bundle SHA256 manifest failed: {manifest}')
    archive_report = verify_release_archive(archive, source_manifest_name='missing-source-manifest')
    if not archive_report.passed:
        raise RuntimeError(f'candidate archive verification failed: {archive_report}')
    provenance = json.loads((bundle / 'BUILD_PROVENANCE.json').read_text(encoding='utf-8'))
    if provenance.get('candidate_id') != CANDIDATE_ID or provenance.get('wheel', {}).get('sha256') != _sha(wheel):
        raise RuntimeError('build provenance does not identify this wheel')
    return {'status': 'PASS', 'wheel_sha256': _sha(wheel), 'wheel_record_rows': wheel_report.record_rows, 'packaged_source_files': source_report['packaged_source_files'], 'source_state_sha256': current_hash, 'bundle_files': manifest.expected, 'archive_sha256': _sha(archive), 'archive_files': archive_report.file_count}


def _browser_checks(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if payload.get('candidate_id') != CANDIDATE_ID or payload.get('status') != 'PASS':
        raise RuntimeError(f'browser evidence is not a D4 PASS: {path}')
    if set(payload.get('viewports', ())) != {'desktop', 'tablet', 'phone'} or set(payload.get('themes', ())) != {'light', 'dark'}:
        raise RuntimeError('browser evidence lacks the required viewport/theme matrix')
    if payload.get('page_errors') or payload.get('console_errors') or payload.get('overflow'):
        raise RuntimeError('browser evidence contains page, console, or overflow failures')
    required = {'overview', 'catalog', 'studio', 'data', 'builder', 'settings', 'generated_studio', 'generated_builder'}
    missing = sorted(required - set(payload.get('surfaces', ())))
    if missing:
        raise RuntimeError(f'browser evidence missing surfaces: {missing}')
    screenshots = [Path(item) for item in payload.get('screenshots', ())]
    if not screenshots or not all(item.is_file() for item in screenshots):
        raise RuntimeError('browser evidence does not reference a complete screenshot set')
    return payload


def _finalize(bundle: Path, output: Path, evidence: Path, static: dict, generated: dict, browser: dict | None) -> dict:
    sys.path.insert(0, str(SOURCE))
    from nicegui_base.governance.release_artifacts import build_deterministic_zip, verify_sha256_manifest, write_sha256_manifest
    browser_result = browser or {'candidate_id': CANDIDATE_ID, 'status': 'NOT_RUN'}
    _write_json(bundle / 'GENERATED_EXPORTS_SUMMARY.json', generated)
    _write_json(bundle / 'BROWSER_ACCEPTANCE_SUMMARY.json', browser_result)
    (bundle / 'CERTIFICATION_SUMMARY.md').write_text(
        f'# {CANDIDATE_ID} certification\n\n'
        f'- Source → wheel → bundle provenance: PASS ({static["packaged_source_files"]} packaged source/assets; source state `{static["source_state_sha256"]}`).\n'
        f'- Installed qualification and independent Studio/Builder bootstrap: {generated["status"]}.\n'
        f'- Browser/visual RC matrix: {browser_result["status"]}.\n\n'
        f'Screenshots and logs are kept at `{evidence}`. This is a near-production RC, not a stable-publication claim.\n', encoding='utf-8')
    write_sha256_manifest(bundle, exclude=BUNDLE_RUNTIME_EXCLUDES)
    check = verify_sha256_manifest(bundle, exclude=BUNDLE_RUNTIME_EXCLUDES)
    if not check.passed:
        raise RuntimeError(f'final bundle manifest failed: {check}')
    archive = build_deterministic_zip(bundle, output / f'{CANDIDATE_ID}_RC.zip', exclude=BUNDLE_RUNTIME_EXCLUDES)
    result = {'candidate_id': CANDIDATE_ID, 'status': 'PASS' if browser else 'NOT_RUN', 'bundle_directory': str(bundle), 'archive': str(archive), 'archive_sha256': _sha(archive), 'wheel_sha256': static['wheel_sha256'], 'static': static, 'generated_exports': generated, 'browser': browser_result, 'evidence': str(evidence)}
    _write_json(output / 'D4_FINAL_RESULT.json', result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=Path('/private/tmp/ngb_d4_rc/bundle'))
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--evidence', type=Path, default=Path('/private/tmp/ngb_d4_rc_evidence'))
    parser.add_argument('--browser-evidence', type=Path)
    args = parser.parse_args(argv)
    bundle = args.bundle.resolve()
    output = bundle.parent
    archive = (args.archive or output / f'{CANDIDATE_ID}_RC.zip').resolve()
    evidence = args.evidence.resolve()
    qual_python = output.parent / f'{output.name}_qualification/venv/bin/python'
    if not qual_python.is_file():
        raise SystemExit(f'qualification interpreter missing: {qual_python}; run the D4 builder first')
    evidence.mkdir(parents=True, exist_ok=True)
    static = _static_checks(bundle, archive)
    generated = _generate_exports(qual_python, evidence)
    browser = _browser_checks(args.browser_evidence.resolve()) if args.browser_evidence else None
    result = _finalize(bundle, output, evidence, static, generated, browser)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
