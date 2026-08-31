import json
from pathlib import Path
from nicegui_base.visual import VISUAL_ROOT

def test_manifests_are_versioned_and_project_authored():
    data=json.loads((VISUAL_ROOT/'manifest/icons.json').read_text())
    assert data['version']=='0.8.0'
    assert all(x['source']=='nicegui-base-project-authored' for x in data['icons'])

def test_license_manifest_records_no_lucide_runtime_files():
    data=json.loads((VISUAL_ROOT/'manifest/licenses.json').read_text())
    ref=next(x for x in data['references'] if x['name']=='Lucide')
    assert 'no Lucide runtime files' in ref['purpose']
