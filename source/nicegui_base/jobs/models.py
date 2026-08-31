from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

class JobStatus(str, Enum):
    QUEUED='queued'; RUNNING='running'; SUCCEEDED='succeeded'; FAILED='failed'; CANCELLED='cancelled'

@dataclass(frozen=True, slots=True)
class JobHandle:
    job_id:str
    label:str|None=None
    metadata:Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if not self.job_id.strip(): raise ValueError('job_id must not be empty')

@dataclass(frozen=True, slots=True)
class JobSnapshot:
    handle:JobHandle
    status:JobStatus
    progress:float|None=None
    message:str|None=None
    error:str|None=None
    result_available:bool=False
    def __post_init__(self):
        if self.progress is not None and not 0 <= self.progress <= 1: raise ValueError('progress must be 0..1')

__all__=['JobStatus','JobHandle','JobSnapshot']
