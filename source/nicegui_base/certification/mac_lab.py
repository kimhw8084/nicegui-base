from __future__ import annotations

import asyncio
import csv
import io
import json
import math
import random
import time
from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Callable
from urllib.parse import quote

from nicegui_base.components import ButtonIntent, ComponentSize, DataQuality, SelectOption, StatusIntent
from nicegui_base.content import ActivityItem, ComparisonItem, KeyValueItem, SearchResultSpec, StepSpec, StepState, TreeNode, TrendDirection
from nicegui_base.data_table import (
    BulkAction, ColumnKind, ConditionalRule, EditableTableSpec, FilterOperator, PinPosition, RowAction, SelectionMode, TableColumn, TableDensity, TablePreset, TableQuery, TableResult,
)
from nicegui_base.forms import ValidationIssue, ValidationSummarySpec
from nicegui_base.engineering import (
    BaselineComparison as BaselineModel,
    CommonalityInterpretation,
    CommonalityTableSpec,
    CommonalityKind,
    CommonalityObservation,
    ConfidenceIndicatorSpec,
    ConfidenceLevel,
    ControlLimits,
    DistributionComparisonSpec,
    EngineeringEntityCardSpec,
    EngineeringEntityKind,
    InvestigationContextSpec,
    EngineeringEntityRef,
    EngineeringStatus,
    EngineeringTimelineEvent,
    EvidenceCardSpec,
    EvidenceChannel,
    EvidenceDirection,
    EvidenceItem,
    EvidenceStrength,
    LimitBand,
    MeasurementPoint,
    ProcessTrendSpec,
    RcaEvidencePanelSpec,
    RcaHypothesis,
)
from nicegui_base.feedback import AsyncState, FeedbackIntent, StateKind, StateViewSpec, ToastSpec
from nicegui_base.filters import ActiveFilter, FilterBarSpec, FilterDefinition, FilterKind, FilterPreset, SavedFilterView as SavedFilterViewSpec
from nicegui_base.integrations.nicegui_components import (
    Accordion, ActionButton, Autocomplete, Button, ButtonGroup, Card, Checkbox, CheckboxGroup, Chip, CollapsiblePanel,
    Combobox, CountBadge, DataQualityBadge, DatePicker, DateRangePicker, DateTimePicker, Divider, FileUpload,
    FreshnessIndicator, IconButton, InteractiveCard, MultiSelect, NumberInput, Panel, PasswordInput, RadioGroup,
    RangeSlider, SearchInput, Select, SeverityIndicator, Slider, SplitButton, StatusBadge, Switch, Tag, TextArea,
    TextInput, TimePicker, Well,
)
from nicegui_base.integrations.nicegui_content import (
    ActivityFeed, BackgroundTaskIndicator, BeforeAfter, CommandPalette, ComparePanel, ComparisonMetric, DeltaIndicator, DescriptionList,
    DifferenceTable, EntityHeader, ImageViewer, JsonViewer, KeyValueList, LogViewer, MarkdownViewer, MetricCard,
    MetricStrip, NotificationCenter, ProgressMetric, ProgressSteps, PropertyGrid, SearchResults, Stepper, TrendIndicator, TreeView,
)
from nicegui_base.integrations.nicegui_data_table import (
    ConditionalCellFormatter, DataTable, EditableTable, ExpandableRow, MasterDetailTable, ServerDataTable, SparklineCell, StatusCell,
    TableColumnManager, TableContextMenu, TableDensitySelector, TablePresetSelector, TableRowActions, TableSelectionBar, TableToolbar, apply_all_table_density,
)
from nicegui_base.integrations.nicegui_engineering import (
    BaselineComparison, ConfidenceIndicator, EngineeringEntityCard, EngineeringProcessTrend, InvestigationContextBar, EngineeringStatusBadge,
    CommonalityTable, EngineeringTimeline, EvidenceCard, OutOfSpecIndicator, PopulationComparisonPanel, RcaEvidencePanel, SpecLimitIndicator,
)
from nicegui_base.integrations.nicegui_interactions import (
    ActionMenu, ActivityDrawer, AdvancedFilterDrawer, Alert, AsyncContent, Banner, ConfirmDialog, ContextMenu, DangerConfirmDialog, DetailDrawer,
    Dialog, DirtyStateGuard, DropdownMenu, EmptyState, ErrorState, FilterBar, FilterChip, FilterDrawer, FilterPresetSelector, Form, FormActions, FormDialog, FormDrawer, FormField, FormSection, FullScreenDialog, InspectorDrawer,
    NoResultsState, NotFoundState, OfflineState, PermissionDeniedState, Popover, PreviewDialog, ProgressBar, ResponsiveDrawer, SavedFilterView, Skeleton, Spinner, StateView, Toast, Tooltip, ValidationMessage, ValidationSummary,
)
from nicegui_base.integrations.nicegui_layout import AppHeader, AppInfoDialog, AppShell, AppSidebar, BackNavigation, EnvironmentBadge, MobileNavigationDrawer, PageHeader, PageNavigation, SegmentedControl, Tabs, UserMenu
from nicegui_base.integrations.nicegui_theme import install_framework_css
from nicegui_base.integrations.nicegui_visual_assets import StateIllustration, SvgIcon
from nicegui_base.integrations.nicegui_visualization import (
    AreaChart, BarChart, BoxPlot, ChartBrush, ChartCrossFilter, ChartDataView, ChartExport, ChartFullscreen, ChartLegend, ChartPanel, ChartSelection, ChartToolbar, ChartTooltip, ChartZoom,
    ControlChart, DistributionPanel, DonutChart, Gauge, Heatmap, Histogram, LineChart, ParetoChart, PlotlyPanel, ProcessTrendPanel, ScatterChart, SpatialMap,
    StackedBarChart, TimelineChart, WaferMap, WaferComparisonMap, ChamberFingerprintMatrix, CommonalityMatrix, RadialProfilePlot, apply_all_chart_themes,
)
from nicegui_base.layouts import ActionRow, AlertStack, ButtonCluster, ContentColumn, FormStack, LayoutSlot, SurfaceGrid, ToolbarGroup
from nicegui_base.overlays import MenuItemSpec
from nicegui_base.navigation import NavigationModel, NavItem, NavSection, TabSpec
from nicegui_base.patterns import (
    AnalysisWorkspacePage, ComparisonPage, CrudPage, DashboardPage, DataExplorerPage, MasterDetailPage, MonitoringPage,
    SearchPage, SettingsPage, WizardPage, PatternSurface,
)
from nicegui_base.services import Command, CommandRegistry
from nicegui_base.visual import Icons, Illustrations
from nicegui_base.visualization import AxisSpec, AxisType, SeriesSpec, SpatialPoint, SpecLimits, WaferPoint
from nicegui_base.version import FRAMEWORK_VERSION

from .mac_lab_css import build_mac_lab_css

LAB_TITLE = 'NiceGUI Base — Linux Reference Lab'
LAB_APP_TITLE = 'NiceGUI Base Reference System'
LAB_APP_SUBTITLE = 'Enterprise engineering application framework'
LAB_VERSION = FRAMEWORK_VERSION
LAB_PORT = 8080


LAB_NAVIGATION = NavigationModel((
    NavSection('start', 'START', (
        NavItem('overview', 'Overview', '/', Icons.HOME),
        NavItem('foundation', 'Foundation', '/foundation', Icons.GRID),
        NavItem('shell_primitives', 'Shell Primitives', '/shell', Icons.SIDEBAR),
    )),
    NavSection('elements', 'ELEMENTS', (
        NavItem('controls', 'Controls', '/controls', Icons.SETTINGS),
        NavItem('forms', 'Forms & Overlays', '/forms', Icons.EDIT),
        NavItem('data', 'DataTable Lab', '/data', Icons.TABLE),
        NavItem('charts', 'Charts', '/charts', Icons.CHART_LINE),
        NavItem('content', 'Content & Workflow', '/content', Icons.FILE),
        NavItem('engineering', 'Engineering & RCA', '/engineering', Icons.WAFER),
    )),
    NavSection('patterns', 'REFERENCE APPS', (
        NavItem('dashboard', 'Dashboard', '/patterns/dashboard', Icons.CHART_BAR),
        NavItem('explorer', 'Data Explorer', '/patterns/explorer', Icons.SEARCH),
        NavItem('master_detail', 'Master / Detail', '/patterns/master-detail', Icons.SPLIT),
        NavItem('crud', 'CRUD', '/patterns/crud', Icons.EDIT),
        NavItem('monitoring', 'Monitoring', '/patterns/monitoring', Icons.ALARM),
        NavItem('search_pattern', 'Search', '/patterns/search', Icons.SEARCH),
        NavItem('settings_pattern', 'Settings', '/patterns/settings', Icons.SETTINGS),
        NavItem('wizard', 'Wizard', '/patterns/wizard', Icons.FORWARD),
        NavItem('comparison', 'Comparison', '/patterns/comparison', Icons.CORRELATION),
        NavItem('analysis', 'Analysis Workspace', '/patterns/analysis', Icons.RCA),
    )),
    NavSection('quality', 'QUALITY', (
        NavItem('states', 'State & Failure', '/states', Icons.WARNING),
        NavItem('performance', 'Performance', '/performance', Icons.DIAGNOSTICS),
    )),
))


@dataclass(frozen=True, slots=True)
class LabRoute:
    path: str
    label: str
    builder: Callable[[Any], None]


_REGISTERED = False
_LAB_CSS_INSTALLED = False


def _ui():
    from nicegui import ui
    return ui


def _lab_css() -> None:
    global _LAB_CSS_INSTALLED
    if _LAB_CSS_INSTALLED:
        return
    _ui().add_css(build_mac_lab_css(), shared=True)
    _LAB_CSS_INSTALLED = True


@contextmanager
def _section(title: str, description: str | None = None):
    ui = _ui()
    with ui.element('section').classes('cui-lab-section') as host:
        with ui.element('div').classes('cui-lab-section__head'):
            with ui.element('div'):
                ui.label(title).classes('cui-lab-section__title')
                if description:
                    ui.label(description).classes('cui-lab-section__description')
        yield host


@contextmanager
def _sample(title: str, *, span: int = 4, soft: bool = False):
    ui = _ui()
    cls = f'cui-lab-sample cui-lab-span-{span}' + (' cui-lab-sample--soft' if soft else '')
    with ui.element('section').classes(cls) as host:
        ui.label(title).classes('cui-lab-sample__title')
        yield host


def _grid():
    return _ui().element('div').classes('cui-lab-grid')


def _sync_theme(mode: str, dark: Any) -> None:
    ui = _ui()
    value = {'light': False, 'dark': True, 'system': None}[mode]
    if hasattr(dark, 'set_value'):
        dark.set_value(value)
    elif value is True:
        dark.enable()
    elif value is False:
        dark.disable()
    else:
        dark.auto()
    ui.run_javascript(f"document.documentElement.dataset.theme={mode!r};")
    if mode in {'light','dark'}:
        apply_all_chart_themes(mode)


def _control_bar() -> None:
    from nicegui import app, ui
    theme = str(app.storage.user.get('cui_lab_theme', 'system'))
    density = str(app.storage.user.get('cui_lab_density', 'compact'))
    motion = str(app.storage.user.get('cui_lab_motion', 'normal'))
    dark = ui.dark_mode()
    _sync_theme(theme, dark)
    ui.run_javascript(f"document.documentElement.dataset.density={density!r}; document.documentElement.dataset.motion={motion!r};")

    def theme_changed(e):
        value = str(getattr(e, 'value', 'system'))
        app.storage.user['cui_lab_theme'] = value
        _sync_theme(value, dark)

    async def density_changed(e):
        value = str(getattr(e, 'value', 'compact'))
        app.storage.user['cui_lab_density'] = value
        ui.run_javascript(f"document.documentElement.dataset.density={value!r};")
        await apply_all_table_density(value)

    def motion_changed(e):
        value = str(getattr(e, 'value', 'normal'))
        app.storage.user['cui_lab_motion'] = value
        ui.run_javascript(
            f"document.documentElement.dataset.motion={value!r}; document.documentElement.classList.toggle('cui-force-reduced-motion',{str(value == 'reduced').lower()});"
        )

    with ui.element('div').classes('cui-lab-controlbar').props('role="toolbar" aria-label="Live design controls"'):
        ui.label('Theme').classes('cui-lab-controlbar__label')
        SegmentedControl({'system': 'System', 'light': 'Light', 'dark': 'Dark'}, value=theme, on_change=theme_changed)
        ui.label('Density').classes('cui-lab-controlbar__label')
        SegmentedControl({'comfortable': 'Comfort', 'compact': 'Compact', 'dense': 'Dense'}, value=density, on_change=density_changed)
        ui.label('Motion').classes('cui-lab-controlbar__label')
        SegmentedControl({'normal': 'Normal', 'reduced': 'Reduced'}, value=motion, on_change=motion_changed)
        ui.element('div').classes('cui-lab-controlbar__spacer')
        ui.label('Resize the real browser window for responsive proof').classes('cui-lab-viewport-badge')


def _shell(route: str, title: str, description: str | None = None):
    shell = AppShell(
        LAB_APP_TITLE, LAB_NAVIGATION, active_route=route, environment='LINUX LAB',
        subtitle=LAB_APP_SUBTITLE, greeting='Good morning', user_name='Process Engineer', user_initials='PE',
        on_settings=lambda: _ui().navigate.to('/patterns/settings'), on_about=None,
        owner='NiceGUI Base / Metrology Engineering', on_support=lambda: _toast('Support contact opened'),
        on_feedback=lambda: _toast('VOC / feedback submission opened'), on_docs=lambda: _toast('Documentation opened'),
    )
    shell.__enter__()
    route_class = 'cui-lab-route-' + (route.strip('/').replace('/', '-') or 'overview')
    shell._lab_page = _ui().element('div').classes(f'cui-page cui-page--wide {route_class}')
    shell._lab_page.__enter__()
    PageHeader(title, description or 'Live NiceGUI Base acceptance surface')
    _control_bar()
    return shell


def _end_shell(shell: AppShell) -> None:
    page = getattr(shell, '_lab_page', None)
    if page is not None:
        page.__exit__(None, None, None)
    shell.__exit__(None, None, None)


def _toast(message: str, intent: FeedbackIntent = FeedbackIntent.INFO) -> None:
    Toast(message, intent=intent).show()


def _lab_table_density() -> TableDensity:
    from nicegui import app
    value = str(app.storage.user.get('cui_lab_density', TableDensity.COMPACT.value))
    try:
        return TableDensity(value)
    except ValueError:
        return TableDensity.COMPACT


def _deferred_lab_surface(title: str, description: str, builder: Callable[[], None], *, button_label: str = 'Load example') -> None:
    """Keep heavyweight lab-only stress surfaces out of the initial page lifecycle.

    The NiceGUI Base component itself is unchanged; this only prevents multiple AG Grid
    applications from running concurrently before the reviewer asks to inspect them.
    """
    ui = _ui()
    with ui.element('div').classes('cui-lab-deferred-wrap'):
        host = ui.element('div').classes('cui-lab-deferred-host')
        mounted = False

        def mount(e=None) -> None:
            nonlocal mounted
            if mounted:
                return
            mounted = True
            placeholder.set_visibility(False)
            with host:
                builder()

        with ui.element('div').classes('cui-lab-deferred') as placeholder:
            with ui.element('div').classes('cui-lab-deferred__copy'):
                ui.label(title).classes('cui-lab-deferred__title')
                ui.label(description).classes('cui-lab-deferred__description')
            Button(button_label, icon=Icons.FORWARD, on_click=mount)


def _deterministic_rows(count: int = 240) -> list[dict[str, Any]]:
    from nicegui_base.certification.pathological_data import engineering_rows
    return engineering_rows(count)


TABLE_COLUMNS = (
    TableColumn('id', 'Measurement', ColumnKind.TEXT, min_width=140, pinned=PinPosition.LEFT),
    TableColumn('lot', 'Lot', ColumnKind.TEXT, min_width=100),
    TableColumn('wafer', 'Wafer', ColumnKind.TEXT, min_width=82),
    TableColumn('tool', 'Tool', ColumnKind.TEXT, min_width=110),
    TableColumn('parameter', 'Parameter', ColumnKind.TEXT, min_width=120),
    TableColumn('value', 'Value', ColumnKind.FLOAT, decimals=3, min_width=100, rules=(
        ConditionalRule(FilterOperator.GT, 42.5, intent='danger'), ConditionalRule(FilterOperator.GT, 41.5, intent='warning'),
    )),
    TableColumn('status', 'Status', ColumnKind.STATUS, min_width=110),
    TableColumn('yield', 'Yield', ColumnKind.PERCENT, decimals=1, min_width=92),
    TableColumn('trend', 'Trend', ColumnKind.SPARKLINE, min_width=120, priority='low'),
    TableColumn('timestamp', 'Observed', ColumnKind.TEXT, min_width=150, priority='low'),
)


def _shell_primitives(_: Any = None) -> None:
    shell = _shell(
        '/shell', 'Shell Primitives',
        'One responsive navigation state machine: expanded desktop, icon-only desktop, or temporary mobile overlay.',
    )
    ui=_ui()
    with Panel():
        ui.label('Responsive navigation contract').classes('cui-lab-section__title')
        ui.label('Desktop has one collapse control inside the rail. Below 900px the rail is removed from interaction and one navigation trigger appears with the header actions — never beside the application title.').classes('cui-lab-section__description')
        with ui.element('div').classes('cui-lab-inline'):
            StatusBadge('Expanded desktop', intent=StatusIntent.SUCCESS)
            StatusBadge('Icon-only desktop', intent=StatusIntent.INFO)
            StatusBadge('Mobile overlay', intent=StatusIntent.WARNING)
        ui.label('Resize the browser to exercise the states. There is intentionally no standalone mobile-navigation demo action because that created a competing navigation system.').classes('cui-lab-type-caption')
    with Panel():
        ui.label('Header interaction contract').classes('cui-lab-section__title')
        ui.label('Application settings and user profile are real structured popovers. Settings navigates to the canonical settings workspace; the user control exposes identity and preferences instead of firing a toast-only action.').classes('cui-lab-section__description')
    Alert('Structural acceptance rule', message='Exactly one navigation affordance is interactive per viewport. Sidebar/footer compression, duplicate menu triggers, content underlap, or lost navigation after resize are release blockers.', intent=FeedbackIntent.INFO)
    _end_shell(shell)


def _overview(_: Any = None) -> None:
    ui = _ui(); shell = _shell('/', 'Overview')
    with ui.element('section').classes('cui-lab-hero'):
        with ui.element('div').classes('cui-lab-hero__copy'):
            ui.label('LIVE REFERENCE SYSTEM').classes('cui-lab-hero__eyebrow')
            ui.label('The executable encyclopedia for NiceGUI Base').classes('cui-lab-hero__title')
            ui.label('Every page in this lab renders the real NiceGUI-backed NiceGUI Base components using synthetic data. Resize the browser, switch theme and density, operate every control, and treat any visible stock NiceGUI/Quasar personality as a release defect.').classes('cui-lab-hero__body')
            with ButtonCluster():
                ActionButton('Open component controls', icon=Icons.SETTINGS, on_click=lambda: ui.navigate.to('/controls'))
                Button('Open DataTable lab', icon=Icons.TABLE, on_click=lambda: ui.navigate.to('/data'))
        with Panel():
            ui.label('Linux acceptance contract').classes('cui-lab-section__title')
            ui.label('The reference app is approved only when the real browser experience has no meaningful visual or interaction difference from the intended NiceGUI Base system.').classes('cui-lab-section__description')
            Divider()
            for label, value in (('Framework', FRAMEWORK_VERSION), ('NiceGUI', '3.15.0 exact pin'), ('Stock visual leaks', '0 required'), ('Primary browser', 'Chrome / Chromium'), ('Secondary browser', 'Microsoft Edge when installed')):
                with ui.element('div').classes('cui-lab-cert-row'):
                    ui.label(label).classes('cui-lab-cert-key'); StatusBadge('Required', intent=StatusIntent.SUCCESS); ui.label(value).classes('cui-lab-cert-detail')
    with MetricStrip():
        MetricCard('Semantic components', 314, delta='framework registry', icon=Icons.GRID)
        MetricCard('Local icons', 143, delta='zero CDN', icon=Icons.IMAGE)
        MetricCard('Automated tests', '427+', delta='pre-Linux baseline', intent=StatusIntent.SUCCESS, icon=Icons.CHECK)
        MetricCard('Visual leaks allowed', 0, delta='release blocker', intent=StatusIntent.DANGER, icon=Icons.SHIELD)
    sec = _section('How to review this app', 'Use the left navigation as a structured acceptance checklist. The lab deliberately includes good states, bad states, long content, missing data and failure scenarios.')
    with sec:
        with _grid():
            for title, body, icon in (
                ('Foundation', 'Colors, typography, spacing, radius, elevation, density and motion.', Icons.GRID),
                ('Element laboratory', 'Every control family in normal, disabled, error and edge states.', Icons.SETTINGS),
                ('Reference applications', 'Ten canonical patterns composed like realistic internal tools.', Icons.CHART_BAR),
                ('Failure states', 'Slow, stale, empty, offline, permission and error conditions.', Icons.WARNING),
            ):
                with _sample(title, span=3):
                    SvgIcon(icon, label=title)
                    ui.label(body).classes('cui-lab-section__description')
    _end_shell(shell)


def _foundation(_: Any = None) -> None:
    ui = _ui(); shell = _shell('/foundation', 'Foundation', 'Inspect the exact visual primitives from which every application is constructed.')
    sec = _section('Semantic color system', 'These are design roles, not a decorative palette. Apps should never invent independent visual colors.')
    with sec:
        with ui.element('div').classes('cui-lab-swatch-grid'):
            for name, token in (
                ('Page', '--cui-page'), ('Primary surface', '--cui-surface'), ('Secondary surface', '--cui-surface-secondary'),
                ('Elevated', '--cui-surface-elevated'), ('Accent', '--cui-accent'), ('Success', '--cui-success'), ('Warning', '--cui-warning'),
                ('Danger', '--cui-danger'), ('Info', '--cui-info'), ('Primary text', '--cui-text-primary'), ('Secondary text', '--cui-text-secondary'),
                ('Border', '--cui-border-default'),
            ):
                with ui.element('div').classes('cui-lab-swatch'):
                    ui.element('div').classes('cui-lab-swatch__color').style(f'--cui-lab-swatch:var({token})')
                    with ui.element('div').classes('cui-lab-swatch__copy'):
                        ui.label(name).classes('cui-lab-swatch__name'); ui.label(token).classes('cui-lab-swatch__token')
    sec = _section('Typography', 'Dense enterprise readability with restrained hierarchy and tabular numerics where values must scan precisely.')
    with sec:
        with _sample('Type scale', span=12):
            for cls, label in (
                ('cui-lab-type-display', 'Display — Strategic overview'), ('cui-lab-type-page', 'Page — Equipment Health'),
                ('cui-lab-type-heading', 'Heading — Affected population'), ('cui-lab-type-subheading', 'Subheading — Process context'),
                ('cui-lab-type-body', 'Body — Designed for compact, high-information internal applications without looking cramped.'),
                ('cui-lab-type-label', 'Label — CHAMBER'), ('cui-lab-type-caption', 'Caption — Updated 2 minutes ago'),
            ):
                ui.label(label).classes(cls)
    sec = _section('Spacing, radius and elevation', 'The lab exposes the token rhythm so visual drift becomes obvious.')
    with sec:
        with _grid():
            with _sample('Spacing rhythm', span=6):
                for name, width in (('XS','4px'),('SM','8px'),('MD','16px'),('LG','24px'),('XL','32px'),('2XL','48px')):
                    with ui.element('div').classes('cui-lab-spacing-row'):
                        ui.label(name).classes('cui-lab-token-code'); ui.element('span').classes('cui-lab-spacing-block').style(f'--cui-lab-space:{width}'); ui.label(width).classes('cui-lab-token-code')
            with _sample('Radii & surfaces', span=6):
                ui.label('Three rectangle families only: control · surface · overlay. Pill is reserved for tags/status.').classes('cui-lab-section__description')
                with ui.element('div').classes('cui-lab-radius-row'):
                    for name, token in (('Control','--cui-radius-control'),('Surface','--cui-radius-surface'),('Overlay','--cui-radius-overlay')):
                        with ui.element('div'):
                            ui.element('div').classes('cui-lab-radius').style(f'--cui-lab-radius:var({token})'); ui.label(name).classes('cui-lab-token-code')
                with SurfaceGrid():
                    with Well(): ui.label('Well').classes('cui-field-label'); ui.label('Secondary containment').classes('cui-lab-type-caption')
                    with Panel(): ui.label('Panel').classes('cui-field-label'); ui.label('Primary structural surface').classes('cui-lab-type-caption')
                    with Card(): ui.label('Card').classes('cui-field-label'); ui.label('Elevated emphasis surface').classes('cui-lab-type-caption')
    sec = _section('Motion system', 'Normal motion is subtle and functional; Reduced Motion removes travel while preserving visible state changes.')
    with sec:
        motion_status = ui.label('Ready · replay changes this status and the real application title.').classes('cui-motion-status')
        def replay_motion():
            motion_status.set_text('Replaying · title + samples are moving now')
            ui.run_javascript("""(() => {
              const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
              const nodes=[...document.querySelectorAll('.cui-motion-demo'),...document.querySelectorAll('.cui-shell-title')];
              nodes.forEach((e,i)=>{
                e.getAnimations().forEach(a=>a.cancel());
                const frames=reduced ? [{opacity:.45},{opacity:1}] : [{opacity:.18,transform:'translateY(12px) scale(.988)'},{opacity:1,transform:'none'}];
                e.animate(frames,{duration:reduced?260:520+i*45,easing:'cubic-bezier(.16,1,.3,1)'});
                e.classList.remove('is-replaying'); void e.offsetWidth; e.classList.add('is-replaying');
              });
              document.documentElement.dataset.motionReplay=String(Date.now());
            })()""")
            ui.timer(0.72, lambda: motion_status.set_text('Replay complete · switch Motion to Reduced and replay again.'), once=True)
        with ButtonCluster():
            Button('Replay motion examples', icon=Icons.PLAY, on_click=replay_motion, intent=ButtonIntent.PRIMARY)
            ui.label('Normal = short movement + opacity. Reduced = opacity/state only.').classes('cui-lab-type-caption')
        with ui.element('div').classes('cui-motion-demo-grid'):
            for label, cls in (('Title entrance','cui-motion-demo--title'),('Section reveal','cui-motion-demo--section'),('Selection feedback','cui-motion-demo--selection')):
                with ui.element('div').classes(f'cui-motion-demo {cls} is-replaying'):
                    ui.label(label).classes('cui-field-label'); ui.label('Purposeful · short · ease-out').classes('cui-lab-type-caption')
    sec = _section('Environment and semantic metadata', 'Environment treatments intentionally differ by operational risk while using the same badge grammar.')
    with sec:
        with ui.element('div').classes('cui-lab-inline'):
            EnvironmentBadge('development'); EnvironmentBadge('staging'); EnvironmentBadge('production')
    sec = _section('Icon grammar', 'All canonical UI icons are local project SVGs and inherit currentColor.')
    with sec:
        with _sample('Representative semantic icons', span=12):
            with ui.element('div').classes('cui-lab-inline'):
                for key in (Icons.SEARCH, Icons.FILTER, Icons.TABLE, Icons.CHART_LINE, Icons.WAFER, Icons.TOOL, Icons.RCA, Icons.EVIDENCE, Icons.WARNING, Icons.SUCCESS, Icons.SETTINGS, Icons.DOWNLOAD):
                    with ui.element('div').classes('cui-lab-icon-tile'):
                        SvgIcon(key, label=key.value); ui.label(key.value).classes('cui-lab-token-code')
    _end_shell(shell)


def _controls(_: Any = None) -> None:
    ui = _ui(); shell = _shell('/controls', 'Control Laboratory', 'Every primitive shown against normal, disabled, selected, error, long-content and compact conditions.')
    sec = _section('Buttons and action hierarchy')
    with sec:
        with _grid():
            with _sample('Intent hierarchy', span=6):
                with ui.element('div').classes('cui-lab-inline'):
                    Button('Primary', intent=ButtonIntent.PRIMARY); Button('Secondary', intent=ButtonIntent.SECONDARY); Button('Tertiary', intent=ButtonIntent.TERTIARY); Button('Ghost', intent=ButtonIntent.GHOST); Button('Danger', intent=ButtonIntent.DANGER)
                with ui.element('div').classes('cui-lab-inline'):
                    ActionButton('Save changes', icon=Icons.SAVE); ActionButton('Processing', loading=True); Button('Disabled', disabled=True)
            with _sample('Icon, group and split actions', span=6):
                with ui.element('div').classes('cui-lab-inline'):
                    IconButton(Icons.SEARCH, label='Search'); IconButton(Icons.REFRESH, label='Refresh'); IconButton(Icons.MORE_HORIZONTAL, label='More'); IconButton(Icons.DELETE, label='Delete', intent=ButtonIntent.DANGER)
                with ButtonGroup():
                    Button('Day'); Button('Week', intent=ButtonIntent.PRIMARY); Button('Month')
                SplitButton('Export', {'CSV': lambda: _toast('CSV export requested', FeedbackIntent.SUCCESS), 'JSON': lambda: _toast('JSON export requested')}, icon=Icons.EXPORT)
    sec = _section('Navigation controls', 'Tabs, segmented controls and user menus are especially important stock-Quasar leakage surfaces.')
    with sec:
        with _grid():
            with _sample('Tabs', span=7):
                tabs=(TabSpec('summary','Summary'),TabSpec('evidence','Evidence'),TabSpec('history','History'),TabSpec('disabled','Disabled',disabled=True))
                with Tabs(tabs) as tabset:
                    with tabset.panel('summary'): ui.label('Summary panel content')
                    with tabset.panel('evidence'): ui.label('Evidence panel content')
                    with tabset.panel('history'): ui.label('History panel content')
                    with tabset.panel('disabled'): ui.label('Disabled')
            with _sample('Segmented + user menu', span=5):
                SegmentedControl({'trend':'Trend','table':'Table','split':'Split'},value='trend')
                UserMenu('PE',on_preferences=lambda:_toast('Preferences'),on_about=lambda:_toast(f'NiceGUI Base {FRAMEWORK_VERSION}'),on_logout=lambda:_toast('Sign-out demo'))
                about=AppInfoDialog('NiceGUI Base Linux Lab',LAB_VERSION,environment='LINUX LAB')
                Button('About this lab',icon=Icons.INFO,on_click=about.open)
    sec = _section('Page navigation helpers', 'Back/next navigation uses the same semantic button and SVG vocabulary.')
    with sec:
        with ui.element('div').classes('cui-lab-stack'):
            BackNavigation('Back to overview', on_click=lambda: ui.navigate.to('/'))
            PageNavigation(previous=('Previous page', lambda: _toast('Previous')), next=('Next page', lambda: _toast('Next')))
    sec = _section('Status and metadata')
    with sec:
        with _sample('Badges, tags and quality', span=12):
            with ui.element('div').classes('cui-lab-inline'):
                StatusBadge('Normal', intent=StatusIntent.SUCCESS, icon=Icons.CHECK); StatusBadge('Watch', intent=StatusIntent.WARNING, icon=Icons.WARNING); StatusBadge('Critical', intent=StatusIntent.DANGER, icon=Icons.ERROR); StatusBadge('Maintenance', intent=StatusIntent.INFO)
                Tag('Recipe R18'); Chip('ETCH-021', selected=True, icon=Icons.TOOL); CountBadge(1287); SeverityIndicator('High severity', intent=StatusIntent.DANGER); FreshnessIndicator('2m ago'); FreshnessIndicator('47m ago', stale=True); DataQualityBadge(DataQuality.COMPLETE)
    sec = _section('Inputs and selections')
    with sec:
        options=(SelectOption('etch','ETCH'),SelectOption('cvd','CVD'),SelectOption('cmp','CMP'),SelectOption('pvd','PVD'))
        with _grid():
            with _sample('Text fields', span=6):
                TextInput('Tool ID', value='ETCH-021', description='Stable field anatomy')
                SearchInput('Search measurements', placeholder='Lot, tool, parameter…')
                PasswordInput('Credential', value='••••••••', readonly=True)
                NumberInput('Upper limit', value=42.75, unit='nm', required=True)
                TextArea('Investigation note', value='Observed spatial signature is strongest on the wafer edge.', rows=3)
            with _sample('Validation and disabled states', span=6):
                TextInput('Required parameter', value='', required=True, error='Parameter is required')
                TextInput('Read-only source', value='SPC-SYSTEM', readonly=True)
                TextInput('Disabled field', value='Unavailable', disabled=True)
                NumberInput('Out-of-range value', value=51.2, error='Must be ≤ 50.0')
            with _sample('Select family', span=6):
                Select('Area', options, value='etch')
                MultiSelect('Processes', options, value=('etch','cvd'), searchable=True)
                Autocomplete('Tool family', options, value='etch')
                Combobox('Tag or create', options)
            with _sample('Choice family', span=6):
                Checkbox('Include maintenance windows', checked=True)
                Checkbox('Disabled choice', disabled=True)
                CheckboxGroup('Evidence channels', options, selected=('etch','cmp'))
                RadioGroup('Population', options, selected='cvd')
                Switch('Auto refresh', checked=True); Switch('Unavailable switch', disabled=True)
            with _sample('Range and temporal', span=6):
                Slider('Confidence threshold', value=72, minimum=0, maximum=100)
                RangeSlider('Measurement window', low=38, high=44, minimum=30, maximum=50, step=.5, unit='nm')
                DatePicker('Start date', value='2026-08-20'); TimePicker('Review time', value='09:30'); DateTimePicker('Event time', value='2026-08-25T09:30')
            with _sample('Date range & upload', span=6):
                DateRangePicker('Investigation period', start='2026-08-18', end='2026-08-25')
                FileUpload(label='Attach evidence', accept=('.csv','.json','.png'), multiple=True, max_files=3)
    sec = _section('Surfaces and disclosure')
    with sec:
        with _grid():
            with _sample('Surfaces', span=6):
                with Panel(): ui.label('Panel — stable primary container')
                with Card(interactive=True): ui.label('Card — elevated emphasis')
                with InteractiveCard(selected=False, on_click=lambda *_: _toast('Interactive card selection toggled', FeedbackIntent.SUCCESS)):
                    ui.label('Interactive card — click to toggle selection').classes('cui-field-label')
                    ui.label('Hover, focus and selected states are all visibly distinct.').classes('cui-field-description')
                with Well(): ui.label('Well — secondary containment')
            with _sample('Disclosure', span=6):
                with CollapsiblePanel('Advanced settings', open=True): ui.label('The expansion header, icon, spacing and animation must remain Company-owned.')
                with Accordion('Secondary section'): ui.label('Collapsed by default')
    _end_shell(shell)


def _forms(_: Any = None) -> None:
    ui = _ui(); shell = _shell('/forms', 'Forms, Overlays & Feedback', 'Exercise real form anatomy, dirty state, dialogs, drawers, menus, progress, alerts and failure recovery.')
    sec = _section('Production form')
    with sec:
        form = Form('equipment-settings', title='Equipment settings')
        with form:
            with FormSection('Routing', description='Changes here are intentionally marked dirty for navigation protection.'):
                tool = Select('Preferred tool', {'etch-14':'ETCH-014','etch-21':'ETCH-021'}, value='etch-21')
                recipe = TextInput('Recipe', value='ETCH_R18', required=True)
                auto = Switch('Automatic dispatch', checked=True)
                form.bind_dirty(tool.element, recipe.element, auto.element)
            with FormSection('Advanced limits', description='Collapsible form-section normalization.', collapsible=True):
                NumberInput('Warning threshold', value=41.5, unit='nm')
                NumberInput('Stop threshold', value=42.5, unit='nm')
            FormActions(form=form, on_primary=lambda *_: _toast('Settings saved', FeedbackIntent.SUCCESS), on_secondary=form.mark_clean, sticky=False)
    sec = _section('Field anatomy and validation summary', 'Direct review of the generic form-field container and aggregated validation state.')
    with sec:
        with _grid():
            with _sample('Generic form field', span=6):
                with FormField('operator_note','Operator note',description='Generic field container hosting a real editable custom control.',required=True):
                    ui.textarea(value='', placeholder='Type or paste an operator note…').props('outlined dense hide-bottom-space rows=3 aria-label="Operator note"').classes('cui-field-control cui-field-width--full')
            with _sample('Validation summary', span=6):
                ValidationSummary(ValidationSummarySpec((ValidationIssue('Tool','Select a tool'), ValidationIssue('Recipe','Recipe is required'))))
    sec = _section('Dialogs, drawers and menus')
    with sec:
        with _sample('Interactive overlays', span=12):
            def open_confirm():
                d=ConfirmDialog('Apply configuration?', description='This confirms the final action hierarchy.', on_confirm=lambda *_: _toast('Configuration applied', FeedbackIntent.SUCCESS)); d.open()
            def open_danger():
                d=DangerConfirmDialog('Delete saved view?', description='Type DELETE to enable the destructive action.', typed_confirmation='DELETE', on_confirm=lambda *_: _toast('Saved view deleted', FeedbackIntent.DANGER)); d.open()
            def open_detail():
                with DetailDrawer('Measurement detail'):
                    EntityHeader('MEAS-100104', subtitle='CD measurement', entity_type='Measurement', status='Watch', status_intent=StatusIntent.WARNING, icon=Icons.METROLOGY)
                    PropertyGrid((KeyValueItem('lot','Lot','L260113'),KeyValueItem('wafer','Wafer','W05'),KeyValueItem('tool','Tool','ETCH-021'),KeyValueItem('value','Value','42.18 nm')))
            def open_inspector():
                with InspectorDrawer('Inspector'):
                    ui.label('Contextual inspector content').classes('cui-lab-section__description')
                    JsonViewer({'tool':'ETCH-021','chamber':'CH-3','status':'watch'})
            with ButtonCluster():
                Button('Confirm dialog', on_click=open_confirm); Button('Danger dialog', intent=ButtonIntent.DANGER, on_click=open_danger); Button('Detail drawer', on_click=open_detail); Button('Inspector', on_click=open_inspector)
                Button('Success toast', on_click=lambda: _toast('Operation completed successfully', FeedbackIntent.SUCCESS)); Button('Warning toast', on_click=lambda: _toast('Freshness threshold exceeded', FeedbackIntent.WARNING))
                menu_button=Button('Open popover').element
                with menu_button:
                    quick_actions=Popover(title='Quick actions')
                    with quick_actions:
                        async def refresh_quick_actions(*_):
                            _toast('Refreshed'); quick_actions.close()
                        async def export_quick_actions(*_):
                            _toast('Export requested'); quick_actions.close()
                        Button('Refresh', intent=ButtonIntent.GHOST, on_click=refresh_quick_actions)
                        Button('Export', intent=ButtonIntent.GHOST, on_click=export_quick_actions)
    sec = _section('Complete overlay & filter accessory gallery', 'Every public overlay/filter accessory has a live review trigger here; composite-only accessories remain exercised by their parent control.')
    with sec:
        active = ActiveFilter('tool', 'Tool', 'ETCH-021', 'ETCH-021')
        with ButtonCluster():
            FilterChip(active, on_remove=lambda *_: _toast('Filter removed'))
            FilterPresetSelector((FilterPreset('all','All lots',{}), FilterPreset('watch','Watch only',{'status':'Watch'})), active_key='watch', on_select=lambda p: _toast(f'Preset: {p.label}'))
            SavedFilterView((SavedFilterViewSpec('mine','My investigation',{'owner':'me'}), SavedFilterViewSpec('critical','Critical only',{'status':'Critical'})), value='mine')
        menu_items=(
            MenuItemSpec('refresh','Refresh',Icons.REFRESH,on_select=lambda *_: _toast('Menu refresh')),
            MenuItemSpec('export','Export',Icons.DOWNLOAD,shortcut='⌘E',on_select=lambda *_: _toast('Menu export')),
            MenuItemSpec('delete','Delete view',Icons.DELETE,danger=True,separator_before=True,on_select=lambda *_: _toast('Delete requested',FeedbackIntent.DANGER)),
        )
        with ButtonCluster():
            trigger=Button('Dropdown menu',icon=Icons.MORE_HORIZONTAL).element
            with trigger: DropdownMenu(menu_items)
            action_trigger=Button('Action menu',icon=Icons.MORE_HORIZONTAL).element
            with action_trigger: ActionMenu(menu_items)
            context_trigger=Button('Right-click context target',icon=Icons.MORE_HORIZONTAL).element
            with context_trigger: ContextMenu(menu_items)
            tip_target=Button('Tooltip target',intent=ButtonIntent.GHOST).element; Tooltip('Company-owned tooltip anatomy').attach(tip_target)
        def open_dialog():
            with Dialog('General dialog',description='Generic dialog anatomy',primary_label='Apply',on_primary=lambda *_:_toast('Applied')):
                ui.label('Dialog body content')
        def open_form_dialog():
            with FormDialog('Form dialog',description='Form-specific dialog treatment',primary_label='Save'):
                TextInput('Name',value='Saved filter')
        def open_preview():
            with PreviewDialog('Preview dialog',description='Read-only preview surface',secondary_label='Close'):
                JsonViewer({'preview':True,'tool':'ETCH-021'})
        def open_fullscreen():
            with FullScreenDialog('Full-screen review',primary_label='Done'):
                ui.label('Full-screen analytical review surface')
        def open_activity():
            with ActivityDrawer('Activity'):
                ActivityFeed((ActivityItem('d1','Refresh completed','Now','320 rows loaded',Icons.REFRESH,StatusIntent.SUCCESS,'System'),))
        def open_filter_drawer(cls, title):
            with cls(title):
                Select('Status',{'all':'All','watch':'Watch','critical':'Critical'},value='watch')
                DateRangePicker('Observed range')
        def open_form_drawer():
            with FormDrawer('Edit measurement'):
                TextInput('Measurement','MEAS-100104'); NumberInput('Value',42.18,unit='nm')
        def open_responsive():
            with ResponsiveDrawer('Responsive detail'):
                ui.label('Resize below the phone breakpoint and inspect drawer containment.')
        with ButtonCluster():
            Button('Dialog',on_click=open_dialog); Button('Form dialog',on_click=open_form_dialog); Button('Preview dialog',on_click=open_preview); Button('Full-screen dialog',on_click=open_fullscreen)
            Button('Activity drawer',on_click=open_activity); Button('Filter drawer',on_click=lambda:open_filter_drawer(FilterDrawer,'Filter')); Button('Advanced filters',on_click=lambda:open_filter_drawer(AdvancedFilterDrawer,'Advanced filters'))
            Button('Form drawer',on_click=open_form_drawer); Button('Responsive drawer',on_click=open_responsive)
        ValidationMessage('Validation messages use the same danger grammar as fields and forms.')
    # Direct runtime-helper coverage: Form normally owns this guard; this disabled instance verifies the public constructor without adding a second browser guard.
    DirtyStateGuard(enabled=False)
    sec = _section('Feedback states')
    with sec:
        with _grid():
            with _sample('Alerts', span=6):
                with AlertStack():
                    Alert('Information', message='Neutral information without visual alarm.', dismissible=True)
                    Alert('Configuration saved', message='Changes are active.', intent=FeedbackIntent.SUCCESS)
                    Alert('Threshold approaching', message='Two chambers are within the warning band.', intent=FeedbackIntent.WARNING)
                    Alert('Query failed', message='A safe correlation ID would be shown here.', intent=FeedbackIntent.DANGER)
            with _sample('Progress & loading', span=6):
                with FormStack():
                    ui.label('Determinate · 68%').classes('cui-field-label'); ProgressBar(value=.68)
                    ui.label('Indeterminate').classes('cui-field-label'); ProgressBar(indeterminate=True)
                    with ui.element('div').classes('cui-lab-inline'): Spinner(); ui.label('Loading latest measurements…')
                    Skeleton(rows=4)
    _end_shell(shell)


def _data(_: Any = None) -> None:
    ui = _ui(); shell = _shell('/data', 'Enterprise DataTable Lab', 'Use this page as the primary AG Grid visual and interaction review surface.')
    rows = _deterministic_rows(320)
    sec = _section('Full enterprise table', 'Search, sort, filter, resize, select, column management, density, conditional cells, status cells, sparklines and CSV export must all feel native to NiceGUI Base.')
    with sec:
        def inspect_measurement(row: dict[str, Any] | Any) -> None:
            record=dict(row or {})
            title=f"{record.get('id','Measurement')} · {record.get('tool','Unknown tool')}"
            with InspectorDrawer(title, subtitle='Measurement detail · double-click a row or use Inspect'):
                EntityHeader(title, subtitle=f"{record.get('lot','—')} · {record.get('wafer','—')} · {record.get('parameter','—')}", icon=Icons.METROLOGY)
                PropertyGrid(tuple(KeyValueItem(key,key.replace('_',' ').title(),record.get(key)) for key in ('lot','wafer','tool','parameter','value','status','yield','timestamp')))
                with Panel():
                    ui.label('Trend').classes('cui-field-label')
                    ui.label(' · '.join(f'{float(v):.2f}' for v in record.get('trend',())[-8:]) or '—').classes('cui-tabular cui-lab-long-string')

        def export_row(row: dict[str, Any] | Any) -> None:
            record=dict(row or {}); name=str(record.get('id','measurement')).replace('/','-')
            ui.download.content(json.dumps(record,indent=2,default=str),f'{name}.json')
            _toast(f'Exported {name}.json',FeedbackIntent.SUCCESS)

        def export_selected(selected: list[dict[str, Any]] | Any) -> None:
            selected=list(selected or [])
            if not selected:
                _toast('Select at least one row to export',FeedbackIntent.WARNING); return
            keys=[c.key for c in TABLE_COLUMNS if c.key!='trend']
            buffer=io.StringIO(); writer=csv.DictWriter(buffer,fieldnames=keys,extrasaction='ignore'); writer.writeheader(); writer.writerows(selected)
            ui.download.content(buffer.getvalue(),'selected-measurements.csv')
            _toast(f'Exported {len(selected)} selected rows',FeedbackIntent.SUCCESS)

        def row_double_click(event) -> None:
            inspect_measurement((getattr(event,'args',{}) or {}).get('data') or {})

        bulk_actions=(
            BulkAction('export-selected','Export selected',Icons.DOWNLOAD,on_action=export_selected),
            BulkAction('hold-selected','Place on hold',Icons.WARNING,intent='danger',on_action=lambda selected:_toast(f'Placed {len(selected)} selected rows on synthetic hold',FeedbackIntent.WARNING)),
        )
        row_actions=(
            RowAction('inspect','Inspect',Icons.EYE,on_action=inspect_measurement),
            RowAction('export-row','Export',Icons.DOWNLOAD,on_action=export_row),
        )
        DataTable(rows, TABLE_COLUMNS, title='Measurement population', description='320 deterministic synthetic records · 50-row active page · double-click any row for inspection', selection=SelectionMode.MULTIPLE, density=_lab_table_density(), bulk_actions=bulk_actions, row_actions=row_actions, on_row_double_click=row_double_click)
    sec = _section('Editable behavior and rollback', 'Invalid edits should roll back and show a Company toast—not a stock notification.')
    with sec:
        def build_editable_table() -> None:
            editable_cols = tuple(TableColumn(c.key,c.label,c.kind,decimals=c.decimals,min_width=c.min_width,editable=(c.key=='value')) for c in TABLE_COLUMNS[:8])
            EditableTable(rows[:18], editable_cols, spec=EditableTableSpec(editable_cols, title='Editable limits', density=_lab_table_density()), validate_edit=lambda row,key,value: 'Value must be numeric' if key=='value' and not str(value).replace('.','',1).isdigit() else None)
        _deferred_lab_surface('Editable table stress test', 'Mount this second AG Grid only when you want to inspect edit and rollback behavior.', build_editable_table, button_label='Load editable table')
    sec = _section('Server-mode simulation', 'The 180ms synthetic request is preserved, but it no longer runs during the initial DataTable page load.')
    with sec:
        async def fetch(query: TableQuery):
            await asyncio.sleep(.18)
            q=(query.search or '').lower(); filtered=[r for r in rows if not q or q in ' '.join(str(v).lower() for v in r.values())]
            start=(query.page-1)*query.page_size; page=filtered[start:start+query.page_size]
            return TableResult(tuple(page), len(filtered), query.page, query.page_size)
        def build_server_table() -> None:
            ServerDataTable(TABLE_COLUMNS, fetch=fetch, title='Server-backed measurements', selection=SelectionMode.SINGLE, density=_lab_table_density())
        _deferred_lab_surface('Server table stress test', 'Mount on demand to exercise loading and latest-request-wins without burdening normal page scrolling.', build_server_table, button_label='Load server table')
    sec = _section('Master/detail, presets and expanded content', 'Community-compatible drilldown and the table accessory surfaces are reviewed explicitly.')
    with sec:
        def build_master_detail_table() -> None:
            master = MasterDetailTable(rows[:24], TABLE_COLUMNS, title='Master/detail measurements', selection=SelectionMode.SINGLE, density=_lab_table_density(),
                detail_title=lambda row: f"{row.get('id','Measurement')} detail",
                detail_renderer=lambda row: PropertyGrid((KeyValueItem('lot','Lot',row.get('lot')),KeyValueItem('tool','Tool',row.get('tool')),KeyValueItem('value','Value',row.get('value')))))
            TablePresetSelector((TablePreset('Compact core',visible_columns=('id','lot','tool','value','status'),density=TableDensity.COMPACT),TablePreset('Dense all',visible_columns=tuple(c.key for c in TABLE_COLUMNS),density=TableDensity.DENSE)), table=master)
            with ExpandableRow('Inline expanded-row anatomy', open=True):
                ui.label('This verifies the normalized expansion surface used by table drilldown helpers.')
        _deferred_lab_surface('Master/detail stress test', 'Mount on demand to inspect drilldown, presets, and expanded-row anatomy.', build_master_detail_table, button_label='Load master/detail table')
    _end_shell(shell)


def _charts(_: Any = None) -> None:
    ui = _ui(); shell = _shell('/charts', 'Visualization Laboratory', 'Every chart uses the same semantic theme and Company toolbar while ECharts remains the rendering engine.')
    cats=('Mon','Tue','Wed','Thu','Fri','Sat','Sun')
    sec = _section('Core analytical charts')
    with sec:
        with _grid():
            with ui.element('div').classes('cui-lab-span-6'):
                LineChart('Yield trend', (SeriesSpec('yield','Yield',(97.8,98.2,97.9,98.5,98.1,98.8,98.6),smooth=True),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=cats), spec_limits=SpecLimits(lower=96,target=98.5))
            with ui.element('div').classes('cui-lab-span-6'):
                BarChart('Excursions by day', (SeriesSpec('exc','Excursions',(2,5,3,8,4,6,2)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=cats))
            with ui.element('div').classes('cui-lab-span-6'):
                AreaChart('Throughput', (SeriesSpec('wph','WPH',(104,111,108,119,117,121,116),smooth=True),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=cats))
            with ui.element('div').classes('cui-lab-span-6'):
                ScatterChart('CD correlation', (SeriesSpec('cd','CD',tuple((x, 39 + x*.22 + math.sin(x)*.4) for x in range(18))),))
            with ui.element('div').classes('cui-lab-span-6'):
                DonutChart('Excursion disposition', (SeriesSpec('state','State',(('Resolved',42),('Monitoring',18),('Open',9))),))
            with ui.element('div').classes('cui-lab-span-6'):
                Gauge('Fleet health', (SeriesSpec('health','Health',(94.6,)),))
            with ui.element('div').classes('cui-lab-span-6'):
                StackedBarChart('Affected vs control', (SeriesSpec('affected','Affected',(18,24,31,11),stack='population'),SeriesSpec('control','Control',(42,38,35,51),stack='population')), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('ETCH-014','ETCH-021','CVD-008','CMP-004')))
            with ui.element('div').classes('cui-lab-span-6'):
                Histogram('CD distribution', (SeriesSpec('count','Count',(2,4,9,16,21,17,10,5,2)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('38.0','38.5','39.0','39.5','40.0','40.5','41.0','41.5','42.0')))
            with ui.element('div').classes('cui-lab-span-6'):
                Heatmap('Tool × day heatmap', (SeriesSpec('heat','Excursion intensity',tuple((x,y,round(1.5 + abs(math.sin(x*.7+y*.9))*8.5,1)) for x in range(7) for y in range(5))),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Mon','Tue','Wed','Thu','Fri','Sat','Sun')), y_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('ETCH-014','ETCH-021','CVD-008','CMP-004','PVD-011')))
            with ui.element('div').classes('cui-lab-span-6'):
                ParetoChart('Excursion contributors',('CH-3','Recipe R18','PM timing','Material','Other'),(34,22,13,8,5),(41.5,68.3,84.1,93.9,100.0))
    sec = _section('Statistical and specialist chart variants', 'Typed wrappers and specialist panels must share the exact same Company chart shell and toolbar.')
    with sec:
        with _grid():
            with ui.element('div').classes('cui-lab-span-6'):
                BoxPlot('CD box plot', (SeriesSpec('cd-box','CD',((38.4,39.2,40.0,40.8,41.7),(38.8,39.5,40.2,41.0,42.1))),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Control','Affected')))
            with ui.element('div').classes('cui-lab-span-6'):
                ControlChart('Control chart', (SeriesSpec('cd-control','CD',(39.7,39.9,40.1,40.0,40.4,41.0,41.4,41.8)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(f'W{i}' for i in range(1,9))), spec_limits=SpecLimits(lower=37.5,upper=42.5,target=40))
            with ui.element('div').classes('cui-lab-span-6'):
                TimelineChart('Event timeline', (SeriesSpec('events','Events',((1,1),(2,2),(3,1),(4,3))),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('PM','Recipe','SPC','Review')))
            with ui.element('div').classes('cui-lab-span-6'):
                DistributionPanel('Distribution panel', (SeriesSpec('dist','Count',(1,4,10,18,13,7,2)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('38','39','39.5','40','40.5','41','42')))
            with ui.element('div').classes('cui-lab-span-12'):
                ProcessTrendPanel('Process trend panel', (SeriesSpec('trend','CD',(39.7,39.8,40.0,40.2,40.8,41.3,41.6)),), x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(i) for i in range(7))), spec_limits=SpecLimits(lower=37.5,upper=42.5,target=40))
    sec = _section('Specialist escape hatch', 'Plotly remains a controlled specialist escape hatch inside the same Company chart surface.')
    with sec:
        PlotlyPanel('Plotly specialist panel', {
            'data':[{'type':'scatter','mode':'lines+markers','x':['A','B','C','D'],'y':[39.8,40.2,41.0,40.7],'name':'CD'}],
            'layout':{'margin':{'l':36,'r':16,'t':16,'b':32},'showlegend':False,'paper_bgcolor':'rgba(0,0,0,0)','plot_bgcolor':'rgba(0,0,0,0)'},
            'config':{'displayModeBar':False,'responsive':True},
        }, description='Specialist escape hatch constrained by Company panel anatomy')
    ChartCrossFilter()  # public nonvisual chart-linking helper; typed charts cover the visual shell above
    sec = _section('Engineering spatial visuals')
    with sec:
        points=[]
        for x in range(-8,9):
            for y in range(-8,9):
                if x*x+y*y<=64:
                    points.append(WaferPoint(x,y,round(40 + math.sin(x/2)*.9 + math.cos(y/3)*.7,3),'watch' if x>5 else 'normal'))
        spatial=[SpatialPoint(x=i%12,y=i//12,value=round(2.5+math.sin(i/7)*.6,3),label=f'Die {i+1}') for i in range(72)]
        with _grid():
            with ui.element('div').classes('cui-lab-span-6'): WaferMap('Wafer spatial signature', points)
            with ui.element('div').classes('cui-lab-span-6'): SpatialMap('Die-level residual', spatial)
        controls=[WaferPoint(p.x,p.y,round(float(p.value)-1.0-(.45 if p.x>5 else 0),3),'normal') for p in points]
        radial_control=[39.85,39.88,39.92,39.96,40.01,40.06,40.12,40.18,40.23]
        radial_affected=[39.91,39.94,40.02,40.14,40.35,40.71,41.12,41.53,41.84]
        with _grid():
            with ui.element('div').classes('cui-lab-span-8'): WaferComparisonMap('Affected vs control wafer signature',points,controls)
            with ui.element('div').classes('cui-lab-span-4'): RadialProfilePlot('Radial CD profile',radial_affected,radial_control,unit='nm')
        with _grid():
            with ui.element('div').classes('cui-lab-span-6'):
                ChamberFingerprintMatrix(
                    'Chamber fingerprint',
                    ('ETCH-014 / CH-2','ETCH-021 / CH-3','ETCH-024 / CH-1','ETCH-031 / CH-4'),
                    ('CD Δ','Pressure','RF bias','PM age','OOS rate'),
                    ((-.18,.06,-.10,.12,.04),(.91,.62,.73,.84,.78),(.11,-.08,.04,.22,.09),(.24,.16,.12,.31,.18)),
                )
            with ui.element('div').classes('cui-lab-span-6'):
                CommonalityMatrix(
                    'RCA commonality matrix',
                    ('CH-3','Recipe R18','PM < 3 d','Material M4','Route A17'),
                    ('Affected','Matched control','Baseline'),
                    ((.94,.18,.12),(.88,.31,.22),(.76,.15,.19),(.61,.55,.48),(.42,.39,.41)),
                )
    _end_shell(shell)


def _synthetic_inspection_image() -> str:
    """Rich local SVG evidence image for the analytical ImageViewer lab."""
    cells=[]
    for iy in range(-5,6):
        for ix in range(-5,6):
            if ix*ix+iy*iy>30:
                continue
            x=240+ix*18; y=126+iy*18
            value=math.sin(ix*.7)+math.cos(iy*.55)+(1.4 if ix>=2 and iy<=-1 else 0)
            if value>1.8: fill='#D85C55'
            elif value>1.0: fill='#F1B55D'
            elif value<-1.0: fill='#4C89D9'
            else: fill='#AFC8E8' if value<0 else '#D9E5F3'
            cells.append(f'<rect x="{x-8}" y="{y-8}" width="16" height="16" rx="2.6" fill="{fill}" stroke="#fff" stroke-width="1"/>')
    svg=(
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="360" viewBox="0 0 720 360">'
        '<rect width="720" height="360" rx="18" fill="#F5F7FA"/>'
        '<defs><clipPath id="inspection-wafer-clip"><circle cx="240" cy="126" r="112"/></clipPath></defs>'
        '<g transform="translate(0,20)">'
        '<circle cx="240" cy="126" r="112" fill="#FFFFFF" stroke="#AAB4C2" stroke-width="2"/>'
        '<g clip-path="url(#inspection-wafer-clip)">'
        '<path d="M231 235 L240 245 L249 235" fill="#F5F7FA" stroke="#AAB4C2" stroke-width="2"/>'
        + ''.join(cells) +
        '</g>'
        '<circle cx="240" cy="126" r="76" fill="none" stroke="#8C97A6" stroke-dasharray="4 5" opacity=".45"/>'
        '<circle cx="240" cy="126" r="40" fill="none" stroke="#8C97A6" stroke-dasharray="4 5" opacity=".35"/>'
        '</g>'
        '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif">'
        '<text x="390" y="70" font-size="18" font-weight="700" fill="#17202C">Wafer 12 · CD residual</text>'
        '<text x="390" y="96" font-size="12" fill="#5E6978">ETCH-021 / CH-3 · Recipe ETCH_R18</text>'
        '<rect x="390" y="126" width="250" height="1" fill="#D7DDE5"/>'
        '<text x="390" y="156" font-size="11" font-weight="700" fill="#6B7685">OBSERVED SIGNATURE</text>'
        '<text x="390" y="181" font-size="14" fill="#17202C">Lower-right excursion cluster</text>'
        '<text x="390" y="207" font-size="12" fill="#5E6978">Edge enrichment · +2.2σ vs control</text>'
        '<text x="390" y="246" font-size="11" font-weight="700" fill="#6B7685">LEGEND</text>'
        '<rect x="390" y="264" width="32" height="8" rx="4" fill="#4C89D9"/><text x="430" y="273" font-size="11" fill="#5E6978">Low</text>'
        '<rect x="490" y="264" width="32" height="8" rx="4" fill="#D9E5F3"/><text x="530" y="273" font-size="11" fill="#5E6978">Nominal</text>'
        '<rect x="390" y="292" width="32" height="8" rx="4" fill="#F1B55D"/><text x="430" y="301" font-size="11" fill="#5E6978">Watch</text>'
        '<rect x="490" y="292" width="32" height="8" rx="4" fill="#D85C55"/><text x="530" y="301" font-size="11" fill="#5E6978">OOS</text>'
        '</g></svg>'
    )
    return 'data:image/svg+xml;charset=utf-8,'+quote(svg)


def _content(_: Any = None) -> None:
    ui = _ui(); shell = _shell('/content', 'Content, Workflow & Commands', 'Viewers and workflow components should visually inherit NiceGUI Base rather than their underlying third-party defaults.')
    sec = _section('Entity and property presentation')
    with sec:
        EntityHeader('ETCH-021 / CH-3', subtitle='Critical etch chamber investigation', entity_type='Chamber', status='Watch', status_intent=StatusIntent.WARNING, icon=Icons.CHAMBER,
                     metadata=(KeyValueItem('area','Area','ETCH'),KeyValueItem('recipe','Recipe','ETCH_R18')))
        with _grid():
            with _sample('Key/value', span=4): KeyValueList((KeyValueItem('lot','Lot','L260142',copyable=True),KeyValueItem('wafer','Wafer','W12'),KeyValueItem('owner','Owner','Process Engineering')))
            with _sample('Property grid', span=4): PropertyGrid((KeyValueItem('status','Status','Watch'),KeyValueItem('age','Last PM','17 days'),KeyValueItem('pressure','Pressure','12.8 mTorr')))
            with _sample('Comparison metric', span=4): ComparisonMetric('Mean CD','42.18 nm',baseline='40.06 nm',delta='+2.12 nm',intent=StatusIntent.DANGER)
    sec = _section('Delta and trend indicators', 'Standalone metric indicators preserve non-color directional semantics.')
    with sec:
        with ui.element('div').classes('cui-lab-inline'):
            DeltaIndicator('+2.12 nm',trend=TrendDirection.UP,intent=StatusIntent.DANGER); TrendIndicator('-1.8%',trend=TrendDirection.DOWN,intent=StatusIntent.SUCCESS); TrendIndicator('Stable',trend=TrendDirection.STABLE)
    sec = _section('Hierarchy and viewers')
    with sec:
        with _grid():
            with _sample('Tree', span=4):
                TreeView((TreeNode('fab','Fab 1',(TreeNode('etch','ETCH',(TreeNode('tool14','ETCH-014'),TreeNode('tool21','ETCH-021'))),TreeNode('cvd','CVD'))),))
            with _sample('Markdown', span=4): MarkdownViewer('### Investigation note\n- Strong edge signature\n- **CH-3** commonality\n- Contradiction retained')
            with _sample('JSON', span=4): JsonViewer({'tool':'ETCH-021','chamber':'CH-3','recipe':'ETCH_R18','values':[40.1,41.2,42.0]})
            with _sample('Code', span=6):
                from nicegui_base.integrations.nicegui_content import CodeViewer
                CodeViewer("query = {'tool': 'ETCH-021', 'status': 'watch'}", language='python')
            with _sample('Log', span=6): LogViewer(('09:31:04 query started','09:31:04 320 records scanned','09:31:05 completed in 184 ms'))
    sec = _section('Generic comparison panel', 'The generic comparison container is shown independently from the Before/After specialization.')
    with sec:
        with ComparePanel() as comparison:
            with comparison.side('Affected'): ui.label('42.18 nm · ETCH-021 / CH-3')
            with comparison.side('Control'): ui.label('40.06 nm · ETCH-014 / CH-2')
    sec = _section('Search, workflow and command palette')
    with sec:
        SearchResults((SearchResultSpec('r1','ETCH-021 / CH-3','Chamber · Watch','Strong affected/control enrichment',Icons.CHAMBER),SearchResultSpec('r2','Recipe ETCH_R18','Recipe','Applied to 84 affected wafers',Icons.RECIPE)))
        steps=(StepSpec('scope','Scope population',state=StepState.COMPLETE),StepSpec('compare','Compare controls',state=StepState.COMPLETE),StepSpec('evidence','Review evidence',state=StepState.ACTIVE),StepSpec('close','Close investigation'))
        ProgressSteps(steps)
        with _grid():
            with _sample('Description list', span=4):
                DescriptionList((KeyValueItem('source','Source','Metrology'),KeyValueItem('quality','Quality','Complete'),KeyValueItem('updated','Updated','2 minutes ago')))
            with _sample('Notification center', span=4):
                NotificationCenter((ToastSpec('CD warning threshold exceeded',FeedbackIntent.WARNING,4000),ToastSpec('Control population refreshed',FeedbackIntent.SUCCESS,3000)))
            with _sample('Activity feed', span=4):
                ActivityFeed((ActivityItem('a1','Investigation opened','09:28','Affected population scoped',Icons.RCA,StatusIntent.INFO,'Process Engineer'),ActivityItem('a2','Control population updated','09:31','215 matched wafers',Icons.CONTROL_POPULATION,StatusIntent.SUCCESS,'System')))
        with _sample('Image viewer', span=12):
            ImageViewer(_synthetic_inspection_image(),alt='Synthetic wafer residual evidence',caption='Wafer 12 · CD residual evidence · wheel to zoom, drag to pan')
        with Stepper(steps) as stepper:
            with stepper.step('scope'): ui.label('Scope affected population and choose matched controls.')
            with stepper.step('compare'): ui.label('Compare route, tool, chamber, recipe and material commonalities.')
            with stepper.step('evidence'): ui.label('Assess supporting and contradicting evidence without hiding contradictions.')
            with stepper.step('close'): ui.label('Document the final disposition and evidence basis.')
        registry=CommandRegistry(); registry.register(Command('search','Search measurements',lambda: ui.navigate.to('/data'),shortcut='⌘K',keywords=('find','table'))); registry.register(Command('rca','Open RCA workspace',lambda: ui.navigate.to('/engineering'),shortcut='⌘R')); registry.register(Command('theme','Review theme foundation',lambda: ui.navigate.to('/foundation')))
        palette=CommandPalette(registry)
        Button('Open command palette', icon=Icons.SEARCH, on_click=palette.open)
    _end_shell(shell)


def _engineering(_: Any = None) -> None:
    ui = _ui(); shell = _shell('/engineering', 'Engineering & RCA Laboratory', 'Purpose-built investigation cockpit: scope, process behavior, population separation, evidence, commonality, contradictions and timeline.')
    entity=EngineeringEntityRef(EngineeringEntityKind.CHAMBER,'ETCH-021/CH-3','ETCH-021 · Chamber 3',EngineeringStatus.WATCH,'Etch critical dimension')
    with MetricStrip():
        MetricCard('Affected population','84 wafers',delta='12 lots',intent=StatusIntent.DANGER,icon=Icons.AFFECTED_POPULATION)
        MetricCard('Matched controls','215 wafers',delta='exact route strategy',intent=StatusIntent.SUCCESS,icon=Icons.CONTROL_POPULATION)
        MetricCard('Evidence confidence','High',delta='2 strong channels',intent=StatusIntent.SUCCESS,icon=Icons.EVIDENCE)
        MetricCard('Contradictions',1,delta='retained in decision',intent=StatusIntent.WARNING,icon=Icons.WARNING)
    InvestigationContextBar(InvestigationContextSpec('EXC-1042','Chamber 3 process degradation','Process Engineering','Evidence review','2 minutes ago'))
    sec = _section('Investigation identity and specification context')
    with sec:
        with _grid():
            with ui.element('div').classes('cui-lab-span-6'): EngineeringEntityCard(EngineeringEntityCardSpec(entity,properties=(('Tool / chamber','ETCH-021 / CH-3'),('Recipe','ETCH_R18'),('Last PM','17 days'),('Lots affected','12 lots'))))
            with _sample('Specification semantics', span=6):
                limits=LimitBand(lower_spec=37.5,upper_spec=42.5,target=40.0,lower_warning=38.2,upper_warning=41.8,unit='nm')
                with ui.element('div').classes('cui-lab-inline'):
                    EngineeringStatusBadge(EngineeringStatus.NORMAL); EngineeringStatusBadge(EngineeringStatus.WATCH); EngineeringStatusBadge(EngineeringStatus.CRITICAL)
                with ui.element('div').classes('cui-lab-stack'):
                    SpecLimitIndicator(40.1,limits=limits); SpecLimitIndicator(41.95,limits=limits); SpecLimitIndicator(43.1,limits=limits)
                    OutOfSpecIndicator(43.1,limits=limits); BaselineComparison(BaselineModel(42.18,40.06,'nm',higher_is_better=False)); ConfidenceIndicator(ConfidenceIndicatorSpec(ConfidenceLevel.HIGH,.82,'Multiple independent evidence channels',calibrated_probability=False))
    sec = _section('Process behavior and population separation', 'Trend and affected/control evidence are deliberately paired so causal reasoning is not separated from the control definition.')
    with sec:
        points=tuple(MeasurementPoint(f'W{i:02d}',40 + math.sin(i/2.4)*.7 + (1.4 if i>14 else 0)) for i in range(1,25))
        affected=tuple(41.2 + math.sin(i)*.55 for i in range(42)); control=tuple(39.8 + math.sin(i*.8)*.42 for i in range(64))
        with _grid():
            with ui.element('div').classes('cui-lab-span-7'): EngineeringProcessTrend(ProcessTrendSpec('CD',points,'nm',LimitBand(37.5,42.5,40),ControlLimits(38.4,41.6,40),title='CD process trend'))
            with ui.element('div').classes('cui-lab-span-5'): PopulationComparisonPanel(DistributionComparisonSpec(affected,control,'CD','nm'))
    sec = _section('Evidence balance', 'Independent support, contradiction and neutral context remain visible at the same level of the investigation.')
    with sec:
        evidence=(
            EvidenceItem('e1','SPC excursion begins after PM',EvidenceChannel.SPC,EvidenceDirection.SUPPORTS,EvidenceStrength.STRONG,'Shift exceeds historical control envelope','SPC'),
            EvidenceItem('e2','Edge spatial signature matches chamber degradation',EvidenceChannel.METROLOGY,EvidenceDirection.SUPPORTS,EvidenceStrength.STRONG,'Affected wafers share an edge-heavy residual signature','Metrology'),
            EvidenceItem('e3','Recipe also appears on healthy control tool',EvidenceChannel.ROUTING,EvidenceDirection.CONTRADICTS,EvidenceStrength.MODERATE,'Recipe commonality alone does not isolate the cause','Route history'),
            EvidenceItem('e4','Maintenance log records pressure adjustment',EvidenceChannel.MAINTENANCE,EvidenceDirection.NEUTRAL,EvidenceStrength.WEAK,'Timing overlaps but evidence is not directional','Maintenance'),
        )
        with _grid():
            for item in evidence:
                with ui.element('div').classes('cui-lab-span-6'): EvidenceCard(EvidenceCardSpec(item))
        hypothesis=RcaHypothesis('h1','Chamber 3 process degradation','Candidate supported by independent SPC and metrology evidence',evidence=evidence,confidence=ConfidenceIndicatorSpec(ConfidenceLevel.HIGH,.82,'Weighted evidence balance'))
        RcaEvidencePanel(RcaEvidencePanelSpec(hypothesis))
    sec = _section('Commonality and investigation timeline', 'High enrichment is shown separately from mere route participation; the timeline preserves temporal context.')
    with sec:
        observations=(
            CommonalityObservation('ch3','Chamber 3',CommonalityKind.CHAMBER,73,84,26,215,interpretation=CommonalityInterpretation.CAUSAL_CANDIDATE),
            CommonalityObservation('tool21','ETCH-021',CommonalityKind.TOOL,77,84,41,215,interpretation=CommonalityInterpretation.OBSERVED),
            CommonalityObservation('r18','ETCH_R18',CommonalityKind.RECIPE,54,84,124,215,interpretation=CommonalityInterpretation.ROUTING),
        )
        now=datetime(2026,8,25,9,30)
        with _grid():
            with ui.element('div').classes('cui-lab-span-7'): CommonalityTable(CommonalityTableSpec(observations))
            with ui.element('div').classes('cui-lab-span-5'):
                EngineeringTimeline((
                    EngineeringTimelineEvent(now,'SPC excursion detected','CD mean crossed the warning envelope.',EngineeringStatus.CRITICAL,entity),
                    EngineeringTimelineEvent(now-timedelta(hours=2),'Recipe R18 started','Affected lots entered CH-3.',EngineeringStatus.WATCH,entity),
                    EngineeringTimelineEvent(now-timedelta(days=17),'Preventive maintenance completed','Pressure subsystem adjusted.',EngineeringStatus.NORMAL,entity),
                ))
    _end_shell(shell)


def _states(_: Any = None) -> None:
    ui = _ui(); shell = _shell('/states', 'State & Failure Laboratory', 'Every unhappy path must still look intentional and preserve clear recovery behavior.')
    sec = _section('Canonical application states')
    with sec:
        with _grid():
            with ui.element('div').classes('cui-lab-span-4'): EmptyState('No data yet', message='Connect a source or adjust the time window.', action_label='Configure', on_action=lambda: _toast('Configure action'))
            with ui.element('div').classes('cui-lab-span-4'): NoResultsState(message='Filters excluded all 18,402 measurements.', on_clear=lambda: _toast('Filters cleared'))
            with ui.element('div').classes('cui-lab-span-4'): ErrorState(message='The synthetic service returned a controlled failure.', error_id='ERR-LAB-2048', on_retry=lambda: _toast('Retry requested'))
            with ui.element('div').classes('cui-lab-span-4'): OfflineState(message='The connection is unavailable. Existing content should remain understandable.', on_retry=lambda: _toast('Connectivity check requested'))
            with ui.element('div').classes('cui-lab-span-4'): PermissionDeniedState(message='You do not have permission to view this investigation.')
            with ui.element('div').classes('cui-lab-span-4'): NotFoundState(message='The requested synthetic investigation does not exist.', on_back=lambda: _toast('Back requested'))
            with ui.element('div').classes('cui-lab-span-4'): StateIllustration(Illustrations.NO_SELECTION, label='No selection')
            with ui.element('div').classes('cui-lab-span-4'): StateView(StateViewSpec(StateKind.EMPTY,'Generic state view','Direct review of the base state component',action_label='Resolve'),on_action=lambda: _toast('State action'))
    sec = _section('Async lifecycle')
    with sec:
        with _grid():
            for label,state in (('Loading',AsyncState.LOADING),('Ready',AsyncState.READY),('Refreshing',AsyncState.REFRESHING),('Empty',AsyncState.EMPTY),('Error',AsyncState.ERROR)):
                with _sample(label, span=4 if label!='Ready' else 8):
                    AsyncContent(state, content=lambda: ui.label('Preserved content remains visible during refresh.'), error_id='ASYNC-LAB-1')
    sec = _section('Stress conditions', 'These deliberately ugly values should not destroy hierarchy or overflow the application shell.')
    with sec:
        with ui.element('div').classes('cui-lab-stress-strip'):
            with Panel(): ui.label('Very long entity name').classes('cui-field-label'); ui.label('ETCH_CRITICAL_DIMENSION_ENGINEERING_MONITORING_TOOL_WITH_A_DELIBERATELY_LONG_IDENTIFIER_00000000042').classes('cui-lab-long-string')
            with Panel(): ui.label('Missing data').classes('cui-field-label'); ui.label('—'); ui.label('Unknown').classes('cui-lab-type-caption')
            with Panel(): ui.label('Large numeric').classes('cui-field-label'); ui.label('12,345,678,901.123456').classes('cui-tabular')
            with Panel() as korean_panel:
                korean_panel.element.classes(add='cui-v2-i18n-stress')
                ui.label('한국어 + English').classes('cui-field-label')
                ui.label('설비 이상 분석 · 공정 조건 비교 · 장비 상태 확인 · Equipment health investigation with mixed-language content').classes('cui-lab-section__description')
            with Panel() as mixed_panel:
                mixed_panel.element.classes(add='cui-v2-i18n-stress')
                ui.label('Long mixed identifier').classes('cui-field-label')
                ui.label('ETCH-021_CH-3_공정이상분석_RECIPE-ETCH_R18_LOT-L260142_WAFER-W12_SUPER_LONG_UNBROKEN_IDENTIFIER_00000042').classes('cui-lab-long-string')
            with Panel(): ui.label('Dense status set').classes('cui-field-label');
            with ui.element('div').classes('cui-lab-inline'):
                StatusBadge('Critical', intent=StatusIntent.DANGER); StatusBadge('Stale', intent=StatusIntent.WARNING); StatusBadge('Offline')
    _end_shell(shell)


def _performance(_: Any = None) -> None:
    ui = _ui(); shell = _shell('/performance', 'Performance Laboratory', 'Interactive workloads expose generation, render assembly, cancellation and query timing instead of hiding work behind a button.')
    sec = _section('Interactive workload benchmark', 'Every action updates visible state immediately. The large workload remains opt-in so ordinary lab navigation stays fast.')
    with sec:
        with Panel():
            with ui.element('div').classes('cui-performance-head'):
                with ui.element('div'):
                    ui.label('Local grid workload').classes('cui-lab-section__title')
                    ui.label('Generate deterministic synthetic rows off the UI event loop, mount the real Company DataTable, then expose timing and status.').classes('cui-lab-section__description')
                state_badge = ui.label('Idle').classes('cui-performance-state is-idle')
            progress = ProgressBar(value=0, label='Performance workload progress')
            progress.element.classes('cui-performance-progress')
            with ui.element('div').classes('cui-performance-metrics'):
                rows_metric = ui.label('0').classes('cui-performance-metric__value'); ui.label('Rows').classes('cui-performance-metric__label')
                generation_metric = ui.label('—').classes('cui-performance-metric__value'); ui.label('Generation').classes('cui-performance-metric__label')
                mount_metric = ui.label('—').classes('cui-performance-metric__value'); ui.label('Table mount').classes('cui-performance-metric__label')
                search_metric = ui.label('—').classes('cui-performance-metric__value'); ui.label('Filter benchmark').classes('cui-performance-metric__label')
            host=ui.element('div').classes('cui-performance-host cui-lab-stack')
            active={'generation':0,'rows':[]}

            def set_state(label: str, state: str):
                state_badge.set_text(label); state_badge.classes(replace=f'cui-performance-state is-{state}')

            async def load_workload(count: int):
                active['generation'] += 1; generation=active['generation']
                set_state(f'Generating {count:,} rows…','loading'); progress.set_indeterminate(True)
                rows_metric.set_text(f'{count:,}'); generation_metric.set_text('Running…'); mount_metric.set_text('—'); search_metric.set_text('—')
                await asyncio.sleep(0)
                started=time.perf_counter(); rows=await asyncio.to_thread(_deterministic_rows,count); generated_ms=(time.perf_counter()-started)*1000
                if generation != active['generation']: return
                active['rows']=rows; generation_metric.set_text(f'{generated_ms:,.0f} ms')
                set_state('Mounting real DataTable…','loading')
                mount_started=time.perf_counter(); host.clear()
                with host:
                    DataTable(rows,TABLE_COLUMNS,title=f'{count:,}-row local grid',description='Real AG Grid surface; search, sort, resize, select, filter and column controls remain active.',selection=SelectionMode.MULTIPLE,density=TableDensity.COMPACT)
                mount_ms=(time.perf_counter()-mount_started)*1000; mount_metric.set_text(f'{mount_ms:,.0f} ms')
                # Pure-Python benchmark provides an immediately comparable query metric; browser interaction remains certified separately.
                query_started=time.perf_counter(); await asyncio.to_thread(lambda: [r for r in rows if r['tool']=='ETCH-021' and r['value']>40]); query_ms=(time.perf_counter()-query_started)*1000
                search_metric.set_text(f'{query_ms:,.1f} ms'); progress.set_value(1); set_state(f'{count:,} rows ready','success')
                _toast(f'{count:,}-row workload ready',FeedbackIntent.SUCCESS)

            def clear_workload():
                active['generation'] += 1; active['rows']=[]; host.clear(); progress.props(remove='indeterminate'); progress.set_value(0)
                rows_metric.set_text('0'); generation_metric.set_text('—'); mount_metric.set_text('—'); search_metric.set_text('—'); set_state('Cancelled','idle')
                with host: EmptyState('No stress workload loaded',message='Choose a workload to exercise the real table. Visible timing appears above as soon as work begins.',compact=True)

            async def load_10k(): await load_workload(10_000)
            async def load_100k(): await load_workload(100_000)
            with ButtonCluster():
                Button('Load 10k rows',icon=Icons.TABLE,on_click=load_10k)
                Button('Load 100k rows',icon=Icons.DIAGNOSTICS,intent=ButtonIntent.DANGER,on_click=load_100k)
                Button('Cancel / clear',intent=ButtonIntent.GHOST,on_click=clear_workload)
            with host: EmptyState('No stress workload loaded',message='Choose 10k first, then 100k when you want the full local stress path.',compact=True)
    sec = _section('Background-work presentation', 'These surfaces demonstrate progress hierarchy independently from the stress workload.')
    with sec:
        with SurfaceGrid():
            with Panel():
                BackgroundTaskIndicator('Re-indexing measurement population', progress=.63, detail='63,004 / 100,000 rows')
            with Panel():
                ProgressMetric('Verification coverage',.94,target=1,display_value='94%',description='Illustrative benchmark coverage metric')
    _end_shell(shell)


def _reference_about() -> None:
    ui=_ui()
    with Dialog('Reference application', description='NiceGUI Base v1.7 canonical application pattern', primary_label='Done', secondary_label=None):
        with ui.element('div').classes('cui-content-column'):
            ui.label('Purpose').classes('cui-field-label')
            ui.label('Production-grade composition proof using deterministic engineering data.').classes('cui-page-description')
            ui.label('Design system').classes('cui-field-label')
            ui.label('Apple × Linear foundation · Stripe information architecture · Company engineering identity.').classes('cui-page-description')


def _reference_shell(route: str) -> AppShell:
    shell=AppShell(
        'Company Engineering Workspace', LAB_NAVIGATION, active_route=route, environment='REF APP',
        subtitle='Reference applications · synthetic engineering data', greeting='Good morning',
        user_name='Process Engineer', user_initials='PE',
        on_settings=lambda:_ui().navigate.to('/patterns/settings'), on_about=_reference_about,
        owner='NiceGUI Base / Metrology Engineering', on_support=lambda:_toast('Support contact opened'),
        on_feedback=lambda:_toast('VOC / feedback submission opened'), on_docs=lambda:_toast('Documentation opened'),
    )
    shell.__enter__()
    return shell


def _pattern_filter_controls(*, include_tool: bool = True, include_window: bool = True) -> None:
    ui=_ui()
    with ui.element('div').classes('cui-pattern-filter-controls'):
        Select('Area', {'all':'All areas','etch':'ETCH','cvd':'CVD','cmp':'CMP'}, value='all')
        if include_tool: Select('Tool', {'all':'All tools','etch021':'ETCH-021','etch014':'ETCH-014','cvd007':'CVD-007'}, value='all')
        if include_window: SegmentedControl({'24h':'24 h','7d':'7 d','30d':'30 d'}, value='7d')


def _pattern_dashboard(_: Any = None) -> None:
    shell=_reference_shell('/patterns/dashboard')
    with DashboardPage('Yield Performance','Executive-to-engineering overview with one clear reading order') as page:
        with page.slot(LayoutSlot.FILTERS):
            _pattern_filter_controls(include_tool=False)
        with page.slot(LayoutSlot.METRICS):
            with MetricStrip():
                MetricCard('Yield','98.4%',delta='+0.7% WoW',trend=TrendDirection.UP,intent=StatusIntent.SUCCESS,icon=Icons.YIELD)
                MetricCard('Excursions',12,delta='3 critical',trend=TrendDirection.UP,intent=StatusIntent.DANGER,icon=Icons.EXCURSION)
                MetricCard('Fleet health','94.6%',delta='stable',trend=TrendDirection.STABLE,icon=Icons.TOOL)
                MetricCard('Stale signals',4,delta='>30 min',intent=StatusIntent.WARNING,icon=Icons.CLOCK)
        with page.slot(LayoutSlot.PRIMARY):
            LineChart('Yield trend',(SeriesSpec('yield','Yield',(97.8,98.1,98.0,98.4,98.2,98.6,98.4),smooth=True),),x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('Mon','Tue','Wed','Thu','Fri','Sat','Sun')))
        with page.slot(LayoutSlot.SECONDARY):
            DonutChart('Excursion state',(SeriesSpec('state','State',(('Resolved',31),('Monitoring',12),('Open',5))),))
        with page.slot(LayoutSlot.DATA):
            DataTable(_deterministic_rows(28),TABLE_COLUMNS,title='Recent measurements',selection=SelectionMode.SINGLE)
        with page.slot(LayoutSlot.ACTIONS):
            Button('Open Data Explorer',intent=ButtonIntent.SECONDARY,icon=Icons.SEARCH,on_click=lambda:_ui().navigate.to('/patterns/explorer'))
            ActionButton('Open active RCA',icon=Icons.RCA,on_click=lambda:_ui().navigate.to('/patterns/analysis'))
    _end_shell(shell)


def _pattern_explorer(_: Any = None) -> None:
    shell=_reference_shell('/patterns/explorer')
    with DataExplorerPage('Process Measurement Explorer','Filter → summarize → analyze → inspect without losing population context') as page:
        with page.slot(LayoutSlot.FILTERS):
            _pattern_filter_controls()
        with page.slot(LayoutSlot.METRICS):
            with MetricStrip():
                MetricCard('Population','18,402',delta='selected rows'); MetricCard('Mean CD','40.62 nm',delta='+0.31 nm')
                MetricCard('OOS','2.8%',intent=StatusIntent.WARNING,delta='516 wafers'); MetricCard('Freshness','4 min',intent=StatusIntent.SUCCESS)
        with page.slot(LayoutSlot.PRIMARY):
            LineChart('Selected parameter',(SeriesSpec('cd','CD',(39.8,40.1,40.4,41.0,40.7,41.5,41.9)),),x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('W01','W02','W03','W04','W05','W06','W07')),spec_limits=SpecLimits(lower=37.5,upper=42.5,target=40))
        with page.slot(LayoutSlot.SECONDARY):
            BarChart('Population by tool',(SeriesSpec('population','Wafers',(3420,2980,2710,2240,1980)),),x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('ETCH-021','ETCH-014','ETCH-024','CVD-007','CMP-011')))
        with page.slot(LayoutSlot.DATA):
            DataTable(_deterministic_rows(180),TABLE_COLUMNS,title='18,402 measurements · synthetic page',selection=SelectionMode.SINGLE)
        with page.slot(LayoutSlot.ACTIONS):
            Button('Save view',intent=ButtonIntent.SECONDARY,icon=Icons.SAVE,on_click=lambda:_toast('Explorer view saved',FeedbackIntent.SUCCESS))
            ActionButton('Start investigation',icon=Icons.RCA,on_click=lambda:_ui().navigate.to('/patterns/wizard'))
    _end_shell(shell)


def _pattern_master_detail(_: Any = None) -> None:
    shell=_reference_shell('/patterns/master-detail')
    with MasterDetailPage('Equipment Fleet','Browse a dense fleet while selected-equipment context stays visible') as page:
        with page.slot(LayoutSlot.FILTERS):
            _pattern_filter_controls(include_window=False)
        with page.slot(LayoutSlot.DATA):
            DataTable(_deterministic_rows(26),TABLE_COLUMNS[:7],title='Equipment signals',selection=SelectionMode.SINGLE)
        with page.slot(LayoutSlot.DETAILS, surface=PatternSurface.INSPECTOR, sticky=True, aria_label='Selected equipment detail'):
            EntityHeader('ETCH-021 / CH-3',subtitle='Etch chamber',status='Watch',status_intent=StatusIntent.WARNING,icon=Icons.CHAMBER)
            PropertyGrid((KeyValueItem('recipe','Recipe','ETCH_R18'),KeyValueItem('pm','Last PM','17 days'),KeyValueItem('health','Health','82%')))
            LineChart('Recent CD',(SeriesSpec('cd','CD',(39.8,39.9,40.2,41.0,41.4,42.0)),),x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('1','2','3','4','5','6')))
            ActionButton('Open chamber analysis',icon=Icons.RCA,on_click=lambda:_ui().navigate.to('/patterns/analysis'))
    _end_shell(shell)


def _pattern_crud(_: Any = None) -> None:
    shell=_reference_shell('/patterns/crud')
    def create_view() -> None:
        drawer=FormDrawer('New saved view', subtitle='Save a reusable investigation configuration')
        with drawer:
            TextInput('View name',placeholder='e.g. Critical chamber review')
            Select('Visibility',{'private':'Private','team':'Process team','shared':'Shared'},value='private')
            TextArea('Description',placeholder='What should this view help engineers review?')
            FormActions(primary_label='Create view',secondary_label='Cancel',on_primary=lambda *_:(drawer.close(),_toast('Saved view created',FeedbackIntent.SUCCESS)),on_secondary=lambda *_:drawer.close())
    with CrudPage('Saved Investigation Views','Create, inspect and manage reusable engineering configurations') as page:
        with page.slot(LayoutSlot.FILTERS):
            with _ui().element('div').classes('cui-pattern-filter-controls'):
                SearchInput('Search saved views',value='')
                SegmentedControl({'all':'All','mine':'Mine','shared':'Shared'},value='all')
        with page.slot(LayoutSlot.ACTIONS):
            ActionButton('New saved view',icon=Icons.ADD,on_click=create_view)
        with page.slot(LayoutSlot.DATA):
            DataTable(({'id':'v1','name':'Critical chambers','owner':'You','status':'Active'},{'id':'v2','name':'Daily yield review','owner':'You','status':'Active'},{'id':'v3','name':'PM correlation','owner':'Process team','status':'Shared'}),(TableColumn('id','ID',ColumnKind.TEXT),TableColumn('name','Name',ColumnKind.TEXT),TableColumn('owner','Owner',ColumnKind.TEXT),TableColumn('status','Status',ColumnKind.STATUS)),title='Saved views',selection=SelectionMode.SINGLE)
    _end_shell(shell)


def _pattern_monitoring(_: Any = None) -> None:
    shell=_reference_shell('/patterns/monitoring')
    with MonitoringPage('Fleet Monitoring','Operational health leads; investigation context stays one click away') as page:
        with page.slot(LayoutSlot.FILTERS):
            _pattern_filter_controls(include_tool=False)
        with page.slot(LayoutSlot.METRICS):
            with MetricStrip():
                MetricCard('Healthy',84,intent=StatusIntent.SUCCESS); MetricCard('Watch',7,intent=StatusIntent.WARNING); MetricCard('Critical',3,intent=StatusIntent.DANGER); MetricCard('Offline',2)
        with page.slot(LayoutSlot.PRIMARY):
            AreaChart('Alarm volume',(SeriesSpec('alarms','Alarms',(3,5,4,9,7,6,12,8),smooth=True),),x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=tuple(str(i) for i in range(8))))
        with page.slot(LayoutSlot.SECONDARY):
            DonutChart('Fleet state',(SeriesSpec('state','State',(('Healthy',84),('Watch',7),('Critical',3),('Offline',2))),))
        with page.slot(LayoutSlot.DETAILS, surface=PatternSurface.SUBTLE):
            Banner('3 critical tools require review',message='ETCH-021 / CH-3 has the strongest cross-signal excursion signature. Latest data is 4 minutes old.',intent=FeedbackIntent.WARNING)
        with page.slot(LayoutSlot.DATA):
            DataTable(_deterministic_rows(60),TABLE_COLUMNS,title='Latest fleet signals')
        with page.slot(LayoutSlot.ACTIONS):
            ActionButton('Review critical tool',icon=Icons.RCA,on_click=lambda:_ui().navigate.to('/patterns/analysis'))
    _end_shell(shell)


def _pattern_search(_: Any = None) -> None:
    shell=_reference_shell('/patterns/search')
    results=(SearchResultSpec('s1','ETCH-021','Tool · Watch','3 active excursions · 2 evidence packages',Icons.TOOL),SearchResultSpec('s2','ETCH-021 / CH-3','Chamber · Watch','Strong commonality with EXC-1042',Icons.CHAMBER),SearchResultSpec('s3','EXC-1042','Investigation · Active','CD drift and edge spatial signature',Icons.RCA))
    def inspect_result(result: SearchResultSpec) -> None:
        drawer=InspectorDrawer(result.title,subtitle=result.subtitle or 'Engineering search result')
        with drawer:
            EntityHeader(result.title,subtitle=result.subtitle,status='Context',status_intent=StatusIntent.INFO,icon=result.icon or Icons.SEARCH)
            DescriptionList((KeyValueItem('type','Type',result.subtitle or 'Engineering entity'),KeyValueItem('summary','Summary',result.description or 'No description'),KeyValueItem('source','Source','Company engineering index')))
            ActionButton('Open workspace',icon=Icons.FORWARD,on_click=lambda:_ui().navigate.to('/patterns/analysis' if result.key=='s3' else '/patterns/master-detail'))
    with SearchPage('Engineering Search','Search-first navigation for tools, chambers, investigations and evidence') as page:
        with page.slot(LayoutSlot.FILTERS, sticky=True):
            SearchInput('Search everything',value='ETCH-021')
            ui=_ui(); ui.label('Refine').classes('cui-field-label')
            Checkbox('Equipment',checked=True); Checkbox('Investigations',checked=True); Checkbox('Evidence',checked=True)
            Divider()
            ui.label('3 results · indexed 2 min ago').classes('cui-page-description')
        with page.slot(LayoutSlot.DATA):
            SearchResults(results,on_select=inspect_result)
    _end_shell(shell)


def _pattern_settings(_: Any = None) -> None:
    shell=_reference_shell('/patterns/settings')
    with SettingsPage('Application Settings','Stable local navigation with a restrained, readable configuration column') as page:
        with page.slot(LayoutSlot.NAVIGATION, sticky=True):
            with _ui().element('nav').classes('cui-settings-navigation').props('aria-label="Settings sections"'):
                Button('Appearance',intent=ButtonIntent.TERTIARY,icon=Icons.SETTINGS,full_width=True)
                Button('Notifications',intent=ButtonIntent.GHOST,icon=Icons.ALARM,full_width=True)
                Button('Data & refresh',intent=ButtonIntent.GHOST,icon=Icons.REFRESH,full_width=True)
                Button('About',intent=ButtonIntent.GHOST,icon=Icons.INFO,full_width=True,on_click=_reference_about)
        with page.slot(LayoutSlot.CONTENT):
            with Form('settings-demo') as form:
                with FormSection('Appearance'):
                    Select('Default theme',{'system':'System','light':'Light','dark':'Dark'},value='system')
                    Select('Density',{'comfortable':'Comfortable','compact':'Compact','dense':'Dense'},value='compact')
                with FormSection('Notifications'):
                    Switch('Excursion notifications',checked=True); Switch('Daily summary',checked=False)
                with FormSection('Data & refresh'):
                    Select('Automatic refresh',{'1m':'Every minute','5m':'Every 5 minutes','manual':'Manual'},value='5m')
                FormActions(form=form,on_primary=lambda *_:_toast('Preferences saved',FeedbackIntent.SUCCESS),on_secondary=lambda *_:_toast('Changes reverted'))
    _end_shell(shell)


def _pattern_wizard(_: Any = None) -> None:
    shell=_reference_shell('/patterns/wizard')
    def review() -> None:
        dialog=PreviewDialog('Review investigation setup',description='Control population is ready to create.',primary_label='Create investigation',secondary_label='Back',on_primary=lambda *_:_ui().navigate.to('/patterns/analysis'))
        with dialog:
            PropertyGrid((KeyValueItem('strategy','Control strategy','Exact route match'),KeyValueItem('sequence','Tool/recipe/chamber','Exact sequence required'),KeyValueItem('population','Estimated controls','215 wafers')))
    with WizardPage('Create Investigation','Guided task with visible progress, bounded decisions and a real review step') as page:
        steps=(StepSpec('scope','Scope',state=StepState.COMPLETE),StepSpec('controls','Controls',state=StepState.ACTIVE),StepSpec('review','Review'))
        with page.slot(LayoutSlot.NAVIGATION):
            ProgressSteps(steps)
        with page.slot(LayoutSlot.CONTENT, surface=PatternSurface.SURFACE):
            ui=_ui(); ui.label('Select control population').classes('cui-pattern-section-title')
            ui.label('Use the narrowest defensible comparison population before reviewing evidence.').classes('cui-page-description')
            Select('Control strategy',{'route':'Exact route match','product':'Same product','time':'Time matched'},value='route')
            Checkbox('Require exact tool / recipe / chamber sequence',checked=True)
            Checkbox('Exclude wafers processed after maintenance',checked=True)
        with page.slot(LayoutSlot.ACTIONS):
            Button('Cancel',intent=ButtonIntent.GHOST,on_click=lambda:_ui().navigate.to('/patterns/dashboard'))
            ActionButton('Review controls',icon=Icons.FORWARD,on_click=review)
    _end_shell(shell)


def _pattern_comparison(_: Any = None) -> None:
    shell=_reference_shell('/patterns/comparison')
    affected=[]
    for y in range(-5,6):
        for x in range(-5,6):
            if x*x+y*y<=29: affected.append(WaferPoint(x,y,40.2+0.08*x+0.04*y+(0.9 if x>3 else 0),'watch' if x>3 else 'normal'))
    control=[WaferPoint(p.x,p.y,float(p.value)-0.85-(0.35 if p.x>3 else 0),'normal') for p in affected]
    with ComparisonPage('Affected vs Control','Direct comparison keeps population identity, deltas and spatial evidence aligned') as page:
        with page.slot(LayoutSlot.FILTERS):
            with _ui().element('div').classes('cui-pattern-filter-controls'):
                Select('Affected population',{'exc1042':'EXC-1042 · 84 wafers'},value='exc1042')
                Select('Control population',{'matched':'Matched route · 215 wafers'},value='matched')
        with page.slot(LayoutSlot.METRICS):
            with MetricStrip(): MetricCard('Affected mean','42.18 nm',intent=StatusIntent.DANGER); MetricCard('Control mean','39.96 nm',intent=StatusIntent.SUCCESS); MetricCard('Delta','+2.22 nm',intent=StatusIntent.DANGER); MetricCard('SMD','1.42',intent=StatusIntent.WARNING)
        with page.slot(LayoutSlot.PRIMARY):
            with BeforeAfter() as compare:
                with compare.side('Affected'):
                    EntityHeader('ETCH-021 / CH-3',subtitle='84 wafers · excursion population',status='Affected',status_intent=StatusIntent.DANGER,icon=Icons.CHAMBER)
                with compare.side('Control'):
                    EntityHeader('ETCH-014 / CH-2',subtitle='215 wafers · matched route',status='Control',status_intent=StatusIntent.SUCCESS,icon=Icons.CHAMBER)
        with page.slot(LayoutSlot.SECONDARY):
            WaferComparisonMap('Spatial signature',affected,control,description='Affected edge signature vs matched control on one scale')
        with page.slot(LayoutSlot.DATA):
            DifferenceTable((ComparisonItem('tool','Tool','ETCH-021','ETCH-014',changed=True),ComparisonItem('recipe','Recipe','ETCH_R18','ETCH_R18',changed=False),ComparisonItem('chamber','Chamber','CH-3','CH-2',changed=True),ComparisonItem('cd','Mean CD','42.18','39.96',delta='+2.22',changed=True)),left_label='Affected',right_label='Control')
    _end_shell(shell)


def _pattern_analysis(_: Any = None) -> None:
    shell=_reference_shell('/patterns/analysis')
    with AnalysisWorkspacePage('Excursion Investigation — EXC-1042','Dense analytical workspace with persistent orientation and semiconductor-native evidence') as page:
        with page.slot(LayoutSlot.FILTERS, surface=PatternSurface.PLAIN, aria_label='Investigation context'):
            InvestigationContextBar(InvestigationContextSpec('EXC-1042','Chamber 3 process degradation','Process Engineering','Evidence review','2 minutes ago'))
        with page.slot(LayoutSlot.PRIMARY):
            with MetricStrip(): MetricCard('Affected','84 wafers'); MetricCard('Controls','215 wafers'); MetricCard('Confidence','High',intent=StatusIntent.SUCCESS); MetricCard('Contradictions',1,intent=StatusIntent.WARNING)
            LineChart('CD trend',(SeriesSpec('cd','CD',(39.8,40.0,40.3,41.1,41.5,42.1,42.0)),),x_axis=AxisSpec(kind=AxisType.CATEGORY,categories=('1','2','3','4','5','6','7')),spec_limits=SpecLimits(lower=37.5,upper=42.5,target=40))
        with page.slot(LayoutSlot.SECONDARY):
            CommonalityMatrix('Population commonality',('CH-3','ETCH-021','ETCH_R18','PM < 3 d'),('Affected','Control','Baseline'),((.87,.12,.18),(.91,.19,.24),(.64,.58,.55),(.72,.21,.20)))
        with page.slot(LayoutSlot.DETAILS, surface=PatternSurface.INSPECTOR, sticky=True, aria_label='Investigation summary'):
            EntityHeader('ETCH-021 / CH-3',subtitle='Leading equipment commonality',status='Watch',status_intent=StatusIntent.WARNING,icon=Icons.CHAMBER)
            PropertyGrid((KeyValueItem('recipe','Recipe','ETCH_R18'),KeyValueItem('pm','Last PM','17 days'),KeyValueItem('affected','Lots affected','12 lots'),KeyValueItem('confidence','Evidence confidence','High')))
            Banner('Working hypothesis',message='Chamber-specific process drift is supported by CD trend, spatial edge signature and affected/control enrichment.',intent=FeedbackIntent.INFO)
            ActionButton('Open RCA cockpit',icon=Icons.RCA,on_click=lambda:_ui().navigate.to('/engineering'))
        with page.slot(LayoutSlot.DATA):
            DataTable(_deterministic_rows(36),TABLE_COLUMNS,title='Affected population evidence')
    _end_shell(shell)


ROUTES = (
    LabRoute('/', 'Overview', _overview), LabRoute('/foundation', 'Foundation', _foundation), LabRoute('/shell', 'Shell primitives', _shell_primitives), LabRoute('/controls', 'Controls', _controls),
    LabRoute('/forms', 'Forms & overlays', _forms), LabRoute('/data', 'DataTable', _data), LabRoute('/charts', 'Charts', _charts),
    LabRoute('/content', 'Content', _content), LabRoute('/engineering', 'Engineering', _engineering), LabRoute('/states', 'States', _states),
    LabRoute('/performance', 'Performance', _performance),
    LabRoute('/patterns/dashboard', 'Dashboard pattern', _pattern_dashboard), LabRoute('/patterns/explorer', 'Explorer pattern', _pattern_explorer),
    LabRoute('/patterns/master-detail', 'Master detail pattern', _pattern_master_detail), LabRoute('/patterns/crud', 'CRUD pattern', _pattern_crud),
    LabRoute('/patterns/monitoring', 'Monitoring pattern', _pattern_monitoring), LabRoute('/patterns/search', 'Search pattern', _pattern_search),
    LabRoute('/patterns/settings', 'Settings pattern', _pattern_settings), LabRoute('/patterns/wizard', 'Wizard pattern', _pattern_wizard),
    LabRoute('/patterns/comparison', 'Comparison pattern', _pattern_comparison), LabRoute('/patterns/analysis', 'Analysis workspace', _pattern_analysis),
)


def register_mac_lab_pages() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    from nicegui import ui
    _lab_css()
    for route in ROUTES:
        def page_builder(_route=route):
            _route.builder(None)
        page_builder.__name__ = 'lab_' + (route.path.strip('/').replace('/','_').replace('-','_') or 'overview')
        ui.page(route.path)(page_builder)
    _REGISTERED = True


def run_mac_lab(*, host: str = '127.0.0.1', port: int = LAB_PORT, show: bool = False, root_path: str = '') -> None:
    from nicegui import app, ui
    from nicegui_base.integrations.nicegui_runtime import NiceGUIRuntimeAdapter
    from nicegui_base.runtime import ProxyConfig, RuntimeConfig, RuntimeEnvironment
    config=RuntimeConfig(app_name=LAB_TITLE,app_version=LAB_VERSION,environment=RuntimeEnvironment.TEST,host=host,port=port,title=LAB_TITLE,show_browser=show,reload=False,proxy=ProxyConfig(root_path=root_path))
    runtime=NiceGUIRuntimeAdapter(config)
    runtime.install_middleware(app); runtime.install_operational_endpoints(app)
    register_mac_lab_pages()
    kwargs=config.nicegui_run_kwargs({'NICEGUI_BASE_STORAGE_SECRET':f'nicegui-base-live-reference-v{FRAMEWORK_VERSION}'})
    ui.run(**kwargs)


__all__ = ['LAB_TITLE','LAB_APP_TITLE','LAB_APP_SUBTITLE','LAB_VERSION','LAB_PORT','LAB_NAVIGATION','LabRoute','ROUTES','register_mac_lab_pages','run_mac_lab']
