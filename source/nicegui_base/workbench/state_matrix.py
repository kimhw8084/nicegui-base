from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class StudioState(str, Enum):
    DEFAULT = 'default'
    LOADING = 'loading'
    EMPTY = 'empty'
    NO_RESULTS = 'no_results'
    STALE = 'stale'
    PARTIAL = 'partial'
    ERROR = 'error'
    PERMISSION = 'permission'
    DISABLED = 'disabled'


@dataclass(frozen=True, slots=True)
class StateDemo:
    state: StudioState
    label: str
    description: str


STATE_DEMOS = (
    StateDemo(StudioState.DEFAULT, 'Default', 'Normal ready content.'),
    StateDemo(StudioState.LOADING, 'Loading', 'Canonical skeleton/loading treatment.'),
    StateDemo(StudioState.EMPTY, 'Empty', 'Valid request with no data yet.'),
    StateDemo(StudioState.NO_RESULTS, 'No Results', 'Data exists but current query/filter has no matches.'),
    StateDemo(StudioState.STALE, 'Stale', 'Last good content remains visible while refresh is degraded.'),
    StateDemo(StudioState.PARTIAL, 'Partial', 'Useful content is available with an explicit data-quality limitation.'),
    StateDemo(StudioState.ERROR, 'Error', 'Recoverable failure with a stable user-facing error ID.'),
    StateDemo(StudioState.PERMISSION, 'Permission', 'Server-governed access restriction state.'),
    StateDemo(StudioState.DISABLED, 'Disabled', 'Capability or action is intentionally unavailable.'),
)


class StateMatrixController:
    """Small deterministic state selector; page owns one preview host at a time.

    State switches never spawn background work, so changing from loading/error cannot
    orphan timers, overlays, or async tasks in the Workbench demonstration itself.
    """

    def __init__(self, initial: StudioState = StudioState.DEFAULT):
        self.current = initial
        self.revision = 0

    def select(self, state: StudioState | str) -> StudioState:
        self.current = StudioState(state)
        self.revision += 1
        return self.current


def render_state(state: StudioState | str, ready_content: Callable[[], None]) -> None:
    state = StudioState(state)
    from nicegui import ui
    from nicegui_base.feedback import AsyncState, FeedbackIntent
    from nicegui_base.integrations.nicegui_components import Button, StatusBadge
    from nicegui_base.integrations.nicegui_interactions import (
        Alert, AsyncContent, EmptyState, ErrorState, NoResultsState, PermissionDeniedState,
    )

    if state is StudioState.DEFAULT:
        ready_content()
        return
    if state is StudioState.LOADING:
        AsyncContent(AsyncState.LOADING, content=ready_content)
        return
    if state is StudioState.EMPTY:
        EmptyState('No data yet', message='Connect or paste development data to render this capability.')
        return
    if state is StudioState.NO_RESULTS:
        NoResultsState('No matching results', message='The current development filter has no matching rows.')
        return
    if state is StudioState.STALE:
        AsyncContent(
            AsyncState.STALE,
            content=ready_content,
            error_message='Refresh failed; showing the last successfully rendered development data.',
        )
        return
    if state is StudioState.PARTIAL:
        Alert('Partial development data', message='Some optional fields are unavailable; the supported subset remains usable.', intent=FeedbackIntent.WARNING)
        ready_content()
        return
    if state is StudioState.ERROR:
        ErrorState('Unable to render sample', message='Correct the development data or configuration and retry.', error_id='WB-DEMO-001')
        return
    if state is StudioState.PERMISSION:
        PermissionDeniedState('Access restricted', message='This demonstrates the governed permission state. Authorization must still run server-side.')
        return
    if state is StudioState.DISABLED:
        with ui.element('section').classes('cui-workbench-disabled-state').props('aria-disabled="true"'):
            StatusBadge('Disabled')
            ui.label('This action is intentionally unavailable in the current configuration.')
            Button('Unavailable action', disabled=True)
        return
    raise ValueError(state)


def render_state_matrix(host, ready_content: Callable[[], None], *, initial: StudioState = StudioState.DEFAULT) -> StateMatrixController:
    from nicegui import ui
    from nicegui_base.integrations.nicegui_layout import SegmentedControl

    controller = StateMatrixController(initial)

    def render() -> None:
        host.clear()
        with host:
            render_state(controller.current, ready_content)

    def changed(event) -> None:
        controller.select(str(getattr(event, 'value', StudioState.DEFAULT.value)))
        render()

    options = {demo.state.value: demo.label for demo in STATE_DEMOS}
    SegmentedControl(options, value=initial.value, on_change=changed)
    render()
    return controller


__all__ = ['STATE_DEMOS','StateDemo','StateMatrixController','StudioState','render_state','render_state_matrix']
