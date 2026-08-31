from __future__ import annotations

import inspect
from contextlib import AbstractContextManager
from typing import Any, Callable, Mapping

from nicegui_base.analysis import (
    AnalysisContext, AnalysisStatus, AnalyticalPanelController, Selection, SelectionBus,
    SelectionKind, SelectionMutationMode, columns_from_schema, query_data_source_table,
)
from nicegui_base.data_sources import DataSource
from nicegui_base.data_table import SelectionMode as TableSelectionMode, ServerDataTableSpec
from nicegui_base.integrations.nicegui_data_table import ServerDataTable
from nicegui_base.visual import render_icon_svg


def _ui():
    try:
        from nicegui import ui
    except ImportError as exc:
        raise RuntimeError('NiceGUI is required to render NiceGUI Base analytical components') from exc
    return ui


def _icon(ui, key: str, *, label: str):
    return ui.html(render_icon_svg(key, size='xs', label=label), sanitize=False).classes('cui-svg-icon-host')


class AnalyticalPanel(AbstractContextManager):
    """Uniform NiceGUI shell for every analytical visualization/table surface."""
    def __init__(self, title: str, *, controller: AnalyticalPanelController | None = None,
                 on_refresh: Callable[..., Any] | None = None, on_export: Callable[..., Any] | None = None,
                 on_data_view: Callable[..., Any] | None = None, on_fullscreen: Callable[..., Any] | None = None,
                 description: str | None = None):
        self.controller=controller or AnalyticalPanelController(); self.title=title
        ui=_ui()
        with ui.element('section').classes('cui-analytical-panel').props('data-status="ready"') as self.element:
            with ui.element('header').classes('cui-analytical-panel__header'):
                with ui.element('div').classes('cui-analytical-panel__heading'):
                    self.title_label=ui.label(title).classes('cui-analytical-panel__title')
                    if description: ui.label(description).classes('cui-caption')
                self.status_label=ui.label('Ready').classes('cui-analytical-panel__status').props('aria-live="polite"')
                with ui.element('div').classes('cui-analytical-panel__actions'):
                    for icon,label,callback in (
                        ('refresh','Refresh',on_refresh),('table','View data',on_data_view),('download','Export',on_export),('maximize','Fullscreen',on_fullscreen),
                    ):
                        if callback is None: continue
                        async def run(e=None, cb=callback):
                            value=cb()
                            if inspect.isawaitable(value): await value
                        with ui.button(on_click=run).props(f'flat round dense aria-label="{label}" title="{label}"').classes('cui-icon-button'):
                            _icon(ui,icon,label=label)
            self.body=ui.element('div').classes('cui-analytical-panel__body')
        self._unsubscribe=self.controller.watch(self._sync)
        self._sync(self.controller.state)

    def _sync(self,state):
        self.element.props(f'data-status="{state.status.value}"')
        label={
            AnalysisStatus.READY:'Ready',AnalysisStatus.LOADING:'Loading…',AnalysisStatus.EMPTY:'No data',
            AnalysisStatus.PARTIAL:'Partial data',AnalysisStatus.STALE:'Stale data',AnalysisStatus.ERROR:'Error',
        }[state.status]
        if state.message: label=f'{label} · {state.message}'
        self.status_label.set_text(label)
    def __enter__(self): self.body.__enter__(); return self
    def __exit__(self,exc_type,exc,tb): return self.body.__exit__(exc_type,exc,tb)
    def close(self): self._unsubscribe()


class DataSourceTable(ServerDataTable):
    """Server-paged table directly backed by a Wave 59 DataSource + AnalysisContext."""
    def __init__(self, source: DataSource, *, schema=None, context: AnalysisContext | None=None,
                 selections: SelectionBus | None=None, row_key: str | None=None, title: str | None=None,
                 selection: TableSelectionMode=TableSelectionMode.NONE, spec: ServerDataTableSpec | None=None, **kwargs):
        self.source=source; self.analysis_context=context; self.selection_bus=selections
        if schema is None:
            # Constructor cannot await schema; provider callers can pass schema explicitly.
            schema=getattr(source,'_schema',None)
        if schema is None: raise ValueError('DataSourceTable requires schema=DataSchema when the source schema is asynchronous')
        columns=columns_from_schema(schema)
        resolved_row_key=row_key or schema.key or (schema.fields[0].name if schema.fields else 'id')
        if spec is None:
            spec=ServerDataTableSpec(tuple(columns), row_key=resolved_row_key, title=title, selection=selection)
        async def fetch(query): return await query_data_source_table(source,query,context=context)
        original_on_select=kwargs.pop('on_select',None)
        async def on_select(rows):
            if self.selection_bus is not None:
                selections_=tuple(Selection(SelectionKind.ROW,str(row.get(resolved_row_key)),{'row':dict(row)},source='data-table') for row in rows)
                self.selection_bus.apply(selections_,mode=SelectionMutationMode.REPLACE,source='data-table')
            if original_on_select:
                value=original_on_select(rows)
                if inspect.isawaitable(value): await value
        super().__init__(columns,fetch=fetch,spec=spec,on_select=on_select,**kwargs)
        self._context_unsubscribe=context.watch(lambda _: self._schedule_context_refresh()) if context is not None else None

    def _schedule_context_refresh(self):
        try:
            import asyncio
            asyncio.get_running_loop().create_task(self.set_page(1),name='nicegui-base-table-context-refresh')
        except RuntimeError: pass

    async def aclose(self):
        if self._context_unsubscribe:self._context_unsubscribe();self._context_unsubscribe=None
        await super().aclose()


__all__=['AnalyticalPanel','DataSourceTable']
