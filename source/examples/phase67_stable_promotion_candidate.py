"""Wave 67 stable-promotion candidate example.

This intentionally has no real enterprise target evidence, so it must remain PENDING.
"""
from nicegui_base import (
    PromotionCandidateStatus,
    assimilate_enterprise_target_evidence,
    build_semiconductor_target_evidence_bundle,
    build_stable_promotion_candidate,
)


def main() -> None:
    bundle = build_semiconductor_target_evidence_bundle(
        'spc-monitor',
        metadata={'provider': 'example-provider', 'source_key': 'example-source'},
    )
    enterprise = assimilate_enterprise_target_evidence((bundle,), provider='example-provider')
    candidate = build_stable_promotion_candidate(enterprise)
    assert candidate.status is PromotionCandidateStatus.PENDING
    assert not candidate.release_channel_ready
    print(f'candidate={candidate.candidate_id[:12]} status={candidate.status.value} gaps={len(candidate.gaps)}')


if __name__ == '__main__':
    main()
