from pathlib import Path

from nicegui_base.ai import ValidationSeverity, ValidatorConfig, validate_app, validate_python_file


def write(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    return p


def codes(issues):
    return {i.code for i in issues}


def test_validator_accepts_semantic_nicegui_base(tmp_path):
    write(tmp_path, 'pages/equipment.py', '''\nfrom nicegui_base import DataExplorerPage, DataTable, Icons\n\ndef build():\n    page = DataExplorerPage(title="Equipment")\n    icon = Icons.REFRESH\n    return page, icon\n''')
    report = validate_app(tmp_path)
    assert report.ok
    assert report.issues == ()


def test_validator_rejects_raw_nicegui_and_aggrid(tmp_path):
    p = write(tmp_path, 'pages/raw.py', 'from nicegui import ui\nui.aggrid({"columnDefs": []})\n')
    issues = validate_python_file(p, root=tmp_path)
    assert {'AI001','AI002'} <= codes(issues)
    assert all(i.severity is ValidationSeverity.ERROR for i in issues if i.code in {'AI001','AI002'})


def test_validator_rejects_raw_layout_and_control(tmp_path):
    p = write(tmp_path, 'pages/raw.py', 'from nicegui import ui\nui.row()\nui.button("Run")\n')
    assert {'AI001','AI004','AI005'} <= codes(validate_python_file(p, root=tmp_path))


def test_validator_warns_arbitrary_icon_and_emoji(tmp_path):
    p = write(tmp_path, 'app.py', 'from nicegui_base import Button\nButton("Run ⚙", icon="settings")\n')
    found = codes(validate_python_file(p, root=tmp_path))
    assert 'AI008' in found
    assert 'AI012' in found


def test_validator_flags_inline_style_and_classes(tmp_path):
    p = write(tmp_path, 'app.py', 'thing.style("padding: 13px; color: #ff0000").classes("mt-4 text-red")\n')
    found = codes(validate_python_file(p, root=tmp_path))
    assert 'AI006' in found
    assert 'AI007' in found
    assert 'AI011' in found


def test_validator_flags_remote_visual(tmp_path):
    p = write(tmp_path, 'app.py', 'ui.image("https://cdn.example.com/icon.svg")\n')
    assert 'AI009' in codes(validate_python_file(p, root=tmp_path))


def test_validator_flags_direct_storage(tmp_path):
    p = write(tmp_path, 'app.py', 'app.storage.user.get("theme")\n')
    assert 'AI010' in codes(validate_python_file(p, root=tmp_path))


def test_validator_warns_ui_layer_sql(tmp_path):
    p = write(tmp_path, 'pages/list.py', 'QUERY = "SELECT * FROM equipment"\n')
    assert 'AI013' in codes(validate_python_file(p, root=tmp_path))


def test_validator_escape_hatch_is_narrow(tmp_path):
    p = write(tmp_path, 'app.py', '# nicegui-base: allow-ai008\nButton("Run", icon="special")\n')
    assert 'AI008' not in codes(validate_python_file(p, root=tmp_path))


def test_validator_excludes_framework_and_build_dirs(tmp_path):
    write(tmp_path, 'nicegui_base/internal.py', 'from nicegui import ui\n')
    write(tmp_path, 'build/generated.py', 'from nicegui import ui\n')
    report = validate_app(tmp_path)
    assert report.scanned_files == 0
    assert report.ok


def test_validator_syntax_error(tmp_path):
    p = write(tmp_path, 'app.py', 'def broken(:\n')
    issues = validate_python_file(p, root=tmp_path)
    assert issues[0].code == 'AI000'
    assert issues[0].severity is ValidationSeverity.ERROR


def test_report_exit_code_for_warnings(tmp_path):
    write(tmp_path, 'app.py', 'Button("Run", icon="settings")\n')
    report = validate_app(tmp_path)
    assert report.ok
    assert report.exit_code() == 0
    assert report.exit_code(warnings_as_errors=True) == 1

def test_validator_scans_css_and_remote_html(tmp_path):
    write(tmp_path, 'assets/app.css', '.x { color: #ff0000; padding: 13px; }\n')
    write(tmp_path, 'templates/a.html', '<img src="https://cdn.example.com/x.svg">\n')
    report = validate_app(tmp_path)
    found = codes(report.issues)
    assert {'AI014','AI011','AI009'} <= found
    assert not report.ok

def test_validation_report_is_json_serializable(tmp_path):
    import json
    write(tmp_path, 'app.py', 'Button("Run", icon="settings")\n')
    report=validate_app(tmp_path)
    encoded=json.dumps(report.to_dict())
    assert 'AI008' in encoded and 'warning_count' in encoded
