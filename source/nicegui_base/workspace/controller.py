from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from typing import Any

from .engine import WorkspaceLayoutEngine
from .models import DockPosition, PanelInteractionState, PanelSpec, WorkspaceBreakpoint, WorkspaceInteractionSnapshot, WorkspaceLayoutSnapshot

WorkspaceWatcher = Callable[['WorkspaceController'], Any]


class WorkspaceController:
    """Interactive authority layered over deterministic WorkspaceLayoutEngine.

    It owns mutable interaction state and undo/redo while leaving geometry validation
    to the proven layout engine. Layout and interaction state can therefore be saved
    independently and restored without browser-specific state.
    """

    def __init__(self, layout: WorkspaceLayoutEngine | None = None, *, history_limit: int = 100) -> None:
        if history_limit < 1: raise ValueError('history_limit must be >= 1')
        self.layout = layout or WorkspaceLayoutEngine()
        self._states: dict[str, PanelInteractionState] = {}
        self._revision=0; self._history_limit=history_limit
        self._undo:list[tuple[WorkspaceLayoutSnapshot, WorkspaceInteractionSnapshot]]=[]
        self._redo:list[tuple[WorkspaceLayoutSnapshot, WorkspaceInteractionSnapshot]]=[]
        self._watchers:list[WorkspaceWatcher]=[]; self._closed=False

    @property
    def revision(self)->int:return self._revision
    @property
    def can_undo(self)->bool:return bool(self._undo)
    @property
    def can_redo(self)->bool:return bool(self._redo)
    @property
    def states(self):return {key:deepcopy(value) for key,value in self._states.items()}

    def _ensure_open(self):
        if self._closed:raise RuntimeError('WorkspaceController is closed')
    def watch(self,callback:WorkspaceWatcher):
        self._ensure_open();self._watchers.append(callback)
        def unsub():
            if callback in self._watchers:self._watchers.remove(callback)
        return unsub
    def _emit(self):
        self._revision+=1
        for callback in tuple(self._watchers):callback(self)
    def _capture(self):return self.layout.snapshot(),self.snapshot()
    def _checkpoint(self):
        self._undo.append(self._capture())
        if len(self._undo)>self._history_limit:self._undo.pop(0)
        self._redo.clear()
    def _mutate(self, fn):
        self._ensure_open(); before=self._capture(); self._checkpoint()
        try: result=fn()
        except BaseException:
            self.layout.restore(before[0]); self.restore(before[1],emit=False); self._undo.pop(); raise
        self._sync_states(); self._emit(); return result
    def _sync_states(self):
        panels=self.layout.panels
        for panel_id,spec in panels.items():
            if panel_id not in self._states:self._states[panel_id]=PanelInteractionState(panel_id,locked=spec.locked)
        for panel_id in tuple(self._states):
            if panel_id not in panels:self._states.pop(panel_id)

    def register_panel(self,spec:PanelSpec,**kwargs):
        return self._mutate(lambda:self.layout.register_panel(spec,**kwargs))
    def remove_panel(self,panel_id:str):return self._mutate(lambda:self.layout.remove_panel(panel_id))
    def state(self,panel_id:str)->PanelInteractionState:
        self._sync_states()
        try:return deepcopy(self._states[panel_id])
        except KeyError as exc:raise KeyError(panel_id) from exc
    def _guard(self,panel_id:str):
        state=self.state(panel_id)
        if state.locked:raise PermissionError(f'panel is locked: {panel_id}')
        return state
    def move(self,panel_id:str,breakpoint:WorkspaceBreakpoint,*,column:int,row:int):
        self._guard(panel_id);return self._mutate(lambda:self.layout.move(panel_id,breakpoint,column=column,row=row))
    def resize(self,panel_id:str,breakpoint:WorkspaceBreakpoint,*,column_span:int,row_span:int):
        self._guard(panel_id);return self._mutate(lambda:self.layout.resize(panel_id,breakpoint,column_span=column_span,row_span=row_span))
    def _set_state(self,panel_id:str,**changes):
        current=self.state(panel_id)
        def op():self._states[panel_id]=replace(current,**changes);return self._states[panel_id]
        return self._mutate(op)
    def collapse(self,panel_id:str,value:bool=True):return self._set_state(panel_id,collapsed=bool(value))
    def hide(self,panel_id:str,value:bool=True):return self._set_state(panel_id,hidden=bool(value))
    def lock(self,panel_id:str,value:bool=True):return self._set_state(panel_id,locked=bool(value))
    def dock(self,panel_id:str,position:DockPosition=DockPosition.NONE):
        self._guard(panel_id);return self._set_state(panel_id,dock=position)
    def split(self,panel_id:str,group:str|None):
        self._guard(panel_id);return self._set_state(panel_id,split_group=group)
    def duplicate(self,panel_id:str,new_panel_id:str)->PanelSpec:
        self._guard(panel_id)
        if not new_panel_id.strip():raise ValueError('new_panel_id must not be empty')
        source=self.layout.panels[panel_id]; clone=replace(source,panel_id=new_panel_id,locked=False,metadata=dict(source.metadata))
        self._mutate(lambda:self.layout.register_panel(clone));return clone
    def reset(self, snapshot:tuple[WorkspaceLayoutSnapshot, WorkspaceInteractionSnapshot] | None=None):
        self._ensure_open(); self._checkpoint()
        if snapshot is None:
            # Deterministically derive all breakpoints from the current registration defaults.
            specs=tuple(self.layout.snapshot().panels); fresh=WorkspaceLayoutEngine()
            for spec in specs:fresh.register_panel(spec)
            self.layout.restore(fresh.snapshot()); self._states={spec.panel_id:PanelInteractionState(spec.panel_id,locked=spec.locked) for spec in specs}
        else:self.layout.restore(snapshot[0]);self.restore(snapshot[1],emit=False)
        self._emit()
    def snapshot(self)->WorkspaceInteractionSnapshot:
        self._sync_states();return WorkspaceInteractionSnapshot(self._revision,tuple(deepcopy(self._states[key]) for key in self.layout.panels))
    def restore(self,snapshot:WorkspaceInteractionSnapshot,*,emit:bool=True):
        self._ensure_open(); available=set(self.layout.panels)
        unknown=[item.panel_id for item in snapshot.states if item.panel_id not in available]
        if unknown:raise ValueError(f'interaction state references unknown panels: {unknown!r}')
        self._states={item.panel_id:deepcopy(item) for item in snapshot.states};self._sync_states();self._revision=snapshot.revision
        if emit:self._emit()
    def undo(self)->bool:
        self._ensure_open()
        if not self._undo:return False
        target=self._undo.pop();self._redo.append(self._capture());self.layout.restore(target[0]);self.restore(target[1],emit=False);self._emit();return True
    def redo(self)->bool:
        self._ensure_open()
        if not self._redo:return False
        target=self._redo.pop();self._undo.append(self._capture());self.layout.restore(target[0]);self.restore(target[1],emit=False);self._emit();return True
    def close(self):self._closed=True;self._watchers.clear();self._undo.clear();self._redo.clear()


__all__=['WorkspaceController','WorkspaceWatcher']
