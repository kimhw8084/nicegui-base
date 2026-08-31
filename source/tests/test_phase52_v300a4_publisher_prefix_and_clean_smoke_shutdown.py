from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from nicegui_base.certification.live_lab import ROUTES
from nicegui_base.certification.runtime_smoke import _stop_process


APPROVED_ROUTES = (
    '/', '/foundation', '/shell', '/controls', '/forms', '/data', '/charts', '/content',
    '/engineering', '/states', '/performance', '/patterns/dashboard',
    '/patterns/explorer', '/patterns/master-detail', '/patterns/crud', '/patterns/monitoring',
    '/patterns/search', '/patterns/settings', '/patterns/wizard', '/patterns/comparison',
    '/patterns/analysis',
)


def test_live_lab_has_only_the_golden_template_route_authority() -> None:
    assert tuple(route.path for route in ROUTES) == APPROVED_ROUTES


def test_smoke_shutdown_is_graceful_and_never_synthesizes_keyboard_interrupt() -> None:
    process = Mock()
    process.poll.side_effect = [None, 0]
    process.returncode = None
    assert _stop_process(process) == 0
    process.terminate.assert_called_once_with()
    process.wait.assert_called_once_with(timeout=8)
    process.send_signal.assert_not_called()
    process.kill.assert_not_called()


def test_smoke_shutdown_escalates_to_kill_only_if_graceful_stop_fails() -> None:
    process = Mock()
    process.poll.side_effect = [None, -9]
    process.returncode = None
    process.terminate.side_effect = RuntimeError('graceful shutdown unavailable')
    assert _stop_process(process) == -9
    process.kill.assert_called_once_with()
    process.wait.assert_called_once_with(timeout=3)
    process.send_signal.assert_not_called()


def test_single_file_entrypoint_exposes_publisher_mount_path_contract() -> None:
    package_root = Path(__file__).resolve().parents[2]
    source = (package_root / 'app.py').read_text(encoding='utf-8')
    assert 'NICEGUI_BASE_ROOT_PATH' in source
    assert 'ROOT_PATH' in source
    assert 'SCRIPT_NAME' in source
    assert 'root_path=_root_path()' in source
