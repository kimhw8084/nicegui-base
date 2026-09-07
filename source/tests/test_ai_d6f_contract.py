from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'agent_tasks' / 'manifest.json'


def test_agent_benchmark_manifest_has_ten_short_authority_cases():
    payload = json.loads(MANIFEST.read_text(encoding='utf-8'))
    scenarios = payload['scenarios']
    assert payload['schema_version'] == 1
    assert len(scenarios) >= 10
    assert len({item['id'] for item in scenarios}) == len(scenarios)
    assert all(len(item['prompt']) < 150 for item in scenarios)
    assert all(item['expected']['pattern'] and item['expected']['visualization'] for item in scenarios)
    assert all(item['schema'] for item in scenarios)


def test_agent_contract_is_concise_and_installs_the_same_discovery_workflow():
    root_contract = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
    source_contract = (ROOT / 'source' / 'AGENTS.md').read_text(encoding='utf-8')
    packaged_contract = (ROOT / 'source' / 'nicegui_base' / 'ai' / 'guides' / 'AGENTS.md').read_text(encoding='utf-8')
    assert len(root_contract) < 6000
    assert source_contract == packaged_contract
    for command in ('catalog-search', 'recommend-pattern', 'recommend-visualization', 'scaffold-plan', 'catalog-audit', 'agent-benchmark'):
        assert command in root_contract


def test_fresh_agent_scaffold_publishes_discovery_commands(tmp_path):
    from nicegui_base.ai.scaffold import install_ai_materials

    install_ai_materials(tmp_path)
    payload = json.loads((tmp_path / '.nicegui_base' / 'install_manifest.json').read_text(encoding='utf-8'))
    assert payload['catalog_search_command'].startswith('nicegui-base catalog-search')
    assert payload['pattern_recommendation_command'].startswith('nicegui-base recommend-pattern')
    assert payload['visualization_recommendation_command'].startswith('nicegui-base recommend-visualization')
    assert payload['scaffold_plan_command'].startswith('nicegui-base scaffold-plan')
    assert payload['catalog_audit_command'].startswith('nicegui-base catalog-audit')
    assert payload['agent_benchmark_command'].startswith('nicegui-base agent-benchmark')


def test_discovery_api_returns_compact_deterministic_authorities():
    from nicegui_base.ai.discovery import (
        catalog_search,
        recommend_pattern,
        recommend_visualization,
        scaffold_plan,
    )

    requirement = 'Build an SPC monitoring workspace for continuous measurements without rational subgroups.'
    pattern = recommend_pattern(requirement).to_dict()
    visual = recommend_visualization(requirement, schema=('timestamp', 'measurement', 'tool')).to_dict()
    plan = scaffold_plan(requirement).to_dict()
    assert pattern['pattern'] == 'analysis_workspace'
    assert visual['primary']['key'] == 'analytics:spc_i_mr'
    assert plan['recipe_command'].endswith('--recipe spc-monitor')
    assert len(catalog_search('SPC monitoring', limit=5)) <= 5
    assert pattern == recommend_pattern(requirement).to_dict()
    assert visual == recommend_visualization(requirement, schema=('timestamp', 'measurement', 'tool')).to_dict()


def test_agent_benchmark_scores_all_cases_and_preserves_five_acceptance_dimensions():
    from nicegui_base.ai.benchmark import run_agent_benchmark

    report = run_agent_benchmark(MANIFEST)
    assert report['passed'] is True
    assert report['scenario_count'] >= 10
    assert report['failed'] == []
    dimensions = {'canonical_reuse', 'design_tokens', 'no_duplicate_primitive', 'data_visual_contract', 'runnable_app'}
    for scenario in report['scenarios']:
        assert set(scenario['scores']) == dimensions
        assert all(scenario['scores'].values())


def test_catalog_audit_is_available_as_agent_facing_compliance_check():
    from nicegui_base.ai.discovery import catalog_audit

    report = catalog_audit()
    assert report['passed'] is True
    assert report['catalog']['total'] == report['catalog']['conforming']
    assert report['framework_catalog']['missing'] == []
    assert report['framework_catalog']['duplicates'] == []


def test_cli_exposes_machine_readable_discovery_commands():
    import subprocess
    import sys

    commands = (
        ('catalog-search', 'SPC monitoring'),
        ('recommend-pattern', 'Build a dashboard with KPIs'),
        ('recommend-visualization', 'continuous measurements without rational subgroups'),
        ('scaffold-plan', 'Build an SPC monitor'),
        ('catalog-audit',),
        ('agent-benchmark', str(MANIFEST)),
    )
    for command in commands:
        result = subprocess.run(
            [sys.executable, '-m', 'nicegui_base.cli', *command, '--format', 'json'],
            cwd=ROOT, env={'PYTHONPATH': str(ROOT / 'source')}, text=True, capture_output=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)
