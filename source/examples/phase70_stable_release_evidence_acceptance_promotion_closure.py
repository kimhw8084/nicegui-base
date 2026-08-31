"""Wave 70 source-only example.

The generic package has no company acceptance artifact, so this example exposes the
policy/registry only and deliberately makes no stable-release or deployment claim.
"""
from nicegui_base import (
    STABLE_PROMOTION_CLOSURE_POLICY,
    STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS,
)


def describe() -> dict[str, object]:
    return {
        'closure_policy': STABLE_PROMOTION_CLOSURE_POLICY.key,
        'target_version': STABLE_PROMOTION_CLOSURE_POLICY.target_version,
        'acceptance_adapters': tuple(STABLE_RELEASE_EVIDENCE_ACCEPTANCE_ADAPTERS),
        'company_acceptance_evidence': 'PENDING',
        'deployment_performed': False,
        'stable_release_published': False,
    }


if __name__ == '__main__':
    print(describe())
