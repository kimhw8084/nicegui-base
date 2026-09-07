from __future__ import annotations

import json
import subprocess
import sys
import warnings
from pathlib import Path

import nicegui_base
from nicegui_base.runtime.config import RuntimeConfig
from nicegui_base.version import FRAMEWORK_DISPLAY_NAME, FRAMEWORK_NAME


def test_primary_identity_is_nicegui_base() -> None:
    assert FRAMEWORK_NAME == "nicegui-base"
    assert FRAMEWORK_DISPLAY_NAME == "NiceGUI Base"
    authority = json.loads((Path("nicegui_base") / "release_authority.json").read_text(encoding="utf-8"))
    assert authority["framework_name"] == "nicegui-base"
    assert authority["python_package"] == "nicegui_base"
    assert authority["primary_cli"] == "nicegui-base"


def test_legacy_root_import_is_deprecated_alias() -> None:
    sys.modules.pop("company_ui", None)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        import company_ui  # noqa: F401
    assert any(issubclass(item.category, DeprecationWarning) for item in captured)
    import company_ui
    assert company_ui.RuntimeConfig is nicegui_base.RuntimeConfig
    assert company_ui.SemiconductorRecipeRuntime is nicegui_base.SemiconductorRecipeRuntime


def test_legacy_environment_prefix_is_fallback_only() -> None:
    cfg = RuntimeConfig.from_env(
        "demo",
        environ={
            "COMPANY_UI_HOST": "127.0.0.7",
            "COMPANY_UI_PORT": "8123",
            "NICEGUI_BASE_HOST": "127.0.0.8",
        },
    )
    assert cfg.host == "127.0.0.8"
    assert cfg.port == 8123


def test_generated_application_uses_only_new_identity(tmp_path: Path) -> None:
    from nicegui_base.ai.project import create_application

    created = create_application(tmp_path / "demo", name="Demo", overwrite=True)
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in created.root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".md", ".json", ".toml", ".txt"}
    )
    assert "nicegui_base" in text
    assert "nicegui-base" in text
    assert "company_ui" not in text
    assert "company-ui" not in text
    assert "COMPANY_UI_" not in text


def test_project_metadata_has_new_primary_and_deprecated_aliases() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "nicegui-base"' in text
    assert 'nicegui-base = "nicegui_base.cli:main"' in text
    assert 'company-ui = "nicegui_base.cli:main"' in text
    assert 'include = ["nicegui_base*", "company_ui"]' in text


def test_current_active_framework_tree_has_no_unapproved_old_brand_refs() -> None:
    allowed = {
        Path("nicegui_base/runtime/config.py"),
        Path("nicegui_base/release_authority.json"),
        Path("nicegui_base/identity_migration.json"),
        # These references are deliberate migration/compatibility guardrails,
        # not generated-application branding.
        Path("nicegui_base/design/hardening_css.py"),
        Path("nicegui_base/workbench/runtime_bundle.py"),
        Path("nicegui_base/workbench/generated_smoke.py"),
        Path("nicegui_base/workbench/codegen.py"),
    }
    offenders: list[str] = []
    for root in (Path("nicegui_base"), Path("examples"), Path("showcase"), Path("linux_bundle"), Path("mac_bundle")):
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix in {".png", ".jpg", ".jpeg", ".whl", ".pyc"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if any(token in text for token in ("company_ui", "company-ui", "Company UI", "COMPANY_UI_")) and path not in allowed:
                offenders.append(str(path))
    assert offenders == []
