from pathlib import Path
import json

ROOT = Path(__file__).parents[1]


def test_required_ai_docs_exist_and_are_nontrivial():
    files = [
        'AGENTS.md','docs/AI_RULES.md','docs/COMPONENT_CATALOG.md','docs/LAYOUT_RULES.md',
        'docs/APP_PATTERNS.md','docs/RECIPES.md','docs/ANTI_PATTERNS.md','docs/ICON_CATALOG.md',
        'docs/VISUAL_RESOURCE_GUIDE.md','docs/COMPANY_ENVIRONMENT.md','docs/TROUBLESHOOTING.md',
    ]
    for rel in files:
        p = ROOT / rel
        assert p.exists(), rel
        assert len(p.read_text(encoding='utf-8')) > 300, rel


def test_construction_manifest_is_machine_readable():
    p = ROOT/'nicegui_base/ai/construction_manifest.json'
    data = json.loads(p.read_text())
    assert data['schema_version'] == 6
    assert len(data['construction_order']) >= 8
    assert len(data['escape_hatch']['required_actions']) >= 4


def test_agents_requires_validation_and_no_invention():
    text = (ROOT/'AGENTS.md').read_text()
    assert 'python -m nicegui_base.validate' in text
    assert 'Do not import `nicegui.ui` directly' in text
    assert 'Page pattern → semantic layout → framework component' in text


def test_machine_readable_root_copies_and_public_api_index():
    for rel in ('AI_CONSTRUCTION_MANIFEST.json','FRAMEWORK_CATALOG.json'):
        data=json.loads((ROOT/rel).read_text())
        assert data
    api=(ROOT/'docs/PUBLIC_API_INDEX.md').read_text()
    assert '`DataTable`' in api and '`NiceGUIRuntimeAdapter`' in api and len(api.splitlines()) > 300
    rules=(ROOT/'docs/VALIDATOR_RULES.md').read_text()
    assert 'AI001' in rules and 'AI014' in rules
    quick=(ROOT/'docs/AI_QUICKSTART.md').read_text()
    assert 'NiceGUIRuntimeAdapter' in quick and 'FRAMEWORK_CATALOG.json' in quick
