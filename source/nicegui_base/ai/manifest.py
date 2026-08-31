from __future__ import annotations

import json
from importlib.resources import files


def load_ai_manifest() -> dict:
    path = files('nicegui_base.ai').joinpath('construction_manifest.json')
    return json.loads(path.read_text(encoding='utf-8'))
