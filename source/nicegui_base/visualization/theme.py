from __future__ import annotations
from dataclasses import dataclass
from nicegui_base.design.tokens import DARK, LIGHT, ThemePalette

@dataclass(frozen=True, slots=True)
class ChartTheme:
    background: str
    text_primary: str
    text_secondary: str
    border: str
    grid: str
    surface_elevated: str
    accent: str
    success: str
    warning: str
    danger: str
    info: str


def chart_theme(mode: str='light') -> ChartTheme:
    p: ThemePalette = DARK if mode == 'dark' else LIGHT
    return ChartTheme(
        background='transparent', text_primary=p.text_primary, text_secondary=p.text_secondary,
        border=p.border_default, grid=p.border_subtle, surface_elevated=p.surface_elevated,
        accent=p.accent, success=p.success, warning=p.warning, danger=p.danger, info=p.info,
    )

__all__=['ChartTheme','chart_theme']
