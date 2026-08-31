# NiceGUI Base v1.6 — Rendered Product Constitution

NiceGUI Base treats NiceGUI, Quasar, AG Grid and ECharts as implementation machinery. They do not define the visible product language. v1.6 adds a stricter rule: **a component is not complete because it exists; it must render, align, space and behave correctly in the real browser.**

## Product doctrine

The target is a restrained, high-density, major-technology internal engineering product: Apple-like geometry and typography discipline, modern financial-product data clarity, minimal decorative chrome, semantic tinted fills, precise optical alignment, strong information hierarchy and no recognizable stock NiceGUI/Quasar personality.

## Geometry

Only three visible rounded-rectangle families are approved:

- **Control — 10px:** buttons, fields, segmented controls and toolbar actions.
- **Surface — 14px:** cards, panels, wells, tables, charts, alerts and menus.
- **Overlay — 18px:** dialogs, command palettes and major modal surfaces.
- Pills are reserved for true pill semantics such as status/count chips.

Legacy radius aliases may map onto these families for compatibility. Applications must not invent new visual radii.

## Full-width application canvas

Desktop shell geometry is deterministic:

- expanded main canvas starts exactly at the expanded sidebar right edge;
- collapsed main canvas starts exactly at the collapsed sidebar right edge;
- main canvas width is exactly `viewport - sidebar width`;
- mobile main canvas is exactly 100% width;
- outer `.cui-page` always spans 100% of the main canvas;
- left/right page gutters are symmetric;
- reading-width restrictions belong to an inner content column, never the outer page canvas.

Applications must not calculate header/sidebar offsets themselves.

## Spacing

Pages, sections and composition primitives own spacing. Individual application components should not add ad-hoc margins.

- Desktop page gutter: 32px.
- Mobile page gutter: 16px.
- Section rhythm: density-aware 22–32px.
- Stack gap: density-aware 12–18px.
- Action/control cluster gap: density-aware 8–12px.
- Surface padding: density-aware 16–24px.

Use `Page`, `Section`, `Stack`, `ActionRow`, `ButtonCluster`, `ToolbarGroup`, `FormStack`, `AlertStack`, `ContentColumn` and `SurfaceGrid` rather than manual spacing.

Joined controls are the only controls allowed to touch.

## Density

Density is real geometry:

| Mode | Control | Table row | Surface padding |
|---|---:|---:|---:|
| Comfortable | 44px | 44px | 24px |
| Compact | 38px | 38px | 20px |
| Dense | 34px | 34px | 16px |

Changing density must visibly alter controls, tables, gaps, section rhythm and surface padding without remounting heavy data surfaces unnecessarily.

## Color and hierarchy

Neutral structural surfaces dominate. Foundation semantic colors must be used by real components, not only displayed in a token gallery.

- Status/risk uses tinted background + semantic text/icon, not colored-outline decoration.
- Structural borders are neutral, subtle and sparse.
- Primary actions use filled accent treatment.
- Secondary actions use soft neutral surfaces.
- Ghost actions are transparent until hover.
- Destructive actions use semantic fill/tint.
- Environment badges must be visually distinguishable while remaining restrained.

## Typography and optical alignment

Long labels and values must wrap or intentionally truncate. Data values use tabular numerics where scanning matters.

Controls share a common height, vertical centering, icon box, focus treatment and radius. Certification measures icon/control centers, append-slot containment, dialog-title/close alignment and workflow-node centering.

Required markers remain inline with their field label.

## Shell

The shell owns application identity and navigation geometry.

- The primary animated title is the **application title**, not the current view name.
- Current view title/subtitle/breadcrumb live in the subordinate page header.
- One desktop collapse control exists.
- Desktop sidebar physically changes width; labels do not merely disappear inside a wide drawer.
- Every navigation item has a semantic Company icon.
- Desktop sidebar contains a frozen owner/support/VOC/footer region.
- Mobile navigation replaces desktop navigation; it never stacks on top of it.
- User/settings menus must open visibly below the fixed header with viewport collision handling.

## Controls and fields

NiceGUI native choice/data models are preserved where they are correct; NiceGUI Base does not add low-level Quasar props that break selection behavior.

- Select/combobox arrows are Company-owned SVGs contained within the field.
- Checkbox/radio selection does not highlight an unrelated group rectangle.
- Switch label and control share one optically centered row.
- Slider thumbs stay round and use a soft focus halo rather than a rectangular artifact.
- Text areas are genuinely editable.
- Attachment surfaces support browse, drag/drop and clipboard paste where enabled.

## Overlays

Toast, Tooltip, Popover, DropdownMenu, ContextMenu, Dialog, Drawer, FullScreenDialog and CommandPalette share one overlay contract:

- viewport collision handling;
- fixed z-index hierarchy;
- deliberate anchor gap;
- consistent 18px major overlay / 14px menu surface geometry;
- focus and Escape behavior;
- explicit click-away policy;
- analytical drawers remain open during internal interaction;
- toasts never collide with the fixed header.

## DataTable

DataTable is a flagship dense-data surface. It must preserve AG Grid's native fast path while owning all visible styling.

Required demonstrated behavior includes sorting, filtering, search, resizing, reorder/pinning/visibility, density, pagination, selection, bulk/row/context actions, export, editing/validation, server mode, master/detail, presets, double-click inspection and compact/dense high-row-count use.

Simple density changes should update grid dimensions in place rather than remounting the table.

## Data visualization

ECharts is a renderer, not a design system. Company analytical charts use reduced chrome, subtle grids, modern tooltips, controlled legends, direct mouse/trackpad zoom where useful, explicit reset/fullscreen/export/data-view actions and strong dark-mode parity.

Heatmap legends must occupy a dedicated non-axis collision zone. Export is one clear action surface rather than duplicate buttons.

Semiconductor-native visuals should use custom Company renderers where generic charts reduce engineering intuition. v1.6 includes wafer maps, die/residual fields, synchronized affected-vs-control wafer comparison and radial center-to-edge profile visualization.

## Behavior is part of certification

The live browser harness verifies not only presence but operation: sidebar collapse width, full-width canvas recomputation, density dimension changes, editable fields, visible menus, dialog/drawer behavior, row inspection, Command Palette navigation, motion replay and chart zoom state.

## Automatic release blockers

Live browser certification treats these as failures:

- main-canvas width mismatch or asymmetric page gutter;
- content under header/sidebar;
- child escaping its container;
- clipped text without intentional truncation;
- sibling overlap or insufficient composition gap;
- missing surface padding;
- off-screen overlay or toast/header collision;
- icon/control mis-centering;
- field append/arrow escaping its control;
- dialog title/close misalignment;
- wrong button/field/surface/overlay radius;
- density control-height mismatch;
- nonfunctional visible interactions covered by the acceptance suite;
- raw stock NiceGUI/Quasar/AG Grid visual leakage.

A source-test PASS is necessary but not sufficient. Target-browser geometry, behavior and an explicitly human-approved visual baseline remain required for Live Certification.
