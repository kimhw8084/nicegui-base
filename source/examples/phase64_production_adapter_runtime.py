from __future__ import annotations

import asyncio
import json

from nicegui_base import (
    AdaptedSemiconductorSource, AdapterConformancePolicy, InMemoryDataSource,
    build_semiconductor_target_runtime_certification, create_semiconductor_recipe_runtime,
    run_semiconductor_adapter_conformance, serialize_recipe_runtime_preset,
)

ROWS = (
    {'id':'M1','timestamp':'2026-08-29T08:00:00','product':'P1','route':'R1','operation':'ETCH10','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','value':10.0},
    {'id':'M2','timestamp':'2026-08-29T08:01:00','product':'P1','route':'R1','operation':'ETCH10','tool':'T1','chamber':'B','lot':'L1','wafer':'W02','value':10.4},
)


class FixtureAdapter:
    key = 'wave64-example-fixture'
    async def open(self, recipe):
        return AdaptedSemiconductorSource(InMemoryDataSource('example', ROWS), metadata={'recipe':recipe.key}, owns_source=True)


async def main() -> dict:
    # Development fixtures deliberately relax production pushdown requirements.
    conformance = await run_semiconductor_adapter_conformance(
        'spc-monitor', FixtureAdapter(),
        policy=AdapterConformancePolicy(require_filter_pushdown=False, require_pagination_pushdown=False),
    )
    runtime = await create_semiconductor_recipe_runtime('spc-monitor', FixtureAdapter(), variant='spc-monitor-fast-response')
    probe = await runtime.refresh()
    setup = runtime.onboarding_view()
    experience = runtime.experience_state(probe)
    preset_json = serialize_recipe_runtime_preset(runtime.capture_preset('Example review'))
    target = build_semiconductor_target_runtime_certification('spc-monitor', adapter_conformance=conformance)
    result = {
        'conformance_passed': conformance.passed,
        'onboarding_ready': setup.ready,
        'runtime_status': experience.status.value,
        'preset_bytes': len(preset_json.encode()),
        'target_promotable': target.promotable,
        'pending_target_gates': [item.key for item in target.pending],
    }
    await runtime.aclose()
    return result


if __name__ == '__main__':
    print(json.dumps(asyncio.run(main()), indent=2, sort_keys=True))
