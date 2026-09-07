from __future__ import annotations

import inspect
import json
import uuid
from contextlib import AbstractContextManager
from typing import Any, Callable, Mapping, Sequence

from nicegui_base.components import StatusIntent
from nicegui_base.content import (
    ActivityItem, BackgroundTaskSpec, ComparisonItem, ComparisonMetricSpec, EntityHeaderSpec, KeyValueItem, MetricCardSpec,
    SearchResultSpec, StepSpec, StepState, TreeNode, TrendDirection,
)
from nicegui_base.services import CommandRegistry
from nicegui_base.visual import render_icon_svg


def _ui():
    try:
        from nicegui import ui
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError('NiceGUI is required to render NiceGUI Base content components') from exc
    return ui


async def _invoke(callback: Callable[..., Any] | None, *args) -> Any:
    if callback is None: return None
    value=callback(*args)
    if inspect.isawaitable(value): return await value
    return value


def _icon(ui, key:str, *, label:str|None=None, size:str='sm'):
    return ui.html(render_icon_svg(key,size=size,label=label),sanitize=False).classes('cui-svg-icon-host')


class DeltaIndicator:
    def __init__(self, value:str, *, trend:TrendDirection=TrendDirection.UNKNOWN, intent:StatusIntent=StatusIntent.NEUTRAL):
        self.value=value; self.trend=trend; self.intent=intent; ui=_ui()
        icons={TrendDirection.UP:'arrow-up',TrendDirection.DOWN:'arrow-down',TrendDirection.STABLE:'minus',TrendDirection.UNKNOWN:'info'}
        with ui.element('span').classes(f'cui-metric-card__delta cui-metric-card__delta--{intent.value}') as self.element:
            _icon(ui,icons[trend],label=trend.value,size='xs'); ui.label(value)


class TrendIndicator(DeltaIndicator): pass


class MetricCard:
    def __init__(self, label:str, value:Any, *, description:str|None=None, delta:str|None=None,
                 trend:TrendDirection=TrendDirection.UNKNOWN, intent:StatusIntent=StatusIntent.NEUTRAL,
                 icon:str|None=None, help_text:str|None=None, on_click:Callable[...,Any]|None=None):
        self.spec=MetricCardSpec(label,value,description,delta,trend,intent,icon,on_click is not None,help_text)
        ui=_ui(); classes='cui-metric-card'+(' is-clickable' if on_click else '')
        with ui.element('section').classes(classes).props('role="button" tabindex="0"' if on_click else '') as self.element:
            with ui.element('div').classes('cui-metric-card__top'):
                if icon:_icon(ui,icon,size='sm')
                ui.label(label).classes('cui-metric-card__label')
            ui.label(str(value)).classes('cui-metric-card__value')
            if delta: DeltaIndicator(delta,trend=trend,intent=intent)
            if description: ui.label(description).classes('cui-metric-card__description')
            if help_text:
                from nicegui_base.integrations.nicegui_interactions import Tooltip
                Tooltip(help_text).attach(self.element)
        if on_click:self.element.on('click',on_click).on('keydown.enter',on_click).on('keydown.space',on_click)


class MetricStrip(AbstractContextManager):
    def __init__(self): self.element=_ui().element('section').classes('cui-metric-strip').props('aria-label="Summary metrics"')
    def __enter__(self): self.element.__enter__(); return self
    def __exit__(self,exc_type,exc,tb): return self.element.__exit__(exc_type,exc,tb)


class ProgressMetric:
    def __init__(self,label:str,value:float,*,target:float=1.0,display_value:str|None=None,description:str|None=None):
        if target<=0: raise ValueError('target must be positive')
        self.label=label; self.value=value; self.target=target; ui=_ui(); pct=max(0,min(1,value/target))
        with ui.element('div').classes('cui-progress-metric') as self.element:
            with ui.element('div').classes('cui-progress-metric__row'):
                ui.label(label).classes('cui-metric-card__label'); ui.label(display_value or f'{pct:.0%}').classes('cui-progress-metric__value')
            from nicegui_base.integrations.nicegui_interactions import ProgressBar
            ProgressBar(value=pct, label=label)
            if description: ui.label(description).classes('cui-metric-card__description')


class ComparisonMetric:
    def __init__(self,label:str,current:Any,*,baseline:Any=None,delta:Any=None,intent:StatusIntent=StatusIntent.NEUTRAL,description:str|None=None):
        self.spec=ComparisonMetricSpec(label,current,baseline,delta,intent,description); ui=_ui()
        with ui.element('div').classes('cui-comparison-metric') as self.element:
            with ui.element('div'):
                ui.label(label).classes('cui-comparison-metric__label')
                if description: ui.label(description).classes('cui-comparison-metric__muted')
            ui.label(str(current)).classes('cui-comparison-metric__value')
            ui.label('—' if baseline is None else str(baseline)).classes('cui-comparison-metric__value cui-comparison-metric__muted')
            ui.label('—' if delta is None else str(delta)).classes(f'cui-comparison-metric__value cui-metric-card__delta--{intent.value}')


class KeyValueList:
    def __init__(self,items:Sequence[KeyValueItem],*,on_copy:Callable[[KeyValueItem],Any]|None=None):
        self.items=tuple(items); ui=_ui()
        with ui.element('dl').classes('cui-key-value-list') as self.element:
            for item in items:
                with ui.element('dt').classes('cui-kv-label').props(f'aria-label="{item.label}"'):
                    ui.label(item.label)
                with ui.element('dd').classes('cui-kv-value'):
                    ui.label('—' if item.value is None else str(item.value))
                    if item.copyable and on_copy:
                        async def copy(e=None,i=item): await _invoke(on_copy,i)
                        b=ui.button(on_click=copy).props('flat round dense aria-label="Copy value"').classes('cui-icon-button')
                        with b:_icon(ui,'copy',label='Copy value',size='xs')


class DescriptionList(KeyValueList): pass


class PropertyGrid:
    def __init__(self,items:Sequence[KeyValueItem]):
        self.items=tuple(items); ui=_ui()
        with ui.element('section').classes('cui-property-grid') as self.element:
            for item in items:
                with ui.element('div').classes('cui-property'):
                    ui.label(item.label).classes('cui-property__label')
                    ui.label('—' if item.value is None else str(item.value)).classes('cui-property__value')
                    if item.description:ui.label(item.description).classes('cui-metric-card__description')


class EntityHeader:
    def __init__(self,title:str,*,subtitle:str|None=None,entity_type:str|None=None,status:str|None=None,
                 status_intent:StatusIntent=StatusIntent.NEUTRAL,icon:str|None=None,metadata:Sequence[KeyValueItem]=()):
        self.spec=EntityHeaderSpec(title,subtitle,entity_type,status,status_intent,icon,tuple(metadata)); ui=_ui()
        from nicegui_base.integrations.nicegui_components import StatusBadge
        with ui.element('header').classes('cui-entity-header') as self.element:
            if icon:
                with ui.element('div').classes('cui-entity-header__icon'):_icon(ui,icon,size='md')
            with ui.element('div').classes('cui-entity-header__copy'):
                with ui.element('div').classes('cui-field-label-row'):
                    ui.label(title).classes('cui-entity-header__title')
                    if status:StatusBadge(status,intent=status_intent)
                if subtitle:ui.label(subtitle).classes('cui-entity-header__subtitle')
                if entity_type or metadata:
                    with ui.element('div').classes('cui-entity-header__meta'):
                        if entity_type:ui.label(entity_type)
                        for item in metadata:ui.label(f'{item.label}: {item.value}')


def _tree_node(node:TreeNode)->dict[str,Any]:
    data={'id':node.key,'label':node.label,'disabled':node.disabled,**dict(node.metadata)}
    if node.children:data['children']=[_tree_node(x) for x in node.children]
    return data


class TreeView:
    def __init__(self,nodes:Sequence[TreeNode],*,selected:str|None=None,on_select:Callable[...,Any]|None=None,tick_strategy:str|None=None):
        self.nodes=tuple(nodes); ui=_ui(); kwargs={'label_key':'label','node_key':'id','on_select':on_select}
        if tick_strategy:kwargs['tick_strategy']=tick_strategy
        self.element=ui.tree([_tree_node(n) for n in nodes],**kwargs).classes('cui-tree')
        if selected is not None: self.element.select(selected)


class MarkdownViewer:
    def __init__(self,content:str,*,extras:Sequence[str]|None=None):
        self.content=content; ui=_ui(); kwargs={'sanitize':True}
        if extras is not None:kwargs['extras']=list(extras)
        self.element=ui.markdown(content,**kwargs).classes('cui-viewer cui-markdown-viewer')


class CodeViewer:
    def __init__(self,code:str,*,language:str='text'):
        self.code=code; self.language=language
        self.element=_ui().code(code,language=language).classes('cui-viewer cui-code-viewer')


class JsonViewer:
    def __init__(self,value:Any,*,read_only:bool=True):
        props={'content':{'json':value},'readOnly':read_only}
        self.element=_ui().json_editor(props).classes('cui-viewer cui-json-viewer')


class LogViewer:
    def __init__(self,lines:Sequence[str]=(),*,max_lines:int=500):
        if max_lines<1:raise ValueError('max_lines must be positive')
        self.element=_ui().log(max_lines=max_lines).classes('cui-viewer cui-log-viewer')
        for line in lines:self.element.push(str(line))
    def push(self,line:str):self.element.push(str(line))


class ImageViewer:
    """Company-owned evidence inspection workspace with observable pan/zoom state."""
    def __init__(self,source:str,*,allow_remote:bool=False,alt:str='Image',caption:str|None=None):
        low=source.lower().strip()
        if (low.startswith('http://') or low.startswith('https://')) and not allow_remote:
            raise ValueError('Remote image sources are disabled by default; package or proxy the asset locally')
        ui=_ui(); self.viewport_id='cui-image-'+uuid.uuid4().hex; self.zoom_id=self.viewport_id+'-zoom'
        with ui.element('section').classes('cui-viewer cui-image-viewer').props('data-cui-image-viewer=true') as self.element:
            with ui.element('div').classes('cui-image-viewer__toolbar').props('aria-label="Image viewer controls"'):
                with ui.element('div').classes('cui-image-viewer__heading'):
                    ui.label(caption or alt).classes('cui-image-viewer__caption')
                    ui.label('Wheel to zoom · drag to pan · double-click to fit').classes('cui-image-viewer__hint')
                with ui.element('div').classes('cui-image-viewer__actions'):
                    ui.label('100%').classes('cui-image-viewer__zoom cui-tabular').props(f'id={json.dumps(self.zoom_id)} aria-live="polite"')
                    self._tool(ui,'minus','Zoom out',f"window.CompanyUISpatial&&window.CompanyUISpatial.zoom('{self.viewport_id}',0.84)")
                    self._tool(ui,'add','Zoom in',f"window.CompanyUISpatial&&window.CompanyUISpatial.zoom('{self.viewport_id}',1.18)")
                    self._tool(ui,'refresh','Fit image',f"window.CompanyUISpatial&&window.CompanyUISpatial.reset('{self.viewport_id}')")
            with ui.element('div').classes('cui-image-viewer__viewport cui-spatial-viewport').props(
                f'id={json.dumps(self.viewport_id)} tabindex="0" aria-label={json.dumps(alt)} data-cui-spatial-scale="1.000"'
            ):
                self.image=ui.image(source).props(f'alt={json.dumps(alt)} draggable=false').classes('cui-image-viewer__image cui-spatial-svg-host')
                ui.label('FIT').classes('cui-image-viewer__mode').props('aria-hidden="true"')
        ui.run_javascript(f"""(() => {{ const id={json.dumps(self.viewport_id)}, zoomId={json.dumps(self.zoom_id)}; const host=document.getElementById(id); if(!host||!window.CompanyUISpatial)return; window.CompanyUISpatial.attach(id); const sync=e=>{{const s=e?.detail?.scale ?? window.CompanyUISpatial.stateOf(id)?.scale ?? 1; const out=document.getElementById(zoomId); if(out)out.textContent=`${{Math.round(s*100)}}%`; const mode=host.querySelector('.cui-image-viewer__mode'); if(mode)mode.textContent=s<=1.001?'FIT':'INSPECT';}}; host.addEventListener('cui-spatial-change',sync); sync(); }})()""")

    @staticmethod
    def _tool(ui, icon:str, label:str, js:str):
        button=ui.button(on_click=lambda: ui.run_javascript(js)).props(
            f'flat round aria-label={json.dumps(label)}'
        ).classes('cui-icon-button cui-icon-button--ghost')
        with button: _icon(ui,icon,label=label,size='xs')
        from nicegui_base.integrations.nicegui_interactions import Tooltip
        Tooltip(label).attach(button)
        return button


class SearchResults:
    def __init__(self,results:Sequence[SearchResultSpec],*,on_select:Callable[[SearchResultSpec],Any]|None=None):
        self.results=tuple(results); ui=_ui()
        with ui.element('section').classes('cui-search-results').props('role="list"') as self.element:
            for result in results:
                async def choose(e=None,r=result):await _invoke(on_select,r)
                with ui.element('article').classes('cui-search-result').props('role="button" tabindex="0"').on('click',choose).on('keydown.enter',choose).on('keydown.space',choose):
                    if result.icon:_icon(ui,result.icon,size='md')
                    with ui.element('div').classes('cui-entity-header__copy'):
                        ui.label(result.title).classes('cui-search-result__title')
                        if result.subtitle:ui.label(result.subtitle).classes('cui-search-result__subtitle')
                        if result.description:ui.label(result.description).classes('cui-search-result__description')


class ProgressSteps:
    def __init__(self,steps:Sequence[StepSpec]):
        self.steps=tuple(steps); ui=_ui(); state_icons={StepState.COMPLETE:'check',StepState.ERROR:'error',StepState.ACTIVE:'arrow-right'}
        with ui.element('nav').classes('cui-progress-steps').props('aria-label="Progress"') as self.element:
            for index,step in enumerate(steps,1):
                state=step.state.value
                with ui.element('div').classes(f'cui-progress-step is-{state}').props(
                    f'aria-current="step"' if step.state is StepState.ACTIVE else ''
                ):
                    with ui.element('div').classes('cui-progress-step__rail'):
                        with ui.element('span').classes('cui-progress-step__marker'):
                            key=step.icon or state_icons.get(step.state)
                            if key:_icon(ui,key,size='xs')
                            else:ui.label(str(index)).classes('cui-progress-step__number')
                    with ui.element('div').classes('cui-progress-step__copy'):
                        ui.label(step.label).classes('cui-progress-step__label')
                        ui.label(state.replace('_',' ').title()).classes('cui-progress-step__state')


class Stepper(AbstractContextManager):
    """NiceGUI stepper wrapper with NiceGUI Base progress semantics."""
    def __init__(self,steps:Sequence[StepSpec],*,value:str|None=None,vertical:bool=False):
        if not steps:raise ValueError('Stepper requires at least one step')
        self.steps=tuple(steps); self.value=value or steps[0].key; self.vertical=vertical; self.stepper=None
    def __enter__(self):
        ui=_ui(); self.stepper=ui.stepper(value=self.value).classes('cui-stepper')
        if self.vertical:self.stepper.props('vertical')
        self.stepper.__enter__(); return self
    def __exit__(self,exc_type,exc,tb):return self.stepper.__exit__(exc_type,exc,tb)
    def step(self,key:str):
        spec=next((s for s in self.steps if s.key==key),None)
        if spec is None:raise KeyError(key)
        return _ui().step(spec.key,title=spec.label)
    def next(self):return self.stepper.next()
    def previous(self):return self.stepper.previous()


class ComparePanel(AbstractContextManager):
    def __init__(self):self.element=_ui().element('section').classes('cui-compare-panel')
    def __enter__(self):self.element.__enter__();return self
    def __exit__(self,exc_type,exc,tb):return self.element.__exit__(exc_type,exc,tb)
    def side(self,label:str):
        ui=_ui(); container=ui.element('section').classes('cui-compare-side'); container.__enter__(); ui.label(label).classes('cui-property__label')
        class _Side(AbstractContextManager):
            def __enter__(self_inner):return self_inner
            def __exit__(self_inner,exc_type,exc,tb):return container.__exit__(exc_type,exc,tb)
        return _Side()


class BeforeAfter(ComparePanel): pass


class DifferenceTable:
    def __init__(self,items:Sequence[ComparisonItem],*,left_label:str='Before',right_label:str='After'):
        self.items=tuple(items); ui=_ui()
        with ui.element('table').classes('cui-difference-table') as self.element:
            with ui.element('thead'):
                with ui.element('tr'):
                    for label in ('Field',left_label,right_label,'Delta'):
                        with ui.element('th'): ui.label(label)
            with ui.element('tbody'):
                for item in items:
                    changed=item.changed if item.changed is not None else item.left!=item.right
                    with ui.element('tr').classes('is-changed' if changed else ''):
                        for value in (item.label,item.left,item.right,item.delta if item.delta is not None else '—'):
                            with ui.element('td'): ui.label('—' if value is None else str(value))


class CommandPalette:
    """Company-owned keyboard-first command surface with fuzzy search and disabled/contextual states."""
    def __init__(self,registry:CommandRegistry,*,placeholder:str='Search commands…',limit:int=20):
        self.registry=registry; self.limit=limit; ui=_ui(); self.dialog=ui.dialog()
        with self.dialog:
            with ui.element('section').classes('cui-command-palette cui-overlay-surface cui-overlay-surface--dialog').props('role="dialog" aria-modal="true" aria-label="Command palette"') as self.element:
                with ui.element('label').classes('cui-command-palette__search'):
                    _icon(ui,'search',size='xs')
                    self.search=ui.element('input').classes('cui-command-palette__search-input').props(
                        f'type="search" autocomplete="off" spellcheck="false" autofocus placeholder="{placeholder}" aria-label="Search commands" aria-controls="cui-command-palette-results"'
                    )
                    async def changed(e):
                        value=e.args if isinstance(getattr(e,'args',None),str) else ''
                        self._render_results(value)
                    async def search_key(e):
                        key=e.args if isinstance(getattr(e,'args',None),str) else ''
                        if key == 'Escape':
                            self.close()
                        elif key == 'ArrowDown':
                            ui.run_javascript("document.querySelector('.cui-command-palette__item:not([disabled])')?.focus()")
                    self.search.on('input',changed,throttle=.08,leading_events=False,trailing_events=True,js_handler='e => emit(e.target.value)')
                    self.search.on('keydown',search_key,js_handler='e => { if (e.key==="ArrowDown") { e.preventDefault(); emit(e.key); } else if (e.key==="Escape") { emit(e.key); } /* Wave 3.5: do not cancel Escape; allow native QDialog dismissal/focus restoration. */ }')
                    with ui.element('kbd').classes('cui-command-palette__escape').props('aria-hidden="true"'):
                        ui.label('ESC')
                self.results=ui.element('div').classes('cui-command-palette__results').props('id="cui-command-palette-results" role="listbox" aria-label="Commands"')
        # Escape is part of the keyboard contract regardless of which palette child owns focus.
        self.element.on('keydown.escape', lambda _e: self.close())
        self._render_results('')
    def open(self):
        self.dialog.open()
        _ui().run_javascript("requestAnimationFrame(()=>document.querySelector('.cui-command-palette__search-input')?.focus())")
        return self
    def close(self):
        self.dialog.close(); return self
    def _render_results(self,query:str):
        ui=_ui(); self.results.clear()
        with self.results:
            commands=self.registry.search(query,limit=self.limit)
            if not commands:
                with ui.element('div').classes('cui-command-palette__empty').props('role="status"'):
                    ui.label('No matching commands').classes('cui-search-result__subtitle')
                return
            for command in commands:
                async def run(e=None,c=command):
                    self.close()
                    await _invoke(lambda: self.registry.execute(c.key))
                async def item_key(e,c=command):
                    key=e.args if isinstance(getattr(e,'args',None),str) else ''
                    if key == 'Escape':
                        self.close(); return
                    direction = 1 if key == 'ArrowDown' else -1 if key == 'ArrowUp' else 0
                    if direction:
                        ui.run_javascript(f"""(() => {{ const items=[...document.querySelectorAll('.cui-command-palette__item:not([disabled])')]; const i=items.indexOf(document.activeElement); if(!items.length)return; items[(i+{direction}+items.length)%items.length].focus(); }})()""")
                props=f'type="button" role="option" aria-label="{command.label}" aria-disabled="{str(not command.is_enabled).lower()}"'
                button=ui.element('button').classes('cui-command-palette__item').props(props).on('click',run)
                button.on('keydown',item_key,js_handler='e => { if (e.key==="ArrowDown"||e.key==="ArrowUp") { e.preventDefault(); emit(e.key); } else if (e.key==="Escape") { emit(e.key); } }')
                if not command.is_enabled: button.props('disabled')
                with button:
                    with ui.element('span').classes('cui-command-palette__item-copy'):
                        ui.label(command.label).classes('cui-command-palette__label')
                        detail=command.description or (command.group if command.group and command.group != 'General' else None)
                        if detail: ui.label(detail).classes('cui-command-palette__group')
                    if command.shortcut:
                        with ui.element('kbd').classes('cui-command-palette__shortcut'):
                            ui.label(command.shortcut)


class BackgroundTaskIndicator:
    def __init__(self,label:str,*,progress:float|None=None,status:str='running',detail:str|None=None,on_cancel:Callable[...,Any]|None=None):
        self.spec=BackgroundTaskSpec(label,progress,status,detail); ui=_ui()
        with ui.element('section').classes('cui-background-task').props('role="status" aria-live="polite"') as self.element:
            if status=='running':ui.spinner(size='sm').classes('cui-spinner')
            else:_icon(ui,'check' if status=='complete' else 'warning',size='sm')
            with ui.element('div').classes('cui-background-task__copy'):
                ui.label(label).classes('cui-background-task__label')
                if detail:ui.label(detail).classes('cui-background-task__detail')
                if progress is not None:
                    from nicegui_base.integrations.nicegui_interactions import ProgressBar
                    ProgressBar(value=progress, label=label)
            if on_cancel:
                b=ui.button(on_click=on_cancel).props('flat round aria-label="Cancel task"').classes('cui-icon-button')
                with b:_icon(ui,'close',label='Cancel task')



class NotificationCenter:
    def __init__(self, notifications: Sequence[Any] = (), *, empty_message: str = 'No notifications'):
        self.notifications=tuple(notifications); ui=_ui()
        with ui.element('section').classes('cui-notification-center').props('aria-label="Notifications"') as self.element:
            if not self.notifications:
                ui.label(empty_message).classes('cui-search-result__subtitle')
            for notification in reversed(self.notifications):
                intent=getattr(getattr(notification,'intent',None),'value',getattr(notification,'intent','info')) or 'info'
                message=str(getattr(notification,'message',notification))
                icon={'success':'check','warning':'warning','danger':'error','info':'info'}.get(str(intent),'info')
                with ui.element('article').classes(f'cui-notification-item is-{intent}').props('role="status"'):
                    _icon(ui,icon,size='sm')
                    with ui.element('div'):
                        ui.label(message).classes('cui-notification-item__title')
                        duration=getattr(notification,'duration_ms',None)
                        if duration: ui.label(f'Displayed for {duration/1000:g}s').classes('cui-notification-item__detail')


class ActivityFeed:
    def __init__(self, items: Sequence[ActivityItem], *, empty_message: str='No recent activity'):
        self.items=tuple(items); ui=_ui()
        with ui.element('section').classes('cui-activity-feed').props('aria-label="Activity"') as self.element:
            if not items: ui.label(empty_message).classes('cui-search-result__subtitle')
            for item in items:
                with ui.element('article').classes(f'cui-activity-item is-{item.intent.value}'):
                    _icon(ui,item.icon or 'history',size='sm')
                    with ui.element('div'):
                        ui.label(item.title).classes('cui-activity-item__title')
                        if item.detail: ui.label(item.detail).classes('cui-activity-item__detail')
                        meta=' · '.join(x for x in (item.actor,item.timestamp) if x)
                        if meta: ui.label(meta).classes('cui-activity-item__meta')

__all__=[
 'DeltaIndicator','TrendIndicator','MetricCard','MetricStrip','ProgressMetric','ComparisonMetric','KeyValueList','DescriptionList',
 'PropertyGrid','EntityHeader','TreeView','MarkdownViewer','CodeViewer','JsonViewer','LogViewer','ImageViewer','SearchResults',
 'ProgressSteps','Stepper','ComparePanel','BeforeAfter','DifferenceTable','CommandPalette','BackgroundTaskIndicator','NotificationCenter','ActivityFeed'
]
