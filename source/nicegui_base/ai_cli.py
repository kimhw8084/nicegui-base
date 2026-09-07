from __future__ import annotations

import argparse
import json
from pathlib import Path

from nicegui_base.ai.context import build_agent_context, render_agent_context
from nicegui_base.ai.preflight import run_agent_preflight
from nicegui_base.ai.scaffold import install_ai_materials
from nicegui_base.ai.project import create_application, create_pattern_application, create_recipe_application
from nicegui_base.ai.gate import run_application_gate
from nicegui_base.ai.discovery import catalog_audit, catalog_search, recommend_pattern, recommend_visualization, scaffold_plan
from nicegui_base.ai.benchmark import run_agent_benchmark


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


def create_pattern_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Create a NiceGUI Base application from a canonical registered pattern.')
    parser.add_argument('path')
    parser.add_argument('--name', required=True)
    parser.add_argument('--pattern', required=True, help='Canonical pattern key, e.g. analysis_workspace or monitoring')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    created = create_pattern_application(args.path, name=args.name, pattern=args.pattern, overwrite=args.overwrite)
    print(f'Created {created.name} at {created.root} using canonical NiceGUI Base pattern {created.pattern} ({created.template}); {len(created.written)} files written.')
    return 0


def create_recipe_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Create a NiceGUI Base application from a canonical semiconductor recipe.')
    parser.add_argument('path')
    parser.add_argument('--name', required=True)
    parser.add_argument('--recipe', required=True)
    parser.add_argument('--variant')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    created = create_recipe_application(args.path, name=args.name, recipe=args.recipe, variant=args.variant, overwrite=args.overwrite)
    variant = f', variant={created.recipe_variant}' if created.recipe_variant else ''
    print(f'Created {created.name} at {created.root} using canonical NiceGUI Base recipe {created.recipe}{variant}; {len(created.written)} files written.')
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


def catalog_search_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Search the bounded canonical NiceGUI Base catalog.')
    parser.add_argument('query', nargs='?', default='')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--intent')
    parser.add_argument('--data-shape')
    parser.add_argument('--domain')
    parser.add_argument('--related-to')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    matches = catalog_search(args.query, limit=args.limit, intent=args.intent, data_shape=args.data_shape, domain=args.domain, related_to=args.related_to)
    payload = {'query': args.query, 'count': len(matches), 'results': [item.to_dict() for item in matches]}
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for item in matches:
            print(f'{item.key}: {item.title} [{item.kind}] — {item.source_authority}')
    return 0


def recommend_pattern_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Recommend one canonical page pattern for a requirement.')
    parser.add_argument('requirement')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    recommendation = recommend_pattern(args.requirement)
    if args.format == 'json':
        print(json.dumps(recommendation.to_dict(), indent=2, sort_keys=True))
    else:
        print(f'{recommendation.pattern}: {recommendation.purpose}')
        print(f'Create: {recommendation.pattern_command}')
    return 0


def recommend_visualization_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Recommend registered analytical visualizations from intent and schema.')
    parser.add_argument('intent')
    parser.add_argument('--schema', action='append', default=[])
    parser.add_argument('--domain')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    recommendation = recommend_visualization(args.intent, schema=args.schema, domain=args.domain, limit=args.limit)
    payload = recommendation.to_dict()
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif recommendation.primary:
        print(f'{recommendation.primary.key}: {recommendation.primary.title}')
        for item in recommendation.results[1:]:
            print(f'Alternative: {item.key}: {item.title}')
    else:
        print('No registered analytical visualization matched the requirement.')
    return 0 if recommendation.primary else 1


def scaffold_plan_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Return deterministic canonical scaffold commands without writing files.')
    parser.add_argument('requirement')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    payload = scaffold_plan(args.requirement).to_dict()
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f'Pattern: {payload["pattern_command"]}')
        if payload['recipe_command']:
            print(f'Recipe: {payload["recipe_command"]}')
    return 0


def catalog_audit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Validate canonical catalog completeness and family coverage.')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    payload = catalog_audit()
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f'Catalog audit: {"PASS" if payload["passed"] else "FAIL"} · {payload["catalog"]["conforming"]}/{payload["catalog"]["total"]} contracts')
    return 0 if payload['passed'] else 1


def benchmark_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Score deterministic agent pattern, visualization and scaffold choices.')
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--no-materialize', action='store_true', help='Score discovery only; skip generated-app gate execution.')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args(argv)
    payload = run_agent_benchmark(args.manifest, materialize=not args.no_materialize)
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f'Agent benchmark: {"PASS" if payload["passed"] else "FAIL"} · {payload["scenario_count"]} scenarios')
        for item in payload['failed']:
            print(f'FAIL: {item}')
    return 0 if payload['passed'] else 1

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


__all__ = [
    'benchmark_main', 'catalog_audit_main', 'catalog_search_main', 'check_main', 'context_main',
    'create_main', 'create_pattern_main', 'create_recipe_main', 'gate_main', 'init_main',
    'recommend_pattern_main', 'recommend_visualization_main', 'recipes_main', 'scaffold_plan_main',
]
