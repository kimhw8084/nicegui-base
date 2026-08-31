from pathlib import Path
from nicegui_base.ai import GUIDE_NAMES, install_ai_materials, read_ai_guide


def test_guides_are_packaged_and_readable():
    assert len(GUIDE_NAMES) >= 10
    assert 'Framework first' in read_ai_guide('AI_RULES.md') or 'framework' in read_ai_guide('AI_RULES.md').lower()
    assert 'NiceGUI Base' in read_ai_guide('AGENTS.md')


def test_install_ai_materials_creates_agent_workspace(tmp_path):
    written=install_ai_materials(tmp_path)
    assert (tmp_path/'AGENTS.md').exists()
    assert (tmp_path/'docs/nicegui_base/COMPONENT_CATALOG.md').exists()
    assert (tmp_path/'.nicegui_base/framework_catalog.json').exists()
    assert len(written) >= len(GUIDE_NAMES)+3
    # default is non-destructive
    original=(tmp_path/'AGENTS.md').read_text()
    assert install_ai_materials(tmp_path) == ()
    assert (tmp_path/'AGENTS.md').read_text() == original
