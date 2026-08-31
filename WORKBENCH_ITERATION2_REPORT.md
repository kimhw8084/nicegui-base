# NiceGUI Base Workbench — Iteration 2 Repository Update Report

## Identity

- Product: NiceGUI Base
- Distribution: `nicegui-base`
- Python package: `nicegui_base`
- Version: `3.0.0a8`
- Production NiceGUI dependency: `nicegui==3.15.0`
- Reviewed GitHub baseline: `62a06ce9fb976cfd93b746af807512ceda92c07e`
- Delivery type: cumulative Iteration 1 + Iteration 2 repository update

## Iteration 2 implementation

Iteration 2 turns the Workbench from a discoverability front door into a practical development accelerator while preserving the existing NiceGUI Base authorities.

Implemented Workbench modules and behavior include:

- Universal Capability Studio with Preview / Data / Configure / States / Interactions / Code grammar.
- Data Dock model and UI for Excel-style TSV paste, CSV and JSON ingestion, inferred schema/roles, quality feedback, rectangular paste, editing, undo/redo, and conversion to the existing `DataSchema` / `InMemoryDataSource` authority.
- State Matrix using the existing NiceGUI Base async/state authorities.
- Recipe data mapping using canonical `resolve_recipe_source(...)`, including required/optional field compatibility and panel availability/degradation.
- Guided Builder v1 with deterministic, explainable recommendations from canonical Workbench metadata and schema compatibility.
- Registry-aware Copy Minimal / Copy Production code generation.
- Governed starter ZIP generation using existing NiceGUI Base project-generation contracts.
- Pattern-specific starter composition for all ten canonical generic application patterns.
- Live data-driven analytical preview refresh, including Hotelling T² and semiconductor analytical surfaces.
- Workbench routing upgrades so components, patterns, analytics, recipes, and framework references use the Capability Studio experience while retaining compatibility routes.

## Iteration 1 retained cumulatively

This update also contains the approved Iteration 1 Workbench implementation, including:

- Workbench shell and Home / Build / Catalog / Recipes / Data / Quality navigation.
- 58/58 canonical semiconductor analytical surfaces.
- 8/8 canonical semiconductor recipes.
- 10/10 generic application patterns.
- Canonical framework catalog discoverability and search.
- Global command/search experience.
- macOS/Linux setup checksum and Workbench identity readiness fixes.

## Source-level validation

Executed in the overlay source context:

```text
79 passed, 9 skipped
```

The nine skipped checks require a complete repository and/or installed NiceGUI/browser runtime and remain environment-gated. They are not reported as PASS.

## Delivery behavior

The repository update includes `apply_iteration2.py`. Run it against an exact `nicegui-base 3.0.0a8` checkout at the reviewed baseline. The helper:

1. verifies package identity and exact `nicegui==3.15.0` dependency;
2. verifies reviewed baseline Git blob anchors and both canonical checksum manifests;
3. verifies the update bundle's own manifest;
4. copies the cumulative Iteration 1 + 2 Workbench source/tests/scripts;
5. rebuilds all three bundled wheel mirrors offline from repository source;
6. verifies wheel CRC, required members and exact dependency metadata;
7. regenerates `source/SHA256SUMS.txt` and `PACKAGE_SHA256SUMS.txt`;
8. writes `WORKBENCH_ITERATION2_APPLY_RESULT.json`.

The helper intentionally refuses to overwrite a checkout that does not match the reviewed baseline. This prevents silently applying the cumulative package to a newer or locally modified source tree.

## Evidence boundary

PASS in this sandbox:

- Iteration 1 + Iteration 2 focused source tests: 79 passed.
- Python source compilation used throughout development.
- macOS/Linux setup and launcher shell syntax checks from the cumulative implementation.
- deterministic code/starter-generation tests.
- Data Dock parse/edit/undo-redo tests.
- recipe required/optional compatibility tests.
- Workbench catalog/search/readiness source-level tests.

PENDING outside this sandbox:

- full 1,300-file repository regression estate after applying this update;
- actual installed `nicegui==3.15.0` runtime execution;
- real server/WebSocket/browser rendering;
- human visual review;
- company/provider/target-environment evidence.

No stable `3.0.0` claim is made.
