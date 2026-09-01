from __future__ import annotations

import ast
import json
import logging
from pathlib import Path

from nicegui_base.diagnostics.debug_runtime import DiagnosticBuffer, build_diagnostic_bundle


SOURCE = Path(__file__).resolve().parents[1]


def test_diagnostic_buffer_is_bounded_and_counts_levels():
    buffer = DiagnosticBuffer(capacity=25)
    logger = logging.getLogger('nicegui_base.test.iteration21')
    for index in range(40):
        record = logger.makeRecord(logger.name, logging.ERROR if index % 3 == 0 else logging.INFO, __file__, 1, f'event-{index}', (), None)
        buffer.emit(record)
    events = buffer.snapshot(limit=100)
    assert len(events) == 25
    assert buffer.counts()['ERROR'] > 0


def test_diagnostic_bundle_declares_privacy_boundaries():
    payload = json.loads(build_diagnostic_bundle(app_name='Test App', browser={'requests': []}).decode())
    assert payload['schema'] == 'nicegui-base-diagnostic-bundle/v1'
    assert payload['privacy']['redacted'] is True
    assert payload['privacy']['http_bodies_collected'] is False
    assert payload['privacy']['cookies_collected'] is False
    assert payload['privacy']['authorization_headers_collected'] is False
    assert payload['privacy']['form_values_collected'] is False
    assert payload['privacy']['local_storage_values_collected'] is False


def test_reference_table_gallery_has_five_distinct_jobs():
    text = (SOURCE / 'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    for title in (
        '1 · Measurement population',
        '2 · Recipe / configuration editor',
        '3 · Equipment maintenance planner',
        '4 · Incident & alarm queue',
        '5 · Change / reconciliation review',
    ):
        assert title in text
    assert "environment='REF APP'" not in text


def test_visualization_gallery_contains_specialist_recipes():
    text = (SOURCE / 'nicegui_base/certification/mac_lab.py').read_text(encoding='utf-8')
    for title in (
        'Step change + PM marker', 'Confidence-band trend', 'Waterfall contribution',
        'Violin + box + points', 'ECDF', 'Q-Q probability diagnostic', 'PCA scores',
        'DOE response surface', 'Treemap loss hierarchy', 'Sankey material → tool → disposition',
        'Defect-cluster scatter',
    ):
        assert title in text


def test_theme_bootstrap_and_scoped_studio_preview_are_present():
    theme = (SOURCE / 'nicegui_base/integrations/nicegui_theme.py').read_text(encoding='utf-8')
    studio = (SOURCE / 'nicegui_base/workbench/capability_studio.py').read_text(encoding='utf-8')
    assert "localStorage.getItem('nicegui_base_theme')" in theme
    assert "data-theme=\"{value}\"" in studio
    assert 'document.documentElement.dataset.theme={value!r}' not in studio


def test_shell_contains_debugger_and_version_metadata():
    layout = (SOURCE / 'nicegui_base/integrations/nicegui_layout.py').read_text(encoding='utf-8')
    assert 'UniversalDebugger' in layout
    assert 'cui-sidebar-version' in layout
    assert 'NiceGUI Base {FRAMEWORK_VERSION}' in layout


def test_builder_exposes_edit_navigation_without_public_numeric_score():
    text = (SOURCE / 'nicegui_base/workbench/builder.py').read_text(encoding='utf-8')
    assert "Button('Edit goal'" in text
    assert "Button('Edit data'" in text
    assert "Button('Change recommendation'" in text
    assert "score {item.score}" not in text


def test_framework_css_installer_calls_always_supply_ui():
    """Runtime-call contract: every framework CSS install must receive NiceGUI ui.

    ``py_compile`` cannot catch a missing required call argument, which is why the
    original Iteration 2.1 package could pass syntax validation yet fail at startup.
    This scans every framework Python source file so the same defect is release-blocking.
    """
    offenders = []
    package_root = SOURCE / 'nicegui_base'
    for path in sorted(package_root.rglob('*.py')):
        if '__pycache__' in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
            if name == 'install_framework_css' and len(node.args) == 0:
                offenders.append(f'{path.relative_to(SOURCE)}:{node.lineno}')
    assert offenders == [], 'install_framework_css requires ui; zero-arg calls: ' + ', '.join(offenders)

