# Wave 62 — Semiconductor Application Recipe Factory

Wave 62 converts the Wave 59–61 data/state/analytics platform into eight governed complete-application starters: `SPCMonitor`, `ExcursionDefenseLine`, `FdcToolHealth`, `LotWaferExplorer`, `YieldLoss`, `PMEffectAnalysis`, `ChamberMatching`, and `RcaCockpit`.

## Architecture

Recipes are composition metadata over the existing authorities. They declare semantic field requirements, manufacturing filters, populations, panel geometry, analytical surfaces, records/detail surfaces and cross-panel interactions. Assembly resolves source semantics from explicit overrides, canonical aliases, then Wave 59 `DataSchema` roles. Strict mode fails explicitly when required semantics are absent; non-strict mode omits only panels whose declared requirements cannot be bound and never invents data.

Every assembled app reuses one Wave 60 `AnalysisContext`, one `SelectionBus`, the existing `AnalysisCoordinator`, Wave 61 semiconductor context/filter facade, and `WorkspaceController`. Generated pages use `AnalysisWorkspacePage` + `NiceGUIWorkspace`; recipes cannot select a competing page/layout runtime.

## Engineer workflow

```bash
nicegui-base recipes "compare chambers after PM"
nicegui-base create ./pm_effect --name "PM Effect Analysis" --template analysis-workspace --recipe pm-effect-analysis
```

The generated `services/data_source.py` is a provider-neutral fixture boundary. Production applications replace that boundary with an approved Wave 59 `DataSource` adapter while retaining the recipe/page/state/query architecture.

## Verification

- 887/887 collected tests PASS across 122 test files.
- 62/62 Wave 62 behavioral tests PASS.
- Governance 0 errors / 0 warnings.
- Shipped examples 0 errors / 0 warnings across 26 files.
- Static certification 12 PASS / 1 expected NiceGUI-unavailable warning / 0 FAIL.
- Visual integration coverage 183/183.
- Root API 1,058, with 0 removals from the 1,043-entry Wave 61 baseline.
- 8 recipe registry entries layered over the existing 58 semiconductor analytical surfaces.
- Final wheel RECORD: 442/442 hashes verified; 0 mismatches.

Target NiceGUI/browser/company-environment execution remains PENDING and is not inferred from source/static validation.
