from nicegui_base.forms.css import build_form_css
from nicegui_base.filters.css import build_filter_css
from nicegui_base.feedback.css import build_feedback_css
from nicegui_base.overlays.css import build_overlay_css


def build_interaction_css() -> str:
    return '\n'.join((build_form_css(), build_filter_css(), build_feedback_css(), build_overlay_css()))

__all__ = ['build_interaction_css']
