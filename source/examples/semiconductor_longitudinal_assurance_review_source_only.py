"""Wave 76 source-only review/exception governance example.

This example intentionally creates no real company review evidence and therefore makes no
REVIEWED/GOVERNED company claim. It demonstrates the bounded policy surface only.
"""
from nicegui_base import LONGITUDINAL_EVIDENCE_EXCEPTION_POLICY, LongitudinalEvidenceExceptionDecision, EvidenceExceptionDisposition

DEFAULT_POLICY = LONGITUDINAL_EVIDENCE_EXCEPTION_POLICY
EXAMPLE_DECISION = LongitudinalEvidenceExceptionDecision(
    'ledger_coverage_gap', EvidenceExceptionDisposition.UNRESOLVED,
    'Example only: real exception authority must come from an approved external reviewer.',
)

assert DEFAULT_POLICY.permit_blocked_evidence_exceptions is False
assert EXAMPLE_DECISION.disposition is EvidenceExceptionDisposition.UNRESOLVED
