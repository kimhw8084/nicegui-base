"""One preview/export dispatch over the canonical catalog. Never embeds lab iframes."""
from __future__ import annotations
import json
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from .models import WorkbenchKind
from .preview_data import checked_rows, numeric_data

CONTENT_DATA_KEYS = frozenset({'metric_card','metric_strip','comparison_metric','key_value_list','property_grid','json_viewer','log_viewer'})


@lru_cache(maxsize=1)
def entries_by_key():
    from .registry_adapters import build_registry_entries
    return {entry.key:entry for entry in build_registry_entries()}


def describe_entry(entry):
    """Return an explicit presentation class, not a readiness score."""
    metadata=entry.metadata; registry=str(metadata.get('registry_name','')); key=str(metadata.get('registry_key',''))
    if entry.kind is WorkbenchKind.COMPONENT: mode='component'
    elif entry.kind is WorkbenchKind.ANALYTIC:
        from .analytic_specimens import DATA_SURFACES
        mode='analytical_data' if metadata.get('surface_key') in DATA_SURFACES else 'analytical_sample'
    elif entry.kind is WorkbenchKind.PATTERN: mode='pattern'
    elif entry.kind is WorkbenchKind.RECIPE: mode='recipe_reference'
    elif registry in {'content','tables','visualizations','engineering','interactions','icons','illustrations'}: mode=registry
    else: mode='reference'
    rows=(mode in {'tables','visualizations','pattern','analytical_data'} or mode=='content' and key in CONTENT_DATA_KEYS)
    contract = entry.reference_contract
    return {
        'key': entry.key, 'mode': mode, 'uses_rows': rows,
        'runnable': mode not in {'reference', 'recipe_reference'},
        'sample_only': mode in {'analytical_sample', 'engineering'}, 'title': entry.title,
        'live_example': contract.live_example,
        'reference_contract': contract.to_dict(),
    }


def supported_options(entry):
    info=describe_entry(entry)
    if info['mode'] in {'visualizations','analytical_data'}: return ('measurement',)
    if info['mode']=='tables': return ('selection',)
    if info['mode']=='component' and entry.metadata.get('component_key') in {'button','action_button','text_input','number_input','textarea','search_input','select','checkbox','switch','slider'}:
        return ('disabled',)
    return ()


def example_rows(entry):
    if not describe_entry(entry)['uses_rows']: return ()
    from .data_dock import DEFAULT_ENGINEERING_SAMPLE
    return tuple(dict(row) for row in DEFAULT_ENGINEERING_SAMPLE)


def _render_content(key, title, rows, options, on_event):
    from nicegui_base.integrations.nicegui_content import PropertyGrid, KeyValueList, MetricCard, MetricStrip, ComparisonMetric, JsonViewer, LogViewer
    from nicegui_base.content import KeyValueItem
    from .framework_specimens import render_framework_specimen
    if key in {'key_value_list','property_grid'}:
        items=tuple(KeyValueItem(str(k),str(k).replace('_',' ').title(),str(v),copyable=True) for k,v in (rows[0] if rows else {'status':'No data'}).items())
        return (PropertyGrid if key=='property_grid' else KeyValueList)(items)
    if key=='metric_card':
        return MetricCard(title,len(rows),delta='rows in the current development dataset')
    if key=='metric_strip':
        with MetricStrip():
            MetricCard('Rows',len(rows));MetricCard('Columns',len(rows[0]) if rows else 0)
        return
    if key=='comparison_metric':
        return ComparisonMetric('Row count',len(rows),baseline=0,delta=f'+{len(rows)}')
    if key=='json_viewer': return JsonViewer(list(rows))
    if key=='log_viewer': return LogViewer(tuple(json.dumps(row,ensure_ascii=False,default=str) for row in rows))
    return render_framework_specimen('content',key,on_event=on_event)


def render_catalog_example(
    entry_key: str,
    *,
    title: str | None = None,
    rows=None,
    options=None,
    on_event=None,
    show_reference=False,
    schema=None,
    measurement_field=None,
    category_field=None,
):
    from nicegui import ui
    from .specimen_css import install_specimen_css
    install_specimen_css()
    from nicegui_base.integrations.nicegui_components import Button
    entry=entries_by_key().get(entry_key)
    if entry is None: raise KeyError(f'Unknown canonical capability {entry_key!r}')
    info=describe_entry(entry); mode=info['mode']; title=title or entry.title; options=dict(options or {})
    if measurement_field and not options.get('measurement'):
        options['measurement'] = measurement_field
    if category_field and not options.get('label_field'):
        options['label_field'] = category_field
    data=checked_rows(example_rows(entry) if rows is None else rows)
    registry=str(entry.metadata.get('registry_name','')); key=str(entry.metadata.get('registry_key',''))
    with ui.element('section').classes('cui-catalog-specimen').props(
        'data-catalog-key='+json.dumps(entry.key)+' data-preview-mode='+json.dumps(mode)):
        if mode=='component':
            from .component_specimens import render_component_specimen
            return render_component_specimen(str(entry.metadata['component_key']),on_event=on_event,disabled=bool(options.get('disabled',False)))
        if mode=='content': return _render_content(key,title,data,options,on_event)
        if mode=='visualizations':
            from .visual_specimens import render_visualization
            return render_visualization(
                key, title=title, rows=data, options=options, on_event=on_event,
                schema=schema, measurement_field=measurement_field, category_field=category_field,
            )
        if mode=='tables':
            from .visual_specimens import render_table
            return render_table(key,title=title,rows=data,options=options,on_event=on_event)
        if mode in {'icons','illustrations'}:
            from nicegui_base.integrations.nicegui_visual_assets import SvgIcon,StateIllustration
            return SvgIcon(key,label=entry.title) if mode=='icons' else StateIllustration(key,label=entry.title)
        if mode=='engineering':
            from .domain_specimens import render_engineering
            return render_engineering(key,title=title,on_event=on_event)
        if mode=='interactions':
            from .domain_specimens import render_interaction
            return render_interaction(key,title=title,on_event=on_event)
        if mode=='pattern':
            from .pattern_specimens import render_pattern
            render_pattern(str(entry.metadata['pattern_key']),title=title,rows=data,on_event=on_event)
        elif mode in {'analytical_sample','analytical_data'}:
            from .analytic_specimens import render_analytic
            with ui.element('div').classes('cui-semantic-visual-example').props(
                'data-visual-semantic=' + json.dumps(str(entry.metadata['surface_key']))
            ):
                render_analytic(str(entry.metadata['surface_key']),entry.category,title=title,rows=data,options=options)
        else:
            from nicegui_base.integrations.nicegui_content import JsonViewer
            ui.label('Explicit nonvisual variant · No live visual required · typed contract reference').classes('cui-workbench-section-title')
            ui.label(entry.reference_contract.nonvisual_variant or entry.description).classes('cui-workbench-note')
            JsonViewer(entry.reference_contract.to_dict())
        reference=entry.metadata.get('full_reference_route') or entry.metadata.get('legacy_route')
        if show_reference and isinstance(reference,str) and reference.startswith('/') and not reference.startswith('//'):
            Button('Open full reference app',on_click=lambda:ui.navigate.to(reference))
