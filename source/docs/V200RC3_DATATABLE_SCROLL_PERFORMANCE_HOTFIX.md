# NiceGUI Base 2.0.0rc3 — DataTable Scroll Performance Hotfix

RC3 preserves the v2 visual/runtime contracts and removes a real scroll-latency regression in the Company DataTable.

## Root cause

- `debounceVerticalScrollbar=true` told AG Grid to delay viewport work until scrolling settled.
- `rowBuffer=3` left too few pre-rendered virtual rows for fast trackpad/wheel movement.
- row hover used an animated background transition, adding paint work while rows moved under the pointer.

## Fix

- Vertical-scroll debouncing is explicitly disabled.
- The virtual row buffer is restored to 10 rows.
- Row hover remains, but the background transition is removed.
- Browser certification now scrolls the real AG Grid viewport and requires a materially later row set to render within 350 ms.

No design constitution or public API contract is changed.
