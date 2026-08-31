# Phase 1 Design Laws

1. Application code must use semantic tokens; raw visual values are framework-internal only.
2. Light and dark palettes are independently designed and must both pass contrast checks for normal text roles.
3. System theme mode is a first-class default.
4. Spacing follows a 4px sub-grid and 8px primary rhythm.
5. Typography uses a small fixed role set; hierarchy is achieved with size, spacing, tone, and restrained weight.
6. Motion is purposeful and short. Reduced-motion preferences override nonessential motion.
7. Density is semantic: comfortable, compact, dense.
8. Application components may consume control-height, spacing, radius, type, color, motion, and breakpoint tokens; they must not redefine them.
9. Numeric engineering data should use tabular numerals where appropriate.
10. NiceGUI/Quasar styling is subordinate to this design system through the integration adapter.
