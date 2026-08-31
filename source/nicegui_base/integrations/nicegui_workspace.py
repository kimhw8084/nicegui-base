from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from typing import Any

from nicegui_base.workspace import DockPosition, PanelSpec, WorkspaceBreakpoint, WorkspaceController
from nicegui_base.visual import render_icon_svg


def _ui():
    try: from nicegui import ui
    except ImportError as exc: raise RuntimeError('NiceGUI is required to render NiceGUI Base workspace components') from exc
    return ui


def _icon(ui,key,label):return ui.html(render_icon_svg(key,size='xs',label=label),sanitize=False).classes('cui-svg-icon-host')


class NiceGUIWorkspace:
    """Interactive renderer for WorkspaceController with governed drag/resize chrome."""
    def __init__(self, controller: WorkspaceController, *, breakpoint: WorkspaceBreakpoint=WorkspaceBreakpoint.DESKTOP):
        self.controller=controller;self.breakpoint=breakpoint;self._panels:dict[str,Any]={};self._bodies:dict[str,Any]={}
        ui=_ui(); columns=controller.layout.columns(breakpoint)
        self.element=ui.element('section').classes('cui-workspace-grid').style(f'--cui-workspace-columns:{columns}')
        self._unsubscribe=controller.watch(lambda _:self.refresh())

    def add_panel(self,spec:PanelSpec, render:Callable[[],Any]|None=None):
        if spec.panel_id not in self.controller.layout.panels:self.controller.register_panel(spec)
        ui=_ui();state=self.controller.state(spec.panel_id);placement=self.controller.layout.placement(spec.panel_id,self.breakpoint)
        with self.element:
            with ui.element('article').classes('cui-workspace-panel').props(
                f'id="cui-workspace-{spec.panel_id}" draggable="true" data-panel-id="{spec.panel_id}" data-collapsed="{str(state.collapsed).lower()}" data-locked="{str(state.locked).lower()}"'
            ).style(self._style(placement)) as panel:
                panel.on('dragstart',lambda e,pid=spec.panel_id:self._drag_start(pid))
                panel.on('dragover',lambda e:None,js_handler='(e)=>{e.preventDefault();e.currentTarget.classList.add("is-drag-over")}')
                panel.on('dragleave',lambda e:None,js_handler='(e)=>e.currentTarget.classList.remove("is-drag-over")')
                panel.on('drop',lambda e,pid=spec.panel_id:self._drop_on(pid),js_handler='(e)=>{e.preventDefault();e.currentTarget.classList.remove("is-drag-over")}')
                with ui.element('div').classes('cui-workspace-panel__chrome'):
                    ui.label(str(spec.metadata.get('title',spec.panel_id))).classes('cui-workspace-panel__title')
                    ui.element('span').classes('cui-workspace-panel__spacer')
                    self._button('minus','Collapse',lambda pid=spec.panel_id:self.controller.collapse(pid,not self.controller.state(pid).collapsed))
                    self._button('lock','Lock',lambda pid=spec.panel_id:self.controller.lock(pid,not self.controller.state(pid).locked))
                    self._button('plus','Wider',lambda pid=spec.panel_id:self._resize(pid,1,0))
                    self._button('chevron-down','Taller',lambda pid=spec.panel_id:self._resize(pid,0,1))
                with ui.element('div').classes('cui-workspace-panel__body') as body:
                    if render:render()
        self._panels[spec.panel_id]=panel;self._bodies[spec.panel_id]=body
        self.refresh();return body

    def _button(self,icon,label,callback):
        ui=_ui()
        with ui.button(on_click=callback).props(f'flat round dense aria-label="{label}" title="{label}"').classes('cui-icon-button'):_icon(ui,icon,label)
    def _style(self,p):return f'grid-column:{p.column+1} / span {p.column_span};grid-row:{p.row+1} / span {p.row_span};'
    def _drag_start(self,panel_id):
        _ui().run_javascript(f'window.__cuiDragPanel={panel_id!r}')
    async def _drop_on(self,target_id):
        source=await _ui().run_javascript('window.__cuiDragPanel||null')
        if not source or source==target_id:return
        target=self.controller.layout.placement(target_id,self.breakpoint)
        try:self.controller.move(str(source),self.breakpoint,column=target.column,row=target.row)
        except (PermissionError,KeyError):return
    def _resize(self,panel_id,dc,dr):
        p=self.controller.layout.placement(panel_id,self.breakpoint)
        try:self.controller.resize(panel_id,self.breakpoint,column_span=max(1,p.column_span+dc),row_span=max(1,p.row_span+dr))
        except PermissionError:return
    def refresh(self):
        for panel_id,panel in tuple(self._panels.items()):
            try:state=self.controller.state(panel_id);p=self.controller.layout.placement(panel_id,self.breakpoint)
            except KeyError:continue
            panel.style(self._style(p));panel.props(f'data-collapsed="{str(state.collapsed).lower()}" data-locked="{str(state.locked).lower()}"')
            if state.hidden:panel.props('hidden')
            else:panel.props(remove='hidden')
    def close(self):self._unsubscribe()


__all__=['NiceGUIWorkspace']
