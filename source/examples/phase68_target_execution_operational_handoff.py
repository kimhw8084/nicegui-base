"""Wave 68 target execution intake example.

No real target execution is available here, so a requested browser PASS without an
artifact deliberately remains PENDING after assimilation.
"""
from nicegui_base import (
    FRAMEWORK_VERSION,
    NICEGUI_VERSION,
    TargetEnvironmentFingerprint,
    TargetExecutionIntakeStatus,
    TargetExecutionObservation,
    TargetGateStatus,
    apply_target_execution_intake,
    build_semiconductor_target_evidence_bundle,
    build_target_execution_intake,
    verify_target_execution_intake,
)


def main() -> None:
    base = build_semiconductor_target_evidence_bundle(
        'spc-monitor',
        metadata={'provider': 'example-provider', 'source_key': 'example-source'},
    )
    intake = build_target_execution_intake(
        'spc-monitor',
        provider='example-provider',
        source_key='example-source',
        environment=TargetEnvironmentFingerprint('3.12.0', 'example-target', NICEGUI_VERSION, 'python'),
        observed_framework_version=FRAMEWORK_VERSION,
        observations=(TargetExecutionObservation(
            'supported_browser', TargetGateStatus.PASS,
            'Example requested PASS has no real browser artifact and must not be accepted.',
        ),),
    )
    verification = verify_target_execution_intake(intake)
    assert verification.status is TargetExecutionIntakeStatus.PENDING
    merged = apply_target_execution_intake(base, intake)
    browser = next(gate for gate in merged.certification.gates if gate.key == 'supported_browser')
    assert browser.status is TargetGateStatus.PENDING
    print(f'intake={intake.intake_id[:12]} status={verification.status.value} browser={browser.status.value}')


if __name__ == '__main__':
    main()
