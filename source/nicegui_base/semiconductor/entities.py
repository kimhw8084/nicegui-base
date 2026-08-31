from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from enum import Enum
from typing import Any, Mapping


def _req(value: str, label: str) -> str:
    value = str(value).strip()
    if not value:
        raise ValueError(f'{label} is required')
    return value


class SemiconductorEntityKind(str, Enum):
    FAB='fab'; AREA='area'; BAY='bay'; TOOL='tool'; CHAMBER='chamber'; MODULE='module'
    TECHNOLOGY='technology'; PRODUCT='product'; ROUTE='route'; OPERATION='operation'; RECIPE='recipe'; RECIPE_VERSION='recipe_version'
    LOT='lot'; CARRIER='carrier'; WAFER='wafer'; DIE='die'
    MEASUREMENT='measurement'; METROLOGY_PARAMETER='metrology_parameter'; INSPECTION='inspection'; DEFECT='defect'; YIELD_BIN='yield_bin'
    SPC_PARAMETER='spc_parameter'; SPC_VIOLATION='spc_violation'; SENSOR='sensor'; FDC_TRACE='fdc_trace'; FDC_FEATURE='fdc_feature'
    ALARM='alarm'; EQUIPMENT_EVENT='equipment_event'; PM='pm'; MAINTENANCE='maintenance'; CALIBRATION='calibration'; ENGINEERING_CHANGE='engineering_change'
    EXCURSION='excursion'; INVESTIGATION='investigation'; HYPOTHESIS='hypothesis'; EVIDENCE='evidence'; CORRECTIVE_ACTION='corrective_action'


@dataclass(frozen=True, slots=True)
class EntityRef:
    kind: SemiconductorEntityKind
    identifier: str
    label: str | None = None
    def __post_init__(self): object.__setattr__(self, 'identifier', _req(self.identifier, 'identifier'))


@dataclass(frozen=True, slots=True)
class SemiconductorEntity:
    identifier: str
    name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        object.__setattr__(self, 'identifier', _req(self.identifier, 'identifier'))
        object.__setattr__(self, 'metadata', dict(self.metadata))
        for relation in _REQUIRED_RELATIONS.get(type(self), ()):
            _req(getattr(self, relation), relation)
        for value_field in _REQUIRED_VALUE_FIELDS.get(type(self), ()):
            _req(getattr(self, value_field), value_field)
        for numeric_field in _FINITE_VALUE_FIELDS.get(type(self), ()):
            value=getattr(self,numeric_field)
            if value is None: continue
            try: numeric=float(value)
            except (TypeError,ValueError) as exc: raise ValueError(f'{numeric_field} must be numeric') from exc
            if not isfinite(numeric): raise ValueError(f'{numeric_field} must be finite')
        if type(self) is SPCParameter and self.lsl is not None and self.usl is not None and float(self.lsl)>=float(self.usl):
            raise ValueError('SPCParameter lsl must be less than usl')


@dataclass(frozen=True, slots=True)
class Fab(SemiconductorEntity): pass
@dataclass(frozen=True, slots=True)
class Area(SemiconductorEntity): fab_id: str = ''
@dataclass(frozen=True, slots=True)
class Bay(SemiconductorEntity): area_id: str = ''
@dataclass(frozen=True, slots=True)
class Tool(SemiconductorEntity): area_id: str = ''; bay_id: str | None = None
@dataclass(frozen=True, slots=True)
class Module(SemiconductorEntity): tool_id: str = ''
@dataclass(frozen=True, slots=True)
class Chamber(SemiconductorEntity): tool_id: str = ''; module_id: str | None = None
@dataclass(frozen=True, slots=True)
class Technology(SemiconductorEntity): node: str | None = None
@dataclass(frozen=True, slots=True)
class Product(SemiconductorEntity): technology_id: str | None = None
@dataclass(frozen=True, slots=True)
class Route(SemiconductorEntity): product_id: str | None = None; technology_id: str | None = None
@dataclass(frozen=True, slots=True)
class Operation(SemiconductorEntity): route_id: str = ''; sequence: int | None = None
@dataclass(frozen=True, slots=True)
class Recipe(SemiconductorEntity): operation_id: str | None = None; tool_family: str | None = None
@dataclass(frozen=True, slots=True)
class RecipeVersion(SemiconductorEntity): recipe_id: str = ''; version: str = ''
@dataclass(frozen=True, slots=True)
class Carrier(SemiconductorEntity): carrier_type: str | None = None
@dataclass(frozen=True, slots=True)
class Lot(SemiconductorEntity): product_id: str | None = None; route_id: str | None = None; carrier_id: str | None = None
@dataclass(frozen=True, slots=True)
class Wafer(SemiconductorEntity): lot_id: str = ''; slot: int | None = None
@dataclass(frozen=True, slots=True)
class Die(SemiconductorEntity): wafer_id: str = ''; die_x: int = 0; die_y: int = 0
@dataclass(frozen=True, slots=True)
class MetrologyParameter(SemiconductorEntity): unit: str | None = None
@dataclass(frozen=True, slots=True)
class Measurement(SemiconductorEntity):
    parameter_id: str = ''; value: float | None = None; timestamp: datetime | None = None
    lot_id: str | None = None; wafer_id: str | None = None; die_id: str | None = None; operation_id: str | None = None
    tool_id: str | None = None; chamber_id: str | None = None; recipe_version_id: str | None = None
@dataclass(frozen=True, slots=True)
class Inspection(SemiconductorEntity): wafer_id: str | None = None; operation_id: str | None = None; tool_id: str | None = None
@dataclass(frozen=True, slots=True)
class Defect(SemiconductorEntity): inspection_id: str | None = None; wafer_id: str | None = None; die_id: str | None = None; defect_class: str | None = None
@dataclass(frozen=True, slots=True)
class YieldBin(SemiconductorEntity): bin_code: str = ''; passing: bool = False
@dataclass(frozen=True, slots=True)
class SPCParameter(SemiconductorEntity): measurement_parameter_id: str | None = None; chart_family: str = 'i_mr'; lsl: float | None = None; usl: float | None = None; target: float | None = None
@dataclass(frozen=True, slots=True)
class SPCViolation(SemiconductorEntity): spc_parameter_id: str = ''; measurement_id: str | None = None; rule: str = ''; timestamp: datetime | None = None
@dataclass(frozen=True, slots=True)
class Sensor(SemiconductorEntity): tool_id: str = ''; chamber_id: str | None = None; unit: str | None = None
@dataclass(frozen=True, slots=True)
class FDCTrace(SemiconductorEntity): sensor_id: str = ''; lot_id: str | None = None; wafer_id: str | None = None; recipe_version_id: str | None = None; start_time: datetime | None = None
@dataclass(frozen=True, slots=True)
class FDCFeature(SemiconductorEntity): trace_id: str = ''; feature_name: str = ''; value: float | None = None
@dataclass(frozen=True, slots=True)
class Alarm(SemiconductorEntity): tool_id: str = ''; chamber_id: str | None = None; code: str = ''; timestamp: datetime | None = None; severity: str | None = None
@dataclass(frozen=True, slots=True)
class EquipmentEvent(SemiconductorEntity): tool_id: str = ''; chamber_id: str | None = None; event_type: str = ''; timestamp: datetime | None = None
@dataclass(frozen=True, slots=True)
class PM(SemiconductorEntity): tool_id: str = ''; chamber_id: str | None = None; started_at: datetime | None = None; completed_at: datetime | None = None
@dataclass(frozen=True, slots=True)
class Maintenance(SemiconductorEntity): tool_id: str = ''; chamber_id: str | None = None; maintenance_type: str = ''; timestamp: datetime | None = None
@dataclass(frozen=True, slots=True)
class Calibration(SemiconductorEntity): tool_id: str = ''; sensor_id: str | None = None; parameter_id: str | None = None; timestamp: datetime | None = None
@dataclass(frozen=True, slots=True)
class EngineeringChange(SemiconductorEntity): affected_entity: EntityRef | None = None; effective_at: datetime | None = None; change_type: str | None = None
@dataclass(frozen=True, slots=True)
class Excursion(SemiconductorEntity): parameter_id: str | None = None; detected_at: datetime | None = None; affected_population_key: str | None = None
@dataclass(frozen=True, slots=True)
class Investigation(SemiconductorEntity): excursion_id: str | None = None; status: str = 'open'; owner: str | None = None
@dataclass(frozen=True, slots=True)
class Hypothesis(SemiconductorEntity): investigation_id: str = ''; statement: str = ''; status: str = 'new'
@dataclass(frozen=True, slots=True)
class Evidence(SemiconductorEntity): hypothesis_id: str = ''; direction: str = 'neutral'; strength: float | None = None; source_entity: EntityRef | None = None
@dataclass(frozen=True, slots=True)
class CorrectiveAction(SemiconductorEntity): investigation_id: str = ''; action: str = ''; status: str = 'open'; owner: str | None = None


_REQUIRED_RELATIONS = {
    Area: ('fab_id',), Bay: ('area_id',), Tool: ('area_id',), Module: ('tool_id',), Chamber: ('tool_id',),
    Operation: ('route_id',), RecipeVersion: ('recipe_id',), Wafer: ('lot_id',), Die: ('wafer_id',),
    Measurement: ('parameter_id',), SPCViolation: ('spc_parameter_id',), Sensor: ('tool_id',),
    FDCTrace: ('sensor_id',), FDCFeature: ('trace_id',), Alarm: ('tool_id',), EquipmentEvent: ('tool_id',),
    PM: ('tool_id',), Maintenance: ('tool_id',), Calibration: ('tool_id',),
    Hypothesis: ('investigation_id',), Evidence: ('hypothesis_id',), CorrectiveAction: ('investigation_id',),
}
_REQUIRED_VALUE_FIELDS = {
    RecipeVersion: ('version',), YieldBin: ('bin_code',), SPCParameter: ('chart_family',), SPCViolation: ('rule',),
    FDCFeature: ('feature_name',), Alarm: ('code',), EquipmentEvent: ('event_type',), Maintenance: ('maintenance_type',),
    Hypothesis: ('statement',), CorrectiveAction: ('action',),
}
_FINITE_VALUE_FIELDS = {
    Measurement: ('value',), SPCParameter: ('lsl','usl','target'), FDCFeature: ('value',), Evidence: ('strength',),
}

_RELATION_FIELDS = {
    Area: ('fab_id',), Bay: ('area_id',), Tool: ('area_id','bay_id'), Module: ('tool_id',), Chamber: ('tool_id','module_id'),
    Product: ('technology_id',), Route: ('product_id','technology_id'), Operation: ('route_id',), Recipe: ('operation_id',), RecipeVersion: ('recipe_id',),
    Lot: ('product_id','route_id','carrier_id'), Wafer: ('lot_id',), Die: ('wafer_id',), Measurement: ('parameter_id','lot_id','wafer_id','die_id','operation_id','tool_id','chamber_id','recipe_version_id'),
    Inspection: ('wafer_id','operation_id','tool_id'), Defect: ('inspection_id','wafer_id','die_id'), SPCViolation: ('spc_parameter_id','measurement_id'),
    Sensor: ('tool_id','chamber_id'), FDCTrace: ('sensor_id','lot_id','wafer_id','recipe_version_id'), FDCFeature: ('trace_id',), Alarm: ('tool_id','chamber_id'), EquipmentEvent: ('tool_id','chamber_id'),
    PM: ('tool_id','chamber_id'), Maintenance: ('tool_id','chamber_id'), Calibration: ('tool_id','sensor_id','parameter_id'), Investigation: ('excursion_id',), Hypothesis: ('investigation_id',), Evidence: ('hypothesis_id',), CorrectiveAction: ('investigation_id',),
}


def relationship_fields(entity_or_type: SemiconductorEntity | type[SemiconductorEntity]) -> tuple[str, ...]:
    typ = entity_or_type if isinstance(entity_or_type, type) else type(entity_or_type)
    return _RELATION_FIELDS.get(typ, ())


__all__ = ['SemiconductorEntityKind','EntityRef','SemiconductorEntity','Fab','Area','Bay','Tool','Chamber','Module','Technology','Product','Route','Operation','Recipe','RecipeVersion','Lot','Carrier','Wafer','Die','Measurement','MetrologyParameter','Inspection','Defect','YieldBin','SPCParameter','SPCViolation','Sensor','FDCTrace','FDCFeature','Alarm','EquipmentEvent','PM','Maintenance','Calibration','EngineeringChange','Excursion','Investigation','Hypothesis','Evidence','CorrectiveAction','relationship_fields']
