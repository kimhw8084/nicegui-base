"""Wave 75 source-only example: longitudinal governance without fabricated company evidence."""
from nicegui_base import (
    OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICY,
    OperationalAssuranceLedgerStatus,
)


def evidence_contract() -> dict[str, object]:
    policy = OPERATIONAL_ASSURANCE_RENEWAL_LEDGER_POLICY
    return {
        'policy_key': policy.key,
        'target_version': policy.target_version,
        'default_max_gap_hours': policy.max_gap_hours,
        'default_expiring_within_hours': policy.expiring_within_hours,
        'default_max_overlap_hours': policy.max_overlap_hours,
        'missing_period_status': OperationalAssuranceLedgerStatus.PENDING.value,
        'tampered_period_status': OperationalAssuranceLedgerStatus.BLOCKED.value,
        'framework_performs_monitoring': False,
        'framework_performs_incident_response': False,
        'framework_performs_rollback': False,
        'framework_performs_deployment_or_publication': False,
    }


if __name__ == '__main__':
    print(evidence_contract())
