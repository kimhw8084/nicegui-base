"""Wave 63 golden example: governed variant + smart onboarding + production runtime."""
from __future__ import annotations

import asyncio

from nicegui_base import (
    AdaptedSemiconductorSource,
    InMemoryDataSource,
    RecipeCustomization,
    RuntimeReadiness,
    create_semiconductor_recipe_runtime,
)

_ROWS = (
    {'id':'M1','timestamp':'2026-08-29T08:00:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':-1.0,'y':0.0,'value':10.0,'sensor':'pressure','sensor_value':1.0,'bin':'PASS','count':95.0,'yield_pct':99.1,'category':'PASS','defect_class':'none'},
    {'id':'M2','timestamp':'2026-08-29T08:01:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'B','lot':'L1','wafer':'W02','x':1.0,'y':0.0,'value':10.4,'sensor':'pressure','sensor_value':1.2,'bin':'B1','count':3.0,'yield_pct':98.7,'category':'B1','defect_class':'particle'},
)


class ApprovedProviderAdapter:
    """Example provider boundary: real projects can open SQL/REST/company sources here."""

    key = 'example-approved-provider'

    async def open(self, recipe):
        source = InMemoryDataSource('wave63-provider', _ROWS)
        return AdaptedSemiconductorSource(
            source,
            field_overrides={'measurement': 'value'},
            metadata={'provider_contract': 'example', 'recipe': recipe.key},
            owns_source=True,
        )


async def build_runtime():
    return await create_semiconductor_recipe_runtime(
        'spc-monitor',
        ApprovedProviderAdapter(),
        variant='spc-monitor-fast-response',
        customization=RecipeCustomization(initial_filters={'product': 'P1'}),
    )


async def main() -> None:
    runtime = await build_runtime()
    try:
        probe = await runtime.refresh()
        assert probe.readiness is RuntimeReadiness.READY
        records = await runtime.records(limit=1)
        print(runtime.recipe.application_name)
        print(runtime.configuration.variant_key)
        print(runtime.onboarding.to_dict()['recommended_overrides'])
        print(records.filtered_total)
    finally:
        await runtime.aclose()


if __name__ == '__main__':
    asyncio.run(main())
