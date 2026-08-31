# Semiconductor stable-promotion candidates

Use Wave 67 after target evidence has been captured through the existing Wave 65/66 authorities.

```python
from nicegui_base import (
    assimilate_enterprise_target_evidence,
    build_promotion_rehearsal,
    build_stable_promotion_candidate,
    package_stable_promotion_candidate,
)

enterprise = assimilate_enterprise_target_evidence(
    bundles,
    operational_readiness=readiness_reports,
    provider="approved-provider-key",
    required_recipe_keys=("spc-monitor",),
    base_dir=evidence_directory,
)

candidate = build_stable_promotion_candidate(enterprise, rehearsals=rehearsal_reports)
package = package_stable_promotion_candidate(
    "stable-candidate.zip",
    candidate,
    artifact_base_dir=evidence_directory,
)
```

A candidate can be packaged while PENDING or BLOCKED. That is intentional: the package is a deterministic handoff of the current evidence and gaps, not a certification mechanism.

Operational rehearsal starts from the canonical runbook:

```python
plan = build_promotion_rehearsal("spc-monitor", "rollback")
```

Record completed or failed runbook step keys only after the rehearsal actually occurs. A rehearsal PASS does not alter target runtime/browser/provider/human evidence.

CLI equivalents:

```bash
nicegui-base promotion-rehearse spc-monitor rollback --completed rollback --completed startup --output rollback.json
nicegui-base promotion-candidate target-evidence.json \
  --provider approved-provider-key \
  --operational-readiness readiness.json \
  --rehearsal rollback.json \
  --output candidate.json \
  --package stable-candidate.zip
```
