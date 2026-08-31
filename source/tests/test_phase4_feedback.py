import pytest

from nicegui_base import (
    AlertSpec, AsyncContentSpec, AsyncState, FeedbackIntent, ProgressSpec, SkeletonSpec, StateKind, StateViewSpec, ToastSpec,
)


def test_alert_intent_class_is_semantic():
    assert 'cui-alert--warning' in AlertSpec('Stale data', intent=FeedbackIntent.WARNING).classes


def test_progress_validates_fraction():
    with pytest.raises(ValueError):
        ProgressSpec(value=1.4)


def test_progress_rejects_value_with_indeterminate():
    with pytest.raises(ValueError):
        ProgressSpec(value=.5, indeterminate=True)


def test_skeleton_rows_validate():
    with pytest.raises(ValueError):
        SkeletonSpec(rows=0)


def test_async_state_supports_refreshing():
    spec = AsyncContentSpec(AsyncState.REFRESHING, preserve_content_while_refreshing=True)
    assert spec.state is AsyncState.REFRESHING


def test_state_view_error_class_and_id():
    spec = StateViewSpec(StateKind.ERROR, 'Unable to load', error_id='A1B2C3')
    assert 'cui-state-view--error' in spec.classes
    assert spec.error_id == 'A1B2C3'


def test_toast_duration_validates():
    with pytest.raises(ValueError):
        ToastSpec('Saved', duration_ms=-1)
