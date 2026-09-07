from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_reference_explorer_navigation_has_no_builder_entry_point():
    from nicegui_base.workbench.app import workbench_navigation

    sections = workbench_navigation().sections
    items = tuple(item for section in sections for item in section.items)
    labels = tuple(item.label for item in items)
    assert labels == (
        'Start Here', 'Design System', 'Components', 'Data & Tables', 'Visualizations',
        'Layouts', 'Application Patterns', 'Semiconductor Recipes', 'Full Applications',
        'AI Development Guide', 'Diagnostics',
    )
    assert all(item.route != '/build' for item in items)
    app_source = (ROOT / 'source/nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    assert "ui.page('/components')(components_page)" in app_source
    assert "ui.page('/patterns')(patterns_page)" in app_source
    assert "ui.page('/applications')(applications_page)" in app_source
    assert "ui.page('/ai-guide')(ai_guide_page)" in app_source
    assert "queue_entry(key)" not in app_source
    assert 'render_home_project_resume' not in app_source


def test_reference_pages_demote_project_authoring_and_reframe_data_playground():
    app_source = (ROOT / 'source/nicegui_base/workbench/app.py').read_text(encoding='utf-8')
    studio_source = (ROOT / 'source/nicegui_base/workbench/capability_studio.py').read_text(encoding='utf-8')
    layout_source = (ROOT / 'source/nicegui_base/workbench/layout_studio.py').read_text(encoding='utf-8')
    assert 'reference_only=True' in app_source
    assert 'Reference example · governed sample data stays on this page' in studio_source
    assert 'Send data and configuration to Builder' not in studio_source
    assert 'Use this pattern in Builder' not in app_source
    assert 'Use in Builder' not in layout_source
    assert 'Example data playground' in studio_source
    assert 'Full Applications' in app_source


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob('*.py') if '__pycache__' not in path.parts))


def test_canonical_pattern_and_recipe_cli_scaffolds_are_deterministic_and_public(tmp_path):
    from nicegui_base.ai.project import create_pattern_application, create_recipe_application

    pattern_a = create_pattern_application(tmp_path / 'pattern-a', name='Pattern App', pattern='data_explorer')
    pattern_b = create_pattern_application(tmp_path / 'pattern-b', name='Pattern App', pattern='data_explorer')
    assert pattern_a.pattern == pattern_b.pattern == 'data_explorer'
    assert "pattern = 'data_explorer'" in (pattern_a.root / 'nicegui_base.toml').read_text(encoding='utf-8')
    assert (pattern_a.root / 'app.py').read_text(encoding='utf-8') == (pattern_b.root / 'app.py').read_text(encoding='utf-8')
    assert all('nicegui_base' in path.read_text(encoding='utf-8') or path.name not in {'app.py', 'home.py'} for path in _python_files(pattern_a.root))
    assert all('workbench' not in path.read_text(encoding='utf-8') for path in _python_files(pattern_a.root))

    recipe = create_recipe_application(tmp_path / 'recipe', name='SPC Recipe App', recipe='spc-monitor')
    assert recipe.recipe == 'spc-monitor'
    assert "recipe = 'spc-monitor'" in (recipe.root / 'nicegui_base.toml').read_text(encoding='utf-8')
    assert all(ast.parse(path.read_text(encoding='utf-8'), filename=str(path)) for path in _python_files(recipe.root))
    assert all('workbench' not in path.read_text(encoding='utf-8') for path in _python_files(recipe.root))


def test_top_level_cli_exposes_canonical_pattern_and_recipe_commands(tmp_path):
    pattern = tmp_path / 'cli-pattern'
    recipe = tmp_path / 'cli-recipe'
    env = {'PYTHONPATH': str(ROOT / 'source')}
    pattern_run = subprocess.run(
        [sys.executable, '-m', 'nicegui_base.cli', 'create-pattern', str(pattern), '--name', 'CLI Pattern', '--pattern', 'monitoring'],
        cwd=ROOT, env={**os.environ, **env}, text=True, capture_output=True, check=False,
    )
    recipe_run = subprocess.run(
        [sys.executable, '-m', 'nicegui_base.cli', 'create-recipe', str(recipe), '--name', 'CLI Recipe', '--recipe', 'spc-monitor'],
        cwd=ROOT, env={**os.environ, **env}, text=True, capture_output=True, check=False,
    )
    assert pattern_run.returncode == 0, pattern_run.stderr
    assert recipe_run.returncode == 0, recipe_run.stderr
    assert 'pattern monitoring' in pattern_run.stdout
    assert "recipe spc-monitor" in recipe_run.stdout
    assert (pattern / 'app.py').exists() and (recipe / 'app.py').exists()
