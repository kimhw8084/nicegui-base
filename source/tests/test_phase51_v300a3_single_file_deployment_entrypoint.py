from __future__ import annotations

import importlib.util
import os
from pathlib import Path


def test_root_app_is_single_file_publisher_entrypoint(monkeypatch) -> None:
    package_root = Path(__file__).resolve().parents[2]
    entrypoint = package_root / 'app.py'
    assert entrypoint.is_file()

    spec = importlib.util.spec_from_file_location('nicegui_base_publisher_entrypoint', entrypoint)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(module, 'run_live_lab', lambda **kwargs: calls.append(kwargs))
    for key in ('NICEGUI_BASE_HOST', 'HOST', 'NICEGUI_BASE_PORT', 'PORT', 'NICEGUI_BASE_ROOT_PATH', 'ROOT_PATH', 'SCRIPT_NAME', 'APPLICATION_ROOT', 'MOUNT_PATH'):
        monkeypatch.delenv(key, raising=False)

    module.main()
    assert calls.pop() == {'host': '0.0.0.0', 'port': 8080, 'show': False, 'root_path': ''}

    monkeypatch.setenv('HOST', '10.0.0.8')
    monkeypatch.setenv('PORT', '9001')
    module.main()
    assert calls.pop() == {'host': '10.0.0.8', 'port': 9001, 'show': False, 'root_path': ''}

    monkeypatch.setenv('NICEGUI_BASE_HOST', '127.0.0.1')
    monkeypatch.setenv('NICEGUI_BASE_PORT', '8123')
    module.main()
    assert calls.pop() == {'host': '127.0.0.1', 'port': 8123, 'show': False, 'root_path': ''}

    monkeypatch.setenv('NICEGUI_BASE_ROOT_PATH', '/team/golden-ui/')
    module.main()
    assert calls.pop() == {'host': '127.0.0.1', 'port': 8123, 'show': False, 'root_path': '/team/golden-ui'}

    monkeypatch.setenv('NICEGUI_BASE_PORT', 'not-a-port')
    try:
        module.main()
    except SystemExit as exc:
        assert 'Invalid port' in str(exc)
    else:
        raise AssertionError('invalid deployment port must fail closed')

    source_root = str(package_root / 'source')
    assert source_root in module.sys.path
