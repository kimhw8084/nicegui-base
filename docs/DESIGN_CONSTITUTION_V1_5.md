# NiceGUI Base v1.5 — Design Constitution

NiceGUI Base treats NiceGUI, Quasar, AG Grid and ECharts as implementation machinery. They do not define the product's visible language.

## Modern visual doctrine

The target is a restrained, high-density, major-technology internal product: Apple-like geometry and typography discipline, modern financial-product data clarity, minimal decorative chrome, semantic tinted fills, precise alignment and strong information hierarchy.

### Geometry

Only three visible rounded-rectangle families are approved:

- **Control — 10px:** buttons, fields, segmented controls, toolbar actions.
- **Surface — 14px:** cards, panels, wells, tables, charts, alerts, menus.
- **Overlay — 18px:** dialogs, command palettes and major modal surfaces.
- Pills are reserved for true pill semantics such as count/status chips.

Legacy `xs/sm/md/lg/xl` radius names remain only as compatibility aliases onto those families. Applications must not invent new radius values.

### Spacing

Pages, sections and component clusters own spacing; individual application components should not add ad-hoc margins.

- Desktop page gutter: 32px.
- Mobile page gutter: 16px.
- Section rhythm: density-aware 22–32px.
- Stack gap: density-aware 12–18px.
- Action/control cluster gap: density-aware 8–12px.
- Surface padding: density-aware 16–24px.

Use `Page`, `Section`, `Stack`, `ActionRow`, `ButtonCluster`, `ToolbarGroup`, `FormStack`, `AlertStack`, `ContentColumn` and `SurfaceGrid` rather than manual spacing.

### Density

Density is geometry, not a label:

| Mode | Control | Table row | Surface padding |
|---|---:|---:|---:|
| Comfortable | 44px | 44px | 24px |
| Compact | 38px | 38px | 20px |
| Dense | 34px | 34px | 16px |

Changing density must visibly alter controls, tables, gaps, section rhythm and surface padding without changing the visual language.

### Color

Neutral structural surfaces dominate. Accent and semantic colors are used deliberately.

- Status/risk uses tinted background + semantic text/icon, not colored outline decoration.
- Structural borders are neutral and subtle.
- Primary actions use a filled accent.
- Secondary actions use a soft neutral surface.
- Ghost actions are transparent until hover.
- Destructive actions use semantic fill/tint, not a red outline as the main signal.

### Typography

Use the system-native stack with disciplined hierarchy. Long labels and values must wrap or intentionally truncate. Data values use tabular numerics where scanning matters.

### Controls

All controls share a common height, vertical centering, icon box, focus treatment and radius. Icon-only controls are optically centered. Joined controls are the only controls allowed to touch.

### Shell

The shell owns header/sidebar/content geometry. Applications may not calculate these offsets themselves.

The canonical header supports title, subtitle/context, subtle title animation, environment, settings, greeting and user/profile actions. The sidebar must always retain an explicit collapse/expand affordance on desktop and transform into mobile navigation at the semantic breakpoint.

### Motion

Motion is short, subtle and functional. Normal mode uses small opacity/translation transitions. Reduced Motion eliminates unnecessary movement while preserving state feedback.

### Data visualization

ECharts is a renderer, not a design system. Company charts use reduced chrome, subtle grid lines, modern tooltips, controlled legends, zoom/reset/fullscreen/export/data-view actions and strong dark-mode parity.

Wafer and die/residual views use purpose-built Company SVG renderers with actual cell geometry, wafer boundary/notch, legends, hover values and pan/zoom rather than generic scatter plots.

## Automatic enforcement

Live browser certification treats these as release failures:

- page gutter missing;
- content under header/sidebar;
- child escaping its container;
- clipped text without an intentional truncation policy;
- sibling overlap;
- accidental zero-gap action clusters;
- icon mis-centering;
- wrong button/field/surface/overlay radius;
- density control-height mismatch;
- raw stock NiceGUI/Quasar/AG Grid visual leakage.

A framework change is not visually complete merely because its source tests pass; target-browser geometry and visual-baseline certification remain required.
