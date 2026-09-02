from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

INTERACTION_SCHEMA_VERSION = 1
STATE_SCOPE = 'tab'
PROVIDER_MUTATION_POLICY = 'none'


@dataclass(frozen=True, slots=True)
class WorkflowActionSpec:
    key: str
    label: str
    effect: str
    persistence: str = 'tab'
    provider_mutation: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            'key': self.key,
            'label': self.label,
            'effect': self.effect,
            'persistence': self.persistence,
            'provider_mutation': self.provider_mutation,
        }


_BASE_REFRESH = WorkflowActionSpec('refresh', 'Refresh', 'Refresh view freshness and notify dependent analysis surfaces.')
_BASE_RESET = WorkflowActionSpec('reset_view', 'Reset view', 'Clear search, filters and current selections.')
_CLEAR_SELECTION = WorkflowActionSpec('clear_selection', 'Clear selection', 'Clear the shared SelectionBus without changing provider data.')
_SAVE_VIEW = WorkflowActionSpec('save_view', 'Save view', 'Save current view context in tab-scoped workflow state.', 'tab')
_ACKNOWLEDGE = WorkflowActionSpec('acknowledge', 'Acknowledge', 'Record acknowledgement in tab state; no provider write occurs.')
_START_DRAFT = WorkflowActionSpec('start_draft', 'New draft', 'Start a local draft workflow without mutating the provider.')
_DISCARD_DRAFT = WorkflowActionSpec('discard_draft', 'Discard draft', 'Discard only the local draft state; provider data is untouched.')
_SAVE_PREFERENCES = WorkflowActionSpec('save_preferences', 'Save preferences', 'Save a generated-app settings checkpoint in tab-scoped workflow state.', 'tab')
_PREVIOUS_STEP = WorkflowActionSpec('previous_step', 'Previous step', 'Move the tab-local guided workflow to the previous step.')
_NEXT_STEP = WorkflowActionSpec('next_step', 'Next step', 'Advance the tab-local guided workflow to the next step.')
_RESET_WORKFLOW = WorkflowActionSpec('reset_workflow', 'Reset workflow', 'Return the tab-local guided workflow to step one.')
_SWAP_FOCUS = WorkflowActionSpec('swap_focus', 'Swap focus', 'Toggle comparison focus between the two logical populations.')

_PATTERN_ACTIONS: dict[str, tuple[WorkflowActionSpec, ...]] = {
    'dashboard': (_BASE_REFRESH, _BASE_RESET, _SAVE_VIEW),
    'monitoring': (_BASE_REFRESH, _BASE_RESET, _CLEAR_SELECTION, _ACKNOWLEDGE),
    'data_explorer': (_BASE_REFRESH, _BASE_RESET, _CLEAR_SELECTION, _SAVE_VIEW),
    'master_detail': (_BASE_REFRESH, _BASE_RESET, _CLEAR_SELECTION),
    'analysis_workspace': (_BASE_REFRESH, _BASE_RESET, _CLEAR_SELECTION, _SAVE_VIEW),
    'comparison': (_BASE_REFRESH, _BASE_RESET, _CLEAR_SELECTION, _SWAP_FOCUS),
    'crud': (_BASE_REFRESH, _BASE_RESET, _START_DRAFT, _DISCARD_DRAFT),
    'search': (_BASE_REFRESH, _BASE_RESET, _CLEAR_SELECTION, _SAVE_VIEW),
    'settings': (_SAVE_PREFERENCES, _BASE_RESET),
    'wizard': (_PREVIOUS_STEP, _NEXT_STEP, _RESET_WORKFLOW),
}


def action_specs_for_pattern(pattern_key: str) -> tuple[WorkflowActionSpec, ...]:
    try:
        return _PATTERN_ACTIONS[str(pattern_key)]
    except KeyError as exc:
        raise KeyError(f'no governed interaction contract for pattern {pattern_key!r}') from exc


def _page_rows(project: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    pages = project.get('pages') if isinstance(project.get('pages'), (list, tuple)) else ()
    if pages:
        result: list[dict[str, str]] = []
        for page in pages:
            if not isinstance(page, Mapping):
                continue
            result.append({
                'module': str(page.get('module') or ''),
                'route': str(page.get('route') or ''),
                'pattern_key': str(page.get('pattern_key') or ''),
            })
        if result:
            return tuple(result)
    return ({
        'module': 'home',
        'route': '/',
        'pattern_key': str(project.get('pattern_key') or ''),
    },)


def _signature_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        schema_version = int(value.get('schema_version') or 0)
    except (TypeError, ValueError, OverflowError):
        schema_version = 0
    return {
        'schema_version': schema_version,
        'state_scope': str(value.get('state_scope') or ''),
        'provider_mutation_policy': str(value.get('provider_mutation_policy') or ''),
        'pages': value.get('pages') if isinstance(value.get('pages'), list) else [],
        'workflow_boundary': str(value.get('workflow_boundary') or ''),
    }


def interaction_contract_for_project(project: Mapping[str, Any]) -> dict[str, object]:
    pages: list[dict[str, object]] = []
    for page in _page_rows(project):
        pattern_key = page['pattern_key']
        actions = action_specs_for_pattern(pattern_key)
        pages.append({
            'module': page['module'],
            'route': page['route'],
            'pattern_key': pattern_key,
            'actions': [action.to_dict() for action in actions],
        })
    contract: dict[str, object] = {
        'schema_version': INTERACTION_SCHEMA_VERSION,
        'state_scope': STATE_SCOPE,
        'provider_mutation_policy': PROVIDER_MUTATION_POLICY,
        'workflow_boundary': 'services.app_workflow:create_page_workflow',
        'pages': pages,
    }
    contract['contract_signature'] = hashlib.sha256(
        json.dumps(_signature_payload(contract), sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    return contract


def validate_interaction_contract(value: Any) -> tuple[str, ...]:
    findings: list[str] = []
    if not isinstance(value, Mapping):
        return ('interaction_contract:not_object',)
    if value.get('schema_version') != INTERACTION_SCHEMA_VERSION:
        findings.append('interaction_contract:schema_version')
    if value.get('state_scope') != STATE_SCOPE:
        findings.append('interaction_contract:state_scope')
    if value.get('provider_mutation_policy') != PROVIDER_MUTATION_POLICY:
        findings.append('interaction_contract:provider_mutation_policy')
    if value.get('workflow_boundary') != 'services.app_workflow:create_page_workflow':
        findings.append('interaction_contract:workflow_boundary')
    pages = value.get('pages')
    if not isinstance(pages, list) or not pages:
        findings.append('interaction_contract:pages')
        pages = []
    routes: list[str] = []
    modules: list[str] = []
    for page in pages:
        if not isinstance(page, Mapping):
            findings.append('interaction_contract:page_not_object'); continue
        route = str(page.get('route') or '')
        module = str(page.get('module') or '')
        pattern = str(page.get('pattern_key') or '')
        routes.append(route); modules.append(module)
        try:
            canonical = action_specs_for_pattern(pattern)
        except KeyError:
            findings.append(f'interaction_contract:unknown_pattern:{pattern}')
            canonical = ()
        actions = page.get('actions')
        if not isinstance(actions, list):
            findings.append(f'interaction_contract:actions:{module}')
            continue
        expected = [action.to_dict() for action in canonical]
        if actions != expected:
            findings.append(f'interaction_contract:canonical_actions:{module}')
        if any(bool(action.get('provider_mutation')) for action in actions if isinstance(action, Mapping)):
            findings.append(f'interaction_contract:provider_mutation:{module}')
    if len(routes) != len(set(routes)):
        findings.append('interaction_contract:duplicate_routes')
    if len(modules) != len(set(modules)):
        findings.append('interaction_contract:duplicate_modules')
    signature = str(value.get('contract_signature') or '')
    expected_signature = hashlib.sha256(
        json.dumps(_signature_payload(value), sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    if signature != expected_signature:
        findings.append('interaction_contract:signature_mismatch')
    return tuple(dict.fromkeys(findings))


def _workflow_source() -> str:
    return '''from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from nicegui_base import AnalysisContext, NiceGUIStateServices, SelectionBus


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


class AppWorkflow:
    """Generated interaction controller backed only by NiceGUI Base canonical state/services.

    This controller intentionally performs no production-provider mutations. CRUD-like
    actions are local draft state until the application team replaces/extends them with
    an approved write service.
    """
    def __init__(self, context: AnalysisContext, selections: SelectionBus, *, route: str, pattern_key: str):
        self.context = context
        self.selections = selections
        self.route = route
        self.pattern_key = pattern_key
        # Storage/notification adapters are resolved lazily inside event callbacks.
        # app.storage.tab requires a connected client and must not be touched while
        # the initial page is still being built.

    @property
    def state(self):
        return NiceGUIStateServices.tab_state()

    @property
    def notifications(self):
        return NiceGUIStateServices.notification_service()

    def _key(self, name: str) -> str:
        return f'workflow:{self.route}:{name}'

    def _set(self, name: str, value: Any) -> Any:
        self.state[self._key(name)] = value
        return value

    def execute(self, action_id: str, event: Any = None) -> None:
        handlers = {
            'refresh': self.refresh,
            'reset_view': self.reset_view,
            'clear_selection': self.clear_selection,
            'save_view': self.save_view,
            'acknowledge': self.acknowledge,
            'start_draft': self.start_draft,
            'discard_draft': self.discard_draft,
            'save_preferences': self.save_preferences,
            'previous_step': self.previous_step,
            'next_step': self.next_step,
            'reset_workflow': self.reset_workflow,
            'swap_focus': self.swap_focus,
        }
        try:
            handler = handlers[str(action_id)]
        except KeyError as exc:
            raise KeyError(f'unknown generated workflow action: {action_id!r}') from exc
        handler()

    def refresh(self) -> None:
        revision = int(self.state.get(self._key('refresh_revision'), 0) or 0) + 1
        self._set('refresh_revision', revision)
        now = _utc_now()
        self.context.set_freshness(as_of=now, freshness_at=now)
        self.notifications.success('View refreshed')

    def reset_view(self) -> None:
        with self.context.transaction():
            self.context.clear_filters()
            self.context.set_search('')
        self.selections.clear(source='generated-workflow-reset')
        self._set('comparison_focus', 'affected')
        self.notifications.notify('View reset')

    def clear_selection(self) -> None:
        self.selections.clear(source='generated-workflow')
        self.notifications.notify('Selection cleared')

    def save_view(self) -> None:
        self._set('saved_view', {
            'route': self.route, 'search': self.context.search,
            'filters': [repr(item) for item in self.context.filters], 'saved_at': _utc_now(),
        })
        self.notifications.success('View saved for this tab')

    def acknowledge(self) -> None:
        self._set('acknowledged_at', _utc_now())
        self.notifications.success('Current view acknowledged')

    def start_draft(self) -> None:
        self._set('draft_open', True)
        self._set('draft_started_at', _utc_now())
        self.notifications.notify('Local draft started')

    def discard_draft(self) -> None:
        self._set('draft_open', False)
        self.notifications.warning('Local draft discarded; provider data was not changed')

    def save_preferences(self) -> None:
        self._set('preferences_checkpoint', {
            'route': self.route, 'saved_at': _utc_now(), 'pattern_key': self.pattern_key,
        })
        self.notifications.success('Preferences checkpoint saved for this tab')

    def previous_step(self) -> None:
        step = max(1, int(self.state.get(self._key('wizard_step'), 1) or 1) - 1)
        self._set('wizard_step', step)
        self.notifications.notify(f'Workflow step {step}')

    def next_step(self) -> None:
        step = int(self.state.get(self._key('wizard_step'), 1) or 1) + 1
        self._set('wizard_step', step)
        self.notifications.notify(f'Workflow step {step}')

    def reset_workflow(self) -> None:
        self._set('wizard_step', 1)
        self.notifications.notify('Workflow reset to step 1')

    def swap_focus(self) -> None:
        current = str(self.state.get(self._key('comparison_focus'), 'affected') or 'affected')
        next_value = 'control' if current == 'affected' else 'affected'
        self._set('comparison_focus', next_value)
        self.notifications.notify(f'Comparison focus: {next_value}')


def create_page_workflow(context: AnalysisContext, selections: SelectionBus, *, route: str, pattern_key: str) -> AppWorkflow:
    return AppWorkflow(context, selections, route=route, pattern_key=pattern_key)
'''


def materialize_interaction_contract(root: Path, project: Mapping[str, Any]) -> tuple[dict[str, object], tuple[Path, ...], dict[str, str]]:
    contract = interaction_contract_for_project(project)
    findings = validate_interaction_contract(contract)
    if findings:
        raise ValueError('generated interaction contract is invalid: ' + '; '.join(findings))
    written: list[Path] = []
    sources: dict[str, str] = {}

    meta = root / '.nicegui_base' / 'interaction_contract.json'
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps(contract, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    written.append(meta)

    workflow = root / 'services' / 'app_workflow.py'
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow_source = _workflow_source()
    workflow.write_text(workflow_source, encoding='utf-8')
    written.append(workflow); sources['services/app_workflow.py'] = workflow_source

    test_path = root / 'tests' / 'test_project_contract.py'
    existing = test_path.read_text(encoding='utf-8') if test_path.is_file() else ''
    addition = '''

def test_generated_interaction_contract() -> None:
    import json
    from pathlib import Path
    contract = json.loads((Path(__file__).resolve().parents[1] / '.nicegui_base' / 'interaction_contract.json').read_text())
    assert contract['state_scope'] == 'tab'
    assert contract['provider_mutation_policy'] == 'none'
    assert contract['workflow_boundary'] == 'services.app_workflow:create_page_workflow'
    assert contract['pages']
    assert all(page['actions'] for page in contract['pages'])
    assert all(not action['provider_mutation'] for page in contract['pages'] for action in page['actions'])
'''
    test_path.write_text(existing.rstrip() + '\n' + addition, encoding='utf-8')
    written.append(test_path); sources['tests/test_project_contract.py'] = test_path.read_text(encoding='utf-8')

    readme = root / 'README.md'
    existing_readme = readme.read_text(encoding='utf-8') if readme.is_file() else '# Generated NiceGUI Base application\n'
    section = '''

## Interaction workflow boundary

Generated pages are wired to `services/app_workflow.py::create_page_workflow()` using NiceGUI Base `AnalysisContext`, `SelectionBus`, `NiceGUIStateServices`, tab state and notification service.

The generated workflow intentionally performs **no production-provider mutations**. CRUD-shaped pages use local draft state only. Tab storage is resolved lazily from action callbacks so initial page construction does not require a storage secret or socket-backed tab state. Add approved write operations behind an application service after connecting the production provider; do not put database mutation logic in page modules.
'''
    if '## Interaction workflow boundary' not in existing_readme:
        readme.write_text(existing_readme.rstrip() + section + '\n', encoding='utf-8')
        written.append(readme)

    return contract, tuple(dict.fromkeys(written)), sources


__all__ = [
    'INTERACTION_SCHEMA_VERSION', 'PROVIDER_MUTATION_POLICY', 'STATE_SCOPE', 'WorkflowActionSpec',
    'action_specs_for_pattern', 'interaction_contract_for_project', 'materialize_interaction_contract',
    'validate_interaction_contract',
]
