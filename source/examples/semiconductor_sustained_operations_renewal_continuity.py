"""Wave 74 source-only example: real company renewal evidence is intentionally not fabricated."""
from nicegui_base import (
    OPERATIONAL_ASSURANCE_CONTINUITY_POLICY,
    SUSTAINED_OPERATIONS_RENEWAL_POLICY,
    OperationalAssuranceContinuityStatus,
    OperationsEvidenceFreshness,
    SustainedOperationsRenewalStatus,
)


def evidence_contract() -> dict[str, object]:
    return {
        'renewal_artifacts': SUSTAINED_OPERATIONS_RENEWAL_POLICY.required_artifact_keys,
        'default_max_age_hours': SUSTAINED_OPERATIONS_RENEWAL_POLICY.max_age_hours,
        'default_expiring_within_hours': SUSTAINED_OPERATIONS_RENEWAL_POLICY.expiring_within_hours,
        'continuity_policy': OPERATIONAL_ASSURANCE_CONTINUITY_POLICY.key,
        'missing_real_evidence_status': SustainedOperationsRenewalStatus.PENDING.value,
        'missing_freshness': OperationsEvidenceFreshness.MISSING.value,
        'blocked_continuity': OperationalAssuranceContinuityStatus.BLOCKED.value,
        'framework_performs_monitoring': False,
        'framework_performs_incident_response': False,
        'framework_performs_rollback': False,
    }


if __name__ == '__main__':
    print(evidence_contract())
