from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nicegui_base.visual import IconSize, build_visual_asset_css, render_icon_svg, render_illustration_svg


@dataclass
class SvgIcon:
    """Rendered semantic SVG icon.

    Integration components render on construction like every other NiceGUI Base
    NiceGUI adapter. ``render`` remains idempotent for compatibility.
    """
    key: str
    size: IconSize | str = IconSize.MD
    label: str | None = None
    element: Any = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        self.render()

    def render(self):
        if self.element is not None:
            return self.element
        from nicegui import ui
        self.element = ui.html(render_icon_svg(self.key, size=self.size, label=self.label), sanitize=False).classes('cui-svg-icon-host')
        return self.element


@dataclass
class StateIllustration:
    key: str
    label: str | None = None
    element: Any = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        self.render()

    def render(self):
        if self.element is not None:
            return self.element
        from nicegui import ui
        self.element = ui.html(render_illustration_svg(self.key, label=self.label), sanitize=False).classes('cui-state-illustration-host')
        return self.element


def install_visual_assets_css():
    from nicegui import ui
    ui.add_css(build_visual_asset_css(), shared=True)


__all__ = ['SvgIcon', 'StateIllustration', 'install_visual_assets_css']
