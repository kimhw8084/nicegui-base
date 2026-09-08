from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any

DEFAULT_SOURCE_BUILD_ID = "NGB-20260907-G2.6"


@dataclass(frozen=True, slots=True)
class PreviewAsset:
    key: str
    filename: str
    source_build_id: str

    @property
    def label(self) -> str:
        return f"Reference preview · {self.source_build_id}"


@lru_cache(maxsize=1)
def _index() -> dict[str, Any]:
    resource = files("nicegui_base.workbench").joinpath("preview_assets/index.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    if int(payload.get("schema_version", 0)) != 2:
        raise ValueError("Reference preview asset index schema is inconsistent.")
    if not isinstance(payload.get("assets"), dict):
        raise ValueError("Reference preview asset index is malformed.")
    return payload


@lru_cache(maxsize=256)
def asset_for_key(key: str) -> PreviewAsset | None:
    payload = _index()
    filename = payload["assets"].get(key)
    if not filename:
        return None
    resource = files("nicegui_base.workbench").joinpath("preview_assets", filename)
    if not resource.is_file():
        return None
    source = str(
        payload.get("sources", {}).get(key)
        or payload.get("default_source_build_id")
        or DEFAULT_SOURCE_BUILD_ID
    )
    return PreviewAsset(key=key, filename=str(filename), source_build_id=source)


@lru_cache(maxsize=256)
def data_uri(asset_key: str) -> str | None:
    asset = asset_for_key(asset_key)
    if asset is None:
        return None
    resource = files("nicegui_base.workbench").joinpath("preview_assets", asset.filename)
    encoded = base64.b64encode(resource.read_bytes()).decode("ascii")
    return "data:image/webp;base64," + encoded


def entry_asset_key(entry) -> str | None:
    kind = getattr(getattr(entry, "kind", None), "value", str(getattr(entry, "kind", "")))
    metadata = getattr(entry, "metadata", {}) or {}
    if kind == "analytic" and metadata.get("surface_key"):
        return f"analytic:{metadata['surface_key']}"
    if kind == "component" and metadata.get("component_key"):
        return f"component:{metadata['component_key']}"
    if kind == "pattern" and metadata.get("pattern_key"):
        return f"pattern:{metadata['pattern_key']}"
    if kind == "recipe" and metadata.get("recipe_key"):
        return f"recipe:{metadata['recipe_key']}"
    return None


def primary_asset_key(section: str) -> str:
    return f"primary:{section}"


def application_asset_key(key: str) -> str:
    return f"application:{key}"


__all__ = [
    "DEFAULT_SOURCE_BUILD_ID",
    "PreviewAsset",
    "application_asset_key",
    "asset_for_key",
    "data_uri",
    "entry_asset_key",
    "primary_asset_key",
]
