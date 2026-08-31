"""Wave 65 golden example: provider SDK -> guided setup -> bounded RC evidence."""
from __future__ import annotations

import asyncio
import json

from nicegui_base import (
    InMemoryDataSource,
    ProviderAdapterManifest,
    ProviderConformanceFixture,
    SemiconductorProviderAdapterBase,
    build_semiconductor_target_evidence_bundle,
    create_semiconductor_recipe_runtime,
    run_provider_conformance_suite,
)

_ROWS = tuple(
    {
        'id': f'M{i:03d}', 'timestamp': f'2026-08-29T08:{i % 60:02d}:00',
        'product': 'P1', 'route': 'R1', 'operation': 'ETCH10', 'tool': 'T1',
        'chamber': 'A' if i % 2 else 'B', 'lot': 'L1', 'wafer': f'W{(i % 4)+1:02d}',
        'value': 10.0 + (i % 5) * 0.1,
    }
    for i in range(20)
)


class ExampleProvider(SemiconductorProviderAdapterBase):
    manifest = ProviderAdapterManifest(
        'wave65-example-provider', 'Wave 65 Example Provider', supported_recipes=('spc-monitor',),
        description='Bounded in-memory development fixture; not production evidence.',
    )

    async def build_source(self, recipe):
        return InMemoryDataSource('wave65-example', _ROWS)

    def field_overrides(self, recipe):
        return {'measurement': 'value', 'time': 'timestamp'}


async def main() -> dict:
    adapter = ExampleProvider()
    suite = await run_provider_conformance_suite(
        adapter,
        (ProviderConformanceFixture('spc-development', 'spc-monitor', 'development'),),
    )
    runtime = await create_semiconductor_recipe_runtime('spc-monitor', adapter)
    try:
        benchmark = await runtime.benchmark(profile='development-smoke')
        workflow = await runtime.prepare_setup_workflow(
            adapter_conformance=suite.results[0].report,
            benchmark=benchmark,
        )
        review = runtime.configuration_review(
            adapter_conformance=suite.results[0].report,
            benchmark=benchmark,
        )
        evidence = build_semiconductor_target_evidence_bundle(
            'spc-monitor', adapter_conformance=suite.results[0].report, benchmark=benchmark,
            metadata={'example_scope': 'development-only'},
        )
        result = {
            'provider_suite_passed': suite.passed,
            'runtime_ready_to_run': workflow.ready_to_run,
            'runtime_release_ready': workflow.ready_for_release,
            'configuration_safe_to_run': review.safe_to_run,
            'target_promotable': evidence.promotable,
            'pending_target_gates': [gate.key for gate in evidence.certification.pending],
        }
        assert suite.passed and workflow.ready_to_run
        assert not workflow.ready_for_release and not evidence.promotable
        return result
    finally:
        await runtime.aclose()


if __name__ == '__main__':
    print(json.dumps(asyncio.run(main()), indent=2, sort_keys=True))
