from __future__ import annotations

import argparse
import json
from pathlib import Path

from nicegui_base.semiconductor.operational_readiness import read_operational_readiness

from .semiconductor_evidence import read_semiconductor_target_evidence
from .semiconductor_orchestrator import PromotionPolicy, build_provider_qualification_pack, build_semiconductor_promotion_decision, write_provider_qualification_pack


def target_qualify_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='nicegui-base target-qualify', description='Aggregate semiconductor target evidence and evaluate fail-closed stable-promotion readiness.')
    parser.add_argument('evidence', nargs='+', help='Wave 65 target-evidence JSON bundle(s)')
    parser.add_argument('--provider', help='Expected provider key. Required when evidence cannot identify exactly one provider.')
    parser.add_argument('--base-dir', type=Path, help='Base directory for relative evidence artifact paths.')
    parser.add_argument('--operational-readiness', action='append', default=[], help='Wave 66 operational-readiness JSON report; repeat for multiple recipes.')
    parser.add_argument('--require-recipe', action='append', default=[], help='Recipe key required in the promotion decision; repeat as needed.')
    parser.add_argument('--qualification-output', type=Path)
    parser.add_argument('--decision-output', type=Path)
    parser.add_argument('--format', choices=('text','json'), default='text')
    args = parser.parse_args(argv[1:] if argv and argv and argv[0].startswith('nicegui-base') else argv)

    bundles = tuple(read_semiconductor_target_evidence(path) for path in args.evidence)
    qualification = build_provider_qualification_pack(bundles, provider=args.provider, base_dir=args.base_dir)
    operational = {}
    for path in args.operational_readiness:
        report = read_operational_readiness(path)
        if report.recipe_key in operational:
            raise ValueError(f'duplicate operational readiness report for recipe {report.recipe_key!r}')
        operational[report.recipe_key] = report
    decision = build_semiconductor_promotion_decision(
        qualification,
        operational_readiness=operational or None,
        policy=PromotionPolicy(required_recipe_keys=tuple(args.require_recipe)),
    )
    if args.qualification_output:
        write_provider_qualification_pack(args.qualification_output, qualification)
    if args.decision_output:
        args.decision_output.parent.mkdir(parents=True, exist_ok=True)
        args.decision_output.write_text(json.dumps(decision.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    payload = {'qualification': qualification.to_dict(), 'decision': decision.to_dict()}
    if args.format == 'json':
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(f'Provider qualification: {qualification.provider} / {qualification.qualification_id}')
        print(f'Stable promotion: {decision.status.value.upper()}')
        for finding in decision.findings:
            print(f'[{finding.severity.value.upper():7}] {finding.code}: {finding.message}')
    if decision.promotable:
        return 0
    return 1 if decision.blocked else 2


if __name__ == '__main__':
    raise SystemExit(target_qualify_main())
