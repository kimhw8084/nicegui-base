import json
import subprocess
import sys
from pathlib import Path


def test_validator_cli_json_output(tmp_path):
    (tmp_path/'app.py').write_text('from nicegui import ui\nui.button("Run")\n')
    result=subprocess.run([sys.executable,'-m','nicegui_base.validate',str(tmp_path),'--format','json'],capture_output=True,text=True)
    assert result.returncode == 1
    data=json.loads(result.stdout)
    assert data['error_count'] >= 2
    assert any(i['code']=='AI001' for i in data['issues'])
