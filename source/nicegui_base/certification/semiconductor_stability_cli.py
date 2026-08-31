from __future__ import annotations

import argparse
import json
from pathlib import Path

from .semiconductor_publication import read_stable_post_promotion_verification
from .semiconductor_stability import (
    POST_RELEASE_STABILITY_EVIDENCE_ADAPTERS,
    PostReleaseStabilityStatus,
    RollbackReadinessStatus,
    load_stable_rollback_readiness_manifest,
    package_stable_rollback_readiness_verification,
    read_post_release_stability_evidence,
    verify_post_release_stability_evidence,
    verify_stable_post_promotion_archive,
    write_post_release_stability_evidence,
    write_stable_rollback_readiness_verification,
)


def _emit(payload: dict, fmt: str) -> None:
    if fmt == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"status={payload['verification']['status']}")
        for finding in payload['verification'].get('findings', ()):
            print(f"- {finding['status']}: {finding['message']}")


def post_release_stability_intake_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base post-release-stability-intake')
    parser.add_argument('post_verification'); parser.add_argument('post_promotion_archive'); parser.add_argument('manifest')
    parser.add_argument('--adapter', choices=tuple(POST_RELEASE_STABILITY_EVIDENCE_ADAPTERS), default='json-manifest')
    parser.add_argument('--artifact-base-dir', type=Path); parser.add_argument('--output', type=Path)
    parser.add_argument('--format', choices=('text','json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)
    post = read_stable_post_promotion_verification(args.post_verification)
    archive_verification = verify_stable_post_promotion_archive(args.post_promotion_archive, expected_verification=post)
    evidence = POST_RELEASE_STABILITY_EVIDENCE_ADAPTERS[args.adapter].load(
        args.manifest, post, args.post_promotion_archive, artifact_base_dir=args.artifact_base_dir,
    )
    verification = verify_post_release_stability_evidence(
        evidence, post_verification=post, post_promotion_archive_path=args.post_promotion_archive, base_dir=args.artifact_base_dir,
    )
    if args.output: write_post_release_stability_evidence(args.output, evidence)
    payload = {'evidence': evidence.to_dict(), 'verification': verification.to_dict(), 'archive_verification': archive_verification.to_dict()}
    _emit(payload, args.format)
    return 0 if verification.status is PostReleaseStabilityStatus.STABLE else (1 if verification.status is PostReleaseStabilityStatus.BLOCKED else 2)


def rollback_readiness_verify_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base rollback-readiness-verify')
    parser.add_argument('post_verification'); parser.add_argument('post_promotion_archive'); parser.add_argument('stability'); parser.add_argument('manifest')
    parser.add_argument('--artifact-base-dir', type=Path); parser.add_argument('--output', type=Path); parser.add_argument('--package', type=Path)
    parser.add_argument('--format', choices=('text','json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)
    post = read_stable_post_promotion_verification(args.post_verification)
    stability = read_post_release_stability_evidence(args.stability)
    verification = load_stable_rollback_readiness_manifest(
        args.manifest, post, args.post_promotion_archive, stability, artifact_base_dir=args.artifact_base_dir,
    )
    if args.output: write_stable_rollback_readiness_verification(args.output, verification)
    package = None
    if args.package:
        package = package_stable_rollback_readiness_verification(args.package, verification, artifact_base_dir=args.artifact_base_dir)
    payload = {'verification': verification.to_dict(), 'package': None if package is None else package.to_dict()}
    _emit(payload, args.format)
    return 0 if verification.status is RollbackReadinessStatus.READY else (1 if verification.status is RollbackReadinessStatus.BLOCKED else 2)


__all__ = ['post_release_stability_intake_main','rollback_readiness_verify_main']
