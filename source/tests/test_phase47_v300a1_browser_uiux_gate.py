from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _hardening() -> str:
    return (ROOT / 'nicegui_base/design/hardening_css.py').read_text(encoding='utf-8')


def test_mobile_interactive_targets_have_final_44px_override():
    css = _hardening()
    marker = '/* v3 browser UI/UX hardening: mobile targets stay finger-safe'
    assert marker in css
    tail = css[css.index(marker):]
    assert '@media(max-width:599px)' in tail
    assert '.cui-environment-badge{display:none!important;}' in tail
    assert '.cui-button.q-btn,.cui-icon-button.q-btn{height:44px!important;min-height:44px!important;}' in tail
    assert '.cui-field-control.q-field{min-height:44px!important;}' in tail
    assert '.cui-choice.q-checkbox,.cui-choice.q-radio,.cui-choice-row{min-height:44px!important;}' in tail


def test_final_reduced_motion_override_follows_all_interaction_rules():
    css = _hardening()
    marker = '/* v3 browser UI/UX hardening: mobile targets stay finger-safe'
    tail = css[css.index(marker):]
    assert '@media(prefers-reduced-motion:reduce)' in tail
    assert '--cui-motion-fast:var(--cui-duration-reduced)' in tail
    assert '--cui-duration-drawer:var(--cui-duration-reduced)' in tail
    assert 'transition-duration:var(--cui-duration-reduced)!important' in tail
    assert '.cui-drawer,.cui-dialog,.cui-overlay-backdrop,.cui-tooltip--company' in tail
