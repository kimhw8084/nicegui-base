# NiceGUI Base v1.7 — Phase 3 Overlay Architecture

Phase 3 replaces ad-hoc Quasar/NiceGUI overlay behavior with one Company-owned interaction and stacking contract.

## Design references

- Raycast: crisp transient surfaces, predictable dismissal, keyboard behavior.
- Apple: modal focus, breathing room, restrained depth, conventional Escape/cancel semantics.
- Linear: low-noise popovers and compact application-layer hierarchy.
- Atlassian Design System: explicit global layering governance rather than local z-index escalation.

## Canonical layer order

`base → sticky/local controls → application chrome → local popup → popover → backdrop → modal → tooltip → toast`

The source of truth is `OverlayLayer` in `nicegui_base.overlays.models` and the matching `--cui-*-z` design tokens.

## Interaction laws

1. Dismissible dialogs and drawers are never forcibly persistent.
2. Every visible close/cancel/confirm/X action routes through the Company close path.
3. Typed destructive confirmation must accept text input, enable only on the exact phrase, and close on confirmation.
4. Canonical integrations never use raw NiceGUI `.tooltip(...)`; Company tooltip owns placement and lifecycle.
5. Company tooltip is viewport-clamped and destroyed on mouseleave, focus loss, scroll, resize, pointer-down, or modal open.
6. Toasts expose a close action and lifetime gauge; hover pauses automatic expiry.
7. Table/chart/image toolbars stay on the local layer and cannot cover popovers, drawers or dialogs.
8. Popover actions explicitly close the Company popover when close-on-action behavior is intended.
9. Browser certification verifies behavior, not just element presence.

## Browser release checks

- Confirm dialog Cancel closes.
- Confirm dialog primary action closes.
- Danger dialog accepts the required phrase, enables the destructive action, and closes.
- Detail drawer survives internal clicks and closes from X.
- Inspector closes with Escape.
- Toast exposes lifetime and close controls and actually dismisses.
- Tooltip appears on target and disappears after pointer departure.
- DataTable toolbar never wins hit-testing over an inspector/modal.
- Layer geometry remains inside the viewport.
