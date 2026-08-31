from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from typing import Any

from .models import AnalysisStatus, AnalyticalPanelState

PanelWatcher = Callable[[AnalyticalPanelState], Any]


class AnalyticalPanelController:
    """State machine shared by all analytical renderers."""
    def __init__(self) -> None:
        self._state=AnalyticalPanelState(); self._watchers:list[PanelWatcher]=[]
    @property
    def state(self)->AnalyticalPanelState:return deepcopy(self._state)
    def watch(self, callback:PanelWatcher):
        self._watchers.append(callback)
        def unsub():
            if callback in self._watchers:self._watchers.remove(callback)
        return unsub
    def _set(self,status:AnalysisStatus,**changes):
        self._state=replace(self._state,status=status,revision=self._state.revision+1,**changes)
        for callback in tuple(self._watchers):callback(self.state)
        return self.state
    def loading(self,message:str|None=None):return self._set(AnalysisStatus.LOADING,message=message,error_type=None)
    def ready(self,message:str|None=None):return self._set(AnalysisStatus.READY,message=message,stale_reason=None,partial_reason=None,error_type=None)
    def empty(self,message:str|None='No data'):return self._set(AnalysisStatus.EMPTY,message=message,error_type=None)
    def partial(self,reason:str,message:str|None=None):return self._set(AnalysisStatus.PARTIAL,message=message,partial_reason=reason,error_type=None)
    def stale(self,reason:str,message:str|None=None):return self._set(AnalysisStatus.STALE,message=message,stale_reason=reason,error_type=None)
    def error(self,error:BaseException|str):
        return self._set(AnalysisStatus.ERROR,message=str(error),error_type=type(error).__name__ if isinstance(error,BaseException) else 'Error')


__all__=['AnalyticalPanelController','PanelWatcher']
