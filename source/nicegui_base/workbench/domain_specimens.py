"""Small canonical engineering and interaction examples, with explicit sample evidence."""
from __future__ import annotations
from datetime import datetime
import math

ENGINEERING_KEYS = frozenset({
    'EngineeringEntityCard','EngineeringStatusBadge','SpecLimitIndicator','OutOfSpecIndicator',
    'BaselineComparison','ProcessTrendSpec','DistributionComparisonSpec','PopulationComparisonPanel',
    'CommonalityTable','EvidenceCard','ConfidenceIndicator','RcaEvidencePanel','RcaWorkspaceSpec','EngineeringTimeline',
})
INTERACTION_KEYS = frozenset({'form','filter_bar','filter_drawer','detail_drawer','form_drawer','dialog',
                            'danger_dialog','popover','menu','toast','alert','banner','state_view','async_content'})


def render_engineering(key, *, title, on_event=None):
    from nicegui import ui
    from nicegui_base import engineering as m
    from nicegui_base.integrations import nicegui_engineering as v
    if key not in ENGINEERING_KEYS: raise KeyError(key)
    ui.label('Synthetic engineering example — evidence and confidence below are illustrative, not production conclusions.').classes('cui-workbench-note')
    entity=m.EngineeringEntityRef(m.EngineeringEntityKind.CHAMBER,'ETCH-021/CH-3','ETCH-021 · Chamber 3',m.EngineeringStatus.WATCH,'Etch critical dimension')
    limits=m.LimitBand(lower_spec=37.5,upper_spec=42.5,target=40.0,lower_warning=38.2,upper_warning=41.8,unit='nm')
    evidence=(m.EvidenceItem('e1','Illustrative SPC shift',m.EvidenceChannel.SPC,m.EvidenceDirection.SUPPORTS,m.EvidenceStrength.MODERATE,'Synthetic data, not causal proof','Example'),
              m.EvidenceItem('e2','Control tool shares recipe',m.EvidenceChannel.ROUTING,m.EvidenceDirection.CONTRADICTS,m.EvidenceStrength.MODERATE,'Keep contradictions visible','Example'))
    hypothesis=m.RcaHypothesis('h1','Example chamber hypothesis','Demonstration only',evidence=evidence,
                               confidence=m.ConfidenceIndicatorSpec(m.ConfidenceLevel.MODERATE,.5,'Uncalibrated synthetic example'))
    if key=='EngineeringEntityCard': return v.EngineeringEntityCard(m.EngineeringEntityCardSpec(entity,properties=(('Recipe','ETCH_R18'),('Population','Synthetic'))))
    if key=='EngineeringStatusBadge': return v.EngineeringStatusBadge(m.EngineeringStatus.WATCH)
    if key=='SpecLimitIndicator': return v.SpecLimitIndicator(40.1,limits=limits)
    if key=='OutOfSpecIndicator': return v.OutOfSpecIndicator(43.1,limits=limits)
    if key=='BaselineComparison': return v.BaselineComparison(m.BaselineComparison(42.18,40.06,'nm',higher_is_better=False))
    if key=='ConfidenceIndicator': return v.ConfidenceIndicator(m.ConfidenceIndicatorSpec(m.ConfidenceLevel.MODERATE,.5,'Demonstration, not probability',calibrated_probability=False))
    if key=='EvidenceCard': return v.EvidenceCard(m.EvidenceCardSpec(evidence[0]))
    if key in {'RcaEvidencePanel','RcaWorkspaceSpec'}:
        if key=='RcaWorkspaceSpec':
            ui.label('RcaWorkspaceSpec is a composition model; this panel demonstrates one candidate hypothesis.').classes('cui-workbench-note')
        return v.RcaEvidencePanel(m.RcaEvidencePanelSpec(hypothesis))
    if key=='ProcessTrendSpec':
        points=tuple(m.MeasurementPoint(f'W{i:02d}',40+math.sin(i/2.4)*.7) for i in range(1,25))
        return v.EngineeringProcessTrend(m.ProcessTrendSpec('CD',points,'nm',limits,m.ControlLimits(38.4,41.6,40),title=title))
    if key in {'DistributionComparisonSpec','PopulationComparisonPanel'}:
        return v.PopulationComparisonPanel(m.DistributionComparisonSpec(tuple(41.2+math.sin(i)*.55 for i in range(42)),tuple(39.8+math.sin(i*.8)*.42 for i in range(64)),'CD','nm'))
    if key=='CommonalityTable':
        observations=(m.CommonalityObservation('ch3','Chamber 3',m.CommonalityKind.CHAMBER,73,84,26,215,interpretation=m.CommonalityInterpretation.OBSERVED),)
        return v.CommonalityTable(m.CommonalityTableSpec(observations))
    if key=='EngineeringTimeline':
        return v.EngineeringTimeline((m.EngineeringTimelineEvent(datetime(2026,9,5,9,30),'Example inspection','Synthetic event',m.EngineeringStatus.WATCH,entity),))
    raise AssertionError(key)


def render_interaction(key, *, title, on_event=None):
    from nicegui import ui
    from nicegui_base.integrations import nicegui_interactions as v
    from nicegui_base.integrations.nicegui_components import Button, TextInput
    from nicegui_base.feedback import FeedbackIntent, StateViewSpec, StateKind, AsyncState
    from nicegui_base.filters import FilterBarSpec, FilterDefinition, FilterKind
    from nicegui_base.overlays import MenuItemSpec
    if key not in INTERACTION_KEYS: raise KeyError(key)
    def emit(message):
        if on_event: on_event(message)
    if key in {'dialog','danger_dialog'}:
        if key=='dialog':
            dialog=v.Dialog(title,description='Demonstration dialog; no production records are changed.',primary_label='Confirm',on_primary=lambda:emit('Dialog confirmed'))
        else:
            dialog=v.DangerConfirmDialog(title,description='Demonstration only; no data is deleted.',typed_confirmation='DELETE',on_confirm=lambda:emit('Demonstration deletion confirmed'))
        Button('Open dialog',on_click=dialog.open)
        return dialog
    if key in {'filter_drawer','detail_drawer','form_drawer'}:
        cls={'filter_drawer':v.AdvancedFilterDrawer,'detail_drawer':v.DetailDrawer,'form_drawer':v.FormDrawer}[key]
        drawer=cls(title)
        with drawer:
            TextInput('Lot',value='LOT-2409')
            Button('Close',on_click=drawer.close)
        Button('Open drawer',on_click=drawer.open)
        return drawer
    if key=='form':
        with v.Form('catalog-demo',title=title):
            field=TextInput('Lot ID',value='LOT-2409')
            status=ui.label('No changes saved.')
            def save():
                text=str(field.element.value or '').strip()
                status.set_text('Enter a lot ID.' if not text else f'Example saved: {text}')
                if text: emit(f'Example saved: {text}')
            Button('Save example',on_click=save)
        return
    if key=='filter_bar':
        return v.FilterBar(FilterBarSpec((FilterDefinition('tool','Tool',FilterKind.TEXT),)))
    if key=='popover':
        button=Button('Show details')
        with button.element:
            with v.Popover(title=title):
                ui.label('Contextual information for the selected item.')
        return
    if key=='menu':
        button=Button('Open actions')
        with button.element:
            return v.ActionMenu((MenuItemSpec('refresh','Refresh',on_select=lambda:emit('Refresh selected')),))
    if key=='toast':
        return Button('Show notification',on_click=lambda:v.Toast('Example operation complete',intent=FeedbackIntent.SUCCESS).show())
    if key in {'alert','banner'}:
        return (v.Alert if key=='alert' else v.Banner)(title,message='Synthetic warning. Your data has not been modified.',intent=FeedbackIntent.WARNING)
    if key=='state_view':
        return v.StateView(StateViewSpec(StateKind.EMPTY,title='No records',message='Add data to begin.'))
    if key=='async_content':
        status={'loaded':False}
        host=ui.element('div')
        def render():
            host.clear()
            with host:
                v.AsyncContent(AsyncState.READY if status['loaded'] else AsyncState.LOADING,content=lambda:ui.label('Example data loaded'))
        def load():
            status['loaded']=True; render(); emit('Example data loaded')
        render(); Button('Complete simulated load',on_click=load)
        return
    raise AssertionError(key)
