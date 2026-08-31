# Wave 69 — Enterprise Promotion Execution Adapter Qualification & Release Audit Closure

Wave 69 adds a bounded qualification and final-audit layer around the existing Wave 66–68 promotion authorities. It does **not** add a deployment engine, a second promotion decision, or a vendor-specific company release integration.

## Promotion execution-adapter qualification

- `PromotionExecutionAdapterQualification` records one external promotion execution adapter identity, version, declared operation capabilities, exact current NiceGUI Base/NiceGUI release identity, qualification authority/reference metadata, and hash-bound qualification artifacts.
- `JsonPromotionExecutionAdapterQualificationAdapter` loads a provider-neutral JSON manifest and captures referenced artifact SHA-256 values without allowing path traversal outside the configured qualification base.
- `verify_promotion_execution_adapter_qualification(...)` is fail-closed:
  - external FAIL/BLOCKED or wrong framework/NiceGUI identity is BLOCKED;
  - requested QUALIFIED without traceable artifact bytes or missing observed release identity stays PENDING;
  - changed captured bytes are BLOCKED;
  - missing required promotion/rollback/incident/evidence-capture capabilities stay PENDING;
  - only current artifact-backed external qualification can become QUALIFIED.
- Approval/change/ticket references remain metadata. Their presence never converts PENDING to QUALIFIED.
- The built-in adapter registry contains only the provider-neutral `json-manifest` intake. Company-specific release systems remain outside the core until an authoritative adapter contract is supplied.

## Stable release audit closure

- `ReleaseAuditPolicy` defines the release-channel audit contract. The default stable policy requires:
  - a READY Wave 68 operational handoff;
  - an artifact-backed QUALIFIED external promotion execution adapter;
  - one complete PASS promotion-operation record for every recipe in the bound stable candidate.
- `build_release_audit_closure(...)` independently re-verifies the bound candidate archive, verifies the execution-adapter qualification, checks operation-record handoff identity, re-hashes every operation artifact, and emits actionable PENDING/BLOCKED diagnostics.
- Supplied optional rollback/incident/evidence-capture records are also verified; corrupt optional evidence blocks closure rather than being ignored.
- `ReleaseAuditStatus.CLOSED` means the required audit evidence set is complete and internally consistent. It **does not** change candidate status, target-gate status, deployment approval, or stable-promotion truth.
- Duplicate recipe/operation records are BLOCKED as ambiguous audit truth.
- Persisted audit findings are included in the deterministic audit identity, so diagnostic tampering is detectable.

## Deterministic audit package

`package_release_audit_closure(...)` creates a deterministic, self-contained ZIP containing:

- `release-audit.json`;
- exact Wave 68 `handoff.json`;
- exact execution-adapter qualification JSON;
- exact verified Wave 67 candidate archive bytes;
- still hash-verified adapter qualification artifacts;
- operation records plus still hash-verified runbook evidence;
- `MANIFEST.sha256` covering every other archive entry.

A BLOCKED or changed evidence set cannot be packaged. PENDING audit packages are allowed for controlled gap handoff, but remain visibly PENDING.

## CLI

```bash
nicegui-base execution-adapter-qualify adapter-qualification.json \
  --artifact-base-dir ./qualification-artifacts \
  --output normalized-adapter-qualification.json

nicegui-base release-audit handoff.json normalized-adapter-qualification.json promotion-operation.json \
  --output release-audit.json \
  --package release-audit.zip
```

The CLI returns `0` for QUALIFIED/CLOSED, `2` for PENDING, and `1` for BLOCKED. Neither command calls a company deployment API.

## Generated application helpers

Semiconductor starters now include additive helpers in `services/release_evidence.py`:

- `qualify_promotion_execution_adapter(...)`
- `close_release_audit(...)`

All Wave 65–68 generated release-evidence helpers remain intact.

## Certification boundary

No authoritative company execution adapter or real enterprise promotion artifacts were supplied in this build environment. Wave 69 therefore certifies the generic qualification/audit machinery and source package only. Actual company execution-adapter qualification, installed target runtime/browser/provider/data/human evidence, external deployment execution, and stable 3.0.0 promotion remain PENDING until genuine company artifacts are supplied and verified.
