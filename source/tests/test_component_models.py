import pytest

from nicegui_base import (
    ActionButtonSpec, BadgeSpec, ButtonIntent, ButtonSpec, CheckboxSpec, ComponentSize,
    DateRangePickerSpec, FileUploadSpec, IconButtonSpec, MultiSelectSpec, NumberInputSpec,
    RangeSliderSpec, SearchInputSpec, SelectOption, SliderSpec, StatusIntent, SurfaceSpec,
    SurfaceVariant, TextAreaSpec, TextInputSpec,
)


def test_primary_button_classes_are_semantic():
    spec = ButtonSpec('Run', intent=ButtonIntent.PRIMARY)
    assert spec.classes == 'cui-button cui-button--primary cui-control--medium'


def test_loading_button_has_state_class():
    assert 'is-loading' in ActionButtonSpec('Run', loading=True).classes


def test_full_width_button_has_state_class():
    assert 'is-full-width' in ButtonSpec('Save', full_width=True).classes


def test_icon_button_requires_accessible_label():
    with pytest.raises(ValueError):
        IconButtonSpec('refresh', '')


def test_icon_button_selected_state_is_explicit():
    assert 'is-selected' in IconButtonSpec('star', 'Favorite', selected=True).classes


def test_surface_variants_are_semantic():
    assert 'cui-surface--card' in SurfaceSpec(SurfaceVariant.CARD).classes
    assert 'is-selected' in SurfaceSpec(SurfaceVariant.INTERACTIVE, selected=True).classes


def test_badge_intent_class():
    assert 'cui-badge--warning' in BadgeSpec('Watch', StatusIntent.WARNING).classes


def test_field_rejects_disabled_readonly_conflict():
    with pytest.raises(ValueError):
        TextInputSpec(label='Name', disabled=True, readonly=True)


def test_field_error_controls_state_class():
    spec = TextInputSpec(label='Tool', error='Required')
    assert 'cui-field-control--error' in spec.classes


def test_number_bounds_validate():
    with pytest.raises(ValueError):
        NumberInputSpec(label='Threshold', minimum=10, maximum=5)


def test_textarea_rows_validate():
    with pytest.raises(ValueError):
        TextAreaSpec(label='Notes', rows=1)


def test_search_debounce_validates():
    with pytest.raises(ValueError):
        SearchInputSpec(label='Search', debounce_ms=-1)


def test_slider_bounds_validate():
    with pytest.raises(ValueError):
        SliderSpec(label='Limit', value=101, minimum=0, maximum=100)


def test_range_slider_bounds_validate():
    with pytest.raises(ValueError):
        RangeSliderSpec(label='Range', low=80, high=20)


def test_upload_limits_validate():
    with pytest.raises(ValueError):
        FileUploadSpec(max_file_size_mb=0)
    with pytest.raises(ValueError):
        FileUploadSpec(multiple=False, max_files=2)


def test_select_options_are_typed():
    spec = MultiSelectSpec(label='Tools', options=(SelectOption('a', 'Tool A'), SelectOption('b', 'Tool B')))
    assert spec.options[0].value == 'a'


def test_date_range_is_a_semantic_field():
    spec = DateRangePickerSpec(label='Period', start='2026-08-01', end='2026-08-25')
    assert spec.start == '2026-08-01'

from nicegui_base import ChipSpec, CountBadgeSpec, DataQuality, DataQualityBadgeSpec, FreshnessIndicatorSpec


def test_chip_selected_class():
    assert 'is-selected' in ChipSpec('Tool A', selected=True).classes


def test_count_badge_caps_large_counts():
    assert CountBadgeSpec(1200, maximum=999).display == '999+'


def test_count_badge_rejects_negative_count():
    with pytest.raises(ValueError):
        CountBadgeSpec(-1)


def test_freshness_stale_maps_to_warning():
    assert FreshnessIndicatorSpec('Updated 12m ago', stale=True).intent is StatusIntent.WARNING


def test_data_quality_intents_are_semantic():
    assert DataQualityBadgeSpec(DataQuality.COMPLETE).intent is StatusIntent.SUCCESS
    assert DataQualityBadgeSpec(DataQuality.UNAVAILABLE).intent is StatusIntent.DANGER
