# NiceGUI Base v2 Public API Policy

## Stable compatibility surface

The names exported from the root `nicegui_base` package and recorded in `PUBLIC_API_CONTRACT.json` are the frozen compatibility surface for the 2.0 release line. The contract records symbol kind, owning module and stable callable parameter structure/defaults.

- Removing an exported symbol or making an incompatible signature change requires an explicit major-version decision.
- Additive exports require intentional contract regeneration and review.
- Implementation submodules are not automatically semver-stable merely because Python permits importing them directly.
- Existing broad 1.x root exports are preserved for compatibility in 3.0.0a8; v2 does not silently delete historical names.
- Future cleanup must use deprecation/migration evidence rather than breaking root imports without warning.

Run `python -m nicegui_base.governance.cli --root .` before packaging. Public API drift is a release failure.
