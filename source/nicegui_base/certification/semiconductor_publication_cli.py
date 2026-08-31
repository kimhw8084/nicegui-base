from __future__ import annotations

import argparse
import json
from pathlib import Path

from .semiconductor_publication import (
    STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS,
    load_stable_post_promotion_verification_manifest,
    package_stable_post_promotion_verification,
    read_stable_release_publication_evidence,
    verify_stable_promotion_closure_archive,
    verify_stable_release_publication_evidence,
    write_stable_post_promotion_verification,
    write_stable_release_publication_evidence,
)
from .semiconductor_release_acceptance import read_stable_release_promotion_closure


def _emit(payload: dict, fmt: str) -> None:
    if fmt == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)); return
    for key, value in payload.items():
        print(f'{key}: {json.dumps(value, sort_keys=True, ensure_ascii=False) if isinstance(value, (dict, list, tuple)) else value}')


def release_publication_intake_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base release-publication-intake')
    parser.add_argument('closure'); parser.add_argument('closure_archive'); parser.add_argument('manifest')
    parser.add_argument('--adapter', choices=tuple(STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS), default='json-manifest')
    parser.add_argument('--artifact-base-dir', type=Path); parser.add_argument('--output', type=Path)
    parser.add_argument('--format', choices=('text','json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)
    closure = read_stable_release_promotion_closure(args.closure)
    archive_verification = verify_stable_promotion_closure_archive(args.closure_archive, expected_closure=closure)
    evidence = STABLE_RELEASE_PUBLICATION_EVIDENCE_ADAPTERS[args.adapter].load(args.manifest, closure, args.closure_archive, artifact_base_dir=args.artifact_base_dir)
    verification = verify_stable_release_publication_evidence(evidence, closure=closure, closure_archive_path=args.closure_archive, base_dir=args.artifact_base_dir)
    if args.output: write_stable_release_publication_evidence(args.output, evidence)
    _emit({'publication': evidence.to_dict(), 'verification': verification.to_dict(), 'closure_archive': archive_verification.to_dict()}, args.format)
    if not archive_verification.verified or verification.blocked: return 1
    return 0 if verification.published else 2


def post_promotion_verify_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base post-promotion-verify')
    parser.add_argument('closure'); parser.add_argument('closure_archive'); parser.add_argument('publication'); parser.add_argument('manifest')
    parser.add_argument('--artifact-base-dir', type=Path); parser.add_argument('--output', type=Path); parser.add_argument('--package', type=Path)
    parser.add_argument('--format', choices=('text','json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv[0].startswith('nicegui-base') else argv)
    closure = read_stable_release_promotion_closure(args.closure)
    publication = read_stable_release_publication_evidence(args.publication)
    verification = load_stable_post_promotion_verification_manifest(
        args.manifest, closure, args.closure_archive, publication, artifact_base_dir=args.artifact_base_dir,
    )
    if args.output: write_stable_post_promotion_verification(args.output, verification)
    package = None
    if args.package: package = package_stable_post_promotion_verification(args.package, verification, artifact_base_dir=args.artifact_base_dir)
    payload = {'verification': verification.to_dict()}
    if package is not None: payload['package'] = package.to_dict()
    _emit(payload, args.format)
    if verification.status.value == 'verified': return 0
    return 1 if verification.status.value == 'blocked' else 2


__all__ = ['post_promotion_verify_main','release_publication_intake_main']
