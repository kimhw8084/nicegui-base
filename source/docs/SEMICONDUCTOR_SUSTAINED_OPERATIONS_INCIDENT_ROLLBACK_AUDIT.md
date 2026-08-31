# Semiconductor sustained-operations acceptance and incident/rollback audit closure

Wave 73 adds a bounded evidence layer above the Wave 72 post-release stability and rollback-readiness authorities. It does not create another monitoring, incident, rollback, deployment, publication, promotion, provider, runtime, or target-gate authority.

## Boundary

The framework may ingest and verify externally produced sustained-operations, incident-audit, rollback-audit, and rollback-execution evidence. It does not perform continuous production monitoring, incident response, rollback, deployment, or publication. Missing real company evidence remains `PENDING`; changed, unsafe, corrupt, or identity-mismatched evidence is `BLOCKED`.

## Immutable Wave 72 package reverification

`verify_stable_rollback_readiness_archive()` independently checks the exact Wave 72 rollback-readiness ZIP:

- safe and unique ZIP paths;
- complete `MANIFEST.sha256` coverage;
- every entry hash;
- persisted rollback-readiness identity;
- separately embedded post-release stability identity;
- nested Wave 71 post-promotion archive hash and independent verification.

A Wave 73 record therefore cannot silently point at a different Wave 72 dossier.

## Sustained-operations acceptance

`SustainedOperationsEvidenceAcceptance` is bound to the exact Wave 72 `readiness_id`, `stability_id`, archive SHA-256, framework version, and exact required NiceGUI version. The stable policy requires externally captured:

- `sustained-operations-window`;
- `incident-audit-summary`.

Requested `ACCEPTED` additionally requires traceable external authority/reference metadata and observed framework/NiceGUI identity. The framework verifies bytes and identity only.

CLI:

```bash
nicegui-base sustained-operations-accept rollback-readiness.json rollback-readiness.zip sustained-operations-manifest.json \
  --output sustained-operations-acceptance.json --format json
```

## Incident / rollback audit closure

`IncidentRollbackAuditClosure` requires the exact Wave 72 readiness dossier plus verified sustained-operations acceptance. The stable policy requires external:

- `incident-audit-closure`;
- `rollback-audit-closure`.

Requested `CLOSED` also requires a traceable external audit authority/reference. `CLOSED` means the documentary evidence audit is complete; it never means NiceGUI Base executed incident response or rollback.

CLI:

```bash
nicegui-base incident-rollback-audit-close rollback-readiness.json rollback-readiness.zip \
  sustained-operations-acceptance.json incident-rollback-audit-manifest.json \
  --output incident-rollback-audit.json --package incident-rollback-audit.zip --format json
```

PENDING closures may be packaged for evidence-gap handoff. BLOCKED or changed evidence is refused by the canonical packager.

## Manifest shape

Both JSON manifests use `schema_version: 1`, exact subject identifiers, a requested status, optional authority/reference metadata, and `artifacts` rows with `key` and `path`. Optional per-artifact `sha256` values are checked against captured bytes. Relative paths are restricted to the manifest/artifact base directory.

## Stable-release truth

Wave 66 remains canonical promotion truth. Waves 67–72 remain the candidate, execution, release-audit, acceptance/closure, publication/post-promotion, and stability/rollback authorities. Wave 73 only accepts sustained-operations evidence and closes the incident/rollback documentary audit. It never upgrades upstream status or target gates.
