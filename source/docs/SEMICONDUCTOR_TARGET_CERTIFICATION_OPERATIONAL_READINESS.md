# Semiconductor target certification and operational readiness

Use Wave 66 only after the application can already be assembled and run through the Wave 62–65 recipe/runtime/provider path.

```python
from nicegui_base import (
    assess_semiconductor_operational_readiness,
    build_provider_qualification_pack,
    build_semiconductor_promotion_decision,
)

readiness = assess_semiconductor_operational_readiness(
    runtime,
    runtime_experience=runtime.experience_state(probe),
    adapter_conformance=adapter_report,
    performance=performance_report,
    benchmark=benchmark_report,
)
qualification = build_provider_qualification_pack(
    (target_evidence_bundle,),
    provider=runtime.source.provider,
    base_dir=evidence_directory,
)
decision = build_semiconductor_promotion_decision(
    qualification,
    operational_readiness={runtime.recipe.key: readiness},
)
```

`decision.promotable` is true only when all required target gates pass, external PASS claims are traceable to current hashed evidence, the bundle identifies the current framework/runtime contract, installed NiceGUI evidence matches the exact required version, evidence is not stale/corrupt, and operational release readiness is complete. Legacy bundles without framework/runtime identity remain PENDING; contradictory version evidence is BLOCKED.

For generated recipe applications, `services/release_evidence.py` includes `evaluate_stable_promotion(...)` and the provider-neutral operational runbook.
