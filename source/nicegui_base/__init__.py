"""NiceGUI Base framework public surface (Phase 11)."""

from nicegui_base.design import (
    BREAKPOINTS, CANONICAL_VIEWPORTS, CONTROL_HEIGHTS, DENSITIES, MOTION, RADII, SPACING, TYPOGRAPHY,
    DesignSystem, ThemeMode, ViewportProfile, build_constitution_css, build_design_system, canonical_viewport,
)
from nicegui_base.integrations import (
    AppHeader, AppInfoDialog, AppShell, AppSidebar, BackNavigation, EnvironmentBadge,
    MobileNavigationDrawer, NiceGUIThemeAdapter, PageHeader, PageNavigation, SegmentedControl,
    ShellConfig, Tabs, UserMenu,
)
from nicegui_base.layouts import (
    Align, ContentWidth, DashboardGrid, FullScreenWorkspace, Gap, Grid, GridPreset,
    LayoutSlot, MasterDetailLayout, Page, PanelSize, ResizablePanel, ResponsiveGrid,
    ActionRow, AlertStack, ButtonCluster, ContentColumn, FormStack, SurfaceGrid, ToolbarGroup,
    ResponsiveRule, ScrollablePanel, Section, SidebarMode, SplitPane, Stack,
    StackDirection, StickyPanel, build_layout_css,
)
from nicegui_base.navigation import Breadcrumb, NavigationModel, NavItem, NavSection, TabSpec
from nicegui_base.patterns import (
    PATTERN_REGISTRY, AnalysisWorkspacePage, ComparisonPage, CrudPage, DashboardPage,
    DataExplorerPage, MasterDetailPage, MonitoringPage, PagePattern, PatternDefinition, PatternSurface,
    PatternPage, SearchPage, SettingsPage, WizardPage, get_pattern,
)

__all__ = [
    'BREAKPOINTS', 'CANONICAL_VIEWPORTS', 'CONTROL_HEIGHTS', 'DENSITIES', 'MOTION', 'RADII', 'SPACING', 'TYPOGRAPHY',
    'ViewportProfile', 'canonical_viewport',
    'DesignSystem', 'ThemeMode', 'build_constitution_css', 'build_design_system', 'NiceGUIThemeAdapter',
    'AppHeader', 'AppInfoDialog', 'AppShell', 'AppSidebar', 'BackNavigation', 'EnvironmentBadge',
    'MobileNavigationDrawer', 'PageHeader', 'PageNavigation', 'SegmentedControl', 'ShellConfig', 'Tabs', 'UserMenu',
    'Align', 'ContentWidth', 'DashboardGrid', 'FullScreenWorkspace', 'Gap', 'Grid', 'GridPreset', 'LayoutSlot',
    'MasterDetailLayout', 'Page', 'PanelSize', 'ResizablePanel', 'ResponsiveGrid', 'ResponsiveRule',
    'ActionRow', 'AlertStack', 'ButtonCluster', 'ContentColumn', 'FormStack', 'SurfaceGrid', 'ToolbarGroup',
    'ScrollablePanel', 'Section', 'SidebarMode', 'SplitPane', 'Stack', 'StackDirection', 'StickyPanel', 'build_layout_css',
    'Breadcrumb', 'NavigationModel', 'NavItem', 'NavSection', 'TabSpec',
    'PATTERN_REGISTRY', 'PagePattern', 'PatternDefinition', 'PatternPage', 'PatternSurface', 'get_pattern',
    'AnalysisWorkspacePage', 'ComparisonPage', 'CrudPage', 'DashboardPage', 'DataExplorerPage',
    'MasterDetailPage', 'MonitoringPage', 'SearchPage', 'SettingsPage', 'WizardPage',
]

# Phase 3 component public surface
from nicegui_base.components import (
    COMPONENT_REGISTRY, ActionButtonSpec, AutocompleteSpec, BadgeSpec, ButtonIntent, ButtonSpec,
    CheckboxGroupSpec, CheckboxSpec, ComboboxSpec, ComponentDefinition, ComponentSize, ControlState,
    DatePickerSpec, DatePrecision, DateRangePickerSpec, DateTimePickerSpec, FieldSpec, FileUploadSpec,
    IconButtonSpec, InputWidth, MultiSelectSpec, NumberInputSpec, RadioGroupSpec, RangeSliderSpec,
    SearchInputSpec, SelectOption, SelectSpec, SliderSpec, StatusIntent, SurfaceSpec, SurfaceVariant,
    SwitchSpec, TextAreaSpec, TextInputSpec, TimePickerSpec, build_component_css, get_component,
)
from nicegui_base.integrations import (
    ActionButton, Autocomplete, Button, Card, Checkbox, CheckboxGroup, Combobox, DatePicker,
    DateRangePicker, DateTimePicker, FileUpload, IconButton, InteractiveCard, MultiSelect, NumberInput,
    Panel, PasswordInput, RadioGroup, RangeSlider, SearchInput, Select, Slider, StatusBadge, Switch,
    Tag, TextArea, TextInput, TimePicker, Well,
)

__all__ += [
    'COMPONENT_REGISTRY','ActionButtonSpec','AutocompleteSpec','BadgeSpec','ButtonIntent','ButtonSpec',
    'CheckboxGroupSpec','CheckboxSpec','ComboboxSpec','ComponentDefinition','ComponentSize','ControlState',
    'DatePickerSpec','DatePrecision','DateRangePickerSpec','DateTimePickerSpec','FieldSpec','FileUploadSpec',
    'IconButtonSpec','InputWidth','MultiSelectSpec','NumberInputSpec','RadioGroupSpec','RangeSliderSpec',
    'SearchInputSpec','SelectOption','SelectSpec','SliderSpec','StatusIntent','SurfaceSpec','SurfaceVariant',
    'SwitchSpec','TextAreaSpec','TextInputSpec','TimePickerSpec','build_component_css','get_component',
    'ActionButton','Autocomplete','Button','Card','Checkbox','CheckboxGroup','Combobox','DatePicker',
    'DateRangePicker','DateTimePicker','FileUpload','IconButton','InteractiveCard','MultiSelect','NumberInput',
    'Panel','PasswordInput','RadioGroup','RangeSlider','SearchInput','Select','Slider','StatusBadge','Switch',
    'Tag','TextArea','TextInput','TimePicker','Well',
]
from nicegui_base.components import ChipSpec, CountBadgeSpec, DataQuality, DataQualityBadgeSpec, FreshnessIndicatorSpec
from nicegui_base.integrations import Accordion, ButtonGroup, Chip, CollapsiblePanel, CountBadge, DataQualityBadge, Divider, FreshnessIndicator, SeverityIndicator, SplitButton
__all__ += ['ChipSpec','CountBadgeSpec','DataQuality','DataQualityBadgeSpec','FreshnessIndicatorSpec','Accordion','ButtonGroup','Chip','CollapsiblePanel','CountBadge','DataQualityBadge','Divider','FreshnessIndicator','SeverityIndicator','SplitButton']


# Phase 4 interaction public surface
from nicegui_base.forms import (
    DirtyStateGuardSpec, FieldValidation, FormActionsSpec, FormFieldSpec, FormSectionSpec, FormSpec, FormState,
    ValidationIssue, ValidationSeverity, ValidationSummarySpec, min_length, numeric_range, pattern, required,
)
from nicegui_base.filters import (
    ActiveFilter, FilterBarSpec, FilterDefinition, FilterKind, FilterPersistence, FilterPreset, SavedFilterView as SavedFilterViewSpec,
)
from nicegui_base.feedback import (
    AlertSpec, AsyncContentSpec, AsyncState, BannerSpec, FeedbackIntent, ProgressSpec, SkeletonSpec,
    StateKind, StateViewSpec, ToastPlacement, ToastSpec,
)
from nicegui_base.overlays import (
    DialogIntent, DialogSpec, DrawerSide, DrawerSpec, MenuItemSpec, MenuSpec, OverlayLayer, OverlayRole, OverlaySize,
    PopoverSpec, TooltipSpec,
)
from nicegui_base.interaction_css import build_interaction_css
from nicegui_base.integrations import (
    ActionMenu, ActivityDrawer, AdvancedFilterDrawer, Alert, AsyncContent, Banner, ConfirmDialog, ContextMenu,
    DangerConfirmDialog, DetailDrawer, Dialog, DirtyStateGuard, DropdownMenu, EmptyState, ErrorState, FilterBar,
    FilterChip, FilterDrawer, FilterPresetSelector, Form, FormActions, FormDialog, FormField, FormDrawer, FormSection,
    FullScreenDialog, InspectorDrawer, NoResultsState, NotFoundState, OfflineState, PermissionDeniedState, Popover,
    PreviewDialog, ProgressBar, ResponsiveDrawer, SavedFilterView, Skeleton, Spinner, StateView, Toast, Tooltip,
    ValidationMessage, ValidationSummary,
)
__all__ += [
    'DirtyStateGuardSpec','FieldValidation','FormActionsSpec','FormFieldSpec','FormSectionSpec','FormSpec','FormState','ValidationIssue',
    'ValidationSeverity','ValidationSummarySpec','min_length','numeric_range','pattern','required',
    'ActiveFilter','FilterBarSpec','FilterDefinition','FilterKind','FilterPersistence','FilterPreset','SavedFilterViewSpec',
    'AlertSpec','AsyncContentSpec','AsyncState','BannerSpec','FeedbackIntent','ProgressSpec','SkeletonSpec','StateKind',
    'StateViewSpec','ToastPlacement','ToastSpec','DialogIntent','DialogSpec','DrawerSide','DrawerSpec','MenuItemSpec',
    'MenuSpec','OverlayLayer','OverlayRole','OverlaySize','PopoverSpec','TooltipSpec','build_interaction_css',
    'ActionMenu','ActivityDrawer','AdvancedFilterDrawer','Alert','AsyncContent','Banner','ConfirmDialog','ContextMenu',
    'DangerConfirmDialog','DetailDrawer','Dialog','DirtyStateGuard','DropdownMenu','EmptyState','ErrorState','FilterBar',
    'FilterChip','FilterDrawer','FilterPresetSelector','Form','FormActions','FormDialog','FormField','FormDrawer','FormSection',
    'FullScreenDialog','InspectorDrawer','NoResultsState','NotFoundState','OfflineState','PermissionDeniedState','Popover',
    'PreviewDialog','ProgressBar','ResponsiveDrawer','SavedFilterView','Skeleton','Spinner','StateView','Toast','Tooltip',
    'ValidationMessage','ValidationSummary',
]
from nicegui_base.interaction_registry import INTERACTION_REGISTRY, InteractionDefinition, get_interaction
__all__ += ['INTERACTION_REGISTRY','InteractionDefinition','get_interaction']

# Phase 5 enterprise DataTable public surface
from nicegui_base.data_table import (
    BulkAction, ColumnKind, ConditionalRule, DataTableSpec, EditCommitMode, EditableTableSpec, FilterGroup, FilterLogic, FilterOperator, FilterSpec,
    PaginationMode, PinPosition, RowAction, SelectionMode, ServerDataTableSpec, SortDirection, SortSpec,
    TABLE_REGISTRY, TableColumn, TableDefinition, TableDensity, TablePreset, TableQuery, TableResult, TableState, TableViewSnapshot,
    apply_query, build_data_table_css, export_csv, format_cell, get_table,
)
from nicegui_base.integrations import (
    ConditionalCellFormatter, DataTable, EditableTable, ExpandableRow, MasterDetailTable, ServerDataTable,
    SparklineCell, StatusCell, TableColumnManager, TableContextMenu, TableDensitySelector, TablePresetSelector,
    TableRowActions, TableSelectionBar, TableToolbar,
)
__all__ += [
    'BulkAction','ColumnKind','ConditionalRule','DataTableSpec','EditCommitMode','EditableTableSpec','FilterGroup','FilterLogic','FilterOperator','FilterSpec',
    'PaginationMode','PinPosition','RowAction','SelectionMode','ServerDataTableSpec','SortDirection','SortSpec',
    'TABLE_REGISTRY','TableColumn','TableDefinition','TableDensity','TablePreset','TableQuery','TableResult','TableState','TableViewSnapshot',
    'apply_query','build_data_table_css','export_csv','format_cell','get_table','ConditionalCellFormatter','DataTable',
    'EditableTable','ExpandableRow','MasterDetailTable','ServerDataTable','SparklineCell','StatusCell','TableColumnManager',
    'TableContextMenu','TableDensitySelector','TablePresetSelector','TableRowActions','TableSelectionBar','TableToolbar',
]

# Phase 6 visualization public surface
from nicegui_base.visualization import (
    AnnotationIntent, AxisSpec, AxisType, CATEGORICAL, ChartAnnotation, ChartEvent, ChartKind, ChartPanelSpec,
    ChartSize, ChartTheme, ChartToolbarSpec, CrossFilterBinding, CrossFilterEngine, DIVERGING, FilterMutation, FilterMutationAction, LinkedAnalysisController,
    LegendPosition, LineStyle, MarkerShape, SelectionMode as ChartSelectionMode, SEQUENTIAL_BLUE, SeriesSpec,
    SpatialPoint, SpecLimits, ThresholdSpec, VISUALIZATION_REGISTRY, WaferPoint, box_summary, build_echarts_options,
    build_visualization_css, chart_theme, get_visualization, histogram, pareto, series_rows, spatial_bounds, stable_series_color,
    wafer_bounds,
)
from nicegui_base.integrations.nicegui_visualization import (
    AreaChart, BarChart, BoxPlot, ChartBrush, ChartCrossFilter, ChartDataView, ChartExport, ChartFullscreen,
    ChartLegend, ChartPanel, ChartSelection, ChartToolbar, ChartTooltip, ChartZoom, ControlChart, DistributionPanel,
    DonutChart, Gauge, Heatmap, Histogram, LineChart, ParetoChart, PlotlyPanel, ProcessTrendPanel, ScatterChart, SpatialMap, WaferComparisonMap, ChamberFingerprintMatrix, CommonalityMatrix, RadialProfilePlot,
    StackedBarChart, TimelineChart, WaferMap,
)

__all__ = [name for name in globals() if not name.startswith('_')]


# Phase 7 visual asset public surface
from nicegui_base.visual import (
    ICON_ALIASES, ICON_REGISTRY, ILLUSTRATION_REGISTRY, ICON_SIZE_PX, Icons, Illustrations, AssetValidationIssue, IconCategory, IconDefinition, IconSize, IllustrationDefinition, VISUAL_ROOT, build_visual_asset_css, get_icon, get_illustration, icon_path, illustration_path, render_icon_svg, render_illustration_svg, resolve_icon_key, search_icons, validate_svg_file, validate_visual_package,
)
from nicegui_base.integrations.nicegui_visual_assets import SvgIcon, StateIllustration, install_visual_assets_css
__all__ = [name for name in globals() if not name.startswith('_')]

# Phase 8 state, services and asynchronous convenience public surface
from nicegui_base.state import BrowserState, PageState, PageStatus, SessionState, SidebarPreference, StateScope, StateStore, TabState, UrlField, UrlState, UserPreferences
from nicegui_base.async_tools import AsyncAction, AsyncLoader, AutoRefreshController, CancelableTask, Debouncer, DuplicatePolicy, ProgressSnapshot, ProgressTask, RefreshStatus, StaleResponseGuard, TaskStatus, Throttler
from nicegui_base.services import ClipboardService, DownloadRequest, DownloadService, KeyboardShortcut, KeyboardShortcutRegistry, NavigationService, NavigationTarget, NotificationService, PreferenceService, ThemeService, normalize_shortcut
from nicegui_base.integrations.nicegui_state import NiceGUIStateServices
__all__ = [name for name in globals() if not name.startswith('_')]
from nicegui_base.services import DialogRequest, DialogService, ErrorService, LoggingService, UserFacingError
__all__ = [name for name in globals() if not name.startswith('_')]
from nicegui_base.convenience_registry import CONVENIENCE_REGISTRY, ConvenienceDefinition, get_convenience
__all__ = [name for name in globals() if not name.startswith('_')]

# Phase 9 semiconductor/engineering reusable layer
from nicegui_base.engineering import *
from nicegui_base.integrations.nicegui_engineering import BaselineComparison as BaselineComparisonView, CommonalityTable, ConfidenceIndicator, EngineeringEntityCard, EngineeringProcessTrend, InvestigationContextBar, EngineeringStatusBadge, EngineeringTimeline, EvidenceCard, OutOfSpecIndicator, PopulationComparisonPanel, RcaEvidencePanel, SpecLimitIndicator
__all__ = [name for name in globals() if not name.startswith('_')]


# Phase 10 security, diagnostics and runtime hardening
from nicegui_base.security import *
from nicegui_base.data_engine import *
from nicegui_base.runtime import *
from nicegui_base.diagnostics import *
from nicegui_base.integrations.nicegui_runtime import NiceGUIRuntimeAdapter
__all__ = [name for name in globals() if not name.startswith('_')]

# Phase 11 Gemma/OpenCode construction contract and static validator
from nicegui_base.ai import (
    AI_CONSTRUCTION_REGISTRY, FRAMEWORK_REGISTRY_COUNTS, ValidatorConfig,
    AgentContextPack, AgentPreflightReport, AgentRecommendation, build_agent_context, get_ai_construction, install_ai_materials,
    load_ai_manifest, load_framework_catalog, read_ai_guide, render_agent_context, run_agent_preflight, validate_app, validate_python_file,
)
__all__ = [name for name in globals() if not name.startswith('_')]

# Phase 12 full integration and certification
from nicegui_base.certification import *
__all__=[name for name in globals() if not name.startswith('_')]

# Phase 13 production hardening
from nicegui_base.version import FRAMEWORK_VERSION, NICEGUI_VERSION, RELEASE_STATUS
from nicegui_base.performance import *
from nicegui_base.services import ApplicationServices, Command, CommandRegistry, WorkspacePreferenceService
from nicegui_base.data_table import TableQueryEngine
__all__=[name for name in globals() if not name.startswith('_')]

# v1.2 production-completion content and workflow surface
from nicegui_base.content import *
from nicegui_base.integrations import (
    ActivityFeed, BackgroundTaskIndicator, BeforeAfter, CodeViewer, CommandPalette, ComparePanel, ComparisonMetric,
    DeltaIndicator, DescriptionList, DifferenceTable, EntityHeader, ImageViewer, JsonViewer, KeyValueList,
    LogViewer, MarkdownViewer, MetricCard, MetricStrip, ProgressMetric, ProgressSteps, PropertyGrid,
    SearchResults, Stepper, TreeView, TrendIndicator, NotificationCenter,
)
__all__=[name for name in globals() if not name.startswith('_')]

# v1.2 durable job boundary
from nicegui_base.jobs import *
__all__=[name for name in globals() if not name.startswith('_')]

from nicegui_base.supply_chain import build_spdx_sbom, build_provenance, sha256_file
__all__=[name for name in globals() if not name.startswith('_')]

# v2 governance public surface
from nicegui_base.governance import GovernanceFinding, GovernanceReport, export_digest, export_names, run_governance
__all__ += ['GovernanceFinding','GovernanceReport','export_digest','export_names','run_governance','RELEASE_STATUS']

# v3 application-platform surface
from nicegui_base.workspace import *
from nicegui_base.extensions import *
from nicegui_base.visualization.semantic import SemanticVisualData, SemanticVisualPlan, SemanticVisualSpec, SemanticVisualizationPlanner, VisualIntent
__all__=[name for name in globals() if not name.startswith('_')]

# Wave 59 provider-neutral production data platform
from nicegui_base.data_sources import (
    AggregateFunction, AggregateQuery, AggregateResult, AggregationSpec, And, Between, Comparison,
    ComparisonOperator, CSVDataSource, DATA_SOURCE_PROVIDERS, DBAPIDataSource, DataSchema, DataSource,
    DataSourceProviderDefinition, DataSourceRegistry, DistinctResult, FieldRole, FieldType, FilterExpression,
    In, InMemoryDataSource, IsNull, Not, Or, Query, QueryResult, QuerySort, QueryStats, SemanticField,
    SortDirection as QuerySortDirection, SourceCapabilities, SourceHealth, SourceHealthStatus, SourceProvenance,
    SQLiteDataSource, TextMatch, TextMatchMode, fields_in_filter, infer_field_type,
)
__all__=[name for name in globals() if not name.startswith('_')]

# Wave 60 shared analysis, crossfilter, analytical-panel, and interactive workspace platform
from nicegui_base.analysis import *
from nicegui_base.integrations import AnalyticalPanel, DataSourceTable, NiceGUIWorkspace
__all__=[name for name in globals() if not name.startswith('_')]

# Wave 61 semiconductor semantic platform and engineering analytics library
from nicegui_base.semiconductor import *
from nicegui_base.integrations.nicegui_semiconductor import SemiconductorAnalyticalPanel, SemiconductorDeploymentReadinessPanel, SemiconductorOnboardingPanel, SemiconductorPostPromotionVerificationPanel, SemiconductorPostReleaseStabilityPanel, SemiconductorSustainedOperationsAcceptancePanel, SemiconductorIncidentRollbackAuditClosurePanel, SemiconductorSustainedOperationsRenewalPanel, SemiconductorOperationalAssuranceContinuityPanel, SemiconductorOperationalAssuranceRenewalLedgerPanel, SemiconductorLongitudinalAssuranceDossierPanel, SemiconductorLongitudinalAssuranceReviewPanel, SemiconductorEvidenceExceptionGovernancePanel, SemiconductorPromotionCandidatePanel, SemiconductorPromotionExecutionAdapterQualificationPanel, SemiconductorPromotionOperationalHandoffPanel, SemiconductorReleaseAuditClosurePanel, SemiconductorRollbackReadinessPanel, SemiconductorRuntimeStatusPanel, SemiconductorSetupWizard, SemiconductorTargetExecutionIntakePanel, SemiconductorStablePromotionClosurePanel, SemiconductorStableReleaseEvidenceAcceptancePanel, SemiconductorStableReleasePublicationPanel
__all__=[name for name in globals() if not name.startswith('_')]
