"""Acceptance benchmark for the agent discovery and scaffolding contract."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from nicegui_base.ai.discovery import recommend_pattern, recommend_visualization
from nicegui_base.ai.gate import run_application_gate
from nicegui_base.ai.project import create_pattern_application, create_recipe_application


_REQUIRED_SCORES = frozenset({
    'canonical_reuse', 'design_tokens', 'no_duplicate_primitive',
    'data_visual_contract', 'runnable_app',
})


def _load_manifest(path: str | Path) -> tuple[dict[str, Any], ...]:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    scenarios = payload.get('scenarios') if isinstance(payload, dict) else None
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError('benchmark manifest must contain a non-empty scenarios list')
    normalized: list[dict[str, Any]] = []
    for item in scenarios:
        if not isinstance(item, dict) or not item.get('id') or not item.get('prompt'):
            raise ValueError('every benchmark scenario requires id and prompt')
        expected = item.get('expected')
        if not isinstance(expected, dict) or not expected.get('pattern') or not expected.get('visualization'):
            raise ValueError(f"{item.get('id', '<unknown>')}: expected pattern and visualization are required")
        normalized.append(item)
    return tuple(normalized)


def _source_has_duplicate_primitive(root: Path) -> bool:
    forbidden = ('from nicegui import', 'import nicegui', 'ui.', 'ui.aggrid', 'ui.echart')
    return any(
        marker in path.read_text(encoding='utf-8')
        for path in root.rglob('*.py')
        if '__pycache__' not in path.parts
        for marker in forbidden
    )


def _materialize_and_check(item: dict[str, Any], root: Path) -> dict[str, Any]:
    expected = item['expected']
    if expected.get('recipe'):
        created = create_recipe_application(root, name='Benchmark Application', recipe=str(expected['recipe']))
    else:
        created = create_pattern_application(root, name='Benchmark Application', pattern=str(expected['pattern']))
    gate = run_application_gate(root)
    return {
        'created_files': len(created.written),
        'gate_passed': gate.passed,
        'gate_failures': [check.name for check in gate.checks if check.status != 'PASS'],
        'duplicate_primitive': _source_has_duplicate_primitive(root),
    }


def _purge_generated_modules() -> None:
    """Keep temporary benchmark workspaces isolated from later in-process tests."""
    prefixes = ('pages', 'services', 'domain', 'data')
    for name in tuple(sys.modules):
        if name == 'app' or name == 'recipe_config' or name in prefixes or name.startswith(tuple(f'{prefix}.' for prefix in prefixes)):
            sys.modules.pop(name, None)


def run_agent_benchmark(manifest: str | Path, *, materialize: bool = True) -> dict[str, Any]:
    """Score all manifest cases; materialization is enabled by default for runnable proof."""
    scenarios: list[dict[str, Any]] = []
    for item in _load_manifest(manifest):
        expected = item['expected']
        pattern = recommend_pattern(str(item['prompt']))
        visual = recommend_visualization(
            str(item['prompt']), schema=tuple(item.get('schema', ())), domain=item.get('domain'), limit=5,
        )
        primary = visual.primary
        recipe_match = expected.get('recipe') is None or pattern.recipe == expected.get('recipe')
        visual_match = primary is not None and primary.key == expected['visualization']
        pattern_match = pattern.pattern == expected['pattern']
        runtime: dict[str, Any] = {'gate_passed': False, 'duplicate_primitive': False}
        if materialize:
            try:
                with tempfile.TemporaryDirectory(prefix='nicegui-base-agent-benchmark-') as directory:
                    runtime = _materialize_and_check(item, Path(directory))
            finally:
                _purge_generated_modules()
        scores = {
            'canonical_reuse': pattern_match and recipe_match and visual_match and bool(pattern.composition_apis),
            'design_tokens': bool(runtime['gate_passed']) if materialize else bool(pattern.composition_apis),
            'no_duplicate_primitive': not runtime['duplicate_primitive'],
            'data_visual_contract': visual_match and bool(primary and primary.data_contract and primary.best_for),
            'runnable_app': bool(runtime['gate_passed']) if materialize else True,
        }
        scenarios.append({
            'id': item['id'],
            'pattern': pattern.to_dict(),
            'visualization': visual.to_dict(),
            'expected': expected,
            'scores': scores,
            'runtime': runtime,
            'passed': set(scores) == _REQUIRED_SCORES and all(scores.values()),
        })
    failed = [item['id'] for item in scenarios if not item['passed']]
    return {
        'manifest': str(Path(manifest).resolve()),
        'materialized': materialize,
        'scenario_count': len(scenarios),
        'passed': not failed,
        'failed': failed,
        'scenarios': scenarios,
    }


__all__ = ['run_agent_benchmark']
