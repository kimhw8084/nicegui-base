from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .tokens import BREAKPOINTS, CONTROL_HEIGHTS, DARK, DENSITIES, LIGHT, MOTION, RADII, SPACING, TYPOGRAPHY, ThemePalette


class ThemeMode(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class DesignSystem:
    light: ThemePalette
    dark: ThemePalette
    spacing: Mapping[str, int]
    radii: Mapping[str, int]
    control_heights: Mapping[str, int]
    breakpoints: Mapping[str, int]
    motion: Mapping[str, object]
    typography: Mapping[str, Mapping[str, object]]
    densities: Mapping[str, Mapping[str, int]]


def build_design_system() -> DesignSystem:
    return DesignSystem(
        light=LIGHT,
        dark=DARK,
        spacing=SPACING,
        radii=RADII,
        control_heights=CONTROL_HEIGHTS,
        breakpoints=BREAKPOINTS,
        motion=MOTION,
        typography=TYPOGRAPHY,
        densities=DENSITIES,
    )
