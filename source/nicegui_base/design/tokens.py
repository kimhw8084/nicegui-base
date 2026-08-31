from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


def _locked(values: dict[str, object]) -> Mapping[str, object]:
    return MappingProxyType(values)


SPACING: Mapping[str, int] = _locked({
    "0": 0,
    "1": 4,
    "2": 8,
    "3": 12,
    "4": 16,
    "5": 20,
    "6": 24,
    "8": 32,
    "10": 40,
    "12": 48,
    "16": 64,
})

RADII: Mapping[str, int] = _locked({
    # v1.6 geometry constitution: only three visible rectangle families.
    # xs/sm are aliases for control geometry; md/lg for surfaces; xl for overlays.
    "micro": 5,
    "inner": 8,
    "control": 10,
    "surface": 14,
    "overlay": 18,
    "xs": 10,
    "sm": 10,
    "md": 14,
    "lg": 18,
    "xl": 18,
    "pill": 999,
})

CONTROL_HEIGHTS: Mapping[str, int] = _locked({
    "compact": 34,
    "default": 38,
    "large": 44,
    "touch_target": 44,
})

BREAKPOINTS: Mapping[str, int] = _locked({
    "phone": 600,
    "tablet": 900,
    "laptop": 1200,
    "desktop": 1440,
    "wide": 1800,
})

MOTION: Mapping[str, object] = _locked({
    "instant_ms": 80,
    "fast_ms": 120,
    "standard_ms": 160,
    "overlay_ms": 200,
    "emphasis_ms": 220,
    "ease_standard": "cubic-bezier(.2,.8,.2,1)",
    "ease_enter": "cubic-bezier(.16,1,.3,1)",
    "ease_exit": "cubic-bezier(.4,0,1,1)",
})

# v2 governed CSS scales. These preserve the approved rendered values while
# ensuring typography and motion cannot drift through local screenshot hotfixes.
# Semantic TYPOGRAPHY/MOTION roles remain the preferred authoring API; these
# scales cover deliberate micro-geometry used by dense enterprise surfaces.
RELATIVE_FONT_SIZES: Mapping[str, str] = _locked({"inline_code": ".92em"})

FONT_SIZES: Mapping[str, float] = _locked({
    "9": 9, "9_5": 9.5, "10": 10, "10_5": 10.5, "11": 11, "11_5": 11.5,
    "12": 12, "12_5": 12.5, "13": 13, "13_5": 13.5, "14": 14, "15": 15,
    "16": 16, "17": 17, "18": 18, "20": 20, "22": 22, "24": 24,
    "26": 26, "28": 28, "32": 32,
})

LINE_HEIGHTS: Mapping[str, float] = _locked({
    "12": 12, "13": 13, "14": 14, "15": 15, "16": 16, "17": 17, "18": 18,
    "19": 19, "20": 20, "21": 21, "24": 24, "28": 28, "29": 29, "30": 30,
    "32": 32, "34": 34,
})

LINE_HEIGHT_RATIOS: Mapping[str, float] = _locked({
    "1": 1, "1_05": 1.05, "1_12": 1.12, "1_15": 1.15, "1_2": 1.2,
    "1_25": 1.25, "1_3": 1.3, "1_35": 1.35, "1_4": 1.4, "1_45": 1.45, "1_5": 1.5, "1_55": 1.55, "1_65": 1.65,
})

FONT_WEIGHTS: Mapping[str, int] = _locked({
    "400": 400, "450": 450, "500": 500, "520": 520, "550": 550, "560": 560,
    "600": 600, "620": 620, "650": 650, "680": 680, "700": 700, "720": 720,
    "730": 730, "750": 750, "760": 760, "780": 780,
})

MOTION_DURATIONS_MS: Mapping[str, int] = _locked({
    "reduced": 1, "instant": 80, "micro": 100, "fast": 120, "feedback": 140,
    "standard": 160, "shell": 180, "overlay": 200, "overlay_precise": 210, "drawer": 220, "reduced_emphasis": 260, "chart": 280,
    "section": 300, "title": 320, "title_long": 360, "selection": 420,
    "section_lux": 500, "title_lux": 520, "title_lux_long": 540, "selection_lux": 620,
    "spinner_compact": 680, "spinner": 700, "spinner_soft": 720,
    "progress": 1050, "progress_long": 1150, "shimmer": 1250, "table_shimmer": 1300,
})

EASINGS: Mapping[str, str] = _locked({
    "linear": "linear",
    "native": "ease",
    "out": "ease-out",
    "in_out": "ease-in-out",
    "standard": "cubic-bezier(.2,.8,.2,1)",
    "enter": "cubic-bezier(.16,1,.3,1)",
    "exit": "cubic-bezier(.4,0,1,1)",
    "progress": "cubic-bezier(.4,0,.2,1)",
})


TYPOGRAPHY: Mapping[str, Mapping[str, object]] = MappingProxyType({
    "display": _locked({"size": 28, "line": 34, "weight": 650, "tracking": -0.035}),
    "page_title": _locked({"size": 26, "line": 32, "weight": 700, "tracking": -0.03}),
    "app_identity": _locked({"size": 17, "line": 21, "weight": 780, "tracking": -0.025}),
    "app_subtitle": _locked({"size": 11.5, "line": 15, "weight": 500, "tracking": 0}),
    "profile_hint": _locked({"size": 10, "line": 13, "weight": 520, "tracking": 0}),
    "profile_name": _locked({"size": 12, "line": 15, "weight": 720, "tracking": 0}),
    "heading": _locked({"size": 18, "line": 24, "weight": 620, "tracking": -0.018}),
    "subheading": _locked({"size": 15, "line": 20, "weight": 600, "tracking": -0.012}),
    "body": _locked({"size": 13, "line": 19, "weight": 400, "tracking": -0.006}),
    "body_strong": _locked({"size": 13, "line": 19, "weight": 550, "tracking": -0.006}),
    "label": _locked({"size": 12, "line": 16, "weight": 550, "tracking": 0}),
    "caption": _locked({"size": 11, "line": 15, "weight": 450, "tracking": 0}),
    "data": _locked({"size": 12, "line": 18, "weight": 450, "tracking": 0}),
    "code": _locked({"size": 12, "line": 18, "weight": 450, "tracking": 0}),
})

DENSITIES: Mapping[str, Mapping[str, int]] = MappingProxyType({
    "comfortable": _locked({
        "control_height": 44, "control_small": 34, "control_medium": 40, "control_large": 40,
        "icon_button_size": 44, "control_padding_x": 16,
        "table_row_height": 44, "table_header_height": 46,
        "stack_gap": 18, "cluster_gap": 12, "content_gap": 28, "section_gap": 32, "surface_padding": 24,
        "gap_scale": 112,
    }),
    "compact": _locked({
        "control_height": 38, "control_small": 30, "control_medium": 34, "control_large": 40,
        "icon_button_size": 38, "control_padding_x": 14,
        "table_row_height": 38, "table_header_height": 40,
        "stack_gap": 16, "cluster_gap": 10, "content_gap": 24, "section_gap": 28, "surface_padding": 20,
        "gap_scale": 100,
    }),
    "dense": _locked({
        "control_height": 34, "control_small": 28, "control_medium": 30, "control_large": 40,
        "icon_button_size": 34, "control_padding_x": 12,
        "table_row_height": 34, "table_header_height": 36,
        "stack_gap": 12, "cluster_gap": 8, "content_gap": 18, "section_gap": 22, "surface_padding": 16,
        "gap_scale": 88,
    }),
})

LAYOUT_METRICS: Mapping[str, int] = _locked({
    # Preserve the final effective v1.7.3 shell geometry (hardening layer).
    "page_gutter": 20,
    "page_gutter_mobile": 16,
    "content_gap": 24,
    "section_gap": 28,
    "stack_gap": 16,
    "cluster_gap": 10,
    "surface_padding": 20,
    "control_height": 38,
    "control_small": 30,
    "control_medium": 34,
    "control_large": 40,
    "control_padding_x": 14,
    "icon_button_size": 38,
    "control_content_gap": 8,
    "table_row_height": 38,
    "table_header_height": 40,
    "shell_header_height": 60,
    "shell_sidebar_width": 256,
    "shell_sidebar_compact_width": 64,
    "nav_item_height": 42,
    "nav_icon_box": 36,
    "overlay_edge_gap": 20,
    "chart_standard_height": 360,
    "chart_large_height": 460,
    "chart_workspace_height": 560,
})

# Responsive overrides preserve the *effective* pre-v2 cascade rather than
# historical declarations that were subsequently overridden by hardening CSS.
# Keys are max-width breakpoints from BREAKPOINTS; only values that actually
# change at that viewport are repeated here.
RESPONSIVE_LAYOUT_METRICS: Mapping[str, Mapping[str, int]] = MappingProxyType({
    "tablet": _locked({"page_gutter": 16}),
    "phone": _locked({"surface_padding": 16, "overlay_edge_gap": 10}),
})


@dataclass(frozen=True, slots=True)
class ThemePalette:
    page: str
    surface: str
    surface_secondary: str
    surface_elevated: str
    surface_hover: str
    surface_selected: str
    text_primary: str
    text_secondary: str
    text_tertiary: str
    text_inverse: str
    border_subtle: str
    border_default: str
    border_strong: str
    accent: str
    accent_hover: str
    accent_soft: str
    focus_ring: str
    success: str
    success_soft: str
    warning: str
    warning_soft: str
    danger: str
    danger_soft: str
    info: str
    info_soft: str
    shadow_1: str
    shadow_2: str
    overlay_scrim: str


LIGHT = ThemePalette(
    page="#F5F5F7",
    surface="#FFFFFF",
    surface_secondary="#F7F7F9",
    surface_elevated="#FFFFFF",
    surface_hover="#F0F1F3",
    surface_selected="#E8F1FF",
    text_primary="#1D1D1F",
    text_secondary="#525256",
    text_tertiary="#74747A",
    text_inverse="#FFFFFF",
    border_subtle="#ECECEF",
    border_default="#E0E0E4",
    border_strong="#C8C8CE",
    accent="#0071E3",
    accent_hover="#0064C8",
    accent_soft="#E8F2FF",
    focus_ring="#66A8FF",
    success="#137A42",
    success_soft="#E9F7EF",
    warning="#936000",
    warning_soft="#FFF4D8",
    danger="#B42318",
    danger_soft="#FDECEA",
    info="#1D5FBF",
    info_soft="#EAF2FF",
    shadow_1="0 1px 2px rgba(0,0,0,.04),0 6px 18px rgba(0,0,0,.035)",
    shadow_2="0 18px 50px rgba(0,0,0,.14)",
    overlay_scrim="rgba(20,20,24,.30)",
)

DARK = ThemePalette(
    page="#0F0F11",
    surface="#18181B",
    surface_secondary="#202024",
    surface_elevated="#26262A",
    surface_hover="#29292E",
    surface_selected="#142945",
    text_primary="#F5F5F7",
    text_secondary="#C7C7CC",
    text_tertiary="#929298",
    text_inverse="#0F0F11",
    border_subtle="#28282D",
    border_default="#34343A",
    border_strong="#4B4B52",
    accent="#5EA6FF",
    accent_hover="#79B6FF",
    accent_soft="#142945",
    focus_ring="#5EA6FF",
    success="#5BDB89",
    success_soft="#132A1C",
    warning="#F1BD5A",
    warning_soft="#312715",
    danger="#FF817A",
    danger_soft="#351918",
    info="#83B3FF",
    info_soft="#152840",
    shadow_1="0 1px 2px rgba(0,0,0,.24),0 8px 24px rgba(0,0,0,.19)",
    shadow_2="0 20px 56px rgba(0,0,0,.44)",
    overlay_scrim="rgba(0,0,0,.52)",
)
