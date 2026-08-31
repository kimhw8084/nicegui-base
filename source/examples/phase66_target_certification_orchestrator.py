"""Wave 66 golden flow: aggregate portable evidence without manufacturing target PASS results."""
from __future__ import annotations

import asyncio

from nicegui_base import (
    InMemoryDataSource,
    assess_semiconductor_operational_readiness,
    build_provider_qualification_pack,
    build_semiconductor_operational_runbook,
    build_semiconductor_promotion_decision,
    build_semiconductor_target_evidence_bundle,
    create_semiconductor_recipe_runtime,
)

ROWS = (
    {'id':'M1','timestamp':'2026-08-29T08:00:00','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','value':10.0},
    {'id':'M2','timestamp':'2026-08-29T08:01:00','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','value':10.4},
)


async def build_example() -> dict[str, object]:
    source = InMemoryDataSource('wave66-demo', ROWS)
    runtime = await create_semiconductor_recipe_runtime('spc-monitor', source)
    runtime.assembly.semiconductor.set('chamber', 'A')
    probe = await runtime.refresh()
    readiness = assess_semiconductor_operational_readiness(runtime, runtime_experience=runtime.experience_state(probe))
    # Deliberately no target/browser/company-provider evidence: the correct result is PENDING.
    bundle = build_semiconductor_target_evidence_bundle('spc-monitor')
    qualification = build_provider_qualification_pack((bundle,), provider=runtime.source.provider)
    decision = build_semiconductor_promotion_decision(qualification, operational_readiness={'spc-monitor': readiness})
    runbook = build_semiconductor_operational_runbook('spc-monitor')
    result = {
        'runtime_ready': readiness.ready_to_run,
        'operational_release_ready': readiness.ready_for_release,
        'target_promotable': decision.promotable,
        'promotion_status': decision.status.value,
        'qualification_id': qualification.qualification_id,
        'pending_target_gates': tuple(item.key for item in bundle.certification.pending),
        'runbook_steps': tuple(item.key for item in runbook.steps),
    }
    await runtime.aclose()
    await source.aclose()
    return result


if __name__ == '__main__':
    output = asyncio.run(build_example())
    assert output['runtime_ready'] is True
    assert output['target_promotable'] is False
    assert output['promotion_status'] == 'pending'
    print(output)
