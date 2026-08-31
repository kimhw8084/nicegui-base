import pytest

from nicegui_base import (
    FieldValidation, FormActionsSpec, FormSpec, FormState, ValidationIssue, ValidationSeverity,
    ValidationSummarySpec, min_length, numeric_range, pattern, required,
)


def test_form_validation_mode_is_constrained():
    with pytest.raises(ValueError):
        FormSpec('edit-tool', validate_on='whenever')


def test_form_state_dirty_and_valid():
    state = FormState(values={'tool': 'A'}, initial_values={'tool': 'B'})
    assert state.dirty is True
    assert state.valid is True


def test_form_state_error_invalidates():
    state = FormState(issues=(ValidationIssue('tool', 'Required'),))
    assert state.valid is False


def test_warning_does_not_invalidate():
    state = FormState(issues=(ValidationIssue('threshold', 'Near upper limit', ValidationSeverity.WARNING),))
    assert state.valid is True


def test_field_validation_runs_multiple_rules():
    validation = FieldValidation('name', (required(), min_length(4)))
    assert len(validation.validate('')) == 2
    assert validation.validate('ETCH') == ()


def test_numeric_range_validation():
    validator = numeric_range(0, 100)
    assert validator(101)
    assert validator(50) is None


def test_pattern_validation():
    validator = pattern(r'[A-Z]{2}-\d{3}', 'Use AA-000 format')
    assert validator('ETCH-1') == 'Use AA-000 format'
    assert validator('AB-123') is None


def test_validation_summary_counts_errors_only():
    spec = ValidationSummarySpec((
        ValidationIssue('tool', 'Required'),
        ValidationIssue('limit', 'Near threshold', ValidationSeverity.WARNING),
    ))
    assert spec.error_count == 1


def test_form_actions_alignment_is_constrained():
    with pytest.raises(ValueError):
        FormActionsSpec(align='random')
