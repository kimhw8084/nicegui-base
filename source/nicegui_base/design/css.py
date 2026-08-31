from __future__ import annotations

from .system import DesignSystem, build_design_system
from .tokens import BREAKPOINTS, EASINGS, FONT_SIZES, FONT_WEIGHTS, LAYOUT_METRICS, LINE_HEIGHTS, LINE_HEIGHT_RATIOS, MOTION_DURATIONS_MS, RELATIVE_FONT_SIZES, RESPONSIVE_LAYOUT_METRICS, ThemePalette


def _palette_vars(prefix: str, p: ThemePalette) -> str:
    values = {
        "page": p.page,
        "surface": p.surface,
        "surface-secondary": p.surface_secondary,
        "surface-elevated": p.surface_elevated,
        "surface-hover": p.surface_hover,
        "surface-selected": p.surface_selected,
        "text-primary": p.text_primary,
        "text-secondary": p.text_secondary,
        "text-tertiary": p.text_tertiary,
        "text-inverse": p.text_inverse,
        "border-subtle": p.border_subtle,
        "border-default": p.border_default,
        "border-strong": p.border_strong,
        "accent": p.accent,
        "accent-hover": p.accent_hover,
        "accent-soft": p.accent_soft,
        "focus-ring": p.focus_ring,
        "success": p.success,
        "success-soft": p.success_soft,
        "warning": p.warning,
        "warning-soft": p.warning_soft,
        "danger": p.danger,
        "danger-soft": p.danger_soft,
        "info": p.info,
        "info-soft": p.info_soft,
        "shadow-1": p.shadow_1,
        "shadow-2": p.shadow_2,
        "overlay-scrim": p.overlay_scrim,
    }
    return "\n".join(f"  --cui-{k}: {v};" for k, v in values.items())


def build_css(system: DesignSystem | None = None) -> str:
    s = system or build_design_system()
    spacing = "\n".join(f"  --cui-space-{k}: {v}px;" for k, v in s.spacing.items())
    radii = "\n".join(f"  --cui-radius-{k}: {v}px;" for k, v in s.radii.items())
    motion = "\n".join(
        f"  --cui-motion-{k.replace('_ms','')}: {v}ms;" if k.endswith("_ms") else f"  --cui-{k.replace('_','-')}: {v};"
        for k, v in s.motion.items()
    )
    governed_type_scale = "\n".join([
        *(f"  --cui-font-size-{k}: {v}px;" for k, v in FONT_SIZES.items()),
        *(f"  --cui-font-size-{k}: {v};" for k, v in RELATIVE_FONT_SIZES.items()),
        *(f"  --cui-line-height-{k}: {v}px;" for k, v in LINE_HEIGHTS.items()),
        *(f"  --cui-line-height-ratio-{k}: {v};" for k, v in LINE_HEIGHT_RATIOS.items()),
        *(f"  --cui-font-weight-{k}: {v};" for k, v in FONT_WEIGHTS.items()),
        *(f"  --cui-duration-{k.replace('_','-')}: {v}ms;" for k, v in MOTION_DURATIONS_MS.items()),
        *(f"  --cui-easing-{k.replace('_','-')}: {v};" for k, v in EASINGS.items()),
    ])
    type_vars = []
    for name, spec in s.typography.items():
        type_vars.extend([
            f"  --cui-type-{name}-size: {spec['size']}px;",
            f"  --cui-type-{name}-line: {spec['line']}px;",
            f"  --cui-type-{name}-weight: {spec['weight']};",
            f"  --cui-type-{name}-tracking: {spec['tracking']}em;",
        ])
    layout_metrics = "\n".join(f"  --cui-{key.replace('_','-')}: {value}px;" for key, value in LAYOUT_METRICS.items())
    responsive_layout = []
    for breakpoint_name, values in RESPONSIVE_LAYOUT_METRICS.items():
        max_width = BREAKPOINTS[breakpoint_name] - 1
        responsive_layout.extend([
            f"@media(max-width:{max_width}px) {{",
            "  :root {",
            *(f"    --cui-{key.replace('_','-')}: {value}px;" for key, value in values.items()),
            "  }",
            "}",
        ])

    density = []
    for name, spec in s.densities.items():
        density.extend([
            f"[data-density='{name}'] {{",
            *(f"  --cui-{key.replace('_','-')}: {value}px;" for key, value in spec.items() if key != 'gap_scale'),
            f"  --cui-density-gap-scale: {spec['gap_scale'] / 100};",
            "}",
        ])

    return f"""
:root {{
{spacing}
{radii}
  --cui-radius-circle: 50%;
{layout_metrics}
{motion}
{governed_type_scale}
{chr(10).join(type_vars)}
  --nicegui-default-padding: var(--cui-space-4);
  --nicegui-default-gap: var(--cui-space-3);
{_palette_vars('light', s.light)}
}}

html[data-theme='light'] {{
{_palette_vars('light', s.light)}
  color-scheme: light;
}}

html[data-theme='dark'] {{
{_palette_vars('dark', s.dark)}
  color-scheme: dark;
}}

@media (prefers-color-scheme: dark) {{
  html[data-theme='system'] {{
{_palette_vars('dark', s.dark)}
    color-scheme: dark;
  }}
}}

@media (prefers-color-scheme: light) {{
  html[data-theme='system'] {{
{_palette_vars('light', s.light)}
    color-scheme: light;
  }}
}}

{chr(10).join(density)}

{chr(10).join(responsive_layout)}

html, body {{
  background: var(--cui-page);
  color: var(--cui-text-primary);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}}

.cui-tabular {{ font-variant-numeric: tabular-nums; }}
.cui-focusable:focus-visible {{ outline: 3px solid color-mix(in srgb, var(--cui-focus-ring) 58%, transparent); outline-offset: 2px; }}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: var(--cui-duration-reduced) !important;
    animation-iteration-count: 1 !important;
    transition-duration: var(--cui-duration-reduced) !important;
    scroll-behavior: auto !important;
  }}
}}
""".strip() + "\n"
