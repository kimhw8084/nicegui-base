# Visual Resource Licenses and Provenance

## Runtime assets shipped in Phase 7
All SVG files under `nicegui_base/visual/icons`, `illustrations`, and `dataviz` were generated/authored specifically for this NiceGUI Base framework phase and are recorded as `nicegui-base-project-authored` in the manifests. They have no remote runtime dependency.

## Lucide reference
Lucide was reviewed as a visual-language and licensing reference. Its public package is ISC-licensed, but **no Lucide SVG runtime files are vendored in this Phase 7 package**, because the build sandbox could not retrieve and verify the external archive. If the company later chooses to vendor Lucide, it must be pinned, checksummed, license-copied, and passed through the same SVG validation pipeline before certification.
