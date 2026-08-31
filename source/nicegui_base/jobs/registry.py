from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
@dataclass(frozen=True,slots=True)
class JobDefinition:
    key:str; public_name:str; purpose:str; use_when:tuple[str,...]; avoid_when:str
_ITEMS={
 'durable_job_adapter':JobDefinition('durable_job_adapter','DurableJobAdapter','Stable long-running-job boundary',('multi-minute analysis','restart-survivable work','external scheduler integration'),'ordinary sub-second UI work'),
 'in_process_job_adapter':JobDefinition('in_process_job_adapter','InProcessJobAdapter','Reference task-backed adapter',('development','short jobs','single-process deployments'),'work that must survive process restarts'),
}
JOB_REGISTRY:Mapping[str,JobDefinition]=MappingProxyType(_ITEMS)
__all__=['JobDefinition','JOB_REGISTRY']
