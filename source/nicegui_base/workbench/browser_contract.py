from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class BrowserViewport:
    key: str
    width: int
    height: int

    def to_dict(self) -> dict[str, object]:
        return {'key': self.key, 'width': self.width, 'height': self.height}


DEFAULT_VIEWPORTS = (
    BrowserViewport('desktop', 1440, 1000),
    BrowserViewport('tablet', 834, 1112),
    BrowserViewport('phone', 390, 844),
)

BASE_CHECKS = (
    'root_route_http_success',
    'no_uncaught_console_errors',
    'no_horizontal_document_overflow',
    'first_interactive_control_keyboard_reachable',
    'visible_focus_indicator',
    'theme_preference_survives_navigation',
    'primary_action_reachable_without_pointer_only_interaction',
)


def build_browser_acceptance_contract(project: Mapping[str, Any]) -> dict[str, object]:
    from nicegui_base.patterns.registry import get_pattern
    pattern_key = str(project.get('pattern_key') or 'analysis_workspace')
    definition = get_pattern(pattern_key)
    required_slots = [slot.value for slot in definition.required_slots if slot.value != 'header']
    allowed_slots = [slot.value for slot in definition.slot_order if slot.value != 'header']
    placements = project.get('placements') if isinstance(project.get('placements'), Mapping) else {}
    checks = list(BASE_CHECKS)
    manual_checks: list[str] = []
    if pattern_key in {'monitoring', 'dashboard'}:
        manual_checks.append('priority_status_or_metric_above_primary_analysis')
    if pattern_key in {'data_explorer', 'crud', 'search', 'master_detail'}:
        manual_checks.append('data_surface_usable_at_phone_width')
    if pattern_key in {'settings', 'wizard'}:
        manual_checks.append('form_actions_keyboard_reachable')
    if pattern_key in {'comparison', 'analysis_workspace'}:
        manual_checks.append('secondary_context_does_not_obscure_primary_workspace')
    return {
        'schema_version': 2,
        'status': 'PENDING_BROWSER_EXECUTION',
        'pattern_key': pattern_key,
        'routes': ['/'],
        'viewports': [item.to_dict() for item in DEFAULT_VIEWPORTS],
        'required_slots': required_slots,
        'allowed_slots': allowed_slots,
        'explicit_slots': sorted(str(slot) for slot, keys in placements.items() if keys),
        'checks': list(dict.fromkeys((*checks, *manual_checks))),
        'automated_checks': list(dict.fromkeys(checks)),
        'manual_checks': list(dict.fromkeys(manual_checks)),
        'runner': {'path': 'tools/browser_acceptance.py', 'command': 'python tools/browser_acceptance.py http://127.0.0.1:8080'},
        'evidence_policy': 'Only an executed browser/device run may produce PASS/FAIL evidence; HTTP/runtime smoke is not browser proof.',
    }


def validate_browser_acceptance_contract(value: Any) -> tuple[str, ...]:
    findings: list[str] = []
    if not isinstance(value, Mapping):
        return ('browser_contract:not_object',)
    schema_version = value.get('schema_version')
    if schema_version not in {1, 2}:
        findings.append('browser_contract:schema_version')
    if value.get('status') != 'PENDING_BROWSER_EXECUTION':
        findings.append('browser_contract:invalid_initial_status')
    routes = value.get('routes')
    if not isinstance(routes, list) or '/' not in routes:
        findings.append('browser_contract:missing_root_route')
    viewports = value.get('viewports')
    if not isinstance(viewports, list) or len(viewports) < 3:
        findings.append('browser_contract:viewports')
    else:
        keys = {str(item.get('key')) for item in viewports if isinstance(item, Mapping)}
        if not {'desktop', 'tablet', 'phone'} <= keys:
            findings.append('browser_contract:canonical_viewports')
    checks = value.get('checks')
    if not isinstance(checks, list) or not set(BASE_CHECKS) <= {str(item) for item in checks}:
        findings.append('browser_contract:base_checks')
    if schema_version == 2:
        automated = value.get('automated_checks')
        manual = value.get('manual_checks')
        runner = value.get('runner')
        if not isinstance(automated, list) or not set(BASE_CHECKS) <= {str(item) for item in automated}:
            findings.append('browser_contract:automated_checks')
        if not isinstance(manual, list):
            findings.append('browser_contract:manual_checks')
        if not isinstance(runner, Mapping) or runner.get('path') != 'tools/browser_acceptance.py':
            findings.append('browser_contract:runner')
    required = value.get('required_slots')
    allowed = value.get('allowed_slots')
    if not isinstance(required, list) or not isinstance(allowed, list) or not set(required) <= set(allowed):
        findings.append('browser_contract:slot_contract')
    return tuple(dict.fromkeys(findings))


__all__ = ['BASE_CHECKS', 'BrowserViewport', 'DEFAULT_VIEWPORTS', 'build_browser_acceptance_contract', 'validate_browser_acceptance_contract']
