from __future__ import annotations

import csv
import inspect
import io
import json
import weakref
import html
import uuid
from collections.abc import Callable, Sequence
from typing import Any

from nicegui_base.visual import render_icon_svg
from nicegui_base.visualization import (
    AxisSpec, AxisType, ChartAnnotation, ChartKind, ChartPanelSpec, ChartSize, CrossFilterEngine, LegendPosition, SelectionMode,
    SeriesSpec, SpatialPoint, SpecLimits, ThresholdSpec, WaferPoint, build_echarts_options, chart_theme,
)


def _ui():
    try:
        from nicegui import ui
    except ImportError as exc:
        raise RuntimeError('NiceGUI is required to render NiceGUI Base visualizations') from exc
    return ui


def _register_client_delete(ui: Any, callback: Callable[..., Any]) -> bool:
    context=getattr(ui,'context',None)
    client=getattr(context,'client',None)
    on_delete=getattr(client,'on_delete',None)
    if callable(on_delete):
        on_delete(callback)
        return True
    return False


async def _invoke(callback: Callable[..., Any] | None, *args) -> Any:
    if callback is None:
        return None
    value = callback(*args)
    if inspect.isawaitable(value):
        return await value
    return value


def _icon(ui, key: str, *, label: str | None = None, size: str = 'xs'):
    return ui.html(render_icon_svg(key, size=size, label=label), sanitize=False).classes('cui-svg-icon-host')

_ACTIVE_CHARTS: 'weakref.WeakSet[ChartPanel]' = weakref.WeakSet()

def apply_all_chart_themes(mode: str) -> None:
    if mode not in {'light','dark'}:
        return
    failures=[]
    for panel in tuple(_ACTIVE_CHARTS):
        try:
            panel.apply_theme(mode)
        except Exception as exc:
            failures.append(f'{type(panel).__name__}: {type(exc).__name__}: {exc}')
    if failures:
        raise RuntimeError('NiceGUI Base chart theme update failed: ' + ' | '.join(failures))


class ChartLegend:
    """Imperative legend controls for a rendered :class:`ChartPanel`."""
    def __init__(self, panel: 'ChartPanel', position: LegendPosition | None = None):
        self.panel = panel
        self.position = position or panel.spec.legend

    def toggle(self, series_name: str):
        return self.panel.element.run_chart_method('dispatchAction', {'type': 'legendToggleSelect', 'name': series_name})

    def select(self, series_name: str):
        return self.panel.element.run_chart_method('dispatchAction', {'type': 'legendSelect', 'name': series_name})

    def unselect(self, series_name: str):
        return self.panel.element.run_chart_method('dispatchAction', {'type': 'legendUnSelect', 'name': series_name})


class ChartTooltip:
    """Programmatic tooltip control backed by ECharts dispatch actions."""
    def __init__(self, panel: 'ChartPanel'): self.panel = panel
    def show(self, *, series_index: int = 0, data_index: int = 0):
        return self.panel.element.run_chart_method('dispatchAction', {'type': 'showTip', 'seriesIndex': series_index, 'dataIndex': data_index})
    def hide(self):
        return self.panel.element.run_chart_method('dispatchAction', {'type': 'hideTip'})


class ChartSelection:
    def __init__(self, panel: 'ChartPanel', mode: SelectionMode | None = None):
        self.panel = panel
        self.mode = mode or panel.spec.selection

    def select(self, *, series_index: int = 0, data_index: int = 0):
        return self.panel.element.run_chart_method('dispatchAction', {'type': 'select', 'seriesIndex': series_index, 'dataIndex': data_index})

    def clear(self):
        # ECharts supports unselect actions for selectable series. Brush selections are cleared separately.
        self.panel.brush.clear()
        for index, _ in enumerate(self.panel.series):
            self.panel.element.run_chart_method('dispatchAction', {'type': 'unselect', 'seriesIndex': index})


class ChartZoom:
    """Two-dimensional analytical view control backed by ECharts dataZoom.

    Direct wheel/trackpad and drag gestures update the ECharts data windows. Toolbar
    operations always read the live chart option first so they continue from the user's
    current direct-manipulation state instead of a stale Python-side percentage.
    """
    IDS = {'x': 'cui-x-zoom', 'y': 'cui-y-zoom'}

    def __init__(self, panel: 'ChartPanel'):
        self.panel = panel
        self._fallback = {'x': (0.0, 100.0), 'y': (0.0, 100.0)}

    @staticmethod
    def _validate(start: float, end: float) -> tuple[float, float]:
        start=float(start); end=float(end)
        if not (0 <= start < end <= 100):
            raise ValueError('zoom range must satisfy 0 <= start < end <= 100')
        return start,end

    async def ranges(self) -> dict[str, tuple[float, float]]:
        result=dict(self._fallback)
        try:
            option=await self.panel.element.run_chart_method('getOption')
        except Exception:
            option=None
        for item in (option or {}).get('dataZoom', ()):
            item_id=item.get('id')
            for axis, zoom_id in self.IDS.items():
                if item_id == zoom_id:
                    result[axis]=(float(item.get('start',0)),float(item.get('end',100)))
        self._fallback.update(result)
        return result

    async def set_range(self, start: float = 0, end: float = 100, *, axis: str = 'both'):
        start,end=self._validate(start,end)
        axes=('x','y') if axis == 'both' else (axis,)
        if any(a not in self.IDS for a in axes):
            raise ValueError("axis must be 'x', 'y', or 'both'")
        for a in axes:
            self._fallback[a]=(start,end)
            await self.panel.element.run_chart_method('dispatchAction', {
                'type':'dataZoom','dataZoomId':self.IDS[a],'start':start,'end':end,
            })

    async def _scale(self, *, axis: str, factor: float):
        current=await self.ranges(); axes=('x','y') if axis == 'both' else (axis,)
        for a in axes:
            start,end=current[a]; span=end-start
            target=max(4.0,min(100.0,span*factor)); center=(start+end)/2
            new_start=max(0.0,center-target/2); new_end=min(100.0,center+target/2)
            if new_end-new_start < target:
                if new_start <= 0: new_end=min(100.0,target)
                elif new_end >= 100: new_start=max(0.0,100-target)
            await self.set_range(new_start,new_end,axis=a)

    async def zoom_in(self, axis: str = 'both'):
        return await self._scale(axis=axis,factor=.66)

    async def zoom_out(self, axis: str = 'both'):
        return await self._scale(axis=axis,factor=1.52)

    async def reset(self, axis: str = 'both'):
        return await self.set_range(0,100,axis=axis)


class ChartBrush:
    def __init__(self, panel: 'ChartPanel'): self.panel = panel
    def clear(self):
        return self.panel.element.run_chart_method('dispatchAction', {'type': 'brush', 'areas': []})


class ChartDataView:
    """Framework-owned, accessible data representation for a chart."""
    def __init__(self, panel: 'ChartPanel'): self.panel = panel

    def rows(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for series in self.panel.series:
            for index, value in enumerate(series.data):
                result.append({'series': series.label, 'index': index, 'value': value})
        return result

    def open(self):
        ui = _ui()
        dialog = ui.dialog()
        with dialog:
            with ui.element('section').classes('cui-dialog cui-chart-data-dialog cui-overlay-surface cui-overlay-surface--dialog').props('role="dialog" aria-modal="true" data-cui-overlay="dialog"'):
                with ui.element('div').classes('cui-dialog__head'):
                    with ui.element('div').classes('cui-dialog__copy'):
                        ui.label(f'{self.panel.spec.title} — Data').classes('cui-dialog__title')
                    close = ui.button(on_click=dialog.close).props('flat round aria-label="Close"').classes('cui-icon-button cui-dialog__close')
                    with close: _icon(ui,'close',label='Close')
                with ui.element('div').classes('cui-dialog__body'):
                    with ui.element('div').classes('cui-chart-data-table-wrap'):
                        with ui.element('table').classes('cui-chart-data-table'):
                            with ui.element('thead'):
                                with ui.element('tr'):
                                    for label in ('Series', 'Index', 'Value'):
                                        with ui.element('th'): ui.label(label)
                            with ui.element('tbody'):
                                for row in self.rows():
                                    with ui.element('tr'):
                                        for value in (row['series'], row['index'], row['value']):
                                            with ui.element('td'): ui.label(str(value))
                with ui.element('div').classes('cui-dialog__footer'):
                    ui.element('div').classes('cui-dialog__footer-spacer')
                    ui.button('Close', on_click=dialog.close).props('flat no-caps').classes('cui-button cui-button--secondary cui-control--medium')
        dialog.open()
        return dialog


class ChartFullscreen:
    def __init__(self, panel: 'ChartPanel'): self.panel = panel
    async def enter(self):
        ui = _ui(); element_id = getattr(self.panel.container, 'id', None)
        if element_id is None:
            return ui.fullscreen.enter()
        return await ui.run_javascript(f'''const e=getHtmlElement({int(element_id)}); if(e?.requestFullscreen) await e.requestFullscreen();''')
    async def exit(self):
        return await _ui().run_javascript('if(document.fullscreenElement) await document.exitFullscreen();')
    async def toggle(self):
        ui=_ui(); element_id=getattr(self.panel.container,'id',None)
        if element_id is None: return ui.fullscreen.toggle()
        return await ui.run_javascript(f'''if(document.fullscreenElement){{await document.exitFullscreen();}}else{{const e=getHtmlElement({int(element_id)});if(e?.requestFullscreen)await e.requestFullscreen();}}''')


class ChartExport:
    def __init__(self, panel: 'ChartPanel'): self.panel = panel

    async def data_url(self, *, image_type: str = 'png', pixel_ratio: int = 2) -> str:
        if image_type not in {'png', 'jpeg', 'svg'}:
            raise ValueError('image_type must be png, jpeg, or svg')
        return await self.panel.element.run_chart_method('getDataURL', {'type': image_type, 'pixelRatio': pixel_ratio, 'backgroundColor': 'transparent'})

    async def download_image(self, filename: str | None = None, *, image_type: str = 'png') -> str:
        data_url = await self.data_url(image_type=image_type)
        filename = filename or f'{self.panel.spec.title.lower().replace(" ", "-")}.{image_type}'
        await _ui().run_javascript(
            f'''const a=document.createElement('a');a.href={json.dumps(data_url)};a.download={json.dumps(filename)};document.body.appendChild(a);a.click();a.remove();'''
        )
        return data_url

    def csv_text(self) -> str:
        buffer=io.StringIO(); writer=csv.writer(buffer); writer.writerow(['series','index','value'])
        for row in self.panel.data_view.rows(): writer.writerow([row['series'],row['index'],row['value']])
        return buffer.getvalue()

    def download_csv(self, filename: str | None = None):
        filename = filename or f'{self.panel.spec.title.lower().replace(" ", "-")}.csv'
        return _ui().download.content(self.csv_text(), filename)

    async def copy_csv(self) -> str:
        text=self.csv_text()
        await _ui().run_javascript(f'navigator.clipboard.writeText({json.dumps(text)})')
        return text


class ChartToolbar:
    """Company analytical toolbar with direct 2D zoom and explicit axis range control."""
    def __init__(self, panel: 'ChartPanel', *, zoom=True, reset=True, fullscreen=True, export_image=True, export_data=True, data_view=True):
        self.panel=panel; self.zoom=zoom; self.reset=reset; self.fullscreen=fullscreen; self.export_image=export_image; self.export_data=export_data; self.data_view=data_view
        self.element=None
        self.render()

    def _button(self, icon: str, label: str, callback):
        ui=_ui(); b=ui.button(on_click=callback).props(f'flat round aria-label={json.dumps(label)}').classes('cui-icon-button')
        with b: _icon(ui,icon,label=label)
        from nicegui_base.integrations.nicegui_interactions import Tooltip
        Tooltip(label).attach(b); return b

    def _range_button(self):
        ui=_ui()
        trigger=ui.button().props('flat round aria-label="View range"').classes('cui-icon-button cui-chart-range-trigger')
        with trigger:
            _icon(ui,'expand',label='View range')
            with ui.menu().props('anchor="bottom right" self="top right" :offset="[0,8]"').classes('cui-menu cui-chart-range-menu cui-overlay-surface cui-overlay-surface--popover'):
                ui.label('View range').classes('cui-chart-range-menu__title')
                ui.label('Wheel/trackpad zooms both axes · drag pans the analytical window').classes('cui-chart-range-menu__help')
                for axis,label in (('both','Both axes'),('x','X axis'),('y','Y axis')):
                    with ui.element('div').classes('cui-chart-range-row'):
                        ui.label(label).classes('cui-chart-range-row__label')
                        async def out(e=None,_axis=axis): await self.panel.zoom.zoom_out(_axis)
                        async def reset(e=None,_axis=axis): await self.panel.zoom.reset(_axis)
                        async def inside(e=None,_axis=axis): await self.panel.zoom.zoom_in(_axis)
                        b=ui.button(on_click=out).props(f'flat round dense aria-label={json.dumps(label+" zoom out")}').classes('cui-icon-button cui-chart-range-row__button')
                        with b:_icon(ui,'minus',label=label+' zoom out')
                        b=ui.button(on_click=reset).props(f'flat round dense aria-label={json.dumps(label+" fit")}').classes('cui-icon-button cui-chart-range-row__button')
                        with b:_icon(ui,'refresh',label=label+' fit')
                        b=ui.button(on_click=inside).props(f'flat round dense aria-label={json.dumps(label+" zoom in")}').classes('cui-icon-button cui-chart-range-row__button')
                        with b:_icon(ui,'add',label=label+' zoom in')
        from nicegui_base.integrations.nicegui_interactions import Tooltip
        Tooltip('View range').attach(trigger)
        return trigger

    def render(self):
        ui=_ui()
        with ui.element('div').classes('cui-chart-toolbar').props('role="toolbar" aria-label="Chart controls"') as self.element:
            if self.zoom:
                async def zoom_in(e=None): await self.panel.zoom.zoom_in('both')
                async def zoom_out(e=None): await self.panel.zoom.zoom_out('both')
                self._button('add','Zoom in',zoom_in)
                self._button('minus','Zoom out',zoom_out)
                self._range_button()
            if self.reset:
                async def reset(e=None): await self.panel.zoom.reset('both')
                self._button('refresh','Reset chart',reset)
            if self.data_view:
                self._button('table','View chart data',lambda: self.panel.data_view.open())
            if self.export_data or self.export_image:
                export_button=ui.button().props('flat round aria-label="Export chart"').classes('cui-icon-button')
                with export_button:
                    _icon(ui,'download',label='Export chart')
                    with ui.menu().props('anchor="bottom right" self="top right" :offset="[0,8]"').classes('cui-menu cui-chart-export-menu cui-overlay-surface cui-overlay-surface--popover'):
                        if self.export_image:
                            async def image(e=None): await self.panel.export.download_image()
                            with ui.button(on_click=image).props('flat dense no-caps').classes('cui-menu-item'):
                                _icon(ui,'image',size='xs'); ui.label('Image · PNG')
                        if self.export_data:
                            with ui.button(on_click=lambda: self.panel.export.download_csv()).props('flat dense no-caps').classes('cui-menu-item'):
                                _icon(ui,'table',size='xs'); ui.label('Data · CSV')
                            async def copy_data(e=None): await self.panel.export.copy_csv()
                            with ui.button(on_click=copy_data).props('flat dense no-caps').classes('cui-menu-item'):
                                _icon(ui,'copy',size='xs'); ui.label('Copy data · CSV')
                from nicegui_base.integrations.nicegui_interactions import Tooltip
                Tooltip('Export').attach(export_button)
            if self.fullscreen:
                async def fullscreen(e=None): await self.panel.fullscreen.toggle()
                self._button('fullscreen','Toggle fullscreen',fullscreen)
        return self.element


class ChartCrossFilter:
    def __init__(self, engine: CrossFilterEngine | None=None): self.engine=engine or CrossFilterEngine()


def _numeric_spatial_values(series: Sequence[SeriesSpec]) -> list[float]:
    values=[]
    for item in series:
        for point in item.data:
            if isinstance(point,(list,tuple)) and len(point)>=3 and isinstance(point[2],(int,float)):
                values.append(float(point[2]))
    return values


def _render_heatmap_scale(ui, series: Sequence[SeriesSpec]):
    values=_numeric_spatial_values(series); low=min(values) if values else 0.0; high=max(values) if values else 1.0
    label=next((s.label for s in series if s.visible),'Intensity')
    with ui.element('div').classes('cui-chart-scale-band').props(f'role="group" aria-label={json.dumps(label+" color scale")}') as band:
        ui.label(label).classes('cui-chart-scale-band__title')
        with ui.element('div').classes('cui-chart-scale-band__scale'):
            ui.label(f'{low:.3g}').classes('cui-chart-scale-band__value')
            ui.element('div').classes('cui-chart-scale-band__gradient').props('aria-hidden="true"')
            ui.label(f'{high:.3g}').classes('cui-chart-scale-band__value')
    return band


def _chart_accessibility_summary(spec: ChartPanelSpec, series: Sequence[SeriesSpec]) -> str:
    visible=[item for item in series if item.visible]
    points=sum(len(item.data) for item in visible)
    kind=spec.kind.value.replace('_',' ')
    summary=f'{kind.title()} chart with {len(visible)} visible series and {points} data points.'
    if spec.description:
        summary += f' {spec.description}'
    return summary


def _render_chart_accessibility_data(ui, spec: ChartPanelSpec, series: Sequence[SeriesSpec], *, summary_id: str) -> None:
    rows=[]
    total=0
    for item in series:
        if not item.visible:
            continue
        total += len(item.data)
        for index,value in enumerate(item.data):
            if len(rows)<200:
                rows.append((item.label,index,value))
    with ui.element('div').classes('cui-chart-a11y'):
        ui.label(_chart_accessibility_summary(spec,series)).props(f'id="{summary_id}"')
        if total>200:
            ui.label(f'Data alternative shows the first 200 of {total} points.')
        with ui.element('table').props('aria-label="Chart data alternative"'):
            with ui.element('thead'):
                with ui.element('tr'):
                    for label in ('Series','Index','Value'):
                        with ui.element('th'): ui.label(label)
            with ui.element('tbody'):
                for label,index,value in rows:
                    with ui.element('tr'):
                        for cell in (label,index,value):
                            with ui.element('td'): ui.label(str(cell))


class ChartPanel:
    def __init__(self, series: Sequence[SeriesSpec], *, spec: ChartPanelSpec,
                 thresholds: Sequence[ThresholdSpec]=(), spec_limits: SpecLimits | None=None, annotations: Sequence[ChartAnnotation]=(),
                 on_click: Callable[..., Any] | None=None, on_select: Callable[..., Any] | None=None, theme_mode: str='light'):
        self.spec=spec; self.series=tuple(series); self.thresholds=tuple(thresholds); self.spec_limits=spec_limits; self.annotations=tuple(annotations); self.theme_mode=theme_mode
        self._disposed=False; self._renderable=True; self._pending_render=False
        chart_id=uuid.uuid4().hex; self.title_id=f'cui-chart-title-{chart_id}'; self.summary_id=f'cui-chart-summary-{chart_id}'
        ui=_ui()
        with ui.element('section').classes(spec.classes).props(f'role="figure" aria-labelledby="{self.title_id}" aria-describedby="{self.summary_id}"') as self.container:
            with ui.element('div').classes('cui-chart-panel__header'):
                with ui.element('div'):
                    ui.label(spec.title).props(f'id="{self.title_id}"').classes('cui-chart-panel__title')
                    if spec.description: ui.label(spec.description).classes('cui-chart-panel__description')
                self.toolbar_host=ui.element('div').classes('cui-chart-toolbar-host')
            with ui.element('div').classes('cui-chart-panel__body'):
                options=build_echarts_options(spec,self.series,thresholds=self.thresholds,spec_limits=self.spec_limits,annotations=getattr(self,'annotations',()),theme=chart_theme(self.theme_mode))
                # ECharts' built-in toolbox remains available in options for API compatibility, but the visual toolbox is hidden;
                # NiceGUI Base renders its own semantic-icon toolbar instead.
                if 'toolbox' in options: options['toolbox']['show']=False
                self.element=ui.echart(options).classes('cui-chart-canvas w-full').props(f'aria-label={json.dumps(spec.title)}')
                self.scale_band=_render_heatmap_scale(ui,self.series) if spec.kind is ChartKind.HEATMAP else None
                _render_chart_accessibility_data(ui,spec,self.series,summary_id=self.summary_id)
        self.legend=ChartLegend(self); self.tooltip=ChartTooltip(self); self.selection=ChartSelection(self)
        self.zoom=ChartZoom(self); self.brush=ChartBrush(self); self.data_view=ChartDataView(self)
        self.fullscreen=ChartFullscreen(self); self.export=ChartExport(self)
        with self.toolbar_host:
            t=spec.toolbar
            self.toolbar=ChartToolbar(self,zoom=t.zoom,reset=t.reset,fullscreen=t.fullscreen,export_image=t.export_image,export_data=t.export_data,data_view=t.data_view)
        _ACTIVE_CHARTS.add(self)
        _register_client_delete(ui,self.dispose)
        self.container.on('cui-chart-visibility', self._handle_visibility, js_handler='e => emit(e.detail)')
        self._install_visibility_observer(ui)
        if on_click:
            if hasattr(self.element, 'on_point_click'): self.element.on_point_click(on_click)
            else: self.element.on('click', on_click)
        if on_select:
            event_name='chart:brushSelected' if spec.selection is SelectionMode.BRUSH else 'chart:selectchanged'
            self.element.on(event_name, on_select)

    def _install_visibility_observer(self, ui: Any) -> None:
        element_id=getattr(self.container,'id',None)
        try: element_id=int(element_id)
        except (TypeError,ValueError): return
        ui.run_javascript(f'''(() => {{
          const host=getHtmlElement({element_id});
          if(!host)return;
          host.__cuiChartVisibilityCleanup?.();
          let intersecting=true;
          let disposed=false;
          const cleanup=()=>{{if(disposed)return;disposed=true;io.disconnect();ro.disconnect();delete host.__cuiChartVisibilityCleanup;}};
          const report=()=>{{
            if(disposed)return;
            if(!host.isConnected){{cleanup();return;}}
            const rect=host.getBoundingClientRect();
            const style=getComputedStyle(host);
            const visible=intersecting && rect.width>0 && rect.height>0 && style.display!=='none' && style.visibility!=='hidden';
            host.dispatchEvent(new CustomEvent('cui-chart-visibility',{{detail:{{visible,width:rect.width,height:rect.height}}}}));
          }};
          const io=new IntersectionObserver(entries=>{{intersecting=Boolean(entries[0]?.isIntersecting);report();}});
          const ro=new ResizeObserver(()=>report());
          io.observe(host);ro.observe(host);host.__cuiChartVisibilityCleanup=cleanup;requestAnimationFrame(report);
        }})()''')

    async def _handle_visibility(self, event: Any) -> None:
        args=getattr(event,'args',{}) or {}
        visible=bool(args.get('visible')) if isinstance(args,dict) else bool(args)
        await self.set_renderable(visible)

    async def set_renderable(self, renderable: bool) -> None:
        """Gate expensive ECharts mutations behind actual visible, non-zero layout."""
        if self._disposed:return
        changed=self._renderable!=bool(renderable); self._renderable=bool(renderable)
        if not self._renderable:return
        if self._pending_render:
            self._pending_render=False; self.element.update()
        if changed:
            try: await self.element.run_chart_method('resize')
            except Exception: pass

    def _replace_options(self, options: dict[str,Any]) -> None:
        self.element.options.clear(); self.element.options.update(options)
        if self._renderable:
            self.element.update(); self._pending_render=False
        else:
            self._pending_render=True

    def update_series(self, series: Sequence[SeriesSpec]) -> None:
        if self._disposed:return
        self.series=tuple(series)
        options=build_echarts_options(self.spec,self.series,thresholds=self.thresholds,spec_limits=self.spec_limits,annotations=getattr(self,'annotations',()),theme=chart_theme(self.theme_mode))
        if 'toolbox' in options: options['toolbox']['show']=False
        self._replace_options(options)

    def apply_theme(self, mode: str) -> None:
        if self._disposed:return
        if mode not in {'light','dark'}: raise ValueError('chart theme mode must be light or dark')
        self.theme_mode=mode
        options=build_echarts_options(self.spec,self.series,thresholds=self.thresholds,spec_limits=self.spec_limits,annotations=getattr(self,'annotations',()),theme=chart_theme(mode))
        if 'toolbox' in options: options['toolbox']['show']=False
        self._replace_options(options)

    def dispose(self) -> None:
        if self._disposed:return
        self._disposed=True; self._pending_render=False
        _ACTIVE_CHARTS.discard(self)


class _TypedChart(ChartPanel):
    KIND=ChartKind.LINE
    def __init__(self, title: str, series: Sequence[SeriesSpec], *, description: str|None=None,
                 size: ChartSize=ChartSize.STANDARD, x_axis: AxisSpec|None=None, y_axis: AxisSpec|None=None,
                 thresholds: Sequence[ThresholdSpec]=(), spec_limits: SpecLimits|None=None, **kwargs):
        spec=ChartPanelSpec(title=title,description=description,kind=self.KIND,size=size,
                            x_axis=x_axis or AxisSpec(kind=AxisType.CATEGORY),y_axis=y_axis or AxisSpec())
        normalized=tuple(SeriesSpec(s.key,s.label,s.data,kind=self.KIND,x_key=s.x_key,y_key=s.y_key,stack=s.stack,
                                    smooth=s.smooth,marker=s.marker,line_style=s.line_style,semantic_color=s.semantic_color,visible=s.visible,y_axis_index=s.y_axis_index) for s in series)
        super().__init__(normalized,spec=spec,thresholds=thresholds,spec_limits=spec_limits,**kwargs)


class LineChart(_TypedChart): KIND=ChartKind.LINE
class AreaChart(_TypedChart): KIND=ChartKind.AREA
class BarChart(_TypedChart): KIND=ChartKind.BAR
class StackedBarChart(_TypedChart): KIND=ChartKind.STACKED_BAR
class ScatterChart(_TypedChart): KIND=ChartKind.SCATTER
class Histogram(_TypedChart): KIND=ChartKind.HISTOGRAM
class BoxPlot(_TypedChart): KIND=ChartKind.BOX_PLOT
class Heatmap(_TypedChart): KIND=ChartKind.HEATMAP
class ParetoChart(ChartPanel):
    def __init__(self, title: str, categories: Sequence[str], values: Sequence[float], cumulative_pct: Sequence[float], *, description: str|None=None, **kwargs):
        if not (len(categories)==len(values)==len(cumulative_pct)): raise ValueError('Pareto categories, values, and cumulative_pct must have equal length')
        series=(SeriesSpec('contributors','Contributors',list(values),kind=ChartKind.BAR), SeriesSpec('cumulative','Cumulative %',list(cumulative_pct),kind=ChartKind.LINE,y_axis_index=1,semantic_color='info',smooth=True))
        spec=ChartPanelSpec(title=title,description=description,kind=ChartKind.PARETO,x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(categories)),y_axis=AxisSpec(kind=AxisType.VALUE))
        super().__init__(series,spec=spec,**kwargs)
class ControlChart(_TypedChart): KIND=ChartKind.CONTROL
class TimelineChart(_TypedChart): KIND=ChartKind.TIMELINE
class DonutChart(_TypedChart): KIND=ChartKind.DONUT
class Gauge(_TypedChart): KIND=ChartKind.GAUGE


def _spatial_bin(value: float, low: float, high: float, bins: int = 7) -> int:
    if high <= low:
        return bins // 2
    ratio=max(0.0,min(1.0,(float(value)-low)/(high-low)))
    return min(bins-1,int(ratio*bins))


class _SpatialSvgPanel:
    """Purpose-built engineering spatial renderer.

    Generic scatter charts distort wafer/die geometry and make spatial signatures
    difficult to read. This renderer owns its SVG coordinate system, legend,
    selection emphasis and zoom/pan behavior while preserving Company chart anatomy.
    """
    def __init__(self,title:str,*,description:str|None=None,size:ChartSize=ChartSize.STANDARD):
        self.title=title;self.description=description;self.size=size;self.viewport_id='cui-spatial-'+uuid.uuid4().hex
        self.container=None;self.element=None;self._zoom=1.0

    def _toolbar(self):
        ui=_ui()
        def button(icon,label,js):
            b=ui.button(on_click=lambda:ui.run_javascript(js)).props(f'flat round aria-label={json.dumps(label)}').classes('cui-icon-button')
            with b:_icon(ui,icon,label=label)
            from nicegui_base.integrations.nicegui_interactions import Tooltip
            Tooltip(label).attach(b)
        button('add','Zoom in',f"window.CompanyUISpatial.zoom('{self.viewport_id}',1.18)")
        button('minus','Zoom out',f"window.CompanyUISpatial.zoom('{self.viewport_id}',0.84)")
        button('refresh','Reset spatial view',f"window.CompanyUISpatial.reset('{self.viewport_id}')")

    def _render(self,svg:str):
        ui=_ui()
        with ui.element('section').classes(f'cui-chart-panel cui-chart-panel--{self.size.value} cui-spatial-panel').props('role="figure"') as self.container:
            with ui.element('div').classes('cui-chart-panel__header'):
                with ui.element('div'):
                    ui.label(self.title).classes('cui-chart-panel__title')
                    if self.description:ui.label(self.description).classes('cui-chart-panel__description')
                with ui.element('div').classes('cui-chart-toolbar'):
                    self._toolbar()
            with ui.element('div').classes('cui-chart-panel__body'):
                with ui.element('div').classes('cui-spatial-viewport').props(f'id={json.dumps(self.viewport_id)} tabindex="0" aria-label={json.dumps(self.title)}'):
                    self.element=ui.html(svg,sanitize=False).classes('cui-spatial-svg-host')
        ui.run_javascript(f"window.CompanyUISpatial && window.CompanyUISpatial.attach('{self.viewport_id}')")


class WaferMap(_SpatialSvgPanel):
    def __init__(self,title:str,points:Sequence[WaferPoint],*,description:str|None=None,size:ChartSize=ChartSize.STANDARD,**kwargs):
        super().__init__(title,description=description or 'Die-level wafer signature · wheel/drag to inspect spatial structure',size=size)
        pts=tuple(points);values=[float(p.value) for p in pts if isinstance(p.value,(int,float))]; low=min(values) if values else 0; high=max(values) if values else 1
        cx,cy,r=220,200,168; xs=[p.x for p in pts] or [-1,1]; ys=[p.y for p in pts] or [-1,1]; span=max(max(abs(float(x)) for x in xs),max(abs(float(y)) for y in ys),1)
        step=(r*1.82)/(span*2+1); die=max(8,min(22,step*.84)); parts=[]
        clip_id=f'{self.viewport_id}-wafer-clip'
        parts.append(f'<svg viewBox="0 0 560 400" role="img" aria-label="{html.escape(title)}" xmlns="http://www.w3.org/2000/svg">')
        parts.append(f'<defs><clipPath id="{clip_id}"><circle cx="220" cy="200" r="168"/></clipPath></defs>')
        parts.append('<g class="cui-wafer-guides" aria-hidden="true"><circle cx="220" cy="200" r="168"/><circle cx="220" cy="200" r="112"/><circle cx="220" cy="200" r="56"/><path d="M220 32V368M52 200H388"/></g>')
        parts.append(f'<g class="cui-wafer-dies" clip-path="url(#{clip_id})">')
        for p in pts:
            x=cx+(float(p.x)/span)*r*.9; y=cy-(float(p.y)/span)*r*.9; status=html.escape(str(getattr(p,'status','') or ''))
            if p.value is None:
                cls='cui-spatial-missing'+(' is-watch' if status.lower() not in {'','normal','ok'} else ''); tooltip=html.escape(f'Die ({p.x}, {p.y}) · no measurement · {status or "normal"}')
            else:
                b=_spatial_bin(float(p.value),low,high); cls=f'cui-spatial-bin-{b}'+(' is-watch' if status.lower() not in {'','normal','ok'} else ''); tooltip=html.escape(f'Die ({p.x}, {p.y}) · {float(p.value):.3f} · {status or "normal"}')
            parts.append(f'<rect class="cui-wafer-die {cls}" x="{x-die/2:.2f}" y="{y-die/2:.2f}" width="{die:.2f}" height="{die:.2f}" rx="3"><title>{tooltip}</title></rect>')
        parts.append('</g><circle class="cui-wafer-boundary" cx="220" cy="200" r="168"/><path class="cui-wafer-notch" d="M211 365 L220 374 L229 365"/>')
        parts.append(_spatial_svg_legend(low,high,x=430,y=92,height=190,title='Measurement'))
        parts.append('<text class="cui-spatial-annotation" x="220" y="22" text-anchor="middle">CENTER ↔ EDGE SIGNATURE</text>')
        parts.append('</svg>');self._render(''.join(parts))


class SpatialMap(_SpatialSvgPanel):
    def __init__(self,title:str,points:Sequence[SpatialPoint],*,description:str|None=None,size:ChartSize=ChartSize.STANDARD,**kwargs):
        super().__init__(title,description=description or 'Die/residual field · hover cells for values; wheel/drag to inspect',size=size)
        pts=tuple(points);values=[float(p.value) for p in pts if isinstance(p.value,(int,float))];low=min(values) if values else 0;high=max(values) if values else 1
        xs=sorted({float(p.x) for p in pts});ys=sorted({float(p.y) for p in pts}); xmap={v:i for i,v in enumerate(xs)};ymap={v:i for i,v in enumerate(ys)}
        left,top,width,height=42,34,360,300; radius=14; cell_w=width/max(1,len(xs));cell_h=height/max(1,len(ys));parts=[f'<svg viewBox="0 0 560 400" role="img" aria-label="{html.escape(title)}" xmlns="http://www.w3.org/2000/svg">']
        clip_id=f'{self.viewport_id}-grid-clip'
        parts.append(f'<defs><clipPath id="{clip_id}"><rect x="42" y="34" width="360" height="300" rx="{radius}"/></clipPath></defs>')
        parts.append(f'<rect class="cui-spatial-grid-bg" x="42" y="34" width="360" height="300" rx="{radius}"/>')
        parts.append(f'<g class="cui-spatial-cells" clip-path="url(#{clip_id})">')
        for p in pts:
            ix=xmap[float(p.x)];iy=ymap[float(p.y)];x=left+ix*cell_w;y=top+(len(ys)-1-iy)*cell_h
            label=html.escape(str(p.label or f'{p.x},{p.y}'))
            if p.value is None:
                cls='cui-spatial-missing'; tooltip=html.escape(f'{label} · no measurement')
            else:
                b=_spatial_bin(float(p.value),low,high); cls=f'cui-spatial-bin-{b}'; tooltip=html.escape(f'{label} · residual {float(p.value):.3f}')
            parts.append(f'<rect class="cui-spatial-cell {cls}" x="{x+1:.2f}" y="{y+1:.2f}" width="{max(2,cell_w-2):.2f}" height="{max(2,cell_h-2):.2f}" rx="4"><title>{tooltip}</title></rect>')
        parts.append('</g>')
        parts.append(f'<rect class="cui-spatial-grid-outline" x="42" y="34" width="360" height="300" rx="{radius}"/>')
        parts.append(_spatial_svg_legend(low,high,x=430,y=92,height=190,title='Residual'))
        parts.append('<text class="cui-spatial-annotation" x="42" y="362">LOWER-LEFT ORIGIN · CELL-LEVEL RESIDUAL FIELD</text>')
        parts.append('</svg>');self._render(''.join(parts))



class WaferComparisonMap(_SpatialSvgPanel):
    """Affected/control wafer comparison with one shared quantitative scale."""
    def __init__(self,title:str,affected:Sequence[WaferPoint],control:Sequence[WaferPoint],*,description:str|None=None,size:ChartSize=ChartSize.STANDARD):
        super().__init__(title,description=description or 'Synchronized affected vs control wafer signature · one shared scale',size=size)
        apts=tuple(affected); cpts=tuple(control); allpts=apts+cpts
        values=[float(p.value) for p in allpts if isinstance(p.value,(int,float))]; low=min(values) if values else 0; high=max(values) if values else 1
        xs=[float(p.x) for p in allpts] or [-1,1]; ys=[float(p.y) for p in allpts] or [-1,1]
        span=max(max(abs(x) for x in xs),max(abs(y) for y in ys),1)
        r=126; step=(r*1.82)/(span*2+1); die=max(6,min(17,step*.82))
        parts=[f'<svg viewBox="0 0 760 400" role="img" aria-label="{html.escape(title)}" xmlns="http://www.w3.org/2000/svg">']
        def wafer(points,cx,label,subtitle):
            clip_id=f'{self.viewport_id}-{label.lower()}-clip'
            parts.append(f'<defs><clipPath id="{clip_id}"><circle cx="{cx}" cy="196" r="{r}"/></clipPath></defs>')
            parts.append(f'<text class="cui-spatial-compare-title" x="{cx}" y="31" text-anchor="middle">{html.escape(label)}</text>')
            parts.append(f'<text class="cui-spatial-compare-subtitle" x="{cx}" y="49" text-anchor="middle">{html.escape(subtitle)}</text>')
            for rr,opacity in ((r,.9),(r*.67,.36),(r*.34,.26)):
                parts.append(f'<circle class="cui-wafer-guide-ring" cx="{cx}" cy="196" r="{rr:.1f}" opacity="{opacity}"/>')
            parts.append(f'<g class="cui-wafer-dies" clip-path="url(#{clip_id})">')
            for point in points:
                x=cx+(float(point.x)/span)*r*.9; y=196-(float(point.y)/span)*r*.9
                status=html.escape(str(getattr(point,'status','') or ''))
                if point.value is None:
                    cls='cui-spatial-missing'+(' is-watch' if status.lower() not in {'','normal','ok'} else ''); tooltip=html.escape(f'{label} die ({point.x}, {point.y}) · no measurement · {status or "normal"}')
                else:
                    b=_spatial_bin(float(point.value),low,high); cls=f'cui-spatial-bin-{b}'+(' is-watch' if status.lower() not in {'','normal','ok'} else ''); tooltip=html.escape(f'{label} die ({point.x}, {point.y}) · {float(point.value):.3f} · {status or "normal"}')
                parts.append(f'<rect class="cui-wafer-die {cls}" x="{x-die/2:.2f}" y="{y-die/2:.2f}" width="{die:.2f}" height="{die:.2f}" rx="2.5"><title>{tooltip}</title></rect>')
            parts.append('</g>')
            parts.append(f'<circle class="cui-wafer-boundary" cx="{cx}" cy="196" r="{r}"/>')
            parts.append(f'<path class="cui-wafer-notch" d="M{cx-8} {196+r-2} L{cx} {196+r+7} L{cx+8} {196+r-2}"/>')
        wafer(apts,190,'AFFECTED',f'{len(apts)} measured dies')
        wafer(cpts,490,'CONTROL',f'{len(cpts)} measured dies')
        parts.append(_spatial_svg_legend(low,high,x=678,y=102,height=176,title='Shared scale'))
        if values:
            am=[float(p.value) for p in apts if isinstance(p.value,(int,float))]; cm=[float(p.value) for p in cpts if isinstance(p.value,(int,float))]
            if am and cm:
                delta=sum(am)/len(am)-sum(cm)/len(cm)
                parts.append(f'<text class="cui-spatial-annotation" x="340" y="370" text-anchor="middle">MEAN Δ {delta:+.3f} · SAME COLOR SCALE</text>')
        parts.append('</svg>'); self._render(''.join(parts))


class ChamberFingerprintMatrix(_SpatialSvgPanel):
    """Purpose-built chamber/process fingerprint matrix on one normalized scale."""
    def __init__(self,title:str,rows:Sequence[str],columns:Sequence[str],values:Sequence[Sequence[float]],*,description:str|None=None,size:ChartSize=ChartSize.STANDARD):
        if not rows or not columns: raise ValueError('ChamberFingerprintMatrix requires row and column labels')
        matrix=[tuple(float(v) for v in row) for row in values]
        if len(matrix)!=len(rows) or any(len(row)!=len(columns) for row in matrix): raise ValueError('fingerprint values must match row/column dimensions')
        super().__init__(title,description=description or 'Normalized chamber/process fingerprint · hover cells for exact contribution',size=size)
        flat=[v for row in matrix for v in row]; low=min(flat); high=max(flat)
        left,top,width,height=126,70,410,230; radius=14; cell_w=width/len(columns); cell_h=height/len(rows)
        clip_id=f'{self.viewport_id}-fingerprint-clip'
        parts=[f'<svg viewBox="0 0 680 390" role="img" aria-label="{html.escape(title)}" xmlns="http://www.w3.org/2000/svg">']
        parts.append(f'<defs><clipPath id="{clip_id}"><rect x="{left}" y="{top}" width="{width}" height="{height}" rx="{radius}"/></clipPath></defs>')
        for j,label in enumerate(columns):
            x=left+(j+.5)*cell_w; parts.append(f'<text class="cui-fingerprint-column" x="{x:.1f}" y="52" text-anchor="middle">{html.escape(str(label))}</text>')
        for i,label in enumerate(rows):
            y=top+(i+.5)*cell_h+4; parts.append(f'<text class="cui-fingerprint-row" x="{left-12}" y="{y:.1f}" text-anchor="end">{html.escape(str(label))}</text>')
        parts.append(f'<rect class="cui-fingerprint-bg" x="{left}" y="{top}" width="{width}" height="{height}" rx="{radius}"/>')
        parts.append(f'<g clip-path="url(#{clip_id})">')
        for i,row in enumerate(matrix):
            for j,value in enumerate(row):
                x=left+j*cell_w; y=top+i*cell_h; b=_spatial_bin(value,low,high)
                tooltip=html.escape(f'{rows[i]} · {columns[j]} · normalized {value:+.3f}')
                parts.append(f'<rect class="cui-fingerprint-cell cui-spatial-bin-{b}" x="{x+1:.2f}" y="{y+1:.2f}" width="{max(2,cell_w-2):.2f}" height="{max(2,cell_h-2):.2f}" rx="4"><title>{tooltip}</title></rect>')
                parts.append(f'<text class="cui-fingerprint-value" x="{x+cell_w/2:.1f}" y="{y+cell_h/2+4:.1f}" text-anchor="middle">{value:+.2f}</text>')
        parts.append('</g>')
        parts.append(f'<rect class="cui-fingerprint-outline" x="{left}" y="{top}" width="{width}" height="{height}" rx="{radius}"/>')
        parts.append(_spatial_svg_legend(low,high,x=574,y=104,height=156,title='Normalized'))
        parts.append('<text class="cui-spatial-annotation" x="126" y="342">ROW = CHAMBER · COLUMN = PROCESS SIGNAL · SHARED NORMALIZED SCALE</text>')
        parts.append('</svg>'); self._render(''.join(parts))


class CommonalityMatrix(_SpatialSvgPanel):
    """Evidence/commonality matrix optimized for RCA population comparison."""
    def __init__(self,title:str,rows:Sequence[str],columns:Sequence[str],scores:Sequence[Sequence[float]],*,description:str|None=None,size:ChartSize=ChartSize.STANDARD):
        if not rows or not columns: raise ValueError('CommonalityMatrix requires row and column labels')
        matrix=[tuple(float(v) for v in row) for row in scores]
        if len(matrix)!=len(rows) or any(len(row)!=len(columns) for row in matrix): raise ValueError('commonality scores must match row/column dimensions')
        if any(v<0 or v>1 for row in matrix for v in row): raise ValueError('commonality scores must be between 0 and 1')
        super().__init__(title,description=description or 'RCA factor commonality · darker cells indicate stronger population enrichment',size=size)
        left,top,width,height=166,72,370,224; radius=14; cw=width/len(columns); ch=height/len(rows); clip_id=f'{self.viewport_id}-commonality-clip'
        parts=[f'<svg viewBox="0 0 660 390" role="img" aria-label="{html.escape(title)}" xmlns="http://www.w3.org/2000/svg">']
        parts.append(f'<defs><clipPath id="{clip_id}"><rect x="{left}" y="{top}" width="{width}" height="{height}" rx="{radius}"/></clipPath></defs>')
        for j,label in enumerate(columns): parts.append(f'<text class="cui-commonality-column" x="{left+(j+.5)*cw:.1f}" y="52" text-anchor="middle">{html.escape(str(label))}</text>')
        for i,label in enumerate(rows): parts.append(f'<text class="cui-commonality-row" x="{left-12}" y="{top+(i+.5)*ch+4:.1f}" text-anchor="end">{html.escape(str(label))}</text>')
        parts.append(f'<rect class="cui-commonality-bg" x="{left}" y="{top}" width="{width}" height="{height}" rx="{radius}"/>')
        parts.append(f'<g clip-path="url(#{clip_id})">')
        for i,row in enumerate(matrix):
            for j,value in enumerate(row):
                x=left+j*cw; y=top+i*ch; opacity=.08+.82*value; tooltip=html.escape(f'{rows[i]} · {columns[j]} · {value*100:.0f}% commonality')
                parts.append(f'<rect class="cui-commonality-cell" x="{x+1:.2f}" y="{y+1:.2f}" width="{max(2,cw-2):.2f}" height="{max(2,ch-2):.2f}" rx="4" fill-opacity="{opacity:.3f}"><title>{tooltip}</title></rect>')
                parts.append(f'<text class="cui-commonality-value" x="{x+cw/2:.1f}" y="{y+ch/2+4:.1f}" text-anchor="middle">{value*100:.0f}%</text>')
        parts.append('</g>')
        parts.append(f'<rect class="cui-commonality-outline" x="{left}" y="{top}" width="{width}" height="{height}" rx="{radius}"/>')
        parts.append('<text class="cui-spatial-annotation" x="166" y="338">FACTOR ENRICHMENT ACROSS AFFECTED / CONTROL / BASELINE POPULATIONS</text>')
        parts.append('</svg>'); self._render(''.join(parts))


class RadialProfilePlot(_SpatialSvgPanel):
    """Center-to-edge profile specialized for wafer radial signatures."""
    def __init__(self,title:str,affected:Sequence[float],control:Sequence[float],*,unit:str='',description:str|None=None,size:ChartSize=ChartSize.STANDARD):
        if len(affected)<2 or len(control)<2: raise ValueError('RadialProfilePlot requires at least two affected and control samples')
        super().__init__(title,description=description or 'Center → edge profile · compare radial signature without Cartesian chart chrome',size=size)
        av=[float(v) for v in affected]; cv=[float(v) for v in control]; values=av+cv; low=min(values); high=max(values); pad=max((high-low)*.12,.1); ymin=low-pad; ymax=high+pad
        left,right,top,bottom=62,590,58,310
        def points(vals):
            out=[]
            for i,value in enumerate(vals):
                x=left+(right-left)*(i/(len(vals)-1)); y=bottom-(bottom-top)*((value-ymin)/(ymax-ymin)); out.append(f'{x:.1f},{y:.1f}')
            return ' '.join(out)
        parts=[f'<svg viewBox="0 0 680 400" role="img" aria-label="{html.escape(title)}" xmlns="http://www.w3.org/2000/svg">']
        for i in range(5):
            y=top+(bottom-top)*i/4; val=ymax-(ymax-ymin)*i/4
            parts.append(f'<line class="cui-radial-grid" x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}"/>')
            parts.append(f'<text class="cui-spatial-legend-label" x="{left-10}" y="{y+4:.1f}" text-anchor="end">{val:.2f}</text>')
        parts.append(f'<line class="cui-radial-axis" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"/>')
        parts.append(f'<polyline class="cui-radial-profile cui-radial-profile--control" points="{points(cv)}"/>')
        parts.append(f'<polyline class="cui-radial-profile cui-radial-profile--affected" points="{points(av)}"/>')
        for vals,cls in ((cv,'control'),(av,'affected')):
            for i,value in enumerate(vals):
                x=left+(right-left)*(i/(len(vals)-1)); y=bottom-(bottom-top)*((value-ymin)/(ymax-ymin))
                parts.append(f'<circle class="cui-radial-point cui-radial-point--{cls}" cx="{x:.1f}" cy="{y:.1f}" r="3.5"><title>{cls.title()} r={i/(len(vals)-1):.2f} · {value:.3f} {html.escape(unit)}</title></circle>')
        parts.append(f'<text class="cui-spatial-annotation" x="{left}" y="345">CENTER · r/R 0.0</text>')
        parts.append(f'<text class="cui-spatial-annotation" x="{right}" y="345" text-anchor="end">EDGE · r/R 1.0</text>')
        parts.append('<g transform="translate(456,22)"><line class="cui-radial-profile cui-radial-profile--affected" x1="0" y1="0" x2="24" y2="0"/><text class="cui-spatial-legend-label" x="32" y="4">Affected</text><line class="cui-radial-profile cui-radial-profile--control" x1="92" y1="0" x2="116" y2="0"/><text class="cui-spatial-legend-label" x="124" y="4">Control</text></g>')
        parts.append(f'<text class="cui-spatial-annotation" x="{left}" y="25">VALUE {html.escape(unit).upper()}</text>')
        parts.append('</svg>'); self._render(''.join(parts))

def _spatial_svg_legend(low:float,high:float,*,x:int,y:int,height:int,title:str)->str:
    step=height/7;parts=[f'<text class="cui-spatial-legend-title" x="{x}" y="{y-18}">{html.escape(title)}</text>']
    for i in range(7):parts.append(f'<rect class="cui-spatial-bin-{6-i}" x="{x}" y="{y+i*step:.2f}" width="12" height="{step+1:.2f}"/>')
    parts.append(f'<text class="cui-spatial-legend-label" x="{x+20}" y="{y+8}">{high:.3g}</text>')
    parts.append(f'<text class="cui-spatial-legend-label" x="{x+20}" y="{y+height}">{low:.3g}</text>')
    return ''.join(parts)


class PlotlyPanel:
    """Escape hatch for specialist Plotly figures while preserving NiceGUI Base panel anatomy."""
    def __init__(self, title: str, figure: Any, *, description: str|None=None, size: ChartSize=ChartSize.STANDARD):
        ui=_ui()
        if isinstance(figure,dict):
            figure=dict(figure); config=dict(figure.get('config') or {})
            config.setdefault('displayModeBar',False); config.setdefault('responsive',True); config.setdefault('scrollZoom',True)
            figure['config']=config
        self.figure=figure
        with ui.element('section').classes(f'cui-chart-panel cui-chart-panel--{size.value}') as self.container:
            with ui.element('div').classes('cui-chart-panel__header'):
                with ui.element('div'):
                    ui.label(title).classes('cui-chart-panel__title')
                    if description: ui.label(description).classes('cui-chart-panel__description')
            with ui.element('div').classes('cui-chart-panel__body'):
                self.element=ui.plotly(figure).classes('cui-chart-canvas w-full')


class DistributionPanel:
    def __init__(self, title: str, series: Sequence[SeriesSpec], **kwargs): self.chart=Histogram(title,series,**kwargs)


class ProcessTrendPanel:
    def __init__(self, title: str, series: Sequence[SeriesSpec], *, spec_limits: SpecLimits|None=None, **kwargs):
        self.chart=ControlChart(title,series,spec_limits=spec_limits,**kwargs)


__all__=[
'ChartPanel','ChartToolbar','ChartLegend','ChartTooltip','ChartSelection','ChartZoom','ChartBrush','ChartCrossFilter','ChartDataView','ChartFullscreen','ChartExport',
'LineChart','AreaChart','BarChart','StackedBarChart','ScatterChart','Histogram','BoxPlot','Heatmap','ParetoChart','ControlChart','TimelineChart','DonutChart','Gauge',
'WaferMap','SpatialMap','WaferComparisonMap','ChamberFingerprintMatrix','CommonalityMatrix','RadialProfilePlot','PlotlyPanel','DistributionPanel','ProcessTrendPanel','apply_all_chart_themes']
