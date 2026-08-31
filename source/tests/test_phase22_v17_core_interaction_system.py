from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_phase2_company_owned_choice_anatomy_replaces_quasar_choice_rendering():
    s=(ROOT/'nicegui_base/integrations/nicegui_components.py').read_text()
    region=s[s.index('class _NativeChoice'):s.index('class _NativeTemporalField')]
    assert "ui.element('input').classes('cui-choice-native')" in region
    assert 'ui.checkbox(' not in region
    assert 'ui.radio(' not in region
    assert 'ui.switch(' not in region
    assert 'cui-choice-row--checkbox' in region
    assert 'cui-choice-row--radio' in region
    assert 'cui-choice-row--switch' in region


def test_phase2_single_slider_uses_native_range_and_range_slider_removes_focus_ring():
    s=(ROOT/'nicegui_base/integrations/nicegui_components.py').read_text()
    css=(ROOT/'nicegui_base/design/hardening_css.py').read_text()
    assert "ui.element('input').classes('cui-native-slider')" in s
    assert "oninput=\\\"this.style.setProperty('--pct'" in s
    assert '.cui-slider--v17.q-slider .q-slider__focus-ring{display:none!important}' in css
    assert 'border:0!important;border-radius:var(--cui-radius-circle)!important;background:#fff!important' in css


def test_phase2_action_loading_uses_contained_spinner_element():
    s=(ROOT/'nicegui_base/integrations/nicegui_components.py').read_text()
    css=(ROOT/'nicegui_base/design/hardening_css.py').read_text()
    action=s[s.index('class ActionButton'):s.index('class IconButton')]
    assert "ui.element('span').classes('cui-button__spinner')" in action
    assert '.cui-button.is-loading::before{display:none!important}' in css
    assert '.cui-button.is-loading:disabled{opacity:1!important' in css


def test_phase2_intent_hierarchy_is_materially_distinct():
    css=(ROOT/'nicegui_base/design/hardening_css.py').read_text()
    assert '.cui-button--primary{background:linear-gradient' in css
    assert '.cui-button--secondary{background:var(--cui-surface)!important' in css
    assert '.cui-button--tertiary{background:color-mix' in css
    assert '.cui-button--ghost{background:transparent!important' in css
    assert '.cui-button--danger{background:linear-gradient' in css


def test_phase2_metadata_optical_center_contract():
    css=(ROOT/'nicegui_base/design/hardening_css.py').read_text()
    assert '.cui-badge,.cui-count-badge,.cui-chip' in css
    assert '.cui-count-badge{height:22px!important;min-width:22px!important' in css
    assert '.cui-badge>.q-label,.cui-badge .q-label,.cui-chip .q-label,.cui-count-badge.q-label' in css


def test_phase2_interactive_card_is_keyboard_focusable_and_toggles_selected():
    s=(ROOT/'nicegui_base/integrations/nicegui_components.py').read_text()
    card=s[s.index('class InteractiveCard'):s.index('class StatusBadge')]
    assert 'tabindex="0"' in card
    assert "self.element.on('click', activate)" in card
    assert "self.element.on('keydown.enter', activate)" in card
    assert "classes(add='is-selected')" in card
    assert "classes(remove='is-selected')" in card


def test_phase2_motion_replay_uses_web_animations_and_reduced_motion():
    lab=(ROOT/'nicegui_base/certification/mac_lab.py').read_text()
    assert "matchMedia('(prefers-reduced-motion: reduce)')" in lab
    assert 'e.animate(frames' in lab
    assert 'dataset.motionReplay' in lab


def test_phase2_environment_badges_are_readable_and_semantically_distinct():
    css=(ROOT/'nicegui_base/design/hardening_css.py').read_text()
    assert '.cui-environment-badge{color:var(--cui-text-primary)!important' in css
    assert '.cui-environment-badge--development{background:color-mix' in css
    assert '.cui-environment-badge--staging{background:color-mix' in css
    assert '.cui-environment-badge--production{background:color-mix' in css


def test_phase2_progress_track_is_thick_and_value_sits_outside_track():
    css=(ROOT/'nicegui_base/design/hardening_css.py').read_text()
    assert '.cui-progress.q-linear-progress,.cui-progress{height:12px!important;min-height:12px!important' in css
    assert '.cui-progress-metric__value{min-width:42px!important;text-align:right!important' in css
