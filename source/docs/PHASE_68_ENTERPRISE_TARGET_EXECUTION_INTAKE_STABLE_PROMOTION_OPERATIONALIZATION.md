# Wave 68 — Enterprise Target Execution Intake & Stable Promotion Operationalization

Wave 68 adds a bounded bridge between real target-environment execution artifacts and the existing Wave 65–67 evidence/promotion authorities. It does **not** add a second certification authority, deployment engine, or vendor-specific infrastructure layer.

## Added target-execution intake contracts

- `TargetExecutionObservation` records only the four external execution gates already owned by the canonical target certification contract: installed NiceGUI, real server/WebSocket lifecycle, supported corporate browser, and human visual baseline.
- `TargetExecutionIntake` binds those observations to recipe/provider/source identity, the current framework/NiceGUI release authority, the observed target environment, and actual artifact SHA-256 values.
- `JsonTargetExecutionIntakeAdapter` loads a provider-neutral manifest and hashes the referenced artifact bytes at intake time. Artifact traversal outside the configured intake base is rejected.
- `verify_target_execution_intake(...)` is fail-closed for changed artifact bytes and framework/runtime identity mismatch. A requested PASS without current artifact/identity evidence remains PENDING.
- `apply_target_execution_intake(...)` updates only the four external gates in an existing canonical `SemiconductorTargetEvidenceBundle`. Provider conformance, fab-scale pushdown/performance, and governed benchmark gates remain untouched and continue to be owned by Waves 64–66.
- Explicit FAIL observations may conservatively block an external gate; incomplete PASS observations never become PASS.
- `nicegui-base target-intake` normalizes and optionally persists the intake, verifies it, and writes safely merged canonical evidence only when the intake is not BLOCKED.

## Added stable-promotion operationalization contracts

- `verify_stable_promotion_candidate_archive(...)` independently reopens a Wave 67 candidate ZIP, rejects unsafe/duplicate entries, verifies `MANIFEST.sha256`, reconstructs `candidate.json`, and checks the expected candidate identity.
- `StablePromotionOperationalHandoff` deterministically binds a stable-promotion candidate to the exact verified candidate archive bytes plus optional company change-reference metadata. A change reference is never interpreted as approval.
- `FilePromotionOperationalHandoffAdapter` is the provider-neutral default handoff adapter. Company deployment/change implementations may wrap this boundary without entering the framework core.
- `package_promotion_operational_handoff(...)` creates a deterministic ZIP containing the exact verified candidate archive plus pending operation-record templates derived from canonical runbooks. The package performs no deployment.
- `PromotionOperationEvidence` binds actual operation artifact bytes to the canonical runbook step/evidence key they satisfy.
- `PromotionOperationRecord` records promotion/rollback/incident/evidence-capture execution evidence against the same Wave 67 rehearsal/runbook step authority. PASS requires every required step and every canonical evidence item; changed or missing captured evidence BLOCKS verification.
- Operation records explicitly declare that they do not mutate candidate status or target-gate status.
- `nicegui-base promotion-handoff` prepares/verifies the handoff; `nicegui-base promotion-operation` records hash-bound operational evidence. Neither command calls a company deployment API.

## Promotion-safety rules

1. Wave 66 remains the stable-promotion truth authority.
2. Wave 67 remains the stable release-channel candidate/rehearsal/package authority.
3. Wave 68 target intake may only update the four existing external execution gates and may never reinterpret provider/benchmark evidence.
4. Requested external PASS without current target artifact bytes and matching release identity stays PENDING.
5. Artifact tampering, framework mismatch, wrong installed NiceGUI identity, or candidate-package corruption is BLOCKED.
6. A Wave 68 handoff can be READY only when the bound Wave 67 candidate is READY and the exact candidate archive independently verifies.
7. READY_FOR_HANDOFF is not DEPLOYED. Company deployment/change approval and execution remain outside the generic framework unless authoritative company adapters are supplied.
8. Operation evidence is audit evidence only. It never upgrades target certification or stable-candidate truth.

## Provider-neutral intake manifest

A target environment can emit a small JSON manifest referencing execution artifacts:

```json
{
  "schema_version": 1,
  "recipe_key": "spc-monitor",
  "provider": "company-provider",
  "source_key": "fab-source",
  "framework_version": "3.0.0a8",
  "environment": {
    "python_version": "3.12.0",
    "platform": "company-target",
    "nicegui_version": "3.15.0",
    "executable": "python",
    "metadata": {}
  },
  "gates": [
    {
      "key": "server_websocket",
      "status": "pass",
      "evidence": "Current-source target runtime smoke completed.",
      "artifact": "runtime_smoke.json"
    }
  ]
}
```

The manifest does not make the gate PASS by itself. The referenced bytes are hashed, identity checked, and merged through the existing evidence authority.

## Generated application helpers

Semiconductor starters now include additive helpers in `services/release_evidence.py`:

- `assimilate_target_execution(...)`
- `prepare_operational_handoff(...)`
- `record_operational_execution(...)`

Existing Wave 65–67 release-evidence helpers remain intact.

## Certification boundary

This build environment has no installed NiceGUI target runtime, approved company provider, representative fab-scale company dataset, supported corporate publisher/browser path, or human visual approval. Wave 68 therefore certifies source behavior and packaging only; those enterprise target gates remain PENDING until actual target artifacts are supplied and verified.
