from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .app_blueprints import ResolvedAppBlueprint, resolve_app_blueprint


def _app_source(app_name: str, blueprint: ResolvedAppBlueprint) -> str:
    imports: list[str] = []
    mappings: list[str] = []
    for page in blueprint.pages:
        alias = f'build_{page.module}'
        imports.append(f'from pages.{page.module} import build_page as {alias}')
        if page.route != '/':
            mappings.append(f'    {page.route!r}: {alias},')
    routes = '\n'.join(mappings)
    return '\n'.join([
        'from __future__ import annotations',
        'import os',
        'from nicegui_base import NiceGUIRuntimeAdapter, RuntimeConfig',
        *imports,
        '',
        'ROUTES = {',
        routes,
        '}',
        '',
        'def runtime() -> NiceGUIRuntimeAdapter:',
        f"    return NiceGUIRuntimeAdapter(RuntimeConfig({app_name!r}, app_version='0.1.0', host=os.getenv('NICEGUI_BASE_HOST','127.0.0.1'), port=int(os.getenv('NICEGUI_BASE_PORT','8080')), require_storage_secret=False, show_browser=False))",
        '',
        'def main() -> None:',
        '    runtime().run(root=build_home, pages=ROUTES)',
        '',
        "if __name__ == '__main__':",
        '    main()',
        '',
    ])


def _navigation(blueprint: ResolvedAppBlueprint) -> list[dict[str, str]]:
    return [
        {'id': page.key, 'label': page.title, 'route': page.route}
        for page in blueprint.pages
    ]


def _page_project(project: Mapping[str, Any], blueprint: ResolvedAppBlueprint, page) -> dict[str, Any]:
    return {
        'name': str(project.get('name') or 'My NiceGUI App'),
        'page_title': page.title if not page.primary else str(project.get('name') or page.title),
        'goal': page.purpose,
        'problem_type': str(project.get('problem_type') or ''),
        'pattern_key': page.pattern_key,
        'placements': {str(slot): list(keys) for slot, keys in page.placements.items()},
        'theme': str(project.get('theme') or 'system'),
        'density': str(project.get('density') or 'compact'),
        'navigation': _navigation(blueprint),
        'active_route': page.route,
        'blueprint_key': blueprint.key,
    }


def materialize_app_blueprint(root: Path, project: Mapping[str, Any], lookup: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[Path, ...], dict[str, str]]:
    """Write a governed multi-page application around the Workbench-composed primary page.

    The primary page keeps the user's explicit pattern/placements. Secondary pages are
    deterministically composed from existing pattern/catalog authorities; the blueprint
    owns information architecture only and never introduces a second component registry.
    """
    blueprint = resolve_app_blueprint(project, lookup.values())
    from .project_codegen import project_home_code

    written: list[Path] = []
    sources: dict[str, str] = {}
    for page in blueprint.pages:
        page_project = _page_project(project, blueprint, page)
        source = project_home_code(page_project, lookup)
        path = root / 'pages' / f'{page.module}.py'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding='utf-8')
        written.append(path)
        sources[path.relative_to(root).as_posix()] = source

    app_source = _app_source(str(project.get('name') or 'My NiceGUI App'), blueprint)
    app_path = root / 'app.py'
    app_path.write_text(app_source, encoding='utf-8')
    written.append(app_path)
    sources['app.py'] = app_source

    test_path = root / 'tests' / 'test_project_contract.py'
    existing = test_path.read_text(encoding='utf-8') if test_path.is_file() else ''
    expected_routes = tuple(page.route for page in blueprint.pages if page.route != '/')
    addition = (
        '\nfrom app import ROUTES\n\n'
        'def test_application_blueprint_routes() -> None:\n'
        f'    assert tuple(ROUTES) == {expected_routes!r}\n'
        f'    assert all(callable(handler) for handler in ROUTES.values())\n'
    )
    test_path.write_text(existing.rstrip() + '\n' + addition, encoding='utf-8')
    written.append(test_path)
    sources['tests/test_project_contract.py'] = test_path.read_text(encoding='utf-8')

    manifest = blueprint.to_dict()
    meta_path = root / '.nicegui_base' / 'app_blueprint.json'
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    written.append(meta_path)
    return manifest, tuple(dict.fromkeys(written)), sources


__all__ = ['materialize_app_blueprint']
