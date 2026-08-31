from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

class CertificationStatus(str, Enum):
    PASS='pass'; WARNING='warning'; FAIL='fail'; SKIP='skip'

@dataclass(frozen=True, slots=True)
class CertificationCheck:
    key: str
    label: str
    status: CertificationStatus
    detail: str
    category: str='integration'
    required: bool=True

@dataclass(frozen=True, slots=True)
class CertificationReport:
    framework_version: str
    checks: tuple[CertificationCheck,...]
    metadata: Mapping[str,object]=field(default_factory=dict)
    @property
    def failures(self): return tuple(c for c in self.checks if c.status is CertificationStatus.FAIL and c.required)
    @property
    def warnings(self): return tuple(c for c in self.checks if c.status is CertificationStatus.WARNING)
    @property
    def passed(self): return not self.failures
    @property
    def summary(self):
        return {s.value: sum(c.status is s for c in self.checks) for s in CertificationStatus}
