from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .benchmarking import run_semiconductor_runtime_benchmark
from .provider_sdk import (
    ProviderConformanceFixture,
    load_provider_fixtures,
    load_semiconductor_adapter,
    provider_adapter_template_source,
    provider_fixture_template,
    run_provider_conformance_suite,
)
from .runtime import create_semiconductor_recipe_runtime


def _write_output(payload: dict, output: Path | None, fmt: str) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) if fmt == 'json' else _render_text(payload)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + ('\n' if not text.endswith('\n') else ''), encoding='utf-8')
    print(text)


def _render_text(payload: dict) -> str:
    if 'results' in payload:
        lines = [f"Provider {payload.get('adapter_key','?')}: {'PASS' if payload.get('passed') else 'FAIL'}"]
        for item in payload.get('results', []):
            fixture = item.get('fixture', {})
            lines.append(f"- {fixture.get('name','fixture')}: {'PASS' if item.get('passed') else 'FAIL'}")
            for guidance in item.get('guidance', []):
                if guidance.get('severity') != 'info':
                    lines.append(f"  {guidance.get('severity','?').upper()} {guidance.get('code')}: {guidance.get('remediation')}")
        for bench in payload.get('benchmarks', []):
            lines.append(f"- benchmark {bench.get('recipe_key')} / {bench.get('profile_key')}: {'PASS' if bench.get('passed') else 'FAIL'}")
        return '\n'.join(lines)
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


async def _check(args) -> int:
    adapter = load_semiconductor_adapter(args.adapter)
    if args.fixtures:
        fixtures = load_provider_fixtures(args.fixtures)
    else:
        recipes = tuple(dict.fromkeys(args.recipe or ()))
        if not recipes:
            raise ValueError('provider-check requires --recipe or --fixtures')
        fixtures = tuple(ProviderConformanceFixture(f'{key}-{args.profile}', key, args.profile) for key in recipes)
    suite = await run_provider_conformance_suite(adapter, fixtures)
    payload = suite.to_dict()
    benchmarks = []
    if args.benchmark_profile:
        recipe_keys = tuple(dict.fromkeys(item.recipe_key for item in fixtures))
        for recipe_key in recipe_keys:
            runtime = await create_semiconductor_recipe_runtime(recipe_key, adapter)
            try:
                report = await run_semiconductor_runtime_benchmark(runtime, profile=args.benchmark_profile)
                benchmarks.append(report.to_dict())
            finally:
                await runtime.aclose()
        payload['benchmarks'] = benchmarks
        payload['passed'] = bool(payload['passed'] and all(item['passed'] for item in benchmarks))
    _write_output(payload, args.output, args.format)
    return 0 if payload['passed'] else 1


def provider_check_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base provider-check')
    parser.add_argument('adapter', help='Local adapter reference in module:object syntax')
    parser.add_argument('--recipe', action='append')
    parser.add_argument('--fixtures', type=Path)
    parser.add_argument('--profile', choices=('development','production'), default='production')
    parser.add_argument('--benchmark-profile', choices=('development-smoke','provider-rc'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--format', choices=('text','json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].endswith('provider-check') else argv)
    return asyncio.run(_check(args))


def provider_init_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base provider-init')
    parser.add_argument('path', type=Path)
    parser.add_argument('--key', required=True)
    parser.add_argument('--class-name', default='CompanySemiconductorAdapter')
    parser.add_argument('--recipe', action='append')
    parser.add_argument('--profile', choices=('development','production'), default='production')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv[1:] if argv and argv[0].endswith('provider-init') else argv)
    root = args.path
    root.mkdir(parents=True, exist_ok=True)
    adapter_path = root / 'data_adapter.py'
    fixture_path = root / 'provider_fixtures.json'
    for path in (adapter_path, fixture_path):
        if path.exists() and not args.overwrite:
            raise FileExistsError(path)
    adapter_path.write_text(provider_adapter_template_source(key=args.key, class_name=args.class_name), encoding='utf-8')
    fixture_path.write_text(json.dumps(provider_fixture_template(recipes=tuple(dict.fromkeys(args.recipe or ['spc-monitor'])), profile_key=args.profile), indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'adapter': str(adapter_path), 'fixtures': str(fixture_path), 'key': args.key}, indent=2))
    return 0


__all__ = ['provider_check_main','provider_init_main']
