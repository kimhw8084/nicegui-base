from __future__ import annotations

import argparse
import json
from pathlib import Path

from nicegui_base.ai.context import build_agent_context, render_agent_context
from nicegui_base.ai.preflight import run_agent_preflight
from nicegui_base.ai.scaffold import install_ai_materials
from nicegui_base.ai.project import create_application
from nicegui_base.ai.gate import run_application_gate


def init_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Install NiceGUI Base coding-agent materials into an application workspace.')
    parser.add_argument('path', nargs='?', default='.')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    written = install_ai_materials(Path(args.path), overwrite=args.overwrite)
    print(f'NiceGUI Base agent materials: {len(written)} files written.')
    return 0


def context_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Build a compact task-specific NiceGUI Base coding-agent context pack.')
    parser.add_argument('task', help='Current application task or requirement')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    pack = build_agent_context(args.task)
    text = json.dumps(pack.to_dict(), indent=2, sort_keys=True) + '\n' if args.format == 'json' else render_agent_context(pack)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
        print(args.output)
    else:
        print(text, end='')
    return 0


def check_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Fail-closed NiceGUI Base coding-agent preflight.')
    parser.add_argument('path', nargs='?', default='.')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    report = run_agent_preflight(args.path)
    if args.format == 'json':
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        for issue in report.issues:
            print(issue)
        print(
            f'NiceGUI Base agent check: {"PASS" if report.passed else "FAIL"} · '
            f'framework {report.framework_version} · scaffold {report.scaffold_version or "missing"} · '
            f'{report.validation_errors} errors · {report.validation_warnings} warnings'
        )
    return 0 if report.passed else 1


def create_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Create a governed NiceGUI Base application starter.')
    parser.add_argument('path')
    parser.add_argument('--name', required=True)
    parser.add_argument('--template', choices=('dashboard','data-explorer','crud','analysis-workspace','responsive-operations','async-workflow'), default='analysis-workspace')
    parser.add_argument('--recipe', help='Semiconductor application recipe, e.g. spc-monitor or FdcToolHealth')
    parser.add_argument('--variant', help='Governed Wave 63 recipe variant, e.g. spc-monitor-fast-response')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    created = create_application(args.path, name=args.name, template=args.template, recipe=args.recipe, recipe_variant=args.variant, overwrite=args.overwrite)
    recipe_text = f', recipe={created.recipe}' if created.recipe else ''
    if created.recipe_variant: recipe_text += f', variant={created.recipe_variant}'
    print(f'Created {created.name} at {created.root} using NiceGUI Base {created.framework_version} ({created.template}{recipe_text}); {len(created.written)} files written.')
    return 0



def recipes_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='List or recommend governed semiconductor application recipes.')
    parser.add_argument('intent', nargs='?')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    from nicegui_base.semiconductor import SEMICONDUCTOR_RECIPE_REGISTRY, recommend_semiconductor_recipe, recipe_catalog_entries
    if args.intent:
        recipe = recommend_semiconductor_recipe(args.intent)
        payload = next(item for item in recipe_catalog_entries() if item['key'] == recipe.key)
        if args.format == 'json':
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f'{recipe.application_name} ({recipe.key}) — {recipe.purpose}')
            variant = payload.get('variants', ())
            variant_arg = f' --variant {variant[0]}' if variant else ''
            print(f'Create: nicegui-base create ./<app> --name "{recipe.application_name}" --recipe {recipe.key}{variant_arg}')
        return 0
    entries = recipe_catalog_entries()
    if args.format == 'json':
        print(json.dumps(entries, indent=2, sort_keys=True))
    else:
        for item in entries:
            print(f"{item['key']}: {item['application_name']} — {item['purpose']}")
    return 0

def gate_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run NiceGUI Base application acceptance gates.')
    parser.add_argument('path', nargs='?', default='.')
    parser.add_argument('--release', action='store_true', help='Require live NiceGUI/browser application certification in addition to source gates.')
    parser.add_argument('--format', choices=('text','json'), default='text')
    args = parser.parse_args(argv)
    report = run_application_gate(args.path, release=args.release)
    if args.format == 'json':
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        for check in report.checks:
            print(f'[{check.status}] {check.name}: {check.detail}')
        print(f'NiceGUI Base application gate: {"PASS" if report.passed else "FAIL"}')
    return 0 if report.passed else 1


__all__ = ['check_main', 'context_main', 'create_main', 'gate_main', 'init_main', 'recipes_main']
