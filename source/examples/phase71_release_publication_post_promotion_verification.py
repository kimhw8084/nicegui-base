"""Wave 71 source-only example.

No company publication or post-release evidence is bundled with the generic source,
so this example intentionally reports those external gates as PENDING.
"""
from nicegui_base import POST_PROMOTION_VERIFICATION_POLICY, STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS


def describe() -> dict[str, object]:
    return {
        'target_version': POST_PROMOTION_VERIFICATION_POLICY.target_version,
        'publication_adapters': tuple(STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS),
        'required_post_release_artifacts': POST_PROMOTION_VERIFICATION_POLICY.required_artifact_keys,
        'company_publication_evidence': 'PENDING',
        'post_promotion_verification': 'PENDING',
        'deployment_performed_by_framework': False,
        'publication_performed_by_framework': False,
        'continuous_monitoring_performed_by_framework': False,
    }


if __name__ == '__main__':
    print(describe())
