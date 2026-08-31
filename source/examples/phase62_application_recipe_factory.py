"""Wave 62 golden example: intent -> complete semiconductor application assembly."""
from __future__ import annotations

import asyncio

from nicegui_base import InMemoryDataSource, assemble_semiconductor_application, recommend_semiconductor_recipe

_ROWS = (
    {'id':'M1','timestamp':'2026-08-29T08:00:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'A','lot':'L1','wafer':'W01','x':-1.0,'y':0.0,'value':10.0,'sensor':'pressure','sensor_value':1.0,'bin':'PASS','count':95.0,'yield_pct':99.1,'category':'PASS','defect_class':'none'},
    {'id':'M2','timestamp':'2026-08-29T08:01:00','fab':'F1','area':'ETCH','product':'P1','route':'R1','operation':'ETCH10','recipe':'RCP1','recipe_version':'1','tool':'T1','chamber':'B','lot':'L1','wafer':'W02','x':1.0,'y':0.0,'value':10.4,'sensor':'pressure','sensor_value':1.2,'bin':'B1','count':3.0,'yield_pct':98.7,'category':'B1','defect_class':'particle'},
)


async def build_for_intent(intent: str = 'is chamber B drifting?'):
    recipe = recommend_semiconductor_recipe(intent)
    source = InMemoryDataSource(f'wave62-{recipe.key}', _ROWS)
    assembly = await assemble_semiconductor_application(recipe, source, strict=False)
    return source, assembly


async def main() -> None:
    source, assembly = await build_for_intent()
    print(assembly.recipe.application_name)
    print(tuple(assembly.surfaces))
    await assembly.aclose(close_source=True)


if __name__ == '__main__':
    asyncio.run(main())
