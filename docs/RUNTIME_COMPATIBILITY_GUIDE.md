# NiceGUI Base 3.0.0a8 — NiceGUI Runtime Compatibility Guide

NiceGUI Base 3.0.0a8 retains the hardened runtime-compatibility contract for the pinned `nicegui==3.15.0` runtime.

## Why this exists

Static/synthetic route construction does not prove the real installed NiceGUI API. NiceGUI Base therefore requires three independent gates before setup is considered successful:

1. **Source contract** — blocks known-invalid API patterns such as `LeftDrawer.open/close`, direct assignment to `EChart.options`, and awaiting native NiceGUI fullscreen setters.
2. **Installed runtime contract** — imports the actual installed NiceGUI 3.15.0 package, reflects critical class APIs, and validates the keyword arguments of every direct NiceGUI Base call to `nicegui.ui` factories against the installed signatures.
3. **Real all-route server smoke** — starts the installed NiceGUI application from a neutral working directory, requests `/healthz`, `/readyz`, and all 22 lab routes, then scans the server log for Python/ASGI runtime failures.

## Commands

```bash
nicegui-base runtime-contract
nicegui-base runtime-smoke
```

`runtime-smoke` does not require Chrome/Chromium. Browser automation is only required for the later visual/interaction certification matrix.

## Linux setup contract

`./setup_linux.sh` performs, in order:

```text
bundle hash verification
→ isolated venv install
→ nicegui-base runtime-contract
→ nicegui-base doctor --no-require-browser
→ nicegui-base runtime-smoke
→ SETUP COMPLETE
```

If any step fails, setup exits non-zero and must not be treated as a successful installation.

## NiceGUI 3.15 contracts explicitly protected

- `LeftDrawer`: `show()`, `hide()`, `toggle()`
- `Dialog`: `open()`, `close()`, `toggle()`
- `Menu`: `open()`, `close()`, `toggle()`
- `ContextMenu`: `open()`, `close()`
- `EChart.options`: read-only property returning a mutable dictionary; update by mutating that dictionary followed by `update()`
- `Fullscreen.enter/exit/toggle`: synchronous state-changing methods
- `Element.classes/style/props`: property helpers, not ordinary class methods

The installed runtime contract also checks all directly used NiceGUI factories such as select, input, upload, AG Grid, EChart, drawer, dialog, menu, progress, tabs, timer and layout elements.
