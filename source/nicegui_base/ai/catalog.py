from __future__ import annotations

import json
from importlib.resources import files


def load_framework_catalog() -> dict:
    path = files('nicegui_base.ai').joinpath('framework_catalog.json')
    return json.loads(path.read_text(encoding='utf-8'))
